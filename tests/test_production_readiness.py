"""
Real Plus500US Authentication and Order Flow Test
This test goes through the actual authentication process to identify necessary adjustments
"""
import os
import sys
from pathlib import Path
from decimal import Decimal
import time
import json

# Fix encoding
if os.name == 'nt':
    try:
        os.system('chcp 65001 > nul')
    except:
        pass

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from plus500us_client import load_config
from plus500us_client.auth import AuthClient
from plus500us_client.session import SessionManager
from plus500us_client.trading import TradingClient
from plus500us_client.models import OrderDraft
from plus500us_client.errors import AuthenticationError, OrderRejectError, CaptchaRequiredError

def print_header(title):
    """Print a formatted header"""
    print("\n" + "="*70)
    print(f" {title}")
    print("="*70)

def print_step(step_num, description):
    """Print a formatted step"""
    print(f"\n🔥 STEP {step_num}: {description}")
    print("-" * 50)

def save_debug_info(filename, data):
    """Save debug information to file"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            if isinstance(data, dict):
                json.dump(data, f, indent=2, default=str)
            else:
                f.write(str(data))
        print(f"   📄 Debug info saved: {filename}")
    except Exception as e:
        print(f"   ⚠️  Could not save debug info: {e}")

def test_real_authentication():
    """Test the real authentication flow"""
    print_header("Real Plus500US Authentication Test")
    
    print("🔐 AUTHENTICATION FLOW TEST")
    print("   Purpose: Identify real authentication requirements")
    print("   Method: Interactive with detailed logging")
    print("   Goal: Successful demo account access")
    
    config = load_config()
    print(f"\n⚙️  Configuration:")
    print(f"   Base URL: {config.base_url}")
    print(f"   Account Type: {config.account_type}")
    
    session_manager = None
    auth_client = None
    
    try:
        print_step(1, "Initialize Components")
        
        session_manager = SessionManager(config)
        auth_client = AuthClient(config, session_manager)
        
        print("✅ Components initialized")
        
        print_step(2, "Check Initial Connection")
        
        # Test basic connectivity
        try:
            response = session_manager.session.get(config.base_url, timeout=10)
            print(f"✅ Connection successful: HTTP {response.status_code}")
            print(f"   Response size: {len(response.text)} characters")
            
            # Check for common Plus500 elements
            if "plus500" in response.text.lower():
                print("✅ Plus500 platform detected")
            else:
                print("⚠️  Plus500 branding not detected in response")
                
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False, {"error": "connection_failed", "details": str(e)}
        
        print_step(3, "Login Page Analysis")
        
        try:
            login_url = f"{config.base_url}/trade?innerTags=_cc_&page=login"
            print(f"🌐 Accessing login page: {login_url}")
            
            login_response = session_manager.session.get(login_url, timeout=20)
            print(f"✅ Login page response: HTTP {login_response.status_code}")
            
            # Save login page for analysis
            save_debug_info("login_page_response.html", login_response.text)
            
            # Check for authentication challenges
            page_content = login_response.text.lower()
            challenges = {
                "captcha": any(term in page_content for term in ["captcha", "recaptcha", "are you human"]),
                "2fa": any(term in page_content for term in ["two-factor", "2fa", "authenticator"]),
                "csrf": "csrf" in page_content or "_token" in page_content,
                "javascript_required": "javascript" in page_content or "js" in page_content
            }
            
            print("🔍 Authentication challenges detected:")
            for challenge, detected in challenges.items():
                status = "⚠️  DETECTED" if detected else "✅ Not detected"
                print(f"   {challenge.upper()}: {status}")
            
            if challenges["captcha"]:
                print("\n🤖 CAPTCHA DETECTED - Testing interactive handoff...")
                try:
                    print("   Attempting interactive handoff for CAPTCHA bypass...")
                    auth_client.interactive_handoff()
                    print("✅ Interactive handoff completed")
                except Exception as e:
                    print(f"⚠️  Interactive handoff failed: {e}")
                    print("📝 Manual intervention required for CAPTCHA")
                    return False, {
                        "error": "captcha_required",
                        "solution": "Use interactive handoff or browser session import",
                        "challenges": challenges
                    }
            
        except Exception as e:
            print(f"❌ Login page analysis failed: {e}")
            return False, {"error": "login_page_failed", "details": str(e)}
        
        print_step(4, "Credential Authentication")
        
        print("🔑 Testing credential authentication...")
        print("   Note: This will use real credentials for demo account")
        
        try:
            # Attempt authentication with interactive mode for better error handling
            login_result = auth_client.login(
                account_type="demo",
                interactive_mode=True
            )
            
            print("🎉 AUTHENTICATION SUCCESSFUL!")
            print("📊 Login result:")
            for key, value in login_result.items():
                if key != "post_login_data":  # Don't print potentially large data
                    print(f"   {key}: {value}")
            
            # Save authentication result for analysis
            save_debug_info("auth_result.json", login_result)
            
            return True, {
                "success": True,
                "account_type": login_result.get("account_type"),
                "challenges": challenges,
                "login_result": login_result
            }
            
        except CaptchaRequiredError as e:
            print(f"🤖 CAPTCHA Required: {e}")
            print("\n📝 CAPTCHA HANDLING REQUIRED:")
            print("   1. Plus500 requires CAPTCHA verification")
            print("   2. Interactive handoff needed")
            print("   3. Browser session import recommended")
            
            return False, {
                "error": "captcha_required",
                "message": str(e),
                "solution": "implement_browser_session_import",
                "challenges": challenges
            }
            
        except AuthenticationError as e:
            print(f"🔐 Authentication Error: {e}")
            print("\n📝 AUTHENTICATION ISSUES:")
            print("   1. Check credentials are correct")
            print("   2. Verify account type (demo/live)")
            print("   3. Check for 2FA requirements")
            
            return False, {
                "error": "authentication_failed",
                "message": str(e),
                "solution": "verify_credentials_and_2fa",
                "challenges": challenges
            }
            
        except Exception as e:
            print(f"❌ Unexpected authentication error: {e}")
            import traceback
            traceback.print_exc()
            
            return False, {
                "error": "unexpected_auth_error",
                "message": str(e),
                "traceback": traceback.format_exc(),
                "challenges": challenges
            }
    
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        return False, {"error": "test_setup_failed", "details": str(e)}

def test_api_endpoints(session_manager, config):
    """Test available API endpoints after authentication"""
    print_step(5, "API Endpoint Discovery")
    
    print("🔍 Testing API endpoints...")
    
    endpoints_to_test = [
        "/api/account",
        "/api/instruments", 
        "/api/positions",
        "/api/orders",
        "/api/quotes",
        "/api/balance"
    ]
    
    endpoint_results = {}
    
    for endpoint in endpoints_to_test:
        url = f"{config.base_url}{endpoint}"
        try:
            response = session_manager.session.get(url, timeout=10)
            endpoint_results[endpoint] = {
                "status_code": response.status_code,
                "accessible": response.status_code < 400,
                "response_size": len(response.text)
            }
            
            status = "✅ ACCESSIBLE" if response.status_code < 400 else f"❌ ERROR {response.status_code}"
            print(f"   {endpoint}: {status}")
            
            if response.status_code < 400 and response.text:
                # Save successful responses for analysis
                filename = f"api_response_{endpoint.replace('/', '_')}.json"
                try:
                    data = response.json()
                    save_debug_info(filename, data)
                except:
                    save_debug_info(filename, response.text)
                    
        except Exception as e:
            endpoint_results[endpoint] = {
                "status_code": None,
                "accessible": False,
                "error": str(e)
            }
            print(f"   {endpoint}: ❌ FAILED - {e}")
    
    return endpoint_results

def test_order_placement(trading_client):
    """Test actual order placement"""
    print_step(6, "Real Order Placement Test")
    
    print("🎯 Testing GC order placement...")
    print("   IMPORTANT: This will place a REAL order on the demo account")
    
    # Confirm with user
    confirmation = input("\n⚠️  Proceed with REAL demo order placement? (y/N): ").strip().lower()
    if confirmation != 'y':
        print("⏸️  Order placement test skipped by user")
        return False, {"skipped": True, "reason": "user_declined"}
    
    try:
        # Create GC order
        order_draft = OrderDraft(
            instrument_id="GC",  # Gold futures
            side="BUY",
            order_type="MARKET",
            qty=Decimal("1"),
            time_in_force="DAY"
        )
        
        print(f"📝 Order draft created:")
        print(f"   Instrument: {order_draft.instrument_id}")
        print(f"   Side: {order_draft.side}")
        print(f"   Type: {order_draft.order_type}")
        print(f"   Quantity: {order_draft.qty}")
        
        # Place the order
        print("\n🚀 PLACING ORDER...")
        placed_order = trading_client.place_order(order_draft)
        
        print("🎉 ORDER PLACED SUCCESSFULLY!")
        print("📊 Order details:")
        print(f"   Order ID: {placed_order.id}")
        print(f"   Status: {placed_order.status}")
        print(f"   Filled Qty: {placed_order.filled_qty}")
        print(f"   Avg Price: {placed_order.avg_price}")
        
        # Save order result
        order_data = {
            "order_id": placed_order.id,
            "status": placed_order.status,
            "filled_qty": str(placed_order.filled_qty),
            "avg_price": str(placed_order.avg_price) if placed_order.avg_price else None,
            "create_time": placed_order.create_time
        }
        save_debug_info("placed_order.json", order_data)
        
        return True, {"success": True, "order": order_data}
        
    except OrderRejectError as e:
        print(f"❌ Order rejected: {e}")
        return False, {"error": "order_rejected", "message": str(e)}
        
    except Exception as e:
        print(f"❌ Order placement failed: {e}")
        import traceback
        traceback.print_exc()
        return False, {"error": "order_failed", "message": str(e), "traceback": traceback.format_exc()}

def main():
    """Main test function"""
    print_header("Plus500US Production Readiness Test")
    
    print("🔬 PRODUCTION READINESS ASSESSMENT")
    print("   Purpose: Identify real-world adjustments needed")
    print("   Scope: End-to-end authentication and trading")
    print("   Account: Demo (safe testing)")
    print("   Output: Actionable improvement recommendations")
    
    results = {
        "timestamp": time.time(),
        "test_results": {},
        "adjustments_needed": [],
        "production_ready": False
    }
    
    # Test 1: Authentication
    auth_success, auth_result = test_real_authentication()
    results["test_results"]["authentication"] = auth_result
    
    if not auth_success:
        print(f"\n❌ Authentication failed: {auth_result.get('error')}")
        results["adjustments_needed"].append({
            "priority": "HIGH",
            "category": "Authentication",
            "issue": auth_result.get("error"),
            "solution": auth_result.get("solution"),
            "details": auth_result.get("message")
        })
        
        # Save results and exit
        save_debug_info("production_readiness_results.json", results)
        return False
    
    print("✅ Authentication successful - proceeding with API tests...")
    
    # Test 2: API Endpoints (if authenticated)
    try:
        config = load_config()
        session_manager = SessionManager(config)
        auth_client = AuthClient(config, session_manager)
        
        # Re-authenticate for API tests
        auth_client.login(account_type="demo", interactive_mode=False)
        
        endpoint_results = test_api_endpoints(session_manager, config)
        results["test_results"]["api_endpoints"] = endpoint_results
        
        # Check which endpoints are accessible
        accessible_endpoints = [ep for ep, result in endpoint_results.items() if result.get("accessible")]
        inaccessible_endpoints = [ep for ep, result in endpoint_results.items() if not result.get("accessible")]
        
        if inaccessible_endpoints:
            results["adjustments_needed"].append({
                "priority": "MEDIUM",
                "category": "API Access",
                "issue": "Some API endpoints not accessible",
                "details": inaccessible_endpoints,
                "solution": "Verify API permissions and endpoint URLs"
            })
        
        # Test 3: Order Placement (if API is accessible)
        if "/api/orders" in accessible_endpoints:
            trading_client = TradingClient(config, session_manager)
            order_success, order_result = test_order_placement(trading_client)
            results["test_results"]["order_placement"] = order_result
            
            if not order_success and not order_result.get("skipped"):
                results["adjustments_needed"].append({
                    "priority": "HIGH",
                    "category": "Order Placement",
                    "issue": order_result.get("error"),
                    "solution": "Fix order placement implementation",
                    "details": order_result.get("message")
                })
            elif order_success:
                print("✅ Order placement successful!")
        else:
            results["adjustments_needed"].append({
                "priority": "HIGH", 
                "category": "Trading API",
                "issue": "Orders API endpoint not accessible",
                "solution": "Verify trading permissions and API endpoint"
            })
    
    except Exception as e:
        print(f"❌ API testing failed: {e}")
        results["adjustments_needed"].append({
            "priority": "HIGH",
            "category": "API Integration",
            "issue": "API testing failed",
            "solution": "Debug API integration issues",
            "details": str(e)
        })
    
    # Assessment
    high_priority_issues = [adj for adj in results["adjustments_needed"] if adj["priority"] == "HIGH"]
    results["production_ready"] = len(high_priority_issues) == 0
    
    # Save final results
    save_debug_info("production_readiness_results.json", results)
    
    # Print assessment
    print_header("Production Readiness Assessment")
    
    if results["production_ready"]:
        print("🎉 PRODUCTION READY!")
        print("   All critical tests passed")
        print("   SDK ready for live demo trading")
    else:
        print("⚠️  ADJUSTMENTS NEEDED BEFORE PRODUCTION")
        print(f"   {len(high_priority_issues)} high-priority issues found")
    
    print(f"\n📊 Test Results Summary:")
    print(f"   Authentication: {'✅ PASS' if auth_success else '❌ FAIL'}")
    print(f"   API Access: {'✅ PASS' if 'api_endpoints' in results['test_results'] else '❌ FAIL'}")
    print(f"   Order Placement: {'✅ PASS' if results['test_results'].get('order_placement', {}).get('success') else '❌ NEEDS TESTING'}")
    
    if results["adjustments_needed"]:
        print(f"\n🔧 Required Adjustments:")
        for i, adjustment in enumerate(results["adjustments_needed"], 1):
            print(f"   {i}. {adjustment['category']} ({adjustment['priority']} priority)")
            print(f"      Issue: {adjustment['issue']}")
            print(f"      Solution: {adjustment['solution']}")
    
    return results["production_ready"]

if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n🚀 SDK is production ready!")
        print("   You can start using it for demo trading")
    else:
        print("\n🔧 Please address the identified issues first")
        print("   Check the generated debug files for details")
        sys.exit(1)