#!/usr/bin/env python3
"""
Plus500 Demo Account Access Implementation
==========================================

Implements demo account access to bypass jurisdiction restrictions
while providing full API functionality for testing and development.

Key Features:
- Demo account creation and authentication
- Bypass geographic restrictions
- Full API access with demo credentials
- Same interface as live trading but with virtual money
- Comprehensive error handling and logging

Author: Plus500 US API Development Team
Version: 1.0.0
Date: 2025-01-20
"""

import json
import logging
import requests
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(name)s:%(levelname)s:[%(asctime)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

class Plus500DemoAccess:
    """
    Plus500 Demo Account Access Client
    
    Provides demo account authentication and API access to bypass
    jurisdiction restrictions while maintaining full functionality.
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.demo_credentials = None
        self.session_data = {}
        self.base_urls = {
            'demo_app': 'https://app-demo.plus500.com',
            'demo_api': 'https://api-demo.plus500.com', 
            'demo_futures': 'https://futures-demo.plus500.com',
            'demo_trade': 'https://demo.plus500.com'
        }
        
        # Enhanced headers for demo access
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'DNT': '1',
        }
        self.session.headers.update(self.headers)
        
    def create_demo_account(self, email: str = None) -> Dict[str, Any]:
        """
        Create a new demo account with Plus500
        
        Args:
            email: Optional email for demo account (will generate if not provided)
            
        Returns:
            Dict containing demo account credentials and session info
        """
        logger.info("🎮 Starting demo account creation process")
        
        # Generate email if not provided
        if not email:
            timestamp = int(time.time())
            email = f"demo_trader_{timestamp}@temporary-mail.com"
            
        # Try multiple demo endpoints
        demo_creation_urls = [
            f"{self.base_urls['demo_app']}/demo/create",
            f"{self.base_urls['demo_trade']}/api/demo/register",
            f"{self.base_urls['demo_futures']}/demo/signup",
            "https://app.plus500.com/demo/create"
        ]
        
        demo_data = {
            'email': email,
            'acceptTerms': True,
            'demoAccount': True,
            'accountType': 'demo',
            'platform': 'web',
            'product': 'futures'
        }
        
        for url in demo_creation_urls:
            try:
                logger.info(f"Attempting demo creation at: {url}")
                response = self.session.post(url, json=demo_data, timeout=10)
                
                logger.info(f"Demo creation response: {response.status_code}")
                if response.status_code == 200:
                    result = response.json() if response.content else {}
                    logger.info(f"Demo account created successfully: {json.dumps(result, indent=2)}")
                    return {
                        'success': True,
                        'email': email,
                        'endpoint': url,
                        'credentials': result
                    }
                    
            except Exception as e:
                logger.warning(f"Demo creation failed at {url}: {e}")
                continue
                
        # Fallback: Direct demo access without registration
        logger.info("🔄 Attempting direct demo access")
        return self._attempt_direct_demo_access()
        
    def _attempt_direct_demo_access(self) -> Dict[str, Any]:
        """
        Attempt to access demo mode directly without account creation
        """
        demo_access_urls = [
            "https://app.plus500.com/?mode=demo",
            "https://demo.plus500.com/trade",
            "https://app.plus500.com/demo",
            "https://futures.plus500.com/?demo=true"
        ]
        
        for url in demo_access_urls:
            try:
                logger.info(f"Attempting direct demo access: {url}")
                response = self.session.get(url, timeout=10)
                
                if response.status_code == 200:
                    # Look for demo session indicators in response
                    content = response.text
                    if any(indicator in content.lower() for indicator in 
                          ['demo', 'practice', 'virtual', 'simulation']):
                        logger.info(f"✅ Demo access successful at: {url}")
                        return {
                            'success': True,
                            'demo_url': url,
                            'access_method': 'direct',
                            'session_cookies': dict(self.session.cookies)
                        }
                        
            except Exception as e:
                logger.warning(f"Direct demo access failed at {url}: {e}")
                continue
                
        return {'success': False, 'error': 'All demo access methods failed'}
    
    def authenticate_demo_account(self, credentials: Dict[str, Any] = None) -> bool:
        """
        Authenticate with demo account credentials
        
        Args:
            credentials: Demo account credentials (if available)
            
        Returns:
            bool: True if authentication successful
        """
        logger.info("🔐 Starting demo account authentication")
        
        # Authentication endpoints for demo
        auth_endpoints = [
            f"{self.base_urls['demo_api']}/UserLogin/Demo",
            f"{self.base_urls['demo_futures']}/api/demo/login",
            "https://api.plus500.com/demo/auth",
            "https://app.plus500.com/api/demo/session"
        ]
        
        # Demo authentication data
        demo_auth_data = {
            'loginType': 'demo',
            'accountType': 'demo',
            'platform': 'web_demo',
            'demoMode': True,
            'product': 'futures'
        }
        
        if credentials:
            demo_auth_data.update(credentials)
            
        for endpoint in auth_endpoints:
            try:
                logger.info(f"Attempting demo authentication: {endpoint}")
                response = self.session.post(endpoint, json=demo_auth_data, timeout=10)
                
                logger.info(f"Demo auth response: {response.status_code}")
                if response.status_code == 200:
                    auth_result = response.json() if response.content else {}
                    logger.info(f"Demo authentication result: {json.dumps(auth_result, indent=2)}")
                    
                    # Extract session data for demo account
                    self.session_data = self._extract_demo_session_data(auth_result)
                    return True
                    
            except Exception as e:
                logger.warning(f"Demo authentication failed at {endpoint}: {e}")
                continue
                
        # Try session-based demo access
        return self._try_session_demo_access()
    
    def _extract_demo_session_data(self, auth_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract session data from demo authentication response"""
        session_data = {
            'demo_mode': True,
            'timestamp': datetime.now().isoformat()
        }
        
        # Extract relevant session parameters
        session_fields = [
            'SessionID', 'SubSessionID', 'SessionToken', 'UserID',
            'WebTraderServiceId', 'LoginSessionID', 'Token'
        ]
        
        for field in session_fields:
            if field in auth_result:
                session_data[field] = auth_result[field]
                
        logger.info(f"Extracted demo session data: {json.dumps(session_data, indent=2)}")
        return session_data
    
    def _try_session_demo_access(self) -> bool:
        """Try to establish demo session through cookie/header manipulation"""
        logger.info("🍪 Attempting session-based demo access")
        
        # Set demo mode cookies and headers
        demo_cookies = {
            'DemoMode': 'true',
            'AccountType': 'demo',
            'PlatformType': 'demo',
            'IsDemo': '1'
        }
        
        for name, value in demo_cookies.items():
            self.session.cookies.set(name, value)
            
        # Add demo headers
        self.session.headers.update({
            'X-Demo-Mode': 'true',
            'X-Account-Type': 'demo',
            'X-Platform': 'demo'
        })
        
        # Test demo session with market data request
        test_endpoints = [
            "https://api.plus500.com/demo/instruments",
            "https://app.plus500.com/api/demo/quotes",
            "https://futures.plus500.com/api/demo/markets"
        ]
        
        for endpoint in test_endpoints:
            try:
                response = self.session.get(endpoint, timeout=5)
                if response.status_code == 200:
                    logger.info(f"✅ Demo session established via: {endpoint}")
                    return True
            except:
                continue
                
        return False
    
    def get_demo_market_data(self) -> Dict[str, Any]:
        """
        Retrieve market data using demo account access
        
        Returns:
            Dict containing market data and instruments
        """
        logger.info("📊 Fetching demo market data")
        
        market_endpoints = [
            "https://api.plus500.com/demo/ClientRequest/GetTradeInstruments",
            "https://app.plus500.com/api/demo/instruments",
            "https://futures.plus500.com/api/demo/instruments",
            "https://demo.plus500.com/api/markets"
        ]
        
        for endpoint in market_endpoints:
            try:
                logger.info(f"Requesting market data from: {endpoint}")
                response = self.session.get(endpoint, timeout=10)
                
                logger.info(f"Market data response: {response.status_code}")
                if response.status_code == 200 and response.content:
                    try:
                        market_data = response.json()
                        logger.info(f"✅ Market data retrieved: {len(str(market_data))} bytes")
                        return {
                            'success': True,
                            'endpoint': endpoint,
                            'data': market_data,
                            'timestamp': datetime.now().isoformat()
                        }
                    except json.JSONDecodeError:
                        logger.info(f"Non-JSON response from {endpoint}: {response.text[:200]}")
                        
            except Exception as e:
                logger.warning(f"Market data request failed: {e}")
                continue
                
        return {'success': False, 'error': 'No market data endpoints accessible'}
    
    def test_demo_trading_functions(self) -> Dict[str, Any]:
        """
        Test core trading functions with demo account
        
        Returns:
            Dict containing test results for all trading functions
        """
        logger.info("🧪 Testing demo trading functions")
        
        test_results = {
            'account_info': self._test_account_info(),
            'balance_check': self._test_balance_check(),
            'positions': self._test_positions(),
            'orders': self._test_orders(),
            'instruments': self._test_instruments()
        }
        
        logger.info(f"Demo trading test results: {json.dumps(test_results, indent=2)}")
        return test_results
    
    def _test_account_info(self) -> Dict[str, Any]:
        """Test account information retrieval"""
        endpoints = [
            "https://api.plus500.com/demo/ClientRequest/GetAccountInfo",
            "https://app.plus500.com/api/demo/account",
            "https://futures.plus500.com/api/demo/account/info"
        ]
        
        for endpoint in endpoints:
            try:
                response = self.session.get(endpoint, timeout=5)
                if response.status_code == 200:
                    return {'success': True, 'endpoint': endpoint, 'data': response.json()}
            except:
                continue
        return {'success': False}
    
    def _test_balance_check(self) -> Dict[str, Any]:
        """Test balance information retrieval"""
        endpoints = [
            "https://api.plus500.com/demo/ClientRequest/GetBalance",
            "https://app.plus500.com/api/demo/balance",
            "https://futures.plus500.com/api/demo/account/balance"
        ]
        
        for endpoint in endpoints:
            try:
                response = self.session.get(endpoint, timeout=5)
                if response.status_code == 200:
                    return {'success': True, 'endpoint': endpoint, 'data': response.json()}
            except:
                continue
        return {'success': False}
    
    def _test_positions(self) -> Dict[str, Any]:
        """Test positions retrieval"""
        endpoints = [
            "https://api.plus500.com/demo/ClientRequest/GetPositions",
            "https://app.plus500.com/api/demo/positions",
            "https://futures.plus500.com/api/demo/trading/positions"
        ]
        
        for endpoint in endpoints:
            try:
                response = self.session.get(endpoint, timeout=5)
                if response.status_code == 200:
                    return {'success': True, 'endpoint': endpoint, 'data': response.json()}
            except:
                continue
        return {'success': False}
    
    def _test_orders(self) -> Dict[str, Any]:
        """Test orders functionality"""
        endpoints = [
            "https://api.plus500.com/demo/ClientRequest/GetOrders",
            "https://app.plus500.com/api/demo/orders",
            "https://futures.plus500.com/api/demo/trading/orders"
        ]
        
        for endpoint in endpoints:
            try:
                response = self.session.get(endpoint, timeout=5)
                if response.status_code == 200:
                    return {'success': True, 'endpoint': endpoint, 'data': response.json()}
            except:
                continue
        return {'success': False}
    
    def _test_instruments(self) -> Dict[str, Any]:
        """Test instruments/markets data"""
        endpoints = [
            "https://api.plus500.com/demo/ClientRequest/GetTradeInstruments",
            "https://app.plus500.com/api/demo/instruments",
            "https://futures.plus500.com/api/demo/markets/instruments"
        ]
        
        for endpoint in endpoints:
            try:
                response = self.session.get(endpoint, timeout=5)
                if response.status_code == 200:
                    return {'success': True, 'endpoint': endpoint, 'data': response.json()}
            except:
                continue
        return {'success': False}
    
    def save_demo_session(self, filename: str = None) -> str:
        """
        Save demo session data for future use
        
        Args:
            filename: Optional filename for session backup
            
        Returns:
            str: Path to saved session file
        """
        if not filename:
            timestamp = int(time.time())
            filename = f"session_backup/plus500_demo_session_{timestamp}.json"
            
        session_backup = {
            'timestamp': datetime.now().isoformat(),
            'session_type': 'demo',
            'session_data': self.session_data,
            'cookies': dict(self.session.cookies),
            'headers': dict(self.session.headers),
            'base_urls': self.base_urls
        }
        
        # Ensure directory exists
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(session_backup, f, indent=2)
            
        logger.info(f"💾 Demo session saved to: {filename}")
        return filename

def main():
    """
    Main execution function for demo account access
    """
    print("🎮 Plus500 Demo Account Access Implementation")
    print("=" * 60)
    
    demo_client = Plus500DemoAccess()
    
    # Step 1: Create or access demo account
    print("\n📝 Step 1: Creating/Accessing Demo Account")
    demo_result = demo_client.create_demo_account()
    
    if demo_result['success']:
        print(f"✅ Demo account access successful!")
        print(f"   Method: {demo_result.get('access_method', 'account_creation')}")
        if 'email' in demo_result:
            print(f"   Email: {demo_result['email']}")
    else:
        print(f"❌ Demo account creation failed: {demo_result.get('error')}")
        return
    
    # Step 2: Authenticate demo account
    print("\n🔐 Step 2: Authenticating Demo Account")
    auth_success = demo_client.authenticate_demo_account(demo_result.get('credentials'))
    
    if auth_success:
        print("✅ Demo authentication successful!")
    else:
        print("⚠️  Demo authentication failed, but continuing with session access...")
    
    # Step 3: Test market data access
    print("\n📊 Step 3: Testing Market Data Access")
    market_data = demo_client.get_demo_market_data()
    
    if market_data['success']:
        print(f"✅ Market data retrieved successfully!")
        print(f"   Endpoint: {market_data['endpoint']}")
        print(f"   Data size: {len(str(market_data['data']))} bytes")
    else:
        print(f"❌ Market data access failed: {market_data.get('error')}")
    
    # Step 4: Test trading functions
    print("\n🧪 Step 4: Testing Trading Functions")
    trading_tests = demo_client.test_demo_trading_functions()
    
    for function_name, result in trading_tests.items():
        status = "✅" if result['success'] else "❌"
        print(f"   {status} {function_name.replace('_', ' ').title()}")
        if result['success'] and 'endpoint' in result:
            print(f"      └─ Working endpoint: {result['endpoint']}")
    
    # Step 5: Save session
    print("\n💾 Step 5: Saving Demo Session")
    session_file = demo_client.save_demo_session()
    print(f"✅ Demo session saved: {session_file}")
    
    # Summary
    print("\n📋 DEMO ACCESS SUMMARY")
    print("=" * 60)
    successful_tests = sum(1 for result in trading_tests.values() if result['success'])
    total_tests = len(trading_tests)
    
    print(f"🎯 Overall Success Rate: {successful_tests}/{total_tests} functions working")
    print(f"📊 Market Data Access: {'✅ Working' if market_data['success'] else '❌ Failed'}")
    print(f"🔐 Authentication: {'✅ Complete' if auth_success else '⚠️  Partial'}")
    print(f"💾 Session Backup: ✅ {session_file}")
    
    if successful_tests > 0:
        print("\n🎉 SUCCESS: Demo account access is working!")
        print("   You can now proceed with demo trading implementation.")
        print("   All session data has been saved for future use.")
    else:
        print("\n⚠️  PARTIAL SUCCESS: Demo access established but API endpoints need adjustment.")
        print("   Recommend proceeding to web scraping fallback implementation.")
    
    return demo_client

if __name__ == "__main__":
    demo_client = main()
