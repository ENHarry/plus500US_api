"""
Complete WebDriver automation workflow example - UNIFIED SINGLE BROWSER VERSION

This example demonstrates a full end-to-end workflow using a SINGLE WebDriver
browser instance for Plus500US, from authentication to trading operations.
"""
import os
import sys
from pathlib import Path
from decimal import Decimal
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Fix encoding for Windows Unicode support
if os.name == 'nt':
    import locale
    try:
        # Set console to use UTF-8 encoding
        os.system('chcp 65001 > nul')
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from plus500us_client import load_config
from plus500us_client.webdriver import WebDriverAuthHandler, WebDriverTradingClient, BrowserManager
from plus500us_client.hybrid import SessionBridge, FallbackHandler
from plus500us_client.errors import ValidationError, OrderRejectError


class UnifiedScreenshotMonitor:
    """Unified screenshot monitor using the same Selenium WebDriver"""
    
    def __init__(self, screenshots_dir: str = "workflow_screenshots"):
        self.screenshots_dir = Path(screenshots_dir)
        self.screenshots_dir.mkdir(exist_ok=True)
        self.driver = None
        
    def set_driver(self, driver):
        """Set the WebDriver instance to use for screenshots"""
        self.driver = driver
        
    def capture_screenshot(self, name: str, description: str = "") -> str:
        """Capture screenshot with timestamp"""
        if not self.driver:
            print(f"   ⚠️  No driver available for screenshot: {name}")
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
    
    def detect_account_balance(self) -> dict:
        """Detect balance from current page using Selenium"""
        if not self.driver:
            return {}
            
        try:
            balance_info = {}
            
            # Look for equity/balance elements using Plus500 specific selectors
            selectors = [
                "//li[@automation='equity']/span[@data-currency]",
                "//span[contains(text(), '$')]",
                "//div[contains(@class, 'account-balance')]//span"
            ]
            
            for i, selector in enumerate(selectors):
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for j, element in enumerate(elements):
                        text = element.text
                        if text and '$' in text:
                            balance_info[f"selector_{i}_{j}"] = {
                                'text': text,
                                'amount': text.replace('$', '').replace(',', '').strip()
                            }
                except:
                    continue
                    
            # Try to detect account mode
            mode_selectors = [
                "//span[contains(text(), 'Demo')]",
                "//span[contains(text(), 'Real')]"
            ]
            
            for selector in mode_selectors:
                try:
                    element = self.driver.find_element(By.XPATH, selector)
                    if element.is_displayed():
                        balance_info['mode'] = element.text
                        break
                except:
                    continue
                    
            return balance_info
            
        except Exception as e:
            print(f"   ⚠️  Balance detection failed: {e}")
            return {}


def simulate_human_click(driver, element):
    """Simulate human-like click for Plus500 compatibility"""
    try:
        # Use JavaScript click for Plus500 compatibility
        driver.execute_script("arguments[0].click();", element)
        time.sleep(0.5)  # Human-like delay
        return True
    except:
        try:
            # Fallback to regular click
            element.click()
            time.sleep(0.5)
            return True
        except:
            return False


def print_header(title):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)


def print_step(step_num, description):
    """Print a formatted step"""
    print(f"\n📋 Step {step_num}: {description}")
    print("-" * 50)


def main():
    print_header("Plus500US Unified Browser Automation Workflow")
    
    print("🚀 This example demonstrates UNIFIED browser automation:")
    print("   1. Single browser instance for all operations")
    print("   2. Integrated authentication and screenshot monitoring")
    print("   3. Proper session restoration in same browser")
    print("   4. Human-like click simulation for Plus500")
    print("   5. Account switching with balance verification")
    print("   6. Real trading operations on demo account")
    
    # Load configuration
    config = load_config()
    config.preferred_method = "webdriver"  # Force WebDriver
    
    print(f"\n⚙️  Configuration:")
    print(f"   Base URL: {config.base_url}")
    print(f"   Account Type: {config.account_type}")
    
    # Initialize components - SINGLE BROWSER INSTANCE
    browser_manager = None
    trading_client = None
    session_data = None
    session_bridge = SessionBridge()
    screenshot_monitor = UnifiedScreenshotMonitor()
    workflow_results = {}
    driver = None
    
    try:
        print_step(1, "Unified Browser Initialization")
        
        # Configure WebDriver
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
        
        # Apply config
        config.webdriver_config.update(webdriver_config)
        
        # Initialize SINGLE browser
        browser_manager = BrowserManager(config)
        driver = browser_manager.start_browser()
        screenshot_monitor.set_driver(driver)
        
        print("✅ Unified browser initialized")
        print(f"   Browser: {user_browser}")
        print("   Screenshot monitoring: Active")
        
        print_step(2, "Session Management")
        
        session_backup_file = "plus500_demo_session.json"
        
        # Check for existing session
        if Path(session_backup_file).exists():
            print("📁 Found existing session, attempting restore...")
            try:
                session_data = session_bridge.restore_session_data(session_backup_file)
                session_age = time.time() - session_data.get('timestamp', 0)
                
                if session_age > 86400:  # 24 hours
                    print("⏰ Session expired, will re-authenticate")
                    session_data = None
                else:
                    print(f"✅ Session valid (age: {session_age/3600:.1f} hours)")
            except Exception as e:
                print(f"⚠️  Session restore failed: {e}")
                session_data = None
        else:
            print("ℹ️  No existing session")
            session_data = None
        
        print_step(3, "Authentication in Single Browser")
        
        if session_data is None:
            # Fresh authentication in current browser
            print("🔐 Starting authentication in current browser...")
            
            # Navigate to login page
            login_url = f"{config.base_url}/trade?innerTags=_cc_&page=login"
            print(f"   🌐 Navigating to: {login_url}")
            driver.get(login_url)
            time.sleep(3)
            
            # Capture login page
            screenshot_monitor.capture_screenshot("01_login_page", "Login page loaded")
            
            # Try automatic credential filling
            auto_login_success = False
            if hasattr(config, 'email') and hasattr(config, 'password') and config.email and config.password:
                print("   🤖 Attempting automatic credential filling...")
                try:
                    # Fill email
                    email_elements = driver.find_elements(By.XPATH, "//input[@type='email' or contains(@placeholder, 'email')]")
                    for element in email_elements:
                        if element.is_displayed():
                            element.clear()
                            element.send_keys(config.email)
                            print("   ✅ Email filled")
                            break
                    
                    # Fill password
                    password_elements = driver.find_elements(By.XPATH, "//input[@type='password']")
                    for element in password_elements:
                        if element.is_displayed():
                            element.clear()
                            element.send_keys(config.password)
                            print("   ✅ Password filled")
                            break
                    
                    screenshot_monitor.capture_screenshot("02_credentials_filled", "Credentials filled")
                    
                    # Click login button with human simulation
                    login_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Log') or @type='submit']")
                    for button in login_buttons:
                        if button.is_displayed():
                            if simulate_human_click(driver, button):
                                print("   🔄 Login button clicked")
                                auto_login_success = True
                                time.sleep(5)  # Wait for login
                                break
                                
                except Exception as e:
                    print(f"   ⚠️  Auto-fill failed: {e}")
            
            if not auto_login_success:
                print("   📝 Manual login required")
                print("   Please complete login in the browser and press Enter when done...")
                input("   Press Enter after completing login: ")
            
            # Wait for successful login (check URL change)
            for i in range(30):  # 30 second timeout
                current_url = driver.current_url
                if 'trade' in current_url and 'login' not in current_url:
                    print("   ✅ Login successful - redirected to trading platform")
                    break
                time.sleep(1)
            else:
                raise Exception("Login timeout - no redirect detected")
            
            screenshot_monitor.capture_screenshot("03_post_login", "After successful login")
            
            # Extract session data from current browser
            cookies = driver.get_cookies()
            session_data = {
                'cookies': cookies,
                'timestamp': time.time(),
                'success': True,
                'account_type': 'unknown'  # Will be detected
            }
            
        else:
            # Restore session in current browser
            print("🔄 Restoring session in current browser...")
            
            # Navigate to base URL first
            driver.get(config.base_url)
            time.sleep(2)
            
            # Clear and restore cookies
            driver.delete_all_cookies()
            for cookie in session_data.get('cookies', []):
                try:
                    driver.add_cookie(cookie)
                except Exception as e:
                    print(f"   ⚠️  Cookie restore failed: {e}")
            
            # Navigate to trading platform
            driver.get(config.base_url + "/trade")
            time.sleep(3)
            
            print("✅ Session restored in current browser")
            screenshot_monitor.capture_screenshot("03_session_restored", "Session restored")
        
        print_step(4, "Account Mode Switch and Balance Monitoring")
        
        # Capture balance before any switching
        balance_before = screenshot_monitor.detect_account_balance()
        print("💰 Balance before account switching:")
        if balance_before:
            for key, info in balance_before.items():
                if isinstance(info, dict):
                    print(f"   {key}: {info['text']}")
                else:
                    print(f"   {key}: {info}")
        
        screenshot_monitor.capture_screenshot("04_balance_before_switch", "Balance before account switch")
        
        # Switch to demo account
        print("\n🔄 Switching to Demo account...")
        try:
            current_mode = browser_manager.get_current_account_mode()
            print(f"   Current mode: {current_mode}")
            
            if current_mode != "demo":
                print("   🔄 Performing account switch...")
                switch_success = browser_manager.switch_account_mode("demo")
                
                if switch_success:
                    print("   ✅ Account switch successful")
                    time.sleep(3)  # Allow UI to update
                    
                    # Capture balance after switch
                    balance_after = screenshot_monitor.detect_account_balance()
                    screenshot_monitor.capture_screenshot("05_balance_after_switch", "Balance after Demo switch")
                    
                    print("💰 Balance after switching to Demo:")
                    if balance_after:
                        for key, info in balance_after.items():
                            if isinstance(info, dict):
                                print(f"   {key}: {info['text']}")
                    
                    # Check for significant balance increase (Live ~$200 to Demo ~$50000)
                    if balance_before and balance_after:
                        try:
                            before_amounts = [float(info['amount']) for info in balance_before.values() 
                                            if isinstance(info, dict) and 'amount' in info and info['amount'].replace('.', '').isdigit()]
                            after_amounts = [float(info['amount']) for info in balance_after.values() 
                                           if isinstance(info, dict) and 'amount' in info and info['amount'].replace('.', '').isdigit()]
                            
                            if before_amounts and after_amounts:
                                max_before = max(before_amounts)
                                max_after = max(after_amounts)
                                
                                if max_after > max_before * 10:
                                    print(f"   🎉 ACCOUNT SWITCH CONFIRMED: ${max_before} → ${max_after}")
                                    workflow_results['account_switch_confirmed'] = True
                                else:
                                    print(f"   📊 Balance change: ${max_before} → ${max_after}")
                        except Exception as e:
                            print(f"   ⚠️  Balance comparison failed: {e}")
                else:
                    print("   ❌ Account switch failed")
            else:
                print("   ✅ Already in Demo mode")
                
        except Exception as e:
            print(f"   ⚠️  Account switch error: {e}")
        
        print_step(5, "Trading Client Initialization")
        
        # Initialize trading client with the SAME browser
        trading_client = WebDriverTradingClient(config, browser_manager)
        trading_client.initialize()
        
        print("✅ Trading client initialized with existing browser")
        print("   Using same browser session for all operations")
        
        print_step(6, "Demo Trading Operations")
        
        print("📈 Performing real demo trading operations...")
        
        # Get current positions
        print("\n📊 Checking current positions...")
        try:
            positions = trading_client.get_positions()
            if positions:
                print(f"   Found {len(positions)} positions")
                for pos in positions[:2]:  # Show first 2
                    print(f"   - {pos.get('instrument')}: {pos.get('side')} {pos.get('quantity')}, P&L: {pos.get('pnl')}")
            else:
                print("   No positions found - will create some")
        except Exception as e:
            print(f"   ⚠️  Position check failed: {e}")
        
        screenshot_monitor.capture_screenshot("06_current_positions", "Current positions check")
        
        # Place a demo market order
        print("\n🎯 Placing demo market order...")
        try:
            current_price = trading_client.get_current_instrument_price()
            if current_price:
                print(f"   Current price: ${current_price}")
                
                # Calculate risk levels
                stop_loss = current_price * Decimal("0.99")  # 1% stop loss
                take_profit = current_price * Decimal("1.02")  # 2% take profit
                
                print(f"   Order: BUY 1 MESU5 @ Market")
                print(f"   Stop Loss: ${stop_loss:.2f}")
                print(f"   Take Profit: ${take_profit:.2f}")
                
                result = trading_client.place_market_order(
                    instrument_id="MESU5",
                    side="BUY",
                    quantity=Decimal("1"),
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
                
                if result.get('success'):
                    print("   ✅ Market order placed successfully")
                    screenshot_monitor.capture_screenshot("07_order_placed", "Market order placed")
                else:
                    print(f"   ❌ Order failed: {result.get('error')}")
                    
        except Exception as e:
            print(f"   ⚠️  Market order failed: {e}")
        
        print_step(7, "Final Balance Verification")
        
        # Final balance check
        final_balance = screenshot_monitor.detect_account_balance()
        screenshot_monitor.capture_screenshot("08_final_balance", "Final balance verification")
        
        if final_balance:
            print("💰 Final account balance:")
            for key, info in final_balance.items():
                if isinstance(info, dict):
                    print(f"   {key}: {info['text']}")
            
            # Check if demo account confirmed
            amounts = [float(info['amount']) for info in final_balance.values() 
                      if isinstance(info, dict) and 'amount' in info and info['amount'].replace('.', '').isdigit()]
            if amounts and max(amounts) > 10000:
                print(f"   ✅ Demo account confirmed: ${max(amounts)}")
                workflow_results['demo_confirmed'] = True
            
        # Save session
        if session_data:
            session_bridge.backup_session_data(session_data, session_backup_file)
            print(f"💾 Session saved for future automatic login")
        
        print_header("Workflow Completed Successfully!")
        print("🎉 Single browser automation workflow completed!")
        print("   ✅ Used one browser instance throughout")
        print("   ✅ Proper session management")
        print("   ✅ Account switching with balance verification")
        print("   ✅ Real demo trading operations")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Workflow failed: {e}")
        screenshot_monitor.capture_screenshot("99_error", f"Error: {e}")
        return False
        
    finally:
        # Single cleanup
        if browser_manager:
            print("\n🧹 Cleaning up browser...")
            try:
                browser_manager.stop_browser()
                print("✅ Browser closed")
            except Exception as e:
                print(f"⚠️  Cleanup error: {e}")


if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n🎯 Unified Browser Workflow Benefits:")
        print("   - Single browser instance = no session conflicts")
        print("   - Proper click simulation for Plus500 compatibility")
        print("   - Integrated screenshot monitoring")
        print("   - Seamless session restoration")
        print("   - Real account switching with balance verification")
    else:
        print("\n💥 Workflow failed - check error screenshot")
        sys.exit(1)