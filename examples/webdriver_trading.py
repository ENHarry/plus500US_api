"""
WebDriver-powered trading automation example for Plus500US

This example demonstrates automated trading using WebDriver,
including order placement, position management, and risk management.
"""
import os
import sys
from pathlib import Path
from decimal import Decimal
import time

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from plus500us_client import load_config
from plus500us_client.webdriver import BrowserManager, WebDriverTradingClient
from plus500us_client.errors import OrderRejectError, ValidationError


def main():
    print("=== Plus500US WebDriver Trading Automation ===")
    print()
    
    # Load configuration
    config = load_config()
    
    # Ensure WebDriver is preferred method
    config.preferred_method = "webdriver"
    
    print(f"Account Type: {config.account_type}")
    print(f"Automation Method: {config.preferred_method}")
    print()
    
    # Initialize browser manager
    browser_manager = BrowserManager(config)
    
    try:
        # Initialize trading client
        print("🤖 Initializing WebDriver trading client...")
        trading_client = WebDriverTradingClient(config, browser_manager)
        trading_client.initialize()
        print("✅ Trading client initialized")
        print()
        
        # Note: In a real scenario, you would first authenticate
        print("⚠️  Note: This example assumes you're already authenticated")
        print("   Run webdriver_login.py first to authenticate")
        print()
        
        # Example 1: Place a market order
        print("📈 Example 1: Placing Market Order")
        print("   Instrument: EURUSD")
        print("   Side: BUY")
        print("   Quantity: 1 contract")
        print("   Stop Loss: 1.0950")
        print("   Take Profit: 1.1050")
        
        try:
            market_order_result = trading_client.place_market_order(
                instrument_id="EURUSD",
                side="BUY",
                quantity=Decimal("1"),
                stop_loss=Decimal("1.0950"),
                take_profit=Decimal("1.1050")
            )
            
            print(f"✅ Market order placed successfully!")
            print(f"   Order ID: {market_order_result.get('order_id', 'N/A')}")
            print(f"   Status: {market_order_result.get('message', 'Unknown')}")
            
        except OrderRejectError as e:
            print(f"❌ Market order rejected: {e}")
        except Exception as e:
            print(f"⚠️  Market order failed: {e}")
        
        print()
        
        # Example 2: Place a limit order
        print("📊 Example 2: Placing Limit Order")
        print("   Instrument: GBPUSD")
        print("   Side: SELL")
        print("   Quantity: 2 contracts")
        print("   Limit Price: 1.2600")
        print("   Stop Loss: 1.2650")
        
        try:
            limit_order_result = trading_client.place_limit_order(
                instrument_id="GBPUSD",
                side="SELL",
                quantity=Decimal("2"),
                limit_price=Decimal("1.2600"),
                stop_loss=Decimal("1.2650")
            )
            
            print(f"✅ Limit order placed successfully!")
            print(f"   Order ID: {limit_order_result.get('order_id', 'N/A')}")
            
        except OrderRejectError as e:
            print(f"❌ Limit order rejected: {e}")
        except Exception as e:
            print(f"⚠️  Limit order failed: {e}")
        
        print()
        
        # Example 3: Get current positions
        print("📋 Example 3: Retrieving Current Positions")
        
        try:
            positions = trading_client.get_positions()
            
            if positions:
                print(f"✅ Found {len(positions)} positions:")
                for i, position in enumerate(positions, 1):
                    print(f"   Position {i}:")
                    print(f"     ID: {position.get('id', 'N/A')}")
                    print(f"     Instrument: {position.get('instrument', 'N/A')}")
                    print(f"     Side: {position.get('side', 'N/A')}")
                    print(f"     Quantity: {position.get('quantity', 'N/A')}")
                    print(f"     P&L: {position.get('pnl', 'N/A')}")
            else:
                print("ℹ️  No open positions found")
                
        except Exception as e:
            print(f"⚠️  Failed to get positions: {e}")
        
        print()
        
        # Example 4: Risk management - Set stop loss
        print("🛡️  Example 4: Risk Management - Setting Stop Loss")
        
        # For demonstration, we'll use a mock position ID
        demo_position_id = "DEMO_POSITION_123"
        
        try:
            sl_result = trading_client.set_stop_loss(
                position_id=demo_position_id,
                stop_loss_price=Decimal("1.0980")
            )
            
            if sl_result:
                print(f"✅ Stop loss set successfully for position {demo_position_id}")
            else:
                print(f"❌ Failed to set stop loss for position {demo_position_id}")
                
        except Exception as e:
            print(f"⚠️  Stop loss operation failed: {e}")
        
        print()
        
        # Example 5: Partial take profit with validation
        print("💰 Example 5: Partial Take Profit (with critical validation)")
        print("   This demonstrates the critical safeguard for partial TP")
        
        # Mock position data for demonstration
        mock_positions = [
            {
                "id": "VALID_POSITION_456",
                "quantity": "5",  # 5 contracts - valid for partial TP
                "instrument": "EURUSD"
            },
            {
                "id": "INVALID_POSITION_789",
                "quantity": "1",  # Only 1 contract - invalid for partial TP
                "instrument": "GBPUSD"
            }
        ]
        
        # Mock the get_positions method
        trading_client.get_positions = lambda: mock_positions
        
        # Valid partial take profit
        print("\n   📊 Testing valid partial take profit:")
        print("     Position: 5 contracts")
        print("     Partial close: 2 contracts")
        print("     Remaining: 3 contracts ✅")
        
        try:
            trading_client.close_position = lambda pos_id, qty: True  # Mock successful close
            
            result = trading_client.execute_partial_take_profit(
                "VALID_POSITION_456", 
                Decimal("2")
            )
            
            if result:
                print("     ✅ Partial take profit executed successfully")
            
        except ValidationError as e:
            print(f"     ❌ Validation error: {e}")
        
        # Invalid partial take profit (position too small)
        print("\n   ⚠️  Testing invalid partial take profit:")
        print("     Position: 1 contract")
        print("     Partial close: 0.5 contracts")
        print("     CRITICAL SAFEGUARD SHOULD PREVENT THIS ❌")
        
        try:
            trading_client.execute_partial_take_profit(
                "INVALID_POSITION_789", 
                Decimal("0.5")
            )
            
        except ValidationError as e:
            print(f"     ✅ SAFEGUARD ACTIVATED: {e}")
        
        # Invalid partial take profit (leaves insufficient remaining)
        print("\n   ⚠️  Testing partial TP that leaves <1 contract:")
        print("     Position: 5 contracts")
        print("     Partial close: 4.5 contracts")
        print("     Remaining: 0.5 contracts ❌")
        
        try:
            trading_client.execute_partial_take_profit(
                "VALID_POSITION_456", 
                Decimal("4.5")
            )
            
        except ValidationError as e:
            print(f"     ✅ SAFEGUARD ACTIVATED: {e}")
        
        print()
        
        # Example 6: Real-time P&L monitoring
        print("📊 Example 6: Real-time P&L Monitoring")
        
        try:
            # Mock P&L monitoring
            pnl = trading_client.monitor_position_pnl("DEMO_POSITION_123")
            
            if pnl is not None:
                print(f"✅ Current P&L: ${pnl}")
            else:
                print("ℹ️  Position not found or P&L unavailable")
                
        except Exception as e:
            print(f"⚠️  P&L monitoring failed: {e}")
        
        print()
        print("🎯 WebDriver Trading Features Demonstrated:")
        print("   ✅ Market order placement with SL/TP")
        print("   ✅ Limit order placement")
        print("   ✅ Position retrieval and monitoring")
        print("   ✅ Risk management (stop loss/take profit)")
        print("   ✅ Critical partial TP validation safeguards")
        print("   ✅ Real-time P&L monitoring")
        print()
        print("🛡️  Safety Features:")
        print("   ✅ Partial TP requires position > 1 contract")
        print("   ✅ Remaining position must be ≥ 1 contract")
        print("   ✅ Order validation and error handling")
        print("   ✅ Anti-bot detection with stealth mode")
        
    except Exception as e:
        print(f"❌ Trading automation failed: {e}")
        print()
        print("💡 Troubleshooting:")
        print("   - Ensure you're authenticated (run webdriver_login.py)")
        print("   - Check Plus500 platform availability")
        print("   - Verify WebDriver setup is correct")
        
        return False
        
    finally:
        # Clean up browser resources
        print("\n🧹 Cleaning up browser resources...")
        browser_manager.cleanup()
        print("✅ Cleanup completed")
    
    return True


if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n🎉 WebDriver trading automation example completed!")
        print("\n📚 Key Takeaways:")
        print("   - WebDriver enables automated trading despite anti-bot protection")
        print("   - Critical safeguards prevent dangerous partial TP operations") 
        print("   - Comprehensive error handling ensures robust automation")
        print("   - DOM-based interactions provide reliable element detection")
    else:
        print("\n💥 WebDriver trading automation example failed!")
        sys.exit(1)