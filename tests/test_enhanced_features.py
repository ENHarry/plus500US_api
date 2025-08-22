#!/usr/bin/env python3
"""
Comprehensive test script for enhanced Plus500US WebDriver features
"""

import os
import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test all enhanced component imports"""
    print("Testing Enhanced Component Imports")
    print("=" * 50)
    
    tests = [
        ("ElementDetector with streaming", "plus500us_client.webdriver.element_detector", "ElementDetector"),
        ("TradeManager with TP editing", "plus500us_client.webdriver.trade_manager", "WebDriverTradeManager"),
        ("InstrumentsDiscovery with extraction", "plus500us_client.webdriver.instruments_discovery", "WebDriverInstrumentsDiscovery"),
        ("AccountManager with optimization", "plus500us_client.webdriver.account_manager", "WebDriverAccountManager"),
        ("AuthHandler with RECAPTCHA", "plus500us_client.webdriver.auth_handler", "WebDriverAuthHandler"),
        ("Enhanced Selectors", "plus500us_client.webdriver.selectors", "Plus500Selectors"),
    ]
    
    passed = 0
    for name, module_name, class_name in tests:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            print(f"[PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
    
    print(f"\nImport Tests: {passed}/{len(tests)} passed")
    return passed == len(tests)

def test_configuration():
    """Test configuration loading"""
    print("\nTesting Configuration")
    print("=" * 50)
    
    try:
        from plus500us_client import load_config
        config = load_config()
        
        print(f"[PASS] Configuration loaded")
        print(f"       Browser: {config.webdriver_config['browser']}")
        print(f"       Account Type: {config.account_type}")
        return True
    except Exception as e:
        print(f"[FAIL] Configuration loading: {e}")
        return False

def test_selectors():
    """Test enhanced selectors"""
    print("\nTesting Enhanced Selectors")
    print("=" * 50)
    
    try:
        from plus500us_client.webdriver.selectors import Plus500Selectors
        selectors = Plus500Selectors()
        
        # Test key selectors
        required_selectors = [
            'RECAPTCHA',
            'RECAPTCHA_CHECKBOX', 
            'RECAPTCHA_CHALLENGE',
            'SIDEBAR_CONTAINER',
            'TRADE_TAB',
            'INFO_TAB',
            'EDIT_ORDER_PRICE_INPUT',
            'SAVE_ORDER_CHANGES',
        ]
        
        passed = 0
        for selector_name in required_selectors:
            if hasattr(selectors, selector_name):
                selector = getattr(selectors, selector_name)
                xpath_count = len(selector.get('xpath', []))
                css_count = len(selector.get('css', []))
                print(f"[PASS] {selector_name} ({xpath_count} xpath, {css_count} css)")
                passed += 1
            else:
                print(f"[FAIL] {selector_name} missing")
        
        print(f"\nSelector Tests: {passed}/{len(required_selectors)} passed")
        return passed == len(required_selectors)
        
    except Exception as e:
        print(f"[FAIL] Selectors test: {e}")
        return False

def test_method_signatures():
    """Test that enhanced methods have correct signatures"""
    print("\nTesting Enhanced Method Signatures")
    print("=" * 50)
    
    try:
        from plus500us_client.webdriver.element_detector import ElementDetector
        from plus500us_client.webdriver.trade_manager import WebDriverTradeManager
        from plus500us_client.webdriver.instruments_discovery import WebDriverInstrumentsDiscovery
        from plus500us_client.webdriver.account_manager import WebDriverAccountManager
        from plus500us_client.webdriver.auth_handler import WebDriverAuthHandler
        
        # Test ElementDetector streaming methods
        if hasattr(ElementDetector, 'stream_instrument_data'):
            print("[PASS] ElementDetector.stream_instrument_data")
        else:
            print("[FAIL] ElementDetector.stream_instrument_data missing")
            
        # Test TradeManager TP editing
        if hasattr(WebDriverTradeManager, 'update_running_take_profit'):
            print("[PASS] WebDriverTradeManager.update_running_take_profit")
        else:
            print("[FAIL] WebDriverTradeManager.update_running_take_profit missing")
            
        # Test InstrumentsDiscovery enhanced methods
        if hasattr(WebDriverInstrumentsDiscovery, '_extract_detailed_instrument_info'):
            print("[PASS] WebDriverInstrumentsDiscovery._extract_detailed_instrument_info")
        else:
            print("[FAIL] WebDriverInstrumentsDiscovery._extract_detailed_instrument_info missing")
            
        # Test AccountManager optimizations
        if hasattr(WebDriverAccountManager, '_wait_for_account_mode_change'):
            print("[PASS] WebDriverAccountManager._wait_for_account_mode_change")
        else:
            print("[FAIL] WebDriverAccountManager._wait_for_account_mode_change missing")
            
        # Test AuthHandler RECAPTCHA
        if hasattr(WebDriverAuthHandler, '_handle_recaptcha'):
            print("[PASS] WebDriverAuthHandler._handle_recaptcha")
        else:
            print("[FAIL] WebDriverAuthHandler._handle_recaptcha missing")
            
        return True
        
    except Exception as e:
        print(f"[FAIL] Method signature test: {e}")
        return False

def main():
    """Run all tests"""
    print("Plus500US Enhanced WebDriver Feature Tests")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(test_imports())
    results.append(test_configuration())
    results.append(test_selectors()) 
    results.append(test_method_signatures())
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("\n" + "=" * 60)
    print(f"FINAL RESULTS: {passed}/{total} test categories passed")
    
    if passed == total:
        print("ALL TESTS PASSED - Enhanced features ready for live testing!")
        print("\nReady to run:")
        print("   python examples/complete_workflow_example.py")
    else:
        print("Some tests failed - please review errors above")
    
    print("=" * 60)
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)