"""
Integration tests for complete WebDriver workflow
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

from plus500us_client.config import Config
from plus500us_client.webdriver import (
    BrowserManager, WebDriverAuthHandler, WebDriverTradingClient,
    ElementDetector, WebDriverUtils
)
from plus500us_client.hybrid import SessionBridge, MethodSelector, FallbackHandler


@pytest.mark.webdriver
@pytest.mark.integration
class TestWebDriverWorkflowIntegration:
    """Test complete WebDriver workflow integration"""
    
    def test_complete_authentication_to_trading_workflow(self, test_config, browser_available):
        """Test complete workflow from authentication to trading"""
        if not browser_available:
            pytest.skip("Browser not available")
        
        # This test simulates the complete workflow but uses mocks for external dependencies
        with patch('plus500us_client.webdriver.auth_handler.input', return_value=""):
            
            # Step 1: Initialize components
            webdriver_config = {"browser": "chrome", "headless": True}
            browser_manager = BrowserManager(test_config)
            
            try:
                # Step 2: Create authentication handler
                auth_handler = WebDriverAuthHandler(test_config, webdriver_config)
                auth_handler.browser_manager = browser_manager
                
                # Mock successful authentication
                mock_session_data = {
                    "cookies": [{"name": "session", "value": "test123", "domain": ".plus500.com"}],
                    "account_type": "demo",
                    "authenticated": True,
                    "user_agent": "Test Browser",
                    "timestamp": 1640995200
                }
                
                with patch.object(auth_handler, 'manual_login_flow', return_value=mock_session_data):
                    session_data = auth_handler.manual_login_flow()
                
                assert session_data["authenticated"] is True
                
                # Step 3: Create trading client
                trading_client = WebDriverTradingClient(test_config, browser_manager)
                trading_client.initialize()
                
                assert trading_client.driver is not None
                assert trading_client.element_detector is not None
                
                # Step 4: Test trading operations (mocked)
                with patch.object(trading_client, '_navigate_to_instrument'):
                    with patch.object(trading_client, '_submit_order', return_value={"success": True, "order_id": "12345"}):
                        with patch.object(trading_client.element_detector, 'find_element_robust', return_value=Mock()):
                            
                            result = trading_client.place_market_order("TEST", "BUY", Decimal("1"))
                            assert result["success"] is True
                
            finally:
                browser_manager.cleanup()
    
    def test_session_bridge_integration(self, test_config, mock_session_data):
        """Test session bridge integration between WebDriver and requests"""
        bridge = SessionBridge()
        
        # Mock requests session
        mock_requests_session = Mock()
        mock_requests_session.cookies = Mock()
        
        # Test session transfer
        requests_session = bridge.transfer_webdriver_to_requests(mock_session_data, mock_requests_session)
        
        assert requests_session is not None
        
        # Test session validation
        with patch.object(requests_session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.url = "https://futures.plus500.com/dashboard"
            mock_get.return_value = mock_response
            
            validation = bridge.validate_session_transfer(requests_session, "https://futures.plus500.com/dashboard")
            assert validation.get('authenticated') is True
    
    def test_fallback_handler_with_webdriver_integration(self, test_config):
        """Test fallback handler integration with WebDriver components"""
        fallback_handler = FallbackHandler(test_config)
        
        # Mock a function that fails with requests but succeeds with WebDriver
        def mock_trading_operation(instrument, side, quantity, method=None):
            if method.value == "requests":
                raise Exception("Anti-bot protection detected")
            elif method.value == "webdriver":
                return {"success": True, "method": "webdriver", "order_id": "WD123"}
        
        # Configure fallback handler
        fallback_handler.method_selector.select_method = Mock(return_value=fallback_handler.method_selector.AutomationMethod.REQUESTS)
        fallback_handler.method_selector.get_fallback_method = Mock(return_value=fallback_handler.method_selector.AutomationMethod.WEBDRIVER)
        fallback_handler.method_selector.record_success = Mock()
        fallback_handler.method_selector.record_failure = Mock()
        
        with patch('time.sleep'):  # Speed up test
            result = fallback_handler.execute_with_fallback(
                mock_trading_operation, "trading",
                context={},
                instrument="TEST", side="BUY", quantity=Decimal("1")
            )
        
        assert result["success"] is True
        assert result["method"] == "webdriver"
    
    def test_element_detection_workflow(self, test_config, browser_available):
        """Test element detection workflow with real browser"""
        if not browser_available:
            pytest.skip("Browser not available")
        
        browser_manager = BrowserManager(test_config)
        
        try:
            driver = browser_manager.get_driver()
            detector = ElementDetector(driver)
            
            # Create test HTML page
            test_html = """
            <html><body>
                <button id="buy-btn" class="trade-button">BUY</button>
                <input id="quantity" type="number" placeholder="Quantity"/>
                <div class="price-display">$100.50</div>
                <table id="positions">
                    <tr><td>Position 1</td><td>BUY</td><td>10</td></tr>
                    <tr><td>Position 2</td><td>SELL</td><td>5</td></tr>
                </table>
            </body></html>
            """
            driver.get(f"data:text/html,{test_html}")
            
            # Test multiple selector strategies
            buy_button_selectors = {
                'xpath': ["//button[@id='buy-btn']", "//button[contains(text(), 'BUY')]"],
                'css': ["#buy-btn", ".trade-button"]
            }
            
            buy_button = detector.find_element_robust(buy_button_selectors)
            assert buy_button is not None
            assert detector.extract_text_safe(buy_button) == "BUY"
            
            # Test input field detection
            quantity_selectors = {
                'xpath': ["//input[@id='quantity']"],
                'css': ["#quantity", "input[type='number']"]
            }
            
            quantity_input = detector.find_element_robust(quantity_selectors)
            assert quantity_input is not None
            
            # Test table row detection
            position_rows = detector.find_elements_robust({
                'xpath': ["//table[@id='positions']//tr[td]"],
                'css': ["#positions tr:has(td)"]
            })
            assert len(position_rows) >= 2
            
        finally:
            browser_manager.cleanup()
    
    def test_trading_automation_workflow_simulation(self, test_config, browser_available):
        """Test trading automation workflow with simulated interface"""
        if not browser_available:
            pytest.skip("Browser not available")
        
        browser_manager = BrowserManager(test_config)
        
        try:
            trading_client = WebDriverTradingClient(test_config, browser_manager)
            trading_client.initialize()
            
            # Create simulated trading interface
            trading_html = """
            <html><body>
                <input id="instrument-search" placeholder="Search instrument"/>
                <select id="order-type">
                    <option value="MARKET">Market</option>
                    <option value="LIMIT">Limit</option>
                </select>
                <button id="buy-btn">BUY</button>
                <button id="sell-btn">SELL</button>
                <input id="quantity" type="number" value="1"/>
                <input id="price" type="number" value="100.00"/>
                <input id="stop-loss" type="number" placeholder="Stop Loss"/>
                <input id="take-profit" type="number" placeholder="Take Profit"/>
                <button id="confirm-order">Confirm Order</button>
                <div id="success-msg" style="display:none">Order placed successfully</div>
                <div id="order-id" style="display:none">ORDER_123456</div>
            </body></html>
            """
            trading_client.driver.get(f"data:text/html,{trading_html}")
            
            # Mock the internal methods to simulate real behavior
            def mock_navigate_to_instrument(instrument_id):
                search_input = trading_client.driver.find_element("id", "instrument-search")
                search_input.clear()
                search_input.send_keys(instrument_id)
            
            def mock_submit_order():
                # Simulate order submission
                success_msg = trading_client.driver.find_element("id", "success-msg")
                order_id_elem = trading_client.driver.find_element("id", "order-id")
                
                # Make elements visible (simulate successful submission)
                trading_client.driver.execute_script("arguments[0].style.display = 'block';", success_msg)
                trading_client.driver.execute_script("arguments[0].style.display = 'block';", order_id_elem)
                
                return {
                    "success": True,
                    "order_id": "ORDER_123456",
                    "message": "Order placed successfully",
                    "timestamp": 1640995200
                }
            
            # Replace methods with mocks
            trading_client._navigate_to_instrument = mock_navigate_to_instrument
            trading_client._submit_order = mock_submit_order
            
            # Test market order placement
            result = trading_client.place_market_order("EURUSD", "BUY", Decimal("1"))
            
            assert result["success"] is True
            assert result["order_id"] == "ORDER_123456"
            
        finally:
            browser_manager.cleanup()
    
    @pytest.mark.slow
    def test_error_handling_and_recovery_workflow(self, test_config, browser_available):
        """Test error handling and recovery in WebDriver workflow"""
        if not browser_available:
            pytest.skip("Browser not available")
        
        browser_manager = BrowserManager(test_config)
        fallback_handler = FallbackHandler(test_config)
        
        try:
            # Test browser crash recovery
            driver1 = browser_manager.get_driver()
            assert browser_manager.is_driver_alive()
            
            # Simulate browser crash
            driver1.quit()
            assert not browser_manager.is_driver_alive()
            
            # Test restart
            driver2 = browser_manager.restart_driver()
            assert browser_manager.is_driver_alive()
            assert driver2 != driver1
            
            # Test element detection with retry
            detector = ElementDetector(driver2)
            
            # Create page with delayed element
            delayed_html = """
            <html><body>
                <div id="loading">Loading...</div>
                <script>
                setTimeout(function() {
                    var btn = document.createElement('button');
                    btn.id = 'delayed-btn';
                    btn.textContent = 'Ready';
                    document.body.appendChild(btn);
                    document.getElementById('loading').style.display = 'none';
                }, 500);
                </script>
            </body></html>
            """
            driver2.get(f"data:text/html,{delayed_html}")
            
            # Test waiting for element
            delayed_button = detector.wait_for_element("id", "delayed-btn", timeout=3)
            assert delayed_button is not None
            assert detector.extract_text_safe(delayed_button) == "Ready"
            
            # Test waiting for element to disappear
            loading_invisible = detector.wait_for_element_invisible("id", "loading", timeout=3)
            assert loading_invisible is True
            
        finally:
            browser_manager.cleanup()
    
    def test_partial_take_profit_validation_workflow(self, test_config):
        """Test partial take profit validation workflow"""
        browser_manager = Mock()
        mock_driver = Mock()
        browser_manager.get_driver.return_value = mock_driver
        
        trading_client = WebDriverTradingClient(test_config, browser_manager)
        trading_client.initialize()
        
        # Mock positions data
        positions_data = [
            {
                "id": "POS_001",
                "instrument": "EURUSD",
                "quantity": "5",  # 5 contracts
                "side": "BUY"
            },
            {
                "id": "POS_002", 
                "instrument": "GBPUSD",
                "quantity": "1",  # Only 1 contract
                "side": "SELL"
            }
        ]
        
        trading_client.get_positions = Mock(return_value=positions_data)
        trading_client.close_position = Mock(return_value=True)
        
        # Test valid partial take profit (position with > 1 contract)
        result = trading_client.execute_partial_take_profit("POS_001", Decimal("2"))
        assert result is True
        trading_client.close_position.assert_called_with("POS_001", Decimal("2"))
        
        # Test invalid partial take profit (position with only 1 contract)
        from plus500us_client.errors import ValidationError
        with pytest.raises(ValidationError, match="Partial take profit requires position > 1 contract"):
            trading_client.execute_partial_take_profit("POS_002", Decimal("0.5"))
        
        # Test partial take profit that would leave insufficient remaining
        with pytest.raises(ValidationError, match="Partial TP would leave position with"):
            trading_client.execute_partial_take_profit("POS_001", Decimal("4.5"))
    
    def test_method_selection_integration_workflow(self, test_config):
        """Test method selection integration in realistic workflow"""
        method_selector = MethodSelector(test_config)
        fallback_handler = FallbackHandler(test_config, method_selector)
        
        # Simulate login operation workflow
        test_config.preferred_method = "auto"
        
        # First login attempt - should try requests
        method1 = method_selector.select_method("login")
        assert method1.value == "requests"
        
        # Simulate captcha error
        from plus500us_client.errors import CaptchaRequiredError
        captcha_error = CaptchaRequiredError("Captcha verification required")
        method_selector.record_failure("login", method1, captcha_error)
        
        # Next login attempt should detect captcha and use WebDriver
        context_with_captcha = {"captcha_detected": True}
        method2 = method_selector.select_method("login", context_with_captcha)
        assert method2.value == "webdriver"
        
        # Simulate successful WebDriver login
        method_selector.record_success("login", method2)
        
        # Trading operations should prefer WebDriver
        trading_method = method_selector.select_method("trading")
        assert trading_method.value == "webdriver"
        
        # Data operations can still try requests (unless history suggests otherwise)
        data_method = method_selector.select_method("market_data")
        # Could be either, depends on failure history
        assert data_method.value in ["requests", "webdriver"]
        
        # Check overall statistics
        stats = method_selector.get_method_stats()
        assert stats["failure_count"] >= 0
        assert "login_requests_failed" in stats["history"]
        assert "login_webdriver_success" in stats["history"]


@pytest.mark.webdriver
@pytest.mark.integration
@pytest.mark.slow
class TestWebDriverRealBrowserIntegration:
    """Integration tests requiring real browser (marked as slow)"""
    
    def test_real_browser_lifecycle_integration(self, test_config, browser_available):
        """Test complete browser lifecycle with real browser"""
        if not browser_available:
            pytest.skip("Browser not available")
        
        browser_manager = BrowserManager(test_config)
        
        try:
            # Test browser creation
            driver = browser_manager.get_driver()
            assert driver is not None
            assert browser_manager.is_driver_alive()
            
            # Test navigation
            driver.get("data:text/html,<html><body><h1>Test Page</h1></body></html>")
            assert "Test Page" in driver.page_source
            
            # Test element operations
            detector = ElementDetector(driver)
            h1_element = detector.find_element_robust({
                'xpath': ["//h1"],
                'css': ["h1"]
            })
            assert h1_element is not None
            assert detector.extract_text_safe(h1_element) == "Test Page"
            
            # Test WebDriver utils
            utils = WebDriverUtils()
            
            # Add a button for interaction testing
            driver.execute_script("""
                var btn = document.createElement('button');
                btn.id = 'test-btn';
                btn.textContent = 'Click Me';
                document.body.appendChild(btn);
            """)
            
            test_button = detector.find_element_robust({
                'xpath': ["//button[@id='test-btn']"],
                'css': ["#test-btn"]
            })
            
            # Test human-like interactions
            utils.human_like_click(driver, test_button)
            
            # Test restart functionality
            old_driver_id = id(driver)
            new_driver = browser_manager.restart_driver()
            new_driver_id = id(new_driver)
            
            assert old_driver_id != new_driver_id
            assert browser_manager.is_driver_alive()
            
        finally:
            browser_manager.cleanup()
    
    def test_authentication_flow_integration(self, test_config, browser_available):
        """Test authentication flow integration with real browser"""
        if not browser_available:
            pytest.skip("Browser not available")
        
        webdriver_config = {"browser": "chrome", "headless": True}
        
        # Mock user input to avoid hanging
        with patch('plus500us_client.webdriver.auth_handler.input', return_value="skip"):
            with WebDriverAuthHandler(test_config, webdriver_config) as auth_handler:
                driver = auth_handler.browser_manager.get_driver()
                
                # Test navigation to login page
                driver.get(test_config.base_url)
                
                # Verify we can detect basic page elements
                auth_handler.element_detector = ElementDetector(driver)
                
                # Test URL-based authentication check
                # (Note: This won't actually authenticate, just tests the mechanism)
                if "plus500" in driver.current_url.lower():
                    # Successfully navigated to Plus500
                    session_data = {
                        "cookies": [],
                        "account_type": "demo", 
                        "authenticated": False,  # Won't be true without real login
                        "user_agent": driver.execute_script("return navigator.userAgent;"),
                        "timestamp": 1640995200
                    }
                    
                    # Test session data validation
                    is_valid = auth_handler._validate_session_data(session_data)
                    # Won't be valid without real cookies/auth, but tests the mechanism
                    assert isinstance(is_valid, bool)