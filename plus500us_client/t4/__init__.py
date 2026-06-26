"""plus500us_client.t4 – T4 API WebSocket SDK for Plus500 Futures.

Primary entry points
--------------------
- :class:`T4Client`   – high-level facade (connect, subscribe, trade)
- :class:`T4Config`   – configuration loaded from environment variables

Endpoints (defined in :mod:`.config`)
--------------------------------------
- Simulator: ``wss://wss-sim.t4login.com/v1``  (default)
- Live:      ``wss://wss.t4login.com/v1``       (requires opt-in)

See docs/README.md for migration notes, installation, and examples.
"""
from .client import T4Client
from .config import T4Config, WS_LIVE_URL, WS_SIM_URL
from .errors import (
    T4AuthError,
    T4ConnectionError,
    T4Error,
    T4LiveTradingNotEnabledError,
    T4NotReadyError,
    T4OrderError,
    T4ProtobufError,
    T4SubscriptionRejectError,
    T4ValidationError,
)
from .marketdata import MarketDepthUpdate, MarketDetailsInfo, MarketTradeUpdate
from .account import AccountState
from .orderrouting import OrderResult

__all__ = [
    "T4Client",
    "T4Config",
    "WS_SIM_URL",
    "WS_LIVE_URL",
    "T4Error",
    "T4ConnectionError",
    "T4AuthError",
    "T4SubscriptionRejectError",
    "T4OrderError",
    "T4ValidationError",
    "T4LiveTradingNotEnabledError",
    "T4NotReadyError",
    "T4ProtobufError",
    "MarketDepthUpdate",
    "MarketDetailsInfo",
    "MarketTradeUpdate",
    "AccountState",
    "OrderResult",
]
