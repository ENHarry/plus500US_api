"""Tests for T4AccountFeed dispatch and state tracking."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from plus500us_client.t4.account import T4AccountFeed, AccountState
from plus500us_client.t4.errors import T4NotReadyError


def _make_feed(authenticated=True):
    feed = T4AccountFeed()
    transport = MagicMock()
    transport.is_authenticated = authenticated
    feed.attach(transport)
    return feed, transport


def _server_msg(field_name, pb_value):
    msg = MagicMock()
    msg.WhichOneof.return_value = field_name
    setattr(msg, field_name, pb_value)
    return msg


class TestSubscribe:
    def test_subscribe_without_auth_raises(self):
        feed, _ = _make_feed(authenticated=False)
        with pytest.raises(T4NotReadyError):
            feed.subscribe()

    def test_subscribe_sends_payload(self):
        feed, transport = _make_feed()
        with patch("plus500us_client.t4.account.build_account_subscribe", return_value=b"ACC_SUB"):
            feed.subscribe(account_ids=["ACC1"])
        transport.send.assert_called_once_with(b"ACC_SUB")
        transport.register_resubscribe.assert_called_once_with(b"ACC_SUB")


class TestDispatch:
    def test_account_update_applied(self):
        feed, _ = _make_feed()
        updates = []
        feed._update_callbacks.append(lambda s: updates.append(s))

        pb = MagicMock()
        pb.account_id = "ACC1"
        pb.balance = 10000.0
        pb.margin = 500.0
        pb.rpl = 200.0
        pb.fees_and_commissions = 5.0
        msg = _server_msg("account_update", pb)
        feed.dispatch(msg)

        assert len(updates) == 1
        state = updates[0]
        assert state.account_id == "ACC1"
        assert state.balance == 10000.0

    def test_account_position_applied(self):
        feed, _ = _make_feed()
        pb = MagicMock()
        pb.account_id = "ACC1"
        pb.market_id = "ESZ25"
        pb.buys = 3
        pb.sells = 1
        msg = _server_msg("account_position", pb)
        feed.dispatch(msg)

        state = feed.get_account("ACC1")
        assert state is not None
        assert state.net_position("ESZ25") == 2

    def test_snapshot_sets_ready(self):
        feed, _ = _make_feed()
        assert not feed.is_ready

        # Build a fake AccountSnapshot with one embedded update
        update_pb = MagicMock()
        update_pb.account_id = "ACC1"
        update_pb.balance = 5000.0
        update_pb.margin = 100.0
        update_pb.rpl = 0.0
        update_pb.fees_and_commissions = 0.0

        inner_msg = MagicMock()
        inner_msg.WhichOneof.return_value = "account_update"
        inner_msg.account_update = update_pb

        snap_pb = MagicMock()
        snap_pb.account_id = "ACC1"
        snap_pb.messages = [inner_msg]

        msg = _server_msg("account_snapshot", snap_pb)
        feed.dispatch(msg)

        assert feed.is_ready
        assert feed.wait_ready(timeout=0.1) is True

    def test_order_update_dispatched(self):
        feed, _ = _make_feed()
        received = []
        feed._order_callbacks.append(lambda m: received.append(m))

        for field in ("order_update", "order_update_failed", "order_update_status"):
            msg = _server_msg(field, MagicMock())
            feed.dispatch(msg)

        assert len(received) == 3

    def test_unknown_field_returns_false(self):
        feed, _ = _make_feed()
        msg = _server_msg("heartbeat", MagicMock())
        assert feed.dispatch(msg) is False


class TestAccountState:
    def test_net_position_zero_on_missing_market(self):
        state = AccountState("ACC1")
        assert state.net_position("ESZ25") == 0

    def test_repr(self):
        state = AccountState("ACC1")
        state.balance = 5000.0
        r = repr(state)
        assert "ACC1" in r
        assert "5000" in r
