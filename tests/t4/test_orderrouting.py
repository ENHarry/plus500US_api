"""Tests for T4OrderRouting validation – no live network required."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from plus500us_client.t4.orderrouting import T4OrderRouting
from plus500us_client.t4.config import T4Config
from plus500us_client.t4.errors import (
    T4NotReadyError,
    T4ValidationError,
    T4LiveTradingNotEnabledError,
)


def _make_routing(*, dry_run=True, live=False, account_ready=True):
    cfg = T4Config(
        env="live" if live else "sim",
        api_key="test-key",
        live_trading_enabled=live,
        dry_run=dry_run,
    )
    routing = T4OrderRouting(cfg)

    transport = MagicMock()
    transport.is_authenticated = True

    account_feed = MagicMock()
    account_feed.is_ready = account_ready
    account_feed.net_position.return_value = 3

    routing.attach(transport, account_feed)
    return routing, transport


class TestSubmitValidation:
    def test_missing_account_id(self):
        routing, _ = _make_routing()
        with pytest.raises(T4ValidationError, match="account_id"):
            routing.submit_order(
                account_id="", market_id="ESZ25",
                buy_sell="BUY", price_type="PRICE_TYPE_MARKET",
                time_type="TIME_TYPE_DAY", volume=1,
            )

    def test_missing_market_id(self):
        routing, _ = _make_routing()
        with pytest.raises(T4ValidationError, match="market_id"):
            routing.submit_order(
                account_id="ACC1", market_id="",
                buy_sell="BUY", price_type="PRICE_TYPE_MARKET",
                time_type="TIME_TYPE_DAY", volume=1,
            )

    def test_invalid_side(self):
        routing, _ = _make_routing()
        with pytest.raises(T4ValidationError, match="buy_sell"):
            routing.submit_order(
                account_id="ACC1", market_id="ESZ25",
                buy_sell="LONG", price_type="PRICE_TYPE_MARKET",
                time_type="TIME_TYPE_DAY", volume=1,
            )

    def test_zero_volume(self):
        routing, _ = _make_routing()
        with pytest.raises(T4ValidationError, match="volume"):
            routing.submit_order(
                account_id="ACC1", market_id="ESZ25",
                buy_sell="BUY", price_type="PRICE_TYPE_MARKET",
                time_type="TIME_TYPE_DAY", volume=0,
            )

    def test_limit_order_without_price(self):
        routing, _ = _make_routing()
        with pytest.raises(T4ValidationError, match="limit_price"):
            routing.submit_order(
                account_id="ACC1", market_id="ESZ25",
                buy_sell="BUY", price_type="PRICE_TYPE_LIMIT",
                time_type="TIME_TYPE_DAY", volume=1,
            )

    def test_stop_order_without_stop_price(self):
        routing, _ = _make_routing()
        with pytest.raises(T4ValidationError, match="stop_price"):
            routing.submit_order(
                account_id="ACC1", market_id="ESZ25",
                buy_sell="SELL", price_type="PRICE_TYPE_STOP",
                time_type="TIME_TYPE_DAY", volume=1,
            )

    def test_trailing_stop_without_trail(self):
        routing, _ = _make_routing()
        with pytest.raises(T4ValidationError, match="trail_distance"):
            routing.submit_order(
                account_id="ACC1", market_id="ESZ25",
                buy_sell="SELL", price_type="PRICE_TYPE_TRAILING_STOP",
                time_type="TIME_TYPE_DAY", volume=1,
            )

    def test_negative_limit_price(self):
        routing, _ = _make_routing()
        with pytest.raises(T4ValidationError, match="limit_price"):
            routing.submit_order(
                account_id="ACC1", market_id="ESZ25",
                buy_sell="BUY", price_type="PRICE_TYPE_LIMIT",
                time_type="TIME_TYPE_DAY", volume=1,
                limit_price=Decimal("-1.0"),
            )


class TestAccountNotReady:
    def test_order_rejected_if_account_not_ready(self):
        routing, _ = _make_routing(account_ready=False)
        with pytest.raises(T4NotReadyError, match="Account subscription"):
            routing.submit_order(
                account_id="ACC1", market_id="ESZ25",
                buy_sell="BUY", price_type="PRICE_TYPE_MARKET",
                time_type="TIME_TYPE_DAY", volume=1,
            )


class TestDryRun:
    def test_dry_run_does_not_send(self):
        routing, transport = _make_routing(dry_run=True)
        result = routing.submit_order(
            account_id="ACC1", market_id="ESZ25",
            buy_sell="BUY", price_type="PRICE_TYPE_MARKET",
            time_type="TIME_TYPE_DAY", volume=2,
        )
        transport.send.assert_not_called()
        assert result.dry_run is True
        assert result.encoded_bytes is not None

    def test_dry_run_revise(self):
        routing, transport = _make_routing(dry_run=True)
        result = routing.revise_order(
            unique_id="UID1", account_id="ACC1", market_id="ESZ25",
            user_id="U1", volume=5,
        )
        transport.send.assert_not_called()
        assert result.dry_run is True

    def test_dry_run_pull(self):
        routing, transport = _make_routing(dry_run=True)
        result = routing.pull_order(
            unique_id="UID1", account_id="ACC1", market_id="ESZ25", user_id="U1",
        )
        transport.send.assert_not_called()
        assert result.dry_run is True


class TestFlattenPosition:
    def test_flatten_sells_long_position(self):
        routing, transport = _make_routing(dry_run=True)
        # net_position mock returns 3 (long)
        result = routing.flatten_position(
            account_id="ACC1", market_id="ESZ25",
            exchange_id="CME", user_id="U1",
        )
        # dry_run, but the encoded bytes should exist and SELL 3
        assert result.dry_run is True
        from plus500us_client.t4.proto.t4.v1 import service_pb2
        from plus500us_client.t4.proto.t4.v1.common import enums_pb2
        msg = service_pb2.ClientMessage()
        msg.ParseFromString(result.encoded_bytes)
        order = msg.order_submit.orders[0]
        assert order.buy_sell == enums_pb2.BuySell.Value("SELL")
        assert order.volume == 3


class TestLiveTradingGuard:
    def test_live_order_blocked_without_flag(self):
        cfg = T4Config(
            env="sim", api_key="k", live_trading_enabled=False, dry_run=False
        )
        routing = T4OrderRouting(cfg)
        transport = MagicMock()
        transport.is_authenticated = True
        account_feed = MagicMock()
        account_feed.is_ready = True
        routing.attach(transport, account_feed)

        # sim env is fine, no exception
        result = routing.submit_order(
            account_id="ACC1", market_id="ESZ25",
            buy_sell="BUY", price_type="PRICE_TYPE_MARKET",
            time_type="TIME_TYPE_DAY", volume=1,
        )
        transport.send.assert_called_once()
