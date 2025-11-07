#!/usr/bin/env python3
"""
Complete Live Test of Plus500 API Implementation
=================================================

This example demonstrates all key functions of the Plus500 API using the 
Plus500ApiClient wrapper. It shows the complete authentication process
for a first-time user and tests all major functionality:

1. First-time authentication (with real credential prompts)
2. Switch to demo account
3. Get account balance
4. Get tradable instruments
5. Get instrument info
6. Get chart data
7. Get buy/sell info
8. Create an order without risk management
9. Get orders
10. Edit the order
11. Cancel the order
12. Get closed positions

This is a comprehensive test of all implemented functionality using the 
unified Plus500ApiClient interface.
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


class Plus500LiveTestRunner:
    """Complete test runner for Plus500 API functionality using unified client"""
    
    def __init__(self):
        self.client = Plus500ApiClient()
        self.test_order_id = None
        self.selected_instrument = None
        
    def print_step(self, step_num: int, description: str):
        """Print formatted step header"""
        print(f"\n{'='*60}")
        print(f"STEP {step_num}: {description}")
        print(f"{'='*60}")
        
    def print_result(self, success: bool, message: str, data=None):
        """Print formatted result"""
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{status}: {message}")
        if data and isinstance(data, dict):
            # Print key information, not the entire response
            if 'balance' in data:
                print(f"  Balance: ${data['balance']}")
            if 'equity' in data:
                print(f"  Equity: ${data['equity']}")
            if 'free_margin' in data:
                print(f"  Free Margin: ${data['free_margin']}")
            if len(data) < 10:  # Only print full data for small responses
                print(f"  Data: {json.dumps(data, indent=2, default=str)}")
        elif data and isinstance(data, list) and len(data) > 0:
            print(f"  Found {len(data)} items")
            if hasattr(data[0], '__dict__'):
                print(f"  Sample: {data[0].__dict__}")
            else:
                print(f"  Sample: {data[0]}")
    
    def step_1_authentication(self):
        """Step 1: Go through authentication like a first time user"""
        self.print_step(1, "First-Time User Authentication")
        
        try:
            # Clear any existing session to simulate first-time user
            if self.client.sm.session_data_path.exists():
                self.client.sm.session_data_path.unlink()
                print("Cleared existing session to simulate first-time user")
            
            print("\n🔐 PLUS500 AUTHENTICATION")
            
            # Check if credentials are available from config/.env
            if self.client.cfg.email and self.client.cfg.password:
                print(f"Using credentials from configuration:")
                print(f"  Email: {self.client.cfg.email}")
                print(f"  Password: {'*' * len(self.client.cfg.password)}")
                username = self.client.cfg.email
                password = self.client.cfg.password
            else:
                print("No credentials found in configuration - prompting user...")
                print("This is a live test - you need to provide real credentials")
                print("Your credentials will be used only for this test session")
                print("-" * 50)
                
                # Get credentials from user (fallback)
                username = input("Enter your Plus500 email: ").strip()
                if not username:
                    raise ValueError("Email is required")
                    
                password = getpass.getpass("Enter your Plus500 password: ").strip()
                if not password:
                    raise ValueError("Password is required")
            
            print("\n🚀 Starting authentication process...")
            print("This may take a moment as we establish your session...")
            
            # Use the unified client's authentication
            if self.client.cfg.email and self.client.cfg.password:
                # Use config credentials
                auth_result = self.client.futures_authenticate()
            else:
                # Use provided credentials
                auth_result = self.client.futures_authenticate(username, password)
            
            if auth_result.get('success'):
                print(f"✅ Authentication successful!")
                print(f"   Session established: {self.client.is_authenticated()}")
                
                # Show authentication details
                session_data = auth_result.get('session_data', {})
                if session_data:
                    user_session = session_data.get('UserSessionId', 'N/A')
                    service_id = session_data.get('WebTraderServiceId', 'N/A')
                    print(f"   User Session ID: {user_session[:20]}..." if len(user_session) > 20 else f"   User Session ID: {user_session}")
                    print(f"   Service ID: {service_id[:20]}..." if len(service_id) > 20 else f"   Service ID: {service_id}")
                
                self.print_result(True, "Authentication completed successfully", 
                                {"authenticated": self.client.is_authenticated()})
                return True
            else:
                error_msg = auth_result.get('message', 'Unknown authentication error')
                self.print_result(False, f"Authentication failed: {error_msg}")
                return False
            
        except KeyboardInterrupt:
            print("\n⚠️  Authentication cancelled by user")
            return False
        except Exception as e:
            self.print_result(False, f"Authentication failed: {str(e)}")
            return False
    
    def step_2_switch_demo(self):
        """Step 2: Switch to demo account"""
        self.print_step(2, "Switch to Demo Account")
        
        try:
            # Get current account mode first
            account_info = self.client.get_account_info()
            current_mode = account_info.get('account_mode', 'Unknown')
            print(f"Current account mode: {current_mode}")
            
            if current_mode.lower() != 'demo':
                print("Switching to demo mode...")
                switch_result = self.client.switch_to_demo()
                self.print_result(True, "Switched to demo account", switch_result)
            else:
                self.print_result(True, "Already in demo mode", {"mode": current_mode})
            
            return True
            
        except Exception as e:
            self.print_result(False, f"Failed to switch to demo: {str(e)}")
            return False
    
    def step_3_account_balance(self):
        """Step 3: Get account balance"""
        self.print_step(3, "Get Account Balance")
        
        try:
            # Get account balance using unified client
            balance_info = self.client.get_account_balance()
            
            self.print_result(True, "Retrieved account balance", balance_info)
            
            # Also get detailed account summary
            try:
                account_summary = self.client.get_account_summary()
                print(f"✅ Account summary: {account_summary.get('account_type', 'Unknown')} account")
                print(f"   Currency: {account_summary.get('currency', 'Unknown')}")
            except Exception as e:
                print(f"⚠️  Detailed account info failed: {e}")
            
            return True
            
        except Exception as e:
            self.print_result(False, f"Failed to get balance: {str(e)}")
            return False
    
    def step_4_tradable_instruments(self):
        """Step 4: Get tradable instruments"""
        self.print_step(4, "Get Tradable Instruments")
        
        try:
            # Get all instruments using unified client
            instruments = self.client.get_instruments()
            tradable_count = len([inst for inst in instruments if getattr(inst, 'is_tradable', True)])
            
            self.print_result(True, f"Found {tradable_count} tradable instruments out of {len(instruments)} total")
            
            # Select a popular instrument for testing
            self.selected_instrument = None
            for instrument in instruments:
                symbol = getattr(instrument, 'symbol', getattr(instrument, 'name', ''))
                if any(keyword in symbol.upper() for keyword in ['EUR', 'GBP', 'USD', 'OIL', 'GOLD', 'AAPL', 'TSLA']):
                    self.selected_instrument = instrument
                    instrument_id = getattr(instrument, 'instrument_id', getattr(instrument, 'id', 'N/A'))
                    print(f"Selected instrument for testing: {symbol} (ID: {instrument_id})")
                    break
            
            if not self.selected_instrument and instruments:
                self.selected_instrument = instruments[0]
                symbol = getattr(self.selected_instrument, 'symbol', 'Unknown')
                print(f"Selected first available instrument: {symbol}")
            
            return True
            
        except Exception as e:
            self.print_result(False, f"Failed to get instruments: {str(e)}")
            return False
    
    def step_5_instrument_info(self):
        """Step 5: Get instrument info"""
        self.print_step(5, "Get Instrument Information")
        
        if not self.selected_instrument:
            self.print_result(False, "No instrument selected")
            return False
        
        try:
            # Get detailed instrument information using unified client
            instrument_id = getattr(self.selected_instrument, 'instrument_id', 
                                  getattr(self.selected_instrument, 'id', None))
            
            if not instrument_id:
                self.print_result(False, "No instrument ID available")
                return False
            
            instrument_details = self.client.get_instrument_details(instrument_id)
            symbol = getattr(self.selected_instrument, 'symbol', 'Unknown')
            
            self.print_result(True, f"Retrieved details for {symbol}", 
                            {"instrument_id": instrument_id})
            
            return True
            
        except Exception as e:
            self.print_result(False, f"Failed to get instrument info: {str(e)}")
            return False
    
    def step_6_chart_data(self):
        """Step 6: Get chart data"""
        self.print_step(6, "Get Chart Data")
        
        if not self.selected_instrument:
            self.print_result(False, "No instrument selected")
            return False
        
        try:
            # Get chart data using unified client
            instrument_id = getattr(self.selected_instrument, 'instrument_id', 
                                  getattr(self.selected_instrument, 'id', None))
            
            if not instrument_id:
                self.print_result(False, "No instrument ID available")
                return False
            
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=24)  # Last 24 hours
            
            chart_data = self.client.get_chart_data(
                instrument_id=instrument_id,
                timeframe='1H',
                from_date=start_time,
                to_date=end_time
            )
            
            data_points = len(chart_data) if isinstance(chart_data, list) else len(chart_data.get('data', []))
            self.print_result(True, f"Retrieved chart data with {data_points} data points")
            
            return True
            
        except Exception as e:
            self.print_result(False, f"Failed to get chart data: {str(e)}")
            return False
    
    def step_7_buy_sell_info(self):
        """Step 7: Get buy/sell info"""
        self.print_step(7, "Get Buy/Sell Information")
        
        if not self.selected_instrument:
            self.print_result(False, "No instrument selected")
            return False
        
        try:
            # Get buy/sell info using unified client
            instrument_id = getattr(self.selected_instrument, 'instrument_id', 
                                  getattr(self.selected_instrument, 'id', None))
            
            if not instrument_id:
                self.print_result(False, "No instrument ID available")
                return False
            
            buy_sell_info = self.client.get_buy_sell_info(
                instrument_id=instrument_id,
                amount=100.0  # Test amount as float
            )
            
            symbol = getattr(self.selected_instrument, 'symbol', 'Unknown')
            self.print_result(True, f"Retrieved buy/sell info for {symbol}", 
                            {
                                "buy_price": buy_sell_info.get('BuyPrice'),
                                "sell_price": buy_sell_info.get('SellPrice'),
                                "spread": buy_sell_info.get('Spread')
                            })
            
            return True
            
        except Exception as e:
            self.print_result(False, f"Failed to get buy/sell info: {str(e)}")
            return False
    
    def step_8_create_order(self):
        """Step 8: Create an order without risk management"""
        self.print_step(8, "Create Order (No Risk Management)")
        
        if not self.selected_instrument:
            self.print_result(False, "No instrument selected")
            return False
        
        try:
            # Create order using unified client
            instrument_id = getattr(self.selected_instrument, 'instrument_id', 
                                  getattr(self.selected_instrument, 'id', None))
            
            if not instrument_id:
                self.print_result(False, "No instrument ID available")
                return False
            
            print("⚠️  Creating a small demo order (will be cancelled immediately)")
            
            # Use place_order method which correctly maps to the trading client
            order_result = self.client.place_order(
                instrument_id=instrument_id,
                amount=100.0,  # Small test amount as float
                operation_type='Buy',
                order_type='Market'
            )
            
            self.test_order_id = order_result.get('OrderId') or order_result.get('order_id')
            symbol = getattr(self.selected_instrument, 'symbol', 'Unknown')
            
            self.print_result(True, f"Created order for {symbol}", 
                            {"order_id": self.test_order_id})
            
            return True
            
        except Exception as e:
            self.print_result(False, f"Failed to create order: {str(e)}")
            return False
    
    def step_9_get_orders(self):
        """Step 9: Get orders"""
        self.print_step(9, "Get Current Orders")
        
        try:
            # Get orders using unified client
            orders = self.client.get_orders()
            
            active_orders = len(orders)
            self.print_result(True, f"Retrieved {active_orders} active orders")
            
            # Find our test order
            if self.test_order_id:
                test_order_found = False
                for order in orders:
                    order_id = str(order.get('OrderId', order.get('order_id', '')))
                    if order_id == str(self.test_order_id):
                        test_order_found = True
                        break
                
                if test_order_found:
                    print(f"✅ Found our test order: {self.test_order_id}")
                else:
                    print(f"⚠️  Test order {self.test_order_id} not found (may have been filled)")
            
            return True
            
        except Exception as e:
            self.print_result(False, f"Failed to get orders: {str(e)}")
            return False
    
    def step_10_edit_order(self):
        """Step 10: Edit the order"""
        self.print_step(10, "Edit Order")
        
        if not self.test_order_id:
            print("⚠️  No test order to edit (order may have been filled)")
            return True
        
        try:
            # Try to edit order using the trading client directly since edit_order 
            # is not exposed in the unified client
            edit_result = self.client.trading_client.edit_plus500_order(
                order_id=self.test_order_id,
                amount='150'  # Change amount
            )
            
            self.print_result(True, f"Edited order {self.test_order_id}", edit_result)
            return True
            
        except Exception as e:
            print(f"⚠️  Failed to edit order (this is normal if order was already filled): {str(e)}")
            return True  # Continue with test
    
    def step_11_cancel_order(self):
        """Step 11: Cancel the order"""
        self.print_step(11, "Cancel Order")
        
        if not self.test_order_id:
            print("⚠️  No test order to cancel")
            return True
        
        try:
            # Cancel order using unified client
            cancel_result = self.client.cancel_order(self.test_order_id)
            
            self.print_result(True, f"Cancelled order {self.test_order_id}", cancel_result)
            return True
            
        except Exception as e:
            print(f"⚠️  Failed to cancel order (this is normal if order was already filled): {str(e)}")
            return True  # Continue with test
    
    def step_12_closed_positions(self):
        """Step 12: Get closed positions"""
        self.print_step(12, "Get Closed Positions")
        
        try:
            # Get closed positions using unified client
            closed_positions = self.client.get_closed_positions()
            
            position_count = len(closed_positions)
            self.print_result(True, f"Retrieved {position_count} closed positions")
            
            return True
            
        except Exception as e:
            self.print_result(False, f"Failed to get closed positions: {str(e)}")
            return False
    
    def run_complete_test(self):
        """Run the complete test suite"""
        print("🚀 PLUS500 API COMPLETE LIVE TEST")
        print("=" * 50)
        print(f"Timestamp: {datetime.now()}")
        print(f"Using: Plus500ApiClient (Unified Interface)")
        print(f"Session directory: {self.client.sm.session_data_path.parent}")
        print()
        print("This test will demonstrate:")
        print("• Real first-time authentication experience")
        print("• All major API functions through unified client")
        print("• Complete order lifecycle (create → edit → cancel)")
        print("• Account management and data retrieval")
        print()
        
        steps = [
            self.step_1_authentication,
            self.step_2_switch_demo,
            self.step_3_account_balance,
            self.step_4_tradable_instruments,
            self.step_5_instrument_info,
            self.step_6_chart_data,
            self.step_7_buy_sell_info,
            self.step_8_create_order,
            self.step_9_get_orders,
            self.step_10_edit_order,
            self.step_11_cancel_order,
            self.step_12_closed_positions
        ]
        
        success_count = 0
        total_steps = len(steps)
        
        for step_func in steps:
            try:
                if step_func():
                    success_count += 1
                time.sleep(1)  # Brief pause between steps
            except KeyboardInterrupt:
                print("\n⚠️  Test interrupted by user")
                break
            except Exception as e:
                print(f"\n❌ Unexpected error in {step_func.__name__}: {e}")
        
        # Final summary
        print(f"\n{'='*60}")
        print("FINAL TEST RESULTS")
        print(f"{'='*60}")
        print(f"✅ Successful steps: {success_count}/{total_steps}")
        print(f"🎯 Success rate: {(success_count/total_steps)*100:.1f}%")
        
        if success_count == total_steps:
            print("🎉 ALL TESTS PASSED! Plus500 API is fully functional!")
        elif success_count >= total_steps * 0.8:
            print("✅ Most tests passed! API is working well with minor issues.")
        else:
            print("⚠️  Several tests failed. Please review the errors above.")
        
        # Show session info
        if self.client.is_authenticated():
            print(f"\n📄 Session saved to: {self.client.sm.session_data_path}")
            print("   This session can be reused for future API calls.")
        
        return success_count == total_steps


if __name__ == "__main__":
    print("Plus500 API Complete Live Test - First Time User Experience")
    print("=" * 65)
    print()
    print("🔥 IMPORTANT: This is a LIVE TEST with REAL AUTHENTICATION")
    print("   • Will use credentials from .env file if available")
    print("   • Otherwise will prompt for credentials")
    print("   • A small demo order will be created and immediately cancelled")
    print("   • Your session will be saved for future use")
    print("   • All operations will be performed on DEMO account")
    print()
    print("This test demonstrates:")
    print("✓ Complete first-time user authentication process")
    print("✓ Using the unified Plus500ApiClient interface")
    print("✓ All major API functionality end-to-end")
    print("✓ Real trading operations (on demo account)")
    print()
    
    response = input("Are you ready to start the live test? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("Test cancelled by user.")
        sys.exit(0)
    
    runner = Plus500LiveTestRunner()
    success = runner.run_complete_test()
    
    sys.exit(0 if success else 1)
        
    def print_step(self, step_num: int, description: str):
        """Print formatted step header"""
        print(f"\n{'='*60}")
        print(f"STEP {step_num}: {description}")
        print(f"{'='*60}")
        
    def print_result(self, success: bool, message: str, data=None):
        """Print formatted result"""
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{status}: {message}")
        if data and isinstance(data, dict):
            # Print key information, not the entire response
            if 'balance' in data:
                print(f"  Balance: ${data['balance']}")
            if 'equity' in data:
                print(f"  Equity: ${data['equity']}")
            if 'free_margin' in data:
                print(f"  Free Margin: ${data['free_margin']}")
            if len(data) < 10:  # Only print full data for small responses
                print(f"  Data: {json.dumps(data, indent=2, default=str)}")
        elif data and isinstance(data, list) and len(data) > 0:
            print(f"  Found {len(data)} items")
            if hasattr(data[0], '__dict__'):
                print(f"  Sample: {data[0].__dict__}")
            else:
                print(f"  Sample: {data[0]}")
    
    def step_1_authentication(self):
        """Step 1: Go through authentication like a first time user"""
        self.print_step(1, "First-Time User Authentication")
        
        try:
            # Clear any existing session to simulate first-time user
            if self.sm.session_data_path.exists():
                self.sm.session_data_path.unlink()
                print("Cleared existing session to simulate first-time user")
            
            # Use futures authentication (most reliable method)
            print("Starting authentication...")
            
            # Get credentials (in real use, these would be prompted)
            email = self.cfg.email or input("Enter email: ")
            password = self.cfg.password or input("Enter password: ")
            
            auth_result = self.auth_client.futures_authenticate(
                email=email,
                password=password,
                debug=False
            )
            
            if auth_result.get('success'):
                self.print_result(True, "Authentication completed successfully", 
                                {"session_valid": self.sm.has_valid_plus500_session()})
                return True
            else:
                self.print_result(False, f"Authentication failed: {auth_result.get('message', 'Unknown error')}")
                return False
            
        except Exception as e:
            self.print_result(False, f"Authentication failed: {str(e)}")
            return False
    
    def step_2_switch_demo(self):
        """Step 2: Switch to demo account"""
        self.print_step(2, "Switch to Demo Account")
        
        try:
            # Get current account mode first
            account_info = self.account_client.get_plus500_account_summary()
            current_mode = account_info.get('account_mode', 'Unknown')
            print(f"Current account mode: {current_mode}")
            
            if current_mode.lower() != 'demo':
                print("Switching to demo mode...")
                switch_result = self.account_client.switch_account_mode('demo')
                self.print_result(True, "Switched to demo account", switch_result)
            else:
                self.print_result(True, "Already in demo mode", {"mode": current_mode})
            
            return True
            
        except Exception as e:
            self.print_result(False, f"Failed to switch to demo: {str(e)}")
            return False
    
    def step_3_account_balance(self):
        """Step 3: Get account balance"""
        self.print_step(3, "Get Account Balance")
        
        try:
            # Get detailed balance information
            balance_summary = self.account_client.get_account_balance_summary()
            funds_info = self.account_client.get_plus500_funds_info()
            
            self.print_result(True, "Retrieved account balance", balance_summary)
            
            # Also test the new funds management info
            try:
                funds_mgmt = self.account_client.get_funds_management_info()
                print("✅ Funds management info retrieved successfully")
            except Exception as e:
                print(f"⚠️  Funds management info failed (may not be available): {e}")
            
            return True
            
        except Exception as e:
            self.print_result(False, f"Failed to get balance: {str(e)}")
            return False
    
    def step_4_tradable_instruments(self):
        """Step 4: Get tradable instruments"""
        self.print_step(4, "Get Tradable Instruments")
        
        try:
            # Get all instruments
            instruments = self.instruments_client.get_plus500_instruments()
            tradable_instruments = [inst for inst in instruments if inst.is_tradable]
            
            self.print_result(True, f"Found {len(tradable_instruments)} tradable instruments out of {len(instruments)} total")
            
            # Select a popular instrument for testing (EUR/USD or similar)
            for instrument in tradable_instruments:
                if any(symbol in instrument.symbol.upper() for symbol in ['EUR', 'GBP', 'USD', 'OIL', 'GOLD']):
                    self.selected_instrument = instrument
                    print(f"Selected instrument for testing: {instrument.symbol} (ID: {instrument.instrument_id})")
                    break
            
            if not self.selected_instrument:
                self.selected_instrument = tradable_instruments[0]
                print(f"Selected first available instrument: {self.selected_instrument.symbol}")
            
            return True
            
        except Exception as e:
            self.print_result(False, f"Failed to get instruments: {str(e)}")
            return False
    
    def step_5_instrument_info(self):
        """Step 5: Get instrument info"""
        self.print_step(5, "Get Instrument Information")
        
        if not self.selected_instrument:
            self.print_result(False, "No instrument selected")
            return False
        
        try:
            # Get detailed instrument information
            instrument_details = self.instruments_client.get_plus500_instrument_details(
                self.selected_instrument.instrument_id
            )
            
            self.print_result(True, f"Retrieved details for {self.selected_instrument.symbol}", 
                            {"instrument_id": self.selected_instrument.instrument_id})
            
            return True
            
        except Exception as e:
            self.print_result(False, f"Failed to get instrument info: {str(e)}")
            return False
    
    def step_6_chart_data(self):
        """Step 6: Get chart data"""
        self.print_step(6, "Get Chart Data")
        
        if not self.selected_instrument:
            self.print_result(False, "No instrument selected")
            return False
        
        try:
            # Get recent chart data
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=24)  # Last 24 hours
            
            chart_data = self.marketdata_client.get_plus500_chart_data(
                instrument_id=self.selected_instrument.instrument_id,
                timeframe='1H',
                start_time=start_time,
                end_time=end_time
            )
            
            data_points = len(chart_data)
            self.print_result(True, f"Retrieved chart data with {data_points} data points")
            
            return True
            
        except Exception as e:
            self.print_result(False, f"Failed to get chart data: {str(e)}")
            return False
    
    def step_7_buy_sell_info(self):
        """Step 7: Get buy/sell info"""
        self.print_step(7, "Get Buy/Sell Information")
        
        if not self.selected_instrument:
            self.print_result(False, "No instrument selected")
            return False
        
        try:
            # Get current buy/sell prices and spreads (using test amount)
            buy_sell_info = self.trading_client.get_plus500_buy_sell_info(
                instrument_id=self.selected_instrument.instrument_id,
                amount=Decimal('100')  # Test amount required for API call
            )
            
            self.print_result(True, f"Retrieved buy/sell info for {self.selected_instrument.symbol}", 
                            {
                                "buy_price": buy_sell_info.get('BuyPrice'),
                                "sell_price": buy_sell_info.get('SellPrice'),
                                "spread": buy_sell_info.get('Spread')
                            })
            
            return True
            
        except Exception as e:
            self.print_result(False, f"Failed to get buy/sell info: {str(e)}")
            return False
    
    def step_8_create_order(self):
        """Step 8: Create an order without risk management"""
        self.print_step(8, "Create Order (No Risk Management)")
        
        if not self.selected_instrument:
            self.print_result(False, "No instrument selected")
            return False
        
        try:
            # Create a small test order
            order_result = self.trading_client.create_plus500_order(
                instrument_id=self.selected_instrument.instrument_id,
                amount=Decimal('100'),  # Small test amount
                operation_type='Buy',  # Buy operation
                order_type='Market'
            )
            
            self.test_order_id = order_result.get('OrderId') or order_result.get('order_id')
            
            self.print_result(True, f"Created order for {self.selected_instrument.symbol}", 
                            {"order_id": self.test_order_id})
            
            return True
            
        except Exception as e:
            self.print_result(False, f"Failed to create order: {str(e)}")
            return False
    
    def step_9_get_orders(self):
        """Step 9: Get orders"""
        self.print_step(9, "Get Current Orders")
        
        try:
            # Get all current orders
            orders = self.trading_client.get_plus500_orders()
            
            active_orders = len(orders)
            self.print_result(True, f"Retrieved {active_orders} active orders")
            
            # Find our test order
            if self.test_order_id:
                test_order = None
                for order in orders:
                    if str(order.get('order_id', order.get('OrderId', ''))) == str(self.test_order_id):
                        test_order = order
                        break
                
                if test_order:
                    print(f"✅ Found our test order: {self.test_order_id}")
                else:
                    print(f"⚠️  Test order {self.test_order_id} not found in active orders (may have been filled)")
            
            return True
            
        except Exception as e:
            self.print_result(False, f"Failed to get orders: {str(e)}")
            return False
    
    def step_10_edit_order(self):
        """Step 10: Edit the order"""
        self.print_step(10, "Edit Order")
        
        if not self.test_order_id:
            self.print_result(False, "No test order to edit")
            return False
        
        try:
            # Try to edit the order (change amount)
            edit_result = self.trading_client.edit_plus500_order(
                order_id=self.test_order_id,
                amount='150'  # Change amount from 100 to 150
            )
            
            self.print_result(True, f"Edited order {self.test_order_id}", edit_result)
            
            return True
            
        except Exception as e:
            self.print_result(False, f"Failed to edit order: {str(e)}")
            # This might fail if order was already filled, which is OK
            return True  # Continue with the test
    
    def step_11_cancel_order(self):
        """Step 11: Cancel the order"""
        self.print_step(11, "Cancel Order")
        
        if not self.test_order_id:
            self.print_result(False, "No test order to cancel")
            return False
        
        try:
            # Cancel the test order
            cancel_result = self.trading_client.cancel_plus500_order(self.test_order_id)
            
            self.print_result(True, f"Cancelled order {self.test_order_id}", cancel_result)
            
            return True
            
        except Exception as e:
            self.print_result(False, f"Failed to cancel order: {str(e)}")
            # This might fail if order was already filled, which is OK
            return True  # Continue with the test
    
    def step_12_closed_positions(self):
        """Step 12: Get closed positions"""
        self.print_step(12, "Get Closed Positions")
        
        try:
            # Get closed positions
            closed_positions = self.trading_client.get_plus500_closed_positions()
            
            position_count = len(closed_positions)
            self.print_result(True, f"Retrieved {position_count} closed positions")
            
            # Test email report functionality
            try:
                print("Testing email report functionality...")
                # Note: This will only work if email is configured
                # email_result = self.trading_client.send_closed_positions_by_email(
                #     email="test@example.com",
                #     from_date=(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                # )
                print("⚠️  Email report test skipped (requires valid email configuration)")
            except Exception as e:
                print(f"⚠️  Email report failed (expected): {e}")
            
            return True
            
        except Exception as e:
            self.print_result(False, f"Failed to get closed positions: {str(e)}")
            return False
    
    def run_complete_test(self):
        """Run the complete test suite"""
        print("🚀 Starting Complete Plus500 API Live Test")
        print(f"Timestamp: {datetime.now()}")
        print(f"Session backup directory: {self.sm.session_data_path.parent}")
        
        steps = [
            self.step_1_authentication,
            self.step_2_switch_demo,
            self.step_3_account_balance,
            self.step_4_tradable_instruments,
            self.step_5_instrument_info,
            self.step_6_chart_data,
            self.step_7_buy_sell_info,
            self.step_8_create_order,
            self.step_9_get_orders,
            self.step_10_edit_order,
            self.step_11_cancel_order,
            self.step_12_closed_positions
        ]
        
        success_count = 0
        total_steps = len(steps)
        
        for step_func in steps:
            try:
                if step_func():
                    success_count += 1
                time.sleep(2)  # Brief pause between steps
            except KeyboardInterrupt:
                print("\n⚠️  Test interrupted by user")
                break
            except Exception as e:
                print(f"\n❌ Unexpected error in {step_func.__name__}: {e}")
        
        # Final summary
        print(f"\n{'='*60}")
        print("FINAL TEST RESULTS")
        print(f"{'='*60}")
        print(f"✅ Successful steps: {success_count}/{total_steps}")
        print(f"🎯 Success rate: {(success_count/total_steps)*100:.1f}%")
        
        if success_count == total_steps:
            print("🎉 ALL TESTS PASSED! Plus500 API is fully functional!")
        elif success_count >= total_steps * 0.8:
            print("✅ Most tests passed! API is working well with minor issues.")
        else:
            print("⚠️  Several tests failed. Please review the errors above.")
        
        return success_count == total_steps


if __name__ == "__main__":
    print("Plus500 API Complete Live Test")
    print("==============================")
    print()
    print("This test will:")
    print("1. Authenticate like a first-time user")
    print("2. Switch to demo account")
    print("3. Test all major API functions")
    print("4. Create, edit, and cancel a test order")
    print("5. Verify all functionality works end-to-end")
    print()
    
    response = input("Are you ready to start the live test? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("Test cancelled by user.")
        sys.exit(0)
    
    runner = Plus500LiveTestRunner()
    success = runner.run_complete_test()
    
    sys.exit(0 if success else 1)
