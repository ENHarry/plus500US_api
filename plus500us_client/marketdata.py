from __future__ import annotations
import time
from typing import List
from .config import Config
from .session import SessionManager
from .models import Quote

class MarketDataClient:
    def __init__(self, cfg: Config, sm: SessionManager):
        self.cfg = cfg
        self.sm = sm
        self._last_request_ts = 0.0

    def _throttle(self) -> None:
        interval = max(0.3, self.cfg.poll_interval_ms / 1000.0)
        now = time.time()
        dt = now - self._last_request_ts
        if dt < interval:
            time.sleep(interval - dt)
        self._last_request_ts = time.time()

    def get_quote(self, instrument_id: str) -> Quote:
        self._throttle()
        s = self.sm.session
        base = self.cfg.base_url
        r = s.get(base + f"/api/quotes/{instrument_id}", timeout=15)
        r.raise_for_status()
        return Quote(**r.json())

    def get_quotes(self, instrument_ids: List[str]) -> List[Quote]:
        quotes = []
        for chunk in (instrument_ids[i:i+25] for i in range(0, len(instrument_ids), 25)):
            self._throttle()
            s = self.sm.session
            base = self.cfg.base_url
            r = s.post(base + "/api/quotes/batch", json={"ids": chunk}, timeout=20)
            r.raise_for_status()
            quotes.extend([Quote(**q) for q in r.json().get("quotes", [])])
        return quotes
