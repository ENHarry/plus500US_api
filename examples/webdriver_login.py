"""
WebDriver-powered authentication example for Plus500US

This example demonstrates how to use WebDriver for authentication,
which is now the primary method due to Plus500's anti-bot protection.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from plus500us_client import load_config
from plus500us_client.webdriver import WebDriverAuthHandler
from plus500us_client.hybrid import SessionBridge


def main():
    print("=== Plus500US WebDriver Authentication ===")
    print()
    
    # Load configuration
    config = load_config()
    print(f"Base URL: {config.base_url}")
    print(f"Account Type: {config.account_type}")
    print(f"Preferred Method: {config.preferred_method}")
    print()
    
    # Configure WebDriver settings
    webdriver_config = {
        "browser": "firefox",
        "headless": False,  # Set to True for headless operation
        "stealth_mode": True,
        "window_size": (1920, 1080),
        "implicit_wait": 10,
        "page_load_timeout": 30,
        "profile_path": "~/.plus500_profile"  # Persistent profile
    }
    
    print("WebDriver Configuration:")
    for key, value in webdriver_config.items():
        print(f"  {key}: {value}")
    print()
    
    # Perform WebDriver authentication
    print("🌐 Starting WebDriver authentication...")
    print("📝 Instructions:")
    print("  1. Browser will open to Plus500 login page")
    print("  2. Complete login manually (including any captcha)")
    print("  3. Select account type (demo/live) if prompted")
    print("  4. Press Enter in this terminal when logged in")
    print()
    
    try:
        with WebDriverAuthHandler(config, webdriver_config) as auth_handler:
            # Perform manual login flow
            session_data = auth_handler.manual_login_flow(
                account_type=config.account_type
            )
            
            print("✅ Authentication completed!")
            print(f"   Account Type: {session_data.get('account_type', 'Unknown')}")
            print(f"   Cookies: {len(session_data.get('cookies', []))} collected")
            print(f"   Authenticated: {session_data.get('authenticated', False)}")
            print()
            
            # Transfer session to requests for API usage
            print("🔄 Transferring session to requests...")
            session_bridge = SessionBridge()
            
            # Create a requests session (normally you'd use SessionManager)
            import requests
            requests_session = requests.Session()
            
            # Transfer WebDriver session to requests
            enhanced_session = session_bridge.transfer_webdriver_to_requests(
                session_data, requests_session
            )
            
            # Validate the transfer
            validation_result = session_bridge.validate_session_transfer(
                enhanced_session, f"{config.base_url}/trade"
            )
            
            if validation_result.get('authenticated'):
                print("✅ Session transfer successful!")
                print("   You can now use requests-based API calls")
                
                # Create backup
                backup_file = session_bridge.backup_session_data(session_data)
                print(f"   Session backup saved: {backup_file}")
                
            else:
                print("⚠️  Session transfer validation failed")
                print("   Manual verification may be needed")
            
            print()
            print("🎯 Next steps:")
            print("   - Use the enhanced requests session for API calls")
            print("   - Session data is backed up for future use")
            print("   - Browser profile is saved for faster future logins")
            
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        print()
        print("💡 Troubleshooting tips:")
        print("   - Ensure Chrome browser is installed and updated")
        print("   - Check if Plus500 website is accessible")
        print("   - Try running with headless=False to see browser interactions")
        print("   - Check firewall/antivirus settings")
        
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n🎉 WebDriver authentication example completed successfully!")
    else:
        print("\n💥 WebDriver authentication example failed!")
        sys.exit(1)