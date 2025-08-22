#!/usr/bin/env python3
"""
Comprehensive WebDriver Analysis Example for Plus500US

This example demonstrates the complete WebDriver functionality including:
- Account type detection and switching
- Enhanced account balance extraction
- Instruments discovery by category
- PnL analysis with win/loss breakdown
- Trade management with running take profit updates

Usage:
    python examples/webdriver_comprehensive_analysis.py
"""

from __future__ import annotations
import time
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Any

from plus500us_client.config import Config
from plus500us_client.session import SessionManager
from plus500us_client.webdriver import (
    WebDriverSessionIntegrator,
    BrowserManager
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main demonstration of WebDriver functionality"""
    
    print("🚀 Plus500US WebDriver Comprehensive Analysis")
    print("=" * 60)
    
    # Initialize configuration and session
    cfg = Config()
    sm = SessionManager(cfg)
    
    # Configure browser for WebDriver
    browser_config = {
        'browser': 'firefox',
        'headless': False,  # Keep visible for demonstration
        'stealth_mode': True,
        'window_size': (1920, 1080),
        'implicit_wait': 10,
        'page_load_timeout': 60
    }
    
    browser_manager = BrowserManager(browser_config)
    
    try:
        # Initialize the WebDriver session integrator
        integrator = WebDriverSessionIntegrator(cfg, sm, browser_manager)
        
        # Start browser and initialize
        driver = browser_manager.start_browser()
        integrator.initialize(driver)
        
        print("✅ WebDriver session integrator initialized")
        
        # Step 1: Manual login (user needs to complete login)
        print("\n📋 MANUAL LOGIN REQUIRED")
        print("Please complete login in the browser window that opened")
        print("The analysis will continue automatically after login...")
        
        # Wait for user to complete login
        input("Press Enter after you have completed login and are on the trading page...")
        
        # Step 2: Account Type Detection and Management
        print("\n🏦 ACCOUNT TYPE ANALYSIS")
        print("-" * 30)
        
        current_account_type = integrator.account_manager.detect_current_account_type()
        print(f"Current Account Type: {current_account_type.upper()}")
        
        # Get enhanced account information
        enhanced_account = integrator.get_enhanced_account_info()
        print(f"Account Balance: ${enhanced_account.balance:,.2f}")
        print(f"Available Funds: ${enhanced_account.available:,.2f}")
        print(f"Margin Used: ${enhanced_account.margin_used:,.2f}")
        
        if hasattr(enhanced_account, 'total_pnl') and enhanced_account.total_pnl:
            print(f"Total P&L: ${enhanced_account.total_pnl:,.2f}")
        
        # Demonstrate account switching (be careful in live accounts)
        print(f"\n🔄 Account Switching Demonstration")
        if current_account_type == 'live':
            print("⚠️  Currently on LIVE account - skipping switch demo for safety")
        else:
            print("Attempting to switch account types...")
            target_type = 'live' if current_account_type == 'demo' else 'demo'
            print(f"Switching from {current_account_type} to {target_type}...")
            
            switch_success = integrator.switch_account_type(target_type)
            if switch_success:
                print(f"✅ Successfully switched to {target_type} account")
                
                # Switch back
                time.sleep(2)
                switch_back = integrator.switch_account_type(current_account_type)
                if switch_back:
                    print(f"✅ Successfully switched back to {current_account_type} account")
            else:
                print("❌ Account switch failed or not available")
        
        # Step 3: Instruments Discovery
        print("\n📊 INSTRUMENTS DISCOVERY BY CATEGORY")
        print("-" * 40)
        
        print("Discovering all available instruments by category...")
        all_instruments = integrator.discover_all_instruments()
        
        print(f"\nDiscovered instruments in {len(all_instruments)} categories:")
        for category, instruments in all_instruments.items():
            print(f"  📁 {category}: {len(instruments)} instruments")
            
            # Show first few instruments as examples
            for i, instrument in enumerate(instruments[:3]):
                name = instrument.get('name', 'Unknown')
                bid = instrument.get('bid')
                ask = instrument.get('ask')
                if bid and ask:
                    print(f"    • {name}: Bid ${bid} / Ask ${ask}")
                else:
                    print(f"    • {name}: Market closed")
                    
            if len(instruments) > 3:
                print(f"    ... and {len(instruments) - 3} more")
            print()
        
        # Step 4: Detailed Category Analysis
        print("\n🔍 DETAILED CATEGORY ANALYSIS")
        print("-" * 35)
        
        # Analyze a specific category in detail
        if 'Crypto' in all_instruments:
            crypto_instruments = all_instruments['Crypto']
            print(f"Analyzing {len(crypto_instruments)} crypto instruments:")
            
            for instrument in crypto_instruments:
                name = instrument.get('name', 'Unknown')
                change_pct = instrument.get('change_pct')
                market_closed = instrument.get('market_closed', False)
                
                status = "🌙 Closed" if market_closed else "🟢 Open"
                change_str = f"{change_pct:+.2f}%" if change_pct else "N/A"
                
                print(f"  • {name}: {change_str} {status}")
        
        # Step 5: PnL Analysis
        print("\n💰 P&L ANALYSIS")
        print("-" * 20)
        
        print("Analyzing today's trading performance...")
        daily_pnl = integrator.analyze_daily_pnl()
        
        print(f"\n📈 Daily P&L Summary for {daily_pnl.get('target_date', 'today')}:")
        print(f"  Net P&L: ${daily_pnl.get('net_pnl', 0):,.2f}")
        print(f"  Total Trades: {daily_pnl.get('total_trades', 0)}")
        print(f"  Winning Trades: {daily_pnl.get('winning_trades', 0)}")
        print(f"  Losing Trades: {daily_pnl.get('losing_trades', 0)}")
        
        if daily_pnl.get('total_trades', 0) > 0:
            win_rate = daily_pnl.get('win_rate', 0)
            avg_win = daily_pnl.get('avg_win', 0)
            avg_loss = daily_pnl.get('avg_loss', 0)
            
            print(f"  Win Rate: {win_rate:.1f}%")
            print(f"  Average Win: ${avg_win:,.2f}")
            print(f"  Average Loss: ${avg_loss:,.2f}")
            
            if daily_pnl.get('win_loss_ratio'):
                print(f"  Win/Loss Ratio: {daily_pnl.get('win_loss_ratio'):.2f}")
        
        # Step 6: Recent Trades Analysis
        print("\n📋 RECENT TRADES ANALYSIS")
        print("-" * 30)
        
        print("Retrieving recent closed trades...")
        recent_trades = integrator.pnl_analyzer.get_recent_trades(limit=10)
        
        if recent_trades:
            print(f"\nLast {len(recent_trades)} trades:")
            for i, trade in enumerate(recent_trades[:5]):  # Show first 5
                datetime_str = trade.get('datetime', 'Unknown time')
                action = trade.get('action', 'N/A')
                instrument = trade.get('instrument', 'Unknown')
                pnl = trade.get('pnl', Decimal('0'))
                pnl_indicator = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
                
                print(f"  {i+1}. {datetime_str} | {action} {instrument} | {pnl_indicator} ${pnl:,.2f}")
        else:
            print("No recent trades found")
        
        # Step 7: Instrument Performance Analysis
        print("\n🎯 INSTRUMENT PERFORMANCE ANALYSIS")
        print("-" * 40)
        
        print("Analyzing performance by instrument...")
        instrument_performance = integrator.pnl_analyzer.analyze_instrument_performance()
        
        instrument_stats = instrument_performance.get('instrument_stats', {})
        if instrument_stats:
            print(f"\nPerformance summary for {len(instrument_stats)} instruments:")
            
            # Show top 5 performers
            sorted_instruments = list(instrument_stats.items())[:5]
            for instrument, stats in sorted_instruments:
                total_pnl = stats.get('total_pnl', Decimal('0'))
                win_rate = stats.get('win_rate', 0)
                total_trades = len(stats.get('trades', []))
                
                pnl_indicator = "🟢" if total_pnl > 0 else "🔴" if total_pnl < 0 else "⚪"
                
                print(f"  • {instrument}: {pnl_indicator} ${total_pnl:,.2f} | {win_rate:.1f}% win rate | {total_trades} trades")
        
        # Step 8: Position Management Demonstration
        print("\n🎮 POSITION MANAGEMENT")
        print("-" * 25)
        
        print("Checking current positions...")
        current_positions = integrator.get_positions_with_enhanced_data()
        
        if current_positions:
            print(f"Found {len(current_positions)} open positions:")
            
            for position in current_positions:
                instrument = position.get('instrument_id', 'Unknown')
                side = position.get('side', 'N/A')
                quantity = position.get('quantity', 0)
                unrealized_pnl = position.get('unrealized_pnl', Decimal('0'))
                
                pnl_indicator = "🟢" if unrealized_pnl > 0 else "🔴" if unrealized_pnl < 0 else "⚪"
                
                print(f"  • {side} {quantity} {instrument} | {pnl_indicator} ${unrealized_pnl:,.2f}")
            
            # Demonstrate running take profit management (on first position)
            if len(current_positions) > 0:
                demo_position = current_positions[0]
                position_id = demo_position.get('id')
                
                print(f"\n🎯 Running Take Profit Demo (Position: {position_id})")
                print("Note: This is a demonstration - no actual orders will be placed")
                
                # Example TP update (would normally use real price calculation)
                # new_tp_price = Decimal('1000.00')  # Example price
                # success = integrator.update_running_take_profit(position_id, new_tp_price)
                # print(f"TP Update Result: {'✅ Success' if success else '❌ Failed'}")
                
                print("(Skipping actual TP update for safety in demo)")
        else:
            print("No open positions found")
        
        # Step 9: Session State Summary
        print("\n📊 SESSION STATE SUMMARY")
        print("-" * 30)
        
        print("Session Integration Status:")
        print(f"  Account Type: {current_account_type}")
        print(f"  WebDriver Status: {'✅ Active' if integrator._initialized else '❌ Inactive'}")
        print(f"  Categories Discovered: {len(all_instruments)}")
        print(f"  Total Instruments: {sum(len(instruments) for instruments in all_instruments.values())}")
        print(f"  Recent Trades Analyzed: {len(recent_trades)}")
        print(f"  Current Positions: {len(current_positions)}")
        
        # Final sync
        print("\n🔄 Final session state synchronization...")
        sync_success = integrator.sync_session_state()
        print(f"Session Sync: {'✅ Success' if sync_success else '❌ Failed'}")
        
        print("\n🎉 Comprehensive WebDriver analysis complete!")
        print("=" * 60)
        
        # Keep browser open for user inspection
        print("\nBrowser will remain open for inspection.")
        print("Close the browser window or press Ctrl+C to exit.")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Shutting down...")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        print(f"\n❌ Analysis failed: {e}")
        
    finally:
        # Clean shutdown
        if browser_manager:
            browser_manager.stop_browser()
        print("Browser closed. Analysis complete.")

if __name__ == "__main__":
    main()