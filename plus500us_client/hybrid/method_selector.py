from __future__ import annotations
import logging
from typing import Dict, Any, Optional, Tuple
from enum import Enum

from ..requests.config import Config
from ..requests.errors import AutomationBlockedError, CaptchaRequiredError

logger = logging.getLogger(__name__)

class AutomationMethod(Enum):
    """Available automation methods"""
    WEBDRIVER = "webdriver"
    REQUESTS = "requests"
    AUTO = "auto"

class MethodSelector:
    """
    Intelligent method selection for Plus500 automation
    
    Determines whether to use WebDriver or requests based on:
    - User preference
    - Anti-bot detection
    - Captcha presence
    - Method availability
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.method_history: Dict[str, bool] = {}
        self.failure_count = 0
        self.max_failures = 3
        
    def select_method(self, operation: str, context: Optional[Dict[str, Any]] = None) -> AutomationMethod:
        """
        Select the optimal automation method for the given operation
        
        Args:
            operation: Operation name (e.g., "login", "trading", "market_data")
            context: Additional context for decision making
            
        Returns:
            Selected automation method
        """
        context = context or {}
        
        # Check user preference first
        preferred = self.config.preferred_method.lower()
        
        if preferred == "webdriver":
            logger.info(f"Using WebDriver for {operation} (user preference)")
            return AutomationMethod.WEBDRIVER
        elif preferred == "requests":
            logger.info(f"Using requests for {operation} (user preference)")
            return AutomationMethod.REQUESTS
        
        # Auto selection logic
        return self._auto_select_method(operation, context)
    
    def _auto_select_method(self, operation: str, context: Dict[str, Any]) -> AutomationMethod:
        """
        Automatically select method based on context and history
        
        Args:
            operation: Operation name
            context: Context information
            
        Returns:
            Selected automation method
        """
        # Check for captcha indicators
        if self._captcha_detected(context):
            logger.info(f"Captcha detected for {operation}, using WebDriver")
            return AutomationMethod.WEBDRIVER
        
        # Check for anti-bot detection
        if self._anti_bot_detected(context):
            logger.info(f"Anti-bot protection detected for {operation}, using WebDriver")
            return AutomationMethod.WEBDRIVER
        
        # Check historical failures
        if self._should_use_webdriver_based_on_history(operation):
            logger.info(f"Using WebDriver for {operation} based on failure history")
            return AutomationMethod.WEBDRIVER
        
        # Operation-specific logic
        if operation in ["login", "initial_auth"]:
            # Authentication often requires human-like behavior
            if self.failure_count > 1:
                logger.info(f"Using WebDriver for {operation} after {self.failure_count} failures")
                return AutomationMethod.WEBDRIVER
            else:
                logger.info(f"Trying requests for {operation} first")
                return AutomationMethod.REQUESTS
        
        elif operation in ["trading", "order_placement"]:
            # Trading is critical - prefer WebDriver for reliability
            logger.info(f"Using WebDriver for critical operation: {operation}")
            return AutomationMethod.WEBDRIVER
        
        elif operation in ["market_data", "account_info", "positions"]:
            # Data retrieval can try requests first
            logger.info(f"Using requests for data operation: {operation}")
            return AutomationMethod.REQUESTS
        
        # Default to WebDriver for unknown operations
        logger.info(f"Using WebDriver as default for unknown operation: {operation}")
        return AutomationMethod.WEBDRIVER
    
    def _captcha_detected(self, context: Dict[str, Any]) -> bool:
        """Check if captcha is detected in context"""
        return (
            context.get("captcha_present", False) or
            context.get("captcha_error", False) or
            "captcha" in str(context.get("error_message", "")).lower()
        )
    
    def _anti_bot_detected(self, context: Dict[str, Any]) -> bool:
        """Check if anti-bot protection is detected"""
        error_msg = str(context.get("error_message", "")).lower()
        status_code = context.get("status_code", 0)
        
        anti_bot_indicators = [
            "blocked", "forbidden", "access denied", "security check",
            "unusual activity", "automated", "bot detected", "rate limit"
        ]
        
        return (
            status_code in [403, 429, 503] or
            any(indicator in error_msg for indicator in anti_bot_indicators) or
            context.get("cloudflare_challenge", False) or
            context.get("rate_limited", False)
        )
    
    def _should_use_webdriver_based_on_history(self, operation: str) -> bool:
        """Check if WebDriver should be used based on failure history"""
        return (
            self.failure_count >= 2 or
            self.method_history.get(f"{operation}_requests_failed", False)
        )
    
    def record_success(self, operation: str, method: AutomationMethod) -> None:
        """Record successful operation"""
        self.method_history[f"{operation}_{method.value}_success"] = True
        
        if method == AutomationMethod.REQUESTS:
            # Reset failure count on requests success
            self.failure_count = max(0, self.failure_count - 1)
        
        logger.debug(f"Recorded success: {operation} with {method.value}")
    
    def record_failure(self, operation: str, method: AutomationMethod, 
                      error: Optional[Exception] = None) -> None:
        """Record failed operation"""
        self.method_history[f"{operation}_{method.value}_failed"] = True
        
        if method == AutomationMethod.REQUESTS:
            self.failure_count += 1
        
        # Analyze failure reason
        if error:
            if isinstance(error, CaptchaRequiredError):
                self.method_history["captcha_detected"] = True
            elif isinstance(error, AutomationBlockedError):
                self.method_history["anti_bot_detected"] = True
        
        logger.warning(f"Recorded failure: {operation} with {method.value}, error: {error}")
    
    def should_fallback(self, operation: str, current_method: AutomationMethod,
                       error: Optional[Exception] = None) -> bool:
        """
        Determine if we should fallback to alternative method
        
        Args:
            operation: Current operation
            current_method: Method that failed
            error: Exception that occurred
            
        Returns:
            True if fallback is recommended
        """
        # Record the failure
        self.record_failure(operation, current_method, error)
        
        # Don't fallback if already using WebDriver
        if current_method == AutomationMethod.WEBDRIVER:
            logger.info("Already using WebDriver, no fallback available")
            return False
        
        # Fallback conditions for requests -> WebDriver
        if current_method == AutomationMethod.REQUESTS:
            fallback_conditions = [
                isinstance(error, CaptchaRequiredError),
                isinstance(error, AutomationBlockedError),
                self.failure_count >= 2,
                self._is_authentication_error(error)
            ]
            
            if any(fallback_conditions):
                logger.info(f"Fallback recommended for {operation}: {error}")
                return True
        
        return False
    
    def _is_authentication_error(self, error: Optional[Exception]) -> bool:
        """Check if error is authentication-related"""
        if not error:
            return False
        
        error_msg = str(error).lower()
        auth_indicators = [
            "authentication", "unauthorized", "login", "credentials",
            "403", "401", "session", "cookie"
        ]
        
        return any(indicator in error_msg for indicator in auth_indicators)
    
    def get_fallback_method(self, current_method: AutomationMethod) -> Optional[AutomationMethod]:
        """
        Get fallback method for current method
        
        Args:
            current_method: Current method that failed
            
        Returns:
            Fallback method or None if no fallback available
        """
        if current_method == AutomationMethod.REQUESTS:
            return AutomationMethod.WEBDRIVER
        elif current_method == AutomationMethod.WEBDRIVER:
            # No fallback from WebDriver currently
            return None
        else:
            return AutomationMethod.WEBDRIVER
    
    def reset_history(self) -> None:
        """Reset method selection history"""
        self.method_history.clear()
        self.failure_count = 0
        logger.info("Method selection history reset")
    
    def get_method_stats(self) -> Dict[str, Any]:
        """Get method selection statistics"""
        return {
            "failure_count": self.failure_count,
            "history": self.method_history.copy(),
            "preferred_method": self.config.preferred_method,
            "webdriver_available": True  # TODO: Actually check WebDriver availability
        }