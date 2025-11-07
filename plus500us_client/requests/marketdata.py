from __future__ import annotations
import time
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from .config import Config
from .session import SessionManager
from .models import Quote, Plus500InstrumentPrice, Plus500ChartData, Plus500BuySellInfo
from .errors import AuthenticationError, TradingError


class MarketDataClient:
    """Enhanced Market Data Client with Plus500-specific operations for Phase 2"""
    
    def __init__(self, cfg: Config, sm: SessionManager):
        self.cfg = cfg
        self.sm = sm
        self._last_request_ts = 0.0
        self._price_cache: Dict[str, Plus500InstrumentPrice] = {}
        self._cache_ttl_seconds = 5  # Cache prices for 5 seconds
        self._last_cache_update: Dict[str, datetime] = {}

    def _throttle(self) -> None:
        interval = max(0.3, self.cfg.poll_interval_ms / 1000.0)
        now = time.time()
        dt = now - self._last_request_ts
        if dt < interval:
            time.sleep(interval - dt)
        self._last_request_ts = time.time()

    # Legacy methods for backward compatibility
    def get_quote(self, instrument_id: str) -> Quote:
        self._throttle()
        s = self.sm.session
        base = self.cfg.base_url
        r = s.get(base + f"/api/quotes/{instrument_id}", timeout=15)
        r.raise_for_status()
        return Quote(**r.json())

    def get_quotes(self, instrument_ids: List[str]) -> List[Quote]:
        quotes = []
        for chunk in (instrument_ids[i:i+25] for i in range(0, len(instrument_ids), 25)):
            self._throttle()
            s = self.sm.session
            base = self.cfg.base_url
            r = s.post(base + "/api/quotes/batch", json={"ids": chunk}, timeout=20)
            r.raise_for_status()
            quotes.extend([Quote(**q) for q in r.json().get("quotes", [])])
        return quotes

    # Phase 2 Enhanced Plus500 Market Data Operations

    def get_plus500_instrument_prices(self, instrument_ids: List[str], use_cache: bool = True) -> List[Plus500InstrumentPrice]:
        """
        Get real-time Plus500 instrument prices using GetInstrumentPricesImm endpoint
        
        Args:
            instrument_ids: List of Plus500 instrument IDs
            use_cache: Whether to use cached prices if available
            
        Returns:
            List of Plus500InstrumentPrice objects with real-time pricing
        """
        if not self.sm.has_valid_plus500_session():
            raise AuthenticationError("Valid Plus500 session required")
        
        # Check cache first if enabled
        if use_cache:
            cached_prices = []
            uncached_ids = []
            now = datetime.now(timezone.utc)
            
            for instrument_id in instrument_ids:
                if (instrument_id in self._price_cache and 
                    instrument_id in self._last_cache_update and
                    (now - self._last_cache_update[instrument_id]).total_seconds() < self._cache_ttl_seconds):
                    cached_prices.append(self._price_cache[instrument_id])
                else:
                    uncached_ids.append(instrument_id)
            
            # If all prices are cached and fresh, return them
            if not uncached_ids:
                return cached_prices
            
            # Update cache for uncached instruments
            if uncached_ids:
                fresh_prices = self._fetch_plus500_prices(uncached_ids)
                self._update_price_cache(fresh_prices)
                return cached_prices + fresh_prices
        
        # No caching, fetch all prices
        return self._fetch_plus500_prices(instrument_ids)

    def _fetch_plus500_prices(self, instrument_ids: List[str]) -> List[Plus500InstrumentPrice]:
        """Internal method to fetch prices from Plus500 API"""
        session_info = self.sm._load_plus500_session()
        if not session_info:
            raise AuthenticationError("No active Plus500 session found")
        
        payload = {
            'SessionID': session_info.session_id,
            'SubSessionID': session_info.sub_session_id,
            'SessionToken': session_info.session_token,
            'InstrumentIds': ','.join(instrument_ids)
        }
        
        response = self.sm.make_plus500_request('/GetInstrumentPricesImm', payload)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                return [Plus500InstrumentPrice(**item) for item in data]
            else:
                # Single instrument response
                return [Plus500InstrumentPrice(**data)]
        else:
            raise TradingError(f"Failed to get instrument prices: {response.status_code}")

    def _update_price_cache(self, prices: List[Plus500InstrumentPrice]) -> None:
        """Update the internal price cache with fresh data"""
        now = datetime.now(timezone.utc)
        for price in prices:
            self._price_cache[price.instrument_id] = price
            self._last_cache_update[price.instrument_id] = now

    def get_plus500_single_price(self, instrument_id: str, use_cache: bool = True) -> Plus500InstrumentPrice:
        """
        Get a single instrument price with caching support
        
        Args:
            instrument_id: Plus500 instrument ID
            use_cache: Whether to use cached price if available
            
        Returns:
            Plus500InstrumentPrice object
        """
        prices = self.get_plus500_instrument_prices([instrument_id], use_cache=use_cache)
        if not prices:
            raise TradingError(f"No price data available for instrument {instrument_id}")
        return prices[0]

    def get_plus500_chart_data(self, instrument_id: str, timeframe: str = '1M', 
                              start_time: Optional[datetime] = None, 
                              end_time: Optional[datetime] = None) -> List[Plus500ChartData]:
        """
        Get Plus500 chart data using GetChartDataImm endpoint
        
        Args:
            instrument_id: Plus500 instrument ID
            timeframe: Chart timeframe ('1M', '5M', '15M', '1H', '4H', '1D')
            start_time: Start time for historical data (optional)
            end_time: End time for historical data (optional)
            
        Returns:
            List of Plus500ChartData objects
        """
        if not self.sm.has_valid_plus500_session():
            raise AuthenticationError("Valid Plus500 session required")
        
        session_info = self.sm._load_plus500_session()
        if not session_info:
            raise AuthenticationError("No active Plus500 session found")
        
        payload = {
            'SessionID': session_info.session_id,
            'SubSessionID': session_info.sub_session_id,
            'SessionToken': session_info.session_token,
            'InstrumentId': instrument_id,
            'Timeframe': timeframe
        }
        
        # Add time range if specified
        if start_time:
            payload['StartTime'] = start_time.isoformat()
        if end_time:
            payload['EndTime'] = end_time.isoformat()
        
        response = self.sm.make_plus500_request('/GetChartDataImm', payload)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                return [Plus500ChartData(**item) for item in data]
            else:
                return [Plus500ChartData(**data)]
        else:
            raise TradingError(f"Failed to get chart data: {response.status_code}")

    def get_plus500_buy_sell_info(self, instrument_id: str) -> Plus500BuySellInfo:
        """
        Get Plus500 pre-trade buy/sell information using FuturesBuySellInfoImm endpoint
        
        Args:
            instrument_id: Plus500 instrument ID
            
        Returns:
            Plus500BuySellInfo object with trading information
        """
        if not self.sm.has_valid_plus500_session():
            raise AuthenticationError("Valid Plus500 session required")
        
        session_info = self.sm._load_plus500_session()
        if not session_info:
            raise AuthenticationError("No active Plus500 session found")
        
        payload = {
            'SessionID': session_info.session_id,
            'SubSessionID': session_info.sub_session_id,
            'SessionToken': session_info.session_token,
            'InstrumentId': instrument_id
        }
        
        response = self.sm.make_plus500_request('/FuturesBuySellInfoImm', payload)
        
        if response.status_code == 200:
            data = response.json()
            return Plus500BuySellInfo(**data)
        else:
            raise TradingError(f"Failed to get buy/sell info: {response.status_code}")

    def get_market_overview(self, categories: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get market overview with pricing data for multiple instruments
        
        Args:
            categories: Optional list of categories to filter by
            
        Returns:
            Market overview data organized by category
        """
        try:
            # Get instruments first (this would typically come from instruments client)
            # For now, we'll return a structure that can be populated
            overview = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'categories': {},
                'total_instruments': 0,
                'active_markets': 0
            }
            
            # This would be enhanced with actual instrument discovery
            # and bulk price fetching in a real implementation
            
            return overview
            
        except Exception as e:
            raise TradingError(f"Failed to get market overview: {str(e)}")

    def calculate_spread_percentage(self, instrument_id: str) -> Decimal:
        """
        Calculate the spread percentage for an instrument
        
        Args:
            instrument_id: Plus500 instrument ID
            
        Returns:
            Spread percentage as Decimal
        """
        try:
            price_data = self.get_plus500_single_price(instrument_id)
            
            if price_data.bid_price and price_data.ask_price:
                spread = price_data.ask_price - price_data.bid_price
                mid_price = (price_data.bid_price + price_data.ask_price) / 2
                spread_percentage = (spread / mid_price) * 100
                return spread_percentage
            else:
                raise TradingError(f"Missing bid/ask prices for instrument {instrument_id}")
                
        except Exception as e:
            raise TradingError(f"Failed to calculate spread: {str(e)}")

    def get_price_alerts(self, price_thresholds: Dict[str, Dict[str, Decimal]]) -> List[Dict[str, Any]]:
        """
        Check current prices against alert thresholds
        
        Args:
            price_thresholds: Dict mapping instrument_id to {'high': price, 'low': price}
            
        Returns:
            List of triggered alerts
        """
        alerts = []
        
        try:
            instrument_ids = list(price_thresholds.keys())
            current_prices = self.get_plus500_instrument_prices(instrument_ids, use_cache=True)
            
            for price_data in current_prices:
                instrument_id = price_data.instrument_id
                thresholds = price_thresholds.get(instrument_id, {})
                
                current_price = price_data.last_price or price_data.bid_price
                if not current_price:
                    continue
                
                # Check high threshold
                if 'high' in thresholds and current_price >= thresholds['high']:
                    alerts.append({
                        'instrument_id': instrument_id,
                        'symbol': price_data.symbol,
                        'alert_type': 'high_threshold',
                        'current_price': current_price,
                        'threshold_price': thresholds['high'],
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
                
                # Check low threshold
                if 'low' in thresholds and current_price <= thresholds['low']:
                    alerts.append({
                        'instrument_id': instrument_id,
                        'symbol': price_data.symbol,
                        'alert_type': 'low_threshold',
                        'current_price': current_price,
                        'threshold_price': thresholds['low'],
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
            
            return alerts
            
        except Exception as e:
            raise TradingError(f"Failed to check price alerts: {str(e)}")

    def clear_price_cache(self) -> None:
        """Clear the internal price cache"""
        self._price_cache.clear()
        self._last_cache_update.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring"""
        now = datetime.now(timezone.utc)
        fresh_entries = sum(
            1 for update_time in self._last_cache_update.values()
            if (now - update_time).total_seconds() < self._cache_ttl_seconds
        )
        
        return {
            'total_cached_instruments': len(self._price_cache),
            'fresh_cache_entries': fresh_entries,
            'cache_ttl_seconds': self._cache_ttl_seconds,
            'last_update_times': {
                instrument_id: update_time.isoformat()
                for instrument_id, update_time in self._last_cache_update.items()
            }
        }
