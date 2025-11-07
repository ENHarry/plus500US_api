"""
In this example, we demonstrate a complete workflow for trading on Plus500US using Selenium WebDriver.
The workflow includes authentication, market data retrieval, and trade execution.
"""
# Import necessary libraries
import os
import sys

# Fix encoding for Windows Unicode support
if os.name == 'nt':
    try:
        os.system('chcp 65001 > nul')
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from decimal import Decimal 
import time
from jqdatasdk import auth
from pathlib import Path
from plus500us_client import load_config
from plus500us_client.webdriver import (
    BrowserManager,
    WebDriverAuthHandler,
    WebDriverTradingClient,
    WebDriverTradeManager,
    WebDriverAccountManager,
    WebDriverInstrumentsDiscovery,
    auth_handler,
)
from plus500us_client.hybrid import SessionBridge, FallbackHandler
from plus500us_client.requests.errors import ValidationError, OrderRejectError

class UnifiedScreenshotMonitor:
    """Screenshot monitor using the same Selenium WebDriver"""
    
    def __init__(self, screenshots_dir: str = "workflow_screenshots"):
        self.screenshots_dir = Path(screenshots_dir)
        self.screenshots_dir.mkdir(exist_ok=True)
        self.driver = None
        
    def set_driver(self, driver):
        self.driver = driver
        
    def capture_screenshot(self, name: str, description: str = "") -> str:
        if not self.driver:
            return ""
        timestamp = int(time.time())
        filename = f"{timestamp}_{name}.png"
        filepath = self.screenshots_dir / filename
        try:
            self.driver.save_screenshot(str(filepath))
            print(f"   📸 Screenshot: {filename} - {description}")
            return str(filepath)
        except Exception as e:
            print(f"   ⚠️  Screenshot failed: {e}")
            return ""

def print_header(title):
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def print_step(step_num, description):
    print(f"\n📋 Step {step_num}: {description}")
    print("-" * 50)


def main():

    # Step 1: Configuration Setup
    print("=== Plus500US WebDriver Authentication Initiated ===")
    print()
     # Load configuration
    config = load_config()
    config.preferred_method = "webdriver"
    print(f"Base URL: {config.base_url}")
    print(f"Account Type: {config.account_type}")
    print()
    
     # Initialize single browser workflow
    browser_manager = None
    screenshot_monitor = UnifiedScreenshotMonitor()
    
    # Step 2: WebDriver Initialization
    
    print_step(1, "Single Browser Initialization")
    try:    
        user_browser = os.getenv("PLUS500_BROWSER", "firefox").lower()
        webdriver_config = {
            "browser": user_browser,
            "headless": False,
            "stealth_mode": True,
            "window_size": (1920, 1080),
            "implicit_wait": 10,
            "page_load_timeout": 30,
            "profile_path": "~/.plus500_demo_profile"
        }
         # Apply user browser preference to config
        config.webdriver_config.update(webdriver_config)
        
        # Initialize browser manager
        browser_manager = BrowserManager(config)
        print("✅ Browser manager initialized")
        print(f"   Selected Browser: {user_browser}")
        print(f"   Supported Browsers: chrome, firefox, edge")
    except Exception as e:
        print(f"   ⚠️  Browser initialization failed: {e}")

    try:    
        print_step(2, "User Authentication")
        auth_handler = WebDriverAuthHandler(config, webdriver_config)
        auth_handler.client_login()

    except Exception as e:
        print(f"   ⚠️  User authentication failed: {e}")

    print_step(3, "Switch to Demo Account")
    try:
        current_acc = auth_handler.account_manager.detect_current_account_type()
        print(f"   Current Account: {current_acc}")
        if current_acc != "demo":
            print("   🔄 Switching to Demo Account...")
            auth_handler.account_manager.switch_account_mode("demo")
            current_acc = auth_handler.account_manager.detect_current_account_type()
            print(f"   Switched Account: {current_acc}")
    except Exception as e:
        print(f"   ⚠️  Failed to switch accounts: {e}")
    
    print_step(4, "Get Account Balance")
    try:
        balance_info = auth_handler.account_manager.get_account_balance()
        print(f"   Account Balance: {balance_info}")
    except Exception as e:
        print(f"   ⚠️  Failed to get account balance: {e}")

    print_step(5, "Get List of Tradable Instruments")
    try:
        id = WebDriverInstrumentsDiscovery(config=config, browser_manager=browser_manager)
        id.initialize(auth_handler.driver)
        tradable_instruments = id.get_all_instruments()
        print(f"   Tradable Instruments: {tradable_instruments}")
    except Exception as e:
        print(f"   ⚠️  Failed to get tradable instruments: {e}")

    print_step(6, "Get Specific Instrument Details")
    try:
        instrument_details = id.get_instrument_details("MES")
        print(f"   Instrument Details: {instrument_details}")
    except Exception as e:
        print(f"   ⚠️  Failed to get instrument details: {e}")
    
    trading_client = WebDriverTradingClient(config=config, browser_manager=browser_manager)
    trading_client.initialize(auth_handler.driver)
    print_step(7, "Plus500US Navigation and Interface Demo")
        
    print("🧭 Demonstrating Plus500US-specific navigation...")
    try:
        # Test navigation to positions
        print("   📍 Testing Positions navigation...")
        trading_client._navigate_to_positions()
        print("   ✅ Successfully navigated to Positions tab")
        
        # Test navigation to orders
        print("   📍 Testing Orders navigation...")
        trading_client._navigate_to_orders()
        print("   ✅ Successfully navigated to Orders tab")
        
    except Exception as e:
        print(f"   ⚠️  Navigation test: {e}")
    
    print_step(8, "Enhanced Position Monitoring and Management")
    
    print("📊 Retrieving current positions...")
    try:
        positions = trading_client.get_positions()
        
        if positions:
            print(f"📋 Found {len(positions)} open positions:")
            for i, pos in enumerate(positions, 1):
                print(f"   Position {i}:")
                print(f"     ID: {pos.get('id', 'N/A')}")
                print(f"     Instrument: {pos.get('instrument', 'N/A')}")
                print(f"     Side: {pos.get('side', 'N/A')}")
                print(f"     Quantity: {pos.get('quantity', 'N/A')}")
                print(f"     P&L: {pos.get('pnl', 'N/A')}")
                print(f"     Current Price: {pos.get('current_price', 'N/A')}")
        else:
            print("ℹ️  No open positions found - this is expected for a fresh demo account")
            print("   We'll create some positions through live trading operations shortly...")
            
    except Exception as e:
        print(f"⚠️  Failed to retrieve positions: {e}")
        positions = []
    
    print_step(9, "Dynamic Trailing Stop Calculation Demo")
    
    print("🎯 Demonstrating Plus500US dynamic trailing stop functionality...")
    
    # Test trailing stop calculation for different instruments
    test_instruments = [
        {"id": "MESU5", "name": "Micro E-mini S&P 500", "price": Decimal("6434.0")},
        {"id": "GBPUSD", "name": "GBP/USD", "price": Decimal("1.2650")},
        {"id": "GOLD", "name": "Gold", "price": Decimal("2450.0")}
    ]
    
    print("\n📊 Trailing Stop Calculations by Instrument:")
    for instrument in test_instruments:
        try:
            # Calculate trailing stop for each instrument
            trailing_amount = trading_client.calculate_trailing_stop_amount(
                instrument["id"], instrument["price"]
            )
            percentage = (trailing_amount / instrument["price"]) * 100
            
            print(f"   {instrument['name']} (${instrument['price']}):")
            print(f"     Trailing Stop: ${trailing_amount}")
            print(f"     Percentage: {percentage:.2f}%")
            print(f"     Price Difference: {trailing_amount}")
            
        except Exception as e:
            print(f"     ❌ Calculation failed: {e}")
    
    # Demonstrate current price detection
    print("\n💰 Current Price Detection Demo:")
    try:
        current_price = trading_client.get_current_instrument_price()
        if current_price:
            print(f"   Detected Current Price: ${current_price}")
            # Calculate trailing stop for detected price
            auto_trailing = trading_client.calculate_trailing_stop_amount("AUTO", current_price)
            print(f"   Auto-Calculated Trailing Stop: ${auto_trailing}")
        else:
            print("   No current price detected (expected in positions view)")
            
    except Exception as e:
        print(f"   Price detection: {e}")
    
    print_step(10, "Live Demo Trading Operations")
    
    print("📈 Executing real trading operations on demo account...")
    
    # Demo 1: Place a Market Order with Risk Management
    print("\n🎯 Demo 1: Market Order with Stop Loss and Take Profit")
    
    # Get current market price first
    print("   📊 Getting current market price...")
    try:
        current_price = trading_client.get_current_instrument_price()
        if current_price:
            print(f"   Current Price: ${current_price}")
            
            # Calculate risk management levels
            instrument = "MESU5"  # Micro E-mini S&P 500
            quantity = Decimal("1")
            side = "BUY"
            
            # Calculate stop loss (1% below current price for BUY)
            stop_loss = current_price * Decimal("0.99")
            # Calculate take profit (2% above current price for BUY)  
            take_profit = current_price * Decimal("1.02")
            
            print(f"   Order Details:")
            print(f"     Instrument: {instrument}")
            print(f"     Side: {side}")
            print(f"     Quantity: {quantity}")
            print(f"     Current Price: ${current_price}")
            print(f"     Stop Loss: ${stop_loss:.2f} (1% risk)")
            print(f"     Take Profit: ${take_profit:.2f} (2% target)")
            
            print("   🔄 Placing live market order...")
            try:
                result = trading_client.place_market_order(
                    instrument_id=instrument,
                    side=side,
                    quantity=quantity,
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
                
                if result.get('success'):
                    print("   ✅ Market order placed successfully!")
                    print(f"   📝 Order ID: {result.get('order_id', 'Unknown')}")
                    print("   🎯 Stop loss and take profit set")
                else:
                    print(f"   ❌ Order failed: {result.get('error', 'Unknown error')}")
                    
            except OrderRejectError as e:
                print(f"   ❌ Order rejected: {e}")
            except Exception as e:
                print(f"   ⚠️  Order placement error: {e}")
                
        else:
            print("   ⚠️  Could not get current price - skipping market order demo")
            
    except Exception as e:
        print(f"   ⚠️  Price detection error: {e}")
    
    # Demo 2: Place a Limit Order and Manage It
    print("\n🎯 Demo 2: Limit Order Placement and Management")
    
    # First place a limit order
    print("   📊 Placing a limit order...")
    try:
        current_price = trading_client.get_current_instrument_price()
        if current_price:
            # Place a limit order 1% above current price for a BUY order
            limit_price = current_price * Decimal("1.01")
            
            print(f"   Limit Order Details:")
            print(f"     Instrument: MESU5")
            print(f"     Side: BUY")
            print(f"     Quantity: 1")
            print(f"     Current Price: ${current_price}")
            print(f"     Limit Price: ${limit_price:.2f} (1% above market)")
            
            limit_result = trading_client.place_limit_order(
                instrument_id="MESU5",
                side="BUY",
                quantity=Decimal("1"),
                limit_price=limit_price
            )
            
            if limit_result.get('success'):
                print("   ✅ Limit order placed successfully!")
                print(f"   📝 Order ID: {limit_result.get('order_id', 'Unknown')}")
                
                # Small delay to allow order to appear in system
                time.sleep(2)
                
            else:
                print(f"   ❌ Limit order failed: {limit_result.get('error', 'Unknown error')}")
                
        else:
            print("   ⚠️  Could not get current price for limit order")
            
    except Exception as e:
        print(f"   ⚠️  Limit order error: {e}")
    
    # Now retrieve and manage orders
    print("\n📋 Retrieving current pending orders...")
    try:
        orders = trading_client.get_orders()
        
        if orders:
            print(f"📋 Found {len(orders)} pending orders:")
            for i, order in enumerate(orders, 1):
                print(f"   Order {i}:")
                print(f"     ID: {order.get('id', 'N/A')}")
                print(f"     Instrument: {order.get('instrument', 'N/A')}")
                print(f"     Side: {order.get('side', 'N/A')}")
                print(f"     Quantity: {order.get('quantity', 'N/A')}")
                print(f"     Type: {order.get('order_type', 'N/A')}")
                print(f"     Price: {order.get('price', 'N/A')}")
                
            # Demonstrate order management operations on the first order
            if len(orders) > 0:
                target_order = orders[0]
                order_id = target_order.get('id')
                
                print(f"\n🔧 Order Management Demo with {target_order.get('instrument')}:")
                print(f"   Target Order: {order_id}")
                
                # Demo order cancellation
                print("   🗑️  Cancelling order...")
                try:
                    cancel_result = trading_client.cancel_order(order_id)
                    if cancel_result:
                        print("   ✅ Order cancelled successfully")
                    else:
                        print("   ❌ Order cancellation failed")
                except Exception as e:
                    print(f"   ⚠️  Order cancellation error: {e}")
                    
        else:
            print("ℹ️  No pending orders found")
            print("   This is normal if orders were just placed and immediately filled")
            
    except Exception as e:
        print(f"⚠️  Failed to retrieve orders: {e}")
    
    # Demo 3: Monitor Created Positions
    print("\n🎯 Demo 3: Position Monitoring and Management")
    
    print("📊 Checking for positions created by our trading operations...")
    try:
        # Refresh positions after our trading operations
        current_positions = trading_client.get_positions()
        
        if current_positions:
            print(f"📋 Found {len(current_positions)} open positions:")
            for i, pos in enumerate(current_positions, 1):
                print(f"   Position {i}:")
                print(f"     ID: {pos.get('id', 'N/A')}")
                print(f"     Instrument: {pos.get('instrument', 'N/A')}")
                print(f"     Side: {pos.get('side', 'N/A')}")
                print(f"     Quantity: {pos.get('quantity', 'N/A')}")
                print(f"     P&L: {pos.get('pnl', 'N/A')}")
                print(f"     Current Price: {pos.get('current_price', 'N/A')}")
            
            # Demonstrate position management
            if len(current_positions) > 0:
                demo_position = current_positions[0]
                position_id = demo_position.get('id')
                
                print(f"\n🔧 Position Management Demo:")
                print(f"   Target Position: {position_id}")
                print(f"   Current P&L: {demo_position.get('pnl', 'N/A')}")
                
                # Demo position closure (optional - comment out to keep positions)
                # print("   🗑️  Closing position...")
                # try:
                #     close_result = trading_client.close_position(position_id)
                #     if close_result:
                #         print("   ✅ Position closed successfully")
                #     else:
                #         print("   ❌ Position closure failed")
                # except Exception as e:
                #     print(f"   ⚠️  Position closure error: {e}")
                
                print("   ℹ️  Position kept open for monitoring (uncomment closure code if needed)")
                
        else:
            print("ℹ️  No positions found after trading operations")
            print("   This may be due to orders not being filled or market conditions")
            
    except Exception as e:
        print(f"⚠️  Failed to retrieve updated positions: {e}")
    
    print_step(11, "Live Risk Management and Account Status")
    
    # Get current account status and real risk information
    print("📊 Live Account Status and Risk Assessment...")
    
    try:
        # Get updated positions for risk management
        live_positions = trading_client.get_positions()
        live_orders = trading_client.get_orders()
        
        print(f"   💼 Account Summary:")
        print(f"     Open Positions: {len(live_positions)}")
        print(f"     Pending Orders: {len(live_orders)}")
        
        # Calculate total exposure and P&L
        total_pnl = Decimal("0")
        total_exposure = 0
        
        for pos in live_positions:
            try:
                pnl_str = pos.get('pnl', '0')
                # Clean P&L string (remove currency symbols, commas)
                pnl_clean = ''.join(filter(lambda x: x.isdigit() or x in '.-+', pnl_str))
                if pnl_clean:
                    total_pnl += Decimal(pnl_clean)
                total_exposure += 1
            except (ValueError, TypeError):
                pass
        
        print(f"     Total P&L: ${total_pnl}")
        print(f"     Total Exposure: {total_exposure} positions")
        
        # Demonstrate risk management on actual positions
        if live_positions:
            print(f"\n🛡️  Risk Management on Live Positions:")
            
            for i, pos in enumerate(live_positions[:2], 1):  # Show first 2 positions
                print(f"   Position {i}: {pos.get('instrument', 'N/A')}")
                print(f"     Side: {pos.get('side', 'N/A')}")
                print(f"     Quantity: {pos.get('quantity', 'N/A')}")
                print(f"     Current P&L: {pos.get('pnl', 'N/A')}")
                
                # Calculate recommended stop loss
                try:
                    current_price = trading_client.get_current_instrument_price()
                    if current_price:
                        side = pos.get('side', 'BUY')
                        if side == 'BUY':
                            recommended_sl = current_price * Decimal("0.98")  # 2% stop loss
                            print(f"     Recommended Stop Loss: ${recommended_sl:.2f} (2% risk)")
                        else:
                            recommended_sl = current_price * Decimal("1.02")  # 2% stop loss
                            print(f"     Recommended Stop Loss: ${recommended_sl:.2f} (2% risk)")
                except Exception:
                    print(f"     Could not calculate recommended stop loss")
                    
        else:
            print("\n🛡️  No open positions to manage")
            print("   Risk management recommendations:")
            print("   - Always set stop losses when opening positions")
            print("   - Use trailing stops for profitable trades")
            print("   - Monitor P&L regularly during market hours")
            
    except Exception as e:
        print(f"⚠️  Failed to get live account status: {e}")
    
    # Demonstrate invalid partial take profit
    print("\n⚠️  Testing Invalid Partial Take Profit (Safety Demo)")
    invalid_position = {
        "id": "UNSAFE_POSITION",
        "quantity": "1",  # Only 1 contract - unsafe for partial TP
        "instrument": "EURUSD"
    }
    
    print(f"   Position: {invalid_position['id']}")
    print(f"   Current Quantity: {invalid_position['quantity']} contract")
    print(f"   Attempted Partial Close: 0.5 contracts")
    
    try:
        # This should trigger the validation error
        if Decimal(invalid_position['quantity']) <= Decimal("1"):
            raise ValidationError("CRITICAL: Partial take profit requires position > 1 contract")
        
    except ValidationError as e:
        print(f"   🛡️  SAFEGUARD PREVENTED DANGEROUS OPERATION: {e}")
        print("   ✅ Position integrity protected")
    
    print_step(12, "System Health and Monitoring")
    
    # Initialize fallback handler for health monitoring
    fallback_handler = FallbackHandler(config)
    
    print("🏥 System Health Check:")
    health = fallback_handler.health_check()
    
    print(f"   Overall Status: {health['overall_status']}")
    for method, status in health['methods'].items():
        print(f"   {method.title()} Method: {status['status']}")
    
    if health['recommendations']:
        print("   📝 Recommendations:")
        for rec in health['recommendations']:
            print(f"     • {rec}")
    
    print_step(13, "Final Balance Verification and Session Cleanup")
    
    print("💰 Final account balance verification...")


if __name__ == "__main__":
    success = main()
    
    if success:
        print("✅ Trading workflow completed successfully.")
    else:
        print("❌ Trading workflow failed.")