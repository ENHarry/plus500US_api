from __future__ import annotations
import logging
import time
from typing import Dict, Any, Optional, Callable, TypeVar, Union
from functools import wraps
from contextlib import contextmanager

from .method_selector import MethodSelector, AutomationMethod
from ..config import Config
from ..errors import (
    AutomationBlockedError, CaptchaRequiredError, RateLimitedError,
    AuthenticationError, OrderRejectError, ValidationError
)

logger = logging.getLogger(__name__)

T = TypeVar('T')

class FallbackHandler:
    """
    Handles automatic fallback between WebDriver and requests methods
    
    Provides:
    - Automatic retry with alternative methods
    - Error analysis and smart fallback decisions
    - Circuit breaker pattern for failed methods
    - Graceful degradation strategies
    """
    
    def __init__(self, config: Config, method_selector: Optional[MethodSelector] = None):
        self.config = config
        self.method_selector = method_selector or MethodSelector(config)
        self.retry_delays = [1, 2, 5]  # Exponential backoff delays
        self.max_retries = 3
        
        # Circuit breaker state
        self.circuit_breaker = {
            "requests": {"failures": 0, "last_failure": 0, "is_open": False},
            "webdriver": {"failures": 0, "last_failure": 0, "is_open": False}
        }
        self.circuit_breaker_threshold = 5
        self.circuit_breaker_timeout = 300  # 5 minutes
    
    def with_fallback(self, operation: str, context: Optional[Dict[str, Any]] = None):
        """
        Decorator for methods that should support automatic fallback
        
        Args:
            operation: Operation name for method selection
            context: Additional context for decision making
            
        Usage:
            @fallback_handler.with_fallback("login")
            def login_operation(self, method: AutomationMethod, **kwargs):
                # Implementation using the specified method
                pass
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            def wrapper(*args, **kwargs) -> T:
                return self.execute_with_fallback(
                    func, operation, context, *args, **kwargs
                )
            return wrapper
        return decorator
    
    def execute_with_fallback(self, func: Callable[..., T], operation: str,
                            context: Optional[Dict[str, Any]] = None,
                            *args, **kwargs) -> T:
        """
        Execute function with automatic fallback support
        
        Args:
            func: Function to execute
            operation: Operation name
            context: Context for method selection
            *args, **kwargs: Arguments to pass to function
            
        Returns:
            Function result
            
        Raises:
            Exception: Last exception if all methods fail
        """
        context = context or {}
        original_method = self.method_selector.select_method(operation, context)
        
        # Check circuit breaker
        if self._is_circuit_open(original_method.value):
            logger.warning(f"Circuit breaker open for {original_method.value}, using fallback")
            fallback_method = self.method_selector.get_fallback_method(original_method)
            if fallback_method and not self._is_circuit_open(fallback_method.value):
                original_method = fallback_method
            else:
                # All methods have open circuits, try anyway with backoff
                self._handle_circuit_breaker_recovery(original_method.value)
        
        methods_to_try = [original_method]
        
        # Add fallback method if available
        fallback_method = self.method_selector.get_fallback_method(original_method)
        if fallback_method and not self._is_circuit_open(fallback_method.value):
            methods_to_try.append(fallback_method)
        
        last_exception = None
        
        for attempt, method in enumerate(methods_to_try):
            logger.info(f"Attempting {operation} with {method.value} (attempt {attempt + 1})")
            
            try:
                # Inject method into kwargs for the function to use
                kwargs['method'] = method
                result = func(*args, **kwargs)
                
                # Record success
                self.method_selector.record_success(operation, method)
                self._record_circuit_success(method.value)
                
                if attempt > 0:
                    logger.info(f"Fallback successful: {operation} completed with {method.value}")
                
                return result
                
            except Exception as e:
                last_exception = e
                logger.warning(f"{operation} failed with {method.value}: {e}")
                
                # Record failure
                self.method_selector.record_failure(operation, method, e)
                self._record_circuit_failure(method.value)
                
                # Check if we should continue with fallback
                if attempt == len(methods_to_try) - 1:
                    # Last attempt, don't retry
                    break
                
                if not self._should_retry(e, method, operation):
                    # Don't retry this type of error
                    break
                
                # Wait before fallback
                if attempt < len(self.retry_delays):
                    delay = self.retry_delays[attempt]
                    logger.info(f"Waiting {delay}s before fallback to {methods_to_try[attempt + 1].value}")
                    time.sleep(delay)
        
        # All methods failed
        logger.error(f"All methods failed for {operation}. Last error: {last_exception}")
        raise last_exception or RuntimeError(f"All automation methods failed for {operation}")
    
    def _should_retry(self, error: Exception, method: AutomationMethod, operation: str) -> bool:
        """Determine if we should retry with fallback method"""
        
        # Don't retry certain types of errors
        non_retryable_errors = [
            ValidationError,  # User input validation errors
            ValueError,      # Programming errors
            TypeError        # Programming errors
        ]
        
        if any(isinstance(error, err_type) for err_type in non_retryable_errors):
            logger.debug(f"Not retrying {type(error).__name__} for {operation}")
            return False
        
        # Always retry these errors with fallback
        retryable_errors = [
            CaptchaRequiredError,
            AutomationBlockedError,
            RateLimitedError,
            AuthenticationError
        ]
        
        if any(isinstance(error, err_type) for err_type in retryable_errors):
            logger.debug(f"Retrying {type(error).__name__} with fallback")
            return True
        
        # Check error message for retry indicators
        error_msg = str(error).lower()
        retry_indicators = [
            "connection", "timeout", "network", "503", "502", "500",
            "temporary", "rate limit", "too many requests"
        ]
        
        should_retry = any(indicator in error_msg for indicator in retry_indicators)
        if should_retry:
            logger.debug(f"Retrying based on error message: {error_msg[:100]}")
        
        return should_retry
    
    def _is_circuit_open(self, method: str) -> bool:
        """Check if circuit breaker is open for method"""
        circuit = self.circuit_breaker.get(method, {})
        
        if not circuit.get("is_open", False):
            return False
        
        # Check if timeout period has passed
        if time.time() - circuit.get("last_failure", 0) > self.circuit_breaker_timeout:
            logger.info(f"Circuit breaker timeout expired for {method}, attempting recovery")
            circuit["is_open"] = False
            circuit["failures"] = 0
            return False
        
        return True
    
    def _record_circuit_failure(self, method: str) -> None:
        """Record failure for circuit breaker"""
        if method not in self.circuit_breaker:
            self.circuit_breaker[method] = {"failures": 0, "last_failure": 0, "is_open": False}
        
        circuit = self.circuit_breaker[method]
        circuit["failures"] += 1
        circuit["last_failure"] = time.time()
        
        if circuit["failures"] >= self.circuit_breaker_threshold:
            circuit["is_open"] = True
            logger.warning(
                f"Circuit breaker opened for {method} after {circuit['failures']} failures"
            )
    
    def _record_circuit_success(self, method: str) -> None:
        """Record success for circuit breaker"""
        if method in self.circuit_breaker:
            circuit = self.circuit_breaker[method]
            circuit["failures"] = max(0, circuit["failures"] - 1)
            
            if circuit["failures"] == 0:
                circuit["is_open"] = False
    
    def _handle_circuit_breaker_recovery(self, method: str) -> None:
        """Handle circuit breaker recovery attempt"""
        circuit = self.circuit_breaker.get(method, {})
        
        # Implement half-open state logic
        if circuit.get("is_open", False):
            recovery_delay = min(60, circuit.get("failures", 1) * 10)
            logger.info(f"Circuit breaker recovery delay: {recovery_delay}s for {method}")
            time.sleep(recovery_delay)
    
    @contextmanager
    def fallback_context(self, operation: str, context: Optional[Dict[str, Any]] = None):
        """Context manager for fallback operations"""
        context = context or {}
        start_time = time.time()
        
        try:
            logger.debug(f"Starting fallback context for {operation}")
            yield self
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Fallback context failed for {operation} after {duration:.2f}s: {e}")
            raise
            
        else:
            duration = time.time() - start_time
            logger.debug(f"Fallback context completed for {operation} in {duration:.2f}s")
    
    def force_method(self, method: AutomationMethod) -> None:
        """Force use of specific method (disables fallback temporarily)"""
        logger.info(f"Forcing method: {method.value}")
        # Temporarily update config
        original_method = self.config.preferred_method
        self.config.preferred_method = method.value
        
        # TODO: Implement method to restore original preference
    
    def get_circuit_status(self) -> Dict[str, Any]:
        """Get circuit breaker status for all methods"""
        status = {}
        for method, circuit in self.circuit_breaker.items():
            status[method] = {
                "is_open": circuit.get("is_open", False),
                "failures": circuit.get("failures", 0),
                "last_failure": circuit.get("last_failure", 0),
                "time_since_failure": time.time() - circuit.get("last_failure", 0)
            }
        return status
    
    def reset_circuit_breakers(self) -> None:
        """Reset all circuit breakers"""
        logger.info("Resetting all circuit breakers")
        for method in self.circuit_breaker:
            self.circuit_breaker[method] = {
                "failures": 0, "last_failure": 0, "is_open": False
            }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on all automation methods"""
        health = {
            "overall_status": "healthy",
            "methods": {},
            "recommendations": []
        }
        
        for method in ["requests", "webdriver"]:
            circuit = self.circuit_breaker.get(method, {})
            method_health = {
                "status": "healthy",
                "failures": circuit.get("failures", 0),
                "circuit_open": circuit.get("is_open", False)
            }
            
            if circuit.get("is_open", False):
                method_health["status"] = "circuit_open"
                health["overall_status"] = "degraded"
                health["recommendations"].append(
                    f"Circuit breaker open for {method} - fallback active"
                )
            elif circuit.get("failures", 0) > self.circuit_breaker_threshold // 2:
                method_health["status"] = "warning"
                health["recommendations"].append(
                    f"High failure rate for {method} - monitor closely"
                )
            
            health["methods"][method] = method_health
        
        return health