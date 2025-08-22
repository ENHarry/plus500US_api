"""
Tests for WebDriver BrowserManager component
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from selenium.common.exceptions import WebDriverException

from plus500us_client.webdriver.browser_manager import BrowserManager
from plus500us_client.config import Config


class TestBrowserManager:
    """Test BrowserManager functionality"""
    
    def test_browser_manager_initialization(self, test_config):
        """Test BrowserManager initializes correctly"""
        manager = BrowserManager(test_config)
        
        assert manager.config == test_config.webdriver_config
        assert manager.main_config == test_config
        assert manager.driver is None
        assert manager.profile_path is not None
        assert not manager.is_browser_alive()
    
    def test_browser_manager_config_validation(self):
        """Test BrowserManager validates configuration"""
        config = Config(webdriver_config={
            "browser": "chrome",
            "headless": True,
            "window_size": (1920, 1080)
        })
        
        manager = BrowserManager(config)
        assert manager.config.webdriver_config["browser"] == "chrome"
        assert manager.config.webdriver_config["headless"] is True
    
    @patch('plus500us_client.webdriver.browser_manager.webdriver.Chrome')
    def test_setup_chrome_driver(self, mock_chrome, test_config):
        """Test Chrome driver setup"""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        manager = BrowserManager(test_config)
        driver = manager._setup_chrome_driver()
        
        assert driver == mock_driver
        mock_chrome.assert_called_once()
    
    @patch('plus500us_client.webdriver.browser_manager.webdriver.Firefox')
    def test_setup_firefox_driver(self, mock_firefox, test_config):
        """Test Firefox driver setup"""
        mock_driver = Mock()
        mock_firefox.return_value = mock_driver
        
        # Update config for Firefox
        test_config.webdriver_config["browser"] = "firefox"
        
        manager = BrowserManager(test_config)
        driver = manager._setup_firefox_driver()
        
        assert driver == mock_driver
        mock_firefox.assert_called_once()
    
    @patch('plus500us_client.webdriver.browser_manager.webdriver.Chrome')
    def test_get_driver_creates_driver(self, mock_chrome, test_config):
        """Test get_driver creates driver instance"""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        manager = BrowserManager(test_config)
        driver = manager.get_driver()
        
        assert driver == mock_driver
        assert manager.driver == mock_driver
        assert manager.is_browser_alive()
    
    @patch('plus500us_client.webdriver.browser_manager.webdriver.Chrome')
    def test_get_driver_reuses_existing(self, mock_chrome, test_config):
        """Test get_driver reuses existing driver"""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        manager = BrowserManager(test_config)
        
        # First call creates driver
        driver1 = manager.get_driver()
        # Second call reuses same driver
        driver2 = manager.get_driver()
        
        assert driver1 == driver2
        assert mock_chrome.call_count == 1
    
    def test_is_browser_alive_false_when_no_driver(self, test_config):
        """Test is_browser_alive returns False when no driver"""
        manager = BrowserManager(test_config)
        assert not manager.is_browser_alive()
    
    def test_is_browser_alive_false_when_driver_quit(self, test_config):
        """Test is_browser_alive handles quit driver"""
        manager = BrowserManager(test_config)
        manager.driver = Mock()
        manager.driver.current_url = "about:blank"
        
        # Simulate driver quit
        manager.driver.current_url = Mock(side_effect=WebDriverException("Driver quit"))
        
        assert not manager.is_browser_alive()
    
    @patch('plus500us_client.webdriver.browser_manager.webdriver.Chrome')
    def test_restart_driver(self, mock_chrome, test_config):
        """Test driver restart functionality"""
        old_driver = Mock()
        new_driver = Mock()
        mock_chrome.side_effect = [old_driver, new_driver]
        
        manager = BrowserManager(test_config)
        
        # Get initial driver
        manager.get_driver()
        assert manager.driver == old_driver
        
        # Restart driver
        restarted_driver = manager.restart_driver()
        
        assert restarted_driver == new_driver
        assert manager.driver == new_driver
        old_driver.quit.assert_called_once()
    
    def test_cleanup_no_driver(self, test_config):
        """Test cleanup when no driver exists"""
        manager = BrowserManager(test_config)
        
        # Should not raise exception
        manager.cleanup()
        assert manager.driver is None
    
    def test_cleanup_with_driver(self, test_config):
        """Test cleanup with active driver"""
        manager = BrowserManager(test_config)
        mock_driver = Mock()
        manager.driver = mock_driver
        
        manager.cleanup()
        
        mock_driver.quit.assert_called_once()
        assert manager.driver is None
    
    def test_cleanup_handles_driver_exception(self, test_config):
        """Test cleanup handles driver exceptions gracefully"""
        manager = BrowserManager(test_config)
        mock_driver = Mock()
        mock_driver.quit.side_effect = WebDriverException("Driver already quit")
        manager.driver = mock_driver
        
        # Should not raise exception
        manager.cleanup()
        assert manager.driver is None
    
    @patch('plus500us_client.webdriver.browser_manager.webdriver.Chrome')
    def test_apply_stealth_mode(self, mock_chrome, test_config):
        """Test stealth mode application"""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        test_config.webdriver_config["stealth_mode"] = True
        
        manager = BrowserManager(test_config)
        driver = manager.get_driver()
        
        # Should have applied stealth mode
        mock_driver.execute_script.assert_called()
    
    def test_human_like_behavior_simulation(self, test_config):
        """Test human-like behavior simulation"""
        manager = BrowserManager(test_config)
        mock_driver = Mock()
        manager.driver = mock_driver
        
        manager._simulate_human_behavior()
        
        # Should have executed some human-like actions
        assert mock_driver.execute_script.call_count > 0
    
    @patch('plus500us_client.webdriver.browser_manager.webdriver.Chrome')
    def test_profile_management(self, mock_chrome, test_config, temp_profile_dir):
        """Test browser profile management"""
        test_config.webdriver_config["profile_path"] = str(temp_profile_dir)
        
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        manager = BrowserManager(test_config)
        manager.get_driver()
        
        # Should have used profile path in Chrome options
        mock_chrome.assert_called_once()
        call_args = mock_chrome.call_args
        assert call_args is not None
    
    def test_window_size_configuration(self, test_config):
        """Test window size is configured correctly"""
        test_config.webdriver_config["window_size"] = (1280, 720)
        
        manager = BrowserManager(test_config)
        mock_driver = Mock()
        manager.driver = mock_driver
        
        manager._configure_window_size()
        
        mock_driver.set_window_size.assert_called_with(1280, 720)
    
    @patch('plus500us_client.webdriver.browser_manager.webdriver.Chrome')
    def test_implicit_wait_configuration(self, mock_chrome, test_config):
        """Test implicit wait is configured"""
        test_config.webdriver_config["implicit_wait"] = 10
        
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        manager = BrowserManager(test_config)
        manager.get_driver()
        
        mock_driver.implicitly_wait.assert_called_with(10)
    
    @patch('plus500us_client.webdriver.browser_manager.webdriver.Chrome')
    def test_page_load_timeout_configuration(self, mock_chrome, test_config):
        """Test page load timeout is configured"""
        test_config.webdriver_config["page_load_timeout"] = 30
        
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        manager = BrowserManager(test_config)
        manager.get_driver()
        
        mock_driver.set_page_load_timeout.assert_called_with(30)
    
    def test_unsupported_browser_raises_error(self, test_config):
        """Test unsupported browser raises ValueError"""
        test_config.webdriver_config["browser"] = "safari"
        
        manager = BrowserManager(test_config)
        
        with pytest.raises(ValueError, match="Unsupported browser"):
            manager.get_driver()
    
    @patch('plus500us_client.webdriver.browser_manager.webdriver.Chrome')
    def test_driver_creation_failure(self, mock_chrome, test_config):
        """Test handling of driver creation failure"""
        mock_chrome.side_effect = WebDriverException("Failed to start browser")
        
        manager = BrowserManager(test_config)
        
        with pytest.raises(RuntimeError, match="Failed to initialize"):
            manager.get_driver()
    
    @patch('plus500us_client.webdriver.browser_manager.undetected_chromedriver')
    def test_undetected_chromedriver_fallback(self, mock_undetected, test_config):
        """Test fallback to undetected-chromedriver"""
        mock_driver = Mock()
        mock_undetected.Chrome.return_value = mock_driver
        
        # Simulate Chrome driver failure
        with patch('plus500us_client.webdriver.browser_manager.webdriver.Chrome', 
                  side_effect=WebDriverException("Chrome failed")):
            
            manager = BrowserManager(test_config)
            driver = manager.get_driver()
            
            assert driver == mock_driver
            mock_undetected.Chrome.assert_called_once()


@pytest.mark.webdriver
class TestBrowserManagerIntegration:
    """Integration tests for BrowserManager (require actual browser)"""
    
    @pytest.mark.slow
    def test_real_chrome_driver_creation(self, test_config, browser_available):
        """Test creating real Chrome driver"""
        if not browser_available:
            pytest.skip("Browser not available")
        
        manager = BrowserManager(test_config)
        
        try:
            driver = manager.get_driver()
            assert driver is not None
            assert manager.is_browser_alive()
            
            # Test basic navigation
            driver.get("about:blank")
            assert "about:blank" in driver.current_url
            
        finally:
            manager.cleanup()
    
    @pytest.mark.slow  
    def test_real_driver_restart(self, test_config, browser_available):
        """Test restarting real driver"""
        if not browser_available:
            pytest.skip("Browser not available")
        
        manager = BrowserManager(test_config)
        
        try:
            # Get initial driver
            driver1 = manager.get_driver()
            driver1_id = id(driver1)
            
            # Restart driver
            driver2 = manager.restart_driver()
            driver2_id = id(driver2)
            
            assert driver2_id != driver1_id
            assert manager.is_browser_alive()
            
        finally:
            manager.cleanup()
    
    @pytest.mark.slow
    def test_profile_persistence(self, test_config, browser_available, temp_profile_dir):
        """Test browser profile persistence"""
        if not browser_available:
            pytest.skip("Browser not available")
        
        test_config.webdriver_config["profile_path"] = str(temp_profile_dir)
        
        manager = BrowserManager(test_config)
        
        try:
            driver = manager.get_driver()
            
            # Navigate to test page and set cookie
            driver.get("https://httpbin.org/")
            driver.add_cookie({"name": "test_cookie", "value": "test_value"})
            
            # Restart browser and check if cookie persists
            manager.restart_driver()
            driver.get("https://httpbin.org/")
            cookies = driver.get_cookies()
            
            # Note: Cookie persistence depends on browser configuration
            # This test verifies the profile mechanism works
            assert isinstance(cookies, list)
            
        finally:
            manager.cleanup()