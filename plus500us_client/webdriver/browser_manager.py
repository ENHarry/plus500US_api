from __future__ import annotations
import os
import time
import random
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.common.exceptions import WebDriverException

try:
    import undetected_chromedriver as uc
    UNDETECTED_CHROME_AVAILABLE = True
except ImportError:
    UNDETECTED_CHROME_AVAILABLE = False

try:
    from webdriver_manager.chrome import ChromeDriverManager
    from webdriver_manager.firefox import GeckoDriverManager
    from webdriver_manager.microsoft import EdgeChromiumDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False

logger = logging.getLogger(__name__)

class BrowserManager:
    """Advanced browser management with anti-detection and stealth features"""
    
    def __init__(self, config):
        from ..config import Config
        
        if isinstance(config, Config):
            # Extract webdriver config from Config object
            self.config = config.webdriver_config
            self.main_config = config
        else:
            # Assume it's a webdriver config dict
            self.config = config
            self.main_config = None
            
        self.driver: Optional[webdriver.Remote] = None
        self.profile_path = Path(self.config.get('profile_path', Path.home() / '.plus500_profile'))
        self.browser_type = self.config.get('browser', 'chrome').lower()
        self.headless = self.config.get('headless', False)
        self.stealth_mode = self.config.get('stealth_mode', True)
        self.window_size = self.config.get('window_size', (1920, 1080))
        self.implicit_wait = self.config.get('implicit_wait', 10)
        self.page_load_timeout = self.config.get('page_load_timeout', 30)
        
    def start_browser(self) -> webdriver.Remote:
        """Start browser with anti-detection features"""
        if self.driver:
            logger.warning("Browser already started")
            return self.driver
            
        logger.info(f"Starting {self.browser_type} browser (headless: {self.headless})")
        
        try:
            if self.browser_type == 'chrome':
                self.driver = self._start_chrome()
            elif self.browser_type == 'firefox':
                self.driver = self._start_firefox()
            elif self.browser_type == 'edge':
                self.driver = self._start_edge()
            else:
                raise ValueError(f"Unsupported browser: {self.browser_type}. Supported: chrome, firefox, edge")
                
            # Configure driver timeouts
            self.driver.implicitly_wait(self.implicit_wait)
            self.driver.set_page_load_timeout(self.page_load_timeout)
            
            # Set window size
            if not self.headless:
                self.driver.set_window_size(*self.window_size)
                
            # Apply stealth modifications
            if self.stealth_mode:
                self._apply_stealth_modifications()
                
            logger.info("Browser started successfully")
            return self.driver
            
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            raise
    
    def stop_browser(self) -> None:
        """Safely stop the browser"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser stopped successfully")
            except Exception as e:
                logger.warning(f"Error stopping browser: {e}")
            finally:
                self.driver = None
    
    def restart_browser(self) -> webdriver.Remote:
        """Restart the browser (useful for clearing state)"""
        self.stop_browser()
        time.sleep(2)  # Give time for cleanup
        return self.start_browser()
    
    def get_driver(self) -> webdriver.Remote:
        """Get the current driver instance"""
        if not self.driver:
            raise RuntimeError("Browser not started. Call start_browser() first.")
        return self.driver
    
    def is_browser_alive(self) -> bool:
        """Check if browser is still responsive"""
        if not self.driver:
            return False
            
        try:
            # Try to get current URL as a health check
            self.driver.current_url
            return True
        except Exception:
            return False
    
    def _start_chrome(self) -> webdriver.Chrome:
        """Start Chrome with optimized options"""
        options = ChromeOptions()
        
        # Basic options
        if self.headless:
            options.add_argument('--headless=new')
        
        # Profile and user data
        if self.profile_path.exists():
            options.add_argument(f'--user-data-dir={self.profile_path}')
        
        # Anti-detection options
        if self.stealth_mode:
            stealth_args = [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-extensions-file-access-check',
                '--disable-extensions-http-throttling',
                '--disable-extensions-https-everywhere',
                '--disable-web-security',
                '--allow-running-insecure-content',
                '--disable-features=VizDisplayCompositor',
                '--disable-ipc-flooding-protection',
                '--disable-renderer-backgrounding',
                '--disable-backgrounding-occluded-windows',
                '--disable-field-trial-config',
                '--disable-back-forward-cache',
                '--disable-hang-monitor',
                '--disable-prompt-on-repost',
                '--disable-sync',
                '--metrics-recording-only',
                '--no-first-run',
                '--safebrowsing-disable-auto-update',
                '--enable-automation=false',
                '--password-store=basic',
                '--use-mock-keychain'
            ]
            
            for arg in stealth_args:
                options.add_argument(arg)
        
        # Randomize user agent
        user_agent = self._get_random_user_agent()
        options.add_argument(f'--user-agent={user_agent}')
        
        # Window size for headless mode
        if self.headless:
            options.add_argument(f'--window-size={self.window_size[0]},{self.window_size[1]}')
        
        # Exclude automation switches
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Performance options
        prefs = {
            "profile.default_content_setting_values": {
                "notifications": 2,  # Block notifications
                "popups": 2,  # Block popups
            },
            "profile.managed_default_content_settings": {
                "images": 2  # Don't load images for faster loading
            } if self.config.get('disable_images', False) else {}
        }
        options.add_experimental_option("prefs", prefs)
        
        # Try undetected Chrome first if available
        if UNDETECTED_CHROME_AVAILABLE and self.stealth_mode:
            try:
                logger.info("Using undetected Chrome driver")
                driver = uc.Chrome(
                    options=options,
                    version_main=None,  # Auto-detect Chrome version
                    user_data_dir=str(self.profile_path) if self.profile_path.exists() else None
                )
                return driver
            except Exception as e:
                logger.warning(f"Undetected Chrome failed, falling back to regular Chrome: {e}")
        
        # Fallback to regular Chrome
        service = None
        if WEBDRIVER_MANAGER_AVAILABLE:
            try:
                service = ChromeService(ChromeDriverManager().install())
            except Exception as e:
                logger.warning(f"WebDriver Manager failed: {e}")
        
        return webdriver.Chrome(service=service, options=options)
    
    def _start_firefox(self) -> webdriver.Firefox:
        """Start Firefox with optimized options"""
        options = FirefoxOptions()
        
        if self.headless:
            options.add_argument('--headless')
        
        # Profile setup
        if self.profile_path.exists():
            options.add_argument(f'--profile={self.profile_path}')
        
        # Anti-detection preferences
        if self.stealth_mode:
            prefs = {
                'dom.webdriver.enabled': False,
                'useAutomationExtension': False,
                'general.useragent.override': self._get_random_user_agent(),
                'dom.webnotifications.enabled': False,
                'media.peerconnection.enabled': False
            }
            
            for key, value in prefs.items():
                options.set_preference(key, value)
        
        service = None
        if WEBDRIVER_MANAGER_AVAILABLE:
            try:
                service = FirefoxService(GeckoDriverManager().install())
            except Exception as e:
                logger.warning(f"WebDriver Manager failed: {e}")
        
        return webdriver.Firefox(service=service, options=options)
    
    def _start_edge(self) -> webdriver.Edge:
        """Start Microsoft Edge with optimized options"""
        options = EdgeOptions()
        
        # Basic options
        if self.headless:
            options.add_argument('--headless=new')
        
        # Profile and user data
        if self.profile_path.exists():
            options.add_argument(f'--user-data-dir={self.profile_path}')
        
        # Anti-detection options (similar to Chrome)
        if self.stealth_mode:
            stealth_args = [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-extensions-file-access-check',
                '--disable-web-security',
                '--allow-running-insecure-content',
                '--disable-features=VizDisplayCompositor',
                '--disable-ipc-flooding-protection',
                '--disable-renderer-backgrounding',
                '--disable-backgrounding-occluded-windows',
                '--disable-field-trial-config',
                '--disable-back-forward-cache',
                '--disable-hang-monitor',
                '--disable-prompt-on-repost',
                '--disable-sync',
                '--metrics-recording-only',
                '--no-first-run',
                '--safebrowsing-disable-auto-update',
                '--enable-automation=false',
                '--password-store=basic',
                '--use-mock-keychain'
            ]
            
            for arg in stealth_args:
                options.add_argument(arg)
        
        # Randomize user agent
        user_agent = self._get_random_user_agent()
        options.add_argument(f'--user-agent={user_agent}')
        
        # Window size for headless mode
        if self.headless:
            options.add_argument(f'--window-size={self.window_size[0]},{self.window_size[1]}')
        
        # Exclude automation switches
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Performance options
        prefs = {
            "profile.default_content_setting_values": {
                "notifications": 2,  # Block notifications
                "popups": 2,  # Block popups
            },
            "profile.managed_default_content_settings": {
                "images": 2  # Don't load images for faster loading
            } if self.config.get('disable_images', False) else {}
        }
        options.add_experimental_option("prefs", prefs)
        
        service = None
        if WEBDRIVER_MANAGER_AVAILABLE:
            try:
                service = EdgeService(EdgeChromiumDriverManager().install())
            except Exception as e:
                logger.warning(f"WebDriver Manager failed: {e}")
        
        return webdriver.Edge(service=service, options=options)
    
    def _apply_stealth_modifications(self) -> None:
        """Apply JavaScript-based stealth modifications"""
        if not self.driver:
            return
            
        stealth_scripts = [
            # Remove webdriver property
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
            
            # Randomize navigator properties
            f"Object.defineProperty(navigator, 'userAgent', {{get: () => '{self._get_random_user_agent()}'}})",
            
            # Modify plugins
            """
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5].map(() => ({
                    0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                    description: "Portable Document Format",
                    filename: "internal-pdf-viewer",
                    length: 1,
                    name: "Chrome PDF Plugin"
                }))
            });
            """,
            
            # Modify languages
            "Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})",
            
            # Mock permissions
            """
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
            );
            """
        ]
        
        for script in stealth_scripts:
            try:
                self.driver.execute_script(script)
            except Exception as e:
                logger.debug(f"Failed to execute stealth script: {e}")
    
    def _get_random_user_agent(self) -> str:
        """Get a random realistic user agent"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0"
        ]
        return random.choice(user_agents)
    
    def simulate_human_behavior(self) -> None:
        """Simulate random human-like behavior"""
        if not self.driver:
            return
            
        # Random mouse movements
        try:
            # Move to random positions
            for _ in range(random.randint(1, 3)):
                x = random.randint(100, self.window_size[0] - 100)
                y = random.randint(100, self.window_size[1] - 100)
                self.driver.execute_script(f"""
                    var event = new MouseEvent('mousemove', {{
                        'view': window,
                        'bubbles': true,
                        'cancelable': true,
                        'clientX': {x},
                        'clientY': {y}
                    }});
                    document.dispatchEvent(event);
                """)
                time.sleep(random.uniform(0.1, 0.5))
                
        except Exception as e:
            logger.debug(f"Human behavior simulation failed: {e}")
    
    def random_delay(self, min_seconds: float = 0.5, max_seconds: float = 2.0) -> None:
        """Add random delay to simulate human behavior"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
    
    def scroll_randomly(self) -> None:
        """Perform random scrolling to simulate reading"""
        if not self.driver:
            return
            
        try:
            # Random scroll amount
            scroll_amount = random.randint(100, 500)
            direction = random.choice(['up', 'down'])
            
            if direction == 'down':
                self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            else:
                self.driver.execute_script(f"window.scrollBy(0, -{scroll_amount});")
                
            self.random_delay(0.5, 1.5)
            
        except Exception as e:
            logger.debug(f"Random scroll failed: {e}")
    
    def take_screenshot(self, filename: Optional[str] = None) -> str:
        """Take a screenshot for debugging"""
        if not self.driver:
            raise RuntimeError("Browser not started")
            
        if not filename:
            timestamp = int(time.time())
            filename = f"screenshot_{timestamp}.png"
            
        filepath = Path(filename)
        self.driver.save_screenshot(str(filepath))
        logger.info(f"Screenshot saved: {filepath}")
        return str(filepath)
    
    def get_browser_info(self) -> Dict[str, Any]:
        """Get information about the current browser session"""
        if not self.driver:
            return {"status": "not_started"}
            
        try:
            return {
                "status": "running",
                "current_url": self.driver.current_url,
                "title": self.driver.title,
                "window_size": self.driver.get_window_size(),
                "user_agent": self.driver.execute_script("return navigator.userAgent;"),
                "cookies_count": len(self.driver.get_cookies()),
                "browser_type": self.browser_type,
                "headless": self.headless,
                "stealth_mode": self.stealth_mode
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def clear_browser_data(self) -> None:
        """Clear browser data (cookies, local storage, etc.)"""
        if not self.driver:
            return
            
        try:
            # Clear cookies
            self.driver.delete_all_cookies()
            
            # Clear local storage and session storage
            self.driver.execute_script("window.localStorage.clear();")
            self.driver.execute_script("window.sessionStorage.clear();")
            
            logger.info("Browser data cleared")
            
        except Exception as e:
            logger.warning(f"Failed to clear browser data: {e}")

    def wait_for_page_load(self, timeout: int = 30) -> bool:
        """
        Wait for page to fully load
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if page loaded successfully
        """
        if not self.driver:
            return False
            
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            # Wait for document ready state
            wait = WebDriverWait(self.driver, timeout)
            wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
            
            # Additional wait for JavaScript to complete
            time.sleep(2)
            
            return True
            
        except Exception as e:
            logger.warning(f"Page load wait failed: {e}")
            return False
    
    def __enter__(self):
        """Context manager entry"""
        return self.start_browser()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop_browser()