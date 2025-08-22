"""
Enhanced trading automation tests for Plus500US WebDriver functionality
"""

import pytest
import time
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from plus500us_client.webdriver.trading_automation import WebDriverTradingClient
from plus500us_client.webdriver.browser_manager import BrowserManager
from plus500us_client.webdriver.element_detector import ElementDetector
from plus500us_client.webdriver.selectors import Plus500Selectors
from plus500us_client.config import Config
from plus500us_client.errors import ValidationError, OrderRejectError


class TestEnhancedTradingAutomation:
    """Test enhanced Plus500US trading automation functionality"""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration"""
        config = Mock(spec=Config)
        config.futures_metadata = {
            "MESU5": {
                "tick_size": 0.25,
                "min_qty": 1
            }
        }
        config.webdriver_config = {
            "browser": "chrome",
            "headless": True,
            "stealth_mode": True
        }
        return config
    
    @pytest.fixture
    def mock_driver(self):
        """Create mock WebDriver"""
        driver = Mock()
        driver.current_url = "https://app.plus500.com/trade"
        driver.title = "Plus500 Trading"
        driver.get_window_size.return_value = {"width": 1920, "height": 1080}
        driver.execute_script.return_value = "complete"
        driver.get_cookies.return_value = []
        return driver
    
    @pytest.fixture
    def mock_browser_manager(self, mock_driver):
        """Create mock browser manager"""
        browser_manager = Mock(spec=BrowserManager)
        browser_manager.get_driver.return_value = mock_driver
        browser_manager.get_current_account_mode.return_value = "demo"
        browser_manager.switch_account_mode.return_value = True
        return browser_manager
    
    @pytest.fixture
    def trading_client(self, mock_config, mock_browser_manager):
        """Create trading client with mocked dependencies"""
        client = WebDriverTradingClient(mock_config, mock_browser_manager)
        client.initialize()
        return client
    
    def test_initialization(self, trading_client):
        """Test client initialization"""
        assert trading_client.driver is not None
        assert trading_client.element_detector is not None
        assert isinstance(trading_client.selectors, Plus500Selectors)
    
    def test_navigate_to_positions(self, trading_client):
        """Test navigation to positions view"""
        # Mock positions navigation element
        mock_element = Mock(spec=WebElement)
        trading_client.element_detector.find_element_robust = Mock(return_value=mock_element)
        trading_client.utils.human_like_click = Mock()
        
        trading_client._navigate_to_positions()
        
        trading_client.element_detector.find_element_robust.assert_called_once()
        trading_client.utils.human_like_click.assert_called_once_with(trading_client.driver, mock_element)
    
    def test_navigate_to_orders(self, trading_client):
        """Test navigation to orders view"""
        # Mock orders navigation element
        mock_element = Mock(spec=WebElement)
        trading_client.element_detector.find_element_robust = Mock(return_value=mock_element)
        trading_client.utils.human_like_click = Mock()
        
        trading_client._navigate_to_orders()
        
        trading_client.element_detector.find_element_robust.assert_called_once()
        trading_client.utils.human_like_click.assert_called_once_with(trading_client.driver, mock_element)
    
    def test_calculate_trailing_stop_amount(self, trading_client):
        """Test dynamic trailing stop calculation"""
        # Test high-priced instrument (0.1% of 6000 = 6.0, rounded to tick size 0.25)
        result = trading_client.calculate_trailing_stop_amount("MESU5", Decimal("6000"))
        assert result == Decimal("6.00")  # 0.1% of 6000, rounded to tick size
        
        # Test medium-priced instrument (0.2% of 500 = 1.0, but minimum $5 enforced)
        result = trading_client.calculate_trailing_stop_amount("TEST", Decimal("500"))
        assert result == Decimal("5.00")  # 0.2% of 500 = 1.0, but minimum $5 enforced
        
        # Test low-priced instrument (0.5% of 50 = 0.25, but minimum $5 enforced)
        result = trading_client.calculate_trailing_stop_amount("TEST", Decimal("50"))
        assert result == Decimal("5.00")  # Minimum $5 enforced
        
        # Test with custom percentage that results in value above minimum
        result = trading_client.calculate_trailing_stop_amount("TEST", Decimal("10000"), Decimal("0.5"))
        assert result == Decimal("50.00")  # 0.5% of 10000 = 50.0
    
    def test_get_current_instrument_price(self, trading_client):
        """Test current price extraction"""
        # Mock price element
        mock_element = Mock(spec=WebElement)
        trading_client.element_detector.find_element_robust = Mock(return_value=mock_element)
        trading_client.element_detector.extract_text_safe = Mock(return_value="6,434.00")
        trading_client.utils.extract_number_from_text = Mock(return_value=6434.0)
        
        result = trading_client.get_current_instrument_price()
        
        assert result == Decimal("6434.0")
        trading_client.element_detector.find_element_robust.assert_called_once()
    
    def test_set_trailing_stop_dynamic(self, trading_client):
        """Test dynamic trailing stop setting"""
        # Mock current price detection
        trading_client.get_current_instrument_price = Mock(return_value=Decimal("6000"))
        
        # Mock trailing stop elements
        mock_switch = Mock(spec=WebElement)
        mock_input = Mock(spec=WebElement)
        
        def mock_find_element(selector, **kwargs):
            if selector == trading_client.selectors.TRAILING_STOP_SWITCH:
                return mock_switch
            elif selector == trading_client.selectors.TRAILING_STOP_INPUT:
                return mock_input
            return None
        
        trading_client.element_detector.find_element_robust = Mock(side_effect=mock_find_element)
        trading_client._is_switch_enabled = Mock(return_value=False)
        trading_client.utils.human_like_click = Mock()
        trading_client.utils.human_like_type = Mock()
        
        result = trading_client._set_trailing_stop_dynamic("MESU5")
        
        assert result is True
        trading_client.utils.human_like_click.assert_called_once_with(trading_client.driver, mock_switch)
        trading_client.utils.human_like_type.assert_called_once()
    
    def test_extract_plus500_position_from_row(self, trading_client):
        """Test position data extraction from DOM row"""
        # Mock row element with position data
        mock_row = Mock(spec=WebElement)
        
        # Mock position elements
        mock_name = Mock(spec=WebElement)
        mock_action = Mock(spec=WebElement)
        mock_amount = Mock(spec=WebElement)
        
        def mock_find_element(by, xpath):
            if "name" in xpath:
                return mock_name
            elif "action" in xpath:
                return mock_action
            elif "amount" in xpath:
                return mock_amount
            raise Exception("Element not found")
        
        mock_row.find_element = Mock(side_effect=mock_find_element)
        
        # Mock text extraction
        trading_client.element_detector.extract_text_safe = Mock()
        trading_client.element_detector.extract_text_safe.side_effect = [
            "Micro E-mini S&P 500 Sep 25",  # instrument
            "BUY",  # side
            "2 Contracts"  # amount
        ]
        trading_client.utils.extract_number_from_text = Mock(return_value=2.0)
        
        result = trading_client._extract_plus500_position_from_row(mock_row)
        
        assert result is not None
        assert result["instrument"] == "Micro E-mini S&P 500 Sep 25"
        assert result["side"] == "BUY"
        assert result["quantity"] == Decimal("2.0")
        assert result["row_element"] == mock_row
    
    def test_extract_plus500_order_from_row(self, trading_client):
        """Test order data extraction from DOM row"""
        # Mock row element with order data
        mock_row = Mock(spec=WebElement)
        
        # Mock order elements
        mock_name = Mock(spec=WebElement)
        mock_action = Mock(spec=WebElement)
        mock_amount = Mock(spec=WebElement)
        mock_limit_stop = Mock(spec=WebElement)
        
        def mock_find_element(by, xpath):
            if "name" in xpath:
                return mock_name
            elif "action" in xpath:
                return mock_action
            elif "amount" in xpath:
                return mock_amount
            elif "limit-stop" in xpath:
                return mock_limit_stop
            raise Exception("Element not found")
        
        mock_row.find_element = Mock(side_effect=mock_find_element)
        
        # Mock text extraction
        trading_client.element_detector.extract_text_safe = Mock()
        trading_client.element_detector.extract_text_safe.side_effect = [
            "Micro E-mini S&P 500 Sep 25",  # instrument
            "SELL",  # side
            "2 Contracts",  # amount
            "Limit: 6,441.00"  # limit-stop
        ]
        trading_client.utils.extract_number_from_text = Mock()
        trading_client.utils.extract_number_from_text.side_effect = [2.0, 6441.0]
        
        result = trading_client._extract_plus500_order_from_row(mock_row)
        
        assert result is not None
        assert result["instrument"] == "Micro E-mini S&P 500 Sep 25"
        assert result["side"] == "SELL"
        assert result["quantity"] == Decimal("2.0")
        assert result["order_type"] == "LIMIT"
        assert result["price"] == Decimal("6441.0")
    
    def test_place_market_order_with_trailing_stop(self, trading_client):
        """Test market order placement with trailing stop"""
        # Mock navigation and element finding
        trading_client._navigate_to_instrument = Mock()
        trading_client._select_order_type = Mock()
        trading_client._set_quantity = Mock()
        trading_client._set_trailing_stop_dynamic = Mock(return_value=True)
        trading_client._submit_order = Mock(return_value={"success": True, "order_id": "12345"})
        
        # Mock button finding and clicking
        mock_button = Mock(spec=WebElement)
        trading_client.element_detector.find_element_robust = Mock(return_value=mock_button)
        trading_client.utils.human_like_click = Mock()
        
        result = trading_client.place_market_order(
            instrument_id="MESU5",
            side="BUY",
            quantity=Decimal("2"),
            trailing_stop=True,
            trailing_stop_percentage=Decimal("0.2")
        )
        
        assert result["success"] is True
        trading_client._navigate_to_instrument.assert_called_once_with("MESU5")
        trading_client._select_order_type.assert_called_once_with("MARKET")
        trading_client._set_quantity.assert_called_once_with(Decimal("2"))
        trading_client._set_trailing_stop_dynamic.assert_called_once_with("MESU5", Decimal("0.2"))
    
    def test_get_positions(self, trading_client):
        """Test positions extraction"""
        # Mock navigation
        trading_client._navigate_to_positions = Mock()
        
        # Mock container and rows
        mock_container = Mock(spec=WebElement)
        mock_rows = [Mock(spec=WebElement), Mock(spec=WebElement)]
        
        trading_client.element_detector.find_element_robust = Mock(return_value=mock_container)
        trading_client.element_detector.find_elements_robust = Mock(return_value=mock_rows)
        
        # Mock position extraction
        mock_position_data = {
            "id": "pos_123",
            "instrument": "MESU5",
            "side": "BUY",
            "quantity": Decimal("2")
        }
        trading_client._extract_plus500_position_from_row = Mock(return_value=mock_position_data)
        
        result = trading_client.get_positions()
        
        assert len(result) == 2
        assert all(pos["instrument"] == "MESU5" for pos in result)
        trading_client._navigate_to_positions.assert_called_once()
    
    def test_close_position(self, trading_client):
        """Test position closure"""
        # Mock position finding
        mock_position_data = {
            "id": "pos_123",
            "instrument": "MESU5",
            "row_element": Mock(spec=WebElement)
        }
        trading_client._find_position_by_identifier = Mock(return_value=mock_position_data)
        
        # Mock close button
        mock_close_button = Mock(spec=WebElement)
        trading_client.element_detector.find_element_robust = Mock(return_value=mock_close_button)
        trading_client.utils.human_like_click = Mock()
        trading_client._confirm_position_close = Mock()
        
        # Mock verification (position not found after close)
        trading_client._find_position_by_identifier.side_effect = [mock_position_data, None]
        
        result = trading_client.close_position("pos_123")
        
        assert result is True
        # Note: human_like_click is called twice - once in click, once in _navigate_to_positions
        assert trading_client.utils.human_like_click.call_count >= 1
        trading_client._confirm_position_close.assert_called_once()
    
    def test_get_orders(self, trading_client):
        """Test orders extraction"""
        # Mock navigation
        trading_client._navigate_to_orders = Mock()
        
        # Mock container and rows
        mock_container = Mock(spec=WebElement)
        mock_rows = [Mock(spec=WebElement)]
        
        trading_client.element_detector.find_element_robust = Mock(return_value=mock_container)
        trading_client.element_detector.find_elements_robust = Mock(return_value=mock_rows)
        
        # Mock order extraction
        mock_order_data = {
            "id": "order_123",
            "instrument": "MESU5",
            "side": "SELL",
            "quantity": Decimal("2"),
            "order_type": "LIMIT",
            "price": Decimal("6441.0")
        }
        trading_client._extract_plus500_order_from_row = Mock(return_value=mock_order_data)
        
        result = trading_client.get_orders()
        
        assert len(result) == 1
        assert result[0]["instrument"] == "MESU5"
        assert result[0]["order_type"] == "LIMIT"
        trading_client._navigate_to_orders.assert_called_once()
    
    def test_cancel_order(self, trading_client):
        """Test order cancellation"""
        # Mock order finding
        mock_order_data = {
            "id": "order_123",
            "instrument": "MESU5",
            "row_element": Mock(spec=WebElement)
        }
        trading_client._find_order_by_identifier = Mock(return_value=mock_order_data)
        
        # Mock cancel button
        mock_cancel_button = Mock(spec=WebElement)
        trading_client.element_detector.find_element_robust = Mock(return_value=mock_cancel_button)
        trading_client.utils.human_like_click = Mock()
        trading_client._confirm_order_cancellation = Mock()
        
        # Mock verification (order not found after cancel)
        trading_client._find_order_by_identifier.side_effect = [mock_order_data, None]
        
        result = trading_client.cancel_order("order_123")
        
        assert result is True
        # Note: human_like_click is called multiple times - navigation and button click
        assert trading_client.utils.human_like_click.call_count >= 1
        trading_client._confirm_order_cancellation.assert_called_once()
    
    def test_edit_order(self, trading_client):
        """Test order editing"""
        # Mock order finding
        mock_order_data = {
            "id": "order_123",
            "instrument": "MESU5",
            "row_element": Mock(spec=WebElement)
        }
        trading_client._find_order_by_identifier = Mock(return_value=mock_order_data)
        
        # Mock edit button
        mock_edit_button = Mock(spec=WebElement)
        trading_client.element_detector.find_element_robust = Mock(return_value=mock_edit_button)
        trading_client.utils.human_like_click = Mock()
        
        # Mock parameter setting methods
        trading_client._set_quantity = Mock()
        trading_client._set_limit_price = Mock()
        trading_client._confirm_order_edit = Mock()
        
        result = trading_client.edit_order(
            "order_123", 
            new_quantity=Decimal("3"), 
            new_price=Decimal("6450.0")
        )
        
        assert result is True
        trading_client._set_quantity.assert_called_once_with(Decimal("3"))
        trading_client._set_limit_price.assert_called_once_with(Decimal("6450.0"))
        trading_client._confirm_order_edit.assert_called_once()
    
    def test_is_switch_enabled(self, trading_client):
        """Test switch enabled detection"""
        # Test active class
        mock_element = Mock(spec=WebElement)
        mock_element.get_attribute.return_value = "switch active"
        assert trading_client._is_switch_enabled(mock_element) is True
        
        # Test checked attribute
        mock_element2 = Mock(spec=WebElement)
        mock_element2.get_attribute.side_effect = lambda attr: "true" if attr == "checked" else ""
        assert trading_client._is_switch_enabled(mock_element2) is True
        
        # Test aria-checked
        mock_element3 = Mock(spec=WebElement)
        mock_element3.get_attribute.side_effect = lambda attr: "true" if attr == "aria-checked" else ""
        assert trading_client._is_switch_enabled(mock_element3) is True
        
        # Test not enabled
        mock_element4 = Mock(spec=WebElement)
        mock_element4.get_attribute.return_value = ""
        assert trading_client._is_switch_enabled(mock_element4) is False
    
    def test_close_all_positions(self, trading_client):
        """Test closing all positions"""
        # Mock positions
        mock_positions = [
            {"id": "pos_1", "instrument": "MESU5"},
            {"id": "pos_2", "instrument": "MESU6"}
        ]
        trading_client.get_positions = Mock(return_value=mock_positions)
        trading_client.close_position = Mock(return_value=True)
        
        result = trading_client.close_all_positions()
        
        assert len(result) == 2
        assert all(r["success"] for r in result)
        assert trading_client.close_position.call_count == 2
    
    def test_cancel_all_orders(self, trading_client):
        """Test cancelling all orders"""
        # Mock orders
        mock_orders = [
            {"id": "order_1", "instrument": "MESU5"},
            {"id": "order_2", "instrument": "MESU6"}
        ]
        trading_client.get_orders = Mock(return_value=mock_orders)
        trading_client.cancel_order = Mock(return_value=True)
        
        result = trading_client.cancel_all_orders()
        
        assert len(result) == 2
        assert all(r["success"] for r in result)
        assert trading_client.cancel_order.call_count == 2
    
    def test_error_handling(self, trading_client):
        """Test error handling in various scenarios"""
        # Test position not found - expect False return, not exception
        trading_client._find_position_by_identifier = Mock(return_value=None)
        trading_client._navigate_to_positions = Mock()
        
        result = trading_client.close_position("nonexistent")
        assert result is False
        
        # Test order not found - expect False return, not exception  
        trading_client._find_order_by_identifier = Mock(return_value=None)
        trading_client._navigate_to_orders = Mock()
        
        result = trading_client.cancel_order("nonexistent")
        assert result is False
        
        # Test missing close button
        trading_client._find_position_by_identifier = Mock(return_value={"row_element": Mock()})
        trading_client.element_detector.find_element_robust = Mock(return_value=None)
        mock_row = Mock()
        mock_row.find_element = Mock(side_effect=Exception("Not found"))
        trading_client._find_position_by_identifier = Mock(return_value={"row_element": mock_row})
        
        result = trading_client.close_position("pos_123")
        assert result is False


class TestBrowserManagerEnhancements:
    """Test enhanced browser manager functionality"""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration"""
        config = Mock()
        config.webdriver_config = {
            "browser": "chrome",
            "headless": False,
            "stealth_mode": True,
            "window_size": (1920, 1080)
        }
        return config
    
    @pytest.fixture
    def browser_manager(self, mock_config):
        """Create browser manager"""
        return BrowserManager(mock_config)
    
    def test_edge_browser_support(self, browser_manager):
        """Test Edge browser configuration"""
        browser_manager.browser_type = "edge"
        
        with patch('plus500us_client.webdriver.browser_manager.webdriver.Edge') as mock_edge:
            with patch('plus500us_client.webdriver.browser_manager.EdgeService'):
                browser_manager._start_edge()
                mock_edge.assert_called_once()
    
    def test_account_mode_detection(self, browser_manager):
        """Test account mode detection"""
        # Mock driver and elements
        mock_driver = Mock()
        browser_manager.driver = mock_driver
        
        # Mock active element
        mock_active_element = Mock()
        mock_active_element.get_attribute.return_value = "active"
        
        with patch('plus500us_client.webdriver.browser_manager.ElementDetector') as mock_detector_class:
            mock_detector = Mock()
            mock_detector.find_element_robust.return_value = mock_active_element
            mock_detector.extract_text_safe.return_value = "Demo Mode"
            mock_detector_class.return_value = mock_detector
            
            result = browser_manager.get_current_account_mode()
            assert result == "demo"
    
    def test_account_switching(self, browser_manager):
        """Test account mode switching"""
        # Mock driver and elements
        mock_driver = Mock()
        browser_manager.driver = mock_driver
        
        with patch.multiple(
            browser_manager,
            get_current_account_mode=Mock(side_effect=["live", "demo"]),
        ):
            with patch('plus500us_client.webdriver.browser_manager.ElementDetector') as mock_detector_class:
                with patch('plus500us_client.webdriver.browser_manager.WebDriverUtils') as mock_utils_class:
                    mock_detector = Mock()
                    mock_utils = Mock()
                    mock_switch_element = Mock()
                    
                    mock_detector.find_element_robust.return_value = mock_switch_element
                    mock_detector_class.return_value = mock_detector
                    mock_utils_class.return_value = mock_utils
                    
                    result = browser_manager.switch_account_mode("demo")
                    assert result is True
                    mock_utils.human_like_click.assert_called_once()
    
    @pytest.mark.parametrize("browser_type", ["chrome", "firefox", "edge"])
    def test_multiple_browser_support(self, mock_config, browser_type):
        """Test support for multiple browsers"""
        mock_config.webdriver_config["browser"] = browser_type
        browser_manager = BrowserManager(mock_config)
        
        assert browser_manager.browser_type == browser_type
        
        # Test that browser type is validated
        with patch.object(browser_manager, f'_start_{browser_type}') as mock_start:
            with patch.object(browser_manager, 'driver', Mock()):
                browser_manager.start_browser()
                mock_start.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])