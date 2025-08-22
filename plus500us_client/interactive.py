\
from __future__ import annotations
import shlex
from http.cookies import SimpleCookie
from urllib.parse import urlparse
from typing import Tuple, Optional
import requests

def _extract_header_from_curl(curl_cmd: str, header_name: str) -> Optional[str]:
    try:
        parts = shlex.split(curl_cmd)
    except Exception:
        return None
    vals = []
    for i, p in enumerate(parts):
        if p in ("-H", "--header") and i + 1 < len(parts):
            hv = parts[i+1]
            if hv.lower().startswith(header_name.lower() + ":"):
                vals.append(hv.split(":", 1)[1].strip())
    return vals[-1] if vals else None

def import_cookies_from_cookie_header(session: requests.Session, base_url: str, cookie_header: str) -> int:
    parsed = urlparse(base_url)
    domain = parsed.hostname or ""
    sc = SimpleCookie()
    sc.load(cookie_header)
    count = 0
    for name, morsel in sc.items():
        cookie = requests.cookies.create_cookie(
            name=name,
            value=morsel.value,
            domain=domain,
            path="/"
        )
        session.cookies.set_cookie(cookie)
        count += 1
    return count

def import_from_curl(session: requests.Session, base_url: str, curl_cmd: str) -> Tuple[int, dict]:
    cookie_header = _extract_header_from_curl(curl_cmd, "Cookie")
    ua = _extract_header_from_curl(curl_cmd, "User-Agent")
    al = _extract_header_from_curl(curl_cmd, "Accept-Language")

    applied = {}
    if ua:
        session.headers["User-Agent"] = ua
        applied["User-Agent"] = ua
    if al:
        session.headers["Accept-Language"] = al
        applied["Accept-Language"] = al

    if not cookie_header:
        return 0, applied
    n = import_cookies_from_cookie_header(session, base_url, cookie_header)
    return n, applied
