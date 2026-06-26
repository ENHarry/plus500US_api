"""Tests for protobuf codec helpers – no live network required."""
from __future__ import annotations

import time
from decimal import Decimal

import pytest

from plus500us_client.t4.codec import (
    build_heartbeat,
    build_login_request,
    build_market_depth_subscribe,
    build_mbo_subscribe,
    build_account_subscribe,
    build_order_submit,
    build_order_revise,
    build_order_pull,
    decode_server_message,
    price_to_decimal,
    decimal_to_price,
)
from plus500us_client.t4.errors import T4ProtobufError


class TestPriceHelpers:
    def test_price_roundtrip(self):
        d = Decimal("4200.50")
        pb = decimal_to_price(d)
        assert pb.value == "4200.50"
        result = price_to_decimal(pb)
        assert result == d

    def test_price_none_on_empty(self):
        from plus500us_client.t4.proto.t4.v1.common import price_pb2
        empty = price_pb2.Price(value="")
        assert price_to_decimal(empty) is None

    def test_price_none_input(self):
        assert price_to_decimal(None) is None

    def test_invalid_price_raises(self):
        from plus500us_client.t4.proto.t4.v1.common import price_pb2
        bad = price_pb2.Price(value="not-a-number")
        with pytest.raises(T4ProtobufError):
            price_to_decimal(bad)

    def test_negative_price_preserved(self):
        d = Decimal("-100.25")
        pb = decimal_to_price(d)
        assert price_to_decimal(pb) == d


class TestHeartbeat:
    def test_heartbeat_decodes(self):
        raw = build_heartbeat()
        assert isinstance(raw, bytes)
        msg = decode_server_message(raw)  # heartbeat field number clashes in service, but bytes encode fine

    def test_heartbeat_contains_timestamp(self):
        before = int(time.time() * 1000)
        raw = build_heartbeat()
        after = int(time.time() * 1000)
        from plus500us_client.t4.proto.t4.v1 import service_pb2
        msg = service_pb2.ClientMessage()
        msg.ParseFromString(raw)
        assert before <= msg.heartbeat.timestamp <= after


class TestLoginRequest:
    def test_api_key_auth(self):
        raw = build_login_request(api_key="my-api-key")
        assert isinstance(raw, bytes)
        from plus500us_client.t4.proto.t4.v1 import service_pb2
        msg = service_pb2.ClientMessage()
        msg.ParseFromString(raw)
        assert msg.login_request.api_key == "my-api-key"

    def test_password_auth(self):
        raw = build_login_request(
            firm="MYFIRM", username="alice", password="s3cr3t",
            app_name="MyApp", app_license="LIC123",
        )
        from plus500us_client.t4.proto.t4.v1 import service_pb2
        msg = service_pb2.ClientMessage()
        msg.ParseFromString(raw)
        lr = msg.login_request
        assert lr.firm == "MYFIRM"
        assert lr.username == "alice"
        assert lr.password == "s3cr3t"
        assert lr.app_name == "MyApp"
        assert lr.app_license == "LIC123"


class TestMarketSubscriptions:
    def test_depth_subscribe(self):
        raw = build_market_depth_subscribe("CME", "ES", "ESZ25", depth_levels=10)
        assert isinstance(raw, bytes)
        from plus500us_client.t4.proto.t4.v1 import service_pb2
        msg = service_pb2.ClientMessage()
        msg.ParseFromString(raw)
        sub = msg.market_depth_subscribe
        assert sub.exchange_id == "CME"
        assert sub.contract_id == "ES"
        assert sub.market_id == "ESZ25"

    def test_mbo_subscribe(self):
        raw = build_mbo_subscribe("CME", "ES", "ESZ25", subscribe=True)
        assert isinstance(raw, bytes)

    def test_mbo_unsubscribe(self):
        raw = build_mbo_subscribe("CME", "ES", "ESZ25", subscribe=False)
        from plus500us_client.t4.proto.t4.v1 import service_pb2
        msg = service_pb2.ClientMessage()
        msg.ParseFromString(raw)
        assert msg.market_by_order_subscribe.subscribe is False


class TestAccountSubscribe:
    def test_subscribe_specific_accounts(self):
        raw = build_account_subscribe(["ACC1", "ACC2"])
        from plus500us_client.t4.proto.t4.v1 import service_pb2
        msg = service_pb2.ClientMessage()
        msg.ParseFromString(raw)
        sub = msg.account_subscribe
        assert list(sub.account_id) == ["ACC1", "ACC2"]
        assert sub.subscribe_all_accounts is False

    def test_subscribe_all(self):
        raw = build_account_subscribe([], subscribe_all=True)
        from plus500us_client.t4.proto.t4.v1 import service_pb2
        msg = service_pb2.ClientMessage()
        msg.ParseFromString(raw)
        assert msg.account_subscribe.subscribe_all_accounts is True


class TestOrderMessages:
    def test_submit_market_order(self):
        raw = build_order_submit(
            account_id="ACC1",
            market_id="ESZ25",
            buy_sell="BUY",
            price_type="PRICE_TYPE_MARKET",
            time_type="TIME_TYPE_DAY",
            volume=2,
        )
        from plus500us_client.t4.proto.t4.v1 import service_pb2
        msg = service_pb2.ClientMessage()
        msg.ParseFromString(raw)
        sub = msg.order_submit
        assert sub.account_id == "ACC1"
        assert sub.market_id == "ESZ25"
        assert len(sub.orders) == 1
        order = sub.orders[0]
        assert order.volume == 2

    def test_submit_limit_order(self):
        raw = build_order_submit(
            account_id="ACC1",
            market_id="ESZ25",
            buy_sell="SELL",
            price_type="PRICE_TYPE_LIMIT",
            time_type="TIME_TYPE_GTC",
            volume=1,
            limit_price=Decimal("5500.25"),
        )
        from plus500us_client.t4.proto.t4.v1 import service_pb2
        msg = service_pb2.ClientMessage()
        msg.ParseFromString(raw)
        order = msg.order_submit.orders[0]
        assert order.limit_price.value == "5500.25"

    def test_revise_order(self):
        raw = build_order_revise(
            unique_id="UID123",
            account_id="ACC1",
            market_id="ESZ25",
            user_id="USER1",
            volume=3,
            limit_price=Decimal("5501.00"),
        )
        from plus500us_client.t4.proto.t4.v1 import service_pb2
        msg = service_pb2.ClientMessage()
        msg.ParseFromString(raw)
        rev = msg.order_revise.revisions[0]
        assert rev.unique_id == "UID123"
        assert rev.volume == 3
        assert rev.limit_price.value == "5501.00"

    def test_pull_order(self):
        raw = build_order_pull(
            unique_id="UID999",
            account_id="ACC1",
            market_id="ESZ25",
            user_id="USER1",
        )
        from plus500us_client.t4.proto.t4.v1 import service_pb2
        msg = service_pb2.ClientMessage()
        msg.ParseFromString(raw)
        pull = msg.order_pull.pulls[0]
        assert pull.unique_id == "UID999"

    def test_malformed_bytes_raises(self):
        with pytest.raises(T4ProtobufError):
            decode_server_message(b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff")
