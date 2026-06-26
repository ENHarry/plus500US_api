"""T4 account feed subscription and state tracking.

Per the T4 docs, account subscription must be completed before order
routing is permitted.  This module tracks that state.

It also keeps a live view of:
 - AccountUpdate   (balance, margin, P&L)
 - AccountPosition (per-market position)
 - AccountDetails  (account settings)
 - AccountProfit   (UPL/RPL)
"""
from __future__ import annotations

import logging
import threading
from decimal import Decimal
from typing import Callable, Dict, List, Optional

from .codec import build_account_subscribe
from .errors import T4NotReadyError

logger = logging.getLogger(__name__)


class AccountState:
    """Live snapshot of a single account."""

    def __init__(self, account_id: str) -> None:
        self.account_id = account_id
        self.balance: Optional[float] = None
        self.margin: Optional[float] = None
        self.rpl: Optional[float] = None
        self.upl: Optional[float] = None
        self.available_cash: Optional[float] = None
        self.fees_and_commissions: Optional[float] = None
        self.positions: Dict[str, object] = {}  # market_id -> AccountPosition pb
        self.details: Optional[object] = None   # AccountDetails pb
        self.is_ready: bool = False

    def apply_update(self, pb) -> None:
        self.balance = pb.balance
        self.margin = pb.margin
        self.rpl = pb.rpl
        self.fees_and_commissions = pb.fees_and_commissions

    def apply_position(self, pb) -> None:
        self.positions[pb.market_id] = pb

    def apply_details(self, pb) -> None:
        self.details = pb

    def apply_profit(self, pb) -> None:
        if pb.HasField("upl"):
            self.upl = pb.upl
        if pb.HasField("available_cash"):
            self.available_cash = pb.available_cash

    def net_position(self, market_id: str) -> int:
        pos = self.positions.get(market_id)
        if pos is None:
            return 0
        return pos.buys - pos.sells

    def __repr__(self) -> str:
        return (
            f"AccountState(id={self.account_id!r}, balance={self.balance}, "
            f"margin={self.margin}, rpl={self.rpl})"
        )


AccountUpdateCallback = Callable[[AccountState], None]
OrderUpdateCallback = Callable[[object], None]   # raw OrderUpdate pb
SnapshotCallback = Callable[[str], None]          # account_id


class T4AccountFeed:
    """Account feed subscription manager.

    Usage::

        feed = T4AccountFeed()
        feed.attach(transport)
        feed.subscribe(account_ids=["ACC123"], on_update=my_handler)
        feed.wait_ready(timeout=15)  # blocks until snapshot received
    """

    def __init__(self) -> None:
        self._transport = None
        self._accounts: Dict[str, AccountState] = {}
        self._update_callbacks: List[AccountUpdateCallback] = []
        self._order_callbacks: List[OrderUpdateCallback] = []
        self._snapshot_callbacks: List[SnapshotCallback] = []
        self._ready_event = threading.Event()
        self._sub_payload: Optional[bytes] = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Attach / dispatch
    # ------------------------------------------------------------------

    def attach(self, transport) -> None:
        self._transport = transport

    def dispatch(self, server_msg) -> bool:
        field = server_msg.WhichOneof("payload")

        if field == "account_subscribe_response":
            r = server_msg.account_subscribe_response
            if not r.success:
                logger.error("Account subscribe rejected: %s", list(r.errors))
            return True

        if field == "account_snapshot":
            self._handle_snapshot(server_msg.account_snapshot)
            return True

        if field == "account_update":
            self._apply_update(server_msg.account_update)
            return True

        if field == "account_position":
            self._apply_position(server_msg.account_position)
            return True

        if field == "account_details":
            self._apply_details(server_msg.account_details)
            return True

        if field == "account_profit":
            self._apply_profit(server_msg.account_profit)
            return True

        if field in ("order_update", "order_update_failed", "order_update_status",
                     "order_update_trade", "order_update_trade_leg", "order_update_multi"):
            for cb in self._order_callbacks:
                _safe_call(cb, server_msg)
            return True

        return False

    # ------------------------------------------------------------------
    # Subscribe
    # ------------------------------------------------------------------

    def subscribe(
        self,
        account_ids: Optional[List[str]] = None,
        subscribe_all: bool = False,
        on_update: Optional[AccountUpdateCallback] = None,
        on_order_update: Optional[OrderUpdateCallback] = None,
        on_snapshot_ready: Optional[SnapshotCallback] = None,
    ) -> None:
        """Subscribe to account feeds."""
        self._require_transport()

        if on_update:
            self._update_callbacks.append(on_update)
        if on_order_update:
            self._order_callbacks.append(on_order_update)
        if on_snapshot_ready:
            self._snapshot_callbacks.append(on_snapshot_ready)

        ids = account_ids or []
        payload = build_account_subscribe(ids, subscribe_all=subscribe_all)
        self._sub_payload = payload
        self._transport.register_resubscribe(payload)
        self._transport.send(payload)
        logger.info("Account subscribe sent (accounts=%s, all=%s)", ids, subscribe_all)

    def unsubscribe(self) -> None:
        if self._sub_payload:
            self._transport.unregister_resubscribe(self._sub_payload)

    # ------------------------------------------------------------------
    # Readiness
    # ------------------------------------------------------------------

    def wait_ready(self, timeout: float = 30.0) -> bool:
        """Block until an account snapshot has been received, or timeout."""
        return self._ready_event.wait(timeout=timeout)

    @property
    def is_ready(self) -> bool:
        return self._ready_event.is_set()

    # ------------------------------------------------------------------
    # State accessors
    # ------------------------------------------------------------------

    def get_account(self, account_id: str) -> Optional[AccountState]:
        return self._accounts.get(account_id)

    def get_all_accounts(self) -> Dict[str, AccountState]:
        with self._lock:
            return dict(self._accounts)

    def net_position(self, account_id: str, market_id: str) -> int:
        state = self._accounts.get(account_id)
        return state.net_position(market_id) if state else 0

    # ------------------------------------------------------------------
    # Internal handlers
    # ------------------------------------------------------------------

    def _get_or_create(self, account_id: str) -> AccountState:
        with self._lock:
            if account_id not in self._accounts:
                self._accounts[account_id] = AccountState(account_id)
            return self._accounts[account_id]

    def _handle_snapshot(self, snap) -> None:
        account_id = snap.account_id
        state = self._get_or_create(account_id)
        # Process all messages embedded in the snapshot
        for msg in snap.messages:
            inner_field = msg.WhichOneof("payload")
            if inner_field == "account_update":
                state.apply_update(msg.account_update)
            elif inner_field == "account_position":
                state.apply_position(msg.account_position)
            elif inner_field == "account_details":
                state.apply_details(msg.account_details)
        state.is_ready = True
        self._ready_event.set()
        logger.info("Account snapshot received: %s", account_id)
        for cb in self._snapshot_callbacks:
            _safe_call(cb, account_id)
        for cb in self._update_callbacks:
            _safe_call(cb, state)

    def _apply_update(self, pb) -> None:
        state = self._get_or_create(pb.account_id)
        state.apply_update(pb)
        for cb in self._update_callbacks:
            _safe_call(cb, state)

    def _apply_position(self, pb) -> None:
        state = self._get_or_create(pb.account_id)
        state.apply_position(pb)

    def _apply_details(self, pb) -> None:
        state = self._get_or_create(pb.account_id)
        state.apply_details(pb)

    def _apply_profit(self, pb) -> None:
        state = self._get_or_create(pb.account_id)
        state.apply_profit(pb)

    def _require_transport(self) -> None:
        if self._transport is None:
            raise T4NotReadyError("AccountFeed not attached to a transport")
        if not self._transport.is_authenticated:
            raise T4NotReadyError("Transport not authenticated")


def _safe_call(cb, *args) -> None:
    try:
        cb(*args)
    except Exception:
        logger.exception("Error in account feed callback")
