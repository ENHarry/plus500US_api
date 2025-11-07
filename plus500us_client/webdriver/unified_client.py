"""
Unified WebDriver Client Interface
Provides a single entry point for all WebDriver-based operations
"""
from __future__ import annotations
import logging
from typing import Optional, Dict, Any, List
from decimal import Decimal

from .browser_manager import BrowserManager
from .auth_handler import WebDriverAuthHandler
from .trading_automation import WebDriverTradingClient
from .account_manager import WebDriverAccountManager
from .instruments_discovery import WebDriverInstrumentsDiscovery
from .pnl_analyzer import WebDriverPnLAnalyzer
from .trade_manager import WebDriverTradeManager
from .session_integrator import WebDriverSessionIntegrator
from ..config import Config
from ..models import Order, Position, Instrument
from ..errors import (
    ClientError, AuthenticationError, ValidationError, 
    CaptchaRequiredError, AutomationBlockedError
)

logger = logging.getLogger(__name__)

class UnifiedWebDriverClient:
    """
    Unified WebDriver client providing a single entry point for all WebDriver operations
    
    This class orchestrates all WebDriver-based modules and provides a clean,
    consistent interface for trading automation, account management, and market data.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the unified WebDriver client
        
        Args:
            config: Configuration object (will load default if None)
        """
        self.config = config or Config()
        self.browser_manager: Optional[BrowserManager] = None
        self.driver = None
        
        # Component instances (initialized lazily)
        self._auth_handler: Optional[WebDriverAuthHandler] = None
        self._trading_client: Optional[WebDriverTradingClient] = None
        self._account_manager: Optional[WebDriverAccountManager] = None
        self._instruments_discovery: Optional[WebDriverInstrumentsDiscovery] = None
        self._pnl_analyzer: Optional[WebDriverPnLAnalyzer] = None
        self._trade_manager: Optional[WebDriverTradeManager] = None
        self._session_integrator: Optional[WebDriverSessionIntegrator] = None
        
        self._is_authenticated = False
        self._session_active = False
        
        logger.info("Unified WebDriver client initialized")
    
    # ========== Browser Management ==========
    
    def start_browser(self, headless: Optional[bool] = None) -> None:
        """
        Start the browser with configured settings
        
        Args:
            headless: Override headless mode setting
        """
        if headless is not None:
            self.config.webdriver_config['headless'] = headless
            
        self.browser_manager = BrowserManager(self.config)
        self.driver = self.browser_manager.start_browser()
        logger.info("Browser started successfully")
    
    def close_browser(self) -> None:
        """Close the browser and cleanup resources"""
        if self.browser_manager:
            self.browser_manager.stop_browser()
            self.browser_manager = None
            self.driver = None
            self._session_active = False
            logger.info("Browser closed and resources cleaned up")
    
    def restart_browser(self) -> None:
        """Restart the browser (useful for clearing state)"""
        self.close_browser()
        self.start_browser()
        logger.info("Browser restarted")
    
    def is_browser_active(self) -> bool:
        """Check if browser is currently active and responsive"""
        return (self.browser_manager is not None and 
                self.browser_manager.is_browser_alive())
    
    # ========== Authentication ==========
    
    @property
    def auth_handler(self) -> WebDriverAuthHandler:
        """Lazy-loaded authentication handler"""
        if self._auth_handler is None:
            if not self.browser_manager:
                raise ClientError("Browser must be started before authentication")
            self._auth_handler = WebDriverAuthHandler(self.config, self.browser_manager)
        return self._auth_handler
    
    def login(self, email: Optional[str] = None, password: Optional[str] = None,
              interactive: bool = False) -> Dict[str, Any]:
        """
        Authenticate user with Plus500
        
        Args:
            email: User email (uses config if None)
            password: User password (uses config if None)
            interactive: Use interactive login mode
            
        Returns:
            Authentication result with cookies and session info
        """
        if not self.is_browser_active():
            self.start_browser()
        
        try:
            if interactive:
                result = self.auth_handler.interactive_login()
            else:
                result = self.auth_handler.login(
                    email or self.config.email,
                    password or self.config.password
                )
            
            if result.get('success'):
                self._is_authenticated = True
                self._session_active = True
                logger.info("Authentication successful")
            else:
                logger.error("Authentication failed")
                
            return result
            
        except CaptchaRequiredError:
            logger.warning("Captcha required - switching to interactive mode")
            return self.login(email, password, interactive=True)
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise AuthenticationError(f"Login failed: {e}")
    
    def logout(self) -> bool:
        """Logout from Plus500"""
        if self._auth_handler:
            success = self._auth_handler.logout()
            if success:
                self._is_authenticated = False
                self._session_active = False
            return success
        return True
    
    @property
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated"""
        return self._is_authenticated and self._session_active
    
    # ========== Trading Operations ==========
    
    @property
    def trading_client(self) -> WebDriverTradingClient:
        """Lazy-loaded trading client"""
        if self._trading_client is None:
            if not self.is_authenticated:
                raise AuthenticationError("Must be authenticated for trading operations")
            self._trading_client = WebDriverTradingClient(self.config, self.browser_manager)
            self._trading_client.initialize(self.driver)
        return self._trading_client
    
    def place_market_order(self, instrument_id: str, side: str, quantity: Decimal,
                          stop_loss: Optional[Decimal] = None,
                          take_profit: Optional[Decimal] = None,
                          **kwargs) -> Dict[str, Any]:
        """
        Place a market order
        
        Args:
            instrument_id: Instrument identifier
            side: "BUY" or "SELL"
            quantity: Order quantity
            stop_loss: Optional stop loss price
            take_profit: Optional take profit price
            **kwargs: Additional order parameters
            
        Returns:
            Order placement result
        """
        return self.trading_client.place_market_order(
            instrument_id, side, quantity, stop_loss, take_profit, **kwargs
        )
    
    def place_limit_order(self, instrument_id: str, side: str, quantity: Decimal,
                         limit_price: Decimal, **kwargs) -> Dict[str, Any]:
        """
        Place a limit order
        
        Args:
            instrument_id: Instrument identifier
            side: "BUY" or "SELL"  
            quantity: Order quantity
            limit_price: Limit price
            **kwargs: Additional order parameters
            
        Returns:
            Order placement result
        """
        return self.trading_client.place_limit_order(
            instrument_id, side, quantity, limit_price, **kwargs
        )
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order"""
        return self.trading_client.cancel_order(order_id)
    
    def modify_order(self, order_id: str, **modifications) -> bool:
        """Modify an existing order"""
        return self.trading_client.modify_order(order_id, **modifications)
    
    # ========== Position Management ==========
    
    def get_positions(self, include_closed: bool = False) -> List[Position]:
        """Get current positions"""
        return self.trading_client.get_positions(include_closed)
    
    def close_position(self, position_id: str, quantity: Optional[Decimal] = None) -> bool:
        """Close a position (partially or fully)"""
        return self.trading_client.close_position(position_id, quantity)
    
    def modify_position(self, position_id: str, **modifications) -> bool:
        """Modify position parameters (stop loss, take profit, etc.)"""
        return self.trading_client.modify_position(position_id, **modifications)
    
    # ========== Account Information ==========
    
    @property
    def account_manager(self) -> WebDriverAccountManager:
        """Lazy-loaded account manager"""
        if self._account_manager is None:
            if not self.is_authenticated:
                raise AuthenticationError("Must be authenticated for account operations")
            self._account_manager = WebDriverAccountManager(self.config, self.browser_manager)
            self._account_manager.initialize(self.driver)
        return self._account_manager
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        return self.account_manager.get_account_info()
    
    def get_balance(self) -> Dict[str, Decimal]:
        """Get account balance information"""
        return self.account_manager.get_balance()
    
    def get_margin_info(self) -> Dict[str, Any]:
        """Get margin information"""
        return self.account_manager.get_margin_info()
    
    # ========== Market Data ==========
    
    @property
    def instruments_discovery(self) -> WebDriverInstrumentsDiscovery:
        """Lazy-loaded instruments discovery"""
        if self._instruments_discovery is None:
            if not self.is_browser_active():
                self.start_browser()
            self._instruments_discovery = WebDriverInstrumentsDiscovery(self.config, self.browser_manager)
            self._instruments_discovery.initialize(self.driver)
        return self._instruments_discovery
    
    def search_instruments(self, query: str) -> List[Instrument]:
        """Search for instruments"""
        return self.instruments_discovery.search_instruments(query)
    
    def get_instrument_details(self, instrument_id: str) -> Optional[Instrument]:
        """Get detailed instrument information"""
        return self.instruments_discovery.get_instrument_details(instrument_id)
    
    def get_popular_instruments(self) -> List[Instrument]:
        """Get list of popular instruments"""
        return self.instruments_discovery.get_popular_instruments()
    
    # ========== P&L Analysis ==========
    
    @property
    def pnl_analyzer(self) -> WebDriverPnLAnalyzer:
        """Lazy-loaded P&L analyzer"""
        if self._pnl_analyzer is None:
            if not self.is_authenticated:
                raise AuthenticationError("Must be authenticated for P&L analysis")
            self._pnl_analyzer = WebDriverPnLAnalyzer(self.config, self.browser_manager)
            self._pnl_analyzer.initialize(self.driver)
        return self._pnl_analyzer
    
    def get_pnl_summary(self) -> Dict[str, Any]:
        """Get P&L summary"""
        return self.pnl_analyzer.get_pnl_summary()
    
    def get_position_pnl(self, position_id: str) -> Dict[str, Any]:
        """Get P&L for specific position"""
        return self.pnl_analyzer.get_position_pnl(position_id)
    
    # ========== Session Management ==========
    
    @property
    def session_integrator(self) -> WebDriverSessionIntegrator:
        """Lazy-loaded session integrator"""
        if self._session_integrator is None:
            self._session_integrator = WebDriverSessionIntegrator(self.config, self.browser_manager)
        return self._session_integrator
    
    def export_session(self) -> Dict[str, Any]:
        """Export current session for use with requests-based methods"""
        if not self.is_authenticated:
            raise AuthenticationError("Must be authenticated to export session")
        return self.session_integrator.export_session()
    
    def import_session(self, session_data: Dict[str, Any]) -> bool:
        """Import session data into WebDriver"""
        success = self.session_integrator.import_session(session_data)
        if success:
            self._is_authenticated = True
            self._session_active = True
        return success
    
    # ========== Utility Methods ==========
    
    def take_screenshot(self, filename: Optional[str] = None) -> str:
        """Take a screenshot for debugging"""
        if self.browser_manager:
            return self.browser_manager.take_screenshot(filename)
        raise ClientError("Browser not active")
    
    def get_browser_info(self) -> Dict[str, Any]:
        """Get browser information"""
        if self.browser_manager:
            return self.browser_manager.get_browser_info()
        return {"status": "inactive"}
    
    def simulate_human_behavior(self) -> None:
        """Simulate human-like behavior"""
        if self.browser_manager:
            self.browser_manager.simulate_human_behavior()
    
    # ========== Context Manager Support ==========
    
    def __enter__(self):
        """Context manager entry"""
        if not self.is_browser_active():
            self.start_browser()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        self.close_browser()
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.close_browser()
        except:
            pass  # Ignore cleanup errors during destruction
