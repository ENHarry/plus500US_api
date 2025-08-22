#!/usr/bin/env python3
"""
WebDriver Account Management Example for Plus500US

This example demonstrates account management functionality including:
- Account type detection (Demo vs Real)
- Account switching
- Enhanced balance extraction
- Real-time balance monitoring

Usage:
    python examples/webdriver_account_management.py
"""

from __future__ import annotations
import time
import logging
from decimal import Decimal

from plus500us_client.config import Config
from plus500us_client.session import SessionManager
from plus500us_client.webdriver import (
    WebDriverAccountManager,
    BrowserManager
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def balance_change_callback(changes: dict, current_data: dict):
    """Callback function for balance changes"""
    print(f"\n💰 Balance Change Detected at {time.strftime('%H:%M:%S')}:")
    
    for field, change_data in changes.items():
        old_value = change_data['old']
        new_value = change_data['new']
        change_amount = change_data['change']
        
        direction = "📈" if change_amount > 0 else "📉"
        print(f"  {direction} {field}: ${old_value:,.2f} → ${new_value:,.2f} (${change_amount:+,.2f})")

def main():
    """Main account management demonstration"""
    
    print("🏦 Plus500US WebDriver Account Management")
    print("=" * 50)
    
    # Initialize configuration and session
    cfg = Config()
    sm = SessionManager(cfg)
    
    # Configure browser for WebDriver
    browser_config = {
        'browser': 'firefox',
        'headless': False,  # Keep visible for demo
        'stealth_mode': True,
        'window_size': (1920, 1080),
        'implicit_wait': 10,
        'page_load_timeout': 60
    }
    
    browser_manager = BrowserManager(browser_config)
    
    try:
        # Initialize account manager
        account_manager = WebDriverAccountManager(cfg, browser_manager)
        
        # Start browser and initialize
        driver = browser_manager.start_browser()
        account_manager.initialize(driver)
        
        print("✅ WebDriver account manager initialized")
        
        # Manual login step
        print("\n📋 MANUAL LOGIN REQUIRED")
        print("Please complete login in the browser window")
        input("Press Enter after login is complete and you're on the trading page...")
        
        # Step 1: Account Type Detection
        print("\n🔍 ACCOUNT TYPE DETECTION")
        print("-" * 30)
        
        current_account_type = account_manager.detect_current_account_type()
        print(f"Detected Account Type: {current_account_type.upper()}")
        
        # Step 2: Extract Account Balance Data
        print("\n💰 ACCOUNT BALANCE EXTRACTION")
        print("-" * 35)
        
        balance_data = account_manager.extract_account_balance_data()
        
        print("Account Balance Summary:")
        print(f"  Account Type: {balance_data.get('account_type', 'Unknown')}")
        
        if balance_data.get('equity'):
            print(f"  💎 Total Equity: ${balance_data['equity']:,.2f}")
        
        if balance_data.get('total_pnl') is not None:
            pnl = balance_data['total_pnl']
            pnl_indicator = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
            print(f"  📊 Total P&L: {pnl_indicator} ${pnl:,.2f}")
        
        if balance_data.get('live_margin_available'):
            print(f"  🎯 Available Live Margin: ${balance_data['live_margin_available']:,.2f}")
        
        if balance_data.get('full_margin_available'):
            print(f"  🏦 Available Full Margin: ${balance_data['full_margin_available']:,.2f}")
        
        if balance_data.get('margin_used'):
            print(f"  📋 Margin Used: ${balance_data['margin_used']:,.2f}")
        
        # Step 3: Enhanced Account Information
        print("\n🌟 ENHANCED ACCOUNT INFORMATION")
        print("-" * 40)
        
        enhanced_account = account_manager.get_enhanced_account_info()
        
        print("Enhanced Account Details:")
        print(f"  Account ID: {enhanced_account.account_id}")
        print(f"  Account Type: {enhanced_account.account_type}")
        print(f"  Currency: {enhanced_account.currency}")
        print(f"  Balance: ${enhanced_account.balance:,.2f}")
        print(f"  Available: ${enhanced_account.available:,.2f}")
        print(f"  Margin Used: ${enhanced_account.margin_used:,.2f}")
        
        if enhanced_account.equity:
            print(f"  Equity: ${enhanced_account.equity:,.2f}")
        
        if enhanced_account.pnl:
            pnl_indicator = "🟢" if enhanced_account.pnl > 0 else "🔴" if enhanced_account.pnl < 0 else "⚪"
            print(f"  P&L: {pnl_indicator} ${enhanced_account.pnl:,.2f}")
        
        # Step 4: Account Switching Demonstration
        print("\n🔄 ACCOUNT SWITCHING DEMONSTRATION")
        print("-" * 40)
        
        if current_account_type == 'live':
            print("⚠️  WARNING: Currently on LIVE account")
            print("Account switching demo will be skipped for safety")
            print("To test switching, please start with a Demo account")
        else:
            print("Demonstrating account type switching...")
            
            # Test switching to the opposite account type
            target_type = 'live' if current_account_type == 'demo' else 'demo'
            
            print(f"Attempting to switch from {current_account_type} to {target_type}...")
            
            switch_success = account_manager.switch_account_type(target_type)
            
            if switch_success:
                print(f"✅ Successfully switched to {target_type} account")
                
                # Verify the switch
                new_account_type = account_manager.detect_current_account_type()
                print(f"Verified: Now on {new_account_type} account")
                
                # Wait a moment then switch back
                print("Waiting 3 seconds before switching back...")
                time.sleep(3)
                
                print(f"Switching back to {current_account_type} account...")
                switch_back_success = account_manager.switch_account_type(current_account_type)
                
                if switch_back_success:
                    final_account_type = account_manager.detect_current_account_type()
                    print(f"✅ Successfully switched back to {final_account_type} account")
                else:
                    print("❌ Failed to switch back")
            else:
                print("❌ Account switch failed or not available")
        
        # Step 5: Real-time Balance Monitoring
        print("\n📈 REAL-TIME BALANCE MONITORING")
        print("-" * 35)
        
        print("Starting real-time balance monitoring...")
        print("This will monitor for balance changes every 10 seconds")
        print("Press Ctrl+C to stop monitoring")
        print()
        
        try:
            # Monitor for 60 seconds or until interrupted
            monitoring_start = time.time()
            monitoring_duration = 60  # 1 minute
            
            last_balance_data = None
            
            while time.time() - monitoring_start < monitoring_duration:
                current_balance_data = account_manager.extract_account_balance_data()
                
                if last_balance_data is not None:
                    # Check for changes
                    changes = account_manager._detect_balance_changes(last_balance_data, current_balance_data)
                    
                    if changes:
                        balance_change_callback(changes, current_balance_data)
                    else:
                        # Show current status without changes
                        current_time = time.strftime('%H:%M:%S')
                        equity = current_balance_data.get('equity', Decimal('0'))
                        pnl = current_balance_data.get('total_pnl', Decimal('0'))
                        print(f"⏰ {current_time} | Equity: ${equity:,.2f} | P&L: ${pnl:+.2f}")
                
                last_balance_data = current_balance_data
                time.sleep(10)  # Check every 10 seconds
            
            print(f"\n✅ Monitoring completed ({monitoring_duration} seconds)")
            
        except KeyboardInterrupt:
            print("\n⏹️  Monitoring stopped by user")
        
        # Step 6: Final Account Summary
        print("\n📊 FINAL ACCOUNT SUMMARY")
        print("-" * 30)
        
        final_balance = account_manager.extract_account_balance_data()
        final_account_type = account_manager.detect_current_account_type()
        
        print("Final Account State:")
        print(f"  Account Type: {final_account_type}")
        print(f"  Equity: ${final_balance.get('equity', 0):,.2f}")
        print(f"  Available Margin: ${final_balance.get('live_margin_available', 0):,.2f}")
        
        if final_balance.get('total_pnl') is not None:
            pnl = final_balance['total_pnl']
            pnl_indicator = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
            print(f"  Total P&L: {pnl_indicator} ${pnl:,.2f}")
        
        print("\n🎉 Account management demonstration complete!")
        
        # Keep browser open for inspection
        print("\nBrowser will remain open for inspection.")
        print("Close the browser window or press Ctrl+C to exit.")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Shutting down...")
        
    except Exception as e:
        logger.error(f"Account management demo failed: {e}")
        print(f"\n❌ Demo failed: {e}")
        
    finally:
        # Clean shutdown
        if browser_manager:
            browser_manager.stop_browser()
        print("Browser closed. Demo complete.")

if __name__ == "__main__":
    main()