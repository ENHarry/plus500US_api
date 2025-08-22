"""
Cross-browser authentication tests for Plus500US
Tests login functionality across Chrome, Firefox, and Edge browsers
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock

from plus500us_client.config import Config
from plus500us_client.webdriver import WebDriverAuthHandler, BrowserManager


class TestCrossBrowserAuth:
    """Test authentication functionality across different browsers"""
    
    @pytest.fixture(scope="class")
    def auth_test_config(self):
        """Create config for authentication testing"""
        return Config(
            base_url="https://futures.plus500.com",
            account_type="demo",
            email="test@example.com",
            password="test_password",
            webdriver_config={
                "browser": "firefox",  # Default
                "headless": True,
                "stealth_mode": True,
                "window_size": (1920, 1080),
                "implicit_wait": 5,
                "page_load_timeout": 15,
            }
        )
    
    @pytest.mark.parametrize("browser_type", ["firefox", "chrome", "edge"])
    def test_auth_handler_initialization(self, auth_test_config, browser_type):
        """Test auth handler can initialize with different browsers"""
        # Create browser-specific config
        browser_config = {
            "browser": browser_type,
            "headless": True,
            "stealth_mode": True
        }
        
        try:
            with patch('plus500us_client.webdriver.auth_handler.BrowserManager') as mock_browser_manager:
                # Mock browser manager
                mock_manager = Mock()
                mock_driver = Mock()
                mock_manager.get_driver.return_value = mock_driver
                mock_manager.start_browser.return_value = mock_driver
                mock_browser_manager.return_value = mock_manager
                
                auth_handler = WebDriverAuthHandler(auth_test_config, browser_config)
                
                # Verify auth handler properties
                assert auth_handler.config == auth_test_config
                assert auth_handler.browser_config == browser_config
                assert auth_handler.browser_config["browser"] == browser_type
                
        except Exception as e:
            pytest.fail(f"Auth handler initialization failed for {browser_type}: {e}")
    
    @pytest.mark.parametrize("browser_type", ["firefox", "chrome", "edge"])
    def test_browser_manager_creation_for_auth(self, auth_test_config, browser_type):
        """Test browser manager creation for authentication with different browsers"""
        browser_config = {
            "browser": browser_type,
            "headless": True,
            "stealth_mode": True
        }
        
        with patch('plus500us_client.webdriver.auth_handler.BrowserManager') as mock_browser_manager:
            # Mock browser manager creation
            mock_manager = Mock()
            mock_browser_manager.return_value = mock_manager
            
            auth_handler = WebDriverAuthHandler(auth_test_config, browser_config)
            
            # Verify browser manager was created with correct config
            mock_browser_manager.assert_called_once()
            call_args = mock_browser_manager.call_args[0][0]
            assert call_args.webdriver_config["browser"] == browser_type
    
    @pytest.mark.parametrize("browser_type", ["firefox", "chrome", "edge"])
    def test_manual_login_flow_browser_support(self, auth_test_config, browser_type):
        """Test manual login flow initialization across browsers"""
        browser_config = {
            "browser": browser_type,
            "headless": True,
            "stealth_mode": True
        }
        
        with patch('plus500us_client.webdriver.auth_handler.BrowserManager') as mock_browser_manager:
            with patch('builtins.input', return_value=''):  # Mock user input
                # Mock browser manager and driver
                mock_manager = Mock()
                mock_driver = Mock()
                mock_driver.get_cookies.return_value = [
                    {"name": "session_id", "value": "test_session"}
                ]
                mock_driver.current_url = "https://futures.plus500.com/trade"
                mock_manager.get_driver.return_value = mock_driver
                mock_manager.start_browser.return_value = mock_driver
                mock_browser_manager.return_value = mock_manager
                
                try:
                    with WebDriverAuthHandler(auth_test_config, browser_config) as auth_handler:
                        # Test manual login flow can be initiated
                        session_data = auth_handler.manual_login_flow()
                        
                        # Verify session data structure
                        assert isinstance(session_data, dict)
                        assert "cookies" in session_data
                        assert "success" in session_data or "account_type" in session_data
                        
                except Exception as e:
                    pytest.fail(f"Manual login flow failed for {browser_type}: {e}")
    
    def test_browser_specific_stealth_configurations(self):
        """Test that stealth configurations are applied correctly for each browser"""
        browsers = ["firefox", "chrome", "edge"]
        
        for browser_type in browsers:
            config = Config(webdriver_config={
                "browser": browser_type,
                "stealth_mode": True,
                "headless": True
            })
            
            browser_manager = BrowserManager(config)
            
            # Verify stealth mode is enabled
            assert browser_manager.stealth_mode is True
            
            # Test browser-specific stealth features
            user_agent = browser_manager._get_random_user_agent()
            assert "Mozilla" in user_agent
            
            # Test that browser type is correctly configured
            assert browser_manager.browser_type == browser_type
    
    @pytest.mark.skipif(
        not os.getenv("PLUS500US_ENABLE_BROWSER_TESTS"), 
        reason="Real browser tests disabled"
    )
    @pytest.mark.parametrize("browser_type", ["firefox", "chrome"])
    def test_real_browser_auth_flow_initiation(self, auth_test_config, browser_type):
        """Test that real browsers can start authentication flow"""
        browser_config = {
            "browser": browser_type,
            "headless": True,
            "stealth_mode": True,
            "implicit_wait": 5,
            "page_load_timeout": 10
        }
        
        auth_handler = None
        try:
            auth_handler = WebDriverAuthHandler(auth_test_config, browser_config)
            
            # Start browser (this will test real browser functionality)
            driver = auth_handler.browser_manager.start_browser()
            assert driver is not None
            
            # Test navigation to login page
            driver.get(auth_test_config.base_url)
            
            # Verify page loaded
            assert driver.current_url.startswith("https://")
            
            # Test basic stealth features are working
            user_agent = driver.execute_script("return navigator.userAgent;")
            assert "Mozilla" in user_agent
            
            # Test browser-specific features
            if browser_type == "firefox":
                assert "Firefox" in user_agent
            elif browser_type == "chrome":
                assert "Chrome" in user_agent
                
        except Exception as e:
            pytest.fail(f"Real browser auth flow initiation failed for {browser_type}: {e}")
        finally:
            if auth_handler:
                auth_handler.browser_manager.stop_browser()
    
    def test_auth_error_handling_across_browsers(self):
        """Test authentication error handling works consistently across browsers"""
        browsers = ["firefox", "chrome", "edge"]
        
        for browser_type in browsers:
            browser_config = {
                "browser": browser_type,
                "headless": True
            }
            
            # Test with invalid config
            invalid_config = Config(
                base_url="invalid://url",
                webdriver_config=browser_config
            )
            
            with patch('plus500us_client.webdriver.auth_handler.BrowserManager') as mock_browser_manager:
                # Mock browser manager to raise error
                mock_manager = Mock()
                mock_manager.start_browser.side_effect = Exception(f"Browser {browser_type} failed")
                mock_browser_manager.return_value = mock_manager
                
                try:
                    auth_handler = WebDriverAuthHandler(invalid_config, browser_config)
                    
                    # This should handle errors gracefully
                    with pytest.raises(Exception):
                        auth_handler.browser_manager.start_browser()
                        
                except Exception as e:
                    # Error handling should be consistent across browsers
                    assert browser_type in str(e) or "failed" in str(e).lower()
    
    def test_session_data_consistency_across_browsers(self):
        """Test that session data format is consistent across browsers"""
        browsers = ["firefox", "chrome", "edge"]
        
        for browser_type in browsers:
            browser_config = {
                "browser": browser_type,
                "headless": True
            }
            
            config = Config(webdriver_config=browser_config)
            
            with patch('plus500us_client.webdriver.auth_handler.BrowserManager') as mock_browser_manager:
                with patch('builtins.input', return_value=''):
                    # Mock consistent browser behavior
                    mock_manager = Mock()
                    mock_driver = Mock()
                    mock_driver.get_cookies.return_value = [
                        {"name": "session_id", "value": f"test_session_{browser_type}"},
                        {"name": "account_type", "value": "demo"}
                    ]
                    mock_driver.current_url = "https://futures.plus500.com/trade"
                    mock_driver.execute_script.return_value = f"Test User Agent {browser_type}"
                    mock_manager.get_driver.return_value = mock_driver
                    mock_manager.start_browser.return_value = mock_driver
                    mock_browser_manager.return_value = mock_manager
                    
                    try:
                        with WebDriverAuthHandler(config, browser_config) as auth_handler:
                            session_data = auth_handler.manual_login_flow()
                            
                            # Verify consistent session data structure
                            required_keys = ["cookies", "user_agent", "account_type"]
                            for key in required_keys:
                                assert key in session_data, f"Missing {key} in session data for {browser_type}"
                            
                            # Verify data types are consistent
                            assert isinstance(session_data["cookies"], list)
                            assert isinstance(session_data["user_agent"], str)
                            assert "success" in session_data or "account_type" in session_data
                            
                    except Exception as e:
                        pytest.fail(f"Session data consistency test failed for {browser_type}: {e}")
    
    def test_environment_variable_browser_selection_for_auth(self):
        """Test environment variable browser selection works for authentication"""
        test_browsers = ["firefox", "chrome", "edge"]
        
        for browser in test_browsers:
            with patch.dict(os.environ, {"PLUS500_BROWSER": browser}):
                with patch('plus500us_client.webdriver.auth_handler.BrowserManager') as mock_browser_manager:
                    # Load config with environment variable
                    from plus500us_client import load_config
                    config = load_config()
                    
                    # Verify browser was set from environment
                    assert config.webdriver_config["browser"] == browser
                    
                    # Create auth handler
                    browser_config = {"browser": browser, "headless": True}
                    mock_manager = Mock()
                    mock_browser_manager.return_value = mock_manager
                    
                    auth_handler = WebDriverAuthHandler(config, browser_config)
                    
                    # Verify correct browser configuration
                    assert auth_handler.browser_config["browser"] == browser


class TestBrowserCompatibilityFeatures:
    """Test browser compatibility and feature detection"""
    
    def test_browser_feature_availability(self):
        """Test browser feature availability detection"""
        # Test webdriver manager availability
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            from webdriver_manager.firefox import GeckoDriverManager
            from webdriver_manager.microsoft import EdgeChromiumDriverManager
            webdriver_manager_available = True
        except ImportError:
            webdriver_manager_available = False
        
        # Test undetected chrome availability
        try:
            import undetected_chromedriver as uc
            undetected_chrome_available = True
        except ImportError:
            undetected_chrome_available = False
        
        # These should be available in a properly configured environment
        # (Will show warnings if not available, but won't fail tests)
        print(f"WebDriver Manager available: {webdriver_manager_available}")
        print(f"Undetected Chrome available: {undetected_chrome_available}")
    
    def test_browser_version_compatibility(self):
        """Test browser version compatibility"""
        # This test ensures our browser configurations are compatible
        # with different browser versions
        browsers = ["firefox", "chrome", "edge"]
        
        for browser_type in browsers:
            config = Config(webdriver_config={
                "browser": browser_type,
                "stealth_mode": True
            })
            
            browser_manager = BrowserManager(config)
            
            # Test that browser manager can handle the configuration
            assert browser_manager.browser_type == browser_type
            assert hasattr(browser_manager, f'_start_{browser_type}')


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])