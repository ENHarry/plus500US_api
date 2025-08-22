from __future__ import annotations
import time
import logging
import re
from decimal import Decimal
from typing import Dict, Any, Optional, List
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .browser_manager import BrowserManager
from .element_detector import ElementDetector
from .selectors import Plus500Selectors
from .utils import WebDriverUtils
from ..config import Config
from ..account import AccountClient
from ..models import Account
from ..errors import ValidationError, AuthenticationError

logger = logging.getLogger(__name__)

class WebDriverAccountManager:
    """Enhanced account management with WebDriver for Plus500US platform"""
    
    def __init__(self, config: Config, browser_manager: Optional[BrowserManager] = None, 
                 account_client: Optional[AccountClient] = None):
        self.config = config
        self.browser_manager = browser_manager
        self.account_client = account_client
        self.driver = None
        self.element_detector: Optional[ElementDetector] = None
        self.selectors = Plus500Selectors()
        self.utils = WebDriverUtils()
        
    def initialize(self, driver=None) -> None:
        """Initialize with WebDriver instance"""
        if driver:
            self.driver = driver
        elif self.browser_manager:
            self.driver = self.browser_manager.get_driver()
        else:
            raise RuntimeError("No WebDriver available. Provide driver or browser_manager.")
        
        self.element_detector = ElementDetector(self.driver)
        logger.info("WebDriver account manager initialized")
    
    def detect_current_account_type(self) -> str:
        """
        Detect current account type (demo/live) from the account switch control
        
        Returns:
            'demo' or 'live' based on active account type
        """
        logger.info("Detecting current account type from WebDriver")
        print("Detecting current account type...")
        try:
            # Find the account switch control
            switch_control = self.element_detector.find_element_robust(
                self.selectors.ACCOUNT_SWITCH_CONTROL, timeout=2
            )
            
            if switch_control:
                print(f"Found account switch control: {switch_control}")
                # Fallback: check if switch control has specific classes
                control_classes = switch_control.get_attribute('class') or ''
                if 'demo' in control_classes.lower():
                    return 'demo'
                elif 'real' in control_classes.lower() or 'live' in control_classes.lower():
                    return 'live'
            else:
                print("Account switch control not found")
                print("Trying alternative detection methods...")
                # Find the active span element
                active_span = self.element_detector.find_element_robust(
                    self.selectors.ACTIVE_ACCOUNT_TYPE, timeout=2
                )
            
                if active_span:
                    active_text = self.element_detector.extract_text_safe(active_span).lower()
                    logger.debug(f"Active account span text: {active_text}")
                    
                    if 'demo' in active_text:
                        logger.info("Detected Demo account as active")
                        return 'demo'
                    elif 'real' in active_text or 'live' in active_text:
                        logger.info("Detected Live/Real account as active")
                        return 'live'
                else:
                    print("Active account span not found")

            # Ultimate fallback
            logger.warning("Could not determine account type from WebDriver, using config default")
            return self.config.account_type
            
        except Exception as e:
            logger.error(f"Failed to detect account type: {e}")
            return self.config.account_type
    
    def switch_account_type(self, target_type: str) -> bool:
        """
        Switch between demo and live accounts
        
        Args:
            target_type: 'demo' or 'live'
            
        Returns:
            True if switch was successful
        """
        target_type = target_type.lower()
        if target_type not in ['demo', 'live']:
            raise ValidationError(f"Invalid account type: {target_type}. Must be 'demo' or 'live'")
        
        logger.info(f"Switching to {target_type} account")
        
        try:
            # Check current account type
            current_type = self.detect_current_account_type()
            if current_type == target_type:
                logger.info(f"Already on {target_type} account")
                return True
            
            # Find the appropriate span to click
            if target_type == 'demo':
                target_span = self.element_detector.find_element_robust(
                    self.selectors.DEMO_MODE_SPAN, timeout=1
                )
            else:
                target_span = self.element_detector.find_element_robust(
                    self.selectors.REAL_MODE_SPAN, timeout=1
                )
            
            if not target_span:
                raise ValidationError(f"Could not find {target_type} account switch button")
            
            # Click the target span
            self.utils.human_like_click(self.driver, target_span)
            
            # Brief wait for switch to initiate
            time.sleep(0.05)
            
            # Verify the switch was successful
            new_type = self.detect_current_account_type()
            if new_type == target_type:
                logger.info(f"Successfully switched to {target_type} account")
                
                # Update config to reflect the change
                self.config.account_type = target_type
                return True
            else:
                logger.error(f"Account switch failed. Expected {target_type}, got {new_type}")
                return False
                
        except Exception as e:
            logger.error(f"Account switch failed: {e}")
            return False
    
    def switch_account_mode(self, target_mode: str) -> bool:
        """
        Switch between demo and live account modes
        
        Args:
            target_mode: 'demo' or 'live'
            
        Returns:
            True if switch was successful
        """
        if not self.driver:
            raise RuntimeError("Browser not started")
            
        target_mode = target_mode.lower()
        if target_mode not in ['demo', 'live']:
            raise ValueError("target_mode must be 'demo' or 'live'")
            
        try:
            from .selectors import Plus500Selectors
            from .element_detector import ElementDetector
            from .utils import WebDriverUtils
            
            selectors = Plus500Selectors()
            element_detector = ElementDetector(self.driver)
            utils = WebDriverUtils()
            
            # Check current account mode with timeout optimization
            start_time = time.time()
            current_mode = self.get_current_account_mode()
            detection_time = time.time() - start_time
            
            if current_mode == target_mode:
                logger.info(f"Already in {target_mode} mode (detected in {detection_time:.2f}s)")
                return True
            
            logger.info(f"Switching from {current_mode} to {target_mode} mode (detection took {detection_time:.2f}s)")
            
            # Find account switch control with optimization
            switch_control = element_detector.find_element_from_selector(
                selectors.ACCOUNT_SWITCH_CONTROL, timeout=2, first_match_only=True
            )
            
            if not switch_control:
                logger.error("Could not find account switch control")
                return False
            
            # Click the switch control with optimized timing
            click_start = time.time()
            utils.human_like_click(self.driver, switch_control)
            
            # Use smart waiting instead of fixed sleep
            success = self._wait_for_account_mode_change(target_mode, timeout=5)
            total_time = time.time() - click_start
            
            if success:
                logger.info(f"Successfully switched to {target_mode} mode in {total_time:.2f}s")
                return True
            else:
    
                logger.error(f"Account switch failed. Current mode: {current_mode}, Target: {target_mode}")
                logger.info('Using Account Span for switching accounts')
                
                # Use proper element detector for finding account spans with optimization
                live_element = element_detector.find_element_from_selector(
                    selectors.REAL_MODE_SPAN, timeout=2, first_match_only=True
                )
                demo_element = element_detector.find_element_from_selector(
                    selectors.DEMO_MODE_SPAN, timeout=2, first_match_only=True
                )
                # Try direct element clicking approach
                if target_mode == 'live' and live_element:
                    logger.info("Attempting to switch to live mode via direct element click")
                    try:
                        # Try standardized class manipulation for live mode
                        if demo_element:
                            try:
                                # Remove active class from demo element
                                self.driver.execute_script("arguments[0].classList.remove('active');", demo_element)
                                # Add active class to live element  
                                self.driver.execute_script("arguments[0].classList.add('active');", live_element)
                                
                                # Click the live element
                                utils.human_like_click(self.driver, live_element)

                            except Exception as e:
                                logger.debug(f"Standardized class manipulation failed: {e}")
                        
                       
                        # Smart wait for change
                        if self._wait_for_account_mode_change(target_mode, timeout=3):
                            logger.info(f"✅Successfully switched to {target_mode} mode via direct click")
                            return True
                            
                    except Exception as e:
                        logger.error(f"Failed to switch to live mode via direct click: {e}")
                        
                elif target_mode == 'demo' and demo_element:
                    logger.info("Attempting to switch to demo mode via direct element click")
                    try:
                        # Try standardized class manipulation for demo mode
                        if live_element:
                            try:
                                # Remove active class from live element
                                self.driver.execute_script("arguments[0].classList.remove('active');", live_element)
                                # Add active class to demo element
                                self.driver.execute_script("arguments[0].classList.add('active');", demo_element)
                                # Click the demo element
                                utils.human_like_click(self.driver, demo_element)
                            except Exception as e:
                                logger.debug(f"Standardized class manipulation failed: {e}")
                        
                        
                        # Smart wait for change
                        if self._wait_for_account_mode_change(target_mode, timeout=2):
                            logger.info(f"✅Successfully switched to {target_mode} mode via direct click")
                            print(f"✅Successfully switched to {target_mode} mode via direct click")
                            return True
                            
                    except Exception as e:
                        logger.error(f"Failed to switch to demo mode via direct click: {e}")
                
                # If direct approach failed, try alternative selector strategies
                logger.warning(f"Direct element click failed, trying alternative methods for {target_mode} mode")
                return self._try_alternative_account_switch(target_mode, element_detector, utils)

        except Exception as e:
            logger.error(f"Failed to switch account mode: {e}")
            return False
    
    def _try_alternative_account_switch(self, target_mode: str, element_detector, utils) -> bool:
        """
        Try alternative methods for account switching when primary method fails
        
        Args:
            target_mode: 'demo' or 'live'
            element_detector: ElementDetector instance
            utils: WebDriverUtils instance
            
        Returns:
            True if switch was successful
        """
        logger.info(f"Trying alternative account switch methods for {target_mode} mode")
        
        try:
            # Method 1: Look for clickable text elements
            text_patterns = [
                f"//span[contains(text(), '{target_mode.title()}')]",
                f"//div[contains(text(), '{target_mode.title()}')]",
                f"//a[contains(text(), '{target_mode.title()}')]",
                f"//button[contains(text(), '{target_mode.title()}')]"
            ]
            
            for pattern in text_patterns:
                try:
                    elements = self.driver.find_elements(By.XPATH, pattern)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            logger.debug(f"Trying to click element with pattern: {pattern}")
                            utils.human_like_click(self.driver, element)
                            
                            # Quick check with shorter timeout for alternatives
                            if self._wait_for_account_mode_change(target_mode, timeout=2):
                                logger.info(f"✅Alternative method successful: switched to {target_mode}")
                                return True
                except Exception as e:
                    logger.debug(f"Pattern {pattern} failed: {e}")
                    continue
            
            # Method 2: Try keyboard navigation if available
            try:
                from selenium.webdriver.common.keys import Keys
                
                # Try Tab + Enter approach
                current_element = self.driver.switch_to.active_element
                current_element.send_keys(Keys.TAB)
                time.sleep(0.5)
                current_element = self.driver.switch_to.active_element
                current_element.send_keys(Keys.ENTER)
                
                # Quick keyboard navigation check
                if self._wait_for_account_mode_change(target_mode, timeout=2):
                    logger.info(f"✅Keyboard navigation successful: switched to {target_mode}")
                    return True
                    
            except Exception as e:
                logger.debug(f"Keyboard navigation failed: {e}")
            
            logger.warning(f"All alternative account switch methods failed for {target_mode} mode")
            return False
            
        except Exception as e:
            logger.error(f"Alternative account switch methods failed: {e}")
            return False
    
    def _wait_for_account_mode_change(self, expected_mode: str, timeout: float = 5.0) -> bool:
        """
        Smart waiting for account mode change with early detection
        
        Args:
            expected_mode: Expected account mode ('demo' or 'live')
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if mode changed to expected value within timeout
        """
        start_time = time.time()
        last_check_time = 0
        check_interval = 0.1  # Check every 100ms for better responsiveness
        
        while time.time() - start_time < timeout:
            current_time = time.time()
            
            # Only check at intervals to avoid excessive polling
            if current_time - last_check_time >= check_interval:
                try:
                    current_mode = self.get_current_account_mode()
                    if current_mode == expected_mode:
                        elapsed = current_time - start_time
                        logger.debug(f"Account mode change detected in {elapsed:.2f}s")
                        return True
                    
                    last_check_time = current_time
                    
                except Exception as e:
                    logger.debug(f"Error during mode change detection: {e}")
            
            time.sleep(0.05)  # Smaller sleep for better responsiveness
        
        logger.debug(f"Account mode change timeout after {timeout}s")
        return False

    def get_current_account_mode(self) -> Optional[str]:
        """
        Get the current account mode (demo or live) with enhanced detection
        
        Returns:
            'demo', 'live', or None if unable to determine
        """
        if not self.driver:
            logger.debug("No driver available for account mode detection")
            return None
            
        try:
            if not self.element_detector:
                self.element_detector = ElementDetector(self.driver)
            
            logger.debug("Starting account mode detection...")
            
            # Strategy 1: Look for active account type indicator
            try:
                active_element = self.element_detector.find_element_from_selector(
                    self.selectors.ACTIVE_ACCOUNT_TYPE, timeout=3, first_match_only=True
                )
                
                if active_element:
                    text = self.element_detector.extract_text_safe(active_element).lower()
                    logger.debug(f"Strategy 1 - Active account element text: '{text}'")
                    if 'demo' in text:
                        logger.info("Account mode detected as 'demo' via active element")
                        return 'demo'
                    elif 'real' in text or 'live' in text:
                        logger.info("Account mode detected as 'live' via active element")
                        return 'live'
            except Exception as e:
                logger.debug(f"Strategy 1 failed: {e}")
            
            # Strategy 2: Check account switch control for current state
            try:
                switch_control = self.element_detector.find_element_from_selector(
                    self.selectors.ACCOUNT_SWITCH_CONTROL, timeout=3, first_match_only=True
                )
                
                if switch_control:
                    switch_text = self.element_detector.extract_text_safe(switch_control).lower()
                    switch_class = switch_control.get_attribute('class') or ''
                    logger.debug(f"Strategy 2 - Switch control text: '{switch_text}', class: '{switch_class}'")
                    
                    if 'demo' in switch_text or 'demo' in switch_class:
                        logger.info("Account mode detected as 'demo' via switch control")
                        return 'demo'
                    elif 'live' in switch_text or 'real' in switch_text or 'live' in switch_class:
                        logger.info("Account mode detected as 'live' via switch control")
                        return 'live'
            except Exception as e:
                logger.debug(f"Strategy 2 failed: {e}")
            
            # Strategy 3: Check demo mode span
            try:
                demo_element = self.element_detector.find_element_from_selector(
                    self.selectors.DEMO_MODE_SPAN, timeout=2, first_match_only=True
                )
                
                if demo_element and demo_element.is_displayed():
                    demo_class = demo_element.get_attribute('class') or ''
                    demo_text = self.element_detector.extract_text_safe(demo_element).lower()
                    logger.debug(f"Strategy 3 - Demo element class: '{demo_class}', text: '{demo_text}', displayed: {demo_element.is_displayed()}")
                    
                    if 'active' in demo_class or 'selected' in demo_class:
                        logger.info("Account mode detected as 'demo' via demo span class")
                        return 'demo'
            except Exception as e:
                logger.debug(f"Strategy 3 failed: {e}")
            
            # Strategy 4: Check real/live mode span
            try:
                real_element = self.element_detector.find_element_from_selector(
                    self.selectors.REAL_MODE_SPAN, timeout=2, first_match_only=True
                )
                
                if real_element and real_element.is_displayed():
                    real_class = real_element.get_attribute('class') or ''
                    real_text = self.element_detector.extract_text_safe(real_element).lower()
                    logger.debug(f"Strategy 4 - Real element class: '{real_class}', text: '{real_text}', displayed: {real_element.is_displayed()}")
                    
                    if 'active' in real_class or 'selected' in real_class:
                        logger.info("Account mode detected as 'live' via real span class")
                        return 'live'
            except Exception as e:
                logger.debug(f"Strategy 4 failed: {e}")
            
            # Strategy 5: Check URL patterns
            try:
                current_url = self.driver.current_url.lower()
                logger.debug(f"Strategy 5 - Current URL: {current_url}")
                
                if 'demo' in current_url or 'practice' in current_url:
                    logger.info("Account mode detected as 'demo' via URL")
                    return 'demo'
                elif 'live' in current_url or 'real' in current_url:
                    logger.info("Account mode detected as 'live' via URL")
                    return 'live'
            except Exception as e:
                logger.debug(f"Strategy 5 failed: {e}")
            
            # Strategy 6: Check page title
            try:
                page_title = self.driver.title.lower()
                logger.debug(f"Strategy 6 - Page title: {page_title}")
                
                if 'demo' in page_title or 'practice' in page_title:
                    logger.info("Account mode detected as 'demo' via page title")
                    return 'demo'
                elif 'live' in page_title or 'real' in page_title:
                    logger.info("Account mode detected as 'live' via page title")
                    return 'live'
            except Exception as e:
                logger.debug(f"Strategy 6 failed: {e}")
            
            # Strategy 7: Check for any visible elements with account indicators
            try:
                # Look for any element containing account type text
                all_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Demo') or contains(text(), 'Live') or contains(text(), 'Real')]")
                
                for element in all_elements[:10]:  # Check first 10 elements
                    if element.is_displayed():
                        element_text = self.element_detector.extract_text_safe(element).lower()
                        if 'demo' in element_text and ('account' in element_text or 'mode' in element_text):
                            logger.info("Account mode detected as 'demo' via visible element")
                            return 'demo'
                        elif ('live' in element_text or 'real' in element_text) and ('account' in element_text or 'mode' in element_text):
                            logger.info("Account mode detected as 'live' via visible element")
                            return 'live'
            except Exception as e:
                logger.debug(f"Strategy 7 failed: {e}")
            
            # All strategies failed
            logger.warning("Could not determine account mode from any method")
            logger.debug("Taking screenshot for debugging...")
            try:
                timestamp = int(time.time())
                screenshot_path = f"debug_account_mode_{timestamp}.png"
                self.driver.save_screenshot(screenshot_path)
                logger.debug(f"Debug screenshot saved: {screenshot_path}")
            except Exception as e:
                logger.debug(f"Could not save debug screenshot: {e}")
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get current account mode: {e}")
            return None
        
    def extract_account_balance_data(self) -> Dict[str, Any]:
        """
        Extract comprehensive account balance and margin data from WebDriver
        
        Returns:
            Dictionary containing account balance information
        """
        logger.info("Extracting account balance data from WebDriver")
        
        balance_data = {
            'account_type': self.detect_current_account_type(),
            'timestamp': time.time()
        }
        
        try:
            # Extract equity (Total Account Value)
            equity_element = self.element_detector.find_element_robust(
                self.selectors.EQUITY_VALUE, timeout=2
            )
            if equity_element:
                equity_text = self.element_detector.extract_text_safe(equity_element)
                equity_value = self._parse_currency_value(equity_text)
                balance_data['equity'] = equity_value
                balance_data['balance'] = equity_value  # Plus500 uses equity as balance
                logger.debug(f"Extracted equity: ${equity_value}")
            
            # Extract total P&L
            pnl_element = self.element_detector.find_element_robust(
                self.selectors.TOTAL_PNL, timeout=5
            )
            if pnl_element:
                pnl_text = self.element_detector.extract_text_safe(pnl_element)
                pnl_value = self._parse_currency_value(pnl_text)
                balance_data['total_pnl'] = pnl_value
                logger.debug(f"Extracted total P&L: ${pnl_value}")
            
            # Extract live margin available
            live_margin_element = self.element_detector.find_element_robust(
                self.selectors.LIVE_MARGIN_AVAILABLE, timeout=2
            )
            if live_margin_element:
                live_margin_text = self.element_detector.extract_text_safe(live_margin_element)
                live_margin_value = self._parse_currency_value(live_margin_text)
                balance_data['live_margin_available'] = live_margin_value
                balance_data['available'] = live_margin_value  # Use live margin as available funds
                logger.debug(f"Extracted live margin available: ${live_margin_value}")
            
            # Extract full margin available
            full_margin_element = self.element_detector.find_element_robust(
                self.selectors.FULL_MARGIN_AVAILABLE, timeout=2
            )
            if full_margin_element:
                full_margin_text = self.element_detector.extract_text_safe(full_margin_element)
                full_margin_value = self._parse_currency_value(full_margin_text)
                balance_data['full_margin_available'] = full_margin_value
                logger.debug(f"Extracted full margin available: ${full_margin_value}")
            
            # Calculate margin used (equity - available margin)
            if 'equity' in balance_data and 'available' in balance_data:
                margin_used = balance_data['equity'] - balance_data['available']
                balance_data['margin_used'] = max(Decimal('0'), margin_used)
            
            logger.info(f"Successfully extracted account balance data: {len(balance_data)} fields")
            return balance_data
            
        except Exception as e:
            logger.error(f"Failed to extract account balance data: {e}")
            return balance_data
    
    def get_enhanced_account_info(self) -> Account:
        """
        Get enhanced account information combining WebDriver and API data
        
        Returns:
            Enhanced Account model with WebDriver-extracted data
        """
        logger.info("Getting enhanced account information")
        
        try:
            # Start with WebDriver extracted data
            webdriver_data = self.extract_account_balance_data()
            
            # Get base account data from API if available
            if self.account_client:
                try:
                    api_account = self.account_client.get_account()
                    logger.debug("Successfully retrieved API account data")
                except Exception as e:
                    logger.warning(f"Could not retrieve API account data: {e}")
                    api_account = None
            else:
                api_account = None
            
            # Merge WebDriver and API data
            if api_account:
                # Start with API data
                account_data = api_account.model_dump()
                
                # Override with WebDriver data where available
                for key, value in webdriver_data.items():
                    if value is not None and key in ['equity', 'balance', 'available', 'margin_used', 'account_type']:
                        account_data[key] = value
                
                # Add WebDriver-specific fields
                account_data['total_pnl'] = webdriver_data.get('total_pnl')
                account_data['live_margin_available'] = webdriver_data.get('live_margin_available')
                account_data['full_margin_available'] = webdriver_data.get('full_margin_available')
                
            else:
                # Create account from WebDriver data only
                account_data = {
                    'account_id': f"plus500_{webdriver_data.get('account_type', 'unknown')}",
                    'account_type': webdriver_data.get('account_type', self.config.account_type),
                    'balance': webdriver_data.get('balance', Decimal('0')),
                    'available': webdriver_data.get('available', Decimal('0')),
                    'margin_used': webdriver_data.get('margin_used', Decimal('0')),
                    'equity': webdriver_data.get('equity'),
                    'pnl': webdriver_data.get('total_pnl'),
                    'currency': 'USD'
                }
            
            enhanced_account = Account(**account_data)
            logger.info(f"Created enhanced account: {enhanced_account.account_type} with ${enhanced_account.balance}")
            return enhanced_account
            
        except Exception as e:
            logger.error(f"Failed to get enhanced account info: {e}")
            raise ValidationError(f"Enhanced account info retrieval failed: {e}")

    def get_account_balance(self) -> Decimal:
        """
        Get the current account balance

        Returns:
            Decimal: The current account balance
        """
        logger.info("Getting account balance")
        try:
            balance_data = self.extract_account_balance_data()
            return balance_data.get('balance', Decimal('0'))
        except Exception as e:
            logger.error(f"Failed to get account balance: {e}")
            raise ValidationError(f"Account balance retrieval failed: {e}")

    def monitor_account_changes(self, callback_func=None, poll_interval: int = 5) -> None:
        """
        Monitor account balance changes in real-time
        
        Args:
            callback_func: Function to call when changes are detected
            poll_interval: Polling interval in seconds
        """
        logger.info(f"Starting account monitoring (poll interval: {poll_interval}s)")
        
        last_balance_data = None
        
        try:
            while True:
                current_balance_data = self.extract_account_balance_data()
                
                if last_balance_data is not None:
                    # Check for changes
                    changes = self._detect_balance_changes(last_balance_data, current_balance_data)
                    
                    if changes and callback_func:
                        callback_func(changes, current_balance_data)
                
                last_balance_data = current_balance_data
                time.sleep(poll_interval)
                
        except KeyboardInterrupt:
            logger.info("Account monitoring stopped by user")
        except Exception as e:
            logger.error(f"Account monitoring failed: {e}")
    
    def _parse_currency_value(self, text: str) -> Optional[Decimal]:
        """
        Parse currency value from text (handles $ signs, commas, etc.)
        
        Args:
            text: Text containing currency value
            
        Returns:
            Decimal value or None if parsing fails
        """
        if not text:
            return None
        
        try:
            # Remove currency symbols, commas, and whitespace
            cleaned_text = re.sub(r'[$,\s‪‬]', '', text.strip())
            
            # Handle negative values
            if cleaned_text.startswith('-') or 'red' in text.lower():
                cleaned_text = cleaned_text.lstrip('-')
                multiplier = -1
            else:
                multiplier = 1
            
            # Extract numeric value
            numeric_match = re.search(r'(\d+\.?\d*)', cleaned_text)
            if numeric_match:
                value = Decimal(numeric_match.group(1)) * multiplier
                return value
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to parse currency value '{text}': {e}")
            return None
    
    def _detect_balance_changes(self, old_data: Dict[str, Any], 
                               new_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect changes between two balance data snapshots
        
        Args:
            old_data: Previous balance data
            new_data: Current balance data
            
        Returns:
            Dictionary of detected changes
        """
        changes = {}
        
        for key in ['equity', 'total_pnl', 'live_margin_available', 'full_margin_available']:
            old_value = old_data.get(key)
            new_value = new_data.get(key)
            
            if old_value is not None and new_value is not None:
                if old_value != new_value:
                    changes[key] = {
                        'old': old_value,
                        'new': new_value,
                        'change': new_value - old_value
                    }
        
        return changes
    
    def get_driver(self):
        """Get the WebDriver instance"""
        return self.driver