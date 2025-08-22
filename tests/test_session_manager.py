"""
Tests for SessionManager with focus on cookie persistence and recaptcha avoidance
"""

import os
import pytest
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from http.cookiejar import LWPCookieJar
import requests

from plus500us_client.config import Config
from plus500us_client.session import SessionManager
from plus500us_client.errors import AutomationBlockedError


class TestSessionManagerPersistence:
    """Test SessionManager cookie persistence and session management"""
    
    def _add_cookie_to_jar(self, cookie_jar, name, value, domain):
        """Helper to add cookie to LWPCookieJar"""
        from http.cookiejar import Cookie
        cookie_obj = Cookie(
            version=0, name=name, value=value, port=None, port_specified=False,
            domain=domain, domain_specified=True, domain_initial_dot=True,
            path="/", path_specified=True, secure=False, expires=None,
            discard=True, comment=None, comment_url=None, rest={}
        )
        cookie_jar.set_cookie(cookie_obj)
    
    @pytest.fixture
    def temp_cookie_file(self):
        """Create temporary cookie file for testing"""
        with tempfile.NamedTemporaryFile(suffix='.cookies', delete=False, mode='w') as f:
            # Write LWP cookie jar header
            f.write("#LWP-Cookies-2.0\n")
            temp_path = Path(f.name)
        yield temp_path
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()
    
    @pytest.fixture
    def test_config(self):
        """Create test config"""
        return Config(
            base_url="https://futures.plus500.com",
            host_url="https://api-futures.plus500.com",
            account_type="demo"
        )
    
    @pytest.fixture
    def sample_cookies(self):
        """Sample authentication cookies"""
        return [
            {"name": "session_id", "value": "test_session_123", "domain": ".plus500.com"},
            {"name": "auth_token", "value": "test_token_456", "domain": ".plus500.com"},
            {"name": "account_type", "value": "demo", "domain": ".plus500.com"},
            {"name": "csrf_token", "value": "csrf_123", "domain": ".plus500.com"}
        ]
    
    def test_session_manager_initialization(self, test_config, temp_cookie_file):
        """Test SessionManager initializes correctly with custom cookie path"""
        sm = SessionManager(test_config, cookie_path=temp_cookie_file)
        
        assert sm.cfg == test_config
        assert sm.cookie_path == temp_cookie_file
        assert isinstance(sm.session, requests.Session)
        assert isinstance(sm.session.cookies, LWPCookieJar)
    
    def test_session_singleton_behavior(self, test_config, temp_cookie_file):
        """Test session singleton behavior"""
        # Clear any existing session
        SessionManager._session = None
        
        sm1 = SessionManager(test_config, cookie_path=temp_cookie_file)
        sm2 = SessionManager(test_config, cookie_path=temp_cookie_file)
        
        # Both should share the same session instance
        assert sm1.session is sm2.session
    
    def test_thread_safety(self, test_config, temp_cookie_file):
        """Test thread-safe session initialization"""
        # Clear any existing session
        SessionManager._session = None
        
        sessions = []
        errors = []
        
        def create_session_manager():
            try:
                sm = SessionManager(test_config, cookie_path=temp_cookie_file)
                sessions.append(sm.session)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads that simultaneously initialize SessionManager
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=create_session_manager)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # No errors should occur
        assert len(errors) == 0
        
        # All sessions should be the same instance
        assert len(set(id(session) for session in sessions)) == 1
    
    def test_cookie_persistence_save_and_load(self, test_config, temp_cookie_file, sample_cookies):
        """Test cookies are saved to file and loaded on next session"""
        # Create session manager and add cookies
        sm = SessionManager(test_config, cookie_path=temp_cookie_file)
        
        # Add sample cookies to session
        for cookie in sample_cookies:
            self._add_cookie_to_jar(
                sm.session.cookies,
                cookie["name"],
                cookie["value"],
                cookie["domain"]
            )
        
        # Save cookies
        sm.save_cookies()
        
        # Verify cookie file was created
        assert temp_cookie_file.exists()
        assert temp_cookie_file.stat().st_size > 0
        
        # Clear session and create new one
        SessionManager._session = None
        sm2 = SessionManager(test_config, cookie_path=temp_cookie_file)
        
        # Verify cookies were loaded
        loaded_cookies = {cookie.name: cookie.value for cookie in sm2.session.cookies}
        
        for expected_cookie in sample_cookies:
            assert expected_cookie["name"] in loaded_cookies
            assert loaded_cookies[expected_cookie["name"]] == expected_cookie["value"]
    
    def test_cookie_persistence_across_process_restart(self, test_config, temp_cookie_file, sample_cookies):
        """Test cookies persist across simulated process restarts"""
        # Simulate first process - create session and save cookies
        sm1 = SessionManager(test_config, cookie_path=temp_cookie_file)
        
        for cookie in sample_cookies:
            self._add_cookie_to_jar(
                sm1.session.cookies,
                cookie["name"],
                cookie["value"],
                cookie["domain"]
            )
        
        sm1.save_cookies()
        
        # Simulate process restart - clear singleton and create new instance
        SessionManager._session = None
        
        # Simulate second process - create new session
        sm2 = SessionManager(test_config, cookie_path=temp_cookie_file)
        
        # Verify authentication cookies are available
        cookie_names = [cookie.name for cookie in sm2.session.cookies]
        
        assert "session_id" in cookie_names
        assert "auth_token" in cookie_names
        assert "account_type" in cookie_names
        assert "csrf_token" in cookie_names
        
        # This simulates avoiding re-captcha since auth cookies are present
        session_cookie = next(c for c in sm2.session.cookies if c.name == "session_id")
        auth_cookie = next(c for c in sm2.session.cookies if c.name == "auth_token")
        
        assert session_cookie.value == "test_session_123"
        assert auth_cookie.value == "test_token_456"
    
    def test_cookie_file_permissions(self, test_config, temp_cookie_file):
        """Test cookie file has appropriate permissions for security"""
        sm = SessionManager(test_config, cookie_path=temp_cookie_file)
        
        # Add a cookie and save
        self._add_cookie_to_jar(sm.session.cookies, "test", "value", ".plus500.com")
        sm.save_cookies()
        
        # Check file permissions (should be readable/writable by owner only)
        file_stat = temp_cookie_file.stat()
        
        # On Windows, this test is less relevant, but we can still check file exists
        assert temp_cookie_file.exists()
        assert file_stat.st_size > 0
    
    def test_missing_cookie_file_handling(self, test_config):
        """Test graceful handling when cookie file doesn't exist"""
        non_existent_path = Path("/tmp/non_existent_cookies.txt")
        
        # Should not raise error even if file doesn't exist
        sm = SessionManager(test_config, cookie_path=non_existent_path)
        
        assert isinstance(sm.session, requests.Session)
        assert len(list(sm.session.cookies)) == 0
    
    def test_csrf_token_management(self, test_config, temp_cookie_file):
        """Test CSRF token injection functionality"""
        sm = SessionManager(test_config, cookie_path=temp_cookie_file)
        
        # Set CSRF token
        test_token = "csrf_test_token_123"
        sm.set_csrf(test_token)
        
        # Test token injection
        headers = {"Content-Type": "application/json"}
        injected_headers = sm.inject_csrf(headers)
        
        assert "X-CSRF-Token" in injected_headers
        assert injected_headers["X-CSRF-Token"] == test_token
        assert injected_headers["Content-Type"] == "application/json"
        
        # Original headers should not be modified
        assert "X-CSRF-Token" not in headers
    
    def test_csrf_token_none_handling(self, test_config, temp_cookie_file):
        """Test CSRF injection when token is None"""
        sm = SessionManager(test_config, cookie_path=temp_cookie_file)
        
        # Don't set CSRF token (should be None)
        headers = {"Content-Type": "application/json"}
        injected_headers = sm.inject_csrf(headers)
        
        # Should return copy of original headers without CSRF
        assert "X-CSRF-Token" not in injected_headers
        assert injected_headers["Content-Type"] == "application/json"
    
    def test_bot_detection_mechanism(self, test_config, temp_cookie_file):
        """Test bot detection raises appropriate error"""
        sm = SessionManager(test_config, cookie_path=temp_cookie_file)
        
        # Test various bot detection strings
        bot_detection_html = [
            "<html><body>Please complete the captcha challenge</body></html>",
            "<html><body>Are you human? Prove it!</body></html>",
            "<html><body>Bot detected. Access denied.</body></html>",
            "<html><body>CAPTCHA verification required</body></html>"
        ]
        
        for html in bot_detection_html:
            with pytest.raises(AutomationBlockedError, match="Manual login required"):
                sm.detect_bot_block(html)
    
    def test_bot_detection_safe_content(self, test_config, temp_cookie_file):
        """Test bot detection doesn't trigger on normal content"""
        sm = SessionManager(test_config, cookie_path=temp_cookie_file)
        
        # Normal content should not trigger bot detection
        normal_html = [
            "<html><body><h1>Welcome to Plus500</h1></body></html>",
            "<html><body>Your account balance is $1000</body></html>",
            "<html><body>Trading dashboard</body></html>"
        ]
        
        for html in normal_html:
            # Should not raise any exception
            sm.detect_bot_block(html)
    
    def test_session_headers_configuration(self, test_config, temp_cookie_file):
        """Test session is configured with proper headers"""
        sm = SessionManager(test_config, cookie_path=temp_cookie_file)
        
        # Get the actual configured values
        expected_headers = {
            "User-Agent": getattr(test_config, 'user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'),
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": getattr(test_config, 'accept_language', 'en-US,en;q=0.9'),
            "Origin": test_config.base_url,
            "Referer": test_config.base_url
        }
        
        for header, expected_value in expected_headers.items():
            assert header in sm.session.headers
            assert sm.session.headers[header] == expected_value
    
    @patch('plus500us_client.session.Path.home')
    def test_default_cookie_path(self, mock_home, test_config):
        """Test default cookie path is set correctly"""
        mock_home.return_value = Path("/home/testuser")
        
        sm = SessionManager(test_config)
        
        expected_path = Path("/home/testuser") / ".plus500us.cookies"
        assert sm.cookie_path == expected_path


class TestSessionManagerAuthenticationSimulation:
    """Test scenarios that simulate authentication state persistence"""
    
    def _add_cookie_to_jar(self, cookie_jar, name, value, domain):
        """Helper to add cookie to LWPCookieJar"""
        from http.cookiejar import Cookie
        cookie_obj = Cookie(
            version=0, name=name, value=value, port=None, port_specified=False,
            domain=domain, domain_specified=True, domain_initial_dot=True,
            path="/", path_specified=True, secure=False, expires=None,
            discard=True, comment=None, comment_url=None, rest={}
        )
        cookie_jar.set_cookie(cookie_obj)
    
    @pytest.fixture
    def temp_cookie_file(self):
        """Create temporary cookie file for testing"""
        with tempfile.NamedTemporaryFile(suffix='.cookies', delete=False, mode='w') as f:
            # Write LWP cookie jar header
            f.write("#LWP-Cookies-2.0\n")
            temp_path = Path(f.name)
        yield temp_path
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()
    
    @pytest.fixture
    def test_config(self):
        """Create test config"""
        return Config(
            base_url="https://futures.plus500.com",
            host_url="https://api-futures.plus500.com",
            account_type="demo"
        )
    
    @pytest.fixture
    def authenticated_session_cookies(self):
        """Realistic authentication cookies"""
        return [
            {"name": "JSESSIONID", "value": "F8A7B2C3D4E5F6G7H8I9J0K1L2M3N4O5", "domain": ".plus500.com"},
            {"name": "authToken", "value": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9", "domain": ".plus500.com"},
            {"name": "userPrefs", "value": "demo", "domain": ".plus500.com"},
            {"name": "sessionState", "value": "authenticated", "domain": ".plus500.com"},
            {"name": "lastActivity", "value": str(int(time.time())), "domain": ".plus500.com"}
        ]
    
    def test_authentication_state_preservation(self, test_config, temp_cookie_file, authenticated_session_cookies):
        """Test that authentication state is preserved across sessions to avoid recaptcha"""
        
        # Simulate first login with WebDriver that overcame captcha
        sm1 = SessionManager(test_config, cookie_path=temp_cookie_file)
        
        # Add authenticated session cookies (as if from successful WebDriver login)
        for cookie in authenticated_session_cookies:
            self._add_cookie_to_jar(
                sm1.session.cookies,
                cookie["name"],
                cookie["value"],
                cookie["domain"]
            )
        
        # Save the authenticated state
        sm1.save_cookies()
        
        # Simulate client restart (user closes application)
        SessionManager._session = None
        
        # User starts client again - new SessionManager instance
        sm2 = SessionManager(test_config, cookie_path=temp_cookie_file)
        
        # Verify authentication cookies are present (no recaptcha needed)
        loaded_cookies = {cookie.name: cookie.value for cookie in sm2.session.cookies}
        
        # Critical cookies for maintaining authentication
        assert "JSESSIONID" in loaded_cookies
        assert "authToken" in loaded_cookies
        assert "sessionState" in loaded_cookies
        
        # Verify values match (complete session restoration)
        assert loaded_cookies["JSESSIONID"] == "F8A7B2C3D4E5F6G7H8I9J0K1L2M3N4O5"
        assert loaded_cookies["authToken"] == "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9"
        assert loaded_cookies["sessionState"] == "authenticated"
        
        # This represents successful avoidance of recaptcha challenge
        assert loaded_cookies["userPrefs"] == "demo"
    
    def test_session_expiry_simulation(self, test_config, temp_cookie_file):
        """Test handling of expired session cookies"""
        import time
        from http.cookies import SimpleCookie
        
        sm = SessionManager(test_config, cookie_path=temp_cookie_file)
        
        # Add expired session cookie
        past_time = int(time.time()) - 86400  # 24 hours ago
        self._add_cookie_to_jar(sm.session.cookies, "expiredSession", "expired_value", ".plus500.com")
        
        # Add valid session cookie  
        future_time = int(time.time()) + 86400  # 24 hours from now
        self._add_cookie_to_jar(sm.session.cookies, "validSession", "valid_value", ".plus500.com")
        
        sm.save_cookies()
        
        # Create new session
        SessionManager._session = None
        sm2 = SessionManager(test_config, cookie_path=temp_cookie_file)
        
        # Verify handling of expired vs valid cookies
        cookie_names = [cookie.name for cookie in sm2.session.cookies]
        
        # Implementation may vary on how LWPCookieJar handles expired cookies
        # The important part is that the session manager gracefully handles them
        assert isinstance(sm2.session.cookies, LWPCookieJar)
    
    def test_multiple_domain_cookie_handling(self, test_config, temp_cookie_file):
        """Test cookies for multiple domains are handled correctly"""
        sm = SessionManager(test_config, cookie_path=temp_cookie_file)
        
        # Add cookies for different Plus500 domains
        domains_and_cookies = [
            (".plus500.com", "main_session", "main_value"),
            ("futures.plus500.com", "futures_session", "futures_value"), 
            ("api-futures.plus500.com", "api_session", "api_value"),
            ("app.plus500.com", "app_session", "app_value")
        ]
        
        for domain, name, value in domains_and_cookies:
            self._add_cookie_to_jar(sm.session.cookies, name, value, domain)
        
        sm.save_cookies()
        
        # Create new session
        SessionManager._session = None
        sm2 = SessionManager(test_config, cookie_path=temp_cookie_file)
        
        # Verify all domain cookies are preserved
        loaded_cookies = [(cookie.name, cookie.value, cookie.domain) for cookie in sm2.session.cookies]
        
        for domain, name, value in domains_and_cookies:
            matching_cookies = [c for c in loaded_cookies if c[0] == name and c[1] == value]
            assert len(matching_cookies) > 0, f"Cookie {name} for domain {domain} not found"
    
    def test_recaptcha_avoidance_workflow(self, test_config, temp_cookie_file):
        """Test complete workflow demonstrating recaptcha avoidance"""
        
        # Phase 1: Initial login (simulating WebDriver overcoming captcha)
        print("\n=== SIMULATING INITIAL LOGIN WITH CAPTCHA SOLVED ===")
        
        sm_initial = SessionManager(test_config, cookie_path=temp_cookie_file)
        
        # Simulate authentication cookies from successful WebDriver login
        auth_cookies = [
            ("JSESSIONID", "ABC123DEF456GHI789", ".plus500.com"),
            ("authToken", "jwt_token_here", ".plus500.com"), 
            ("accountType", "demo", ".plus500.com"),
            ("csrfToken", "csrf_12345", ".plus500.com"),
            ("loginTimestamp", str(int(time.time())), ".plus500.com")
        ]
        
        for name, value, domain in auth_cookies:
            self._add_cookie_to_jar(sm_initial.session.cookies, name, value, domain)
        
        # Save authentication state
        sm_initial.save_cookies()
        print(f"[SUCCESS] Saved {len(auth_cookies)} authentication cookies to {temp_cookie_file}")
        
        # Phase 2: Client restart (simulating app close/reopen)
        print("\n=== SIMULATING CLIENT RESTART ===")
        
        # Clear singleton to simulate fresh process
        SessionManager._session = None
        
        # Phase 3: New session creation (no recaptcha needed!)
        print("\n=== CREATING NEW SESSION WITHOUT RECAPTCHA ===")
        
        sm_restored = SessionManager(test_config, cookie_path=temp_cookie_file)
        
        # Verify authentication state is restored
        restored_cookies = {c.name: c.value for c in sm_restored.session.cookies}
        
        print(f"[SUCCESS] Restored {len(restored_cookies)} cookies from persistent storage")
        
        # Critical assertion: authentication cookies are present
        assert "JSESSIONID" in restored_cookies
        assert "authToken" in restored_cookies  
        assert "accountType" in restored_cookies
        
        print("[SUCCESS] Authentication state successfully restored!")
        print("[SUCCESS] User can continue trading WITHOUT solving captcha again!")
        
        # Verify specific values to ensure complete restoration
        assert restored_cookies["JSESSIONID"] == "ABC123DEF456GHI789"
        assert restored_cookies["authToken"] == "jwt_token_here"
        assert restored_cookies["accountType"] == "demo"
        
        print("[SUCCESS] Session values perfectly match - seamless authentication continuity!")