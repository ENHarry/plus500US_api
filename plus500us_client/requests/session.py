from __future__ import annotations
import re
import threading
import json
from pathlib import Path
from http.cookiejar import LWPCookieJar
from typing import Optional, Dict, Any
import requests
from .config import Config
from .errors import AutomationBlockedError, AuthenticationError

class SessionManager:
    _lock = threading.Lock()
    _session: requests.Session | None = None
    _csrf_token: str | None = None

    def __init__(self, cfg: Config, *, cookie_path: Path | None = None, authenticated_session: requests.Session | None = None) -> None:
        self.cfg = cfg
        
        # Use project directory for session backup instead of home directory
        project_root = Path(__file__).resolve().parents[2]  # Go up from requests/ to plus500US_api/
        session_backup_dir = project_root / "session_backup"
        
        # Ensure session backup directory exists
        session_backup_dir.mkdir(exist_ok=True)
        
        self.cookie_path = cookie_path or (session_backup_dir / ".plus500us.cookies")
        self.session_data_path = session_backup_dir / ".plus500_session.json"
        self._plus500_session: Optional[Dict[str, str]] = None
        self._external_session = authenticated_session  # Store external authenticated session
        self._load_plus500_session()
        self._ensure_session()

    def _ensure_session(self) -> None:
        with self._lock:
            if self._session is None:
                # Use external authenticated session if provided
                if self._external_session is not None:
                    self._session = self._external_session
                    return
                
                # Create new session if no external session provided
                s = requests.Session()
                
                # Ensure cookie directory exists
                self.cookie_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Create and assign LWPCookieJar
                cookie_jar = LWPCookieJar(str(self.cookie_path))
                s.cookies = cookie_jar  # type: ignore[assignment]
                
                try:
                    s.cookies.load(ignore_discard=True, ignore_expires=True)  # type: ignore[attr-defined]
                except (FileNotFoundError, AttributeError):
                    pass
                s.headers.update({
                    "User-Agent": self.cfg.user_agent,
                    "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
                    "Accept-Language": self.cfg.accept_language,
                    "Origin": self.cfg.base_url,
                    "Referer": self.cfg.base_url,
                })
                self._session = s

    def set_authenticated_session(self, session: requests.Session) -> None:
        """Set an external authenticated session to use for API calls"""
        with self._lock:
            self._external_session = session
            self._session = session

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            self._ensure_session()
        return self._session  # type: ignore[return-value]

    def save_cookies(self) -> None:
        """Save cookies to file"""
        try:
            if isinstance(self.session.cookies, LWPCookieJar):
                # Ensure cookie directory exists
                self.cookie_path.parent.mkdir(parents=True, exist_ok=True)
                self.session.cookies.save(ignore_discard=True, ignore_expires=True)
        except Exception as e:
            print(f"Warning: Failed to save cookies: {e}")
            pass

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

    def _load_plus500_session(self) -> None:
        """Load Plus500 session data from file"""
        try:
            if self.session_data_path.exists():
                with open(self.session_data_path, 'r') as f:
                    self._plus500_session = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._plus500_session = None

    def _save_plus500_session(self) -> None:
        """Save Plus500 session data to file"""
        if self._plus500_session:
            try:
                # Ensure directory exists
                self.session_data_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(self.session_data_path, 'w') as f:
                    json.dump(self._plus500_session, f, indent=2)
            except Exception as e:
                # Log error but don't raise to avoid breaking the session
                print(f"Warning: Failed to save session data: {e}")
                pass

    def set_plus500_session(self, session_data: Dict[str, str]) -> None:
        """Set Plus500 session authentication data"""
        self._plus500_session = session_data.copy()
        self._save_plus500_session()

    def get_plus500_session(self) -> Optional[Dict[str, str]]:
        """Get Plus500 session authentication data"""
        return self._plus500_session.copy() if self._plus500_session else None

    def has_valid_plus500_session(self) -> bool:
        """Check if we have valid Plus500 session data"""
        # Check if we have an authenticated external session (from Plus500FuturesAuth)
        if self._external_session and len(self._external_session.cookies) > 0:
            return True
            
        # Check traditional Plus500 session data
        if not self._plus500_session:
            return False
        # Updated to check for new authentication parameters
        required_fields = ["UserSessionId", "WebTraderServiceId", "Hash"]
        return all(self._plus500_session.get(field) for field in required_fields)

    def clear_plus500_session(self) -> None:
        """Clear Plus500 session data"""
        self._plus500_session = None
        try:
            # Clear session data file
            if self.session_data_path.exists():
                self.session_data_path.unlink()
            
            # Clear cookie file
            if self.cookie_path.exists():
                self.cookie_path.unlink()
                
        except Exception as e:
            print(f"Warning: Failed to clear session files: {e}")
            pass

    def prepare_plus500_payload(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare request payload with Plus500 session data"""
        payload = dict(data)
        
        # If we have an external authenticated session, extract auth data from cookies
        if self._external_session is not None:
            auth_data = self._extract_auth_data_from_session()
            if auth_data:
                payload.update(auth_data)
                return payload
        
        # Fallback to stored session data
        if self.has_valid_plus500_session() and self._plus500_session:
            payload.update(self._plus500_session)
        else:
            # Last resort: create minimal session data for testing
            payload.update({
                "Platform": "WebTrader2",
                "Culture": "en-US",
                "TimeZone": "America/New_York"
            })
        
        return payload
    
    def _extract_auth_data_from_session(self) -> Dict[str, str]:
        """Extract authentication data from the authenticated session cookies"""
        if not self._external_session:
            return {}
        
        auth_data = {}
        
        # Extract session ID from ASP.NET session cookie
        for cookie in self._external_session.cookies:
            if cookie.name == 'ASP.NET_SessionId':
                auth_data['SessionID'] = cookie.value
            elif cookie.name == 'webvisitid':
                auth_data['UserSessionId'] = cookie.value
            elif cookie.name == 'LangCultureCode':
                auth_data['Culture'] = cookie.value
        
        # Add standard platform information
        auth_data.update({
            'Platform': 'WebTrader2',
            'Product': 'FuturesWeb',
            'TimeZone': 'America/New_York'
        })
        
        # If we don't have Culture from cookies, use default
        if 'Culture' not in auth_data:
            auth_data['Culture'] = 'en-US'
        
        return auth_data

    def make_plus500_request(self, endpoint: str, data: Optional[Dict[str, Any]] = None, 
                           method: str = "POST") -> requests.Response:
        """Make authenticated request to Plus500 endpoint"""
        if not endpoint.startswith("/ClientRequest/"):
            endpoint = f"/ClientRequest/{endpoint}"
        
        url = f"{self.cfg.host_url}{endpoint}"
        payload = self.prepare_plus500_payload(data or {})
        
        # Convert payload to form data format for Plus500
        if method.upper() == "POST":
            response = self.session.post(url, data=payload, timeout=30)
        else:
            response = self.session.get(url, params=payload, timeout=30)
        
        return response
