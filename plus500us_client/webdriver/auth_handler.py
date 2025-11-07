from __future__ import annotations
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from regex import T
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from sympy import N

from plus500us_client import webdriver
from plus500us_client.hybrid import session_bridge

from .browser_manager import BrowserManager
from .element_detector import ElementDetector
from .selectors import Plus500Selectors
from .account_manager import WebDriverAccountManager
from ..config import Config
from ..errors import AuthenticationError, CaptchaRequiredError
from ..hybrid import SessionBridge
from ..security import secure_logger, SecureCredentialHandler


logger = secure_logger(__name__)

class WebDriverAuthHandler:
    """Handles authentication through WebDriver with manual login and cookie transfer"""
    
    def __init__(self, config: Config, browser_config: Optional[Dict[str, Any]] = None):
        self.config = config
        self.browser_config = browser_config or self._get_default_browser_config()
        self.browser_manager = BrowserManager(self.browser_config)
        self.element_detector: Optional[ElementDetector] = None
        self.driver = None
        self.selectors = Plus500Selectors()
        self.account_manager = WebDriverAccountManager(config=self.config, browser_manager=self.browser_manager)

    def client_login(self, email: str = None, password: str = None):
        """
        Direct client login using email and password
        
        Args:
            email: User email
            password: User password
            
        Returns:
            Dictionary containing session data and cookies
        """
        if email and password:
            self.config.email = email
            self.config.password = password

        session_bridge = SessionBridge()
        session_backup_file = "plus500_session_backup.json"
        session_data = None

        # Start browser
        self.driver = self.browser_manager.start_browser()
        self.element_detector = ElementDetector(self.driver)
        
        # Initialize account manager with driver
        self.account_manager.initialize(self.driver)
        
        # Navigate to main page
        login_url = f"{self.config.base_url}/trade?innerTags=_cc_&page=login"
        self.driver.get(login_url)
        self.element_detector.wait_for_page_load()

        # Check for saved session data
        if Path(session_backup_file).exists():
            try:
                session_data = session_bridge.restore_session_data(session_backup_file)
                print("✅ Extracted session from backup. Proceeding with automatic login.")
                session_data = self._automatic_login_flow(session_data)
            except Exception as e:
                session_data = None
                self._take_debug_screenshot("session_restore_error")
                logger.error(f"Failed to restore session from backup: {e}")
                session_data = self.manual_login_flow()
        else:
           session_data = self.manual_login_flow()

        # Store the session data
        session_bridge.backup_session_data(session_data, session_backup_file)

    def _automatic_login_flow(self, session_data: Optional[Dict[str, Any]] = None):
        """
        Complete automatic login flow with cookie transfer

        Returns:
            Dictionary containing session data and cookies
        """
        try:
            
            if session_data:
                print("Removing Current session cookies.")
                self.driver.delete_all_cookies()
                print("🔄 Restoring session cookies...")
                
                # Ensure session_data is a dict and has cookies
                if isinstance(session_data, dict):
                    cookies = session_data.get('cookies', [])

                else:
                    logger.error(f"Session data is not a dict: {type(session_data)}")
                    raise AuthenticationError("Invalid session data format")
                
                for cookie in cookies:
                    try:
                        self.driver.add_cookie(cookie)
                        print(f"✅ Restored cookie: {cookie['name']}")
                    except:
                        pass
                self.driver.refresh()
                time.sleep(0.1)
                print("✅ All Session cookies restored")

            # Wait for Login elements to be visible
            em = self.element_detector.safe_wait_for_element(self.selectors.LOGIN_EMAIL, timeout=1)
            pa = self.element_detector.safe_wait_for_element(self.selectors.LOGIN_PASSWORD, timeout=1)
            lg = self.element_detector.safe_wait_for_element(self.selectors.LOGIN_BUTTON, timeout=1)

            # Keys
            if em and pa and lg:
                try:
                    # Use credential masking for security
                    masked_email = SecureCredentialHandler.mask_sensitive_data(self.config.email or "")
                    logger.info(f"Entering credentials for email: {masked_email}")
                    
                    self.element_detector.safe_send_keys(self.selectors.LOGIN_EMAIL, self.config.email)
                    self.element_detector.safe_send_keys(self.selectors.LOGIN_PASSWORD, self.config.password)
                    self.element_detector.safe_click(self.selectors.KEEP_ME_LOGGED_IN)  
                    self.element_detector.safe_click(self.selectors.LOGIN_BUTTON)

                    # Smart ReCAPTCHA Detection with Content Validation
                    recaptcha_container = self.element_detector.find_element_from_selector(self.selectors.RECAPTCHA, timeout=3,
                                                                                           first_match_only=True)
                    if recaptcha_container:
                        if self._is_recaptcha_active(recaptcha_container):
                            print("🔒 Active ReCAPTCHA challenge detected, waiting for human completion...")
                            success = self._handle_recaptcha(recaptcha_container)
                            if not success:
                                raise CaptchaRequiredError("ReCAPTCHA not completed - manual intervention required")
                            print("✅ ReCAPTCHA completed successfully.")
                        else:
                            logger.debug("ReCAPTCHA container found but inactive - continuing automatic login")
                            print("✅ No active ReCAPTCHA challenge - proceeding with automatic login.")
                    else:
                        print("✅ No ReCAPTCHA detected.")

                    # Wait for potential redirects
                    self.element_detector.wait_for_page_load(timeout=3)

                    # Check if logged in
                    if self._is_already_logged_in():
                        session_data = self._extract_session_data()
                        logger.info("✅ Automatic login successful")
                        return session_data
                    else:
                        logger.warning("Login completed but dashboard not detected")
                        raise AuthenticationError("Login completed but not successfully authenticated")

                except Exception as e:
                    logger.error(f"Error during login: {e}")
                    self._take_debug_screenshot("login_error")
                    raise AuthenticationError("Login failed due to input error")
            else:
                logger.warning("Login elements not found")
                self._take_debug_screenshot("login_elements_not_found")
                raise AuthenticationError("Login failed due to missing elements")        
            
        except Exception as e:
            logger.error(f"Automatic login flow failed: {e}")
            self._take_debug_screenshot("auto_login_error")
            raise AuthenticationError(f"Login failed: {e}")

    def manual_login_flow(self, account_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Complete manual login flow with browser handoff
        
        Args:
            account_type: 'demo' or 'live' account selection
            
        Returns:
            Dictionary containing session data and cookies
        """
        try:
            # Start browser
            logger.info("Starting manual login flow")
            
            # Wait for page load
            self.element_detector.wait_for_page_load()
            self.browser_manager.random_delay(1, 2)
            
            # Check if already logged in
            if self._is_already_logged_in():
                logger.info("Already logged in, extracting session data")
                return self._extract_session_data()
            
            # Display login instructions
            self._display_login_instructions(account_type)
            
            # Wait for user to complete login
            self._wait_for_login_completion()
            
            # Verify login success
            self._verify_login_success()
            
            # Select account type if needed
            if account_type:
                self.account_manager.switch_account_mode(account_type)

            # Extract session data
            session_data = self._extract_session_data()
            
            logger.info("Manual login flow completed successfully")
            return session_data
            
        except Exception as e:
            logger.error(f"Manual login flow failed: {e}")
            self._take_debug_screenshot("login_error")
            raise AuthenticationError(f"Login failed: {e}")
    
    def get_current_session_data(self) -> Dict[str, Any]:
        """
        Get current session data from active WebDriver instance
        
        Returns:
            Dictionary containing current session data and cookies
        """
        if not self.driver:
            raise AuthenticationError("No active WebDriver session")
        
        try:
            # Extract current session data
            return self._extract_session_data()
            
        except Exception as e:
            logger.error(f"Failed to get current session data: {e}")
            raise AuthenticationError(f"Session data extraction failed: {e}")
        
    def quick_cookie_import(self, stay_open: bool = True) -> Dict[str, Any]:
        """
        Quick cookie import for already authenticated users
        
        Args:
            stay_open: Keep browser open after cookie import
            
        Returns:
            Dictionary containing session data
        """
        try:
            self.driver = self.browser_manager.start_browser()
            self.element_detector = ElementDetector(self.driver)
            
            # Navigate to main page
            self.driver.get(self.config.base_url)
            self.element_detector.wait_for_page_load()
            
            # Check if logged in
            if self._is_already_logged_in():
                session_data = self._extract_session_data()
                
                if not stay_open:
                    self.browser_manager.stop_browser()
                    
                return session_data
            else:
                raise AuthenticationError("Not logged in - please use manual_login_flow")
                
        except Exception as e:
            logger.error(f"Cookie import failed: {e}")
            raise
    
    def _get_default_browser_config(self) -> Dict[str, Any]:
        """Get default browser configuration"""
        return {
            'browser': 'firefox',
            'headless': False,  # Always visible for manual login
            'stealth_mode': True,
            'window_size': (1920, 1080),
            'implicit_wait': 10,
            'page_load_timeout': 60,
            'profile_path': self.config.base_url.replace('https://', '').replace('/', '_') + '_profile'
        }
    
    def _display_login_instructions(self, account_type: Optional[str] = None) -> None:
        """Display clear instructions for manual login"""
        print("\n" + "="*60)
        print("🌐 MANUAL LOGIN REQUIRED")
        print("="*60)
        print(f"📍 Browser opened at: {self.driver.current_url}")
        print(f"🎯 Target account: {account_type or 'Any'}")
        print()
        print("📋 INSTRUCTIONS:")
        print("1. ✅ Complete login in the browser window")
        print("2. ✅ Handle any captcha/2FA verification")
        if account_type == 'demo':
            print("3. ✅ Select DEMO account when prompted")
        elif account_type == 'live':
            print("3. ⚠️  Select LIVE account when prompted")
        else:
            print("3. ✅ Select your preferred account type")
        print("4. ✅ Wait for trading dashboard to load")
        print("5. ✅ The client will automatically detect completion")
        print()
        print("⏳ Waiting for login completion...")
        print("   (You have up to 5 minutes)")
        print("="*60)
    
    def _wait_for_login_completion(self, timeout: int = 300) -> None:
        """
        Wait for user to complete login manually
        
        Args:
            timeout: Maximum wait time in seconds (default 5 minutes)
        """
        start_time = time.time()
        last_url = ""
        
        while time.time() - start_time < timeout:
            try:
                current_url = self.driver.current_url
                
                # Check for successful login indicators
                if self._is_login_successful():
                    logger.info("Login completion detected")
                    return
                
                # Check for common error states
                if self._check_for_login_errors():
                    raise AuthenticationError("Login error detected on page")
                
                # Log URL changes for debugging
                if current_url != last_url:
                    logger.debug(f"URL changed to: {current_url}")
                    last_url = current_url
                
                # Add human-like behavior simulation
                if time.time() % 30 < 1:  # Every 30 seconds
                    self.browser_manager.simulate_human_behavior()
                
                time.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                logger.debug(f"Error during login wait: {e}")
                time.sleep(2)
                continue
        
        # Timeout reached
        self._take_debug_screenshot("login_timeout")
        raise TimeoutException("Login timeout - user did not complete login within 5 minutes")
    
    def _is_already_logged_in(self) -> bool:
        """Check if user is already logged in"""
        success_indicators = [
            self.selectors.DASHBOARD_INDICATOR,
            self.selectors.BALANCE_DISPLAY,
            {"xpath": ["//div[contains(@class, 'trading-workspace')]"], "css": [".trading-workspace"]}
        ]
        
        for indicator in success_indicators:
            if self.element_detector.is_element_present(indicator):
                logger.debug("Found login success indicator")
                return True
        
        # Check URL patterns
        current_url = self.driver.current_url.lower()
        success_patterns = ['dashboard', 'trading', 'workspace', 'portfolio']
        
        if any(pattern in current_url for pattern in success_patterns):
            logger.debug("URL indicates successful login")
            return True
            
        return False
    
    def _is_login_successful(self) -> bool:
        """Check if login was successful by looking for dashboard elements"""
        return self._is_already_logged_in()
    
    def _check_for_login_errors(self) -> bool:
        """Check for login error messages or blocked states"""
        error_indicators = [
            {"xpath": ["//div[contains(@class, 'error') and contains(text(), 'login')]"], "css": [".login-error"]},
            {"xpath": ["//div[contains(text(), 'Invalid') or contains(text(), 'incorrect')]"], "css": [".error-message"]},
            {"xpath": ["//div[contains(text(), 'blocked') or contains(text(), 'suspended')]"], "css": [".account-blocked"]}
        ]
        
        for indicator in error_indicators:
            if self.element_detector.is_element_present(indicator):
                return True
                
        return False
    
    def _verify_login_success(self) -> None:
        """Verify that login was successful"""
        if not self._is_login_successful():
            self._take_debug_screenshot("login_verification_failed")
            raise AuthenticationError("Login verification failed - dashboard not detected")
        
        logger.info("✅ Login verified successfully")
    
    def _extract_session_data(self) -> Dict[str, Any]:
        """Extract comprehensive session data from browser"""
        try:
            # Get all cookies
            cookies = self.driver.get_cookies()
            
            # Get current URL and title
            current_url = self.driver.current_url
            page_title = self.driver.title
            
            # Extract CSRF token if available
            csrf_token = self._extract_csrf_token()
            
            # Get local storage data
            local_storage = self._get_local_storage()
            
            # Get session storage data
            session_storage = self._get_session_storage()
            
            # Get user agent
            user_agent = self.driver.execute_script("return navigator.userAgent;")
            
            # Detect account type from page content
            account_type = self._detect_account_type()
            
            session_data = {
                'cookies': cookies,
                'url': current_url,
                'title': page_title,
                'csrf_token': csrf_token,
                'local_storage': local_storage,
                'session_storage': session_storage,
                'user_agent': user_agent,
                'account_type': account_type,
                'timestamp': time.time(),
                'success': True
            }
            
            logger.info(f"Extracted session data: {len(cookies)} cookies, account: {account_type}")
            return session_data
            
        except Exception as e:
            logger.error(f"Failed to extract session data: {e}")
            return {'success': False, 'error': str(e)}
    
    def _extract_csrf_token(self) -> Optional[str]:
        """Extract CSRF token from page"""
        try:
            # Try multiple methods to find CSRF token
            csrf_selectors = [
                "//meta[@name='csrf-token']/@content",
                "//input[@name='_token']/@value",
                "//meta[@name='_token']/@content"
            ]
            
            for selector in csrf_selectors:
                try:
                    token = self.driver.execute_script(f"return document.evaluate('{selector}', document, null, XPathResult.STRING_TYPE, null).stringValue;")
                    if token:
                        return token
                except:
                    continue
                    
            # Try to find in JavaScript variables
            js_token = self.driver.execute_script("""
                var token = window.csrfToken || window._token || window.csrf_token;
                return token || null;
            """)
            
            return js_token
            
        except Exception as e:
            logger.debug(f"Could not extract CSRF token: {e}")
            return None
    
    def _get_local_storage(self) -> Dict[str, Any]:
        """Get local storage data"""
        try:
            return self.driver.execute_script("""
                var storage = {};
                for (var i = 0; i < localStorage.length; i++) {
                    var key = localStorage.key(i);
                    storage[key] = localStorage.getItem(key);
                }
                return storage;
            """)
        except Exception as e:
            logger.debug(f"Could not get local storage: {e}")
            return {}
    
    def _get_session_storage(self) -> Dict[str, Any]:
        """Get session storage data"""
        try:
            return self.driver.execute_script("""
                var storage = {};
                for (var i = 0; i < sessionStorage.length; i++) {
                    var key = sessionStorage.key(i);
                    storage[key] = sessionStorage.getItem(key);
                }
                return storage;
            """)
        except Exception as e:
            logger.debug(f"Could not get session storage: {e}")
            return {}
    
    def _detect_account_type(self) -> str:
        """Detect current account type from page content"""
        try:
            # Look for demo/live indicators in the page
            
            
            # Check for demo indicators
            for xpath in Plus500Selectors.DEMO_MODE_SPAN:
                try:
                    element = self.driver.find_element(By.XPATH, xpath)
                    if element.is_displayed():
                        return 'demo'
                except:
                    continue
            
            # Check for live indicators
            for xpath in Plus500Selectors.REAL_MODE_SPAN:
                try:
                    element = self.driver.find_element(By.XPATH, xpath)
                    if element.is_displayed():
                        return 'live'
                except:
                    continue

            # Check for live indicators
            for xpath in Plus500Selectors.REAL_MODE_SPAN:
                try:
                    element = self.driver.find_element(By.XPATH, xpath)
                    if element.is_displayed():
                        return 'live'
                except:
                    continue

            # Check URL for account type
            current_url = self.driver.current_url.lower()
            if 'demo' in current_url:
                return 'demo'
            elif 'live' in current_url:
                return 'live'

            # Default to configured account type
            return self.config.account_type
            
        except Exception as e:
            logger.debug(f"Could not detect account type: {e}")
            return self.config.account_type
    
    def _handle_recaptcha(self, recaptcha_element) -> bool:
        """
        Handle RECAPTCHA detection with human input waiting
        
        Args:
            recaptcha_element: WebDriver element containing RECAPTCHA
            
        Returns:
            True if RECAPTCHA was completed successfully
        """
        logger.info("RECAPTCHA detected - waiting for human completion")
        
        try:
            # Take screenshot for user reference
            self._take_debug_screenshot("recaptcha_detected")
            
            # Check RECAPTCHA type and provide specific instructions
            recaptcha_type = self._identify_recaptcha_type(recaptcha_element)
            self._display_recaptcha_instructions(recaptcha_type)
            
            # Wait for human completion with timeout
            timeout = 120  # 2 minutes
            start_time = time.time()
            
            print(f"⏳ Waiting for RECAPTCHA completion (timeout: {timeout} seconds)...")
            print("   Please complete the RECAPTCHA challenge in the browser window.")
            print("   The system will automatically detect completion.")
            
            while time.time() - start_time < timeout:
                try:
                    # Check if RECAPTCHA is still present
                    current_recaptcha = self.element_detector.find_element_from_selector(
                        self.selectors.RECAPTCHA, timeout=1
                    )
                    
                    if not current_recaptcha or not current_recaptcha.is_displayed():
                        print("✅ RECAPTCHA appears to be completed!")
                        time.sleep(2)  # Wait for any redirects
                        return True
                    
                    # Check if login succeeded (RECAPTCHA completed)
                    if self._is_already_logged_in():
                        print("✅ Login successful - RECAPTCHA completed!")
                        return True
                    
                    # Check for error messages
                    if self._check_for_login_errors():
                        print("❌ Login error detected")
                        return False
                    
                    # Update progress indicator
                    remaining = int(timeout - (time.time() - start_time))
                    if remaining % 10 == 0:  # Update every 10 seconds
                        print(f"   ⏱️  {remaining} seconds remaining...")
                    
                    time.sleep(1)  # Check every second
                    
                except Exception as e:
                    logger.debug(f"Error checking RECAPTCHA completion: {e}")
                    time.sleep(1)
                    continue
            
            # Timeout reached
            print("⚠️  RECAPTCHA completion timeout reached")
            self._take_debug_screenshot("recaptcha_timeout")
            return False
            
        except Exception as e:
            logger.error(f"Error handling RECAPTCHA: {e}")
            self._take_debug_screenshot("recaptcha_error")
            return False
    
    def _identify_recaptcha_type(self, recaptcha_element) -> str:
        """
        Identify the type of RECAPTCHA challenge
        
        Args:
            recaptcha_element: WebDriver element containing RECAPTCHA
            
        Returns:
            String identifying RECAPTCHA type
        """
        try:
            element_html = recaptcha_element.get_attribute('outerHTML').lower()
            
            if 'hcaptcha' in element_html:
                return 'hcaptcha'
            elif 'recaptcha' in element_html:
                if 'checkbox' in element_html or 'v2' in element_html:
                    return 'recaptcha_v2'
                else:
                    return 'recaptcha_v3'
            else:
                return 'unknown'
                
        except Exception:
            return 'unknown'
    
    def _display_recaptcha_instructions(self, recaptcha_type: str) -> None:
        """
        Display specific instructions based on RECAPTCHA type
        
        Args:
            recaptcha_type: Type of RECAPTCHA detected
        """
        print("\n" + "="*60)
        print("🔒 RECAPTCHA CHALLENGE DETECTED")
        print("="*60)
        
        if recaptcha_type == 'recaptcha_v2':
            print("📋 INSTRUCTIONS for Google reCAPTCHA v2:")
            print("   1. Look for the 'I'm not a robot' checkbox")
            print("   2. Click the checkbox")
            print("   3. If images appear, select them as instructed")
            print("   4. Wait for the green checkmark")
            
        elif recaptcha_type == 'hcaptcha':
            print("📋 INSTRUCTIONS for hCaptcha:")
            print("   1. Look for the hCaptcha challenge box")
            print("   2. Click on the images as instructed")
            print("   3. Continue until all challenges are complete")
            print("   4. Wait for completion confirmation")
            
        elif recaptcha_type == 'recaptcha_v3':
            print("📋 INSTRUCTIONS for Google reCAPTCHA v3:")
            print("   1. This should be automatic (no user interaction)")
            print("   2. If a challenge appears, complete it as shown")
            print("   3. Wait for automatic verification")
            
        else:
            print("📋 GENERAL INSTRUCTIONS:")
            print("   1. Look for any CAPTCHA or verification challenge")
            print("   2. Complete the challenge as instructed")
            print("   3. Wait for verification to complete")
        
        print("\n🕐 The system will automatically detect completion.")
        print("💡 TIP: Keep this browser window active and visible.")
        print("🎯 DO NOT refresh the page or navigate away.")
        print("="*60 + "\n")
    
    def _take_debug_screenshot(self, prefix: str) -> None:
        """Take screenshot for debugging"""
        try:
            if self.browser_manager:
                filename = f"{prefix}_{int(time.time())}.png"
                self.browser_manager.take_screenshot(filename)
        except Exception as e:
            logger.debug(f"Could not take screenshot: {e}")
    
    def _is_recaptcha_active(self, recaptcha_element) -> bool:
        """
        Check if RECAPTCHA container has active content requiring human intervention
        
        Args:
            recaptcha_element: WebDriver element containing RECAPTCHA
            
        Returns:
            True if CAPTCHA challenge is active and needs human input
            False if container is empty/inactive and login can proceed automatically
        """
        logger.debug("Checking if RECAPTCHA is active...")
        
        try:
            # Strategy 1: Check element innerHTML content
            inner_html = recaptcha_element.get_attribute('innerHTML') or ''
            logger.debug(f"RECAPTCHA innerHTML length: {len(inner_html.strip())}")
            
            if not inner_html.strip():
                logger.debug("RECAPTCHA container is empty - not active")
                return False
            
            # Strategy 2: Check for child elements
            child_elements = recaptcha_element.find_elements(By.XPATH, ".//*")
            logger.debug(f"RECAPTCHA child elements count: {len(child_elements)}")
            
            if not child_elements:
                logger.debug("RECAPTCHA has no child elements - not active")
                return False
            
            # Strategy 3: Check for specific RECAPTCHA indicators
            active_indicators = self._check_recaptcha_active_indicators(recaptcha_element)
            logger.debug(f"RECAPTCHA active indicators found: {active_indicators}")
            
            if not active_indicators:
                logger.debug("No active RECAPTCHA indicators found - not active")
                return False
            
            # Strategy 4: Check visibility of challenge elements
            has_visible_elements = self._has_visible_recaptcha_elements(recaptcha_element)
            logger.debug(f"RECAPTCHA has visible elements: {has_visible_elements}")
            
            if not has_visible_elements:
                logger.debug("No visible RECAPTCHA elements - not active")
                return False
            
            # If we reach here, RECAPTCHA appears to be active
            logger.info("RECAPTCHA determined to be ACTIVE - human intervention required")
            return True
            
        except Exception as e:
            logger.debug(f"Error checking RECAPTCHA activity: {e}")
            # If we can't determine, err on the side of caution and treat as active
            logger.warning("Could not determine RECAPTCHA activity - treating as active for safety")
            return True
    
    def _check_recaptcha_active_indicators(self, recaptcha_element) -> bool:
        """
        Enhanced check for specific indicators that RECAPTCHA is active
        Optimized for Plus500 HTML structure with iframe detection
        
        Args:
            recaptcha_element: WebDriver element containing RECAPTCHA
            
        Returns:
            True if active indicators are found
        """
        try:
            # Strategy 1: Check for Plus500 specific reCAPTCHA iframe structure
            plus500_indicators = [
                ".//iframe[@title='reCAPTCHA' and contains(@src, 'recaptcha/api2/anchor')]",
                ".//iframe[@title='reCAPTCHA' and @width='304' and @height='78']",
                ".//textarea[@id='g-recaptcha-response'][@class='g-recaptcha-response']",
                ".//iframe[contains(@src, 'google.com/recaptcha/api2/anchor')]"
            ]
            
            for indicator in plus500_indicators:
                try:
                    element = recaptcha_element.find_element(By.XPATH, indicator)
                    if element:
                        logger.debug(f"Found Plus500 reCAPTCHA indicator: {indicator}")
                        # For iframe elements, check if they have a valid src with API parameters
                        if element.tag_name == 'iframe':
                            src = element.get_attribute('src') or ''
                            if 'k=' in src and 'co=' in src:  # reCAPTCHA API parameters
                                logger.debug(f"Active reCAPTCHA iframe with API parameters: {src[:100]}...")
                                return True
                        # For textarea, check if it exists (indicates reCAPTCHA structure)
                        elif element.tag_name == 'textarea':
                            logger.debug("Found g-recaptcha-response textarea - indicates active reCAPTCHA")
                            return True
                except:
                    continue
            
            # Strategy 2: Check iframe dimensions and content for Plus500
            iframes = recaptcha_element.find_elements(By.TAG_NAME, "iframe")
            for iframe in iframes:
                try:
                    src = iframe.get_attribute('src') or ''
                    width = iframe.get_attribute('width') or iframe.size.get('width', 0)
                    height = iframe.get_attribute('height') or iframe.size.get('height', 0)
                    title = iframe.get_attribute('title') or ''
                    
                    # Plus500 specific dimensions and structure
                    if (title == 'reCAPTCHA' and str(width) == '304' and str(height) == '78'):
                        logger.debug(f"Found Plus500 reCAPTCHA iframe with correct dimensions: {width}x{height}")
                        return True
                    
                    # Check for reCAPTCHA API structure
                    if ('recaptcha/api2/anchor' in src and 'k=' in src):
                        logger.debug(f"Found reCAPTCHA API anchor iframe: {src[:100]}...")
                        return True
                        
                except Exception as e:
                    logger.debug(f"Error checking iframe {iframe}: {e}")
                    continue
            
            # Strategy 3: Check for Google reCAPTCHA v2 indicators (fallback)
            v2_indicators = [
                ".//div[contains(@class, 'recaptcha-checkbox')]",
                ".//iframe[contains(@title, 'reCAPTCHA')]",
                ".//div[contains(text(), 'not a robot')]",
                ".//span[contains(@role, 'checkbox')]"
            ]
            
            for indicator in v2_indicators:
                try:
                    element = recaptcha_element.find_element(By.XPATH, indicator)
                    if element and element.is_displayed():
                        logger.debug(f"Found generic reCAPTCHA v2 indicator: {indicator}")
                        return True
                except:
                    continue
            
            # Strategy 4: Check for hCaptcha indicators (fallback)
            hcaptcha_indicators = [
                ".//div[contains(@class, 'hcaptcha-box')]",
                ".//iframe[contains(@src, 'hcaptcha')]",
                ".//div[contains(@class, 'challenge-container')]"
            ]
            
            for indicator in hcaptcha_indicators:
                try:
                    element = recaptcha_element.find_element(By.XPATH, indicator)
                    if element and element.is_displayed():
                        logger.debug(f"Found hCaptcha indicator: {indicator}")
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking RECAPTCHA indicators: {e}")
            return False
    
    def _has_visible_recaptcha_elements(self, recaptcha_element) -> bool:
        """
        Check if RECAPTCHA has visible, interactive elements
        
        Args:
            recaptcha_element: WebDriver element containing RECAPTCHA
            
        Returns:
            True if visible elements are found
        """
        try:
            # Check for visible and enabled interactive elements
            interactive_selectors = [
                "button", "input", "select", "textarea", "iframe",
                "[role='button']", "[role='checkbox']", "[tabindex]"
            ]
            
            for selector in interactive_selectors:
                try:
                    elements = recaptcha_element.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            logger.debug(f"Found visible interactive element: {selector}")
                            return True
                except:
                    continue
            
            # Check for visible text content that indicates an active challenge
            text_content = recaptcha_element.text.strip().lower()
            active_text_indicators = [
                'verify', 'captcha', 'challenge', 'robot', 'human',
                'click', 'select', 'identify', 'complete'
            ]
            
            for indicator in active_text_indicators:
                if indicator in text_content:
                    logger.debug(f"Found active text indicator: '{indicator}' in '{text_content[:100]}...'")
                    return True
            
            # Check element dimensions (active CAPTCHAs usually have size)
            element_size = recaptcha_element.size
            if element_size['width'] > 100 and element_size['height'] > 50:
                logger.debug(f"RECAPTCHA has significant size: {element_size}")
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking visible RECAPTCHA elements: {e}")
            return False
    
    def close_browser(self) -> None:
        """Close the browser"""
        if self.browser_manager:
            self.browser_manager.stop_browser()
    
    def keep_browser_open(self) -> None:
        """Keep browser open for continued use"""
        logger.info("Browser will remain open for continued use")
        logger.info("Call close_browser() when done")
    
    def get_browser_manager(self) -> BrowserManager:
        """Get the browser manager for continued use"""
        return self.browser_manager
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close_browser()