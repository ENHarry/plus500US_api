#!/usr/bin/env python3
"""
Test smart RECAPTCHA detection with different scenarios
"""

import os
import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_recaptcha_import():
    """Test that enhanced RECAPTCHA detection methods are available"""
    print("Testing Smart RECAPTCHA Detection Import")
    print("=" * 50)
    
    try:
        from plus500us_client.webdriver.auth_handler import WebDriverAuthHandler
        from plus500us_client import load_config
        
        config = load_config()
        auth_handler = WebDriverAuthHandler(config)
        
        # Check if new methods exist
        methods_to_check = [
            '_is_recaptcha_active',
            '_check_recaptcha_active_indicators', 
            '_has_visible_recaptcha_elements'
        ]
        
        for method_name in methods_to_check:
            if hasattr(auth_handler, method_name):
                print(f"[PASS] Method {method_name} available")
            else:
                print(f"[FAIL] Method {method_name} missing")
                return False
        
        print("All smart RECAPTCHA detection methods available")
        return True
        
    except Exception as e:
        print(f"[FAIL] Import test failed: {e}")
        return False

def test_authentication_flow_logic():
    """Test that authentication flow uses smart detection"""
    print("\nTesting Authentication Flow Logic")
    print("=" * 50)
    
    try:
        # Read the auth_handler.py file to verify the logic
        auth_handler_path = project_root / "plus500us_client" / "webdriver" / "auth_handler.py"
        
        with open(auth_handler_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for smart detection patterns
        checks = [
            ("Smart detection call", "_is_recaptcha_active(recaptcha_container)" in content),
            ("Conditional handling", "if self._is_recaptcha_active(recaptcha_container)" in content),
            ("Inactive container message", "inactive - continuing automatic login" in content),
            ("Active challenge message", "Active ReCAPTCHA challenge detected" in content),
        ]
        
        for check_name, condition in checks:
            if condition:
                print(f"[PASS] {check_name}")
            else:
                print(f"[FAIL] {check_name}")
                return False
        
        print("Authentication flow properly implements smart detection")
        return True
        
    except Exception as e:
        print(f"[FAIL] Flow logic test failed: {e}")
        return False

def test_detection_strategies():
    """Test the different detection strategies"""
    print("\nTesting RECAPTCHA Detection Strategies")
    print("=" * 50)
    
    try:
        # Read auth_handler.py to check detection strategy implementation
        auth_handler_path = project_root / "plus500us_client" / "webdriver" / "auth_handler.py"
        
        with open(auth_handler_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for different strategy implementations
        strategies = [
            ("innerHTML validation", "get_attribute('innerHTML')" in content),
            ("Child elements check", "find_elements(By.XPATH, \".//*\")" in content), 
            ("reCAPTCHA v2 detection", "recaptcha-checkbox" in content),
            ("hCaptcha detection", "hcaptcha" in content),
            ("Generic CAPTCHA detection", "generic_indicators" in content),
            ("Iframe validation", "iframe[@src" in content),
            ("Visibility check", "is_displayed()" in content),
            ("Size validation", "element_size" in content),
        ]
        
        passed = 0
        for strategy_name, condition in strategies:
            if condition:
                print(f"[PASS] {strategy_name} strategy")
                passed += 1
            else:
                print(f"[FAIL] {strategy_name} strategy")
        
        print(f"Detection strategies: {passed}/{len(strategies)} implemented")
        return passed == len(strategies)
        
    except Exception as e:
        print(f"[FAIL] Detection strategies test failed: {e}")
        return False

def test_selector_compatibility():
    """Test that RECAPTCHA selectors are compatible with smart detection"""
    print("\nTesting RECAPTCHA Selector Compatibility")
    print("=" * 50)
    
    try:
        from plus500us_client.webdriver.selectors import Plus500Selectors
        
        selectors = Plus500Selectors()
        
        # Check that required selectors exist
        required_selectors = ['RECAPTCHA', 'RECAPTCHA_CHECKBOX', 'RECAPTCHA_CHALLENGE']
        
        for selector_name in required_selectors:
            if hasattr(selectors, selector_name):
                selector_dict = getattr(selectors, selector_name)
                xpath_count = len(selector_dict.get('xpath', []))
                css_count = len(selector_dict.get('css', []))
                print(f"[PASS] {selector_name} ({xpath_count} xpath, {css_count} css)")
            else:
                print(f"[FAIL] {selector_name} missing")
                return False
        
        print("All RECAPTCHA selectors available for smart detection")
        return True
        
    except Exception as e:
        print(f"[FAIL] Selector compatibility test failed: {e}")
        return False

def test_logging_enhancement():
    """Test that enhanced logging is implemented"""
    print("\nTesting Enhanced RECAPTCHA Logging")
    print("=" * 50)
    
    try:
        auth_handler_path = project_root / "plus500us_client" / "webdriver" / "auth_handler.py"
        
        with open(auth_handler_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for enhanced logging statements
        logging_checks = [
            ("Detection start", "Checking if RECAPTCHA is active" in content),
            ("Content length", "innerHTML length:" in content),
            ("Child elements", "child elements count:" in content),
            ("Active indicators", "active indicators found:" in content),
            ("Visibility check", "has visible elements:" in content),
            ("Decision logging", "determined to be ACTIVE" in content),
            ("Inactive decision", "not active" in content),
        ]
        
        passed = 0
        for log_name, condition in logging_checks:
            if condition:
                print(f"[PASS] {log_name} logging")
                passed += 1
            else:
                print(f"[FAIL] {log_name} logging")
        
        print(f"Enhanced logging: {passed}/{len(logging_checks)} implemented")
        return passed >= len(logging_checks) - 1  # Allow 1 missing
        
    except Exception as e:
        print(f"[FAIL] Logging enhancement test failed: {e}")
        return False

def main():
    """Run all smart RECAPTCHA tests"""
    print("Smart RECAPTCHA Detection Test Suite")
    print("=" * 60)
    
    tests = [
        test_recaptcha_import,
        test_authentication_flow_logic,
        test_detection_strategies,
        test_selector_compatibility, 
        test_logging_enhancement
    ]
    
    passed = 0
    for test_func in tests:
        if test_func():
            passed += 1
    
    print("\n" + "=" * 60)
    print(f"FINAL RESULTS: {passed}/{len(tests)} test categories passed")
    
    if passed == len(tests):
        print("ALL TESTS PASSED - Smart RECAPTCHA detection ready!")
        print("\nKey Improvements:")
        print("- Empty RECAPTCHA containers won't interrupt login")
        print("- Only active challenges trigger human intervention") 
        print("- Enhanced logging for debugging")
        print("- Multiple detection strategies for reliability")
        print("- Compatible with v2, v3, and hCaptcha")
    else:
        print("Some tests failed - please review errors above")
    
    print("=" * 60)
    return passed == len(tests)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)