"""T4 SDK error hierarchy."""
from __future__ import annotations


class T4Error(Exception):
    """Base class for all T4 SDK errors."""


class T4ConnectionError(T4Error):
    """WebSocket connection failure."""


class T4AuthError(T4Error):
    """Authentication rejected by the T4 server."""

    def __init__(self, result_code: str, message: str = "") -> None:
        self.result_code = result_code
        super().__init__(f"Auth failed [{result_code}]: {message}")


class T4SubscriptionRejectError(T4Error):
    """Server rejected a market or account subscription."""

    def __init__(self, market_id: str, reason: str) -> None:
        self.market_id = market_id
        self.reason = reason
        super().__init__(f"Subscription rejected for {market_id!r}: {reason}")


class T4OrderError(T4Error):
    """Order routing failure."""

    def __init__(self, unique_id: str, status_detail: str) -> None:
        self.unique_id = unique_id
        self.status_detail = status_detail
        super().__init__(f"Order {unique_id!r} failed: {status_detail}")


class T4ValidationError(T4Error):
    """Local pre-flight validation failed before the message was sent."""


class T4LiveTradingNotEnabledError(T4Error):
    """Attempted to submit a live order without explicit opt-in."""


class T4NotReadyError(T4Error):
    """Client not yet authenticated or account not yet subscribed."""


class T4ProtobufError(T4Error):
    """Protobuf encode/decode failure."""
