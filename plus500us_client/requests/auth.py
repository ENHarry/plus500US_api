\
from __future__ import annotations
import getpass
from typing import Optional, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential_jitter
from .config import Config
from .session import SessionManager
from .errors import AuthenticationError, AuthorizationError, AutomationBlockedError, CaptchaRequiredError
from . import interactive
from .post_login import PostLoginDataService

class AuthClient:
    def __init__(self, cfg: Config, sm: SessionManager):
        self.cfg = cfg
        self.sm = sm

    def plus500_authenticate(self, email: Optional[str] = None, password: Optional[str] = None, 
                           account_type: str = 'demo') -> Dict[str, Any]:
        """
        Authenticate using Plus500 authentication system via futures_authenticate
        This method is deprecated, use futures_authenticate instead
        
        Args:
            email: Login email
            password: Login password  
            account_type: 'demo' or 'real'
            
        Returns:
            Authentication result with session data
        """
        # Redirect to the integrated futures authentication
        return self.futures_authenticate(email, password, debug=False)
    
    def futures_authenticate(self, email: Optional[str] = None, password: Optional[str] = None, 
                           debug: bool = False) -> Dict[str, Any]:
        """
        Authenticate using the production Plus500 US Futures authentication system
        Integrated version that works directly with SessionManager
        
        Args:
            email: Login email
            password: Login password  
            debug: Enable debug logging
            
        Returns:
            Dict with authentication status and session
        """

        if self.cfg.email and self.cfg.password:
            email_val = self.cfg.email
            password_val = self.cfg.password
        else:
            # Use provided credentials
            email_val = email
            password_val = password

        if not email_val or not password_val:
            raise AuthenticationError("Email and password are required")
        
        # Use the integrated Plus500FuturesAuth class
        from .plus500_futures_auth import Plus500FuturesAuth
        
        auth_client = Plus500FuturesAuth(debug=debug)
        result = auth_client.authenticate(email_val, password_val)
        
        if result['success'] and auth_client.get_authenticated_session():
            # Set the authenticated session in our SessionManager
            session = auth_client.get_authenticated_session()
            if session is not None:
                self.sm.set_authenticated_session(session)
            
        return {
            'success': result['success'],
            'session': auth_client.get_authenticated_session(),
            'message': result.get('error', 'Authentication successful' if result['success'] else 'Authentication failed'),
            'authenticated': result['success'],
            'session_data': result.get('session_data', {}),
            'steps': result.get('steps', {})
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(1, max=6))
    def login(self, email: Optional[str] = None, password: Optional[str] = None, totp_code: Optional[str] = None, 
              account_type: Optional[str] = None, *, interactive_mode: bool = False) -> dict:
        s = self.sm.session
        host = self.cfg.host_url
        base = self.cfg.base_url

        # Use provided account type or config default
        selected_account_type = account_type or self.cfg.account_type
        
        # Interactive account type selection if not specified
        if not account_type and interactive_mode:
            selected_account_type = self._prompt_account_type()

        r = s.get(base + "/trade?innerTags=_cc_&page=login", timeout=20)
        r.raise_for_status()
        if any(k in r.text.lower() for k in ("captcha", "are you human", "recaptcha")):
            if interactive_mode:
                raise CaptchaRequiredError("Captcha detected. Use interactive handoff to import browser session cookies.")
            raise CaptchaRequiredError("Captcha detected. Re-run login with interactive_mode=True and import cookies.")

        csrf = "PLACEHOLDER_CSRF"
        self.sm.set_csrf(csrf)

        # Enhanced credential loading with better validation
        email_val = email or self.cfg.email
        password_val = password or self.cfg.password
        
        # Only prompt for missing credentials if in interactive mode
        if interactive_mode:
            if not email_val:
                email_val = self._prompt_credential("Email")
            if not password_val:
                password_val = self._prompt_credential("Password", hidden=True)
        
        if not email_val or not password_val:
            if interactive_mode:
                raise AuthenticationError("Missing email/password. Authentication cancelled by user.")
            else:
                raise AuthenticationError("Missing email/password. Set PLUS500US_EMAIL and PLUS500US_PASSWORD environment variables, or add to config file, or use --interactive mode.")

        payload = {
            "email": email_val,
            "password": password_val,
            "account_type": selected_account_type
        }

        headers = self.sm.inject_csrf({})
        rr = s.post(host + "/ClientRequest/GetPostLoginInfoImm", json=payload, headers=headers, timeout=20)
        if rr.status_code == 401:
            raise AuthenticationError("Invalid credentials or second factor required.")
        if rr.status_code in (403,):
            raise AuthorizationError("Not authorized.")
        rr.raise_for_status()
        
        # Update config with selected account type
        self.cfg.account_type = selected_account_type
        self.sm.save_cookies()
        
        login_info: Dict[str, Any] = rr.json() if rr.text else {"account_type": selected_account_type}
        
        # Retrieve post-login data
        if interactive_mode:
            try:
                from .plus500_futures_auth import authenticate_plus500_futures, Plus500FuturesAuth
                post_login_service = PostLoginDataService(self.cfg, self.sm)
                post_login_data = post_login_service.retrieve_all_data()
                login_info["post_login_data"] = post_login_data
            except Exception as e:
                print(f"⚠ Warning: Could not retrieve post-login data: {e}")
        
        return login_info

    def interactive_handoff(self) -> None:
        s = self.sm.session
        base = self.cfg.base_url
        print(f"""
                === Interactive Browser Handoff ===
                1) Log in in your browser at: {base}/trade?innerTags=_cc_&page=login  (use DEMO for testing)
                2) After login, open DevTools → Network, pick any request to this domain.
                3) Right Click → Copy → Copy as cURL.
                4) Paste the FULL cURL here. We'll import cookies + headers.
                (Alternatively, press Enter and paste only the Cookie header value in the next prompt.)
                """)
        try:
            curl_cmd = input("Paste cURL (or press Enter to skip): ").strip()
        except EOFError:
            curl_cmd = ""

        applied = {}
        n = 0
        if curl_cmd:
            n, applied = interactive.import_from_curl(s, base, curl_cmd)
            if n == 0:
                print("[warn] No cookies found in cURL. Falling back to raw Cookie header...")

        if n == 0:
            raw_cookie = input("Paste only the Cookie header value (e.g., 'name=value; name2=value2'): ").strip()
            if not raw_cookie:
                raise CaptchaRequiredError("No cookies provided. Cannot proceed.")
            n = interactive.import_cookies_from_cookie_header(s, base, raw_cookie)

        self.sm.save_cookies()
        print(f"[ok] Imported {n} cookie(s). Applied headers: {applied}. Authenticated requests should now work.")

    def _prompt_account_type(self) -> str:
        """Interactive account type selection"""
        print("\nSelect account type:")
        print("1) Demo (recommended for testing)")
        print("2) Live (real money trading)")
        
        while True:
            try:
                choice = input("Enter choice (1-2): ").strip()
                if choice == "1":
                    return "demo"
                elif choice == "2":
                    return "live"
                else:
                    print("Please enter 1 or 2")
            except (EOFError, KeyboardInterrupt):
                raise AuthenticationError("Account type selection cancelled")

    def _prompt_credential(self, name: str, hidden: bool = False) -> Optional[str]:
        """Interactive credential input"""
        try:
            if hidden:
                value = getpass.getpass(f"Enter {name}: ")
            else:
                value = input(f"Enter {name}: ").strip()
            
            # Return None for empty strings to avoid infinite prompting
            return value if value else None
        except (EOFError, KeyboardInterrupt):
            return None

    def logout(self) -> None:
        s = self.sm.session
        host = self.cfg.host_url
        headers = self.sm.inject_csrf({})
        s.post(host + "/ClientRequest/Logout", headers=headers, timeout=15)
        self.sm.save_cookies()
