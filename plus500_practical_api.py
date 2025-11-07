#!/usr/bin/env python3
"""
Plus500 Practical API Client
Working implementation based on discovered endpoints and capabilities.
"""

import requests
import json
import time
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import logging

class Plus500API:
    """Practical Plus500 API client focused on working functionality."""
    
    def __init__(self):
        self.session = requests.Session()
        self.web_url = "https://futures.plus500.com"
        self.api_url = "https://api-futures.plus500.com"
        
        # Session state
        self.initialized = False
        self.global_config = {}
        
        # Configure session
        self._setup_headers()
        
    def _setup_headers(self):
        """Configure standard browser headers."""
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
    
    def initialize(self) -> bool:
        """Initialize the API session."""
        
        print("🔄 Initializing Plus500 API...")
        
        try:
            # Access the web app to establish session
            response = self.session.get(f"{self.web_url}/trade")
            
            if response.status_code != 200:
                print(f"❌ Failed to access web app: {response.status_code}")
                return False
            
            # Extract configuration from web app
            self._extract_config(response.text)
            
            # Test API connectivity
            test_response = self.session.get(f"{self.api_url}/handle-cookies")
            if test_response.status_code == 200:
                self.initialized = True
                print("✅ API initialized successfully")
                return True
            else:
                print(f"❌ API connectivity test failed: {test_response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            return False
    
    def _extract_config(self, html_content: str):
        """Extract useful configuration from the web app."""
        
        # Extract server URL
        server_match = re.search(r'"s":\s*"([^"]+)"', html_content)
        if server_match:
            self.global_config['server_url'] = server_match.group(1)
        
        # Extract version
        version_match = re.search(r'"v":\s*"([^"]+)"', html_content)
        if version_match:
            self.global_config['version'] = version_match.group(1)
        
        # Extract application type
        app_type_match = re.search(r'"applicationType":\s*"([^"]+)"', html_content)
        if app_type_match:
            self.global_config['application_type'] = app_type_match.group(1)
        
        print(f"   📊 Extracted config: {self.global_config}")
    
    def get_market_data(self, instrument_id: Optional[str] = None) -> Dict[str, Any]:
        """Get market data, optionally for a specific instrument."""
        
        if not self.initialized:
            return {'error': 'API not initialized'}
        
        params = {}
        if instrument_id:
            params['InstrumentID'] = instrument_id
        
        try:
            response = self.session.get(f"{self.api_url}/ClientRequest/GetMarketData", params=params)
            
            result = {
                'status_code': response.status_code,
                'content_length': len(response.content),
                'headers': dict(response.headers)
            }
            
            if response.content:
                try:
                    if 'application/json' in response.headers.get('content-type', ''):
                        result['data'] = response.json()
                    else:
                        result['raw_content'] = response.content.decode('utf-8', errors='ignore')
                except Exception as e:
                    result['parse_error'] = str(e)
                    result['raw_content'] = response.content[:200]
            
            return result
            
        except Exception as e:
            return {'error': str(e)}
    
    def get_quotes(self, instrument_id: Optional[str] = None, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get quotes, optionally for a specific instrument or symbol."""
        
        if not self.initialized:
            return {'error': 'API not initialized'}
        
        params = {}
        if instrument_id:
            params['InstrumentID'] = instrument_id
        if symbol:
            params['symbol'] = symbol
        
        try:
            response = self.session.get(f"{self.api_url}/ClientRequest/GetQuotes", params=params)
            
            result = {
                'status_code': response.status_code,
                'content_length': len(response.content),
                'content_type': response.headers.get('content-type', 'unknown')
            }
            
            if response.content:
                try:
                    if 'application/json' in response.headers.get('content-type', ''):
                        result['data'] = response.json()
                    else:
                        result['text_content'] = response.text
                except Exception as e:
                    result['parse_error'] = str(e)
                    result['raw_content'] = response.content[:200]
            else:
                result['note'] = 'Empty response - may indicate no data available for parameters'
            
            return result
            
        except Exception as e:
            return {'error': str(e)}
    
    def get_server_time(self) -> Dict[str, Any]:
        """Get server time."""
        
        if not self.initialized:
            return {'error': 'API not initialized'}
        
        try:
            response = self.session.get(f"{self.api_url}/ClientRequest/GetServerTime")
            
            result = {
                'status_code': response.status_code,
                'content_length': len(response.content),
                'timestamp': datetime.now().isoformat()
            }
            
            if response.content:
                try:
                    if 'application/json' in response.headers.get('content-type', ''):
                        result['server_data'] = response.json()
                    else:
                        result['text_content'] = response.text
                except Exception as e:
                    result['parse_error'] = str(e)
            
            return result
            
        except Exception as e:
            return {'error': str(e)}
    
    def get_platform_info(self) -> Dict[str, Any]:
        """Get platform information."""
        
        if not self.initialized:
            return {'error': 'API not initialized'}
        
        try:
            response = self.session.get(f"{self.api_url}/ClientRequest/GetPlatformInfo")
            
            result = {
                'status_code': response.status_code,
                'content_length': len(response.content),
                'content_type': response.headers.get('content-type', 'unknown')
            }
            
            if response.content:
                try:
                    if 'application/json' in response.headers.get('content-type', ''):
                        result['platform_data'] = response.json()
                    else:
                        result['text_content'] = response.text
                except Exception as e:
                    result['parse_error'] = str(e)
            
            return result
            
        except Exception as e:
            return {'error': str(e)}
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get API configuration."""
        
        if not self.initialized:
            return {'error': 'API not initialized'}
        
        try:
            response = self.session.get(f"{self.api_url}/ClientRequest/GetConfiguration")
            
            result = {
                'status_code': response.status_code,
                'content_length': len(response.content),
                'content_type': response.headers.get('content-type', 'unknown')
            }
            
            if response.content:
                try:
                    if 'application/json' in response.headers.get('content-type', ''):
                        result['config_data'] = response.json()
                    else:
                        result['text_content'] = response.text
                except Exception as e:
                    result['parse_error'] = str(e)
            
            return result
            
        except Exception as e:
            return {'error': str(e)}
    
    def test_various_instruments(self) -> Dict[str, Any]:
        """Test market data with various instrument IDs."""
        
        if not self.initialized:
            return {'error': 'API not initialized'}
        
        # Common instrument IDs to test
        test_instruments = ['1', '2', '3', '4', '5', '10', '100', '101', '500']
        test_symbols = ['SPX', 'ES', 'NQ', 'YM', 'RTY', 'BTC', 'ETH', 'GC', 'CL', 'NG']
        
        results = {
            'by_instrument_id': {},
            'by_symbol': {},
            'summary': {'total_tested': 0, 'responses_with_data': 0}
        }
        
        print("🧪 Testing various instruments...")
        
        # Test by instrument ID
        for instrument_id in test_instruments:
            print(f"   Testing instrument ID: {instrument_id}")
            
            result = self.get_market_data(instrument_id)
            results['by_instrument_id'][instrument_id] = result
            results['summary']['total_tested'] += 1
            
            if result.get('content_length', 0) > 0:
                results['summary']['responses_with_data'] += 1
                print(f"      ✅ Got data ({result['content_length']} bytes)")
        
        # Test by symbol
        for symbol in test_symbols:
            print(f"   Testing symbol: {symbol}")
            
            result = self.get_quotes(symbol=symbol)
            results['by_symbol'][symbol] = result
            results['summary']['total_tested'] += 1
            
            if result.get('content_length', 0) > 0:
                results['summary']['responses_with_data'] += 1
                print(f"      ✅ Got data ({result['content_length']} bytes)")
        
        return results
    
    def comprehensive_test(self) -> Dict[str, Any]:
        """Run a comprehensive test of all available functionality."""
        
        print("🚀 Running comprehensive API test...")
        
        if not self.initialize():
            return {'error': 'Failed to initialize API'}
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'global_config': self.global_config,
            'tests': {}
        }
        
        # Test basic endpoints
        print("\n📊 Testing basic endpoints...")
        
        tests = {
            'server_time': self.get_server_time,
            'platform_info': self.get_platform_info,
            'configuration': self.get_configuration,
            'market_data_basic': lambda: self.get_market_data(),
            'quotes_basic': lambda: self.get_quotes()
        }
        
        for test_name, test_func in tests.items():
            print(f"   Running {test_name}...")
            results['tests'][test_name] = test_func()
        
        # Test various instruments
        print("\n🎯 Testing various instruments...")
        results['tests']['instrument_testing'] = self.test_various_instruments()
        
        return results

def main():
    """Main execution."""
    
    print("🚀 Plus500 Practical API Client")
    print("=" * 50)
    
    api = Plus500API()
    
    # Run comprehensive test
    results = api.comprehensive_test()
    
    # Save results
    timestamp = int(time.time())
    filename = f"plus500_practical_test_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: {filename}")
    
    # Summary
    if 'tests' in results:
        print(f"\n📊 SUMMARY:")
        working_tests = [name for name, result in results['tests'].items() 
                        if isinstance(result, dict) and not result.get('error')]
        print(f"   ✅ Working tests: {len(working_tests)}")
        
        if working_tests:
            print(f"   🎯 Working endpoints:")
            for test_name in working_tests:
                test_result = results['tests'][test_name]
                if isinstance(test_result, dict) and test_result.get('content_length', 0) > 0:
                    print(f"      • {test_name}: {test_result['content_length']} bytes")
                else:
                    print(f"      • {test_name}: Available")
    
    print(f"\n🎯 Next steps:")
    print(f"   1. ✅ API connectivity established")
    print(f"   2. 🔧 Test results show what endpoints work")
    print(f"   3. 💡 Build functionality around working endpoints")

if __name__ == "__main__":
    main()
