from __future__ import annotations
import re
import threading
from pathlib import Path
from http.cookiejar import LWPCookieJar
import requests
from .config import Config
from .errors import AutomationBlockedError

class SessionManager:
    _lock = threading.Lock()
    _session: requests.Session | None = None
    _csrf_token: str | None = None

    def __init__(self, cfg: Config, *, cookie_path: Path | None = None) -> None:
        self.cfg = cfg
        self.cookie_path = cookie_path or (Path.home() / ".plus500us.cookies")
        self._ensure_session()

    def _ensure_session(self) -> None:
        with self._lock:
            if self._session is None:
                s = requests.Session()
                s.cookies = LWPCookieJar(str(self.cookie_path))
                try:
                    s.cookies.load(ignore_discard=True, ignore_expires=True)
                except FileNotFoundError:
                    pass
                s.headers.update({
                    "User-Agent": self.cfg.user_agent,
                    "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
                    "Accept-Language": self.cfg.accept_language,
                    "Origin": self.cfg.base_url,
                    "Referer": self.cfg.base_url,
                })
                self._session = s

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            self._ensure_session()
        return self._session  # type: ignore[return-value]

    def save_cookies(self) -> None:
        if isinstance(self.session.cookies, LWPCookieJar):
            self.session.cookies.save(ignore_discard=True, ignore_expires=True)

    def set_csrf(self, token: str | None) -> None:
        self._csrf_token = token

    def inject_csrf(self, headers: dict) -> dict:
        if self._csrf_token:
            headers = dict(headers)
            headers["X-CSRF-Token"] = self._csrf_token
        return headers

    def detect_bot_block(self, html_text: str) -> None:
        if re.search(r"captcha|bot|are you human", html_text, re.I):
            raise AutomationBlockedError("Automation blocked by anti-bot/captcha. Manual login required.")
