from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from .config import Config
from .session import SessionManager
from .models import Instrument, Plus500InstrumentData, Plus500BuySellInfo
from .errors import InstrumentNotFound, AuthenticationError, TradingError


class InstrumentsClient:
    """Enhanced Instruments Client with Plus500-specific operations for Phase 2"""
    
    def __init__(self, cfg: Config, sm: SessionManager):
        self.cfg = cfg
        self.sm = sm
        self._cache: dict[str, Instrument] = {}
        self._plus500_cache: dict[str, Plus500InstrumentData] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_minutes = 30  # Cache instruments for 30 minutes

    # Legacy methods for backward compatibility
    def list_instruments(self, market: Optional[str] = None) -> List[Instrument]:
        s = self.sm.session
        base = self.cfg.base_url
        r = s.get(base + "/ClientRequest/GetTradeInstruments", timeout=20)
        r.raise_for_status()
        items = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
        result = [Instrument(**it) for it in items]
        for ins in result:
            self._cache[ins.id] = ins
        return result

    def get_instrument(self, symbol_or_id: str) -> Instrument:
        for ins in self._cache.values():
            if ins.id == symbol_or_id or ins.symbol == symbol_or_id:
                return ins
        for ins in self.list_instruments():
            if ins.id == symbol_or_id or ins.symbol == symbol_or_id:
                return ins
        raise InstrumentNotFound(symbol_or_id)

    def resolve_contract(self, root: str, expiry: str) -> Instrument:
        symbol = f"{root}{expiry}"
        return self.get_instrument(symbol)

    # Phase 2 Enhanced Plus500 Instrument Operations

    def get_plus500_instruments(self, force_refresh: bool = False) -> List[Plus500InstrumentData]:
        """
        Get Plus500 instruments using GetTradeInstruments endpoint with enhanced caching
        
        Args:
            force_refresh: Force refresh of cached data
            
        Returns:
            List of Plus500InstrumentData objects
        """
        # Check cache validity
        if not force_refresh and self._is_cache_valid():
            return list(self._plus500_cache.values())
        
        if not self.sm.has_valid_plus500_session():
            raise AuthenticationError("Valid Plus500 session required")
        
        session_info = self.sm._load_plus500_session()
        if not session_info:
            raise AuthenticationError("No active Plus500 session found")
        
        payload = {
            'SessionID': session_info.session_id,
            'SubSessionID': session_info.sub_session_id,
            'SessionToken': session_info.session_token
        }
        
        response = self.sm.make_plus500_request('/GetTradeInstruments', payload)
        
        if response.status_code == 200:
            data = response.json()
            instruments = []
            
            if isinstance(data, list):
                instruments = [Plus500InstrumentData(**item) for item in data]
            else:
                # Handle single instrument or wrapped response
                items = data.get('instruments', [data]) if isinstance(data, dict) else [data]
                instruments = [Plus500InstrumentData(**item) for item in items]
            
            # Update cache
            self._plus500_cache.clear()
            for instrument in instruments:
                self._plus500_cache[instrument.instrument_id] = instrument
            
            self._cache_timestamp = datetime.now(timezone.utc)
            return instruments
        else:
            raise TradingError(f"Failed to get Plus500 instruments: {response.status_code}")

    def _is_cache_valid(self) -> bool:
        """Check if the current cache is still valid"""
        if not self._cache_timestamp or not self._plus500_cache:
            return False
        
        now = datetime.now(timezone.utc)
        cache_age_minutes = (now - self._cache_timestamp).total_seconds() / 60
        return cache_age_minutes < self._cache_ttl_minutes

    def get_plus500_instrument_by_id(self, instrument_id: str, force_refresh: bool = False) -> Plus500InstrumentData:
        """
        Get a specific Plus500 instrument by ID
        
        Args:
            instrument_id: Plus500 instrument ID
            force_refresh: Force refresh of cached data
            
        Returns:
            Plus500InstrumentData object
        """
        # Check cache first
        if not force_refresh and instrument_id in self._plus500_cache and self._is_cache_valid():
            return self._plus500_cache[instrument_id]
        
        # Refresh cache and search
        instruments = self.get_plus500_instruments(force_refresh=True)
        
        for instrument in instruments:
            if instrument.instrument_id == instrument_id:
                return instrument
        
        raise InstrumentNotFound(f"Plus500 instrument not found: {instrument_id}")

    def search_plus500_instruments(self, 
                                  symbol: Optional[str] = None,
                                  name: Optional[str] = None, 
                                  category: Optional[str] = None,
                                  subcategory: Optional[str] = None,
                                  is_tradable: Optional[bool] = None) -> List[Plus500InstrumentData]:
        """
        Search Plus500 instruments with various filters
        
        Args:
            symbol: Symbol to search for (partial match)
            name: Name to search for (partial match)
            category: Exact category match
            subcategory: Exact subcategory match
            is_tradable: Filter by tradable status
            
        Returns:
            List of matching Plus500InstrumentData objects
        """
        instruments = self.get_plus500_instruments()
        filtered = instruments
        
        if symbol:
            filtered = [i for i in filtered if symbol.upper() in i.symbol.upper()]
        
        if name:
            filtered = [i for i in filtered if name.upper() in i.name.upper()]
        
        if category:
            filtered = [i for i in filtered if i.category == category]
        
        if subcategory:
            filtered = [i for i in filtered if i.subcategory == subcategory]
        
        if is_tradable is not None:
            filtered = [i for i in filtered if i.is_tradable == is_tradable]
        
        return filtered

    def get_plus500_instrument_categories(self) -> Dict[str, List[str]]:
        """
        Get all available categories and subcategories
        
        Returns:
            Dict mapping categories to lists of subcategories
        """
        instruments = self.get_plus500_instruments()
        categories: Dict[str, set] = {}
        
        for instrument in instruments:
            if instrument.category:
                if instrument.category not in categories:
                    categories[instrument.category] = set()
                
                if instrument.subcategory:
                    categories[instrument.category].add(instrument.subcategory)
        
        # Convert sets to sorted lists
        return {cat: sorted(list(subcats)) for cat, subcats in categories.items()}

    def get_plus500_tradable_instruments(self) -> List[Plus500InstrumentData]:
        """
        Get only tradable Plus500 instruments
        
        Returns:
            List of tradable Plus500InstrumentData objects
        """
        return self.search_plus500_instruments(is_tradable=True)

    def get_plus500_instruments_by_category(self, category: str) -> List[Plus500InstrumentData]:
        """
        Get Plus500 instruments filtered by category
        
        Args:
            category: Category name to filter by
            
        Returns:
            List of Plus500InstrumentData objects in the specified category
        """
        return self.search_plus500_instruments(category=category)

    def get_plus500_instrument_details(self, instrument_id: str) -> Dict[str, Any]:
        """
        Get detailed Plus500 instrument information using FuturesInstrumentDetailsImm
        
        Args:
            instrument_id: Plus500 instrument ID
            
        Returns:
            Detailed instrument information
        """
        payload = {'InstrumentId': instrument_id}
        
        response = self.sm.make_plus500_request("FuturesInstrumentDetailsImm", payload)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise TradingError(f"Failed to get instrument details: {response.status_code}")

    def get_plus500_market_summary(self) -> Dict[str, Any]:
        """
        Get Plus500 market summary with instrument counts and categories
        
        Returns:
            Market summary statistics
        """
        try:
            instruments = self.get_plus500_instruments()
            categories = self.get_plus500_instrument_categories()
            
            tradable_count = len([i for i in instruments if i.is_tradable])
            total_count = len(instruments)
            
            # Get market status summary
            market_statuses = {}
            for instrument in instruments:
                status = instrument.market_status or 'Unknown'
                market_statuses[status] = market_statuses.get(status, 0) + 1
            
            summary = {
                'total_instruments': total_count,
                'tradable_instruments': tradable_count,
                'non_tradable_instruments': total_count - tradable_count,
                'categories': {cat: len(subcats) for cat, subcats in categories.items()},
                'market_statuses': market_statuses,
                'cache_timestamp': self._cache_timestamp.isoformat() if self._cache_timestamp else None,
                'cache_age_minutes': (
                    (datetime.now(timezone.utc) - self._cache_timestamp).total_seconds() / 60
                    if self._cache_timestamp else None
                )
            }
            
            return summary
            
        except Exception as e:
            raise TradingError(f"Failed to get market summary: {str(e)}")

    def refresh_plus500_cache(self) -> int:
        """
        Force refresh of Plus500 instrument cache
        
        Returns:
            Number of instruments loaded
        """
        instruments = self.get_plus500_instruments(force_refresh=True)
        return len(instruments)

    def clear_cache(self) -> None:
        """Clear all cached instrument data"""
        self._cache.clear()
        self._plus500_cache.clear()
        self._cache_timestamp = None

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring"""
        return {
            'legacy_cache_size': len(self._cache),
            'plus500_cache_size': len(self._plus500_cache),
            'cache_timestamp': self._cache_timestamp.isoformat() if self._cache_timestamp else None,
            'cache_ttl_minutes': self._cache_ttl_minutes,
            'cache_is_valid': self._is_cache_valid()
        }
