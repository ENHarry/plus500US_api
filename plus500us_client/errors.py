"""
Error classes for the Plus500US API client.
Re-exports all error classes for backward compatibility.
"""

from .requests.errors import (
    ClientError,
    AuthenticationError,
    AuthorizationError,
    AutomationBlockedError,
    RateLimitedError,
    OrderRejectError,
    InstrumentNotFound,
    ValidationError,
    TradingError,
    APIError,
    CaptchaRequiredError,
    PartialTakeProfitError,
    RiskManagementError,
    PositionSizeError,
)

__all__ = [
    'ClientError',
    'AuthenticationError',
    'AuthorizationError',
    'AutomationBlockedError',
    'RateLimitedError',
    'OrderRejectError',
    'InstrumentNotFound',
    'ValidationError',
    'TradingError',
    'APIError',
    'CaptchaRequiredError',
    'PartialTakeProfitError',
    'RiskManagementError',
    'PositionSizeError',
]