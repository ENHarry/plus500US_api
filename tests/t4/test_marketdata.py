"""Tests for T4MarketData dispatch and subscription management."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from plus500us_client.t4.marketdata import T4MarketData
from plus500us_client.t4.errors import T4NotReadyError


def _make_server_msg(field_name, pb_value):
    """Build a minimal mock ServerMessage with one payload field set."""
    msg = MagicMock()
    msg.WhichOneof.return_value = field_name
    setattr(msg, field_name, pb_value)
    return msg


class TestAttach:
    def test_subscribe_without_attach_raises(self):
        md = T4MarketData()
        with pytest.raises(T4NotReadyError):
            md.subscribe_depth("CME", "ES", "ESZ25", on_depth=lambda d: None)

    def test_subscribe_without_auth_raises(self):
        md = T4MarketData()
        transport = MagicMock()
        transport.is_authenticated = False
        md.attach(transport)
        with pytest.raises(T4NotReadyError):
            md.subscribe_depth("CME", "ES", "ESZ25", on_depth=lambda d: None)


class TestDispatch:
    def _attached_md(self):
        md = T4MarketData()
        transport = MagicMock()
        transport.is_authenticated = True
        md.attach(transport)
        return md, transport

    def test_market_details_dispatched(self):
        md, _ = self._attached_md()
        received = []
        md.on_market_details(lambda info: received.append(info))

        # Build a fake MarketDetails pb
        pb = MagicMock()
        pb.exchange_id = "CME"
        pb.contract_id = "ES"
        pb.market_id = "ESZ25"
        pb.description = "E-Mini S&P 500"
        pb.currency = "USD"
        pb.decimals = 2
        pb.point_value.value = "0.5"
        pb.min_price_increment.value = "0.25"

        msg = _make_server_msg("market_details", pb)
        result = md.dispatch(msg)

        assert result is True
        assert len(received) == 1
        assert received[0].market_id == "ESZ25"
        assert received[0].description == "E-Mini S&P 500"

    def test_unhandled_field_returns_false(self):
        md, _ = self._attached_md()
        msg = _make_server_msg("login_response", MagicMock())
        assert md.dispatch(msg) is False

    def test_depth_callback_called_by_market_id(self):
        md, transport = self._attached_md()
        received_esz = []
        received_nqz = []

        # Patch the codec to avoid real bytes
        with patch("plus500us_client.t4.marketdata.build_market_depth_subscribe", return_value=b"FAKE"):
            md.subscribe_depth("CME", "ES", "ESZ25", on_depth=lambda d: received_esz.append(d))
            md.subscribe_depth("CME", "NQ", "NQZ25", on_depth=lambda d: received_nqz.append(d))

        # Simulate a market_depth message for ESZ25
        depth_pb = MagicMock()
        depth_pb.market_id = "ESZ25"
        depth_pb.bids = []
        depth_pb.asks = []
        depth_pb.trade_data = None
        msg = _make_server_msg("market_depth", depth_pb)
        md.dispatch(msg)

        assert len(received_esz) == 1
        assert len(received_nqz) == 0

    def test_subscription_reject_callback(self):
        md, _ = self._attached_md()
        rejected = []
        md.on_subscription_reject(lambda mid, r: rejected.append((mid, r)))

        reject_pb = MagicMock()
        reject_pb.market_id = "ESZ25"
        reject_pb.reason = "Not subscribed to exchange"
        msg = _make_server_msg("market_depth_subscribe_reject", reject_pb)
        md.dispatch(msg)

        assert rejected == [("ESZ25", "Not subscribed to exchange")]


class TestResubscribeRegistry:
    def test_register_on_subscribe(self):
        md = T4MarketData()
        transport = MagicMock()
        transport.is_authenticated = True
        md.attach(transport)

        with patch("plus500us_client.t4.marketdata.build_market_depth_subscribe", return_value=b"SUB"):
            md.subscribe_depth("CME", "ES", "ESZ25", on_depth=lambda d: None)

        transport.register_resubscribe.assert_called_once_with(b"SUB")
        transport.send.assert_called_once_with(b"SUB")

    def test_unregister_on_unsubscribe(self):
        md = T4MarketData()
        transport = MagicMock()
        transport.is_authenticated = True
        md.attach(transport)

        with patch("plus500us_client.t4.marketdata.build_market_depth_subscribe", return_value=b"SUB"):
            md.subscribe_depth("CME", "ES", "ESZ25", on_depth=lambda d: None)
            md.unsubscribe_depth("ESZ25")

        transport.unregister_resubscribe.assert_called_once_with(b"SUB")
