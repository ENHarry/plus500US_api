#!/usr/bin/env python3
"""
Plus500 Session-Based API Client
Focuses on session establishment and working with partial authentication.
"""

import requests
import json
import time
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import logging
from urllib.parse import urljoin, urlparse, parse_qs

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

class Plus500SessionAPI:
    """Plus500 API client that works with session-based authentication."""
    
    def __init__(self):
        self.session = requests.Session()
        self.web_url = "https://futures.plus500.com"
        self.api_url = "https://api-futures.plus500.com"
        
        # Session state
        self.authenticated = False
        self.session_data = {}
        self.global_config = {}
        
        # Configure session headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        })
    
    def establish_session(self) -> bool:
        """Establish a session with the Plus500 system."""
        
        print("🔄 Establishing session with Plus500...")
        
        try:
            # Step 1: Access main web app
            print("   📍 Step 1: Accessing web app...")
            response = self.session.get(f"{self.web_url}/trade")
            
            if response.status_code != 200:
                print(f"   ❌ Web app access failed: {response.status_code}")
                return False
            
            print(f"   ✅ Web app access successful")
            
            # Step 2: Extract global configuration
            print("   📍 Step 2: Extracting global configuration...")
            if self._extract_global_config(response.text):
                print("   ✅ Global config extracted")
            else:
                print("   ⚠️  Global config extraction failed")
            
            # Step 3: Initialize API session
            print("   📍 Step 3: Initializing API session...")
            if self._initialize_api_session():
                print("   ✅ API session initialized")
                self.authenticated = True
                return True
            else:
                print("   ❌ API session initialization failed")
                return False
                
        except Exception as e:
            print(f"   ❌ Session establishment failed: {e}")
            return False
    
    def _extract_global_config(self, html_content: str) -> bool:
        """Extract globalConfig from web app HTML."""
        
        try:
            # Look for globalConfig object
            config_pattern = r'var\s+globalConfig\s*=\s*({[^;]+});'
            match = re.search(config_pattern, html_content)
            
            if match:
                config_str = match.group(1)
                
                # Extract key values manually (since it's JavaScript, not JSON)
                patterns = {
                    's': r'"s":\s*"([^"]+)"',
                    'v': r'"v":\s*"([^"]+)"',
                    'u': r'"u":\s*"([^"]+)"',
                    'lang2CharsCode': r'"lang2CharsCode":\s*"([^"]+)"',
                    'applicationType': r'"applicationType":\s*"([^"]+)"'
                }
                
                for key, pattern in patterns.items():
                    value_match = re.search(pattern, config_str)
                    if value_match:
                        self.global_config[key] = value_match.group(1)
                
                print(f"      🔍 Extracted config keys: {list(self.global_config.keys())}")
                return True
                
            return False
            
        except Exception as e:
            print(f"      ❌ Config extraction error: {e}")
            return False
    
    def _initialize_api_session(self) -> bool:
        """Initialize API session with minimal requirements."""
        
        try:
            # Test basic API connectivity
            response = self.session.get(f"{self.api_url}/handle-cookies")
            
            if response.status_code == 200:
                data = response.json()
                print(f"      🔍 API response: {data}")
                return True
            
            return False
            
        except Exception as e:
            print(f"      ❌ API initialization error: {e}")
            return False
    
    def get_available_endpoints(self) -> Dict[str, Any]:
        """Test and return information about available endpoints."""
        
        print("🔍 Testing available API endpoints...")
        
        endpoints = {
            # Market data endpoints (most likely to work)
            'chart_data': '/ClientRequest/GetChartDataImm',
            'instruments': '/ClientRequest/GetTradeInstruments',
            'market_data': '/ClientRequest/GetMarketData',
            'quotes': '/ClientRequest/GetQuotes',
            'server_time': '/ClientRequest/GetServerTime',
            
            # Platform information
            'app_info': '/ClientRequest/GetApplicationInfo',
            'config': '/ClientRequest/GetConfiguration',
            'market_status': '/ClientRequest/GetMarketStatus',
            'platform_info': '/ClientRequest/GetPlatformInfo',
            'trading_hours': '/ClientRequest/GetTradingHours',
            'spread_info': '/ClientRequest/GetSpreadInfo',
            
            # Session management
            'cookies': '/handle-cookies'
        }
        
        results = {}
        
        for name, endpoint in endpoints.items():
            try:
                response = self.session.get(f"{self.api_url}{endpoint}")
                
                endpoint_info = {
                    'status_code': response.status_code,
                    'content_type': response.headers.get('content-type', 'unknown'),
                    'content_length': len(response.content)
                }
                
                # Parse response if possible
                if response.content:
                    try:
                        if 'application/json' in response.headers.get('content-type', ''):
                            endpoint_info['response'] = response.json()
                        else:
                            endpoint_info['text_preview'] = response.text[:100]
                    except:
                        endpoint_info['raw_preview'] = response.content[:50]
                
                results[name] = endpoint_info
                
                # Status logging
                if response.status_code == 200:
                    if endpoint_info.get('response', {}).get('ResultCode') == 2:
                        print(f"   🔒 {name}: Requires authentication")
                    else:
                        print(f"   ✅ {name}: Working")
                else:
                    print(f"   ❌ {name}: Status {response.status_code}")
                    
            except Exception as e:
                results[name] = {'error': str(e)}
                print(f"   💥 {name}: Error - {e}")
        
        return results
    
    def try_market_data_with_params(self) -> Dict[str, Any]:
        """Try market data endpoints with various parameters."""
        
        print("🎯 Testing market data endpoints with parameters...")
        
        test_params = [
            # Common instrument IDs that might work
            {'InstrumentID': '1'},      # Often S&P 500
            {'InstrumentID': '2'},      # Often another major index
            {'InstrumentID': '3'},
            {'instrumentId': '1'},      # Alternative parameter name
            {'symbol': 'SPX'},          # Symbol-based
            {'symbol': 'ES'},           # ES futures
            
            # Time-based parameters
            {'timeframe': '1m'},
            {'timeframe': '5m'},
            {'timeframe': '1h'},
            
            # Empty parameters (sometimes works)
            {},
        ]
        
        endpoints_to_test = [
            '/ClientRequest/GetChartDataImm',
            '/ClientRequest/GetTradeInstruments',
            '/ClientRequest/GetQuotes',
            '/ClientRequest/GetMarketData'
        ]
        
        results = {}
        
        for endpoint in endpoints_to_test:
            endpoint_results = {}
            
            for i, params in enumerate(test_params):
                try:
                    print(f"   Testing {endpoint} with params {params}...")
                    
                    response = self.session.get(f"{self.api_url}{endpoint}", params=params)
                    
                    result = {
                        'status_code': response.status_code,
                        'params': params,
                        'content_length': len(response.content)
                    }
                    
                    if response.content:
                        try:
                            if 'application/json' in response.headers.get('content-type', ''):
                                result['response'] = response.json()
                        except:
                            result['text_preview'] = response.text[:100]
                    
                    endpoint_results[f'test_{i}'] = result
                    
                    # Check if we got useful data
                    if (response.status_code == 200 and 
                        result.get('response', {}).get('ResultCode') != 2):
                        print(f"      ✅ Potential success with params {params}")
                    
                except Exception as e:
                    endpoint_results[f'test_{i}'] = {'error': str(e)}
            
            results[endpoint] = endpoint_results
        
        return results
    
    def extract_web_app_data(self) -> Dict[str, Any]:
        """Extract additional data from the web application."""
        
        print("🌐 Extracting data from web application...")
        
        try:
            response = self.session.get(f"{self.web_url}/trade")
            
            if response.status_code != 200:
                return {'error': f'Web app access failed: {response.status_code}'}
            
            html_content = response.text
            extracted = {}
            
            # Extract various JavaScript variables and configurations
            patterns = {
                'ProductManager': r'ProductManager\.product\.([^;]+)',
                'applicationType': r'"applicationType":\s*"([^"]+)"',
                'isInTrade': r'"isInTrade":\s*([^,}]+)',
                'version': r'"v":\s*"([^"]+)"',
                'server_url': r'"s":\s*"([^"]+)"',
                'web_url': r'"u":\s*"([^"]+)"'
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, html_content)
                if match:
                    extracted[key] = match.group(1)
                    print(f"   ✅ Found {key}: {match.group(1)}")
            
            # Look for any embedded data that might be useful
            if 'window.initialData' in html_content:
                extracted['has_initial_data'] = True
                print("   ✅ Found window.initialData")
            
            if 'window.appConfig' in html_content:
                extracted['has_app_config'] = True  
                print("   ✅ Found window.appConfig")
            
            return extracted
            
        except Exception as e:
            return {'error': str(e)}
    
    def generate_session_report(self) -> None:
        """Generate a comprehensive report of the session and capabilities."""
        
        print(f"\n" + "="*60)
        print(f"📊 PLUS500 SESSION REPORT")
        print(f"="*60)
        
        print(f"\n🔐 SESSION STATUS:")
        print(f"   Authenticated: {self.authenticated}")
        print(f"   Global Config Keys: {list(self.global_config.keys())}")
        print(f"   Session Data: {len(self.session_data)} items")
        
        # Test endpoints
        endpoint_results = self.get_available_endpoints()
        
        # Test with parameters
        param_results = self.try_market_data_with_params()
        
        # Extract web app data
        web_data = self.extract_web_app_data()
        
        print(f"\n🌐 WEB APP DATA:")
        for key, value in web_data.items():
            if key != 'error':
                print(f"   {key}: {value}")
        
        print(f"\n💾 SAVING RESULTS...")
        
        # Save comprehensive results
        timestamp = int(time.time())
        results = {
            'timestamp': datetime.now().isoformat(),
            'session_status': {
                'authenticated': self.authenticated,
                'global_config': self.global_config,
                'session_data': self.session_data
            },
            'endpoint_tests': endpoint_results,
            'parameter_tests': param_results,
            'web_app_data': web_data
        }
        
        filename = f"plus500_session_report_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"   Results saved to: {filename}")
        
        print(f"\n🎯 NEXT STEPS:")
        print(f"   1. ✅ Session established successfully")
        print(f"   2. 🔧 Most endpoints require authentication")
        print(f"   3. 🌐 Web app integration provides configuration data")
        print(f"   4. 💡 Consider implementing actual login flow")

def main():
    """Main execution."""
    
    print("🚀 Plus500 Session-Based API Testing")
    print("=" * 50)
    
    api = Plus500SessionAPI()
    
    # Establish session
    if api.establish_session():
        print("\n✅ Session established successfully!")
        
        # Generate comprehensive report
        api.generate_session_report()
        
    else:
        print("\n❌ Failed to establish session")

if __name__ == "__main__":
    main()
