#!/usr/bin/env python3
"""
Plus500 US Futures Authentication Client
Production-ready client for Plus500 US futures trading authentication

This client handles the complex authentication flow with redirections and security masks
that Plus500 uses for US futures accounts.
"""

import requests
import json
import time
from urllib.parse import urljoin
from typing import Dict, Any, Optional, Tuple
import logging
from datetime import datetime

class Plus500FuturesAuth:
    """Production Plus500 US Futures Authentication Client"""
    
    def __init__(self, debug: bool = False):
        self.base_url = "https://futures.plus500.com"
        self.api_url = "https://api-futures.plus500.com"  # Backend API URL for actual API calls
        self.session = requests.Session()
        self.debug = debug
        
        # Setup logging
        if debug:
            logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)
        
        # Authentication state
        self.is_authenticated = False
        self.session_cookies = {}
        self.session_data = {}  # Store critical session parameters
        self.auth_headers = {}
        
        # Configure session with realistic headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache'
        })
    
    def _save_session_backup(self, session_data: Dict[str, Any]):
        """Save session data to backup folder for debugging"""
        try:
            import os
            backup_dir = "session_backup"
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = int(time.time())
            backup_file = f"{backup_dir}/plus500_session_backup_{timestamp}.json"
            
            with open(backup_file, 'w') as f:
                json.dump(session_data, f, indent=2, default=str)
            
            self._log(f"Session data saved to {backup_file}")
            
        except Exception as e:
            self._log(f"Failed to save session backup: {e}", "error")

    def get_session_parameters(self) -> Dict[str, str]:
        """Get the session parameters needed for API calls"""
        return {
            'UserSessionId': self.session_data.get('UserSessionId', 'N/A'),
            'WebTraderServiceId': self.session_data.get('WebTraderServiceId', 'N/A'), 
            'Hash': self.session_data.get('Hash', 'N/A')
        }

    def _log(self, message: str, level: str = "info"):
        """Log message with timestamp"""
        if not self.debug:
            return
            
        timestamp = datetime.now().strftime("%H:%M:%S")
        if level == "debug":
            self.logger.debug(f"[{timestamp}] {message}")
        elif level == "info":
            self.logger.info(f"[{timestamp}] {message}")
        elif level == "error":
            self.logger.error(f"[{timestamp}] {message}")
    
    def _extract_session_data(self, response: requests.Response) -> Dict[str, Any]:
        """Extract useful session data from response"""
        session_data = {}
        
        # Store important cookies
        for cookie in response.cookies:
            if cookie.name in ['webvisitid', 'innerTags', 'referralDomain', 'Lang2CharsCode', 'LangCultureCode']:
                self.session_cookies[cookie.name] = cookie.value
                session_data[f'cookie_{cookie.name}'] = cookie.value
        
        # Extract any JSON data
        if 'application/json' in response.headers.get('content-type', ''):
            try:
                json_data = response.json()
                if isinstance(json_data, dict):
                    session_data['response_data'] = json_data
                    
                    # Extract critical session parameters for API calls
                    if 'UserSessionId' in json_data:
                        self.session_data['UserSessionId'] = json_data['UserSessionId']
                        session_data['UserSessionId'] = json_data['UserSessionId']
                    
                    if 'WebTraderServiceId' in json_data:
                        self.session_data['WebTraderServiceId'] = json_data['WebTraderServiceId']
                        session_data['WebTraderServiceId'] = json_data['WebTraderServiceId']
                    
                    if 'Hash' in json_data:
                        self.session_data['Hash'] = json_data['Hash']
                        session_data['Hash'] = json_data['Hash']
                        
            except Exception:
                pass
        
        return session_data
    
    def authenticate(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate with Plus500 US Futures
        
        Args:
            email: User email address
            password: User password
            
        Returns:
            Dict with authentication status and session data
        """
        self._log("Starting Plus500 US Futures authentication...")
        
        auth_result = {
            'success': False,
            'timestamp': datetime.now().isoformat(),
            'steps': {},
            'session_data': {},
            'error': None
        }
        
        try:
            # Step 1: Navigate to the web app first (like browser does)
            self._log("Step 1: Load futures web app")
            web_app_url = f"{self.base_url}/trade?innerTags=_cc_&page=login"
            
            # Set proper headers to mimic browser
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            })
            
            response = self.session.get(web_app_url)
            auth_result['steps']['web_app_load'] = {
                'status_code': response.status_code,
                'success': response.status_code == 200
            }
            print(10*'='+'Step 1: Web App Load Response '+10*'=')
            print(f"Status: {response.status_code}")
            print(f"Content length: {len(response.text)}")
            print(f"Response headers: {dict(response.headers)}")
            
            if response.status_code != 200:
                auth_result['error'] = f"Web app loading failed: {response.status_code}"
                return auth_result
            
            self._extract_session_data(response)

            # Step 2: Initialize API session (now that we have web app cookies)
            self._log("Step 2: Initialize API session")
            app_init_url = f"{self.api_url}/AppInitiatedImm/WebTrader2/"
            params = {
                'innerTags': '_cc_',
                'page': 'login',
                'isInTradeContext': 'false'
            }
            
            response = self.session.get(app_init_url, params=params)
            auth_result['steps']['app_init'] = {
                'status_code': response.status_code,
                'success': response.status_code == 200
            }
            print(10*'='+'Step 2: App Init Response '+10*'=')
            print(response.text)
            if response.status_code != 200:
                auth_result['error'] = f"App initialization failed: {response.status_code}"
                return auth_result
            
            self._extract_session_data(response)
            
            # Step 3: Handle cookies endpoint
            self._log("Step 3: Handle cookies")
            cookies_url = f"{self.api_url}/handle-cookies"
            response = self.session.get(cookies_url)
            auth_result['steps']['handle_cookies'] = {
                'status_code': response.status_code,
                'success': response.status_code == 200
            }
            print(10*'='+'Step 3: Handle Cookies Response '+10*'=')
            print(response.text)
            if response.status_code != 200:
                auth_result['error'] = f"Handle cookies failed: {response.status_code}"
                return auth_result

            # Step 4: Load login page (important for session state)
            self._log("Step 4: Load login page")
            login_page_url = f"{self.base_url}/trade?innerTags=_cc_&page=login"
            response = self.session.get(login_page_url)
            auth_result['steps']['login_page'] = {
                'status_code': response.status_code,
                'success': response.status_code == 200
            }
            print(10*'='+'Step 4: Login Page Response '+10*'=')
            print(response.text)
            if response.status_code != 200:
                auth_result['error'] = f"Login page loading failed: {response.status_code}"
                return auth_result

            # Step 5: Perform login (the core authentication)
            self._log("Step 5: Perform login")
            login_url = f"{self.api_url}/UserLogin/WebTrader2"
            
            # Prepare login data for US futures account
            login_data = {
                'email': email,
                'password': password,
                'accountType': 'demo',  # US futures accounts default to demo initially
                'rememberMe': True
            }
            
            # Update headers for login request
            self.session.headers.update({
                'Content-Type': 'application/json',
                'Origin': self.base_url,
                'Referer': login_page_url
            })
            
            response = self.session.post(login_url, json=login_data)
            session_data = self._extract_session_data(response)
            print(10*'='+'Step 5: Login Response '+10*'=')
            print(response.text)

            auth_result['steps']['user_login'] = {
                'status_code': response.status_code,
                'success': response.status_code == 200,
                'session_data': session_data
            }
            
            if response.status_code != 200:
                auth_result['error'] = f"Login failed: {response.status_code}"
                return auth_result
            
            # Parse login response
            try:
                login_response = response.json()
                login_result = login_response.get('LoginResult', 'Unknown')
                
                self._log(f"Login response keys: {list(login_response.keys())}")
                self._log(f"Full login response: {json.dumps(login_response, indent=2, default=str)}")
                
                # For US futures, we expect specific responses
                if login_result in ['Success', 'InvalidProduct']:  # InvalidProduct is normal for jurisdiction
                    self._log("Login successful - US futures account authenticated")
                    self.is_authenticated = True
                    auth_result['success'] = True
                    
                    # Store authentication data
                    auth_result['session_data'] = {
                        'cookies': self.session_cookies,
                        'login_result': login_result,
                        'response': login_response
                    }
                    
                    # Extract session parameters from login response and cookies
                    if 'UserSessionId' in login_response:
                        self.session_data['UserSessionId'] = login_response['UserSessionId']
                        auth_result['session_data']['UserSessionId'] = login_response['UserSessionId']
                        self._log(f"Extracted UserSessionId: {login_response['UserSessionId']}")
                    
                    if 'WebTraderServiceId' in login_response:
                        self.session_data['WebTraderServiceId'] = login_response['WebTraderServiceId']
                        auth_result['session_data']['WebTraderServiceId'] = login_response['WebTraderServiceId']
                        self._log(f"Extracted WebTraderServiceId: {login_response['WebTraderServiceId']}")
                    
                    if 'Hash' in login_response:
                        self.session_data['Hash'] = login_response['Hash']
                        auth_result['session_data']['Hash'] = login_response['Hash']
                        self._log(f"Extracted Hash: {login_response['Hash']}")
                    
                    # Check for session parameters in cookies
                    for cookie in self.session.cookies:
                        if cookie.name == 'UserSessionId':
                            self.session_data['UserSessionId'] = cookie.value
                            auth_result['session_data']['UserSessionId'] = cookie.value
                            self._log(f"Extracted UserSessionId from cookie: {cookie.value}")
                        elif cookie.name == 'WebTraderServiceId':
                            self.session_data['WebTraderServiceId'] = cookie.value  
                            auth_result['session_data']['WebTraderServiceId'] = cookie.value
                            self._log(f"Extracted WebTraderServiceId from cookie: {cookie.value}")
                        elif cookie.name == 'Hash':
                            self.session_data['Hash'] = cookie.value
                            auth_result['session_data']['Hash'] = cookie.value
                            self._log(f"Extracted Hash from cookie: {cookie.value}")
                    
                    # Log what session parameters we found
                    session_params = self.get_session_parameters()
                    self._log(f"Session parameters extracted: {session_params}")
                    
                    # Save session data to backup folder for debugging
                    self._save_session_backup(auth_result['session_data'])
                    
                    # Step 6: Get post-login info (completes the flow)
                    self._log("Step 6: Get post-login info")
                    post_login_url = f"{self.api_url}/ClientRequest/GetPostLoginInfoImm"
                    response = self.session.get(post_login_url)
                    print(10*'='+'Step 6: Post Login Info Response '+10*'=')
                    print(response.text)
                    
                    auth_result['steps']['post_login'] = {
                        'status_code': response.status_code,
                        'success': response.status_code in [200, 302]  # 302 redirect is normal
                    }
                    
                    # Try to extract session data from post-login response
                    session_data_post = self._extract_session_data(response)
                    if session_data_post:
                        auth_result['session_data'].update(session_data_post)
                    
                    # Step 7: Try additional API calls that might provide session parameters
                    self._log("Step 7: Try additional endpoints for session data")
                    
                    # Try chart data endpoint
                    try:
                        chart_url = f"{self.api_url}/ClientRequest/GetChartDataImm"
                        response = self.session.get(chart_url)
                        self._log(f"Chart data endpoint response: {response.status_code}")
                        chart_session_data = self._extract_session_data(response)
                        if chart_session_data:
                            auth_result['session_data'].update(chart_session_data)
                    except Exception as e:
                        self._log(f"Chart data endpoint error: {e}")
                    
                    # Try instruments endpoint
                    try:
                        instruments_url = f"{self.api_url}/ClientRequest/GetTradeInstruments"
                        response = self.session.get(instruments_url)
                        self._log(f"Instruments endpoint response: {response.status_code}")
                        instruments_session_data = self._extract_session_data(response)
                        if instruments_session_data:
                            auth_result['session_data'].update(instruments_session_data)
                    except Exception as e:
                        self._log(f"Instruments endpoint error: {e}")
                    
                    # Final session parameter check
                    final_session_params = self.get_session_parameters()
                    self._log(f"Final session parameters: {final_session_params}")
                    
                else:
                    auth_result['error'] = f"Login failed: {login_result}"
                    special_error = login_response.get('SpecialErrorMsg', '')
                    if special_error:
                        auth_result['error'] += f" - {special_error}"
                        
            except Exception as e:
                auth_result['error'] = f"Failed to parse login response: {e}"
                return auth_result
                
        except Exception as e:
            auth_result['error'] = f"Authentication failed: {e}"
            self._log(f"Authentication error: {e}", "error")
        
        return auth_result
    
    def get_authenticated_session(self) -> Optional[requests.Session]:
        """
        Get the authenticated session for making API calls
        
        Returns:
            Authenticated requests session if logged in, None otherwise
        """
        if self.is_authenticated:
            return self.session
        return None
    
    def is_session_valid(self) -> bool:
        """
        Check if the current session is still valid
        
        Returns:
            True if session is valid, False otherwise
        """
        if not self.is_authenticated:
            return False
        
        try:
            # Test with a simple API call
            test_url = f"{self.api_url}/handle-cookies"
            response = self.session.get(test_url)
            return response.status_code == 200
        except:
            return False
    
    def logout(self):
        """Logout and clear session"""
        self.is_authenticated = False
        self.session_cookies.clear()
        self.session.cookies.clear()
        self._log("Logged out successfully")


def authenticate_plus500_futures(email: str, password: str, debug: bool = False) -> Tuple[bool, Optional[requests.Session], str]:
    """
    Convenience function to authenticate with Plus500 US Futures
    
    Args:
        email: User email
        password: User password  
        debug: Enable debug logging
        
    Returns:
        Tuple of (success, authenticated_session, message)
    """
    client = Plus500FuturesAuth(debug=debug)
    result = client.authenticate(email, password)
    
    if result['success']:
        return True, client.get_authenticated_session(), "Authentication successful"
    else:
        error_msg = result.get('error', 'Unknown error')
        return False, None, f"Authentication failed: {error_msg}"


# Example usage
if __name__ == "__main__":
    # Load credentials from environment
    try:
        from dotenv import load_dotenv
        import os
        load_dotenv()
        
        email = os.getenv('email', '').strip('"')
        password = os.getenv('password', '').strip('"')
        
        if not email or not password:
            print("❌ Missing credentials in .env file")
            exit(1)
        
        print("🚀 Testing Plus500 US Futures Authentication")
        print("=" * 50)
        
        # Test authentication
        success, session, message = authenticate_plus500_futures(email, password, debug=True)
        
        if success:
            print(f"✅ {message}")
            print(f"🔗 Authenticated session ready for API calls")
            
            # Test session validity  
            if session:
                client = Plus500FuturesAuth()
                client.session = session
                client.is_authenticated = True
                
                if client.is_session_valid():
                    print(f"✅ Session is valid and ready for trading API calls")
                else:
                    print(f"⚠️  Session may have limitations but authentication succeeded")
                
        else:
            print(f"❌ {message}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
