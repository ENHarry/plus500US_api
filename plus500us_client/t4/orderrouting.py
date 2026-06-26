"""T4 order routing: submit, revise, pull with pre-flight validation.

Safety rules enforced locally (before any network call):
 - Account subscription must be confirmed (``account_feed.is_ready``).
 - Live trading requires ``config.live_trading_enabled == True``.
 - Dry-run mode logs the encoded payload but does not send it.
 - Volume must be a positive integer.
 - ``buy_sell`` must be "BUY" or "SELL".
 - Limit orders must supply a limit_price; stop orders must supply a stop_price.
 - ``market_id`` and ``account_id`` must be non-empty strings.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Callable, Dict, List, Optional

from .codec import (
    build_order_pull,
    build_order_revise,
    build_order_submit,
)
from .config import T4Config
from .errors import (
    T4LiveTradingNotEnabledError,
    T4NotReadyError,
    T4ValidationError,
)

logger = logging.getLogger(__name__)


# Map of price_type names that require a limit_price field
_LIMIT_PRICE_REQUIRED = {
    "PRICE_TYPE_LIMIT",
    "PRICE_TYPE_STOP_LIMIT",
    "PRICE_TYPE_LIMIT_CLOSE",
    "PRICE_TYPE_LIMIT_TOUCH",
    "PRICE_TYPE_TRAILING_STOP_LIMIT",
    "PRICE_TYPE_FUNARI_LIMIT",
}

_STOP_PRICE_REQUIRED = {
    "PRICE_TYPE_STOP",
    "PRICE_TYPE_STOP_LIMIT",
}

_TRAIL_REQUIRED = {
    "PRICE_TYPE_TRAILING_STOP",
    "PRICE_TYPE_TRAILING_STOP_LIMIT",
}


class OrderResult:
    """Lightweight representation of an order routing outcome."""

    def __init__(
        self,
        dry_run: bool = False,
        encoded_bytes: Optional[bytes] = None,
        submitted: bool = False,
    ) -> None:
        self.dry_run = dry_run
        self.encoded_bytes = encoded_bytes
        self.submitted = submitted

    def __repr__(self) -> str:
        if self.dry_run:
            return f"OrderResult(dry_run=True, bytes={len(self.encoded_bytes or b'')})"
        return f"OrderResult(submitted={self.submitted})"


OrderUpdateCb = Callable[[object], None]


class T4OrderRouting:
    """Order routing with validation and dry-run support."""

    def __init__(self, config: T4Config) -> None:
        self._cfg = config
        self._transport = None
        self._account_feed = None
        self._update_callbacks: List[OrderUpdateCb] = []

    # ------------------------------------------------------------------
    # Attach
    # ------------------------------------------------------------------

    def attach(self, transport, account_feed) -> None:
        self._transport = transport
        self._account_feed = account_feed

    # ------------------------------------------------------------------
    # Public order actions
    # ------------------------------------------------------------------

    def submit_order(
        self,
        *,
        account_id: str,
        market_id: str,
        buy_sell: str,
        price_type: str,
        time_type: str,
        volume: int,
        limit_price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        trail_distance: Optional[Decimal] = None,
        tag: Optional[str] = None,
        user_id: Optional[str] = None,
        manual_order_indicator: bool = True,
    ) -> OrderResult:
        """Build and send an order submit message.

        Returns an :class:`OrderResult`; in dry-run mode the bytes are
        returned without sending.
        """
        self._validate_ready(account_id)
        self._validate_order(
            account_id=account_id,
            market_id=market_id,
            buy_sell=buy_sell,
            price_type=price_type,
            time_type=time_type,
            volume=volume,
            limit_price=limit_price,
            stop_price=stop_price,
            trail_distance=trail_distance,
        )

        payload = build_order_submit(
            account_id=account_id,
            market_id=market_id,
            buy_sell=buy_sell,
            price_type=price_type,
            time_type=time_type,
            volume=volume,
            limit_price=limit_price,
            stop_price=stop_price,
            trail_distance=trail_distance,
            tag=tag,
            user_id=user_id,
            manual_order_indicator=manual_order_indicator,
        )

        if self._cfg.dry_run:
            logger.info(
                "[DRY-RUN] OrderSubmit: account=%s market=%s side=%s type=%s vol=%d",
                account_id, market_id, buy_sell, price_type, volume,
            )
            return OrderResult(dry_run=True, encoded_bytes=payload)

        self._require_live_if_live()
        self._transport.send(payload)
        logger.info(
            "OrderSubmit sent: account=%s market=%s side=%s type=%s vol=%d",
            account_id, market_id, buy_sell, price_type, volume,
        )
        return OrderResult(submitted=True, encoded_bytes=payload)

    def revise_order(
        self,
        *,
        unique_id: str,
        account_id: str,
        market_id: str,
        user_id: str,
        volume: Optional[int] = None,
        limit_price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        trail_price: Optional[Decimal] = None,
        tag: Optional[str] = None,
        manual_order_indicator: bool = True,
    ) -> OrderResult:
        """Revise (modify) an existing working order."""
        self._validate_ready(account_id)
        if not unique_id:
            raise T4ValidationError("unique_id is required for OrderRevise")
        if volume is not None and volume < 1:
            raise T4ValidationError(f"volume must be >= 1, got {volume}")

        payload = build_order_revise(
            unique_id=unique_id,
            account_id=account_id,
            market_id=market_id,
            user_id=user_id,
            volume=volume,
            limit_price=limit_price,
            stop_price=stop_price,
            trail_price=trail_price,
            tag=tag,
            manual_order_indicator=manual_order_indicator,
        )

        if self._cfg.dry_run:
            logger.info("[DRY-RUN] OrderRevise: unique_id=%s", unique_id)
            return OrderResult(dry_run=True, encoded_bytes=payload)

        self._require_live_if_live()
        self._transport.send(payload)
        logger.info("OrderRevise sent: unique_id=%s", unique_id)
        return OrderResult(submitted=True, encoded_bytes=payload)

    def pull_order(
        self,
        *,
        unique_id: str,
        account_id: str,
        market_id: str,
        user_id: str,
        tag: Optional[str] = None,
        manual_order_indicator: bool = True,
    ) -> OrderResult:
        """Cancel (pull) a working order."""
        self._validate_ready(account_id)
        if not unique_id:
            raise T4ValidationError("unique_id is required for OrderPull")

        payload = build_order_pull(
            unique_id=unique_id,
            account_id=account_id,
            market_id=market_id,
            user_id=user_id,
            tag=tag,
            manual_order_indicator=manual_order_indicator,
        )

        if self._cfg.dry_run:
            logger.info("[DRY-RUN] OrderPull: unique_id=%s", unique_id)
            return OrderResult(dry_run=True, encoded_bytes=payload)

        self._require_live_if_live()
        self._transport.send(payload)
        logger.info("OrderPull sent: unique_id=%s", unique_id)
        return OrderResult(submitted=True, encoded_bytes=payload)

    def flatten_position(
        self,
        *,
        account_id: str,
        market_id: str,
        exchange_id: str,
        user_id: str,
    ) -> OrderResult:
        """Submit a market order to flatten the net position.

        WARNING: This is a best-effort helper.  It reads the local account
        state to determine the net position.  Do not rely on this alone
        in production; validate positions independently.
        """
        if self._account_feed is None:
            raise T4NotReadyError("Account feed not attached")
        net = self._account_feed.net_position(account_id, market_id)
        if net == 0:
            logger.info("flatten_position: no open position for %s/%s", account_id, market_id)
            return OrderResult(submitted=False)
        buy_sell = "SELL" if net > 0 else "BUY"
        volume = abs(net)
        return self.submit_order(
            account_id=account_id,
            market_id=market_id,
            buy_sell=buy_sell,
            price_type="PRICE_TYPE_MARKET",
            time_type="TIME_TYPE_DAY",
            volume=volume,
            user_id=user_id,
            tag="flatten",
        )

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _validate_ready(self, account_id: str) -> None:
        if self._transport is None:
            raise T4NotReadyError("Order routing not attached to transport")
        if not self._transport.is_authenticated:
            raise T4NotReadyError("Transport not authenticated")
        if self._account_feed is None or not self._account_feed.is_ready:
            raise T4NotReadyError(
                "Account subscription not complete. Call account_feed.subscribe() "
                "and wait_ready() before submitting orders."
            )

    def _validate_order(
        self,
        *,
        account_id: str,
        market_id: str,
        buy_sell: str,
        price_type: str,
        time_type: str,
        volume: int,
        limit_price: Optional[Decimal],
        stop_price: Optional[Decimal],
        trail_distance: Optional[Decimal],
    ) -> None:
        if not account_id:
            raise T4ValidationError("account_id is required")
        if not market_id:
            raise T4ValidationError("market_id is required")
        if buy_sell not in ("BUY", "SELL"):
            raise T4ValidationError(f"buy_sell must be 'BUY' or 'SELL', got {buy_sell!r}")
        if not isinstance(volume, int) or volume < 1:
            raise T4ValidationError(f"volume must be a positive integer, got {volume!r}")

        if price_type in _LIMIT_PRICE_REQUIRED and limit_price is None:
            raise T4ValidationError(
                f"price_type={price_type!r} requires a limit_price"
            )
        if price_type in _STOP_PRICE_REQUIRED and stop_price is None:
            raise T4ValidationError(
                f"price_type={price_type!r} requires a stop_price"
            )
        if price_type in _TRAIL_REQUIRED and trail_distance is None:
            raise T4ValidationError(
                f"price_type={price_type!r} requires a trail_distance"
            )

        if limit_price is not None and limit_price <= 0:
            raise T4ValidationError(f"limit_price must be positive, got {limit_price}")
        if stop_price is not None and stop_price <= 0:
            raise T4ValidationError(f"stop_price must be positive, got {stop_price}")
        if trail_distance is not None and trail_distance <= 0:
            raise T4ValidationError(f"trail_distance must be positive, got {trail_distance}")

    def _require_live_if_live(self) -> None:
        if self._cfg.env == "live" and not self._cfg.live_trading_enabled:
            raise T4LiveTradingNotEnabledError(
                "Cannot send orders to live exchange: "
                "PLUS500_T4_LIVE_TRADING_ENABLED is not set to 'true'"
            )
