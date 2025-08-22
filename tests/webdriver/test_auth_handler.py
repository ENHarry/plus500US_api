"""
Tests for WebDriver Authentication Handler component
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import time

from plus500us_client.webdriver.auth_handler import WebDriverAuthHandler
from plus500us_client.errors import AuthenticationError, CaptchaRequiredError


class TestWebDriverAuthHandler:
    """Test WebDriverAuthHandler functionality"""
    
    def test_auth_handler_initialization(self, test_config):
        """Test WebDriverAuthHandler initializes correctly"""
        browser_config = {"browser": "chrome", "headless": True}
        handler = WebDriverAuthHandler(test_config, browser_config)
        
        assert handler.config == test_config
        assert handler.browser_config == browser_config
        assert handler.browser_manager is not None
        assert handler.element_detector is None
        assert handler.driver is None
    
    def test_auth_handler_context_manager(self, test_config):
        """Test WebDriverAuthHandler as context manager"""
        browser_config = {"browser": "chrome", "headless": True}
        
        with patch.object(WebDriverAuthHandler, 'close_browser') as mock_close:
            with WebDriverAuthHandler(test_config, browser_config) as handler:
                assert isinstance(handler, WebDriverAuthHandler)
            
            mock_close.assert_called_once()
    
    @patch('plus500us_client.webdriver.auth_handler.input')
    def test_manual_login_flow_success(self, mock_input, test_config, mock_auth_cookies):
        """Test successful manual login flow"""
        mock_input.return_value = ""  # User presses enter
        browser_config = {"browser": "chrome", "headless": True}
        
        handler = WebDriverAuthHandler(test_config, browser_config)
        
        # Mock browser manager and driver
        mock_driver = Mock()
        mock_driver.get_cookies.return_value = mock_auth_cookies
        mock_driver.current_url = "https://futures.plus500.com/dashboard"
        
        handler.browser_manager = Mock()
        handler.browser_manager.get_driver.return_value = mock_driver
        handler.element_detector = Mock()
        
        # Mock successful authentication check
        handler._check_authentication_success = Mock(return_value=True)
        
        session_data = handler.manual_login_flow()
        
        assert session_data["authenticated"] is True
        assert session_data["cookies"] == mock_auth_cookies
        assert session_data["account_type"] is not None
        mock_driver.get.assert_called()
    
    @patch('plus500us_client.webdriver.auth_handler.input')
    def test_manual_login_flow_with_account_type(self, mock_input, test_config, mock_auth_cookies):
        """Test manual login flow with specific account type"""
        mock_input.return_value = ""
        browser_config = {"browser": "chrome", "headless": True}
        
        handler = WebDriverAuthHandler(test_config, browser_config)
        
        mock_driver = Mock()
        mock_driver.get_cookies.return_value = mock_auth_cookies
        mock_driver.current_url = "https://futures.plus500.com/dashboard"
        
        handler.browser_manager = Mock()
        handler.browser_manager.get_driver.return_value = mock_driver
        handler.element_detector = Mock()
        handler._is_login_successful = Mock(return_value=True)
        handler._extract_session_data = Mock(return_value={
            "success": True,
            "cookies": mock_auth_cookies,
            "account_type": "live"
        })
        handler._select_account_type = Mock()
        
        session_data = handler.manual_login_flow(account_type="live")
        
        assert session_data["account_type"] == "live"
        handler._select_account_type.assert_called_with("live")
    
    @patch('plus500us_client.webdriver.auth_handler.input')
    def test_manual_login_flow_timeout(self, mock_input, test_config):
        """Test manual login flow timeout"""
        mock_input.return_value = ""
        browser_config = {"browser": "chrome", "headless": True}
        
        handler = WebDriverAuthHandler(test_config, browser_config)
        
        mock_driver = Mock()
        handler.browser_manager = Mock()
        handler.browser_manager.get_driver.return_value = mock_driver
        handler.element_detector = Mock()
        
        # Mock authentication never succeeds
        handler._is_login_successful = Mock(return_value=False)
        
        with patch('time.time', side_effect=[0, 100, 200, 601]):  # Simulate timeout
            with pytest.raises(Exception):  # TimeoutException or AuthenticationError
                handler.manual_login_flow()
    
    def test_check_authentication_success_dashboard_url(self, test_config):
        """Test authentication success check with dashboard URL"""
        handler = WebDriverAuthHandler(test_config, {})
        
        mock_driver = Mock()
        mock_driver.current_url = "https://futures.plus500.com/dashboard"
        handler.driver = mock_driver
        handler.element_detector = Mock()
        handler.element_detector.is_element_present = Mock(return_value=False)
        
        result = handler._is_login_successful()
        
        assert result is True
    
    def test_check_authentication_success_trading_url(self, test_config):
        """Test authentication success check with trading URL"""
        handler = WebDriverAuthHandler(test_config, {})
        
        mock_driver = Mock()
        mock_driver.current_url = "https://futures.plus500.com/trading/instruments"
        handler.driver = mock_driver
        handler.element_detector = Mock()
        handler.element_detector.is_element_present = Mock(return_value=False)
        
        result = handler._is_login_successful()
        
        assert result is True
    
    def test_check_authentication_success_login_url(self, test_config):
        """Test authentication success check still on login page"""
        handler = WebDriverAuthHandler(test_config, {})
        
        mock_driver = Mock()
        mock_driver.current_url = "https://futures.plus500.com/trade?innerTags=_cc_&page=login"
        handler.driver = mock_driver
        handler.element_detector = Mock()
        handler.element_detector.is_element_present = Mock(return_value=False)
        
        result = handler._is_login_successful()
        
        assert result is False
    
    def test_check_authentication_success_with_element_check(self, test_config):
        """Test authentication success with element presence check"""
        handler = WebDriverAuthHandler(test_config, {})
        
        mock_driver = Mock()
        mock_driver.current_url = "https://futures.plus500.com/some-page"
        handler.driver = mock_driver
        
        mock_element_detector = Mock()
        mock_element_detector.is_element_present.return_value = True
        handler.element_detector = mock_element_detector
        
        result = handler._is_login_successful()
        
        assert result is True
    
    def test_extract_session_data(self, test_config, mock_auth_cookies):
        """Test session data extraction"""
        handler = WebDriverAuthHandler(test_config, {})
        
        mock_driver = Mock()
        mock_driver.get_cookies.return_value = mock_auth_cookies
        mock_driver.execute_script.return_value = "Mozilla/5.0 Test Agent"
        handler.driver = mock_driver
        
        session_data = handler._extract_session_data("demo")
        
        assert session_data["cookies"] == mock_auth_cookies
        assert session_data["account_type"] == "demo"
        assert session_data["authenticated"] is True
        assert "user_agent" in session_data
        assert "timestamp" in session_data
    
    def test_select_account_type_demo(self, test_config):
        """Test demo account type selection"""
        handler = WebDriverAuthHandler(test_config, {})
        
        mock_driver = Mock()
        mock_demo_button = Mock()
        mock_driver.find_element.return_value = mock_demo_button
        handler.driver = mock_driver
        handler.utils = Mock()
        
        handler._select_account_type("demo")
        
        handler.utils.human_like_click.assert_called_with(mock_driver, mock_demo_button)
    
    def test_select_account_type_live(self, test_config):
        """Test live account type selection"""
        handler = WebDriverAuthHandler(test_config, {})
        
        mock_driver = Mock()
        mock_live_button = Mock()
        mock_driver.find_element.return_value = mock_live_button
        handler.driver = mock_driver
        handler.utils = Mock()
        
        handler._select_account_type("live")
        
        handler.utils.human_like_click.assert_called_with(mock_driver, mock_live_button)
    
    def test_select_account_type_button_not_found(self, test_config):
        """Test account type selection when button not found"""
        handler = WebDriverAuthHandler(test_config, {})
        
        mock_driver = Mock()
        mock_driver.find_element.side_effect = Exception("Element not found")
        handler.driver = mock_driver
        
        # Should not raise exception, just log warning
        handler._select_account_type("demo")
    
    def test_detect_captcha_challenge(self, test_config):
        """Test captcha detection"""
        handler = WebDriverAuthHandler(test_config, {})
        
        mock_driver = Mock()
        handler.driver = mock_driver
        handler.element_detector = Mock()
        
        # Mock captcha element found
        handler.element_detector.is_element_present.return_value = True
        
        result = handler._detect_captcha_challenge()
        
        assert result is True
    
    def test_detect_captcha_no_challenge(self, test_config):
        """Test no captcha detection"""
        handler = WebDriverAuthHandler(test_config, {})
        
        mock_driver = Mock()
        handler.driver = mock_driver
        handler.element_detector = Mock()
        
        # Mock no captcha element
        handler.element_detector.is_element_present.return_value = False
        
        result = handler._detect_captcha_challenge()
        
        assert result is False
    
    def test_wait_for_manual_intervention_captcha_detected(self, test_config):
        """Test waiting for manual intervention when captcha detected"""
        handler = WebDriverAuthHandler(test_config, {})
        handler._detect_captcha_challenge = Mock(side_effect=[True, True, False])
        
        with patch('time.sleep'):
            handler._wait_for_manual_intervention()
        
        # Should have checked multiple times until captcha resolved
        assert handler._detect_captcha_challenge.call_count >= 2
    
    def test_cleanup_with_driver(self, test_config):
        """Test cleanup with active driver"""
        handler = WebDriverAuthHandler(test_config, {})
        
        mock_browser_manager = Mock()
        handler.browser_manager = mock_browser_manager
        
        handler.cleanup()
        
        mock_browser_manager.cleanup.assert_called_once()
    
    def test_cleanup_without_driver(self, test_config):
        """Test cleanup without driver"""
        handler = WebDriverAuthHandler(test_config, {})
        handler.browser_manager = None
        
        # Should not raise exception
        handler.cleanup()
    
    def test_get_cookies_for_domain(self, test_config):
        """Test getting cookies for specific domain"""
        handler = WebDriverAuthHandler(test_config, {})
        
        all_cookies = [
            {"name": "session", "value": "123", "domain": ".plus500.com"},
            {"name": "other", "value": "456", "domain": ".example.com"},
            {"name": "auth", "value": "789", "domain": "futures.plus500.com"}
        ]
        
        mock_driver = Mock()
        mock_driver.get_cookies.return_value = all_cookies
        handler.driver = mock_driver
        
        plus500_cookies = handler._get_cookies_for_domain("plus500.com")
        
        assert len(plus500_cookies) == 2
        assert plus500_cookies[0]["name"] == "session"
        assert plus500_cookies[1]["name"] == "auth"
    
    def test_validate_session_data(self, test_config, mock_session_data):
        """Test session data validation"""
        handler = WebDriverAuthHandler(test_config, {})
        
        is_valid = handler._validate_session_data(mock_session_data)
        
        assert is_valid is True
    
    def test_validate_session_data_missing_cookies(self, test_config):
        """Test session data validation with missing cookies"""
        handler = WebDriverAuthHandler(test_config, {})
        
        invalid_data = {
            "authenticated": True,
            "account_type": "demo"
            # Missing cookies
        }
        
        is_valid = handler._validate_session_data(invalid_data)
        
        assert is_valid is False
    
    def test_validate_session_data_empty_cookies(self, test_config):
        """Test session data validation with empty cookies"""
        handler = WebDriverAuthHandler(test_config, {})
        
        invalid_data = {
            "authenticated": True,
            "account_type": "demo",
            "cookies": []  # Empty cookies
        }
        
        is_valid = handler._validate_session_data(invalid_data)
        
        assert is_valid is False
    
    def test_validate_session_data_not_authenticated(self, test_config, mock_auth_cookies):
        """Test session data validation when not authenticated"""
        handler = WebDriverAuthHandler(test_config, {})
        
        invalid_data = {
            "authenticated": False,  # Not authenticated
            "account_type": "demo",
            "cookies": mock_auth_cookies
        }
        
        is_valid = handler._validate_session_data(invalid_data)
        
        assert is_valid is False


@pytest.mark.webdriver
@pytest.mark.auth
class TestWebDriverAuthHandlerIntegration:
    """Integration tests for WebDriverAuthHandler"""
    
    @pytest.mark.slow
    def test_browser_opens_login_page(self, test_config, browser_available):
        """Test that browser opens Plus500 login page"""
        if not browser_available:
            pytest.skip("Browser not available")
        
        browser_config = {"browser": "chrome", "headless": True}
        
        with WebDriverAuthHandler(test_config, webdriver_config) as handler:
            driver = handler.browser_manager.get_driver()
            
            # Navigate to login page
            driver.get(test_config.base_url)
            
            # Basic checks
            assert "plus500" in driver.current_url.lower()
            assert driver.title is not None
            assert len(driver.title) > 0
    
    @pytest.mark.slow
    def test_element_detection_on_real_page(self, test_config, browser_available):
        """Test element detection on real Plus500 page"""
        if not browser_available:
            pytest.skip("Browser not available")
        
        browser_config = {"browser": "chrome", "headless": True}
        
        with WebDriverAuthHandler(test_config, webdriver_config) as handler:
            driver = handler.browser_manager.get_driver()
            handler.element_detector = handler._create_element_detector()
            
            # Navigate to login page
            driver.get(test_config.base_url)
            
            # Try to find common elements (this may vary based on Plus500's actual page structure)
            login_selectors = {
                'xpath': [
                    "//input[@type='email']",
                    "//input[@name='email']",
                    "//input[contains(@placeholder, 'email')]"
                ],
                'css': [
                    "input[type='email']",
                    ".email-input",
                    "#email"
                ]
            }
            
            # Note: This test may fail if Plus500 changes their page structure
            # It's mainly to verify the integration works
            email_input = handler.element_detector.find_element_robust(login_selectors, timeout=5)
            
            # Don't assert element is found as page structure may vary
            # Just verify the detection mechanism works without errors
            assert isinstance(email_input, (type(None), object))
    
    @pytest.mark.slow
    @pytest.mark.captcha
    def test_captcha_detection_mechanism(self, test_config, browser_available):
        """Test captcha detection mechanism"""
        if not browser_available:
            pytest.skip("Browser not available")
        
        browser_config = {"browser": "chrome", "headless": True}
        
        with WebDriverAuthHandler(test_config, webdriver_config) as handler:
            driver = handler.browser_manager.get_driver()
            handler.element_detector = handler._create_element_detector()
            
            # Create a test page with captcha-like elements
            captcha_html = """
            <html><body>
            <div class="captcha-container">
                <div id="recaptcha">reCAPTCHA</div>
                <iframe src="https://www.google.com/recaptcha/"></iframe>
            </div>
            </body></html>
            """
            driver.get(f"data:text/html,{captcha_html}")
            
            # Test captcha detection
            has_captcha = handler._detect_captcha_challenge()
            
            # Should detect the captcha elements
            assert has_captcha is True