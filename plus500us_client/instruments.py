from __future__ import annotations
from typing import List, Optional
from .config import Config
from .session import SessionManager
from .models import Instrument
from .errors import InstrumentNotFound

class InstrumentsClient:
    def __init__(self, cfg: Config, sm: SessionManager):
        self.cfg = cfg
        self.sm = sm
        self._cache: dict[str, Instrument] = {}

    def list_instruments(self, market: Optional[str] = None) -> List[Instrument]:
        s = self.sm.session
        base = self.cfg.base_url
        r = s.get(base + "/ClientRequest/GetTradeInstruments", timeout=20)
        r.raise_for_status()
        items = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
        result = [Instrument(**it) for it in items]
        for ins in result:
            self._cache[ins.id] = ins
        return result

    def get_instrument(self, symbol_or_id: str) -> Instrument:
        for ins in self._cache.values():
            if ins.id == symbol_or_id or ins.symbol == symbol_or_id:
                return ins
        for ins in self.list_instruments():
            if ins.id == symbol_or_id or ins.symbol == symbol_or_id:
                return ins
        raise InstrumentNotFound(symbol_or_id)

    def resolve_contract(self, root: str, expiry: str) -> Instrument:
        symbol = f"{root}{expiry}"
        return self.get_instrument(symbol)
