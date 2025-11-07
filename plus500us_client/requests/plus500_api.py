"""
Plus500 API Client - Comprehensive Wrapper

This module provides a unified API client that wraps all the individual
client modules and provides a single interface for all Plus500 API operations.
"""

from __future__ import annotations
import warnings
from typing import List, Optional, Dict, Any, Union, Type, TypeVar
from decimal import Decimal
from datetime import datetime

from .config import Config
from .auth import AuthClient
from .account import AccountClient
from .post_login import PostLoginDataService
from .session import SessionManager
from .trading import TradingClient
from .trading_api import Plus500TradingAPI
from .instruments import InstrumentsClient
from .marketdata import MarketDataClient
from .risk_management import RiskManagementService
from .risk_manager import AdvancedRiskManager
from .trading_utils import AdvancedTradingUtils
from .security import SecureCredentialHandler, SecurityAuditor
from .models import *
from .errors import TradingError, AuthenticationError, ValidationError


class Plus500ApiClient:
    """
    Comprehensive API client that provides a unified interface to all
    Plus500 API functionality through the requests-based modules.
    
    This client wraps all individual client modules and provides both
    legacy compatibility and enhanced functionality.
    """
    
    def __init__(self):
        """
        Initialize the comprehensive Plus500 API client
        
        Args:
            cfg: Configuration object
            sm: Session manager with authenticated session
        """
        self.cfg = Config()
        self.sm = SessionManager(self.cfg)
        
        # Core client modules
        self.auth_client = AuthClient(self.cfg, self.sm)
        self.account_client = AccountClient(self.cfg, self.sm)
        self.postlogin_client = PostLoginDataService(self.cfg, self.sm)
        self.trading_client = TradingClient(self.cfg, self.sm)
        self.trading_api = Plus500TradingAPI(self.cfg, self.sm)
        self.instruments_client = InstrumentsClient(self.cfg, self.sm)
        self.marketdata_client = MarketDataClient(self.cfg, self.sm)

        # Enhanced components
        self.risk_manager = RiskManagementService(self.cfg, self.sm, self.trading_client)
        self.advanced_risk_manager = AdvancedRiskManager(self.cfg, self.sm)
        self.trading_utils = AdvancedTradingUtils(self.cfg, self.sm)
        self.security_handler = SecureCredentialHandler()
        self.security_auditor = SecurityAuditor()

    # ===================
    # Authentication Methods
    # ===================

    def authenticate(self, username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
        """Authenticate with Plus500"""
        # Use config defaults if not provided
        email_val = username or self.cfg.email
        password_val = password or self.cfg.password
        return self.auth_client.plus500_authenticate(email_val, password_val)

    def futures_authenticate(self, username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
        """Authenticate with Plus500 Futures"""
        # Use config defaults if not provided
        email_val = username or self.cfg.email
        password_val = password or self.cfg.password
        
        if not email_val or not password_val:
            raise ValueError("Username and password must be provided (either as parameters or in config)")
        
        return self.auth_client.futures_authenticate(email_val, password_val)
    
    def is_authenticated(self) -> bool:
        """Check if session is authenticated"""
        return self.sm.has_valid_plus500_session()
    
    def logout(self) -> None:
        """Logout and clear session"""
        self.auth_client.logout()

    # ===================
    # Account Management
    # ===================
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        return self.account_client.get_plus500_account_summary()
    
    def get_account_summary(self) -> Dict[str, Any]:
        """Legacy alias for get_account_info"""
        return self.get_account_info()
    
    def get_account_balance(self) -> Dict[str, Any]:
        """Get account balance information"""
        return self.account_client.get_account_balance_summary()
    
    def switch_to_demo(self) -> Dict[str, Any]:
        """Switch to demo account"""
        return self.account_client.switch_account_mode('demo')
    
    def switch_to_real(self) -> Dict[str, Any]:
        """Switch to real account"""
        return self.account_client.switch_account_mode('real')
    
    def switch_account_mode(self, mode: str) -> Dict[str, Any]:
        """Switch account mode (demo/real)"""
        return self.account_client.switch_account_mode(mode)
    
    def get_funds_info(self) -> Dict[str, Any]:
        """Get funds information"""
        return self.trading_api.get_funds_management_info()
    
    def edit_demo_funds(self, amount: Decimal) -> Dict[str, Any]:
        """Edit demo account funds"""
        return self.trading_api.get_demo_edit_funds()

    # ===================
    # Trading Operations
    # ===================
    
    def create_order(self, instrument_id: str, amount: float, direction: str,
                    order_type: str = "Market", **kwargs) -> Dict[str, Any]:
        """Create a trading order"""
        return self.trading_api.create_futures_order(
            instrument_id, amount, direction, order_type, **kwargs
        )
    
    def place_order(self, instrument_id: str, amount: float, operation_type: str,
                   order_type: str = "Market", limit_price: Optional[float] = None,
                   stop_price: Optional[float] = None) -> Dict[str, Any]:
        """Place order with Plus500 API"""
        from decimal import Decimal
        return self.trading_client.create_plus500_order(
            instrument_id=instrument_id,
            amount=Decimal(str(amount)), 
            operation_type=operation_type,
            order_type=order_type,
            limit_price=Decimal(str(limit_price)) if limit_price else None,
            stop_price=Decimal(str(stop_price)) if stop_price else None
        )
    
    def place_market_order(self, symbol: str, amount: float, direction: str,
                          stop_loss: Optional[float] = None,
                          take_profit: Optional[float] = None) -> Dict[str, Any]:
        """Place a market order"""
        return self.trading_api.place_market_order(
            symbol, amount, direction, stop_loss, take_profit
        )
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an order"""
        return self.trading_client.cancel_plus500_order(order_id)
    
    def close_position(self, position_id: str, amount: Optional[Decimal] = None) -> Dict[str, Any]:
        """Close a position"""
        return self.trading_client.close_plus500_position(position_id, amount)
    
    def close_instrument(self, instrument_id: str) -> Dict[str, Any]:
        """Close all positions for an instrument"""
        # This would need to be implemented in the trading client
        return {"message": "close_instrument not yet implemented"}

    # ===================
    # Position Management
    # ===================
    
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get open positions"""
        return self.trading_client.get_plus500_open_positions()
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Legacy alias for get_open_positions"""
        return self.get_open_positions()
    
    def get_closed_positions(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get closed positions"""
        return self.trading_client.get_plus500_closed_positions(limit, offset)
    
    def get_position_history(self, from_date: Optional[datetime] = None,
                           to_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get position history"""
        return self.get_closed_positions(50, 0)  # Enhanced with date filtering could be added

    # ===================
    # Order Management
    # ===================
    
    def get_orders(self) -> List[Dict[str, Any]]:
        """Get pending orders"""
        # Note: Pending orders endpoint not implemented in current API
        return []
    
    def get_pending_orders(self) -> List[Dict[str, Any]]:
        """Get pending orders"""
        return self.get_orders()
    
    def get_order_history(self) -> List[Dict[str, Any]]:
        """Get order history"""
        return self.get_closed_positions()  # Orders are part of closed positions

    # ===================
    # Instrument Operations
    # ===================
    
    def get_instruments(self, product_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get available instruments"""
        instruments = self.instruments_client.get_plus500_instruments()
        # Convert to dictionaries for API compatibility
        return [instr.model_dump() if hasattr(instr, 'model_dump') else instr.__dict__ for instr in instruments]
    
    def get_trade_instruments(self, product_type: Optional[str] = None) -> Dict[str, Any]:
        """Get trade instruments from API"""
        return self.trading_api.get_trade_instruments(product_type)
    
    def get_instrument_details(self, instrument_id: str) -> Dict[str, Any]:
        """Get detailed instrument information"""
        return self.trading_api.get_futures_instrument_details(instrument_id)
    
    def get_instrument_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get instrument by symbol"""
        instruments = self.get_instruments()
        for instrument in instruments:
            if instrument.get('symbol', '').upper() == symbol.upper():
                return instrument
        return None
    
    def search_instruments(self, query: str) -> List[Dict[str, Any]]:
        """Search instruments by name or symbol"""
        instruments = self.instruments_client.search_plus500_instruments(query)
        return [instr.model_dump() if hasattr(instr, 'model_dump') else instr.__dict__ for instr in instruments]

    # ===================
    # Market Data
    # ===================
    
    def get_market_data(self, instrument_id: str) -> Dict[str, Any]:
        """Get market data for instrument"""
        prices = self.marketdata_client.get_plus500_instrument_prices([instrument_id])
        if prices:
            return prices[0].model_dump() if hasattr(prices[0], 'model_dump') else prices[0].__dict__
        return {}
    
    def get_instrument_prices(self, instrument_ids: List[str]) -> List[Dict[str, Any]]:
        """Get prices for multiple instruments"""
        prices = self.marketdata_client.get_plus500_instrument_prices(instrument_ids)
        return [price.model_dump() if hasattr(price, 'model_dump') else price.__dict__ for price in prices]
    
    def get_buy_sell_info(self, instrument_id: str, amount: float) -> Dict[str, Any]:
        """Get buy/sell information for instrument"""
        return self.trading_api.get_futures_buy_sell_info(instrument_id, amount)
    
    def get_chart_data(self, instrument_id: str, timeframe: str = "1H",
                      from_date: Optional[datetime] = None,
                      to_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get chart data for instrument"""
        return self.trading_api.get_chart_data(instrument_id, timeframe, from_date, to_date)

    # ===================
    # Risk Management
    # ===================
    
    def add_risk_management(self, instrument_id: str, stop_loss: Optional[float] = None,
                          take_profit: Optional[float] = None) -> Dict[str, Any]:
        """Add risk management to position"""
        return self.trading_api.add_risk_management_to_instrument(
            instrument_id, stop_loss, take_profit
        )
    
    def calculate_position_size(self, instrument_id: str, risk_amount: Decimal,
                              stop_loss_distance: Decimal) -> Decimal:
        """Calculate optimal position size"""
        # Placeholder implementation
        return risk_amount / stop_loss_distance
    
    def validate_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate order before placing"""
        # Placeholder implementation
        return {"valid": True, "order": order_data}

    # ===================
    # Post-Login Operations
    # ===================
    
    def get_post_login_info(self) -> Dict[str, Any]:
        """Get post-login information"""
        return self.trading_api.get_post_login_info()
    
    def process_post_login_data(self) -> Dict[str, Any]:
        """Process post-login data"""
        # Placeholder implementation
        return {"status": "post_login_processing_not_implemented"}

    # ===================
    # Advanced Features
    # ===================
    
    def get_trading_signals(self, instrument_id: str) -> Dict[str, Any]:
        """Get trading signals for instrument"""
        # Placeholder implementation
        return {"signals": "trading_signals_not_implemented"}
    
    def optimize_portfolio(self) -> Dict[str, Any]:
        """Optimize current portfolio"""
        # Placeholder implementation
        return {"optimization": "portfolio_optimization_not_implemented"}
    
    def audit_security(self) -> Dict[str, Any]:
        """Perform security audit"""
        # Placeholder implementation
        return {"audit": "security_audit_not_implemented"}

    # ===================
    # Utility Methods
    # ===================
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on all components"""
        return {
            'session_active': self.sm.has_valid_plus500_session(),
            'auth_status': self.is_authenticated(),
            'account_accessible': bool(self.get_account_info()),
            'instruments_available': len(self.get_instruments()) > 0,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_api_status(self) -> Dict[str, Any]:
        """Get API status information"""
        return {
            'authenticated': self.is_authenticated(),
            'session_manager': str(type(self.sm).__name__),
            'config': {
                'base_url': self.cfg.base_url,
                'host_url': self.cfg.host_url,
                'account_type': self.cfg.account_type
            }
        }

    # ===================
    # Legacy Compatibility
    # ===================
    
    def futures_create_order(self, *args, **kwargs) -> Dict[str, Any]:
        """Legacy alias for create_order"""
        return self.create_order(*args, **kwargs)
    
    def futures_close_instrument(self, instrument_id: str) -> Dict[str, Any]:
        """Legacy alias for close_instrument"""
        return self.close_instrument(instrument_id)
    
    def futures_get_closed_positions(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Legacy alias for get_closed_positions"""
        return self.get_closed_positions(limit, offset)
    
    def futures_buy_sell_info(self, instrument_id: str, amount: Decimal) -> Dict[str, Any]:
        """Legacy alias for get_buy_sell_info"""
        return self.get_buy_sell_info(instrument_id, float(amount))

    # ===================
    # Context Manager Support
    # ===================
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.is_authenticated():
            self.logout()
        return False
