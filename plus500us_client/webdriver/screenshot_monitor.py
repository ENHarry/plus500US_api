"""
Screenshot monitoring utility for Plus500US workflow validation
Uses Playwright to capture UI states and monitor account balance changes
"""

import os
import time
from pathlib import Path
from typing import Optional, Dict, Any
from playwright.sync_api import sync_playwright, Page, Browser
import logging

logger = logging.getLogger(__name__)

class ScreenshotMonitor:
    """Monitor UI states and capture screenshots for workflow validation"""
    
    def __init__(self, base_url: str, screenshots_dir: str = "workflow_screenshots"):
        self.base_url = base_url
        self.screenshots_dir = Path(screenshots_dir)
        self.screenshots_dir.mkdir(exist_ok=True)
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None
        
    def start_monitoring(self, headless: bool = False) -> None:
        """Start Playwright browser for monitoring"""
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=headless)
            context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            self.page = context.new_page()
            logger.info("Screenshot monitoring started")
        except Exception as e:
            logger.error(f"Failed to start screenshot monitoring: {e}")
            raise
    
    def stop_monitoring(self) -> None:
        """Stop Playwright browser"""
        try:
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            logger.info("Screenshot monitoring stopped")
        except Exception as e:
            logger.warning(f"Error stopping screenshot monitoring: {e}")
    
    def capture_screenshot(self, name: str, description: str = "") -> str:
        """Capture screenshot with timestamp and description"""
        if not self.page:
            raise RuntimeError("Monitoring not started. Call start_monitoring() first.")
        
        timestamp = int(time.time())
        filename = f"{timestamp}_{name}.png"
        filepath = self.screenshots_dir / filename
        
        try:
            self.page.screenshot(path=str(filepath), full_page=True)
            logger.info(f"Screenshot captured: {filename} - {description}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Failed to capture screenshot {name}: {e}")
            return ""
    
    def navigate_and_capture(self, url: str, name: str, description: str = "", wait_time: int = 3) -> str:
        """Navigate to URL and capture screenshot"""
        if not self.page:
            raise RuntimeError("Monitoring not started")
        
        try:
            self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            time.sleep(wait_time)  # Allow page to fully load
            return self.capture_screenshot(name, description)
        except Exception as e:
            logger.error(f"Failed to navigate and capture {url}: {e}")
            return ""
    
    def capture_login_state(self) -> str:
        """Capture login page state"""
        login_url = f"{self.base_url}/trade?innerTags=_cc_&page=login"
        return self.navigate_and_capture(
            login_url, 
            "01_login_page", 
            "Login page before authentication"
        )
    
    def capture_post_login_state(self) -> str:
        """Capture state immediately after login"""
        trading_url = f"{self.base_url}/trade"
        return self.navigate_and_capture(
            trading_url,
            "02_post_login",
            "Trading platform after login - before account switch"
        )
    
    def capture_account_switch_state(self) -> str:
        """Capture state after account mode switch"""
        return self.capture_screenshot(
            "03_account_switched",
            "Trading platform after account mode switch to Demo"
        )
    
    def detect_account_balance(self) -> Optional[Dict[str, Any]]:
        """Detect current account balance from UI"""
        if not self.page:
            return None
        
        try:
            # Look for balance indicators
            balance_selectors = [
                "[data-automation='equity']",
                ".equity-value",
                ".account-balance",
                ".balance-amount",
                "span:has-text('$')",
                "div:has-text('Equity')"
            ]
            
            balance_info = {}
            
            for selector in balance_selectors:
                try:
                    elements = self.page.locator(selector).all()
                    for element in elements:
                        text = element.text_content()
                        if text and '$' in text:
                            # Extract numeric value
                            import re
                            numbers = re.findall(r'[\d,]+\.?\d*', text.replace(',', ''))
                            if numbers:
                                balance_info[selector] = {
                                    'text': text,
                                    'amount': numbers[0]
                                }
                except Exception:
                    continue
            
            # Try to get account mode indicator
            mode_selectors = [
                "span:has-text('Demo')",
                "span:has-text('Real')",
                "span:has-text('Live')",
                ".account-mode",
                "[data-mode]"
            ]
            
            for selector in mode_selectors:
                try:
                    element = self.page.locator(selector).first
                    if element.is_visible():
                        balance_info['mode'] = element.text_content()
                        break
                except Exception:
                    continue
            
            return balance_info if balance_info else None
            
        except Exception as e:
            logger.error(f"Failed to detect account balance: {e}")
            return None
    
    def monitor_balance_change(self, expected_demo_amount: float = 50000.0) -> Dict[str, Any]:
        """Monitor balance change to verify account switch"""
        try:
            # Capture initial state
            initial_balance = self.detect_account_balance()
            initial_screenshot = self.capture_screenshot(
                "balance_before_switch",
                "Account balance before Demo switch"
            )
            
            # Wait a moment for any UI updates
            time.sleep(2)
            
            # Capture final state
            final_balance = self.detect_account_balance()
            final_screenshot = self.capture_screenshot(
                "balance_after_switch", 
                "Account balance after Demo switch"
            )
            
            # Analyze balance change
            result = {
                'initial_balance': initial_balance,
                'final_balance': final_balance,
                'initial_screenshot': initial_screenshot,
                'final_screenshot': final_screenshot,
                'switch_detected': False,
                'balance_increased': False
            }
            
            # Check if balance increased significantly (indicating Demo switch)
            if initial_balance and final_balance:
                try:
                    initial_amounts = [float(info['amount'].replace(',', '')) 
                                     for info in initial_balance.values() 
                                     if isinstance(info, dict) and 'amount' in info]
                    final_amounts = [float(info['amount'].replace(',', '')) 
                                   for info in final_balance.values() 
                                   if isinstance(info, dict) and 'amount' in info]
                    
                    if initial_amounts and final_amounts:
                        max_initial = max(initial_amounts)
                        max_final = max(final_amounts)
                        
                        # Check for significant increase (Live ~$200 to Demo ~$50000)
                        if max_final > max_initial * 10:  # At least 10x increase
                            result['switch_detected'] = True
                            result['balance_increased'] = True
                            logger.info(f"Account switch detected: ${max_initial} → ${max_final}")
                        
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse balance amounts: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to monitor balance change: {e}")
            return {'error': str(e)}
    
    def create_monitoring_report(self, workflow_results: Dict[str, Any]) -> str:
        """Create HTML report with screenshots and results"""
        report_path = self.screenshots_dir / "workflow_report.html"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Plus500US Workflow Monitoring Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .screenshot {{ margin: 20px 0; padding: 10px; border: 1px solid #ccc; }}
                .screenshot img {{ max-width: 800px; height: auto; }}
                .balance-info {{ background: #f0f0f0; padding: 10px; margin: 10px 0; }}
                .success {{ color: green; }}
                .error {{ color: red; }}
                .warning {{ color: orange; }}
            </style>
        </head>
        <body>
            <h1>Plus500US Workflow Monitoring Report</h1>
            <p>Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <h2>Workflow Results</h2>
            <div class="balance-info">
                <strong>Account Switch Detection:</strong> 
                <span class="{'success' if workflow_results.get('switch_detected') else 'error'}">
                    {'✅ Detected' if workflow_results.get('switch_detected') else '❌ Not Detected'}
                </span>
            </div>
            
            <h2>Screenshots</h2>
        """
        
        # Add screenshots to report
        for screenshot_file in sorted(self.screenshots_dir.glob("*.png")):
            html_content += f"""
            <div class="screenshot">
                <h3>{screenshot_file.stem}</h3>
                <img src="{screenshot_file.name}" alt="{screenshot_file.stem}">
            </div>
            """
        
        html_content += """
        </body>
        </html>
        """
        
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info(f"Monitoring report created: {report_path}")
            return str(report_path)
        except Exception as e:
            logger.error(f"Failed to create monitoring report: {e}")
            return ""

    def __enter__(self):
        """Context manager entry"""
        self.start_monitoring()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop_monitoring()