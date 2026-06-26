"""Tests for T4Config – no live network required."""
from __future__ import annotations

import os
import pytest

from plus500us_client.t4.config import T4Config, WS_SIM_URL, WS_LIVE_URL
from plus500us_client.t4.errors import T4Error


class TestT4Config:
    """Config construction and validation."""

    def _make(self, **env_overrides):
        """Build a T4Config with test env vars."""
        env = {
            "PLUS500_T4_ENV": "sim",
            "PLUS500_T4_API_KEY": "test-api-key",
            **env_overrides,
        }
        # Temporarily inject into os.environ via monkeypatching done in callers,
        # but here we pass through dataclass fields directly.
        return T4Config(
            env=env.get("PLUS500_T4_ENV", "sim"),
            api_key=env.get("PLUS500_T4_API_KEY"),
            firm=env.get("PLUS500_T4_FIRM"),
            username=env.get("PLUS500_T4_USERNAME"),
            password=env.get("PLUS500_T4_PASSWORD"),
            app_name=env.get("PLUS500_T4_APP_NAME"),
            app_license=env.get("PLUS500_T4_APP_LICENSE"),
            account_id=env.get("PLUS500_T4_ACCOUNT_ID"),
            live_trading_enabled=env.get("PLUS500_T4_LIVE_TRADING_ENABLED", "false").lower() == "true",
        )

    def test_sim_is_default(self):
        cfg = self._make()
        assert cfg.env == "sim"
        assert cfg.is_sim is True

    def test_ws_url_sim(self):
        cfg = self._make()
        assert cfg.ws_url == WS_SIM_URL

    def test_ws_url_live(self):
        cfg = self._make(
            PLUS500_T4_ENV="live",
            PLUS500_T4_LIVE_TRADING_ENABLED="true",
        )
        assert cfg.ws_url == WS_LIVE_URL
        assert cfg.is_sim is False

    def test_api_key_auth_detected(self):
        cfg = self._make(PLUS500_T4_API_KEY="my-key")
        assert cfg.has_api_key_auth() is True
        assert cfg.has_password_auth() is False

    def test_password_auth_detected(self):
        cfg = self._make(
            PLUS500_T4_API_KEY="",
            PLUS500_T4_FIRM="MYFIRM",
            PLUS500_T4_USERNAME="user",
            PLUS500_T4_PASSWORD="pass",
        )
        assert cfg.has_password_auth() is True
        assert cfg.has_api_key_auth() is False

    def test_no_credentials_raises(self):
        with pytest.raises(ValueError, match="No T4 credentials"):
            self._make(PLUS500_T4_API_KEY="")

    def test_live_without_flag_raises(self):
        with pytest.raises(ValueError, match="PLUS500_T4_LIVE_TRADING_ENABLED"):
            self._make(
                PLUS500_T4_ENV="live",
                PLUS500_T4_LIVE_TRADING_ENABLED="false",
            )

    def test_invalid_env_raises(self):
        with pytest.raises(ValueError, match="must be 'sim' or 'live'"):
            self._make(PLUS500_T4_ENV="staging")

    def test_repr_does_not_leak_credentials(self):
        cfg = self._make(PLUS500_T4_API_KEY="supersecret")
        r = repr(cfg)
        assert "supersecret" not in r
        assert "api_key" in r

    def test_dry_run_default_false(self):
        cfg = self._make()
        assert cfg.dry_run is False
