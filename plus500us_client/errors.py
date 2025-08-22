class ClientError(Exception):
    pass

class AuthenticationError(ClientError):
    pass

class AuthorizationError(ClientError):
    pass

class AutomationBlockedError(ClientError):
    pass

class RateLimitedError(ClientError):
    pass

class OrderRejectError(ClientError):
    pass

class InstrumentNotFound(ClientError):
    pass

class ValidationError(ClientError):
    pass

class CaptchaRequiredError(ClientError):
    """Raised when the site demands human verification (captcha/bot check)."""
    pass

class PartialTakeProfitError(ClientError):
    """Raised when partial take profit validation fails."""
    pass

class RiskManagementError(ClientError):
    """Raised when risk management operations fail."""
    pass

class PositionSizeError(ValidationError):
    """Raised when position size validation fails."""
    pass
