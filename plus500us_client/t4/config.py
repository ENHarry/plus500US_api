"""T4 API configuration loaded from environment variables."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env from project root on import
_project_root = Path(__file__).resolve().parents[3]
load_dotenv(_project_root / ".env", override=False)

logger = logging.getLogger(__name__)

# WebSocket endpoint constants (from docs.t4login.com)
WS_SIM_URL = "wss://wss-sim.t4login.com/v1"
WS_LIVE_URL = "wss://wss.t4login.com/v1"
WS_ADMIN_SIM_URL = "wss://wssadmin-sim.t4login.com/v1"
WS_ADMIN_LIVE_URL = "wss://wssadmin.t4login.com/v1"

HEARTBEAT_INTERVAL_SECONDS = 20
HEARTBEAT_TIMEOUT_CYCLES = 3


@dataclass
class T4Config:
    """Configuration for the T4 API client.

    All sensitive values must be loaded from environment variables.
    Never set credentials directly in code.
    """

    # Environment: "sim" (default/safe) or "live" (requires explicit opt-in)
    env: str = field(default_factory=lambda: os.getenv("PLUS500_T4_ENV", "sim"))

    # Authentication – at least one method required
    api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("PLUS500_T4_API_KEY") or None
    )
    firm: Optional[str] = field(
        default_factory=lambda: os.getenv("PLUS500_T4_FIRM") or None
    )
    username: Optional[str] = field(
        default_factory=lambda: os.getenv("PLUS500_T4_USERNAME") or None
    )
    password: Optional[str] = field(
        default_factory=lambda: os.getenv("PLUS500_T4_PASSWORD") or None
    )
    app_name: Optional[str] = field(
        default_factory=lambda: os.getenv("PLUS500_T4_APP_NAME") or None
    )
    app_license: Optional[str] = field(
        default_factory=lambda: os.getenv("PLUS500_T4_APP_LICENSE") or None
    )

    # Account defaults
    account_id: Optional[str] = field(
        default_factory=lambda: os.getenv("PLUS500_T4_ACCOUNT_ID") or None
    )
    default_market_id: Optional[str] = field(
        default_factory=lambda: os.getenv("PLUS500_T4_DEFAULT_MARKET_ID") or None
    )

    # Safety: live trading disabled by default
    live_trading_enabled: bool = field(
        default_factory=lambda: os.getenv(
            "PLUS500_T4_LIVE_TRADING_ENABLED", "false"
        ).lower()
        == "true"
    )

    # Dry-run: build messages but do not send order-routing messages
    dry_run: bool = field(
        default_factory=lambda: os.getenv("PLUS500_T4_DRY_RUN", "false").lower()
        == "true"
    )

    # Logging
    log_level: str = field(
        default_factory=lambda: os.getenv("PLUS500_T4_LOG_LEVEL", "INFO").upper()
    )

    # Connection tuning
    reconnect_max_attempts: int = 10
    reconnect_base_delay: float = 1.0   # seconds, doubles each retry up to max
    reconnect_max_delay: float = 60.0

    def __post_init__(self) -> None:
        self._validate()
        self._configure_logging()

    # ------------------------------------------------------------------
    # Derived helpers
    # ------------------------------------------------------------------

    @property
    def ws_url(self) -> str:
        """Return the correct WebSocket URL based on env setting."""
        if self.env == "live":
            return WS_LIVE_URL
        return WS_SIM_URL

    @property
    def is_sim(self) -> bool:
        return self.env != "live"

    def has_api_key_auth(self) -> bool:
        return bool(self.api_key)

    def has_password_auth(self) -> bool:
        return bool(self.firm and self.username and self.password)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate(self) -> None:
        if self.env not in ("sim", "live"):
            raise ValueError(
                f"PLUS500_T4_ENV must be 'sim' or 'live', got: {self.env!r}"
            )

        if self.env == "live" and not self.live_trading_enabled:
            raise ValueError(
                "Live environment selected but PLUS500_T4_LIVE_TRADING_ENABLED is not "
                "'true'. Set it explicitly to enable live trading."
            )

        if not self.has_api_key_auth() and not self.has_password_auth():
            raise ValueError(
                "No T4 credentials configured. Set PLUS500_T4_API_KEY, "
                "or PLUS500_T4_FIRM + PLUS500_T4_USERNAME + PLUS500_T4_PASSWORD."
            )

    def _configure_logging(self) -> None:
        numeric = getattr(logging, self.log_level, logging.INFO)
        logging.basicConfig(
            level=numeric,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
        logging.getLogger("plus500us_client.t4").setLevel(numeric)

    # ------------------------------------------------------------------
    # Safe repr – never logs credentials
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        auth = "api_key" if self.has_api_key_auth() else "password"
        return (
            f"T4Config(env={self.env!r}, auth={auth!r}, "
            f"account_id={self.account_id!r}, dry_run={self.dry_run})"
        )
