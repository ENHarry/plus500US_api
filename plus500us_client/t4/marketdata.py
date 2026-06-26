"""T4 market data subscription management.

Wraps the transport layer to provide a high-level API for:
 - Market depth (Level 2) subscriptions
 - Market-by-order (MBO) subscriptions
 - Market detail caching
 - Trade tick callbacks

Each subscription registers its re-subscribe payload with the transport
so it survives reconnects automatically.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Callable, Dict, List, Optional

from .codec import (
    build_market_depth_subscribe,
    build_mbo_subscribe,
    price_to_decimal,
)
from .errors import T4NotReadyError, T4SubscriptionRejectError

logger = logging.getLogger(__name__)


class MarketDepthLevel:
    """Single price level from a MarketDepth update."""

    __slots__ = ("price", "volume", "orders", "implied_volume")

    def __init__(self, price: Optional[Decimal], volume: int, orders: int, implied_volume: int) -> None:
        self.price = price
        self.volume = volume
        self.orders = orders
        self.implied_volume = implied_volume

    def __repr__(self) -> str:
        return f"Level(price={self.price}, vol={self.volume}, ord={self.orders})"


class MarketDepthUpdate:
    """Parsed market depth snapshot."""

    def __init__(self, pb_msg) -> None:
        self.market_id: str = pb_msg.market_id
        self.bids: List[MarketDepthLevel] = [
            MarketDepthLevel(
                price_to_decimal(l.price), l.volume, l.orders, l.implied_volume
            )
            for l in pb_msg.bids
        ]
        self.asks: List[MarketDepthLevel] = [
            MarketDepthLevel(
                price_to_decimal(l.price), l.volume, l.orders, l.implied_volume
            )
            for l in pb_msg.asks
        ]
        td = pb_msg.trade_data
        self.last_trade_price: Optional[Decimal] = price_to_decimal(td.last_trade_price) if td else None
        self.last_trade_volume: int = td.last_trade_volume if td else 0
        self.total_volume: int = td.total_volume if td else 0
        self.bid: Optional[Decimal] = price_to_decimal(td.bid) if td else None
        self.ask: Optional[Decimal] = price_to_decimal(td.ask) if td else None

    @property
    def best_bid(self) -> Optional[Decimal]:
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> Optional[Decimal]:
        return self.asks[0].price if self.asks else None


class MarketTradeUpdate:
    """Parsed trade tick (MarketDepthTrade)."""

    def __init__(self, pb_msg) -> None:
        self.market_id: str = pb_msg.market_id
        self.price: Optional[Decimal] = price_to_decimal(pb_msg.price)
        self.volume: int = pb_msg.volume


class MarketDetailsInfo:
    """Parsed market details / contract metadata."""

    def __init__(self, pb_msg) -> None:
        self.exchange_id: str = pb_msg.exchange_id
        self.contract_id: str = pb_msg.contract_id
        self.market_id: str = pb_msg.market_id
        self.description: str = pb_msg.description
        self.currency: str = pb_msg.currency
        self.decimals: int = pb_msg.decimals
        self.point_value: Optional[Decimal] = price_to_decimal(pb_msg.point_value)
        self.min_price_increment: Optional[Decimal] = price_to_decimal(pb_msg.min_price_increment)

    def __repr__(self) -> str:
        return (
            f"MarketDetails({self.market_id!r}, {self.description!r}, "
            f"MPI={self.min_price_increment}, PV={self.point_value})"
        )


DepthCallback = Callable[[MarketDepthUpdate], None]
TradeCallback = Callable[[MarketTradeUpdate], None]
DetailsCallback = Callable[[MarketDetailsInfo], None]
RejectCallback = Callable[[str, str], None]  # (market_id, reason)


class T4MarketData:
    """Market data subscription manager.

    Attach to a ``T4Transport`` instance by calling ``attach(transport)``
    before subscribing.
    """

    def __init__(self) -> None:
        self._transport = None
        self._depth_callbacks: Dict[str, List[DepthCallback]] = {}
        self._trade_callbacks: Dict[str, List[TradeCallback]] = {}
        self._details_callbacks: List[DetailsCallback] = []
        self._reject_callbacks: List[RejectCallback] = []
        self._market_details: Dict[str, MarketDetailsInfo] = {}
        # Track active depth subscription payloads keyed by market_id
        self._depth_sub_payloads: Dict[str, bytes] = {}
        self._mbo_sub_payloads: Dict[str, bytes] = {}
        self._mbo_callbacks: Dict[str, list] = {}

    # ------------------------------------------------------------------
    # Attach / dispatch
    # ------------------------------------------------------------------

    def attach(self, transport) -> None:
        """Attach this manager to a T4Transport instance."""
        self._transport = transport

    def dispatch(self, server_msg) -> bool:
        """Process a ServerMessage.  Return True if the message was handled."""
        field = server_msg.WhichOneof("payload")

        if field == "market_details":
            info = MarketDetailsInfo(server_msg.market_details)
            self._market_details[info.market_id] = info
            for cb in self._details_callbacks:
                _safe_call(cb, info)
            return True

        if field == "market_depth":
            update = MarketDepthUpdate(server_msg.market_depth)
            for cb in self._depth_callbacks.get(update.market_id, []):
                _safe_call(cb, update)
            return True

        if field == "market_depth_trade":
            trade = MarketTradeUpdate(server_msg.market_depth_trade)
            for cb in self._trade_callbacks.get(trade.market_id, []):
                _safe_call(cb, trade)
            return True

        if field == "market_depth_subscribe_reject":
            r = server_msg.market_depth_subscribe_reject
            logger.warning("Market depth subscribe rejected: %s – %s", r.market_id, r.reason)
            for cb in self._reject_callbacks:
                _safe_call(cb, r.market_id, r.reason)
            return True

        if field == "market_by_order_subscribe_reject":
            r = server_msg.market_by_order_subscribe_reject
            logger.warning("MBO subscribe rejected: %s – %s", r.market_id, r.reason)
            for cb in self._reject_callbacks:
                _safe_call(cb, r.market_id, r.reason)
            return True

        if field in ("market_by_order_snapshot", "market_by_order_update", "market_by_order_trade",
                     "market_high_low", "market_price_limits", "market_settlement", "market_snapshot"):
            mid = getattr(getattr(server_msg, field), "market_id", "")
            for cb in self._mbo_callbacks.get(mid, []):
                _safe_call(cb, server_msg)
            return True

        return False

    # ------------------------------------------------------------------
    # Subscribe / unsubscribe
    # ------------------------------------------------------------------

    def subscribe_depth(
        self,
        exchange_id: str,
        contract_id: str,
        market_id: str,
        on_depth: DepthCallback,
        on_trade: Optional[TradeCallback] = None,
        depth_levels: int = 10,
    ) -> None:
        """Subscribe to market depth updates for *market_id*."""
        self._require_transport()
        payload = build_market_depth_subscribe(
            exchange_id, contract_id, market_id, depth_levels=depth_levels
        )
        self._depth_callbacks.setdefault(market_id, []).append(on_depth)
        if on_trade:
            self._trade_callbacks.setdefault(market_id, []).append(on_trade)
        self._depth_sub_payloads[market_id] = payload
        self._transport.register_resubscribe(payload)
        self._transport.send(payload)
        logger.info("Subscribed to market depth: %s", market_id)

    def unsubscribe_depth(self, market_id: str) -> None:
        """Unsubscribe from market depth for *market_id*."""
        payload = self._depth_sub_payloads.pop(market_id, None)
        if payload:
            self._transport.unregister_resubscribe(payload)
        self._depth_callbacks.pop(market_id, None)
        self._trade_callbacks.pop(market_id, None)

    def subscribe_mbo(
        self,
        exchange_id: str,
        contract_id: str,
        market_id: str,
        on_update: Callable,
    ) -> None:
        """Subscribe to market-by-order updates for *market_id*."""
        self._require_transport()
        payload = build_mbo_subscribe(exchange_id, contract_id, market_id, subscribe=True)
        self._mbo_callbacks.setdefault(market_id, []).append(on_update)
        self._mbo_sub_payloads[market_id] = payload
        self._transport.register_resubscribe(payload)
        self._transport.send(payload)
        logger.info("Subscribed to MBO: %s", market_id)

    def unsubscribe_mbo(
        self,
        exchange_id: str,
        contract_id: str,
        market_id: str,
    ) -> None:
        """Unsubscribe from market-by-order for *market_id*."""
        payload = build_mbo_subscribe(exchange_id, contract_id, market_id, subscribe=False)
        old = self._mbo_sub_payloads.pop(market_id, None)
        if old:
            self._transport.unregister_resubscribe(old)
        self._mbo_callbacks.pop(market_id, None)
        self._transport.send(payload)

    # ------------------------------------------------------------------
    # Event hooks
    # ------------------------------------------------------------------

    def on_market_details(self, cb: DetailsCallback) -> None:
        """Register a callback for MarketDetails messages."""
        self._details_callbacks.append(cb)

    def on_subscription_reject(self, cb: RejectCallback) -> None:
        """Register a callback for subscription rejection messages."""
        self._reject_callbacks.append(cb)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def get_market_details(self, market_id: str) -> Optional[MarketDetailsInfo]:
        return self._market_details.get(market_id)

    def _require_transport(self) -> None:
        if self._transport is None:
            raise T4NotReadyError("MarketData not attached to a transport. Call attach() first.")
        if not self._transport.is_authenticated:
            raise T4NotReadyError("Transport is not authenticated yet.")


def _safe_call(cb, *args) -> None:
    try:
        cb(*args)
    except Exception:
        logger.exception("Error in market data callback")
