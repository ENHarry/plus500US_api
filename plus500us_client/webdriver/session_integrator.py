from __future__ import annotations
import time
import logging
from typing import Dict, Any, Optional, Union, List
from decimal import Decimal

from .account_manager import WebDriverAccountManager
from .instruments_discovery import WebDriverInstrumentsDiscovery
from .pnl_analyzer import WebDriverPnLAnalyzer
from .trade_manager import WebDriverTradeManager
from .browser_manager import BrowserManager
from ..config import Config
from ..session import SessionManager
from ..account import AccountClient
from ..trading import TradingClient
from ..instruments import InstrumentsClient
from ..models import Account, Instrument, Position
from ..errors import ValidationError, AuthenticationError

logger = logging.getLogger(__name__)

class WebDriverSessionIntegrator:
    """
    Central integration point for WebDriver functionality with existing API clients
    Provides seamless bridging between WebDriver extracted data and API-based operations
    """
    
    def __init__(self, config: Config, session_manager: SessionManager, 
                 browser_manager: Optional[BrowserManager] = None):
        self.config = config
        self.session_manager = session_manager
        self.browser_manager = browser_manager
        self.driver = None
        
        # Initialize API clients
        self.account_client = AccountClient(config, session_manager)
        self.trading_client = TradingClient(config, session_manager)
        self.instruments_client = InstrumentsClient(config, session_manager)
        
        # Initialize WebDriver components
        self.account_manager = WebDriverAccountManager(config, browser_manager, self.account_client)
        self.instruments_discovery = WebDriverInstrumentsDiscovery(config, browser_manager, self.instruments_client)
        self.pnl_analyzer = WebDriverPnLAnalyzer(config, browser_manager)
        self.trade_manager = WebDriverTradeManager(config, self.trading_client, session_manager, browser_manager)
        
        # Integration state
        self._initialized = False
        self._last_sync_time = 0
        self._sync_interval = 30  # Sync every 30 seconds
        
    def initialize(self, driver=None) -> None:
        """Initialize all WebDriver components with shared driver instance"""
        if driver:
            self.driver = driver
        elif self.browser_manager:
            self.driver = self.browser_manager.get_driver()
        else:
            raise RuntimeError("No WebDriver available. Provide driver or browser_manager.")
        
        # Initialize all components with the same driver
        self.account_manager.initialize(self.driver)
        self.instruments_discovery.initialize(self.driver)
        self.pnl_analyzer.initialize(self.driver)
        self.trade_manager.initialize(self.driver)
        
        self._initialized = True
        logger.info("WebDriver session integrator initialized successfully")
    
    def get_enhanced_account_info(self) -> Account:
        """
        Get enhanced account information combining WebDriver and API data
        with automatic fallback mechanisms
        
        Returns:
            Enhanced Account model
        """
        logger.info("Getting enhanced account information with WebDriver integration")
        
        if not self._initialized:
            raise RuntimeError("Session integrator not initialized")
        
        try:
            # Primary: Use WebDriver account manager for enhanced data
            enhanced_account = self.account_manager.get_enhanced_account_info()
            
            # Verify account type consistency
            webdriver_account_type = self.account_manager.detect_current_account_type()
            if enhanced_account.account_type != webdriver_account_type:
                logger.warning(f"Account type mismatch: API={enhanced_account.account_type}, WebDriver={webdriver_account_type}")
                enhanced_account.account_type = webdriver_account_type
            
            logger.info(f"Enhanced account info: {enhanced_account.account_type} account with ${enhanced_account.balance}")
            return enhanced_account
            
        except Exception as e:
            logger.warning(f"WebDriver account enhancement failed: {e}, falling back to API only")
            
            # Fallback: Use API client only
            try:
                api_account = self.account_client.get_account()
                logger.info("Using API-only account data as fallback")
                return api_account
            except Exception as api_error:
                logger.error(f"API account fallback also failed: {api_error}")
                raise ValidationError(f"Both WebDriver and API account retrieval failed: {e}")
    
    def switch_account_type(self, target_type: str) -> bool:
        """
        Switch account type with session state synchronization
        
        Args:
            target_type: 'demo' or 'live'
            
        Returns:
            True if successful
        """
        logger.info(f"Switching to {target_type} account with session integration")
        
        if not self._initialized:
            raise RuntimeError("Session integrator not initialized")
        
        try:
            # Use WebDriver to switch account
            success = self.account_manager.switch_account_type(target_type)
            
            if success:
                # Update config to maintain consistency
                self.config.account_type = target_type
                
                # Force refresh of cached data
                self._last_sync_time = 0
                
                logger.info(f"Successfully switched to {target_type} account")
                return True
            else:
                logger.error(f"Failed to switch to {target_type} account")
                return False
                
        except Exception as e:
            logger.error(f"Account switch failed: {e}")
            return False
    
    def discover_all_instruments(self, force_refresh: bool = False) -> Dict[str, List[Dict[str, Any]]]:
        """
        Discover all instruments with enhanced metadata
        
        Args:
            force_refresh: Force refresh of cached data
            
        Returns:
            Dictionary of instruments by category
        """
        logger.info("Discovering all instruments with enhanced metadata")
        
        if not self._initialized:
            raise RuntimeError("Session integrator not initialized")
        
        try:
            # Use WebDriver discovery for comprehensive data
            webdriver_instruments = self.instruments_discovery.discover_all_instruments_by_category(force_refresh)
            
            # Enhance with API data where possible
            enhanced_instruments = self._enhance_instruments_with_api_data(webdriver_instruments)
            
            logger.info(f"Discovered instruments in {len(enhanced_instruments)} categories")
            return enhanced_instruments
            
        except Exception as e:
            logger.warning(f"WebDriver instruments discovery failed: {e}, falling back to API")
            
            # Fallback: Use API instruments only
            try:
                api_instruments = self.instruments_client.list_instruments()
                
                # Convert to category format
                fallback_instruments = {
                    'All Instruments': [self._instrument_to_dict(inst) for inst in api_instruments]
                }
                
                logger.info("Using API-only instruments data as fallback")
                return fallback_instruments
                
            except Exception as api_error:
                logger.error(f"API instruments fallback also failed: {api_error}")
                return {}
    
    def analyze_daily_pnl(self, target_date=None) -> Dict[str, Any]:
        """
        Analyze daily P&L with comprehensive statistics
        
        Args:
            target_date: Date to analyze (defaults to today)
            
        Returns:
            Comprehensive P&L analysis
        """
        logger.info(f"Analyzing daily P&L for {target_date or 'today'}")
        
        if not self._initialized:
            raise RuntimeError("Session integrator not initialized")
        
        try:
            return self.pnl_analyzer.analyze_daily_pnl(target_date)
        except Exception as e:
            logger.error(f"P&L analysis failed: {e}")
            return {
                'error': str(e),
                'net_pnl': Decimal('0'),
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0
            }
    
    def get_positions_with_enhanced_data(self) -> List[Dict[str, Any]]:
        """
        Get positions with enhanced WebDriver data
        
        Returns:
            List of enhanced position data
        """
        logger.info("Getting positions with enhanced WebDriver data")
        
        if not self._initialized:
            raise RuntimeError("Session integrator not initialized")
        
        try:
            # Get positions from WebDriver
            webdriver_positions = self.trade_manager.extract_current_positions()
            
            # Enhance with API data
            try:
                api_positions = self.trading_client.get_positions()
                enhanced_positions = self._merge_position_data(webdriver_positions, api_positions)
            except Exception as api_error:
                logger.warning(f"API positions retrieval failed: {api_error}, using WebDriver data only")
                enhanced_positions = webdriver_positions
            
            logger.info(f"Retrieved {len(enhanced_positions)} positions with enhanced data")
            return enhanced_positions
            
        except Exception as e:
            logger.error(f"Enhanced positions retrieval failed: {e}")
            
            # Fallback to API only
            try:
                api_positions = self.trading_client.get_positions()
                return [self._position_to_dict(pos) for pos in api_positions]
            except Exception as api_error:
                logger.error(f"API positions fallback failed: {api_error}")
                return []
    
    def update_running_take_profit(self, position_id: str, new_tp_price: Decimal) -> bool:
        """
        Update running take profit with integrated approach
        
        Args:
            position_id: Position identifier
            new_tp_price: New take profit price
            
        Returns:
            True if successful
        """
        logger.info(f"Updating running take profit for {position_id} to ${new_tp_price}")
        
        if not self._initialized:
            raise RuntimeError("Session integrator not initialized")
        
        try:
            return self.trade_manager.update_running_take_profit(position_id, new_tp_price)
        except Exception as e:
            logger.error(f"Running TP update failed: {e}")
            return False
    
    def monitor_and_manage_positions(self, monitoring_rules: Dict[str, Any]) -> None:
        """
        Monitor positions and automatically manage based on rules
        
        Args:
            monitoring_rules: Dictionary of monitoring and management rules
        """
        logger.info("Starting integrated position monitoring and management")
        
        if not self._initialized:
            raise RuntimeError("Session integrator not initialized")
        
        try:
            while True:
                # Get current positions
                positions = self.get_positions_with_enhanced_data()
                
                for position in positions:
                    position_id = position.get('id')
                    
                    # Apply monitoring rules if defined for this position
                    if position_id in monitoring_rules:
                        rules = monitoring_rules[position_id]
                        self._apply_position_rules(position, rules)
                
                # Sync session state periodically
                if time.time() - self._last_sync_time > self._sync_interval:
                    self._sync_session_state()
                
                time.sleep(5)  # Check every 5 seconds
                
        except KeyboardInterrupt:
            logger.info("Position monitoring stopped by user")
        except Exception as e:
            logger.error(f"Position monitoring failed: {e}")
    
    def sync_session_state(self) -> bool:
        """
        Synchronize WebDriver and API session states
        
        Returns:
            True if synchronization successful
        """
        logger.debug("Synchronizing session state between WebDriver and API")
        
        try:
            # Check account type consistency
            webdriver_account_type = self.account_manager.detect_current_account_type()
            config_account_type = self.config.account_type
            
            if webdriver_account_type != config_account_type:
                logger.info(f"Syncing account type: {config_account_type} -> {webdriver_account_type}")
                self.config.account_type = webdriver_account_type
            
            # Update last sync time
            self._last_sync_time = time.time()
            
            return True
            
        except Exception as e:
            logger.warning(f"Session state sync failed: {e}")
            return False
    
    def _enhance_instruments_with_api_data(self, webdriver_instruments: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        """Enhance WebDriver instruments with API metadata"""
        try:
            api_instruments = self.instruments_client.list_instruments()
            api_lookup = {inst.symbol: inst for inst in api_instruments}
            
            enhanced_instruments = {}
            
            for category, instruments in webdriver_instruments.items():
                enhanced_category = []
                
                for wd_instrument in instruments:
                    symbol = wd_instrument.get('symbol', '')
                    
                    # Try to find matching API instrument
                    api_instrument = api_lookup.get(symbol)
                    
                    if api_instrument:
                        # Merge WebDriver and API data
                        enhanced = wd_instrument.copy()
                        enhanced.update({
                            'tick_size': api_instrument.tick_size,
                            'min_qty': api_instrument.min_qty,
                            'currency': api_instrument.currency,
                            'exchange': api_instrument.exchange
                        })
                        enhanced_category.append(enhanced)
                    else:
                        enhanced_category.append(wd_instrument)
                
                enhanced_instruments[category] = enhanced_category
            
            return enhanced_instruments
            
        except Exception as e:
            logger.warning(f"Could not enhance instruments with API data: {e}")
            return webdriver_instruments
    
    def _merge_position_data(self, webdriver_positions: List[Dict[str, Any]], 
                           api_positions: List[Position]) -> List[Dict[str, Any]]:
        """Merge WebDriver and API position data"""
        api_lookup = {pos.instrument_id: pos for pos in api_positions}
        
        enhanced_positions = []
        
        for wd_position in webdriver_positions:
            instrument_id = wd_position.get('instrument_id', '')
            
            # Try to find matching API position
            api_position = api_lookup.get(instrument_id)
            
            if api_position:
                # Merge data, preferring WebDriver for real-time values
                enhanced = wd_position.copy()
                enhanced.update({
                    'api_id': api_position.id,
                    'realized_pnl': api_position.realized_pnl,
                    'margin_used': api_position.margin_used
                })
                enhanced_positions.append(enhanced)
            else:
                enhanced_positions.append(wd_position)
        
        return enhanced_positions
    
    def _apply_position_rules(self, position: Dict[str, Any], rules: Dict[str, Any]) -> None:
        """Apply management rules to a position"""
        try:
            position_id = position.get('id')
            current_pnl = position.get('unrealized_pnl', Decimal('0'))
            
            # Check TP update rules
            tp_rules = rules.get('tp_updates', [])
            for rule in tp_rules:
                trigger_pnl = rule.get('trigger_pnl')
                new_tp_price = rule.get('new_tp_price')
                applied = rule.get('applied', False)
                
                if not applied and current_pnl >= trigger_pnl:
                    success = self.update_running_take_profit(position_id, new_tp_price)
                    if success:
                        rule['applied'] = True
                        logger.info(f"Applied TP rule for position {position_id}: ${trigger_pnl} -> ${new_tp_price}")
            
            # Add other rule types here (SL updates, partial closes, etc.)
            
        except Exception as e:
            logger.warning(f"Failed to apply rules to position {position.get('id')}: {e}")
    
    def _sync_session_state(self) -> None:
        """Internal method to sync session state"""
        self.sync_session_state()
    
    def _instrument_to_dict(self, instrument: Instrument) -> Dict[str, Any]:
        """Convert Instrument model to dictionary"""
        return {
            'id': instrument.id,
            'symbol': instrument.symbol,
            'name': instrument.name,
            'tick_size': instrument.tick_size,
            'min_qty': instrument.min_qty,
            'currency': instrument.currency,
            'exchange': instrument.exchange
        }
    
    def _position_to_dict(self, position: Position) -> Dict[str, Any]:
        """Convert Position model to dictionary"""
        return {
            'id': position.id,
            'instrument_id': position.instrument_id,
            'side': position.side,
            'quantity': position.qty,
            'avg_price': position.avg_price,
            'unrealized_pnl': position.unrealized_pnl,
            'realized_pnl': position.realized_pnl,
            'margin_used': position.margin_used,
            'timestamp': time.time()
        }
    
    def get_driver(self):
        """Get the WebDriver instance"""
        return self.driver