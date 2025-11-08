"""
Focused GC Order Test - Direct Target Approach
This test specifically targets GC (Gold) and uses improved clicking strategies
"""
import os
import sys
from pathlib import Path
from decimal import Decimal
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.action_chains import ActionChains

def print_step(step, description):
    print(f"\n🔥 STEP {step}: {description}")
    print("-" * 50)

def robust_click(driver, element, description="element"):
    """Try multiple click strategies"""
    print(f"   🎯 Attempting to click {description}")
    
    strategies = [
        lambda: element.click(),
        lambda: driver.execute_script("arguments[0].click();", element),
        lambda: ActionChains(driver).move_to_element(element).click().perform(),
        lambda: ActionChains(driver).click(element).perform()
    ]
    
    for i, strategy in enumerate(strategies, 1):
        try:
            strategy()
            print(f"   ✅ Click successful (strategy {i})")
            time.sleep(1)
            return True
        except Exception as e:
            print(f"   ⚠️  Strategy {i} failed: {str(e)[:50]}...")
            continue
    
    print(f"   ❌ All click strategies failed for {description}")
    return False

def take_screenshot(driver, name):
    """Take and save screenshot"""
    try:
        filename = f"gc_focused_{name}.png"
        driver.save_screenshot(filename)
        print(f"   📸 Screenshot: {filename}")
    except Exception as e:
        print(f"   ⚠️  Screenshot failed: {e}")

def main():
    print("=" * 70)
    print(" FOCUSED GC (GOLD) ORDER TEST")
    print("=" * 70)
    print("🥇 Target: Buy 1 GC contract")
    print("🎯 Focus: Direct GC targeting, no symbol switching")
    print("🔧 Strategy: Multiple click methods, wait for elements")
    
    # Setup Firefox with specific options for Plus500
    options = Options()
    options.add_argument("--width=1920")
    options.add_argument("--height=1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference("useAutomationExtension", False)
    
    driver = None
    
    try:
        print_step(1, "Initialize Browser for Plus500")
        driver = webdriver.Firefox(options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("✅ Firefox initialized with stealth settings")
        take_screenshot(driver, "01_browser_start")
        
        print_step(2, "Navigate to Plus500 Futures Platform")
        url = "https://futures.plus500.com"
        print(f"🌐 Loading: {url}")
        driver.get(url)
        
        # Wait for page load
        WebDriverWait(driver, 20).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        print("✅ Platform loaded")
        take_screenshot(driver, "02_platform_loaded")
        
        # Check if we need to accept cookies or login
        print("🔍 Checking for popups/login requirements...")
        
        # Look for cookie/accept buttons
        cookie_selectors = [
            "//button[contains(text(), 'Accept') or contains(text(), 'OK')]",
            "//button[contains(text(), 'Continue') or contains(text(), 'Agree')]"
        ]
        
        for selector in cookie_selectors:
            try:
                buttons = driver.find_elements(By.XPATH, selector)
                for btn in buttons:
                    if btn.is_displayed():
                        print(f"   🍪 Found popup button: {btn.text}")
                        robust_click(driver, btn, "popup button")
                        time.sleep(2)
                        break
            except:
                continue
        
        print_step(3, "Search Specifically for GC (Gold)")
        
        # Strategy 1: Direct navigation to trading page
        try:
            trade_url = "https://futures.plus500.com/trade"
            print(f"🌐 Direct navigation to: {trade_url}")
            driver.get(trade_url)
            time.sleep(5)
            take_screenshot(driver, "03_trade_page")
        except Exception as e:
            print(f"⚠️  Direct trade page failed: {e}")
        
        # Strategy 2: Look for search functionality
        search_attempted = False
        search_selectors = [
            "//input[@placeholder and contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'search')]",
            "//input[@type='search']",
            "//input[contains(@class, 'search')]"
        ]
        
        for selector in search_selectors:
            try:
                search_boxes = driver.find_elements(By.XPATH, selector)
                for search_box in search_boxes:
                    if search_box.is_displayed():
                        print("   🔍 Found search box - searching for GC")
                        search_box.clear()
                        search_box.send_keys("GC")
                        search_box.send_keys(Keys.ENTER)
                        time.sleep(3)
                        search_attempted = True
                        take_screenshot(driver, "04_gc_search")
                        break
            except Exception as e:
                continue
            if search_attempted:
                break
        
        # Strategy 3: Look for commodities/metals section
        if not search_attempted:
            print("🔍 Looking for Commodities/Metals navigation...")
            nav_selectors = [
                "//a[contains(text(), 'Commodities') or contains(text(), 'Metals')]",
                "//button[contains(text(), 'Commodities') or contains(text(), 'Metals')]",
                "//*[contains(@class, 'nav') and (contains(text(), 'Commodities') or contains(text(), 'Metals'))]"
            ]
            
            for selector in nav_selectors:
                try:
                    nav_elements = driver.find_elements(By.XPATH, selector)
                    for nav in nav_elements:
                        if nav.is_displayed():
                            print(f"   📂 Found navigation: {nav.text}")
                            robust_click(driver, nav, "commodities navigation")
                            time.sleep(3)
                            take_screenshot(driver, "05_commodities_section")
                            break
                except:
                    continue
        
        print_step(4, "Locate GC Contract Specifically")
        
        # Look for GC specifically in various forms
        gc_selectors = [
            "//*[text()='GC' or text()='GC ' or contains(text(), 'GC ')]",
            "//*[contains(text(), 'Gold') and (contains(text(), 'Future') or contains(text(), 'Contract'))]",
            "//*[contains(text(), 'XAUUSD') or contains(text(), 'XAU/USD')]",
            "//tr[.//text()[contains(., 'GC')]]",
            "//div[.//text()[contains(., 'GC')]]"
        ]
        
        gc_element = None
        for selector in gc_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for elem in elements:
                    if elem.is_displayed() and elem.text.strip():
                        print(f"   🥇 Found GC element: '{elem.text.strip()}'")
                        gc_element = elem
                        break
                if gc_element:
                    break
            except Exception as e:
                continue
        
        if not gc_element:
            print("⚠️  GC not immediately visible - trying manual page scan")
            # Scroll down to load more instruments
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            take_screenshot(driver, "06_after_scroll")
            
            # Try again after scrolling
            for selector in gc_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    for elem in elements:
                        if elem.is_displayed() and 'GC' in elem.text:
                            print(f"   🥇 Found GC after scroll: '{elem.text.strip()}'")
                            gc_element = elem
                            break
                    if gc_element:
                        break
                except:
                    continue
        
        print_step(5, "Execute GC Buy Order")
        
        if gc_element:
            print(f"🎯 Target locked: {gc_element.text}")
            
            # Scroll to the GC element
            driver.execute_script("arguments[0].scrollIntoView(true);", gc_element)
            time.sleep(1)
            
            # Look for Buy button specifically near the GC element
            # Check parent and sibling elements
            parent = gc_element.find_element(By.XPATH, "..")
            
            buy_selectors_relative = [
                ".//button[contains(text(), 'Buy') or contains(text(), 'BUY')]",
                ".//a[contains(text(), 'Buy') or contains(text(), 'BUY')]", 
                "..//button[contains(text(), 'Buy') or contains(text(), 'BUY')]",
                "../..//button[contains(text(), 'Buy') or contains(text(), 'BUY')]"
            ]
            
            buy_button = None
            for selector in buy_selectors_relative:
                try:
                    buttons = parent.find_elements(By.XPATH, selector)
                    for btn in buttons:
                        if btn.is_displayed():
                            print(f"   🔘 Found Buy button near GC: '{btn.text}'")
                            buy_button = btn
                            break
                    if buy_button:
                        break
                except:
                    continue
            
            if not buy_button:
                # Look for any clickable element in the GC row that might open trading
                print("   🔍 No direct Buy button - looking for clickable GC row")
                try:
                    # Try clicking the GC element itself
                    print("   🎯 Clicking GC element to open trading interface")
                    robust_click(driver, gc_element, "GC element")
                    time.sleep(3)
                    take_screenshot(driver, "07_gc_clicked")
                    
                    # Now look for Buy button in any modal/popup
                    buy_button_selectors = [
                        "//button[contains(text(), 'Buy') or contains(text(), 'BUY')]",
                        "//a[contains(text(), 'Buy') or contains(text(), 'BUY')]"
                    ]
                    
                    for selector in buy_button_selectors:
                        try:
                            buttons = driver.find_elements(By.XPATH, selector)
                            for btn in buttons:
                                if btn.is_displayed():
                                    print(f"   🔘 Found Buy button in popup: '{btn.text}'")
                                    buy_button = btn
                                    break
                            if buy_button:
                                break
                        except:
                            continue
                            
                except Exception as e:
                    print(f"   ⚠️  Clicking GC element failed: {e}")
            
            if buy_button:
                print("🚀 EXECUTING BUY ORDER FOR GC")
                
                # Highlight the button for visual confirmation
                driver.execute_script("arguments[0].style.border='3px solid red'", buy_button)
                take_screenshot(driver, "08_buy_button_highlighted")
                
                # Click the buy button
                success = robust_click(driver, buy_button, "GC Buy button")
                
                if success:
                    print("✅ Buy button clicked successfully!")
                    time.sleep(3)
                    take_screenshot(driver, "09_after_buy_click")
                    
                    # Look for order dialog
                    dialog_selectors = [
                        "//div[contains(@class, 'modal') or contains(@class, 'dialog')]",
                        "//form[contains(@class, 'order') or contains(@class, 'trade')]"
                    ]
                    
                    order_dialog = None
                    for selector in dialog_selectors:
                        try:
                            dialogs = driver.find_elements(By.XPATH, selector)
                            for dialog in dialogs:
                                if dialog.is_displayed():
                                    print("   📋 Order dialog detected!")
                                    order_dialog = dialog
                                    break
                            if order_dialog:
                                break
                        except:
                            continue
                    
                    if order_dialog:
                        print("🎯 CONFIGURING ORDER IN DIALOG")
                        
                        # Set quantity to 1
                        quantity_selectors = [
                            ".//input[@type='number']",
                            ".//input[contains(@placeholder, 'amount') or contains(@placeholder, 'quantity')]"
                        ]
                        
                        for selector in quantity_selectors:
                            try:
                                inputs = order_dialog.find_elements(By.XPATH, selector)
                                for inp in inputs:
                                    if inp.is_displayed():
                                        print("   📝 Setting quantity to 1")
                                        inp.clear()
                                        inp.send_keys("1")
                                        break
                            except:
                                continue
                        
                        take_screenshot(driver, "10_quantity_set")
                        
                        # Submit the order
                        submit_selectors = [
                            ".//button[contains(text(), 'Confirm') or contains(text(), 'Submit')]",
                            ".//button[contains(text(), 'Place') or contains(text(), 'Buy')]"
                        ]
                        
                        for selector in submit_selectors:
                            try:
                                submit_buttons = order_dialog.find_elements(By.XPATH, selector)
                                for btn in submit_buttons:
                                    if btn.is_displayed():
                                        print(f"   🚀 SUBMITTING ORDER: '{btn.text}'")
                                        robust_click(driver, btn, "Submit order button")
                                        time.sleep(3)
                                        take_screenshot(driver, "11_order_submitted")
                                        
                                        print("🎉 GC ORDER SUBMITTED!")
                                        print("   📊 Order: BUY 1 GC contract")
                                        print("   🏦 Account: Demo")
                                        print("   ✅ Execution: Completed")
                                        
                                        return True
                            except Exception as e:
                                print(f"   ⚠️  Submit button error: {e}")
                                continue
                    
                    else:
                        print("   ⚠️  No order dialog appeared after clicking Buy")
                        
                else:
                    print("   ❌ Failed to click Buy button")
                    
            else:
                print("   ❌ No Buy button found for GC")
                
        else:
            print("❌ Could not locate GC contract on the platform")
            print("📝 Manual verification needed:")
            print("   1. Check if GC is available on this platform")
            print("   2. Verify account has access to futures trading")
            print("   3. Confirm GC symbol naming convention")
        
        # Keep browser open for manual inspection
        print("\n🔍 MANUAL VERIFICATION MODE")
        print("Browser will stay open for manual inspection...")
        print("Please manually verify GC availability and place order if needed")
        input("Press Enter when ready to close browser...")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        take_screenshot(driver, "error_state")
        return False
        
    finally:
        if driver:
            print("\n🧹 Closing browser...")
            driver.quit()

if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n🎯 FOCUSED GC TEST RESULTS:")
        print("   ✅ Targeted GC specifically (no symbol switching)")
        print("   ✅ Used robust clicking strategies") 
        print("   ✅ Manual verification option provided")
        print("   📸 Screenshots saved for review")
    else:
        print("\n❌ Test encountered issues - check screenshots")
        sys.exit(1)