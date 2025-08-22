"""
Tests for Hybrid Method Selector component
"""
import pytest
from unittest.mock import Mock

from plus500us_client.hybrid.method_selector import MethodSelector, AutomationMethod
from plus500us_client.errors import CaptchaRequiredError, AutomationBlockedError, AuthenticationError


class TestMethodSelector:
    """Test MethodSelector functionality"""
    
    def test_method_selector_initialization(self, test_config):
        """Test MethodSelector initializes correctly"""
        selector = MethodSelector(test_config)
        
        assert selector.config == test_config
        assert selector.method_history == {}
        assert selector.failure_count == 0
        assert selector.max_failures == 3
    
    def test_select_method_webdriver_preference(self, test_config):
        """Test method selection with WebDriver preference"""
        test_config.preferred_method = "webdriver"
        selector = MethodSelector(test_config)
        
        method = selector.select_method("login")
        
        assert method == AutomationMethod.WEBDRIVER
    
    def test_select_method_requests_preference(self, test_config):
        """Test method selection with requests preference"""
        test_config.preferred_method = "requests"
        selector = MethodSelector(test_config)
        
        method = selector.select_method("login")
        
        assert method == AutomationMethod.REQUESTS
    
    def test_auto_select_method_captcha_detected(self, test_config):
        """Test auto selection when captcha detected"""
        test_config.preferred_method = "auto"
        selector = MethodSelector(test_config)
        
        context = {"captcha_present": True}
        method = selector.select_method("login", context)
        
        assert method == AutomationMethod.WEBDRIVER
    
    def test_auto_select_method_anti_bot_detected(self, test_config):
        """Test auto selection when anti-bot protection detected"""
        test_config.preferred_method = "auto"
        selector = MethodSelector(test_config)
        
        context = {"error_message": "Access denied - unusual activity detected"}
        method = selector.select_method("login", context)
        
        assert method == AutomationMethod.WEBDRIVER
    
    def test_auto_select_method_rate_limited(self, test_config):
        """Test auto selection when rate limited"""
        test_config.preferred_method = "auto"
        selector = MethodSelector(test_config)
        
        context = {"status_code": 429}
        method = selector.select_method("login", context)
        
        assert method == AutomationMethod.WEBDRIVER
    
    def test_auto_select_method_cloudflare_challenge(self, test_config):
        """Test auto selection with Cloudflare challenge"""
        test_config.preferred_method = "auto"
        selector = MethodSelector(test_config)
        
        context = {"cloudflare_challenge": True}
        method = selector.select_method("trading", context)
        
        assert method == AutomationMethod.WEBDRIVER
    
    def test_auto_select_method_login_operation(self, test_config):
        """Test auto selection for login operation"""
        test_config.preferred_method = "auto"
        selector = MethodSelector(test_config)
        
        method = selector.select_method("login")
        
        # Should try requests first for login
        assert method == AutomationMethod.REQUESTS
    
    def test_auto_select_method_login_with_failures(self, test_config):
        """Test auto selection for login after failures"""
        test_config.preferred_method = "auto"
        selector = MethodSelector(test_config)
        selector.failure_count = 2
        
        method = selector.select_method("login")
        
        # Should use WebDriver after failures
        assert method == AutomationMethod.WEBDRIVER
    
    def test_auto_select_method_trading_operation(self, test_config):
        """Test auto selection for trading operation"""
        test_config.preferred_method = "auto"
        selector = MethodSelector(test_config)
        
        method = selector.select_method("trading")
        
        # Trading operations should prefer WebDriver
        assert method == AutomationMethod.WEBDRIVER
    
    def test_auto_select_method_market_data_operation(self, test_config):
        """Test auto selection for market data operation"""
        test_config.preferred_method = "auto"
        selector = MethodSelector(test_config)
        
        method = selector.select_method("market_data")
        
        # Data operations can try requests first
        assert method == AutomationMethod.REQUESTS
    
    def test_auto_select_method_unknown_operation(self, test_config):
        """Test auto selection for unknown operation"""
        test_config.preferred_method = "auto"
        selector = MethodSelector(test_config)
        
        method = selector.select_method("unknown_operation")
        
        # Unknown operations default to WebDriver
        assert method == AutomationMethod.WEBDRIVER
    
    def test_captcha_detected_in_context(self, test_config):
        """Test captcha detection in context"""
        selector = MethodSelector(test_config)
        
        contexts = [
            {"captcha_present": True},
            {"captcha_error": True},
            {"error_message": "Please complete the CAPTCHA verification"}
        ]
        
        for context in contexts:
            assert selector._captcha_detected(context) is True
    
    def test_anti_bot_detected_in_context(self, test_config):
        """Test anti-bot detection in context"""
        selector = MethodSelector(test_config)
        
        contexts = [
            {"status_code": 403},
            {"status_code": 429},
            {"status_code": 503},
            {"error_message": "Access blocked due to automated activity"},
            {"error_message": "Rate limit exceeded"},
            {"cloudflare_challenge": True},
            {"rate_limited": True}
        ]
        
        for context in contexts:
            assert selector._anti_bot_detected(context) is True
    
    def test_record_success(self, test_config):
        """Test recording successful operation"""
        selector = MethodSelector(test_config)
        selector.failure_count = 2
        
        selector.record_success("login", AutomationMethod.REQUESTS)
        
        assert selector.method_history["login_requests_success"] is True
        assert selector.failure_count == 1  # Should decrease failure count
    
    def test_record_failure(self, test_config, captcha_error):
        """Test recording failed operation"""
        selector = MethodSelector(test_config)
        
        selector.record_failure("login", AutomationMethod.REQUESTS, captcha_error)
        
        assert selector.method_history["login_requests_failed"] is True
        assert selector.failure_count == 1
        assert selector.method_history["captcha_detected"] is True
    
    def test_record_failure_automation_blocked(self, test_config, automation_blocked_error):
        """Test recording automation blocked failure"""
        selector = MethodSelector(test_config)
        
        selector.record_failure("trading", AutomationMethod.REQUESTS, automation_blocked_error)
        
        assert selector.method_history["trading_requests_failed"] is True
        assert selector.method_history["anti_bot_detected"] is True
    
    def test_should_fallback_captcha_error(self, test_config, captcha_error):
        """Test fallback decision for captcha error"""
        selector = MethodSelector(test_config)
        
        should_fallback = selector.should_fallback("login", AutomationMethod.REQUESTS, captcha_error)
        
        assert should_fallback is True
        assert selector.failure_count == 1
    
    def test_should_fallback_automation_blocked(self, test_config, automation_blocked_error):
        """Test fallback decision for automation blocked error"""
        selector = MethodSelector(test_config)
        
        should_fallback = selector.should_fallback("trading", AutomationMethod.REQUESTS, automation_blocked_error)
        
        assert should_fallback is True
    
    def test_should_fallback_multiple_failures(self, test_config):
        """Test fallback decision after multiple failures"""
        selector = MethodSelector(test_config)
        selector.failure_count = 1
        
        should_fallback = selector.should_fallback("login", AutomationMethod.REQUESTS, Exception("Generic error"))
        
        assert should_fallback is True
        assert selector.failure_count == 2
    
    def test_should_fallback_webdriver_method(self, test_config):
        """Test no fallback available from WebDriver"""
        selector = MethodSelector(test_config)
        
        should_fallback = selector.should_fallback("login", AutomationMethod.WEBDRIVER, Exception("Error"))
        
        assert should_fallback is False
    
    def test_should_fallback_authentication_error(self, test_config):
        """Test fallback for authentication error"""
        selector = MethodSelector(test_config)
        auth_error = AuthenticationError("Invalid credentials")
        
        should_fallback = selector.should_fallback("login", AutomationMethod.REQUESTS, auth_error)
        
        assert should_fallback is True
    
    def test_get_fallback_method_from_requests(self, test_config):
        """Test getting fallback method from requests"""
        selector = MethodSelector(test_config)
        
        fallback = selector.get_fallback_method(AutomationMethod.REQUESTS)
        
        assert fallback == AutomationMethod.WEBDRIVER
    
    def test_get_fallback_method_from_webdriver(self, test_config):
        """Test getting fallback method from WebDriver"""
        selector = MethodSelector(test_config)
        
        fallback = selector.get_fallback_method(AutomationMethod.WEBDRIVER)
        
        assert fallback is None  # No fallback from WebDriver
    
    def test_get_fallback_method_from_auto(self, test_config):
        """Test getting fallback method from auto"""
        selector = MethodSelector(test_config)
        
        fallback = selector.get_fallback_method(AutomationMethod.AUTO)
        
        assert fallback == AutomationMethod.WEBDRIVER
    
    def test_reset_history(self, test_config):
        """Test resetting method selection history"""
        selector = MethodSelector(test_config)
        selector.method_history = {"test": True}
        selector.failure_count = 3
        
        selector.reset_history()
        
        assert selector.method_history == {}
        assert selector.failure_count == 0
    
    def test_get_method_stats(self, test_config):
        """Test getting method selection statistics"""
        selector = MethodSelector(test_config)
        selector.failure_count = 2
        selector.method_history = {"login_failed": True}
        
        stats = selector.get_method_stats()
        
        assert stats["failure_count"] == 2
        assert stats["history"]["login_failed"] is True
        assert stats["preferred_method"] == test_config.preferred_method
        assert "webdriver_available" in stats
    
    def test_should_use_webdriver_based_on_history(self, test_config):
        """Test WebDriver selection based on history"""
        selector = MethodSelector(test_config)
        
        # Test failure count threshold
        selector.failure_count = 2
        assert selector._should_use_webdriver_based_on_history("login") is True
        
        # Test specific operation failure
        selector.failure_count = 0
        selector.method_history["login_requests_failed"] = True
        assert selector._should_use_webdriver_based_on_history("login") is True
        
        # Test no issues
        selector.failure_count = 0
        selector.method_history = {}
        assert selector._should_use_webdriver_based_on_history("login") is False
    
    def test_is_authentication_error(self, test_config):
        """Test authentication error detection"""
        selector = MethodSelector(test_config)
        
        auth_errors = [
            Exception("Authentication failed"),
            Exception("401 Unauthorized"),
            Exception("403 Forbidden"),
            Exception("Invalid session"),
            Exception("Cookie expired"),
            Exception("Login required")
        ]
        
        for error in auth_errors:
            assert selector._is_authentication_error(error) is True
        
        # Test non-auth error
        generic_error = Exception("Network timeout")
        assert selector._is_authentication_error(generic_error) is False
        
        # Test None error
        assert selector._is_authentication_error(None) is False


class TestAutomationMethod:
    """Test AutomationMethod enum"""
    
    def test_automation_method_values(self):
        """Test AutomationMethod enum values"""
        assert AutomationMethod.WEBDRIVER.value == "webdriver"
        assert AutomationMethod.REQUESTS.value == "requests"
        assert AutomationMethod.AUTO.value == "auto"
    
    def test_automation_method_comparison(self):
        """Test AutomationMethod comparison"""
        assert AutomationMethod.WEBDRIVER == AutomationMethod.WEBDRIVER
        assert AutomationMethod.WEBDRIVER != AutomationMethod.REQUESTS
    
    def test_automation_method_string_representation(self):
        """Test AutomationMethod string representation"""
        assert str(AutomationMethod.WEBDRIVER) == "AutomationMethod.WEBDRIVER"
        assert repr(AutomationMethod.REQUESTS) == "<AutomationMethod.REQUESTS: 'requests'>"


class TestMethodSelectorIntegration:
    """Integration tests for MethodSelector"""
    
    def test_complex_failure_scenario(self, test_config):
        """Test complex failure and recovery scenario"""
        selector = MethodSelector(test_config)
        test_config.preferred_method = "auto"
        
        # Initial login attempt - should try requests first
        method1 = selector.select_method("login")
        assert method1 == AutomationMethod.REQUESTS
        
        # First failure - should still try requests
        selector.record_failure("login", AutomationMethod.REQUESTS, Exception("Network error"))
        method2 = selector.select_method("login")
        assert method2 == AutomationMethod.REQUESTS
        
        # Second failure - should switch to WebDriver
        selector.record_failure("login", AutomationMethod.REQUESTS, Exception("Another error"))
        method3 = selector.select_method("login")
        assert method3 == AutomationMethod.WEBDRIVER
        
        # Success with WebDriver - should prefer WebDriver for future logins
        selector.record_success("login", AutomationMethod.WEBDRIVER)
        method4 = selector.select_method("login")
        assert method4 == AutomationMethod.WEBDRIVER
    
    def test_captcha_detection_scenario(self, test_config, captcha_error):
        """Test captcha detection and handling scenario"""
        selector = MethodSelector(test_config)
        test_config.preferred_method = "auto"
        
        # Initial attempt
        method1 = selector.select_method("login")
        assert method1 == AutomationMethod.REQUESTS
        
        # Captcha error - should immediately switch to WebDriver
        should_fallback = selector.should_fallback("login", AutomationMethod.REQUESTS, captcha_error)
        assert should_fallback is True
        
        # Next attempt should use WebDriver due to captcha history
        context = {"captcha_detected": True}
        method2 = selector.select_method("login", context)
        assert method2 == AutomationMethod.WEBDRIVER
    
    def test_operation_specific_behavior(self, test_config):
        """Test operation-specific method selection behavior"""
        selector = MethodSelector(test_config)
        test_config.preferred_method = "auto"
        
        # Trading operations should prefer WebDriver
        trading_method = selector.select_method("trading")
        assert trading_method == AutomationMethod.WEBDRIVER
        
        order_method = selector.select_method("order_placement")
        assert order_method == AutomationMethod.WEBDRIVER
        
        # Data operations can start with requests
        data_method = selector.select_method("market_data")
        assert data_method == AutomationMethod.REQUESTS
        
        account_method = selector.select_method("account_info")
        assert account_method == AutomationMethod.REQUESTS
    
    def test_reset_and_recovery(self, test_config):
        """Test history reset and recovery"""
        selector = MethodSelector(test_config)
        
        # Build up failure history
        for i in range(3):
            selector.record_failure("login", AutomationMethod.REQUESTS, Exception(f"Error {i}"))
        
        assert selector.failure_count == 3
        assert len(selector.method_history) > 0
        
        # Reset history
        selector.reset_history()
        
        assert selector.failure_count == 0
        assert selector.method_history == {}
        
        # Should behave like fresh start
        test_config.preferred_method = "auto"
        method = selector.select_method("login")
        assert method == AutomationMethod.REQUESTS