"""Protobuf encode/decode helpers for T4 messages.

Prices in the T4 API are carried as string-wrapped decimal values
(e.g. Price{value: "4200.50"}).  All conversion goes through Python's
``decimal.Decimal`` to avoid float rounding errors.
"""
from __future__ import annotations

import time
from decimal import Decimal, InvalidOperation
from typing import Optional

from .errors import T4ProtobufError

# Lazy-import the generated pb2 modules to keep startup fast and avoid
# circular imports.  Call _pb() once to get the module reference.
_service_pb2 = None
_auth_pb2 = None
_market_pb2 = None
_account_pb2 = None
_orderrouting_pb2 = None
_enums_pb2 = None
_price_pb2 = None


def _svc():
    global _service_pb2
    if _service_pb2 is None:
        from .proto.t4.v1 import service_pb2  # type: ignore
        _service_pb2 = service_pb2
    return _service_pb2


def _auth():
    global _auth_pb2
    if _auth_pb2 is None:
        from .proto.t4.v1.auth import auth_pb2  # type: ignore
        _auth_pb2 = auth_pb2
    return _auth_pb2


def _mkt():
    global _market_pb2
    if _market_pb2 is None:
        from .proto.t4.v1.market import market_pb2  # type: ignore
        _market_pb2 = market_pb2
    return _market_pb2


def _acct():
    global _account_pb2
    if _account_pb2 is None:
        from .proto.t4.v1.account import account_pb2  # type: ignore
        _account_pb2 = account_pb2
    return _account_pb2


def _order():
    global _orderrouting_pb2
    if _orderrouting_pb2 is None:
        from .proto.t4.v1.orderrouting import orderrouting_pb2  # type: ignore
        _orderrouting_pb2 = orderrouting_pb2
    return _orderrouting_pb2


def _enums():
    global _enums_pb2
    if _enums_pb2 is None:
        from .proto.t4.v1.common import enums_pb2  # type: ignore
        _enums_pb2 = enums_pb2
    return _enums_pb2


def _price():
    global _price_pb2
    if _price_pb2 is None:
        from .proto.t4.v1.common import price_pb2  # type: ignore
        _price_pb2 = price_pb2
    return _price_pb2


# ---------------------------------------------------------------------------
# Price / Decimal helpers
# ---------------------------------------------------------------------------

def price_to_decimal(price_msg) -> Optional[Decimal]:
    """Convert a Price protobuf message to Decimal.  Returns None if empty."""
    if price_msg is None:
        return None
    val = getattr(price_msg, "value", "")
    if not val:
        return None
    try:
        return Decimal(val)
    except InvalidOperation as exc:
        raise T4ProtobufError(f"Invalid price string: {val!r}") from exc


def decimal_to_price(value: Decimal):
    """Convert a Decimal to a Price protobuf message."""
    return _price().Price(value=str(value))


def decimal_msg_to_decimal(decimal_msg) -> Optional[Decimal]:
    """Convert a Decimal protobuf message to Python Decimal."""
    if decimal_msg is None:
        return None
    val = getattr(decimal_msg, "value", "")
    if not val:
        return None
    try:
        return Decimal(val)
    except InvalidOperation as exc:
        raise T4ProtobufError(f"Invalid decimal string: {val!r}") from exc


def decimal_to_decimal_msg(value: Decimal):
    """Convert a Python Decimal to a Decimal protobuf message."""
    return _price().Decimal(value=str(value))


# ---------------------------------------------------------------------------
# Envelope encode / decode
# ---------------------------------------------------------------------------

def encode_client_message(msg) -> bytes:
    """Serialise a ClientMessage to bytes."""
    try:
        return msg.SerializeToString()
    except Exception as exc:
        raise T4ProtobufError(f"Failed to encode ClientMessage: {exc}") from exc


def decode_server_message(data: bytes):
    """Deserialise bytes into a ServerMessage."""
    msg = _svc().ServerMessage()
    try:
        msg.ParseFromString(data)
    except Exception as exc:
        raise T4ProtobufError(f"Failed to decode ServerMessage: {exc}") from exc
    return msg


# ---------------------------------------------------------------------------
# Builder helpers – one function per outbound message type
# ---------------------------------------------------------------------------

def build_heartbeat() -> bytes:
    ts_ms = int(time.time() * 1000)
    hb = _svc().Heartbeat(timestamp=ts_ms)
    msg = _svc().ClientMessage(heartbeat=hb)
    return encode_client_message(msg)


def build_login_request(
    *,
    api_key: Optional[str] = None,
    firm: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    app_name: Optional[str] = None,
    app_license: Optional[str] = None,
) -> bytes:
    kwargs: dict = {}
    if api_key:
        kwargs["api_key"] = api_key
    else:
        if firm:
            kwargs["firm"] = firm
        if username:
            kwargs["username"] = username
        if password:
            kwargs["password"] = password
        if app_name:
            kwargs["app_name"] = app_name
        if app_license:
            kwargs["app_license"] = app_license

    login = _auth().LoginRequest(**kwargs)
    msg = _svc().ClientMessage(login_request=login)
    return encode_client_message(msg)


def build_market_depth_subscribe(
    exchange_id: str,
    contract_id: str,
    market_id: str,
    depth_levels: int = 10,
) -> bytes:
    enums = _enums()
    sub = _mkt().MarketDepthSubscribe(
        exchange_id=exchange_id,
        contract_id=contract_id,
        market_id=market_id,
        buffer=enums.DepthBuffer.Value("DEPTH_BUFFER_ALL"),
        depth_levels=enums.DepthLevels.Value(
            f"DEPTH_LEVELS_{depth_levels}" if depth_levels in (1, 5, 10) else "DEPTH_LEVELS_10"
        ),
    )
    msg = _svc().ClientMessage(market_depth_subscribe=sub)
    return encode_client_message(msg)


def build_mbo_subscribe(
    exchange_id: str,
    contract_id: str,
    market_id: str,
    subscribe: bool = True,
) -> bytes:
    sub = _mkt().MarketByOrderSubscribe(
        exchange_id=exchange_id,
        contract_id=contract_id,
        market_id=market_id,
        subscribe=subscribe,
    )
    msg = _svc().ClientMessage(market_by_order_subscribe=sub)
    return encode_client_message(msg)


def build_account_subscribe(
    account_ids: list[str],
    subscribe_all: bool = False,
) -> bytes:
    enums = _enums()
    sub = _acct().AccountSubscribe(
        subscribe=enums.AccountSubscribeType.Value("ACCOUNT_SUBSCRIBE"),
        subscribe_all_accounts=subscribe_all,
        account_id=account_ids,
    )
    msg = _svc().ClientMessage(account_subscribe=sub)
    return encode_client_message(msg)


def build_order_submit(
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
) -> bytes:
    enums = _enums()
    order_kwargs: dict = {
        "buy_sell": enums.BuySell.Value(buy_sell),
        "price_type": enums.PriceType.Value(price_type),
        "time_type": enums.TimeType.Value(time_type),
        "volume": volume,
    }
    if limit_price is not None:
        order_kwargs["limit_price"] = decimal_to_price(limit_price)
    if stop_price is not None:
        order_kwargs["stop_price"] = decimal_to_price(stop_price)
    if trail_distance is not None:
        order_kwargs["trail_distance"] = decimal_to_price(trail_distance)
    if tag is not None:
        order_kwargs["tag"] = tag

    order = _order().OrderSubmit.Order(**order_kwargs)

    submit_kwargs: dict = {
        "account_id": account_id,
        "market_id": market_id,
        "order_link": enums.OrderLink.Value("ORDER_LINK_NONE"),
        "manual_order_indicator": manual_order_indicator,
        "orders": [order],
    }
    if user_id is not None:
        submit_kwargs["user_id"] = user_id

    submit = _order().OrderSubmit(**submit_kwargs)
    msg = _svc().ClientMessage(order_submit=submit)
    return encode_client_message(msg)


def build_order_revise(
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
) -> bytes:
    revise_kwargs: dict = {"unique_id": unique_id}
    if volume is not None:
        revise_kwargs["volume"] = volume
    if limit_price is not None:
        revise_kwargs["limit_price"] = decimal_to_price(limit_price)
    if stop_price is not None:
        revise_kwargs["stop_price"] = decimal_to_price(stop_price)
    if trail_price is not None:
        revise_kwargs["trail_price"] = decimal_to_price(trail_price)
    if tag is not None:
        revise_kwargs["tag"] = tag

    revise = _order().OrderRevise.Revise(**revise_kwargs)
    msg_kwargs = {
        "user_id": user_id,
        "account_id": account_id,
        "market_id": market_id,
        "manual_order_indicator": manual_order_indicator,
        "revisions": [revise],
    }
    revise_msg = _order().OrderRevise(**msg_kwargs)
    msg = _svc().ClientMessage(order_revise=revise_msg)
    return encode_client_message(msg)


def build_order_pull(
    *,
    unique_id: str,
    account_id: str,
    market_id: str,
    user_id: str,
    tag: Optional[str] = None,
    manual_order_indicator: bool = True,
) -> bytes:
    pull_kwargs: dict = {"unique_id": unique_id}
    if tag is not None:
        pull_kwargs["tag"] = tag

    pull = _order().OrderPull.Pull(**pull_kwargs)
    pull_msg = _order().OrderPull(
        user_id=user_id,
        account_id=account_id,
        market_id=market_id,
        manual_order_indicator=manual_order_indicator,
        pulls=[pull],
    )
    msg = _svc().ClientMessage(order_pull=pull_msg)
    return encode_client_message(msg)
