from __future__ import annotations
import time
import random
import logging
from typing import Any, Optional, Dict, List
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import WebDriverException

logger = logging.getLogger(__name__)

class WebDriverUtils:
    """Utility functions for WebDriver automation"""
    
    @staticmethod
    def human_like_click(driver, element: WebElement, 
                        random_offset: bool = True, delay_range: tuple = (0.1, 0.5)) -> bool:
        """
        Perform human-like click with random timing and movement
        
        Args:
            driver: WebDriver instance
            element: Element to click
            random_offset: Add random offset to click position
            delay_range: Range for random delay before click
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Random delay before action
            delay = random.uniform(*delay_range)
            time.sleep(delay)
            
            # Scroll element into view
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.2)
            
            # Get element location and size
            location = element.location
            size = element.size
            
            # Create action chain
            actions = ActionChains(driver)
            
            if random_offset:
                # Calculate random offset within element bounds
                offset_x = random.randint(-size['width']//4, size['width']//4)
                offset_y = random.randint(-size['height']//4, size['height']//4)
                actions.move_to_element_with_offset(element, offset_x, offset_y)
            else:
                actions.move_to_element(element)
            
            # Random pause before click
            time.sleep(random.uniform(0.1, 0.3))
            
            # Perform click
            actions.click().perform()
            
            # Small delay after click
            time.sleep(random.uniform(0.1, 0.2))
            
            return True
            
        except Exception as e:
            logger.error(f"Human-like click failed: {e}")
            return False
    
    @staticmethod
    def human_like_type(driver, element: WebElement, text: str,
                       typing_speed: tuple = (0.05, 0.15), clear_first: bool = True) -> bool:
        """
        Type text with human-like timing
        
        Args:
            driver: WebDriver instance
            element: Input element
            text: Text to type
            typing_speed: Range for delay between keystrokes
            clear_first: Clear field before typing
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Click element first
            element.click()
            time.sleep(0.2)
            
            # Clear field if requested
            if clear_first:
                element.clear()
                time.sleep(0.1)
            
            # Type with human-like timing
            for char in text:
                element.send_keys(char)
                delay = random.uniform(*typing_speed)
                time.sleep(delay)
            
            return True
            
        except Exception as e:
            logger.error(f"Human-like typing failed: {e}")
            return False
    
    @staticmethod
    def wait_for_element_stable(driver, element: WebElement, 
                               stability_time: float = 1.0, max_wait: float = 10.0) -> bool:
        """
        Wait for element to be stable (not moving/changing)
        
        Args:
            driver: WebDriver instance
            element: Element to monitor
            stability_time: Time element must be stable
            max_wait: Maximum wait time
            
        Returns:
            True if element became stable, False if timeout
        """
        start_time = time.time()
        last_location = None
        last_size = None
        stable_since = None
        
        while time.time() - start_time < max_wait:
            try:
                current_location = element.location
                current_size = element.size
                
                if (current_location == last_location and 
                    current_size == last_size and
                    last_location is not None):
                    
                    if stable_since is None:
                        stable_since = time.time()
                    elif time.time() - stable_since >= stability_time:
                        return True
                else:
                    stable_since = None
                
                last_location = current_location
                last_size = current_size
                time.sleep(0.1)
                
            except Exception:
                time.sleep(0.1)
                continue
        
        return False
    
    @staticmethod
    def smart_scroll_to_element(driver, element: WebElement, 
                               offset_from_top: int = 100) -> bool:
        """
        Scroll to element with optimal positioning
        
        Args:
            driver: WebDriver instance
            element: Element to scroll to
            offset_from_top: Pixels from top of viewport
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get element position
            element_y = element.location['y']
            
            # Calculate scroll position
            scroll_y = element_y - offset_from_top
            
            # Perform scroll
            driver.execute_script(f"window.scrollTo(0, {scroll_y});")
            time.sleep(0.5)
            
            # Verify element is visible
            return element.is_displayed()
            
        except Exception as e:
            logger.error(f"Smart scroll failed: {e}")
            return False
    
    @staticmethod
    def extract_number_from_text(text: str) -> Optional[float]:
        """
        Extract numeric value from text string
        
        Args:
            text: Text containing number
            
        Returns:
            Extracted number or None if not found
        """
        import re
        
        if not text:
            return None
        
        # Remove currency symbols and common prefixes
        cleaned = re.sub(r'[\$£€¥₹,\s]', '', text.strip())
        
        # Extract number (including decimals)
        number_match = re.search(r'[-+]?(\d+\.?\d*|\.\d+)', cleaned)
        
        if number_match:
            try:
                return float(number_match.group())
            except ValueError:
                pass
        
        return None
    
    @staticmethod
    def parse_percentage(text: str) -> Optional[float]:
        """
        Parse percentage from text
        
        Args:
            text: Text containing percentage
            
        Returns:
            Percentage as decimal (e.g., 5% -> 0.05) or None
        """
        if not text:
            return None
        
        # Remove spaces and extract number before %
        cleaned = text.replace(' ', '')
        
        import re
        match = re.search(r'([-+]?\d+\.?\d*)%', cleaned)
        
        if match:
            try:
                percentage = float(match.group(1))
                return percentage / 100.0
            except ValueError:
                pass
        
        return None
    
    @staticmethod
    def wait_for_page_ready(driver, timeout: int = 30) -> bool:
        """
        Wait for page to be completely ready
        
        Args:
            driver: WebDriver instance
            timeout: Maximum wait time
            
        Returns:
            True if page is ready, False if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check document ready state
                ready_state = driver.execute_script("return document.readyState")
                
                # Check for jQuery if present
                jquery_ready = driver.execute_script("""
                    if (typeof jQuery !== 'undefined') {
                        return jQuery.active === 0;
                    }
                    return true;
                """)
                
                # Check for active requests (if XMLHttpRequest is tracked)
                no_active_requests = driver.execute_script("""
                    if (window.activeRequests !== undefined) {
                        return window.activeRequests === 0;
                    }
                    return true;
                """)
                
                if (ready_state == "complete" and 
                    jquery_ready and 
                    no_active_requests):
                    return True
                    
            except Exception:
                pass
            
            time.sleep(0.5)
        
        return False
    
    @staticmethod
    def capture_element_screenshot(driver, element: WebElement, 
                                 filename: Optional[str] = None) -> Optional[str]:
        """
        Capture screenshot of specific element
        
        Args:
            driver: WebDriver instance
            element: Element to capture
            filename: Optional filename
            
        Returns:
            Filename of screenshot or None if failed
        """
        try:
            if filename is None:
                filename = f"element_screenshot_{int(time.time())}.png"
            
            # Take element screenshot
            element.screenshot(filename)
            logger.info(f"Element screenshot saved: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Element screenshot failed: {e}")
            return None
    
    @staticmethod
    def get_element_xpath(driver, element: WebElement) -> Optional[str]:
        """
        Get XPath of element for debugging
        
        Args:
            driver: WebDriver instance
            element: Element to get XPath for
            
        Returns:
            XPath string or None if failed
        """
        try:
            xpath = driver.execute_script("""
                function getXPath(element) {
                    if (element.id !== '') {
                        return "//*[@id='" + element.id + "']";
                    }
                    if (element === document.body) {
                        return '/html/body';
                    }
                    var ix = 0;
                    var siblings = element.parentNode.childNodes;
                    for (var i = 0; i < siblings.length; i++) {
                        var sibling = siblings[i];
                        if (sibling === element) {
                            return getXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                        }
                        if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {
                            ix++;
                        }
                    }
                }
                return getXPath(arguments[0]);
            """, element)
            
            return xpath
            
        except Exception as e:
            logger.error(f"XPath extraction failed: {e}")
            return None
    
    @staticmethod
    def monitor_network_activity(driver, timeout: int = 10) -> Dict[str, Any]:
        """
        Monitor network activity (requires Chrome with logging enabled)
        
        Args:
            driver: WebDriver instance
            timeout: Monitoring duration
            
        Returns:
            Network activity summary
        """
        try:
            # Enable network logging (Chrome only)
            driver.execute_cdp_cmd('Network.enable', {})
            
            start_time = time.time()
            requests_count = 0
            errors_count = 0
            
            # Monitor for specified timeout
            while time.time() - start_time < timeout:
                logs = driver.get_log('performance')
                
                for log in logs:
                    message = log.get('message', {})
                    if isinstance(message, str):
                        import json
                        try:
                            message = json.loads(message)
                        except:
                            continue
                    
                    method = message.get('method', '')
                    
                    if method == 'Network.requestWillBeSent':
                        requests_count += 1
                    elif method == 'Network.loadingFailed':
                        errors_count += 1
                
                time.sleep(0.1)
            
            return {
                'duration': timeout,
                'requests_count': requests_count,
                'errors_count': errors_count,
                'requests_per_second': requests_count / timeout
            }
            
        except Exception as e:
            logger.error(f"Network monitoring failed: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def detect_loading_state(driver) -> Dict[str, bool]:
        """
        Detect various loading states on the page
        
        Args:
            driver: WebDriver instance
            
        Returns:
            Dictionary of loading state indicators
        """
        try:
            states = {}
            
            # Check for common loading indicators
            loading_selectors = [
                ".loading",
                ".spinner", 
                ".progress",
                "[data-loading='true']",
                ".overlay.loading"
            ]
            
            for selector in loading_selectors:
                try:
                    elements = driver.find_elements("css selector", selector)
                    states[f"loading_{selector.replace('.', '').replace('[', '').replace(']', '')}"] = any(
                        el.is_displayed() for el in elements
                    )
                except:
                    states[f"loading_{selector.replace('.', '').replace('[', '').replace(']', '')}"] = False
            
            # Check JavaScript loading state
            try:
                states['document_ready'] = driver.execute_script("return document.readyState === 'complete'")
                states['jquery_ready'] = driver.execute_script("""
                    if (typeof jQuery !== 'undefined') {
                        return jQuery.active === 0;
                    }
                    return true;
                """)
            except:
                states['document_ready'] = False
                states['jquery_ready'] = True
            
            return states
            
        except Exception as e:
            logger.error(f"Loading state detection failed: {e}")
            return {'error': str(e)}
        
        