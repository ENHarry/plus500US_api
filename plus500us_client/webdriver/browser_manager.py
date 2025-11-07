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
    uc = None
    UNDETECTED_CHROME_AVAILABLE = False

try:
    from webdriver_manager.chrome import ChromeDriverManager
    from webdriver_manager.firefox import GeckoDriverManager
    from webdriver_manager.microsoft import EdgeChromiumDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False

from .performance_monitor import get_optimizer, get_profiler, monitor_performance, StartupOptimizer
from ..security import secure_logger

logger = secure_logger(__name__)

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
        self.service: Optional[Any] = None  # Track service for cleanup
        self.driver_id: Optional[str] = None  # Unique ID for tracking
        self.profile_path = Path(self.config.get('profile_path', Path.home() / '.plus500_profile'))
        self.browser_type = self.config.get('browser', 'chrome').lower()
        self.headless = self.config.get('headless', False)
        self.stealth_mode = self.config.get('stealth_mode', True)
        self.window_size = self.config.get('window_size', (1920, 1080))
        self.implicit_wait = self.config.get('implicit_wait', 10)
        self.page_load_timeout = self.config.get('page_load_timeout', 30)
        self.performance_mode = self.config.get('performance_mode', False)
        
        # Get optimizer instance
        self.optimizer = get_optimizer()
        
    @monitor_performance("browser_startup")
    def start_browser(self) -> webdriver.Remote:
        """Start browser with anti-detection features and performance optimization"""
        if self.driver:
            logger.warning("Browser already started")
            return self.driver
            
        # Apply performance optimizations if enabled
        if self.performance_mode:
            self._apply_performance_optimizations()
            
        logger.info(f"Starting {self.browser_type} browser (headless: {self.headless}, performance: {self.performance_mode})")
        
        try:
            if self.browser_type == 'chrome':
                self.driver = self._start_chrome()
            elif self.browser_type == 'firefox':
                self.driver = self._start_firefox()
            elif self.browser_type == 'edge':
                self.driver = self._start_edge()
            elif self.browser_type == 'safari':
                self.driver = self._start_safari()
            elif self.browser_type == 'opera':
                self.driver = self._start_opera()
            else:
                raise ValueError(f"Unsupported browser: {self.browser_type}. Supported: chrome, firefox, edge, safari, opera")
                
            # Register driver for cleanup
            self.driver_id = f"{self.browser_type}_{int(time.time())}"
            self.optimizer.register_driver(self.driver_id, self.driver, self.service)
                
            # Configure driver timeouts
            self.driver.implicitly_wait(self.implicit_wait)
            self.driver.set_page_load_timeout(self.page_load_timeout)
            
            # Set window size
            if not self.headless:
                width, height = self.window_size
                self.driver.set_window_size(width, height)
                
            # Apply stealth modifications
            if self.stealth_mode:
                self._apply_stealth_modifications()
                
            # Apply additional anti-detection measures
            self._apply_advanced_anti_detection()
            
            # Warm up browser if performance mode is enabled
            if self.performance_mode:
                warmup_time = StartupOptimizer.warmup_browser(self.driver)
                logger.info(f"Browser warmed up in {warmup_time:.2f}s")
                
            logger.info("Browser started successfully")
            return self.driver
            
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            # Clean up on failure
            self.cleanup()
            raise
            raise
    
    def stop_browser(self) -> bool:
        """Safely stop the browser"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser stopped successfully")
                return True
            except Exception as e:
                logger.warning(f"Error stopping browser: {e}")
                return False
            finally:
                self.driver = None
        return True
    
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
        if UNDETECTED_CHROME_AVAILABLE and self.stealth_mode and uc:
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
        if WEBDRIVER_MANAGER_AVAILABLE:
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                self.service = ChromeService(ChromeDriverManager().install())
            except Exception as e:
                logger.warning(f"WebDriver Manager failed: {e}")
                self.service = ChromeService()
        else:
            self.service = ChromeService()

        return webdriver.Chrome(service=self.service, options=options)
    
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
        
        if WEBDRIVER_MANAGER_AVAILABLE:
            try:
                from webdriver_manager.firefox import GeckoDriverManager
                self.service = FirefoxService(GeckoDriverManager().install())
            except Exception as e:
                logger.warning(f"WebDriver Manager failed: {e}")
                self.service = FirefoxService()
        else:
            self.service = FirefoxService()

        return webdriver.Firefox(service=self.service, options=options)
    
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
                from webdriver_manager.microsoft import EdgeChromiumDriverManager
                service = EdgeService(EdgeChromiumDriverManager().install())
            except Exception as e:
                logger.warning(f"WebDriver Manager failed: {e}")
        
        if service:
            return webdriver.Edge(service=service, options=options)
        else:
            return webdriver.Edge(options=options)
    
    def _start_safari(self) -> 'webdriver.Safari':
        """Start Safari browser (macOS only)"""
        import platform
        if platform.system() != 'Darwin':
            raise ValueError("Safari is only available on macOS")
        
        from selenium.webdriver.safari.options import Options as SafariOptions
        options = SafariOptions()
        
        # Safari has limited configuration options
        if self.stealth_mode:
            logger.warning("Safari has limited stealth mode support")
        
        # Safari doesn't use external driver
        return webdriver.Safari(options=options)
    
    def _start_opera(self) -> 'webdriver.Chrome':
        """Start Opera browser (uses Chrome driver)"""
        from selenium.webdriver.chrome.options import Options as ChromeOptions
        options = ChromeOptions()
        
        # Find Opera executable
        import platform
        system = platform.system()
        if system == "Windows":
            opera_paths = [
                r"C:\Program Files\Opera\launcher.exe",
                r"C:\Program Files (x86)\Opera\launcher.exe",
                r"C:\Users\{}\AppData\Local\Programs\Opera\launcher.exe".format(os.getenv('USERNAME', ''))
            ]
        elif system == "Darwin":  # macOS
            opera_paths = ["/Applications/Opera.app/Contents/MacOS/Opera"]
        else:  # Linux
            opera_paths = ["/usr/bin/opera", "/opt/opera/opera"]
        
        opera_binary = None
        for path in opera_paths:
            if os.path.exists(path):
                opera_binary = path
                break
        
        if not opera_binary:
            raise ValueError("Opera browser not found. Please install Opera or use a different browser.")
        
        options.binary_location = opera_binary
        
        # Apply stealth options (similar to Chrome)
        if self.stealth_mode:
            stealth_args = [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-images' if self.config.get('disable_images', False) else '',
            ]
            for arg in stealth_args:
                if arg:  # Only add non-empty args
                    options.add_argument(arg)
        
        if self.headless:
            options.add_argument('--headless=new')
        
        # Use Chrome driver for Opera
        service = None
        if WEBDRIVER_MANAGER_AVAILABLE:
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = ChromeService(ChromeDriverManager().install())
            except Exception as e:
                logger.warning(f"WebDriver Manager failed for Opera: {e}")
        
        if service:
            return webdriver.Chrome(service=service, options=options)
        else:
            return webdriver.Chrome(options=options)
    
    def _apply_advanced_anti_detection(self) -> None:
        """Apply advanced anti-detection measures"""
        if not self.driver:
            return
        
        try:
            # Remove navigator.webdriver property
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            
            # Spoof navigator properties
            self.driver.execute_script("""
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5].map(() => ({
                        0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                        description: "Portable Document Format",
                        filename: "internal-pdf-viewer",
                        length: 1,
                        name: "Chrome PDF Plugin"
                    }))
                });
            """)
            
            # Spoof permissions
            self.driver.execute_script("""
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({state: Notification.permission}) :
                        originalQuery(parameters)
                );
            """)
            
            # Mock WebGL vendor
            self.driver.execute_script("""
                const getParameter = WebGLRenderingContext.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) {
                        return 'Intel Inc.';
                    }
                    if (parameter === 37446) {
                        return 'Intel Iris OpenGL Engine';
                    }
                    return getParameter(parameter);
                };
            """)
            
            # Randomize canvas fingerprint
            self.driver.execute_script("""
                const toBlob = HTMLCanvasElement.prototype.toBlob;
                const toDataURL = HTMLCanvasElement.prototype.toDataURL;
                const getImageData = CanvasRenderingContext2D.prototype.getImageData;
                
                const noisify = function(canvas, context) {
                    const shift = {
                        'r': Math.floor(Math.random() * 10) - 5,
                        'g': Math.floor(Math.random() * 10) - 5,
                        'b': Math.floor(Math.random() * 10) - 5,
                        'a': Math.floor(Math.random() * 10) - 5
                    };
                    const width = canvas.width, height = canvas.height;
                    if (width && height) {
                        const imageData = getImageData.apply(context, [0, 0, width, height]);
                        for (let i = 0; i < height; i++) {
                            for (let j = 0; j < width; j++) {
                                const n = ((i * (width * 4)) + (j * 4));
                                imageData.data[n + 0] = imageData.data[n + 0] + shift.r;
                                imageData.data[n + 1] = imageData.data[n + 1] + shift.g;
                                imageData.data[n + 2] = imageData.data[n + 2] + shift.b;
                                imageData.data[n + 3] = imageData.data[n + 3] + shift.a;
                            }
                        }
                        context.putImageData(imageData, 0, 0);
                    }
                };
                
                HTMLCanvasElement.prototype.toBlob = function() {
                    noisify(this, this.getContext('2d'));
                    return toBlob.apply(this, arguments);
                };
                
                HTMLCanvasElement.prototype.toDataURL = function() {
                    noisify(this, this.getContext('2d'));
                    return toDataURL.apply(this, arguments);
                };
            """)
            
            logger.debug("Advanced anti-detection measures applied")
            
        except Exception as e:
            logger.warning(f"Failed to apply some anti-detection measures: {e}")
    
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
    
    def _apply_performance_optimizations(self):
        """Apply performance optimizations to browser configuration"""
        optimizer_config = self.optimizer.optimize_browser_config(self.browser_type)
        
        # Update timeouts for faster operations
        if 'timeouts' in optimizer_config:
            timeouts = optimizer_config['timeouts']
            self.implicit_wait = timeouts.get('implicit', 5)
            self.page_load_timeout = timeouts.get('page_load', 20)
        
        # Apply browser-specific optimizations
        if self.browser_type == 'chrome' and 'chrome_options' in optimizer_config:
            if 'chrome_options' not in self.config:
                self.config['chrome_options'] = []
            self.config['chrome_options'].extend(optimizer_config['chrome_options'])
        
        elif self.browser_type == 'firefox' and 'firefox_prefs' in optimizer_config:
            if 'firefox_prefs' not in self.config:
                self.config['firefox_prefs'] = {}
            self.config['firefox_prefs'].update(optimizer_config['firefox_prefs'])
        
        logger.info("Applied performance optimizations")
    
    @monitor_performance("browser_cleanup")
    def cleanup(self) -> bool:
        """Clean up browser resources with performance monitoring"""
        try:
            if self.driver_id:
                return self.optimizer.cleanup_driver(self.driver_id)
            else:
                # Fallback cleanup
                return self.stop_browser()
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return False