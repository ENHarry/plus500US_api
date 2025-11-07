"""
Complete Plus500 Authentication and Trading Example
This example demonstrates the complete authentication flow and basic trading operations.
"""

import os
import sys
import json
from pathlib import Path
import time
# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from plus500us_client.requests.config import Config
from plus500us_client.requests.session import SessionManager
from plus500us_client.requests.auth import AuthClient
from plus500us_client.requests.errors import AuthenticationError, AuthorizationError


def main():
    """Complete authentication and trading example"""
    
    print("=== Plus500 Complete Authentication Example ===\n")
    
    # Step 1: Initialize configuration
    print("1. Initializing configuration...")
    cfg = Config()
    sm = SessionManager(cfg)
    auth_client = AuthClient(cfg, sm)
    
    # Step 2: Get credentials (from environment or prompt)
    email = os.getenv('email')
    password = os.getenv('password')

    if not email:
        email = input("Enter your Plus500 email: ").strip()
    if not password:
        import getpass
        password = getpass.getpass("Enter your Plus500 password: ")
    
    print(f"Using email: {email}")
    
    try:
        # Step 3: Authenticate using the new system
        print("\n2. Authenticating with Plus500...")
        auth_result = auth_client.plus500_authenticate(
            email=email,
            password=password,
            account_type='demo'  # Use demo for testing
        )
        
        print("✅ Authentication successful!")
        print(f"Account type: {auth_result['account_type']}")
        print(f"API ready: {auth_result['api_ready']}")
        
        # Step 4: Get the Plus500 client for API operations
        print("\n3. Getting Plus500 API client...")
        plus500_client = auth_client.get_plus500_client()
        
        if not plus500_client.is_authenticated():
            raise AuthenticationError("Client not properly authenticated")
            
        print("✅ API client ready!")
        
        # Step 5: Test basic API operations
        print("\n4. Testing API operations...")
        
        # Get account information
        print("   Getting account information...")
        try:
            account_info = plus500_client.get_account_info()
            print(f"   ✅ Account info retrieved")
            # Don't print sensitive account details
        except Exception as e:
            print(f"   ❌ Failed to get account info: {e}")
        
        # Get trading instruments
        print("   Getting trading instruments...")
        try:
            instruments = plus500_client.get_trade_instruments()
            print(f"   ✅ Trading instruments retrieved")
            if 'InstrumentList' in instruments:
                print(f"   Found {len(instruments['InstrumentList'])} instruments")
            elif 'instruments' in instruments:
                print(f"   Found {len(instruments['instruments'])} instruments")
        except Exception as e:
            print(f"   ❌ Failed to get instruments: {e}")
        
        # Get positions
        print("   Getting open positions...")
        try:
            positions = plus500_client.get_positions()
            print(f"   ✅ Positions retrieved")
            if 'Positions' in positions:
                print(f"   Open positions: {len(positions['Positions'])}")
            elif 'positions' in positions:
                print(f"   Open positions: {len(positions['positions'])}")
        except Exception as e:
            print(f"   ❌ Failed to get positions: {e}")
            
        # Get closed positions history
        print("   Getting position history...")
        try:
            history = plus500_client.get_closed_positions(limit=10)
            print(f"   ✅ Position history retrieved")
            if 'ClosedPositions' in history:
                print(f"   Recent closed positions: {len(history['ClosedPositions'])}")
            elif 'positions' in history:
                print(f"   Recent closed positions: {len(history['positions'])}")
        except Exception as e:
            print(f"   ❌ Failed to get position history: {e}")
        
        # Step 6: Display authentication data summary
        print("\n5. Authentication Summary:")
        auth_data = plus500_client.auth_data
        print(f"   User Session ID: {'✅' if auth_data.get('UserSessionId') else '❌'}")
        print(f"   WebTrader Service ID: {'✅' if auth_data.get('WebTraderServiceId') else '❌'}")
        print(f"   Hash: {'✅' if auth_data.get('Hash') else '❌'}")
        print(f"   Client Type: {auth_data.get('ClientType', 'Not set')}")
        print(f"   Product Type: {auth_data.get('EProductType', 'Not set')}")
        print(f"   Connection Token: {'✅' if auth_data.get('connectionToken') else '❌'}")
        
        # Step 7: Save authentication data for inspection
        auth_data_file = Path("authentication_data.json")
        with open(auth_data_file, 'w') as f:
            # Remove sensitive data before saving
            safe_auth_data = {k: v for k, v in auth_data.items() 
                            if not any(sensitive in k.lower() for sensitive in ['password', 'token', 'hash'])}
            safe_auth_data['_note'] = 'Sensitive authentication data has been filtered out'
            json.dump(safe_auth_data, f, indent=2)
        print(f"\n6. Authentication data saved to: {auth_data_file}")
        
        print("\n=== Authentication Test Complete ===")
        print("✅ All authentication steps completed successfully!")
        print("\nNext steps:")
        print("- You can now use the plus500_client for trading operations")
        print("- Session data is saved and will be reused on subsequent runs")
        print("- Use plus500_client.create_order() to place trades")
        print("- Use plus500_client.close_position() to close positions")
        
    except AuthenticationError as e:
        print(f"\n❌ Authentication failed: {e}")
        print("\nTroubleshooting:")
        print("- Verify your email and password are correct")
        print("- Check if your account is locked or needs verification")
        print("- Try logging in manually through the web interface first")
        return 1
        
    except AuthorizationError as e:
        print(f"\n❌ Authorization failed: {e}")
        print("Your credentials are valid but access is denied.")
        return 1
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
