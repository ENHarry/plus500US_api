"""
Quick timing test for key operations in the workflow
Tests individual components without full browser automation
"""
import time
import sys
import os
from datetime import datetime

# Fix encoding
if os.name == 'nt':
    try:
        os.system('chcp 65001 > nul')
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

sys.path.append('examples')

def time_operation(name, func, *args, **kwargs):
    """Time a single operation"""
    start = time.perf_counter()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting: {name}")
    
    try:
        result = func(*args, **kwargs)
        end = time.perf_counter()
        duration = end - start
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Completed: {name} in {duration:.3f}s")
        return result, duration
    except Exception as e:
        end = time.perf_counter()
        duration = end - start
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Failed: {name} after {duration:.3f}s - {e}")
        return None, duration

def main():
    print("="*70)
    print("QUICK TIMING TEST - KEY OPERATIONS")
    print(f"Started: {datetime.now().strftime('%H:%M:%S')}")
    print("="*70)
    
    timings = {}
    total_start = time.perf_counter()
    
    # Test 1: Configuration loading
    def load_config_test():
        from plus500us_client import load_config
        config = load_config()
        config.preferred_method = "webdriver"
        return config
    
    config, duration = time_operation("Configuration Loading", load_config_test)
    timings["config_load"] = duration
    
    if config:
        print(f"  - Base URL: {config.base_url}")
        print(f"  - Account Type: {config.account_type}")
    
    # Test 2: WebDriver imports
    def import_webdriver():
        from plus500us_client.webdriver import (
            BrowserManager,
            WebDriverAuthHandler,
            WebDriverTradingClient
        )
        return True
    
    _, duration = time_operation("WebDriver Module Imports", import_webdriver)
    timings["webdriver_imports"] = duration
    
    # Test 3: Browser manager initialization (without actual browser)
    def init_browser_manager():
        from plus500us_client.webdriver import BrowserManager
        webdriver_config = {
            "browser": "firefox",
            "headless": True,  # Use headless to avoid UI
            "stealth_mode": False,
            "window_size": (1920, 1080),
            "implicit_wait": 5,
            "page_load_timeout": 15
        }
        config.webdriver_config.update(webdriver_config)
        return BrowserManager(config)
    
    browser_mgr, duration = time_operation("Browser Manager Init", init_browser_manager)
    timings["browser_manager_init"] = duration
    
    # Test 4: Hybrid system imports
    def import_hybrid():
        from plus500us_client.hybrid import SessionBridge, FallbackHandler
        return FallbackHandler(config)
    
    fallback, duration = time_operation("Hybrid System Import", import_hybrid)
    timings["hybrid_imports"] = duration
    
    # Test 5: Health check (without actual connections)
    if fallback:
        def health_check():
            return fallback.health_check()
        
        health, duration = time_operation("System Health Check", health_check)
        timings["health_check"] = duration
        
        if health:
            print(f"  - Overall Status: {health.get('overall_status', 'Unknown')}")
            print(f"  - Methods Available: {len(health.get('methods', {}))}")
    
    # Test 6: Model imports and validation
    def test_models():
        from plus500us_client.models import Instrument, OrderDraft
        from decimal import Decimal
        
        # Create a test instrument
        instrument = Instrument(
            id="TEST",
            name="Test Instrument", 
            tick_size=Decimal("0.01"),
            min_qty=Decimal("1")
        )
        
        # Create a test order draft
        order = OrderDraft(
            instrument_id="TEST",
            side="BUY",
            quantity=Decimal("1"),
            order_type="MARKET"
        )
        
        return instrument, order
    
    models, duration = time_operation("Model Creation & Validation", test_models)
    timings["model_operations"] = duration
    
    # Test 7: Guards and validation
    def test_guards():
        from plus500us_client.guards import tick_round, ensure_qty_increment
        from decimal import Decimal
        
        price = Decimal("100.123")
        tick_size = Decimal("0.01") 
        rounded = tick_round(price, tick_size)
        
        qty = Decimal("0.5")
        min_qty = Decimal("1.0")
        validated = ensure_qty_increment(qty, min_qty)
        
        return rounded, validated
    
    guards_result, duration = time_operation("Guards & Validation", test_guards)
    timings["guards_validation"] = duration
    
    if guards_result:
        print(f"  - Price rounding: {guards_result[0]}")
        print(f"  - Quantity validation: {guards_result[1]}")
    
    total_end = time.perf_counter()
    total_duration = total_end - total_start
    
    print("\n" + "="*70)
    print("TIMING SUMMARY")
    print("="*70)
    
    for operation, duration in timings.items():
        percentage = (duration / total_duration) * 100
        print(f"{operation:25}: {duration:6.3f}s ({percentage:5.1f}%)")
    
    print("-" * 70)
    print(f"{'TOTAL':25}: {total_duration:6.3f}s (100.0%)")
    print(f"Completed: {datetime.now().strftime('%H:%M:%S')}")
    print("="*70)
    
    return True

if __name__ == "__main__":
    success = main()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")