from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
import requests
from requests.cookies import RequestsCookieJar

logger = logging.getLogger(__name__)

class SessionBridge:
    """Bridge for transferring session data between WebDriver and requests.Session"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def transfer_webdriver_to_requests(self, session_data: Dict[str, Any], 
                                     requests_session: Optional[requests.Session] = None) -> requests.Session:
        """
        Transfer WebDriver session data to requests.Session
        
        Args:
            session_data: Session data from WebDriver authentication
            requests_session: Existing session to update (creates new if None)
            
        Returns:
            Configured requests.Session with transferred cookies and headers
        """
        if requests_session is None:
            requests_session = requests.Session()
        
        try:
            # Transfer cookies
            self._transfer_cookies(session_data.get('cookies', []), requests_session)
            
            # Transfer headers
            self._transfer_headers(session_data, requests_session)
            
            # Transfer CSRF token
            csrf_token = session_data.get('csrf_token')
            if csrf_token:
                requests_session.headers['X-CSRF-Token'] = csrf_token
                self.logger.debug("CSRF token transferred to requests session")
            
            # Set user agent from WebDriver
            user_agent = session_data.get('user_agent')
            if user_agent:
                requests_session.headers['User-Agent'] = user_agent
                self.logger.debug("User-Agent transferred to requests session")
            
            # Set additional headers for consistency
            requests_session.headers.update({
                'Accept': 'text/html,application/json;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin'
            })
            
            cookie_count = len(session_data.get('cookies', []))
            self.logger.info(f"Successfully transferred {cookie_count} cookies to requests session")
            
            return requests_session
            
        except Exception as e:
            self.logger.error(f"Failed to transfer WebDriver session to requests: {e}")
            raise
    
    def transfer_requests_to_webdriver(self, requests_session: requests.Session, 
                                     webdriver_instance, base_domain: str) -> None:
        """
        Transfer requests.Session cookies to WebDriver
        
        Args:
            requests_session: Source requests session
            webdriver_instance: Target WebDriver instance
            base_domain: Base domain for cookies
        """
        try:
            # Navigate to domain first (required for cookie setting)
            current_url = webdriver_instance.current_url
            parsed_domain = urlparse(base_domain)
            
            if not current_url.startswith(base_domain):
                webdriver_instance.get(base_domain)
            
            # Clear existing cookies
            webdriver_instance.delete_all_cookies()
            
            # Transfer cookies from requests to WebDriver
            cookie_count = 0
            for cookie in requests_session.cookies:
                cookie_dict = {
                    'name': cookie.name,
                    'value': cookie.value,
                    'domain': cookie.domain or parsed_domain.netloc,
                    'path': cookie.path or '/',
                }
                
                # Add optional cookie attributes
                if cookie.expires:
                    cookie_dict['expiry'] = int(cookie.expires)
                if hasattr(cookie, 'secure') and cookie.secure:
                    cookie_dict['secure'] = True
                if hasattr(cookie, 'rest') and cookie.rest.get('HttpOnly'):
                    cookie_dict['httpOnly'] = True
                
                try:
                    webdriver_instance.add_cookie(cookie_dict)
                    cookie_count += 1
                except Exception as e:
                    self.logger.debug(f"Could not add cookie {cookie.name}: {e}")
            
            self.logger.info(f"Transferred {cookie_count} cookies to WebDriver")
            
        except Exception as e:
            self.logger.error(f"Failed to transfer requests session to WebDriver: {e}")
            raise
    
    def sync_sessions_bidirectional(self, webdriver_instance, requests_session: requests.Session,
                                  base_domain: str) -> None:
        """
        Synchronize cookies bidirectionally between WebDriver and requests
        
        Args:
            webdriver_instance: WebDriver instance
            requests_session: requests.Session instance
            base_domain: Base domain for cookies
        """
        try:
            # Extract current WebDriver cookies
            webdriver_cookies = webdriver_instance.get_cookies()
            
            # Update requests session with WebDriver cookies
            for cookie in webdriver_cookies:
                requests_session.cookies.set(
                    name=cookie['name'],
                    value=cookie['value'],
                    domain=cookie.get('domain'),
                    path=cookie.get('path', '/'),
                    secure=cookie.get('secure', False)
                )
            
            # Update WebDriver with any new requests cookies
            self.transfer_requests_to_webdriver(requests_session, webdriver_instance, base_domain)
            
            self.logger.info("Bidirectional session sync completed")
            
        except Exception as e:
            self.logger.error(f"Bidirectional sync failed: {e}")
            raise
    
    def validate_session_transfer(self, requests_session: requests.Session, 
                                test_url: str) -> Dict[str, Any]:
        """
        Validate that session transfer was successful by testing a request
        
        Args:
            requests_session: Session to validate
            test_url: URL to test authentication against
            
        Returns:
            Validation results
        """
        try:
            # Make a test request
            response = requests_session.get(test_url, timeout=10)
            
            # Check for authentication indicators
            is_authenticated = self._check_authentication_indicators(response)
            
            validation_result = {
                'success': is_authenticated,
                'status_code': response.status_code,
                'url': response.url,
                'cookies_count': len(requests_session.cookies),
                'headers_count': len(requests_session.headers),
                'response_size': len(response.content),
                'authenticated': is_authenticated
            }
            
            if is_authenticated:
                self.logger.info("Session validation successful - authenticated request")
            else:
                self.logger.warning("Session validation failed - not authenticated")
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Session validation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'authenticated': False
            }
    
    def backup_session_data(self, session_data: Dict[str, Any], 
                           filepath: Optional[str] = None) -> str:
        """
        Backup session data to file for later restoration
        
        Args:
            session_data: Session data to backup
            filepath: Optional file path (auto-generated if None)
            
        Returns:
            Path to backup file
        """
        import json
        import time
        from pathlib import Path
        
        if filepath is None:
            timestamp = int(time.time())
            filepath = f"/session_backup/plus500_session_backup_{timestamp}.json"
        
        backup_data = {
            'timestamp': time.time(),
            'cookies': session_data.get('cookies', []),
            'csrf_token': session_data.get('csrf_token'),
            'user_agent': session_data.get('user_agent'),
            'account_type': session_data.get('account_type'),
            'url': session_data.get('url'),
            'local_storage': session_data.get('local_storage', {}),
            'session_storage': session_data.get('session_storage', {})
        }
        
        try:
            with open(filepath, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            self.logger.info(f"Session data backed up to: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Failed to backup session data: {e}")
            raise
    
    def restore_session_data(self, filepath: str) -> Dict[str, Any]:
        """
        Restore session data from backup file
        
        Args:
            filepath: Path to backup file
            
        Returns:
            Restored session data
        """
        import json
        
        try:
            with open(filepath, 'r') as f:
                backup_data = json.load(f)
            
            self.logger.info(f"Session data restored from: {filepath}")
            return backup_data
            
        except Exception as e:
            self.logger.error(f"Failed to restore session data: {e}")
            raise
    
    def _transfer_cookies(self, webdriver_cookies: List[Dict[str, Any]], 
                         requests_session: requests.Session) -> None:
        """Transfer cookies from WebDriver format to requests session"""
        for cookie in webdriver_cookies:
            try:
                requests_session.cookies.set(
                    name=cookie['name'],
                    value=cookie['value'],
                    domain=cookie.get('domain'),
                    path=cookie.get('path', '/'),
                    secure=cookie.get('secure', False)
                )
            except Exception as e:
                self.logger.debug(f"Could not transfer cookie {cookie.get('name', 'unknown')}: {e}")
    
    def _transfer_headers(self, session_data: Dict[str, Any], 
                         requests_session: requests.Session) -> None:
        """Transfer relevant headers from WebDriver session"""
        # Basic headers that should be consistent
        user_agent = session_data.get('user_agent')
        if user_agent:
            requests_session.headers['User-Agent'] = user_agent
        
        # Get referer from current URL
        current_url = session_data.get('url')
        if current_url:
            requests_session.headers['Referer'] = current_url
            
            # Set origin based on URL
            from urllib.parse import urlparse
            parsed = urlparse(current_url)
            origin = f"{parsed.scheme}://{parsed.netloc}"
            requests_session.headers['Origin'] = origin
    
    def _check_authentication_indicators(self, response: requests.Response) -> bool:
        """
        Check if response indicates successful authentication
        
        Args:
            response: HTTP response to check
            
        Returns:
            True if authenticated, False otherwise
        """
        # Check status code
        if response.status_code == 401:
            return False
        
        # Check for redirect to login page
        if 'login' in response.url.lower():
            return False
        
        # Check response content for authentication indicators
        content = response.text.lower()
        
        # Negative indicators (not authenticated)
        negative_indicators = [
            'please log in',
            'sign in required',
            'unauthorized',
            'access denied',
            'session expired',
            'login required'
        ]
        
        if any(indicator in content for indicator in negative_indicators):
            return False
        
        # Positive indicators (authenticated)
        positive_indicators = [
            'dashboard',
            'balance',
            'portfolio',
            'trading',
            'account',
            'logout'
        ]
        
        if any(indicator in content for indicator in positive_indicators):
            return True
        
        # Check for presence of session-related cookies
        auth_cookies = ['session', 'auth', 'token', 'login']
        response_cookies = [cookie.name.lower() for cookie in response.cookies]
        
        if any(auth_cookie in cookie_name for auth_cookie in auth_cookies 
               for cookie_name in response_cookies):
            return True
        
        # Default to checking status code
        return 200 <= response.status_code < 300
    
    def get_session_info(self, requests_session: requests.Session) -> Dict[str, Any]:
        """Get information about current session state"""
        cookies_info = []
        for cookie in requests_session.cookies:
            cookies_info.append({
                'name': cookie.name,
                'domain': cookie.domain,
                'path': cookie.path,
                'secure': getattr(cookie, 'secure', False),
                'expires': getattr(cookie, 'expires', None)
            })
        
        return {
            'cookies_count': len(requests_session.cookies),
            'cookies': cookies_info,
            'headers': dict(requests_session.headers),
            'proxies': requests_session.proxies,
            'verify': requests_session.verify
        }