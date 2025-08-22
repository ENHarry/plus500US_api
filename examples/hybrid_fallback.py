"""
Hybrid automation with intelligent fallback example

This example demonstrates how the hybrid system automatically
switches between requests and WebDriver based on conditions.
"""
import os
import sys
from pathlib import Path
from decimal import Decimal

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from plus500us_client import load_config
from plus500us_client.hybrid import MethodSelector, FallbackHandler, AutomationMethod
from plus500us_client.errors import CaptchaRequiredError, AutomationBlockedError


# Mock functions to simulate different automation scenarios
def mock_login_operation(email, password, method: AutomationMethod = None):
    """Mock login operation that demonstrates fallback behavior"""
    print(f"   🔄 Attempting login with {method.value} method...")
    
    if method == AutomationMethod.REQUESTS:
        # Simulate captcha challenge for requests method
        print("   🤖 Anti-bot protection detected!")
        raise CaptchaRequiredError("Please complete captcha verification")
    
    elif method == AutomationMethod.WEBDRIVER:
        # Simulate successful WebDriver login
        print("   ✅ WebDriver login successful!")
        return {
            "authenticated": True,
            "method": "webdriver",
            "session_id": "WD_SESSION_123",
            "account_type": "demo"
        }


def mock_trading_operation(instrument, side, quantity, method: AutomationMethod = None):
    """Mock trading operation that works with WebDriver"""
    print(f"   🔄 Attempting trade with {method.value} method...")
    
    if method == AutomationMethod.REQUESTS:
        # Simulate trading blocked for requests
        print("   🚫 Trading automation blocked!")
        raise AutomationBlockedError("Automated trading detected and blocked")
    
    elif method == AutomationMethod.WEBDRIVER:
        # Simulate successful WebDriver trading
        print("   ✅ WebDriver trading successful!")
        return {
            "success": True,
            "order_id": f"WD_ORDER_{instrument}_{side}",
            "method": "webdriver"
        }


def mock_data_operation(endpoint, method: AutomationMethod = None):
    """Mock data operation that works with both methods"""
    print(f"   🔄 Fetching data with {method.value} method...")
    
    # Data operations work with both methods
    return {
        "success": True,
        "data": f"Sample data from {endpoint}",
        "method": method.value
    }


def main():
    print("=== Plus500US Hybrid Automation with Intelligent Fallback ===")
    print()
    
    # Load configuration
    config = load_config()
    config.preferred_method = "auto"  # Enable automatic method selection
    
    print(f"Preferred Method: {config.preferred_method}")
    print()
    
    # Initialize hybrid components
    method_selector = MethodSelector(config)
    fallback_handler = FallbackHandler(config, method_selector)
    
    print("🧠 Hybrid System Components Initialized:")
    print("   ✅ Method Selector - Chooses optimal automation method")
    print("   ✅ Fallback Handler - Handles failures and retries")
    print("   ✅ Circuit Breaker - Protects against repeated failures")
    print()
    
    # Example 1: Login with fallback
    print("🔐 Example 1: Login with Automatic Fallback")
    print("   Expected behavior: requests → captcha → fallback to WebDriver")
    
    try:
        result = fallback_handler.execute_with_fallback(
            mock_login_operation,
            operation="login",
            context={},
            email="demo@example.com",
            password="password123"
        )
        
        print(f"   🎉 Login successful with {result['method']} method!")
        print(f"   Session ID: {result.get('session_id', 'N/A')}")
        
    except Exception as e:
        print(f"   ❌ Login failed: {e}")
    
    print()
    
    # Example 2: Trading operation (prefers WebDriver)
    print("📈 Example 2: Trading Operation")
    print("   Expected behavior: Direct WebDriver (trading prefers reliable method)")
    
    try:
        result = fallback_handler.execute_with_fallback(
            mock_trading_operation,
            operation="trading",
            context={},
            instrument="EURUSD",
            side="BUY",
            quantity=Decimal("1")
        )
        
        print(f"   🎉 Trading successful with {result['method']} method!")
        print(f"   Order ID: {result.get('order_id', 'N/A')}")
        
    except Exception as e:
        print(f"   ❌ Trading failed: {e}")
    
    print()
    
    # Example 3: Data operation (tries requests first)
    print("📊 Example 3: Data Operation")
    print("   Expected behavior: requests first (data operations are lighter)")
    
    try:
        result = fallback_handler.execute_with_fallback(
            mock_data_operation,
            operation="market_data",
            context={},
            endpoint="/instruments"
        )
        
        print(f"   ✅ Data retrieval successful with {result['method']} method!")
        print(f"   Data: {result.get('data', 'N/A')}")
        
    except Exception as e:
        print(f"   ❌ Data operation failed: {e}")
    
    print()
    
    # Example 4: Circuit breaker demonstration
    print("⚡ Example 4: Circuit Breaker Protection")
    print("   Simulating repeated failures to trigger circuit breaker...")
    
    # Lower circuit breaker threshold for demonstration
    fallback_handler.circuit_breaker_threshold = 2
    
    def failing_operation(method: AutomationMethod = None):
        if method == AutomationMethod.REQUESTS:
            raise Exception("Service unavailable")
        return "success"
    
    # Trigger failures to open circuit breaker
    for i in range(3):
        try:
            print(f"   Attempt {i+1}:")
            fallback_handler.execute_with_fallback(
                failing_operation,
                operation="test_operation",
                context={}
            )
        except Exception as e:
            print(f"     ❌ Failed: {e}")
    
    # Check circuit breaker status
    circuit_status = fallback_handler.get_circuit_status()
    print(f"   Circuit Status: {circuit_status}")
    
    if circuit_status.get("requests", {}).get("is_open"):
        print("   ⚡ Circuit breaker OPENED for requests method")
        print("   🔄 Future operations will skip requests automatically")
    
    print()
    
    # Example 5: Health check
    print("🏥 Example 5: System Health Check")
    
    health = fallback_handler.health_check()
    print(f"   Overall Status: {health['overall_status']}")
    
    for method, status in health['methods'].items():
        print(f"   {method.title()} Method:")
        print(f"     Status: {status['status']}")
        print(f"     Failures: {status['failures']}")
        print(f"     Circuit Open: {status['circuit_open']}")
    
    if health['recommendations']:
        print("   📝 Recommendations:")
        for rec in health['recommendations']:
            print(f"     • {rec}")
    
    print()
    
    # Example 6: Method selection statistics
    print("📈 Example 6: Method Selection Statistics")
    
    stats = method_selector.get_method_stats()
    print(f"   Failure Count: {stats['failure_count']}")
    print(f"   Preferred Method: {stats['preferred_method']}")
    print(f"   WebDriver Available: {stats['webdriver_available']}")
    
    if stats['history']:
        print("   📊 Operation History:")
        for operation, result in stats['history'].items():
            print(f"     {operation}: {result}")
    
    print()
    
    # Example 7: Manual method forcing
    print("🎯 Example 7: Manual Method Selection")
    
    # Force WebDriver method
    fallback_handler.force_method(AutomationMethod.WEBDRIVER)
    print("   🔧 Forced method to WebDriver")
    
    try:
        result = fallback_handler.execute_with_fallback(
            mock_data_operation,
            operation="forced_test",
            context={},
            endpoint="/account"
        )
        print(f"   ✅ Forced operation successful with {result['method']}")
        
    except Exception as e:
        print(f"   ❌ Forced operation failed: {e}")
    
    print()
    
    # Example 8: Context-aware method selection
    print("🧠 Example 8: Context-Aware Method Selection")
    
    contexts = [
        {"captcha_present": True, "description": "Captcha detected"},
        {"status_code": 429, "description": "Rate limited"},
        {"cloudflare_challenge": True, "description": "Cloudflare challenge"},
        {"error_message": "blocked", "description": "Access blocked"},
        {}, # Normal context
    ]
    
    for context in contexts:
        method = method_selector.select_method("adaptive_test", context)
        desc = context.get("description", "Normal operation")
        print(f"   {desc}: → {method.value}")
    
    print()
    
    print("🎯 Hybrid System Features Demonstrated:")
    print("   ✅ Intelligent method selection based on operation type")
    print("   ✅ Automatic fallback when primary method fails")
    print("   ✅ Circuit breaker protection against repeated failures")
    print("   ✅ Context-aware adaptation (captcha, rate limits, etc.)")
    print("   ✅ Health monitoring and diagnostics")
    print("   ✅ Manual method forcing for specific scenarios")
    print("   ✅ Operation history and failure tracking")
    print()
    
    print("🛡️  Reliability Features:")
    print("   ✅ Graceful degradation when methods fail")
    print("   ✅ Exponential backoff for retries")
    print("   ✅ Circuit breaker prevents cascading failures")
    print("   ✅ Method selection learns from failure patterns")
    
    return True


if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n🎉 Hybrid fallback automation example completed!")
        print("\n📚 Key Benefits:")
        print("   - Automatic adaptation to Plus500's anti-bot measures")
        print("   - Intelligent method selection based on operation context")
        print("   - Built-in reliability with circuit breaker protection")
        print("   - Seamless user experience despite underlying complexity")
    else:
        print("\n💥 Hybrid fallback automation example failed!")
        sys.exit(1)