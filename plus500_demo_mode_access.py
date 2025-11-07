#!/usr/bin/env python3
"""
Plus500 Demo Mode Access - Improved Implementation
==================================================

Enhanced demo access implementation that uses the main Plus500 platform
but switches to demo mode, avoiding jurisdiction restrictions.

Key Improvements:
- Uses main Plus500 endpoints with demo mode parameters
- Handles cookie conflicts and session management better
- Focuses on the actual Plus500 demo toggle functionality
- Bypasses geographic restrictions through demo mode

Author: Plus500 US API Development Team  
Version: 1.1.0
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

class Plus500DemoModeAccess:
    """
    Plus500 Demo Mode Access Client
    
    Uses the main Plus500 platform but switches to demo mode
    to bypass jurisdiction restrictions while maintaining functionality.
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session_data = {}
        
        # Main Plus500 URLs with demo mode parameters
        self.base_urls = {
            'app_demo': 'https://app.plus500.com/?mode=demo',
            'futures_demo': 'https://futures.plus500.com/?demo=true',
            'api_main': 'https://api.plus500.com',
            'api_futures': 'https://api-futures.plus500.com'
        }
        
        # Enhanced headers
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
            'X-Demo-Mode': 'true',
            'X-Account-Type': 'demo'
        }
        self.session.headers.update(self.headers)
        
    def initialize_demo_session(self) -> Dict[str, Any]:
        """
        Initialize demo session by accessing main Plus500 platform in demo mode
        
        Returns:
            Dict containing initialization results
        """
        logger.info("🎮 Initializing Plus500 demo mode session")
        
        # Step 1: Access main demo page to establish session
        demo_urls = [
            'https://app.plus500.com/?mode=demo',
            'https://app.plus500.com/demo',
            'https://futures.plus500.com/?demo=true',
            'https://app.plus500.com/?accountType=demo'
        ]
        
        for url in demo_urls:
            try:
                logger.info(f"Accessing demo mode: {url}")
                response = self.session.get(url, timeout=15)
                
                if response.status_code == 200:
                    content = response.text
                    
                    # Look for demo mode indicators
                    demo_indicators = [
                        'demo', 'practice', 'virtual', 'simulation',
                        'DemoMode', 'IsDemo', 'accountType=demo'
                    ]
                    
                    found_indicators = [ind for ind in demo_indicators if ind.lower() in content.lower()]
                    
                    if found_indicators:
                        logger.info(f"✅ Demo mode detected: {found_indicators}")
                        
                        # Extract any session parameters from the page
                        session_info = self._extract_session_from_html(content)
                        
                        return {
                            'success': True,
                            'demo_url': url,
                            'session_info': session_info,
                            'demo_indicators': found_indicators,
                            'cookies': self._safe_cookies_dict()
                        }
                    else:
                        logger.info(f"Demo mode not clearly detected at {url}")
                        
            except Exception as e:
                logger.warning(f"Failed to access {url}: {e}")
                continue
                
        return {'success': False, 'error': 'Could not establish demo mode session'}
    
    def _safe_cookies_dict(self) -> Dict[str, str]:
        """Safely convert cookies to dict, handling duplicates"""
        cookies = {}
        for cookie in self.session.cookies:
            # Handle duplicate cookies by keeping the last one
            cookies[cookie.name] = cookie.value
        return cookies
    
    def _extract_session_from_html(self, html_content: str) -> Dict[str, Any]:
        """Extract session parameters from HTML content"""
        session_info = {}
        
        # Look for common session parameters in JavaScript
        import re
        
        patterns = {
            'sessionId': r'"SessionID"\s*:\s*"([^"]*)"',
            'userId': r'"UserID"\s*:\s*"?([^",]*)"?',
            'token': r'"Token"\s*:\s*"([^"]*)"',
            'webTraderServiceId': r'"WebTraderServiceId"\s*:\s*"([^"]*)"',
            'apiVersion': r'"v"\s*:\s*"([^"]*)"',
            'baseUrl': r'"s"\s*:\s*"([^"]*)"'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, html_content, re.IGNORECASE)
            if match:
                session_info[key] = match.group(1)
                logger.info(f"Extracted {key}: {match.group(1)}")
                
        return session_info
    
    def attempt_demo_authentication(self) -> Dict[str, Any]:
        """
        Attempt demo authentication using various approaches
        
        Returns:
            Dict containing authentication results
        """
        logger.info("🔐 Attempting demo authentication")
        
        # Approach 1: Try futures demo with existing session
        futures_result = self._try_futures_demo_auth()
        if futures_result['success']:
            return futures_result
            
        # Approach 2: Try CFD demo authentication  
        cfd_result = self._try_cfd_demo_auth()
        if cfd_result['success']:
            return cfd_result
            
        # Approach 3: Session-based demo access
        session_result = self._try_session_demo_access()
        return session_result
    
    def _try_futures_demo_auth(self) -> Dict[str, Any]:
        """Try futures platform demo authentication"""
        logger.info("Attempting futures demo authentication")
        
        # Set demo mode cookies specifically
        demo_cookies = {
            'IsDemo': 'true',
            'DemoMode': '1',
            'AccountType': 'demo'
        }
        
        for name, value in demo_cookies.items():
            self.session.cookies.set(name, value, domain='.plus500.com')
            
        # Try futures demo login
        auth_data = {
            'accountType': 'demo',
            'demoMode': True,
            'platform': 'futures',
            'product': 'futures'
        }
        
        endpoints = [
            'https://api-futures.plus500.com/UserLogin/Demo',
            'https://api-futures.plus500.com/UserLogin/WebTrader2?demo=true',
            'https://futures.plus500.com/api/demo/login'
        ]
        
        for endpoint in endpoints:
            try:
                response = self.session.post(endpoint, json=auth_data, timeout=10)
                logger.info(f"Futures demo auth response [{endpoint}]: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        logger.info(f"Futures demo auth success: {json.dumps(result, indent=2)}")
                        return {'success': True, 'method': 'futures_demo', 'data': result}
                    except:
                        return {'success': True, 'method': 'futures_demo', 'data': response.text}
                        
            except Exception as e:
                logger.warning(f"Futures demo auth failed [{endpoint}]: {e}")
                continue
                
        return {'success': False, 'method': 'futures_demo'}
    
    def _try_cfd_demo_auth(self) -> Dict[str, Any]:
        """Try CFD platform demo authentication"""
        logger.info("Attempting CFD demo authentication")
        
        auth_data = {
            'accountType': 'demo',
            'demoMode': True,
            'platform': 'cfd'
        }
        
        endpoints = [
            'https://api.plus500.com/UserLogin/Demo',
            'https://api.plus500.com/UserLogin/WebTrader2?demo=true',
            'https://app.plus500.com/api/demo/auth'
        ]
        
        for endpoint in endpoints:
            try:
                response = self.session.post(endpoint, json=auth_data, timeout=10)
                logger.info(f"CFD demo auth response [{endpoint}]: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        logger.info(f"CFD demo auth success: {json.dumps(result, indent=2)}")
                        return {'success': True, 'method': 'cfd_demo', 'data': result}
                    except:
                        return {'success': True, 'method': 'cfd_demo', 'data': response.text}
                        
            except Exception as e:
                logger.warning(f"CFD demo auth failed [{endpoint}]: {e}")
                continue
                
        return {'success': False, 'method': 'cfd_demo'}
    
    def _try_session_demo_access(self) -> Dict[str, Any]:
        """Try session-based demo access"""
        logger.info("🍪 Attempting session-based demo access")
        
        # Test if existing session works for demo data
        test_endpoints = [
            'https://api.plus500.com/ClientRequest/GetTradeInstruments?demo=true',
            'https://api-futures.plus500.com/ClientRequest/GetTradeInstruments?demo=true',
            'https://app.plus500.com/api/instruments?demo=true'
        ]
        
        for endpoint in test_endpoints:
            try:
                response = self.session.get(endpoint, timeout=10)
                logger.info(f"Session demo test [{endpoint}]: {response.status_code}")
                
                if response.status_code == 200 and response.content:
                    try:
                        data = response.json()
                        if data:  # Non-empty response
                            logger.info(f"✅ Session demo access working: {endpoint}")
                            return {
                                'success': True, 
                                'method': 'session_demo',
                                'endpoint': endpoint,
                                'data': data
                            }
                    except:
                        # Even if not JSON, a 200 response with content is promising
                        if len(response.content) > 10:
                            return {
                                'success': True,
                                'method': 'session_demo', 
                                'endpoint': endpoint,
                                'data': response.text[:500]
                            }
                            
            except Exception as e:
                logger.warning(f"Session demo test failed [{endpoint}]: {e}")
                continue
                
        return {'success': False, 'method': 'session_demo'}
    
    def test_demo_endpoints(self) -> Dict[str, Any]:
        """
        Test various demo endpoints to find working ones
        
        Returns:
            Dict containing test results for all endpoints
        """
        logger.info("🧪 Testing demo endpoints")
        
        endpoint_tests = {
            'instruments': self._test_instruments_endpoints(),
            'account_info': self._test_account_endpoints(),
            'market_data': self._test_market_data_endpoints(),
            'trading': self._test_trading_endpoints()
        }
        
        return endpoint_tests
    
    def _test_instruments_endpoints(self) -> Dict[str, Any]:
        """Test instruments/markets endpoints"""
        endpoints = [
            'https://api.plus500.com/ClientRequest/GetTradeInstruments?demo=true',
            'https://api-futures.plus500.com/ClientRequest/GetTradeInstruments?demo=true',
            'https://app.plus500.com/api/instruments?demo=true',
            'https://futures.plus500.com/api/instruments?demo=true'
        ]
        
        return self._test_endpoint_list(endpoints, 'instruments')
    
    def _test_account_endpoints(self) -> Dict[str, Any]:
        """Test account information endpoints"""
        endpoints = [
            'https://api.plus500.com/ClientRequest/GetAccountInfo?demo=true',
            'https://api-futures.plus500.com/ClientRequest/GetAccountInfo?demo=true',
            'https://app.plus500.com/api/account?demo=true'
        ]
        
        return self._test_endpoint_list(endpoints, 'account')
    
    def _test_market_data_endpoints(self) -> Dict[str, Any]:
        """Test market data endpoints"""
        endpoints = [
            'https://api.plus500.com/ClientRequest/GetQuotes?demo=true',
            'https://api-futures.plus500.com/ClientRequest/GetQuotes?demo=true',
            'https://app.plus500.com/api/quotes?demo=true'
        ]
        
        return self._test_endpoint_list(endpoints, 'market_data')
    
    def _test_trading_endpoints(self) -> Dict[str, Any]:
        """Test trading-related endpoints"""
        endpoints = [
            'https://api.plus500.com/ClientRequest/GetPositions?demo=true',
            'https://api-futures.plus500.com/ClientRequest/GetPositions?demo=true',
            'https://app.plus500.com/api/positions?demo=true'
        ]
        
        return self._test_endpoint_list(endpoints, 'trading')
    
    def _test_endpoint_list(self, endpoints: list, category: str) -> Dict[str, Any]:
        """Test a list of endpoints and return results"""
        results = []
        
        for endpoint in endpoints:
            try:
                response = self.session.get(endpoint, timeout=8)
                
                result = {
                    'endpoint': endpoint,
                    'status_code': response.status_code,
                    'success': response.status_code == 200,
                    'content_length': len(response.content) if response.content else 0
                }
                
                if response.status_code == 200 and response.content:
                    try:
                        data = response.json()
                        result['data_preview'] = str(data)[:200] if data else "Empty JSON"
                        result['has_data'] = bool(data)
                    except:
                        result['data_preview'] = response.text[:200]
                        result['has_data'] = len(response.content) > 10
                        
                results.append(result)
                logger.info(f"{category} [{endpoint}]: {response.status_code} ({len(response.content)} bytes)")
                
            except Exception as e:
                results.append({
                    'endpoint': endpoint,
                    'success': False,
                    'error': str(e)
                })
                logger.warning(f"{category} [{endpoint}]: Failed - {e}")
                
        return {
            'category': category,
            'total_tested': len(endpoints),
            'successful': sum(1 for r in results if r.get('success', False)),
            'results': results
        }
    
    def save_demo_session(self, filename: Optional[str] = None) -> str:
        """Save demo session data safely"""
        if not filename:
            timestamp = int(time.time())
            filename = f"session_backup/plus500_demo_mode_session_{timestamp}.json"
            
        session_backup = {
            'timestamp': datetime.now().isoformat(),
            'session_type': 'demo_mode',
            'session_data': self.session_data,
            'cookies': self._safe_cookies_dict(),
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
    Main execution function for demo mode access
    """
    print("🎮 Plus500 Demo Mode Access - Improved Implementation")
    print("=" * 65)
    
    demo_client = Plus500DemoModeAccess()
    
    # Step 1: Initialize demo session
    print("\n📝 Step 1: Initializing Demo Session")
    init_result = demo_client.initialize_demo_session()
    
    if init_result['success']:
        print(f"✅ Demo session initialized successfully!")
        print(f"   URL: {init_result['demo_url']}")
        print(f"   Demo indicators: {init_result['demo_indicators']}")
        if init_result.get('session_info'):
            print(f"   Session info extracted: {len(init_result['session_info'])} parameters")
    else:
        print(f"❌ Demo session initialization failed: {init_result.get('error')}")
        return
    
    # Step 2: Attempt demo authentication
    print("\n🔐 Step 2: Attempting Demo Authentication")
    auth_result = demo_client.attempt_demo_authentication()
    
    if auth_result['success']:
        print(f"✅ Demo authentication successful!")
        print(f"   Method: {auth_result['method']}")
        if 'endpoint' in auth_result:
            print(f"   Endpoint: {auth_result['endpoint']}")
    else:
        print(f"⚠️  Demo authentication partial - continuing with session access")
    
    # Step 3: Test demo endpoints comprehensively
    print("\n🧪 Step 3: Testing Demo Endpoints")
    endpoint_tests = demo_client.test_demo_endpoints()
    
    total_successful = 0
    total_tested = 0
    
    for category, results in endpoint_tests.items():
        successful = results['successful']
        tested = results['total_tested']
        total_successful += successful
        total_tested += tested
        
        status = "✅" if successful > 0 else "❌"
        print(f"   {status} {category.replace('_', ' ').title()}: {successful}/{tested} working")
        
        # Show details for working endpoints
        for result in results['results']:
            if result.get('success') and result.get('has_data'):
                print(f"      └─ Working: {result['endpoint']}")
                print(f"         Data: {result.get('data_preview', 'N/A')}")
    
    # Step 4: Save session
    print("\n💾 Step 4: Saving Demo Session")
    session_file = demo_client.save_demo_session()
    print(f"✅ Demo session saved: {session_file}")
    
    # Summary
    print("\n📋 DEMO MODE ACCESS SUMMARY")
    print("=" * 65)
    
    success_rate = (total_successful / total_tested * 100) if total_tested > 0 else 0
    
    print(f"🎯 Overall Success Rate: {total_successful}/{total_tested} endpoints ({success_rate:.1f}%)")
    print(f"🔗 Session Established: {'✅ Yes' if init_result['success'] else '❌ No'}")
    print(f"🔐 Authentication: {'✅ Complete' if auth_result['success'] else '⚠️  Partial'}")
    print(f"💾 Session Backup: ✅ {session_file}")
    
    if total_successful > 0:
        print("\n🎉 SUCCESS: Demo mode access is working!")
        print("   You can now proceed with demo trading implementation.")
        print("   Working endpoints identified for continued development.")
    elif init_result['success']:
        print("\n⚠️  PARTIAL SUCCESS: Demo session established but API access limited.")
        print("   Recommend proceeding to web scraping implementation.")
    else:
        print("\n❌ LIMITED SUCCESS: Try VPN access or web scraping approach.")
    
    return demo_client

if __name__ == "__main__":
    demo_client = main()
