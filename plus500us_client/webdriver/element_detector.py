from __future__ import annotations
import time
import logging
from typing import Optional, List, Dict, Any, Union
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementNotInteractableException,
    StaleElementReferenceException, WebDriverException
)
from .selectors import Plus500Selectors

logger = logging.getLogger(__name__)

class ElementDetector:
    """Robust element detection with multiple fallback strategies using XPath and CSS selectors"""
    
    def __init__(self, driver, default_timeout: int = 5):
        self.driver = driver
        self.default_timeout = default_timeout
        self.selectors = Plus500Selectors()
        # Performance optimization: cache successful selectors
        self._successful_selectors = {}
        self._selector_stats = {}
        
    def _update_selector_stats(self, selector_type: str, selector: str, success: bool) -> None:
        """Update statistics for selector performance tracking"""
        if selector_type not in self._selector_stats:
            self._selector_stats[selector_type] = {}
        if selector not in self._selector_stats[selector_type]:
            self._selector_stats[selector_type][selector] = {'success': 0, 'total': 0}
        
        stats = self._selector_stats[selector_type][selector]
        stats['total'] += 1
        if success:
            stats['success'] += 1
        
    def find_element_robust(self, selector_dict: Dict[str, List[str]], 
                           timeout: Optional[int] = None, 
                           wait_for_clickable: bool = False,
                           first_match_only: bool = True) -> Optional[WebElement]:
        """
        Try multiple selector strategies with comprehensive fallbacks
        
        Args:
            selector_dict: Dictionary with 'xpath' and 'css' keys containing selector lists
            timeout: Wait timeout (uses default if None)
            wait_for_clickable: Wait for element to be clickable instead of just present
            first_match_only: Exit at first successful match for efficiency
            
        Returns:
            WebElement if found, None otherwise
        """
        timeout = timeout or self.default_timeout
        
        # Strategy 1: Try all XPath selectors first (most reliable)
        element = self._try_xpath_selectors(selector_dict.get('xpath', []), timeout, wait_for_clickable, first_match_only)
        if element:
            logger.debug(f"Found element using XPath selector")
            print(f"Found element using XPath selector: {element}")
            return element
            
        # Strategy 2: Try all CSS selectors
        element = self._try_css_selectors(selector_dict.get('css', []), timeout//2, wait_for_clickable, first_match_only)
        if element:
            logger.debug(f"Found element using CSS selector")
            print(f"Found element using CSS selector: {element}")
            return element
            
        # Strategy 3: Try dynamic pattern generation
        element = self._try_dynamic_selectors(timeout//3)
        if element:
            logger.debug(f"Found element using dynamic selector")
            return element
            
        # Strategy 4: Try partial matches and fuzzy finding
        element = self._try_fuzzy_selectors(timeout//4)
        if element:
            logger.debug(f"Found element using fuzzy selector")
            return element
            
        logger.warning(f"Failed to find element with any selector strategy")
        return None
    
    def find_elements_robust(self, selector_dict: Dict[str, List[str]], 
                            timeout: Optional[int] = None) -> List[WebElement]:
        """Find multiple elements using robust strategies"""
        timeout = timeout or self.default_timeout
        elements = []
        
        # Try XPath selectors first
        for xpath in selector_dict.get('xpath', []):
            try:
                found_elements = WebDriverWait(self.driver, timeout//4).until(
                    EC.presence_of_all_elements_located((By.XPATH, xpath))
                )
                if found_elements:
                    elements.extend(found_elements)
            except TimeoutException:
                continue
                
        # Try CSS selectors if no XPath results
        if not elements:
            for css in selector_dict.get('css', []):
                try:
                    found_elements = WebDriverWait(self.driver, timeout//4).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, css))
                    )
                    if found_elements:
                        elements.extend(found_elements)
                except TimeoutException:
                    continue
                    
        return list(set(elements))  # Remove duplicates
    
    def wait_for_element_disappear(self, selector_dict: Dict[str, List[str]], 
                                  timeout: Optional[int] = None) -> bool:
        """Wait for element to disappear (useful for loading indicators)"""
        timeout = timeout or self.default_timeout
        
        for xpath in selector_dict.get('xpath', []):
            try:
                WebDriverWait(self.driver, timeout).until_not(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
                return True
            except TimeoutException:
                continue
                
        return False
    
    def safe_wait_for_element(self, selector_dict: Dict[str, List[str]], 
                        timeout: Optional[int] = None):
        """Wait for element to appear"""
        timeout = timeout or self.default_timeout
        for xpath in selector_dict.get('xpath', []):
            try:
                WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
                return True
            except TimeoutException:
                continue
        return False

    def is_element_present(self, selector_dict: Dict[str, List[str]]) -> bool:
        """Quick check if element exists (no wait)"""
        # Try XPath first
        for xpath in selector_dict.get('xpath', []):
            try:
                self.driver.find_element(By.XPATH, xpath)
                return True
            except NoSuchElementException:
                continue
                
        # Try CSS selectors
        for css in selector_dict.get('css', []):
            try:
                self.driver.find_element(By.CSS_SELECTOR, css)
                return True
            except NoSuchElementException:
                continue
                
        return False
    
    def wait_for_page_load(self, timeout: int = 10) -> bool:
        """Wait for page to fully load"""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            return True
        except TimeoutException:
            return False
    
    
    def find_element_from_selector(self, selector_dict: Dict[str, List[str]], 
                                   timeout: Optional[int] = None, 
                                   first_match_only: bool = False) -> Optional[WebElement]:
        """Find and return WebElement from selector dictionary"""
        if first_match_only:
            return self.find_first_element(selector_dict, timeout)
        return self.find_element_robust(selector_dict, timeout)

    def safe_click(self, selector_dict: Dict[str, List[str]], max_retries: int = 3, timeout: Optional[int] = None) -> bool:
        """Safely click element using selector dictionary"""
        element = self.find_element_from_selector(selector_dict)
        if not element:
            logger.error("Element not found for clicking")
            return False
        return self._safe_click_element(element, max_retries)
    
    def safe_send_keys(self, selector_dict: Dict[str, List[str]], text: str, clear_first: bool = True) -> bool:
        """Safely send keys to element using selector dictionary"""
        element = self.find_element_from_selector(selector_dict)
        if not element:
            logger.error("Element not found for sending keys")
            return False
        return self._safe_send_keys_to_element(element, text, clear_first)
    
    def _safe_click_element(self, element: WebElement, max_retries: int = 3) -> bool:
        """Safely click element with retries for stale elements"""
        for attempt in range(max_retries):
            try:
                # Wait for element to be clickable
                WebDriverWait(self.driver, 1).until(EC.element_to_be_clickable(element))
                
                # Scroll element into view
                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(0.1)
                
                # Click the element
                element.click()
                return True
                
            except (StaleElementReferenceException, ElementNotInteractableException) as e:
                logger.warning(f"Click attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                    
            except Exception as e:
                logger.error(f"Unexpected error during click: {e}")
                return False
                
        return False
    
    def _safe_send_keys_to_element(self, element: WebElement, text: str, clear_first: bool = True) -> bool:
        """Safely send keys to element with retries"""
        try:
            # Wait for element to be interactive
            WebDriverWait(self.driver, 2).until(EC.element_to_be_clickable(element))
            
            # Clear field if requested
            if clear_first:
                element.clear()
                time.sleep(0.2)
            
            # Send the text
            element.send_keys(text)
            return True
            
        except Exception as e:
            logger.error(f"Failed to send keys '{text}': {e}")
            return False
    
    def extract_text_safe(self, element: WebElement) -> str:
        """Safely extract text from element"""
        try:
            return element.text.strip()
        except StaleElementReferenceException:
            logger.warning("Element became stale while extracting text")
            return ""
        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            return ""
    
    def _try_xpath_selectors(self, xpaths: List[str], timeout: int, 
                            wait_for_clickable: bool = False, first_match_only: bool = True) -> Optional[WebElement]:
        """
        Try all XPath selectors in order with optimization for first match
        
        Args:
            xpaths: List of XPath selectors to try
            timeout: Total timeout for all selectors
            wait_for_clickable: Wait for element to be clickable instead of just present
            first_match_only: Exit immediately on first successful match
            
        Returns:
            WebElement if found, None otherwise
        """
        if first_match_only and self._successful_selectors.get('xpath'):
            # Try the previously successful selector first
            successful_xpath = self._successful_selectors['xpath']
            if successful_xpath in xpaths:
                xpaths = [successful_xpath] + [x for x in xpaths if x != successful_xpath]
        
        for i, xpath in enumerate(xpaths):
            # Calculate timeout per selector based on position and strategy
            if first_match_only:
                # Give more time to first few selectors
                selector_timeout = max(1, timeout // (i + 1))
            else:
                selector_timeout = timeout // len(xpaths)
                
            try:
                if wait_for_clickable:
                    element = WebDriverWait(self.driver, selector_timeout).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                else:
                    element = WebDriverWait(self.driver, selector_timeout).until(
                        EC.presence_of_element_located((By.XPATH, xpath))
                    )
                
                if element and element.is_displayed():
                    # Cache successful selector for future optimization
                    self._successful_selectors['xpath'] = xpath
                    self._update_selector_stats('xpath', xpath, True)
                    return element
                    
            except TimeoutException:
                self._update_selector_stats('xpath', xpath, False)
                continue
            except Exception as e:
                logger.debug(f"XPath selector '{xpath}' failed: {e}")
                self._update_selector_stats('xpath', xpath, False)
                continue
                
        return None
    
    def _try_css_selectors(self, css_selectors: List[str], timeout: int,
                          wait_for_clickable: bool = False, first_match_only: bool = True) -> Optional[WebElement]:
        """
        Try all CSS selectors in order with optimization for first match
        
        Args:
            css_selectors: List of CSS selectors to try
            timeout: Total timeout for all selectors
            wait_for_clickable: Wait for element to be clickable instead of just present
            first_match_only: Exit immediately on first successful match
            
        Returns:
            WebElement if found, None otherwise
        """
        if first_match_only and self._successful_selectors.get('css'):
            # Try the previously successful selector first
            successful_css = self._successful_selectors['css']
            if successful_css in css_selectors:
                css_selectors = [successful_css] + [c for c in css_selectors if c != successful_css]
        
        for i, css in enumerate(css_selectors):
            # Calculate timeout per selector based on position and strategy
            if first_match_only:
                # Give more time to first few selectors
                selector_timeout = max(1, timeout // (i + 1))
            else:
                selector_timeout = timeout // len(css_selectors)
                
            try:
                if wait_for_clickable:
                    element = WebDriverWait(self.driver, selector_timeout).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, css))
                    )
                else:
                    element = WebDriverWait(self.driver, selector_timeout).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, css))
                    )
                
                if element and element.is_displayed():
                    # Cache successful selector for future optimization
                    self._successful_selectors['css'] = css
                    self._update_selector_stats('css', css, True)
                    return element
                    
            except TimeoutException:
                self._update_selector_stats('css', css, False)
                continue
            except Exception as e:
                logger.debug(f"CSS selector '{css}' failed: {e}")
                self._update_selector_stats('css', css, False)
                continue
                
        return None
    
    def _try_dynamic_selectors(self, timeout: int) -> Optional[WebElement]:
        """Generate and try dynamic selectors based on common patterns"""
        dynamic_patterns = [
            # Button patterns
            "//button[contains(@onclick, 'buy') or contains(@data-action, 'buy')]",
            "//button[contains(@onclick, 'sell') or contains(@data-action, 'sell')]",
            "//button[contains(@class, 'btn') and (contains(text(), 'Buy') or contains(text(), 'Sell'))]",
            
            # Input patterns
            "//input[contains(@class, 'amount') or contains(@id, 'quantity')]",
            "//input[@type='number' and (contains(@placeholder, 'qty') or contains(@name, 'qty'))]",
            
            # Trading panel patterns
            "//div[contains(@class, 'trading-panel')]//button[1]",
            "//div[contains(@class, 'order-panel')]//input[@type='number']",
            
            # Generic clickable patterns
            "//button[contains(@class, 'primary') or contains(@class, 'action')]",
            "//*[@role='button' and contains(@class, 'trade')]"
        ]
        
        for pattern in dynamic_patterns:
            try:
                element = WebDriverWait(self.driver, timeout//len(dynamic_patterns)).until(
                    EC.presence_of_element_located((By.XPATH, pattern))
                )
                if element and element.is_displayed():
                    logger.debug(f"Found element with dynamic pattern: {pattern}")
                    return element
            except TimeoutException:
                continue
            except Exception:
                continue
                
        return None
    
    def _try_fuzzy_selectors(self, timeout: int) -> Optional[WebElement]:
        """Try fuzzy matching based on partial text and attributes"""
        fuzzy_patterns = [
            # Partial text matches
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'buy')]",
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'sell')]",
            "//input[contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'amount')]",
            
            # Attribute partial matches
            "//*[contains(@class, 'trade') or contains(@class, 'order')]//button",
            "//*[contains(@data-test, 'buy') or contains(@data-test, 'sell')]",
            "//*[contains(@aria-label, 'trade') or contains(@aria-label, 'order')]"
        ]
        
        for pattern in fuzzy_patterns:
            try:
                elements = self.driver.find_elements(By.XPATH, pattern)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        logger.debug(f"Found element with fuzzy pattern: {pattern}")
                        return element
            except Exception:
                continue
                
        return None
    
    def get_element_info(self, element: WebElement) -> Dict[str, Any]:
        """Get comprehensive information about an element for debugging"""
        try:
            return {
                'tag_name': element.tag_name,
                'text': element.text,
                'attributes': {
                    'id': element.get_attribute('id'),
                    'class': element.get_attribute('class'),
                    'name': element.get_attribute('name'),
                    'type': element.get_attribute('type'),
                    'data-test': element.get_attribute('data-test'),
                    'aria-label': element.get_attribute('aria-label')
                },
                'is_displayed': element.is_displayed(),
                'is_enabled': element.is_enabled(),
                'location': element.location,
                'size': element.size
            }
        except Exception as e:
            return {'error': str(e)}
    
    def stream_instrument_data(self, instrument_id: str, callback_func=None, poll_interval: int = 1) -> None:
        """
        Stream real-time price data for a specified instrument
        
        Args:
            instrument_id: Instrument identifier to monitor
            callback_func: Function to call with price updates
            poll_interval: Polling interval in seconds
        """
        logger.info(f"Starting real-time price streaming for instrument: {instrument_id}")
        
        last_price_data = None
        
        try:
            while True:
                # Get current price data from sidebar
                current_data = self._extract_current_price_data()
                
                if current_data and current_data != last_price_data:
                    logger.debug(f"Price update for {instrument_id}: {current_data}")
                    
                    if callback_func:
                        callback_func(instrument_id, current_data)
                    else:
                        # Default logging if no callback
                        logger.info(f"Price update: {current_data}")
                    
                    last_price_data = current_data
                
                time.sleep(poll_interval)
                
        except KeyboardInterrupt:
            logger.info(f"Price streaming stopped by user for {instrument_id}")
        except Exception as e:
            logger.error(f"Price streaming failed for {instrument_id}: {e}")
    
    def _extract_current_price_data(self) -> Optional[Dict[str, Any]]:
        """
        Extract current price data from the sidebar
        
        Returns:
            Dictionary with current price information or None
        """
        try:
            from .selectors import Plus500Selectors
            selectors = Plus500Selectors()
            
            # Find the sidebar container
            sidebar = self.find_element_from_selector(
                selectors.SIDEBAR_CONTAINER, timeout=2
            )
            
            if not sidebar:
                return None
            
            price_data = {
                'timestamp': time.time()
            }
            
            # Extract buy/sell prices from Trade tab
            try:
                # Make sure we're on Trade tab
                self.navigate_to_trade_tab()
                
                # Extract sell price
                sell_element = self.find_element_from_selector(
                    selectors.INSTRUMENT_SELL_PRICE, timeout=1
                )
                if sell_element:
                    sell_price = self._parse_price_from_text(
                        self.extract_text_safe(sell_element)
                    )
                    if sell_price is not None:
                        price_data['sell_price'] = sell_price
                
                # Extract buy price
                buy_element = self.find_element_from_selector(
                    selectors.INSTRUMENT_BUY_PRICE, timeout=1
                )
                if buy_element:
                    buy_price = self._parse_price_from_text(
                        self.extract_text_safe(buy_element)
                    )
                    if buy_price is not None:
                        price_data['buy_price'] = buy_price
                
            except Exception as e:
                logger.debug(f"Failed to extract trade tab prices: {e}")
            
            # Extract live statistics from Info tab
            try:
                # Switch to Info tab
                self.navigate_to_info_tab()
                
                # Extract 5min change
                change_5min_element = self.find_element_from_selector(
                    selectors.CHANGE_5MIN, timeout=1
                )
                if change_5min_element:
                    change_5min = self._parse_percentage_from_text(
                        self.extract_text_safe(change_5min_element)
                    )
                    if change_5min is not None:
                        price_data['change_5min'] = change_5min
                
                # Extract 1hour change
                change_1hour_element = self.find_element_from_selector(
                    selectors.CHANGE_1HOUR, timeout=1
                )
                if change_1hour_element:
                    change_1hour = self._parse_percentage_from_text(
                        self.extract_text_safe(change_1hour_element)
                    )
                    if change_1hour is not None:
                        price_data['change_1hour'] = change_1hour
                
                # Extract 1day change
                change_1day_element = self.find_element_from_selector(
                    selectors.CHANGE_1DAY, timeout=1
                )
                if change_1day_element:
                    change_1day = self._parse_percentage_from_text(
                        self.extract_text_safe(change_1day_element)
                    )
                    if change_1day is not None:
                        price_data['change_1day'] = change_1day
                
            except Exception as e:
                logger.debug(f"Failed to extract info tab data: {e}")
            
            return price_data if len(price_data) > 1 else None  # Return only if we have actual data
            
        except Exception as e:
            logger.debug(f"Failed to extract current price data: {e}")
            return None
    
    def navigate_to_trade_tab(self) -> bool:
        """
        Navigate to the Trade tab in the sidebar
        
        Returns:
            True if successful
        """
        try:
            from .selectors import Plus500Selectors
            from .utils import WebDriverUtils
            
            selectors = Plus500Selectors()
            utils = WebDriverUtils()
            
            trade_tab = self.find_element_from_selector(
                selectors.TRADE_TAB, timeout=3
            )
            
            if trade_tab:
                utils.human_like_click(self.driver, trade_tab)
                time.sleep(0.5)
                return True
                
            return False
            
        except Exception as e:
            logger.debug(f"Failed to navigate to Trade tab: {e}")
            return False
    
    def navigate_to_info_tab(self) -> bool:
        """
        Navigate to the Info tab in the sidebar
        
        Returns:
            True if successful
        """
        try:
            from .selectors import Plus500Selectors
            from .utils import WebDriverUtils
            
            selectors = Plus500Selectors()
            utils = WebDriverUtils()
            
            info_tab = self.find_element_from_selector(
                selectors.INFO_TAB, timeout=3
            )
            
            if info_tab:
                utils.human_like_click(self.driver, info_tab)
                time.sleep(0.5)
                return True
                
            return False
            
        except Exception as e:
            logger.debug(f"Failed to navigate to Info tab: {e}")
            return False
    
    def _parse_price_from_text(self, text: str) -> Optional[float]:
        """
        Parse price value from text
        
        Args:
            text: Text containing price
            
        Returns:
            Price as float or None
        """
        if not text:
            return None
        
        try:
            import re
            # Remove commas and whitespace
            cleaned = re.sub(r'[,\s]', '', text.strip())
            
            # Extract numeric value
            match = re.search(r'(\d+\.?\d*)', cleaned)
            if match:
                return float(match.group(1))
            
            return None
            
        except Exception:
            return None
    
    def _parse_percentage_from_text(self, text: str) -> Optional[float]:
        """
        Parse percentage value from text
        
        Args:
            text: Text containing percentage
            
        Returns:
            Percentage as float or None
        """
        if not text:
            return None
        
        try:
            # Remove % symbol and whitespace
            cleaned = text.replace('%', '').replace('\u200e', '').strip()
            
            # Handle negative values
            if cleaned.startswith('-'):
                return -float(cleaned[1:])
            else:
                return float(cleaned)
            
        except Exception:
            return None
    
    def find_first_element(self, selector_dict: Dict[str, List[str]], 
                          timeout: Optional[int] = None) -> Optional[WebElement]:
        """
        Optimized element finder that returns immediately on first match
        
        Args:
            selector_dict: Dictionary with 'xpath' and 'css' keys containing selector lists
            timeout: Wait timeout (uses default if None)
            
        Returns:
            WebElement if found, None otherwise
        """
        timeout = timeout or self.default_timeout
        
        # Strategy 1: Try XPath selectors with early return
        element = self._try_xpath_selectors_optimized(selector_dict.get('xpath', []), timeout)
        if element:
            logger.debug(f"Found element using optimized XPath selector")
            return element
            
        # Strategy 2: Try CSS selectors with early return
        element = self._try_css_selectors_optimized(selector_dict.get('css', []), timeout//2)
        if element:
            logger.debug(f"Found element using optimized CSS selector")
            return element
            
        # Strategy 3: Quick fallback selectors
        element = self._try_quick_fallback_selectors(timeout//3)
        if element:
            logger.debug(f"Found element using quick fallback selector")
            return element
            
        logger.warning(f"Failed to find element with optimized selectors")
        return None
    
    def _try_xpath_selectors_optimized(self, xpaths: List[str], timeout: int) -> Optional[WebElement]:
        """Try XPath selectors with immediate return on first match and smart caching"""
        # Reorder selectors based on success history
        ordered_xpaths = self._get_prioritized_selectors(xpaths, 'xpath')
        
        for xpath in ordered_xpaths:
            try:
                element = WebDriverWait(self.driver, timeout//len(ordered_xpaths) if len(ordered_xpaths) > 0 else timeout).until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
                
                if element and element.is_displayed():
                    logger.debug(f"Found element with optimized XPath: {xpath}")
                    # Cache successful selector for future use
                    self._record_successful_selector(xpath, 'xpath')
                    return element
                    
            except TimeoutException:
                continue
            except Exception as e:
                logger.debug(f"Optimized XPath selector '{xpath}' failed: {e}")
                continue
                
        return None
    
    def _try_css_selectors_optimized(self, css_selectors: List[str], timeout: int) -> Optional[WebElement]:
        """Try CSS selectors with immediate return on first match"""
        for css in css_selectors:
            try:
                element = WebDriverWait(self.driver, timeout//len(css_selectors) if len(css_selectors) > 0 else timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, css))
                )
                
                if element and element.is_displayed():
                    logger.debug(f"Found element with optimized CSS: {css}")
                    return element
                    
            except TimeoutException:
                continue
            except Exception as e:
                logger.debug(f"Optimized CSS selector '{css}' failed: {e}")
                continue
                
        return None
    
    def _try_quick_fallback_selectors(self, timeout: int) -> Optional[WebElement]:
        """Try quick fallback selectors for common patterns"""
        quick_patterns = [
            # Most common button patterns first
            "//button[contains(@class, 'btn-primary')]",
            "//button[contains(@onclick, 'buy')]",
            "//button[contains(@onclick, 'sell')]",
            "//input[@type='number'][1]",
            "//div[contains(@class, 'trading-panel')]//button[1]"
        ]
        
        for pattern in quick_patterns:
            try:
                element = WebDriverWait(self.driver, timeout//len(quick_patterns)).until(
                    EC.presence_of_element_located((By.XPATH, pattern))
                )
                if element and element.is_displayed():
                    logger.debug(f"Found element with quick fallback: {pattern}")
                    return element
            except TimeoutException:
                continue
            except Exception:
                continue
                
        return None
    
    def _get_prioritized_selectors(self, selectors: List[str], selector_type: str) -> List[str]:
        """Reorder selectors based on success history"""
        if not selectors:
            return selectors
            
        # Sort by success rate (successful selectors first)
        def selector_priority(selector):
            stats = self._selector_stats.get(f"{selector_type}:{selector}", {'success': 0, 'attempts': 0})
            if stats['attempts'] == 0:
                return 0.5  # Unknown selectors get medium priority
            return stats['success'] / stats['attempts']
        
        return sorted(selectors, key=selector_priority, reverse=True)
    
    def _record_successful_selector(self, selector: str, selector_type: str):
        """Record successful selector usage for performance optimization"""
        key = f"{selector_type}:{selector}"
        if key not in self._selector_stats:
            self._selector_stats[key] = {'success': 0, 'attempts': 0}
        
        self._selector_stats[key]['success'] += 1
        self._selector_stats[key]['attempts'] += 1
        
        # Keep cache size manageable
        if len(self._selector_stats) > 100:
            # Remove oldest entries
            sorted_by_usage = sorted(self._selector_stats.items(), 
                                   key=lambda x: x[1]['attempts'])
            for key, _ in sorted_by_usage[:20]:  # Remove bottom 20%
                del self._selector_stats[key]