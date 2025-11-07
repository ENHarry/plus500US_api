#!/usr/bin/env python3
"""
Test anonymous/session-based API access to determine what endpoints work without full login.
Since we can access the trading page and get some API responses, let's see what we can do.
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

class Plus500AnonymousAPI:
    """Test API access with minimal authentication requirements."""
    
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://api-futures.plus500.com"
        self.web_url = "https://futures.plus500.com"
        
        # Standard browser headers
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
        
    def initialize_session(self) -> bool:
        """Initialize session by accessing the web app."""
        try:
            print("🔄 Initializing session with web app...")
            
            # Step 1: Access main web app to establish session
            response = self.session.get(f"{self.web_url}/trade")
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print("   ✅ Web app access successful")
                return True
            else:
                print(f"   ❌ Web app access failed")
                return False
                
        except Exception as e:
            print(f"   ❌ Session initialization failed: {e}")
            return False
    
    def test_public_endpoints(self) -> Dict[str, Any]:
        """Test various API endpoints that might work without authentication."""
        
        results = {}
        
        # List of endpoints to test
        endpoints = [
            # Market data endpoints
            "/ClientRequest/GetChartDataImm",
            "/ClientRequest/GetTradeInstruments", 
            "/ClientRequest/GetMarketData",
            "/ClientRequest/GetInstrumentData",
            "/ClientRequest/GetQuotes",
            
            # Information endpoints
            "/ClientRequest/GetServerTime",
            "/ClientRequest/GetApplicationInfo",
            "/ClientRequest/GetConfiguration",
            "/ClientRequest/GetMarketStatus",
            
            # Trading platform info
            "/ClientRequest/GetPlatformInfo",
            "/ClientRequest/GetTradingHours",
            "/ClientRequest/GetSpreadInfo",
            
            # Other potential endpoints
            "/handle-cookies",
            "/ping",
            "/status",
            "/health"
        ]
        
        print(f"\n🧪 Testing {len(endpoints)} API endpoints...")
        
        for endpoint in endpoints:
            try:
                print(f"\n   Testing: {endpoint}")
                
                response = self.session.get(f"{self.base_url}{endpoint}")
                
                result_info = {
                    'status_code': response.status_code,
                    'content_type': response.headers.get('content-type', 'unknown'),
                    'content_length': len(response.content),
                    'response_time': response.elapsed.total_seconds()
                }
                
                # Try to parse response
                if response.content:
                    try:
                        if 'application/json' in response.headers.get('content-type', ''):
                            parsed_content = response.json()
                            result_info['json_response'] = parsed_content
                        else:
                            # Get first 200 chars of text response
                            text_content = response.text[:200]
                            result_info['text_preview'] = text_content
                    except:
                        result_info['raw_content_preview'] = response.content[:100]
                
                results[endpoint] = result_info
                
                # Status indicator
                if response.status_code == 200:
                    print(f"      ✅ 200 OK - {result_info['content_length']} bytes")
                elif response.status_code in [401, 403]:
                    print(f"      🔒 {response.status_code} - Authentication required")
                elif response.status_code == 404:
                    print(f"      ❌ 404 - Not found")
                else:
                    print(f"      ⚠️  {response.status_code} - Other response")
                    
            except Exception as e:
                results[endpoint] = {'error': str(e)}
                print(f"      💥 Error: {e}")
                
        return results
    
    def test_web_app_integration(self) -> Dict[str, Any]:
        """Test what data we can extract from the web app itself."""
        
        print(f"\n🌐 Testing web app data extraction...")
        
        try:
            response = self.session.get(f"{self.web_url}/trade")
            
            if response.status_code != 200:
                return {'error': f'Web app access failed: {response.status_code}'}
            
            html_content = response.text
            extracted_data = {}
            
            # Look for globalConfig
            if 'globalConfig' in html_content:
                print("   ✅ Found globalConfig data")
                extracted_data['has_global_config'] = True
                
                # Try to extract the actual config
                import re
                config_pattern = r'globalConfig\s*=\s*({[^;]+})'
                match = re.search(config_pattern, html_content)
                if match:
                    try:
                        # This is tricky because it's JavaScript, not JSON
                        # We'll just note that it exists for now
                        extracted_data['global_config_found'] = True
                    except:
                        pass
            
            # Look for other useful data patterns
            patterns_to_find = [
                'ProductManager',
                'applicationType',
                'isInTrade',
                'ErrorTrackingDns',
                'firebaseConfiguration'
            ]
            
            for pattern in patterns_to_find:
                if pattern in html_content:
                    extracted_data[f'has_{pattern}'] = True
                    print(f"   ✅ Found {pattern}")
                    
            return extracted_data
            
        except Exception as e:
            return {'error': str(e)}
    
    def generate_report(self, api_results: Dict, web_results: Dict) -> None:
        """Generate a comprehensive report of findings."""
        
        print(f"\n" + "="*60)
        print(f"📊 COMPREHENSIVE API ACCESS REPORT")
        print(f"="*60)
        
        # Count successes
        successful_endpoints = [ep for ep, result in api_results.items() 
                              if isinstance(result, dict) and result.get('status_code') == 200]
        
        auth_required_endpoints = [ep for ep, result in api_results.items() 
                                 if isinstance(result, dict) and result.get('status_code') in [401, 403]]
        
        print(f"\n📈 ENDPOINT SUMMARY:")
        print(f"   ✅ Successful endpoints: {len(successful_endpoints)}")
        print(f"   🔒 Auth-required endpoints: {len(auth_required_endpoints)}")
        print(f"   ❌ Failed/Not found: {len(api_results) - len(successful_endpoints) - len(auth_required_endpoints)}")
        
        if successful_endpoints:
            print(f"\n🎯 WORKING ENDPOINTS:")
            for endpoint in successful_endpoints:
                result = api_results[endpoint]
                print(f"   • {endpoint}")
                print(f"     - Content-Type: {result.get('content_type', 'unknown')}")
                print(f"     - Size: {result.get('content_length', 0)} bytes")
                if 'json_response' in result:
                    print(f"     - JSON Response: {result['json_response']}")
                elif 'text_preview' in result:
                    print(f"     - Text Preview: {result['text_preview'][:100]}...")
        
        if auth_required_endpoints:
            print(f"\n🔒 AUTHENTICATION-REQUIRED ENDPOINTS:")
            for endpoint in auth_required_endpoints:
                print(f"   • {endpoint}")
        
        print(f"\n🌐 WEB APP CAPABILITIES:")
        for key, value in web_results.items():
            if key != 'error':
                print(f"   • {key}: {value}")
        
        if web_results.get('error'):
            print(f"   ❌ Web app error: {web_results['error']}")
        
        print(f"\n💡 RECOMMENDATIONS:")
        if successful_endpoints:
            print(f"   ✅ Some endpoints work - we can build limited functionality")
            print(f"   🔧 Focus on working endpoints for market data and platform info")
        else:
            print(f"   ⚠️  No working API endpoints found")
            
        if web_results and not web_results.get('error'):
            print(f"   🌐 Web app integration possible for additional data")
        
        print(f"\n🎯 NEXT STEPS:")
        print(f"   1. Build functionality around working endpoints")
        print(f"   2. Investigate authentication requirements for protected endpoints")
        print(f"   3. Consider web scraping for additional data if API is limited")

def main():
    """Main test execution."""
    
    print("🚀 Starting Plus500 Anonymous API Testing")
    print("=" * 50)
    
    api = Plus500AnonymousAPI()
    
    # Initialize session
    if not api.initialize_session():
        print("❌ Failed to initialize session. Exiting.")
        return
    
    # Test API endpoints
    api_results = api.test_public_endpoints()
    
    # Test web app integration  
    web_results = api.test_web_app_integration()
    
    # Generate comprehensive report
    api.generate_report(api_results, web_results)
    
    # Save results
    timestamp = int(time.time())
    results_file = f"anonymous_api_test_results_{timestamp}.json"
    
    full_results = {
        'timestamp': datetime.now().isoformat(),
        'api_endpoints': api_results,
        'web_app_data': web_results
    }
    
    with open(results_file, 'w') as f:
        json.dump(full_results, f, indent=2)
    
    print(f"\n💾 Results saved to: {results_file}")

if __name__ == "__main__":
    main()
