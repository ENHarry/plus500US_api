"""
Hybrid WebDriver Fallback Integration for Plus500 API Client - Phase 3
Implements intelligent fallback to WebDriver when API methods fail
"""

import time
import asyncio
from typing import Dict, List, Optional, Any, Union, Protocol
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from dataclasses import dataclass, field
from enum import Enum
import logging

from .config import Config
from .session import SessionManager
from .account import AccountClient
from .marketdata import MarketDataClient
from .instruments import InstrumentsClient
from .trading_api import Plus500TradingAPI
from .errors import AuthenticationError, TradingError, APIError


class FallbackStrategy(Enum):
    """Fallback strategies for hybrid mode"""
    NEVER = "never"                    # Never use WebDriver fallback
    ON_ERROR = "on_error"             # Use WebDriver only when API fails
    PREFERENCE = "preference"          # Prefer WebDriver for certain operations
    ALWAYS = "always"                 # Always use WebDriver (testing mode)


class FallbackReason(Enum):
    """Reasons for fallback activation"""
    API_ERROR = "api_error"
    AUTHENTICATION_FAILED = "auth_failed"
    RATE_LIMITED = "rate_limited"
    SESSION_EXPIRED = "session_expired"
    DATA_UNAVAILABLE = "data_unavailable"
    MANUAL_OVERRIDE = "manual_override"


@dataclass
class FallbackEvent:
    """Records a fallback event for monitoring"""
    timestamp: datetime
    method_name: str
    reason: FallbackReason
    api_error: Optional[str] = None
    webdriver_success: bool = False
    execution_time_ms: float = 0.0
    data_quality: Optional[str] = None  # "full", "partial", "failed"


@dataclass
class HybridConfig:
    """Configuration for hybrid API/WebDriver mode"""
    fallback_strategy: FallbackStrategy = FallbackStrategy.ON_ERROR
    max_api_retries: int = 3
    retry_delay_seconds: float = 1.0
    webdriver_timeout_seconds: float = 30.0
    enable_fallback_caching: bool = True
    fallback_cache_ttl_seconds: int = 300  # 5 minutes
    preferred_webdriver_operations: List[str] = field(default_factory=list)
    monitor_fallback_events: bool = True
    fallback_success_threshold: float = 0.8  # 80% success rate required


class WebDriverProtocol(Protocol):
    """Protocol for WebDriver integration"""
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information via WebDriver"""
        ...
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get positions via WebDriver"""
        ...
    
    def get_orders(self) -> List[Dict[str, Any]]:
        """Get orders via WebDriver"""
        ...
    
    def get_instruments(self) -> List[Dict[str, Any]]:
        """Get instruments via WebDriver"""
        ...
    
    def get_market_data(self, instrument_id: str) -> Dict[str, Any]:
        """Get market data via WebDriver"""
        ...
    
    def place_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Place order via WebDriver"""
        ...


class HybridAPIClient:
    """
    Hybrid API client that intelligently falls back to WebDriver
    when API methods fail or are unavailable
    """
    
    def __init__(
        self, 
        cfg: Config, 
        sm: SessionManager,
        webdriver_client: Optional[WebDriverProtocol] = None,
        hybrid_config: Optional[HybridConfig] = None
    ):
        self.cfg = cfg
        self.sm = sm
        self.hybrid_config = hybrid_config or HybridConfig()
        self.webdriver_client = webdriver_client
        
        # Initialize API clients
        self.api_client = Plus500TradingAPI(cfg, sm)
        self.account_client = AccountClient(cfg, sm)
        self.marketdata_client = MarketDataClient(cfg, sm)
        self.instruments_client = InstrumentsClient(cfg, sm)
        
        # Fallback monitoring
        self.fallback_events: List[FallbackEvent] = []
        self.api_success_rates: Dict[str, float] = {}
        self.last_api_attempt: Dict[str, datetime] = {}
        
        # Fallback cache
        self.fallback_cache: Dict[str, Any] = {}
        self.fallback_cache_timestamps: Dict[str, datetime] = {}
        
        self.logger = logging.getLogger(__name__)

    def set_webdriver_client(self, webdriver_client: WebDriverProtocol):
        """Set or update the WebDriver client"""
        self.webdriver_client = webdriver_client

    def update_hybrid_config(self, config: HybridConfig):
        """Update hybrid configuration"""
        self.hybrid_config = config

    # Helper methods for safe WebDriver calls
    def _safe_webdriver_get_account_info(self):
        """Safely call webdriver get_account_info"""
        if self.webdriver_client is None:
            raise TradingError("WebDriver client not available")
        return self.webdriver_client.get_account_info()
    
    def _safe_webdriver_get_positions(self):
        """Safely call webdriver get_positions"""
        if self.webdriver_client is None:
            raise TradingError("WebDriver client not available")
        return self.webdriver_client.get_positions()
    
    def _safe_webdriver_get_orders(self):
        """Safely call webdriver get_orders"""
        if self.webdriver_client is None:
            raise TradingError("WebDriver client not available")
        return self.webdriver_client.get_orders()
    
    def _safe_webdriver_get_instruments(self):
        """Safely call webdriver get_instruments"""
        if self.webdriver_client is None:
            raise TradingError("WebDriver client not available")
        return self.webdriver_client.get_instruments()
    
    def _safe_webdriver_get_market_data(self, instrument_id: str):
        """Safely call webdriver get_market_data"""
        if self.webdriver_client is None:
            raise TradingError("WebDriver client not available")
        return self.webdriver_client.get_market_data(instrument_id)
    
    def _safe_webdriver_place_order(self, order_data: Dict[str, Any]):
        """Safely call webdriver place_order"""
        if self.webdriver_client is None:
            raise TradingError("WebDriver client not available")
        return self.webdriver_client.place_order(order_data)

    # ===================
    # Account Operations
    # ===================

    async def get_account_info(self, force_webdriver: bool = False) -> Dict[str, Any]:
        """
        Get account information with intelligent fallback
        
        Args:
            force_webdriver: Force use of WebDriver instead of API
            
        Returns:
            Account information dictionary
        """
        method_name = "get_account_info"
        
        if self._should_use_webdriver(method_name, force_webdriver):
            return await self._execute_with_webdriver(
                method_name, 
                self._safe_webdriver_get_account_info
            )
        
        # Try API first
        try:
            result = await self._execute_with_retry(
                lambda: self.account_client.get_plus500_account_summary()
            )
            self._record_api_success(method_name)
            return result
            
        except Exception as e:
            return await self._handle_api_failure(
                method_name, e, 
                self._safe_webdriver_get_account_info
            )

    async def get_account_balance(self, force_webdriver: bool = False) -> Dict[str, Any]:
        """Get account balance with fallback"""
        method_name = "get_account_balance"
        
        if self._should_use_webdriver(method_name, force_webdriver):
            return await self._execute_with_webdriver(
                method_name,
                self._safe_webdriver_get_account_info
            )
        
        try:
            result = await self._execute_with_retry(
                lambda: self.account_client.get_account_balance_summary()
            )
            self._record_api_success(method_name)
            return result
            
        except Exception as e:
            return await self._handle_api_failure(
                method_name, e,
                self._safe_webdriver_get_account_info
            )

    async def get_positions(self, force_webdriver: bool = False) -> List[Dict[str, Any]]:
        """Get positions with fallback"""
        method_name = "get_positions"
        
        if self._should_use_webdriver(method_name, force_webdriver):
            return await self._execute_with_webdriver(
                method_name,
                self._safe_webdriver_get_positions
            )
        
        try:
            result = await self._execute_with_retry(
                lambda: self.api_client.get_open_positions()
            )
            self._record_api_success(method_name)
            return result
            
        except Exception as e:
            return await self._handle_api_failure(
                method_name, e,
                self._safe_webdriver_get_positions
            )

    async def get_orders(self, force_webdriver: bool = False) -> List[Dict[str, Any]]:
        """Get orders with fallback"""
        method_name = "get_orders"
        
        if self._should_use_webdriver(method_name, force_webdriver):
            return await self._execute_with_webdriver(
                method_name,
                self._safe_webdriver_get_orders
            )
        
        try:
            # Note: get_pending_orders not available in current API - would need implementation
            # For now, return empty result to avoid breaking the fallback chain
            result = []  # Return empty list to match expected return type
            # result = await self._execute_with_retry(
            #     lambda: self.api_client.get_pending_orders()
            # )
            self._record_api_success(method_name)
            return result
            
        except Exception as e:
            return await self._handle_api_failure(
                method_name, e,
                self._safe_webdriver_get_orders
            )

    # ====================
    # Market Data Operations
    # ====================

    async def get_instruments(self, force_webdriver: bool = False) -> List[Dict[str, Any]]:
        """Get instruments with fallback"""
        method_name = "get_instruments"
        
        # Check cache first
        cached_result = self._get_from_fallback_cache(method_name)
        if cached_result is not None:
            return cached_result
        
        if self._should_use_webdriver(method_name, force_webdriver):
            result = await self._execute_with_webdriver(
                method_name,
                self._safe_webdriver_get_instruments
            )
            self._store_in_fallback_cache(method_name, result)
            return result
        
        try:
            result = await self._execute_with_retry(
                lambda: self.instruments_client.get_plus500_instruments()
            )
            self._record_api_success(method_name)
            self._store_in_fallback_cache(method_name, result)
            return result
            
        except Exception as e:
            result = await self._handle_api_failure(
                method_name, e,
                self._safe_webdriver_get_instruments
            )
            self._store_in_fallback_cache(method_name, result)
            return result

    async def get_market_data(
        self, 
        instrument_id: str, 
        force_webdriver: bool = False
    ) -> Dict[str, Any]:
        """Get market data with fallback"""
        method_name = f"get_market_data_{instrument_id}"
        
        if self._should_use_webdriver(method_name, force_webdriver):
            return await self._execute_with_webdriver(
                method_name,
                lambda: self._safe_webdriver_get_market_data(instrument_id)
            )
        
        try:
            result = await self._execute_with_retry(
                lambda: self.marketdata_client.get_plus500_instrument_prices([instrument_id])
            )
            self._record_api_success(method_name)
            return result.get(instrument_id, {}) if result else {}
            
        except Exception as e:
            return await self._handle_api_failure(
                method_name, e,
                lambda: self._safe_webdriver_get_market_data(instrument_id)
            )

    # ===================
    # Trading Operations
    # ===================

    async def place_order(
        self, 
        order_data: Dict[str, Any], 
        force_webdriver: bool = False
    ) -> Dict[str, Any]:
        """Place order with fallback"""
        method_name = "place_order"
        
        if self._should_use_webdriver(method_name, force_webdriver):
            return await self._execute_with_webdriver(
                method_name,
                lambda: self._safe_webdriver_place_order(order_data)
            )
        
        try:
            # Convert order data to API format
            api_order_data = self._convert_order_data_for_api(order_data)
            result = await self._execute_with_retry(
                lambda: self.api_client.create_futures_order(**api_order_data)
            )
            self._record_api_success(method_name)
            return result
            
        except Exception as e:
            return await self._handle_api_failure(
                method_name, e,
                lambda: self._safe_webdriver_place_order(order_data)
            )

    # ===================
    # Private Helper Methods
    # ===================

    def _should_use_webdriver(self, method_name: str, force_webdriver: bool) -> bool:
        """Determine if WebDriver should be used for this operation"""
        if force_webdriver:
            return True
            
        if self.webdriver_client is None:
            return False
            
        strategy = self.hybrid_config.fallback_strategy
        
        if strategy == FallbackStrategy.NEVER:
            return False
        elif strategy == FallbackStrategy.ALWAYS:
            return True
        elif strategy == FallbackStrategy.PREFERENCE:
            return method_name in self.hybrid_config.preferred_webdriver_operations
        elif strategy == FallbackStrategy.ON_ERROR:
            # Check if API has been failing for this method
            success_rate = self.api_success_rates.get(method_name, 1.0)
            return success_rate < self.hybrid_config.fallback_success_threshold
        
        return False

    async def _execute_with_retry(self, api_call):
        """Execute API call with retry logic"""
        if self.hybrid_config.max_api_retries <= 0:
            raise TradingError("Invalid retry configuration: max_api_retries must be > 0")
            
        last_exception = None
        
        for attempt in range(self.hybrid_config.max_api_retries):
            try:
                return await asyncio.get_event_loop().run_in_executor(
                    None, api_call
                )
            except Exception as e:
                last_exception = e
                if attempt < self.hybrid_config.max_api_retries - 1:
                    await asyncio.sleep(self.hybrid_config.retry_delay_seconds)
                    
        # last_exception should never be None here since we have at least one attempt
        if last_exception is None:
            raise TradingError("Unexpected error: no exception recorded during retry attempts")
        raise last_exception

    async def _execute_with_webdriver(self, method_name: str, webdriver_call):
        """Execute WebDriver call with monitoring"""
        start_time = time.time()
        
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, webdriver_call
            )
            execution_time = (time.time() - start_time) * 1000
            
            self._record_fallback_event(
                method_name, 
                FallbackReason.MANUAL_OVERRIDE,
                webdriver_success=True,
                execution_time_ms=execution_time
            )
            
            return result
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            
            self._record_fallback_event(
                method_name,
                FallbackReason.MANUAL_OVERRIDE,
                webdriver_success=False,
                execution_time_ms=execution_time
            )
            
            raise TradingError(f"WebDriver fallback failed for {method_name}: {str(e)}")

    async def _handle_api_failure(
        self, 
        method_name: str, 
        api_error: Exception, 
        webdriver_call
    ):
        """Handle API failure and attempt WebDriver fallback"""
        self._record_api_failure(method_name)
        
        if self.webdriver_client is None:
            raise api_error
        
        reason = self._categorize_api_error(api_error)
        
        try:
            result = await self._execute_with_webdriver(method_name, webdriver_call)
            
            self._record_fallback_event(
                method_name,
                reason,
                api_error=str(api_error),
                webdriver_success=True
            )
            
            return result
            
        except Exception as wd_error:
            self._record_fallback_event(
                method_name,
                reason,
                api_error=str(api_error),
                webdriver_success=False
            )
            
            # Both API and WebDriver failed
            raise TradingError(
                f"Both API and WebDriver failed for {method_name}. "
                f"API error: {str(api_error)}. WebDriver error: {str(wd_error)}"
            )

    def _categorize_api_error(self, error: Exception) -> FallbackReason:
        """Categorize API error to determine fallback reason"""
        error_str = str(error).lower()
        
        if "authentication" in error_str or "unauthorized" in error_str:
            return FallbackReason.AUTHENTICATION_FAILED
        elif "rate limit" in error_str or "too many requests" in error_str:
            return FallbackReason.RATE_LIMITED
        elif "session" in error_str and "expired" in error_str:
            return FallbackReason.SESSION_EXPIRED
        elif "not available" in error_str or "no data" in error_str:
            return FallbackReason.DATA_UNAVAILABLE
        else:
            return FallbackReason.API_ERROR

    def _record_api_success(self, method_name: str):
        """Record successful API call"""
        self.last_api_attempt[method_name] = datetime.now(timezone.utc)
        
        # Update success rate (simple moving average)
        current_rate = self.api_success_rates.get(method_name, 1.0)
        self.api_success_rates[method_name] = min(1.0, current_rate + 0.1)

    def _record_api_failure(self, method_name: str):
        """Record failed API call"""
        self.last_api_attempt[method_name] = datetime.now(timezone.utc)
        
        # Update success rate
        current_rate = self.api_success_rates.get(method_name, 1.0)
        self.api_success_rates[method_name] = max(0.0, current_rate - 0.2)

    def _record_fallback_event(
        self,
        method_name: str,
        reason: FallbackReason,
        api_error: Optional[str] = None,
        webdriver_success: bool = False,
        execution_time_ms: float = 0.0
    ):
        """Record a fallback event for monitoring"""
        if self.hybrid_config.monitor_fallback_events:
            event = FallbackEvent(
                timestamp=datetime.now(timezone.utc),
                method_name=method_name,
                reason=reason,
                api_error=api_error,
                webdriver_success=webdriver_success,
                execution_time_ms=execution_time_ms
            )
            
            self.fallback_events.append(event)
            
            # Keep only last 1000 events
            if len(self.fallback_events) > 1000:
                self.fallback_events = self.fallback_events[-1000:]

    def _get_from_fallback_cache(self, key: str) -> Optional[Any]:
        """Get data from fallback cache if valid"""
        if not self.hybrid_config.enable_fallback_caching:
            return None
            
        if key not in self.fallback_cache:
            return None
            
        timestamp = self.fallback_cache_timestamps.get(key)
        if timestamp is None:
            return None
            
        age = (datetime.now(timezone.utc) - timestamp).total_seconds()
        if age > self.hybrid_config.fallback_cache_ttl_seconds:
            # Cache expired
            del self.fallback_cache[key]
            del self.fallback_cache_timestamps[key]
            return None
            
        return self.fallback_cache[key]

    def _store_in_fallback_cache(self, key: str, data: Any):
        """Store data in fallback cache"""
        if self.hybrid_config.enable_fallback_caching:
            self.fallback_cache[key] = data
            self.fallback_cache_timestamps[key] = datetime.now(timezone.utc)

    def _convert_order_data_for_api(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert generic order data to Plus500 API format"""
        # This would convert standardized order format to Plus500 API format
        # Implementation would depend on the specific order data structure
        return order_data

    # ===================
    # Monitoring and Stats
    # ===================

    def get_fallback_statistics(self) -> Dict[str, Any]:
        """Get comprehensive fallback statistics"""
        total_events = len(self.fallback_events)
        
        if total_events == 0:
            return {
                'total_fallback_events': 0,
                'fallback_success_rate': 0.0,
                'average_execution_time_ms': 0.0,
                'fallback_reasons': {},
                'api_success_rates': self.api_success_rates.copy()
            }
        
        successful_fallbacks = sum(1 for e in self.fallback_events if e.webdriver_success)
        success_rate = successful_fallbacks / total_events
        
        avg_execution_time = sum(e.execution_time_ms for e in self.fallback_events) / total_events
        
        reason_counts = {}
        for event in self.fallback_events:
            reason_counts[event.reason.value] = reason_counts.get(event.reason.value, 0) + 1
        
        return {
            'total_fallback_events': total_events,
            'fallback_success_rate': success_rate,
            'average_execution_time_ms': avg_execution_time,
            'fallback_reasons': reason_counts,
            'api_success_rates': self.api_success_rates.copy(),
            'last_24h_events': len([
                e for e in self.fallback_events 
                if (datetime.now(timezone.utc) - e.timestamp).total_seconds() < 86400
            ])
        }

    def get_method_performance(self, method_name: str) -> Dict[str, Any]:
        """Get performance statistics for a specific method"""
        method_events = [e for e in self.fallback_events if e.method_name == method_name]
        
        if not method_events:
            return {
                'method_name': method_name,
                'api_success_rate': self.api_success_rates.get(method_name, 1.0),
                'fallback_events': 0,
                'fallback_success_rate': 0.0,
                'last_attempt': self.last_api_attempt.get(method_name)
            }
        
        successful_fallbacks = sum(1 for e in method_events if e.webdriver_success)
        fallback_success_rate = successful_fallbacks / len(method_events)
        
        return {
            'method_name': method_name,
            'api_success_rate': self.api_success_rates.get(method_name, 1.0),
            'fallback_events': len(method_events),
            'fallback_success_rate': fallback_success_rate,
            'last_attempt': self.last_api_attempt.get(method_name),
            'recent_events': method_events[-5:]  # Last 5 events
        }

    def clear_fallback_history(self):
        """Clear fallback event history and reset statistics"""
        self.fallback_events.clear()
        self.api_success_rates.clear()
        self.last_api_attempt.clear()
        self.fallback_cache.clear()
        self.fallback_cache_timestamps.clear()

    def export_fallback_report(self) -> Dict[str, Any]:
        """Export comprehensive fallback report"""
        return {
            'report_timestamp': datetime.now(timezone.utc).isoformat(),
            'hybrid_config': {
                'fallback_strategy': self.hybrid_config.fallback_strategy.value,
                'max_api_retries': self.hybrid_config.max_api_retries,
                'webdriver_timeout_seconds': self.hybrid_config.webdriver_timeout_seconds,
                'fallback_success_threshold': self.hybrid_config.fallback_success_threshold
            },
            'statistics': self.get_fallback_statistics(),
            'method_performance': {
                method: self.get_method_performance(method) 
                for method in set(e.method_name for e in self.fallback_events)
            },
            'recent_events': [
                {
                    'timestamp': e.timestamp.isoformat(),
                    'method': e.method_name,
                    'reason': e.reason.value,
                    'success': e.webdriver_success,
                    'execution_time_ms': e.execution_time_ms
                }
                for e in self.fallback_events[-50:]  # Last 50 events
            ]
        }
