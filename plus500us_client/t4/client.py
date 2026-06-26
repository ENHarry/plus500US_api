"""T4Client – the primary public API for the T4 WebSocket SDK.

Quick-start::

    from plus500us_client.t4 import T4Client, T4Config

    cfg = T4Config()          # reads env vars; defaults to simulator
    client = T4Client(cfg)
    client.connect()           # authenticates, starts heartbeat

    # Market data
    client.market_data.subscribe_depth(
        exchange_id="CME", contract_id="ES", market_id="ESZ25",
        on_depth=lambda d: print(d.best_bid, d.best_ask),
    )

    # Account
    client.account_feed.subscribe(account_ids=["ACC123"])
    client.account_feed.wait_ready()

    # Orders
    client.orders.submit_order(
        account_id="ACC123", market_id="ESZ25",
        buy_sell="BUY", price_type="PRICE_TYPE_LIMIT",
        time_type="TIME_TYPE_DAY", volume=1,
        limit_price=Decimal("5500.00"),
    )

    client.close()
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Callable, List, Optional

from .account import T4AccountFeed
from .config import T4Config
from .errors import T4NotReadyError
from .marketdata import T4MarketData
from .orderrouting import T4OrderRouting
from .transport import T4Transport

logger = logging.getLogger(__name__)


class T4Client:
    """High-level T4 API client.

    Composes transport, market data, account feed, and order routing
    into a single convenient interface.

    Parameters
    ----------
    config:
        A :class:`~plus500us_client.t4.config.T4Config` instance.
        If omitted, a default one is created from environment variables.
    """

    def __init__(self, config: Optional[T4Config] = None) -> None:
        self.config = config or T4Config()
        self.market_data = T4MarketData()
        self.account_feed = T4AccountFeed()
        self.orders = T4OrderRouting(self.config)

        self._transport: Optional[T4Transport] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def connect(
        self,
        timeout: float = 30.0,
        on_connected: Optional[Callable[[], None]] = None,
        on_disconnected: Optional[Callable[[Exception | None], None]] = None,
    ) -> None:
        """Connect to the T4 server and authenticate.

        Blocks until the :class:`~.transport.T4Transport` is authenticated
        or *timeout* seconds elapse.

        Raises
        ------
        T4ConnectionError
            If the connection or authentication fails within *timeout*.
        T4AuthError
            If the server rejects our credentials.
        """
        if self._transport is not None and self._transport.is_authenticated:
            logger.warning("connect() called on already-connected client; ignoring")
            return

        def _on_message(server_msg):
            if not self.market_data.dispatch(server_msg):
                self.account_feed.dispatch(server_msg)

        self._transport = T4Transport(
            config=self.config,
            on_message=_on_message,
            on_connected=on_connected,
            on_disconnected=on_disconnected,
        )

        self.market_data.attach(self._transport)
        self.account_feed.attach(self._transport)
        self.orders.attach(self._transport, self.account_feed)

        env_label = "SIMULATOR" if self.config.is_sim else "LIVE"
        logger.info("Connecting to T4 %s (%s)", env_label, self.config.ws_url)
        if self.config.dry_run:
            logger.warning("DRY-RUN mode active: order messages will NOT be sent")
        if not self.config.is_sim:
            logger.warning(
                "LIVE TRADING ACTIVE – orders will reach the exchange. "
                "Ensure you have completed Plus500/T4 certification."
            )

        self._transport.start(timeout=timeout)

    def close(self) -> None:
        """Cleanly shut down the client."""
        if self._transport:
            self._transport.close()
            self._transport = None
            logger.info("T4Client closed")

    def __enter__(self) -> "T4Client":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        return self._transport is not None and self._transport.is_authenticated

    @property
    def login_response(self):
        """The LoginResponse proto message from the last successful auth."""
        return self._transport.login_response if self._transport else None

    @property
    def session_id(self) -> Optional[str]:
        """Current session ID (never logged by the SDK)."""
        lr = self.login_response
        return lr.session_id if lr else None

    @property
    def user_id(self) -> Optional[str]:
        lr = self.login_response
        return lr.user_id if lr else None

    @property
    def firm_id(self) -> Optional[str]:
        lr = self.login_response
        return lr.firm_id if lr else None

    def _require_connected(self) -> None:
        if not self.is_connected:
            raise T4NotReadyError(
                "Client is not connected. Call connect() first."
            )

    # ------------------------------------------------------------------
    # Shortcut methods (delegates to sub-managers)
    # ------------------------------------------------------------------

    def subscribe_depth(
        self,
        exchange_id: str,
        contract_id: str,
        market_id: str,
        on_depth: Callable,
        on_trade: Optional[Callable] = None,
        depth_levels: int = 10,
    ) -> None:
        """Shortcut for ``client.market_data.subscribe_depth(...)``."""
        self.market_data.subscribe_depth(
            exchange_id, contract_id, market_id,
            on_depth=on_depth, on_trade=on_trade, depth_levels=depth_levels,
        )

    def subscribe_account(
        self,
        account_ids: Optional[List[str]] = None,
        subscribe_all: bool = False,
        on_update: Optional[Callable] = None,
        on_order_update: Optional[Callable] = None,
        on_snapshot_ready: Optional[Callable] = None,
    ) -> None:
        """Shortcut for ``client.account_feed.subscribe(...)``."""
        self.account_feed.subscribe(
            account_ids=account_ids,
            subscribe_all=subscribe_all,
            on_update=on_update,
            on_order_update=on_order_update,
            on_snapshot_ready=on_snapshot_ready,
        )

    def wait_account_ready(self, timeout: float = 30.0) -> bool:
        """Shortcut for ``client.account_feed.wait_ready(...)``."""
        return self.account_feed.wait_ready(timeout=timeout)

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
    ):
        """Shortcut for ``client.orders.submit_order(...)``."""
        return self.orders.submit_order(
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

    def revise_order(self, *, unique_id: str, account_id: str, market_id: str,
                     user_id: str, **kwargs):
        """Shortcut for ``client.orders.revise_order(...)``."""
        return self.orders.revise_order(
            unique_id=unique_id, account_id=account_id,
            market_id=market_id, user_id=user_id, **kwargs
        )

    def pull_order(self, *, unique_id: str, account_id: str, market_id: str,
                   user_id: str, **kwargs):
        """Shortcut for ``client.orders.pull_order(...)``."""
        return self.orders.pull_order(
            unique_id=unique_id, account_id=account_id,
            market_id=market_id, user_id=user_id, **kwargs
        )
