"""
Tests for Hybrid Fallback Handler component
"""
import pytest
from unittest.mock import Mock, patch
import time

from plus500us_client.hybrid.fallback_handler import FallbackHandler
from plus500us_client.hybrid.method_selector import MethodSelector, AutomationMethod
from plus500us_client.errors import CaptchaRequiredError, AutomationBlockedError, ValidationError


class TestFallbackHandler:
    """Test FallbackHandler functionality"""
    
    def test_fallback_handler_initialization(self, test_config, method_selector):
        """Test FallbackHandler initializes correctly"""
        handler = FallbackHandler(test_config, method_selector)
        
        assert handler.config == test_config
        assert handler.method_selector == method_selector
        assert handler.retry_delays == [1, 2, 5]
        assert handler.max_retries == 3
        assert "requests" in handler.circuit_breaker
        assert "webdriver" in handler.circuit_breaker
    
    def test_fallback_handler_auto_method_selector(self, test_config):
        """Test FallbackHandler creates method selector automatically"""
        handler = FallbackHandler(test_config)
        
        assert isinstance(handler.method_selector, MethodSelector)
        assert handler.method_selector.config == test_config
    
    def test_with_fallback_decorator(self, fallback_handler):
        """Test with_fallback decorator functionality"""
        @fallback_handler.with_fallback("test_operation")
        def test_function(value, method=None):
            if method == AutomationMethod.REQUESTS:
                raise CaptchaRequiredError("Captcha required")
            return f"success_{value}"
        
        # Mock method selector to try requests first, then webdriver
        fallback_handler.method_selector.select_method = Mock(return_value=AutomationMethod.REQUESTS)
        fallback_handler.method_selector.get_fallback_method = Mock(return_value=AutomationMethod.WEBDRIVER)
        fallback_handler.method_selector.record_success = Mock()
        fallback_handler.method_selector.record_failure = Mock()
        
        result = test_function("test")
        
        assert result == "success_test"
        fallback_handler.method_selector.record_success.assert_called()
    
    def test_execute_with_fallback_success_first_method(self, fallback_handler):
        """Test execute_with_fallback succeeds on first method"""
        def test_func(method=None):
            return "success"
        
        fallback_handler.method_selector.select_method = Mock(return_value=AutomationMethod.WEBDRIVER)
        fallback_handler.method_selector.record_success = Mock()
        
        result = fallback_handler.execute_with_fallback(test_func, "test_operation")
        
        assert result == "success"
        fallback_handler.method_selector.record_success.assert_called_with("test_operation", AutomationMethod.WEBDRIVER)
    
    def test_execute_with_fallback_success_after_fallback(self, fallback_handler):
        """Test execute_with_fallback succeeds after fallback"""
        call_count = 0
        
        def test_func(method=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1 and method == AutomationMethod.REQUESTS:
                raise CaptchaRequiredError("Captcha required")
            return "success_fallback"
        
        fallback_handler.method_selector.select_method = Mock(return_value=AutomationMethod.REQUESTS)
        fallback_handler.method_selector.get_fallback_method = Mock(return_value=AutomationMethod.WEBDRIVER)
        fallback_handler.method_selector.record_success = Mock()
        fallback_handler.method_selector.record_failure = Mock()
        
        with patch('time.sleep'):  # Speed up test
            result = fallback_handler.execute_with_fallback(test_func, "test_operation")
        
        assert result == "success_fallback"
        assert call_count == 2
        fallback_handler.method_selector.record_failure.assert_called()
        fallback_handler.method_selector.record_success.assert_called()
    
    def test_execute_with_fallback_all_methods_fail(self, fallback_handler):
        """Test execute_with_fallback when all methods fail"""
        def test_func(method=None):
            raise Exception("All methods fail")
        
        fallback_handler.method_selector.select_method = Mock(return_value=AutomationMethod.REQUESTS)
        fallback_handler.method_selector.get_fallback_method = Mock(return_value=AutomationMethod.WEBDRIVER)
        fallback_handler.method_selector.record_failure = Mock()
        
        with patch('time.sleep'):
            with pytest.raises(Exception, match="All methods fail"):
                fallback_handler.execute_with_fallback(test_func, "test_operation")
    
    def test_execute_with_fallback_circuit_breaker_open(self, fallback_handler):
        """Test execute_with_fallback with circuit breaker open"""
        # Open circuit for requests
        fallback_handler.circuit_breaker["requests"]["is_open"] = True
        fallback_handler.circuit_breaker["requests"]["failures"] = 5
        
        def test_func(method=None):
            return f"success_{method.value}"
        
        fallback_handler.method_selector.select_method = Mock(return_value=AutomationMethod.REQUESTS)
        fallback_handler.method_selector.get_fallback_method = Mock(return_value=AutomationMethod.WEBDRIVER)
        fallback_handler.method_selector.record_success = Mock()
        
        result = fallback_handler.execute_with_fallback(test_func, "test_operation")
        
        # Should have used WebDriver due to circuit breaker
        assert "webdriver" in result
    
    def test_should_retry_validation_error(self, fallback_handler):
        """Test should_retry returns False for validation errors"""
        error = ValidationError("Invalid input")
        
        should_retry = fallback_handler._should_retry(error, AutomationMethod.REQUESTS, "test_op")
        
        assert should_retry is False
    
    def test_should_retry_captcha_error(self, fallback_handler, captcha_error):
        """Test should_retry returns True for captcha errors"""
        should_retry = fallback_handler._should_retry(captcha_error, AutomationMethod.REQUESTS, "test_op")
        
        assert should_retry is True
    
    def test_should_retry_automation_blocked_error(self, fallback_handler, automation_blocked_error):
        """Test should_retry returns True for automation blocked errors"""
        should_retry = fallback_handler._should_retry(automation_blocked_error, AutomationMethod.REQUESTS, "test_op")
        
        assert should_retry is True
    
    def test_should_retry_network_error(self, fallback_handler):
        """Test should_retry returns True for network errors"""
        error = Exception("Connection timeout")
        
        should_retry = fallback_handler._should_retry(error, AutomationMethod.REQUESTS, "test_op")
        
        assert should_retry is True
    
    def test_should_retry_rate_limit_error(self, fallback_handler):
        """Test should_retry returns True for rate limit errors"""
        error = Exception("429 Too Many Requests")
        
        should_retry = fallback_handler._should_retry(error, AutomationMethod.REQUESTS, "test_op")
        
        assert should_retry is True
    
    def test_is_circuit_open_false_when_not_open(self, fallback_handler):
        """Test is_circuit_open returns False when circuit not open"""
        result = fallback_handler._is_circuit_open("requests")
        
        assert result is False
    
    def test_is_circuit_open_true_when_open(self, fallback_handler):
        """Test is_circuit_open returns True when circuit open"""
        fallback_handler.circuit_breaker["requests"]["is_open"] = True
        fallback_handler.circuit_breaker["requests"]["last_failure"] = time.time()
        
        result = fallback_handler._is_circuit_open("requests")
        
        assert result is True
    
    def test_is_circuit_open_timeout_recovery(self, fallback_handler):
        """Test circuit breaker timeout recovery"""
        fallback_handler.circuit_breaker["requests"]["is_open"] = True
        fallback_handler.circuit_breaker["requests"]["last_failure"] = time.time() - 400  # 400 seconds ago
        fallback_handler.circuit_breaker_timeout = 300  # 5 minutes
        
        result = fallback_handler._is_circuit_open("requests")
        
        assert result is False
        assert fallback_handler.circuit_breaker["requests"]["is_open"] is False
    
    def test_record_circuit_failure(self, fallback_handler):
        """Test recording circuit breaker failure"""
        fallback_handler._record_circuit_failure("requests")
        
        assert fallback_handler.circuit_breaker["requests"]["failures"] == 1
        assert fallback_handler.circuit_breaker["requests"]["last_failure"] > 0
    
    def test_record_circuit_failure_opens_circuit(self, fallback_handler):
        """Test circuit breaker opens after threshold failures"""
        # Record failures up to threshold
        for _ in range(fallback_handler.circuit_breaker_threshold):
            fallback_handler._record_circuit_failure("requests")
        
        assert fallback_handler.circuit_breaker["requests"]["is_open"] is True
        assert fallback_handler.circuit_breaker["requests"]["failures"] == 5
    
    def test_record_circuit_success(self, fallback_handler):
        """Test recording circuit breaker success"""
        # Setup some failures first
        fallback_handler.circuit_breaker["requests"]["failures"] = 3
        
        fallback_handler._record_circuit_success("requests")
        
        assert fallback_handler.circuit_breaker["requests"]["failures"] == 2
    
    def test_record_circuit_success_closes_circuit(self, fallback_handler):
        """Test circuit breaker closes after success"""
        fallback_handler.circuit_breaker["requests"]["failures"] = 1
        fallback_handler.circuit_breaker["requests"]["is_open"] = True
        
        fallback_handler._record_circuit_success("requests")
        
        assert fallback_handler.circuit_breaker["requests"]["failures"] == 0
        assert fallback_handler.circuit_breaker["requests"]["is_open"] is False
    
    def test_handle_circuit_breaker_recovery(self, fallback_handler):
        """Test circuit breaker recovery handling"""
        fallback_handler.circuit_breaker["requests"]["is_open"] = True
        fallback_handler.circuit_breaker["requests"]["failures"] = 3
        
        with patch('time.sleep') as mock_sleep:
            fallback_handler._handle_circuit_breaker_recovery("requests")
            
            # Should have slept for recovery delay
            mock_sleep.assert_called_once()
            call_args = mock_sleep.call_args[0]
            assert call_args[0] > 0  # Some delay was applied
    
    def test_fallback_context_manager_success(self, fallback_handler):
        """Test fallback context manager with success"""
        with fallback_handler.fallback_context("test_operation") as ctx:
            assert ctx == fallback_handler
            # Context should complete without exception
    
    def test_fallback_context_manager_exception(self, fallback_handler):
        """Test fallback context manager with exception"""
        with pytest.raises(ValueError):
            with fallback_handler.fallback_context("test_operation"):
                raise ValueError("Test error")
    
    def test_force_method(self, fallback_handler):
        """Test forcing specific method"""
        original_method = fallback_handler.config.preferred_method
        
        fallback_handler.force_method(AutomationMethod.WEBDRIVER)
        
        assert fallback_handler.config.preferred_method == "webdriver"
    
    def test_get_circuit_status(self, fallback_handler):
        """Test getting circuit breaker status"""
        # Setup some circuit state
        fallback_handler.circuit_breaker["requests"]["failures"] = 2
        fallback_handler.circuit_breaker["requests"]["last_failure"] = time.time() - 100
        
        status = fallback_handler.get_circuit_status()
        
        assert "requests" in status
        assert "webdriver" in status
        assert status["requests"]["failures"] == 2
        assert status["requests"]["time_since_failure"] > 90
    
    def test_reset_circuit_breakers(self, fallback_handler):
        """Test resetting all circuit breakers"""
        # Setup some failures
        fallback_handler.circuit_breaker["requests"]["failures"] = 5
        fallback_handler.circuit_breaker["requests"]["is_open"] = True
        fallback_handler.circuit_breaker["webdriver"]["failures"] = 2
        
        fallback_handler.reset_circuit_breakers()
        
        for method in ["requests", "webdriver"]:
            assert fallback_handler.circuit_breaker[method]["failures"] == 0
            assert fallback_handler.circuit_breaker[method]["is_open"] is False
    
    def test_health_check_healthy(self, fallback_handler):
        """Test health check when all methods healthy"""
        health = fallback_handler.health_check()
        
        assert health["overall_status"] == "healthy"
        assert health["methods"]["requests"]["status"] == "healthy"
        assert health["methods"]["webdriver"]["status"] == "healthy"
        assert len(health["recommendations"]) == 0
    
    def test_health_check_circuit_open(self, fallback_handler):
        """Test health check with circuit breaker open"""
        fallback_handler.circuit_breaker["requests"]["is_open"] = True
        
        health = fallback_handler.health_check()
        
        assert health["overall_status"] == "degraded"
        assert health["methods"]["requests"]["status"] == "circuit_open"
        assert len(health["recommendations"]) > 0
        assert "Circuit breaker open for requests" in health["recommendations"][0]
    
    def test_health_check_high_failure_rate(self, fallback_handler):
        """Test health check with high failure rate"""
        fallback_handler.circuit_breaker["webdriver"]["failures"] = 3  # Half of threshold
        
        health = fallback_handler.health_check()
        
        assert health["methods"]["webdriver"]["status"] == "warning"
        assert len(health["recommendations"]) > 0
        assert "High failure rate for webdriver" in health["recommendations"][0]


class TestFallbackHandlerIntegration:
    """Integration tests for FallbackHandler"""
    
    def test_realistic_captcha_fallback_scenario(self, test_config):
        """Test realistic captcha detection and fallback scenario"""
        handler = FallbackHandler(test_config)
        
        # Mock method selector behavior
        handler.method_selector.select_method = Mock(return_value=AutomationMethod.REQUESTS)
        handler.method_selector.get_fallback_method = Mock(return_value=AutomationMethod.WEBDRIVER)
        handler.method_selector.record_success = Mock()
        handler.method_selector.record_failure = Mock()
        
        call_count = 0
        
        def login_function(email, password, method=None):
            nonlocal call_count
            call_count += 1
            
            if method == AutomationMethod.REQUESTS:
                # Simulate captcha on requests method
                raise CaptchaRequiredError("Please complete captcha verification")
            elif method == AutomationMethod.WEBDRIVER:
                # Simulate success with WebDriver
                return {"authenticated": True, "method": "webdriver"}
        
        with patch('time.sleep'):  # Speed up test
            result = handler.execute_with_fallback(
                login_function, "login", 
                context={}, 
                email="test@example.com", 
                password="password123"
            )
        
        assert result["authenticated"] is True
        assert result["method"] == "webdriver"
        assert call_count == 2  # Should have tried both methods
        
        # Should have recorded failure and success
        handler.method_selector.record_failure.assert_called_with(
            "login", AutomationMethod.REQUESTS, pytest.any(CaptchaRequiredError)
        )
        handler.method_selector.record_success.assert_called_with(
            "login", AutomationMethod.WEBDRIVER
        )
    
    def test_circuit_breaker_protection_scenario(self, test_config):
        """Test circuit breaker protection in realistic scenario"""
        handler = FallbackHandler(test_config)
        handler.circuit_breaker_threshold = 2  # Lower threshold for testing
        
        handler.method_selector.select_method = Mock(return_value=AutomationMethod.REQUESTS)
        handler.method_selector.get_fallback_method = Mock(return_value=AutomationMethod.WEBDRIVER)
        handler.method_selector.record_failure = Mock()
        handler.method_selector.record_success = Mock()
        
        def failing_function(method=None):
            if method == AutomationMethod.REQUESTS:
                raise Exception("Service unavailable")
            return "webdriver_success"
        
        # First call should try requests and fail
        with patch('time.sleep'):
            try:
                handler.execute_with_fallback(failing_function, "test_operation")
            except Exception:
                pass
        
        # Second call should also try requests and fail, opening circuit
        with patch('time.sleep'):
            try:
                handler.execute_with_fallback(failing_function, "test_operation")
            except Exception:
                pass
        
        # Circuit should now be open for requests
        assert handler.circuit_breaker["requests"]["is_open"] is True
        
        # Third call should skip requests due to open circuit
        with patch('time.sleep'):
            result = handler.execute_with_fallback(failing_function, "test_operation")
        
        assert result == "webdriver_success"
        # Should have used WebDriver directly due to circuit breaker
    
    def test_multiple_operation_types_scenario(self, test_config):
        """Test handling multiple operation types with different behaviors"""
        handler = FallbackHandler(test_config)
        
        # Setup method selector to behave differently for different operations
        def mock_select_method(operation, context=None):
            if operation == "trading":
                return AutomationMethod.WEBDRIVER  # Trading prefers WebDriver
            else:
                return AutomationMethod.REQUESTS   # Others try requests first
        
        handler.method_selector.select_method = Mock(side_effect=mock_select_method)
        handler.method_selector.get_fallback_method = Mock(return_value=AutomationMethod.WEBDRIVER)
        handler.method_selector.record_success = Mock()
        
        def mock_operation(operation_type, method=None):
            return f"{operation_type}_success_{method.value}"
        
        # Test different operation types
        operations = ["login", "trading", "market_data", "account_info"]
        
        for operation in operations:
            result = handler.execute_with_fallback(
                mock_operation, operation, 
                context={}, 
                operation_type=operation
            )
            
            assert operation in result
            assert "success" in result
    
    def test_recovery_after_circuit_breaker_timeout(self, test_config):
        """Test recovery after circuit breaker timeout"""
        handler = FallbackHandler(test_config)
        handler.circuit_breaker_timeout = 1  # 1 second for testing
        
        # Open circuit breaker
        handler.circuit_breaker["requests"]["is_open"] = True
        handler.circuit_breaker["requests"]["last_failure"] = time.time() - 2  # 2 seconds ago
        
        def test_function(method=None):
            return f"success_{method.value}"
        
        handler.method_selector.select_method = Mock(return_value=AutomationMethod.REQUESTS)
        handler.method_selector.record_success = Mock()
        
        result = handler.execute_with_fallback(test_function, "test_operation")
        
        # Should have recovered and used requests
        assert "requests" in result
        assert handler.circuit_breaker["requests"]["is_open"] is False