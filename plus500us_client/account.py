from __future__ import annotations
from .config import Config
from .session import SessionManager
from .models import Account

class AccountClient:
    def __init__(self, cfg: Config, sm: SessionManager):
        self.cfg = cfg
        self.sm = sm

    def get_account(self) -> Account:
        s = self.sm.session
        host = self.cfg.host_url
        r = s.get(host + "/ClientRequest/account", timeout=15)
        r.raise_for_status()
        return Account(**r.json())
