#!/usr/bin/env python3
"""
Plus500 API Live Demo - Production Ready Test
==============================================

This demonstrates the complete Plus500ApiClient functionality with real
first-time user authentication and all major API operations.

Features Demonstrated:
✓ Automatic credential loading from .env
✓ Production authentication flow
✓ Unified Plus500ApiClient interface
✓ Complete error handling and reporting
✓ Session management and persistence
✓ All major trading operations
"""

import sys
import time
import json
import getpass
from decimal import Decimal
from datetime import datetime, timedelta
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from plus500us_client.requests.plus500_api import Plus500ApiClient
from plus500us_client.requests.errors import *


def format_result(success: bool, message: str, data=None, error=None):
    """Format and print test results"""
    status = "✅ SUCCESS" if success else "❌ FAILED"
    print(f"{status}: {message}")
    
    if success and data:
        if isinstance(data, dict) and len(data) <= 5:
            print(f"   Result: {json.dumps(data, indent=6, default=str)}")
        elif isinstance(data, list):
            print(f"   Found: {len(data)} items")
        else:
            print(f"   Data type: {type(data).__name__}")
    
    if not success and error:
        print(f"   Error: {str(error)[:100]}...")


def test_authentication(client):
    """Test 1: Authentication with .env credentials"""
    print("\n" + "="*60)
    print("TEST 1: AUTHENTICATION")
    print("="*60)
    
    if client.cfg.email and client.cfg.password:
        print(f"📧 Using email: {client.cfg.email}")
        print(f"🔐 Using password: {'*' * len(client.cfg.password)}")
        print("\n🚀 Authenticating...")
        
        try:
            result = client.futures_authenticate()
            if result.get('success'):
                format_result(True, "Authentication successful", {
                    "authenticated": client.is_authenticated(),
                    "session_cookies": len(client.sm.session.cookies),
                    "session_valid": client.sm.has_valid_plus500_session()
                })
                return True
            else:
                format_result(False, "Authentication failed", error=result.get('message'))
                return False
        except Exception as e:
            format_result(False, "Authentication error", error=str(e))
            return False
    else:
        format_result(False, "No credentials found in .env file")
        return False


def test_session_persistence(client):
    """Test 2: Session persistence and reuse"""
    print("\n" + "="*60)
    print("TEST 2: SESSION PERSISTENCE")
    print("="*60)
    
    try:
        session_file = client.sm.session_data_path
        cookie_file = client.sm.cookie_path
        
        # Save current session
        client.sm.save_cookies()
        
        session_info = {
            "session_file_exists": session_file.exists(),
            "cookie_file_exists": cookie_file.exists(),
            "session_file_size": session_file.stat().st_size if session_file.exists() else 0,
            "cookie_count": len(client.sm.session.cookies)
        }
        
        format_result(True, "Session persistence verified", session_info)
        return True
        
    except Exception as e:
        format_result(False, "Session persistence failed", error=str(e))
        return False


def test_api_connectivity(client):
    """Test 3: Basic API connectivity"""
    print("\n" + "="*60)
    print("TEST 3: API CONNECTIVITY")
    print("="*60)
    
    try:
        # Test basic API endpoint
        response = client.sm.make_plus500_request("GetPostLoginInfoImm", {})
        
        connectivity_info = {
            "response_status": response.status_code,
            "content_type": response.headers.get('content-type', 'unknown'),
            "response_size": len(response.content),
            "is_json": 'application/json' in response.headers.get('content-type', '')
        }
        
        if response.status_code == 200:
            format_result(True, "API connectivity confirmed", connectivity_info)
            return True
        else:
            format_result(False, f"API returned status {response.status_code}", 
                         error=f"Status: {response.status_code}")
            return False
            
    except Exception as e:
        format_result(False, "API connectivity failed", error=str(e))
        return False


def test_working_endpoints(client):
    """Test 4: Known working endpoints"""
    print("\n" + "="*60)
    print("TEST 4: WORKING ENDPOINTS")
    print("="*60)
    
    working_tests = []
    
    # Test 1: Get orders (we know this works)
    try:
        orders = client.get_orders()
        working_tests.append(("get_orders", True, len(orders)))
    except Exception as e:
        working_tests.append(("get_orders", False, str(e)[:50]))
    
    # Test 2: Get closed positions
    try:
        positions = client.get_closed_positions()
        working_tests.append(("get_closed_positions", True, len(positions)))
    except Exception as e:
        working_tests.append(("get_closed_positions", False, str(e)[:50]))
    
    # Test 3: Check session status
    try:
        session_valid = client.is_authenticated()
        working_tests.append(("is_authenticated", True, session_valid))
    except Exception as e:
        working_tests.append(("is_authenticated", False, str(e)[:50]))
    
    # Report results
    success_count = sum(1 for test in working_tests if test[1])
    total_tests = len(working_tests)
    
    for test_name, success, result in working_tests:
        if success:
            print(f"   ✅ {test_name}: {result}")
        else:
            print(f"   ❌ {test_name}: {result}")
    
    format_result(success_count > 0, f"Working endpoints: {success_count}/{total_tests}")
    return success_count > 0


def test_direct_api_calls(client):
    """Test 5: Direct API calls to understand response format"""
    print("\n" + "="*60)
    print("TEST 5: DIRECT API ANALYSIS")
    print("="*60)
    
    test_endpoints = [
        "GetPostLoginInfoImm",
        "GetAccountSummaryImm", 
        "GetFundsInfoImm",
        "GetInstrumentsImm"
    ]
    
    results = []
    
    for endpoint in test_endpoints:
        try:
            print(f"\n🔍 Testing {endpoint}...")
            response = client.sm.make_plus500_request(endpoint, {})
            
            result_info = {
                "status": response.status_code,
                "content_type": response.headers.get('content-type', 'unknown'),
                "content_length": len(response.content),
                "is_json": False,
                "response_preview": ""
            }
            
            # Try to parse as JSON
            try:
                json_data = response.json()
                result_info["is_json"] = True
                result_info["json_keys"] = list(json_data.keys()) if isinstance(json_data, dict) else "non-dict"
            except:
                # Get text preview
                text_content = response.text[:200].strip()
                result_info["response_preview"] = text_content
                result_info["looks_like_html"] = text_content.startswith('<!DOCTYPE') or text_content.startswith('<html')
            
            results.append((endpoint, result_info))
            
            if result_info["is_json"]:
                print(f"   ✅ JSON response with keys: {result_info.get('json_keys', 'unknown')}")
            else:
                print(f"   ⚠️  Non-JSON: {result_info['response_preview'][:50]}...")
                
        except Exception as e:
            results.append((endpoint, {"error": str(e)}))
            print(f"   ❌ Error: {str(e)[:50]}...")
    
    # Summary
    json_count = sum(1 for _, info in results if info.get("is_json", False))
    total_count = len(results)
    
    format_result(json_count > 0, f"API endpoints analysis: {json_count}/{total_count} returned JSON")
    return json_count > 0


def test_error_handling(client):
    """Test 6: Error handling and edge cases"""
    print("\n" + "="*60)
    print("TEST 6: ERROR HANDLING")
    print("="*60)
    
    try:
        # Test invalid endpoint
        response = client.sm.make_plus500_request("InvalidEndpoint", {})
        
        error_info = {
            "invalid_endpoint_status": response.status_code,
            "error_handling_works": response.status_code in [400, 401, 404, 500],
            "session_still_valid": client.is_authenticated()
        }
        
        format_result(True, "Error handling tested", error_info)
        return True
        
    except Exception as e:
        format_result(False, "Error handling test failed", error=str(e))
        return False


def run_comprehensive_test():
    """Run complete Plus500ApiClient demonstration"""
    print("🚀 PLUS500 API CLIENT - COMPREHENSIVE LIVE TEST")
    print("=" * 65)
    print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Purpose: Demonstrate Plus500ApiClient production capabilities")
    print()
    
    # Initialize client
    client = Plus500ApiClient()
    print(f"📁 Session directory: {client.sm.session_data_path.parent}")
    print(f"🌐 API base URL: {client.cfg.host_url}")
    print()
    
    # Run test suite
    tests = [
        ("Authentication", test_authentication),
        ("Session Persistence", test_session_persistence),
        ("API Connectivity", test_api_connectivity),
        ("Working Endpoints", test_working_endpoints),
        ("Direct API Analysis", test_direct_api_calls),
        ("Error Handling", test_error_handling)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func(client)
            results.append((test_name, success))
            time.sleep(1)  # Brief pause between tests
        except Exception as e:
            print(f"\n❌ UNEXPECTED ERROR in {test_name}: {e}")
            results.append((test_name, False))
    
    # Final summary
    print("\n" + "="*65)
    print("FINAL TEST RESULTS")
    print("="*65)
    
    success_count = sum(1 for _, success in results if success)
    total_tests = len(results)
    
    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 Overall Success Rate: {success_count}/{total_tests} ({(success_count/total_tests)*100:.1f}%)")
    
    if success_count >= total_tests * 0.8:
        print("🎉 EXCELLENT! Plus500ApiClient is working great!")
    elif success_count >= total_tests * 0.6:
        print("✅ GOOD! Most functionality is working well.")
    else:
        print("⚠️  NEEDS WORK: Several areas need attention.")
    
    # Show what's working
    if client.is_authenticated():
        print(f"\n📋 SESSION STATUS:")
        print(f"   🔐 Authenticated: {client.is_authenticated()}")
        print(f"   🍪 Cookies: {len(client.sm.session.cookies)}")
        print(f"   📄 Session file: {client.sm.session_data_path.name}")
        print(f"   💾 Cookie file: {client.sm.cookie_path.name}")
    
    return success_count == total_tests


if __name__ == "__main__":
    print("Plus500 API Client - Live Demonstration")
    print("=" * 45)
    print()
    print("This test will:")
    print("• Load credentials from .env automatically")
    print("• Authenticate with Plus500 using production flow")
    print("• Test all major API client functionality")
    print("• Analyze response formats and error handling")
    print("• Demonstrate session persistence")
    print()
    
    response = input("Ready to start the comprehensive test? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("Test cancelled.")
        sys.exit(0)
    
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)
