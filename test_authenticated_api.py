#!/usr/bin/env python3
"""
Test authenticated API calls to see what actually works with current session
"""

import requests
import json
from plus500us_client.requests.plus500_futures_auth import Plus500FuturesAuth
from dotenv import load_dotenv
import os

# Load credentials
load_dotenv()
email = os.getenv('email', '').strip('"')
password = os.getenv('password', '').strip('"')

def test_api_endpoints():
    """Test various API endpoints to see what works with current session"""
    
    print("🧪 Testing API Endpoints with Current Authentication")
    print("=" * 60)
    
    # Authenticate first
    client = Plus500FuturesAuth(debug=True)
    result = client.authenticate(email, password)
    
    if not result.get('success'):
        print(f"❌ Authentication failed: {result.get('error')}")
        return
    
    session = client.get_authenticated_session()
    if not session:
        print("❌ Failed to get authenticated session")
        return [], []
        
    api_url = client.api_url
    
    # Test various endpoints
    endpoints = [
        # Basic status endpoints
        ("/handle-cookies", "GET", None),
        ("/ClientRequest/GetPostLoginInfoImm", "GET", None),
        ("/ClientRequest/GetChartDataImm", "GET", None),
        ("/ClientRequest/GetTradeInstruments", "GET", None),
        
        # Market data endpoints
        ("/ClientRequest/GetMarketData", "GET", None),
        ("/ClientRequest/GetInstruments", "GET", None),
        ("/ClientRequest/GetCategories", "GET", None),
        
        # Account endpoints
        ("/ClientRequest/GetAccountInfo", "GET", None),
        ("/ClientRequest/GetBalance", "GET", None),
        ("/ClientRequest/GetPositions", "GET", None),
        ("/ClientRequest/GetOrders", "GET", None),
        
        # Try with different parameters
        ("/ClientRequest/GetInstruments", "GET", {"CategoryID": "1"}),
        ("/ClientRequest/GetMarketData", "GET", {"InstrumentID": "1"}),
    ]
    
    successful_endpoints = []
    failed_endpoints = []
    
    for endpoint, method, params in endpoints:
        try:
            url = f"{api_url}{endpoint}"
            print(f"\n🔍 Testing: {method} {endpoint}")
            
            if method == "GET":
                response = session.get(url, params=params)
            else:
                response = session.post(url, json=params)
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"   ✅ Success - Response: {json.dumps(data, indent=2)[:200]}...")
                    successful_endpoints.append((endpoint, response.status_code, data))
                except:
                    print(f"   ✅ Success - HTML/Text response (length: {len(response.text)})")
                    successful_endpoints.append((endpoint, response.status_code, "HTML/Text"))
            else:
                print(f"   ❌ Failed - {response.status_code}")
                failed_endpoints.append((endpoint, response.status_code))
                
        except Exception as e:
            print(f"   💥 Exception: {e}")
            failed_endpoints.append((endpoint, f"Exception: {e}"))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    print(f"\n✅ Successful endpoints ({len(successful_endpoints)}):")
    for endpoint, status, data in successful_endpoints:
        data_preview = str(data)[:100] + "..." if len(str(data)) > 100 else str(data)
        print(f"   {endpoint} -> {status} - {data_preview}")
    
    print(f"\n❌ Failed endpoints ({len(failed_endpoints)}):")
    for endpoint, status in failed_endpoints:
        print(f"   {endpoint} -> {status}")
    
    # Test cookies and session info
    print(f"\n🍪 Current session cookies:")
    for cookie in session.cookies:
        print(f"   {cookie.name} = {cookie.value[:50]}...")
    
    return successful_endpoints, failed_endpoints

def test_web_app_integration():
    """Test if we can extract useful info from the web app itself"""
    
    print("\n🌐 Testing Web App Integration")
    print("=" * 40)
    
    client = Plus500FuturesAuth(debug=False)
    result = client.authenticate(email, password)
    
    if not result.get('success'):
        print(f"❌ Authentication failed")
        return
    
    session = client.get_authenticated_session()
    if not session:
        print(f"❌ Authentication failed")
        return None
    
    # Try to access the main trading page
    try:
        main_page_url = f"{client.base_url}/trade"
        print(f"🔍 Accessing main trading page: {main_page_url}")
        
        response = session.get(main_page_url)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            # Look for useful JavaScript variables or data
            content = response.text
            
            # Look for common patterns that might contain session or instrument data
            patterns = [
                'globalConfig =',
                'window.globalConfig',
                'sessionData',
                'userConfig',
                'instrumentData',
                'ProductManager',
            ]
            
            found_data = {}
            for pattern in patterns:
                if pattern in content:
                    # Extract a snippet around the pattern
                    start = content.find(pattern)
                    if start != -1:
                        snippet = content[start:start+500]
                        found_data[pattern] = snippet
                        print(f"   ✅ Found {pattern}: {snippet[:100]}...")
            
            if found_data:
                print(f"\n📄 Extracted {len(found_data)} data patterns from web page")
                return found_data
            else:
                print("   ℹ️ No recognizable data patterns found")
        
    except Exception as e:
        print(f"   💥 Exception accessing web app: {e}")
    
    return None

if __name__ == "__main__":
    if not email or not password:
        print("❌ Missing credentials in .env file")
        exit(1)
    
    # Test API endpoints
    result = test_api_endpoints()
    if result:
        successful, failed = result
    else:
        successful, failed = [], []
    
    # Test web app integration
    web_data = test_web_app_integration()
    
    print("\n🎯 NEXT STEPS:")
    if successful:
        print("1. ✅ Some API endpoints are working - we can proceed with API integration")
        print("2. 🔧 Focus on the working endpoints to build functionality")
        print("3. 📊 Use successful endpoints to extract useful data")
    else:
        print("1. 🔄 All API endpoints failed - may need alternative approach")
        print("2. 🌐 Web app integration might be the better path")
        print("3. 🤖 Browser automation might be necessary for full functionality")
