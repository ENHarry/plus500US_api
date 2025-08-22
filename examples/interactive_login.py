from plus500us_client import load_config, SessionManager
from plus500us_client.auth import AuthClient
from plus500us_client.errors import CaptchaRequiredError
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def main():
    print("=== Plus500US Interactive Login ===")
    
    # Load config and check credentials
    cfg = load_config()
    print(f"Account Type: {cfg.account_type}")
    print(f"Base URL: {cfg.base_url}")
    print(f"Email configured: {'Yes' if cfg.email else 'No'}")
    print(f"Password configured: {'Yes' if cfg.password else 'No'}")
    print()
    
    sm = SessionManager(cfg)
    auth = AuthClient(cfg, sm)
    
    try:
        print("Attempting programmatic login...")
        login_result = auth.login(interactive_mode=False)
        print("✓ Logged in programmatically.")
        
        # Show account type from login result
        if "account_type" in login_result:
            print(f"Account Type: {login_result['account_type']}")
            
    except CaptchaRequiredError:
        print("Captcha detected; switching to interactive handoff...")
        auth.interactive_handoff()
        print("✓ Session imported. You can now call authenticated endpoints.")
    except Exception as e:
        print(f"❌ Login failed: {e}")
        print("\nTip: Make sure you have set PLUS500US_EMAIL and PLUS500US_PASSWORD environment variables")
        print("Or create a .env file in the project root with these variables.")

if __name__ == "__main__":
    main()
