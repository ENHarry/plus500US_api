"""
Tests for WebDriver Trading Automation component
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

from plus500us_client.webdriver.trading_automation import WebDriverTradingClient
from plus500us_client.errors import OrderRejectError, ValidationError


class TestWebDriverTradingClient:
    """Test WebDriverTradingClient functionality"""
    
    def test_trading_client_initialization(self, test_config, mock_browser_manager):
        """Test WebDriverTradingClient initializes correctly"""
        client = WebDriverTradingClient(test_config, mock_browser_manager)
        
        assert client.config == test_config
        assert client.browser_manager == mock_browser_manager
        assert client.driver is None
        assert client.element_detector is None
    
    def test_trading_client_initialize_with_driver(self, test_config, mock_driver):
        """Test initialize with provided driver"""
        client = WebDriverTradingClient(test_config)
        client.initialize(mock_driver)
        
        assert client.driver == mock_driver
        assert client.element_detector is not None
    
    def test_trading_client_initialize_with_browser_manager(self, test_config, mock_browser_manager):
        """Test initialize with browser manager"""
        client = WebDriverTradingClient(test_config, mock_browser_manager)
        client.initialize()
        
        assert client.driver == mock_browser_manager.get_driver()
        assert client.element_detector is not None
    
    def test_initialize_without_driver_or_manager_raises_error(self, test_config):
        """Test initialize raises error without driver or manager"""
        client = WebDriverTradingClient(test_config)
        
        with pytest.raises(RuntimeError, match="No WebDriver available"):
            client.initialize()
    
    def test_place_market_order_success(self, mock_webdriver_trading_client, mock_element_detector):
        """Test successful market order placement"""
        # Setup mocks
        mock_button = Mock()
        mock_element_detector.find_element_robust.return_value = mock_button
        
        client = mock_webdriver_trading_client
        client._navigate_to_instrument = Mock()
        client._select_order_type = Mock()
        client._set_quantity = Mock()
        client._submit_order = Mock(return_value={"success": True, "order_id": "12345"})
        
        # Execute
        result = client.place_market_order("TEST_INSTRUMENT", "BUY", Decimal("10"))
        
        # Verify
        assert result["success"] is True
        assert result["order_id"] == "12345"
        client._navigate_to_instrument.assert_called_with("TEST_INSTRUMENT")
        client._select_order_type.assert_called_with("MARKET")
        client._set_quantity.assert_called_with(Decimal("10"))
    
    def test_place_market_order_with_stop_loss_and_take_profit(self, mock_webdriver_trading_client):
        """Test market order with SL/TP"""
        client = mock_webdriver_trading_client
        client._navigate_to_instrument = Mock()
        client._select_order_type = Mock()
        client._set_quantity = Mock()
        client._set_stop_loss = Mock()
        client._set_take_profit = Mock()
        client._submit_order = Mock(return_value={"success": True, "order_id": "12345"})
        
        mock_button = Mock()
        client.element_detector.find_element_robust.return_value = mock_button
        
        result = client.place_market_order(
            "TEST_INSTRUMENT", "BUY", Decimal("10"),
            stop_loss=Decimal("95.0"), take_profit=Decimal("105.0")
        )
        
        assert result["success"] is True
        client._set_stop_loss.assert_called_with(Decimal("95.0"))
        client._set_take_profit.assert_called_with(Decimal("105.0"))
    
    def test_place_market_order_button_not_found(self, mock_webdriver_trading_client):
        """Test market order fails when button not found"""
        client = mock_webdriver_trading_client
        client._navigate_to_instrument = Mock()
        client._select_order_type = Mock()
        client.element_detector.find_element_robust.return_value = None
        
        with pytest.raises(OrderRejectError, match="Could not find BUY button"):
            client.place_market_order("TEST_INSTRUMENT", "BUY", Decimal("10"))
    
    def test_place_limit_order_success(self, mock_webdriver_trading_client):
        """Test successful limit order placement"""
        client = mock_webdriver_trading_client
        client._navigate_to_instrument = Mock()
        client._select_order_type = Mock()
        client._set_limit_price = Mock()
        client._set_quantity = Mock()
        client._submit_order = Mock(return_value={"success": True, "order_id": "54321"})
        
        mock_button = Mock()
        client.element_detector.find_element_robust.return_value = mock_button
        
        result = client.place_limit_order(
            "TEST_INSTRUMENT", "SELL", Decimal("5"), Decimal("102.50")
        )
        
        assert result["success"] is True
        assert result["order_id"] == "54321"
        client._select_order_type.assert_called_with("LIMIT")
        client._set_limit_price.assert_called_with(Decimal("102.50"))
    
    def test_place_stop_order_success(self, mock_webdriver_trading_client):
        """Test successful stop order placement"""
        client = mock_webdriver_trading_client
        client._navigate_to_instrument = Mock()
        client._select_order_type = Mock()
        client._set_stop_price = Mock()
        client._set_quantity = Mock()
        client._submit_order = Mock(return_value={"success": True, "order_id": "67890"})
        
        mock_button = Mock()
        client.element_detector.find_element_robust.return_value = mock_button
        
        result = client.place_stop_order(
            "TEST_INSTRUMENT", "BUY", Decimal("3"), Decimal("98.00")
        )
        
        assert result["success"] is True
        client._select_order_type.assert_called_with("STOP")
        client._set_stop_price.assert_called_with(Decimal("98.00"))
    
    def test_place_bracket_order_market(self, mock_webdriver_trading_client):
        """Test bracket order with market execution"""
        client = mock_webdriver_trading_client
        client.place_market_order = Mock(return_value={"success": True, "order_id": "11111"})
        
        result = client.place_bracket_order(
            "TEST_INSTRUMENT", "BUY", Decimal("8"), "MARKET",
            stop_loss=Decimal("95.0"), take_profit=Decimal("105.0")
        )
        
        assert result["success"] is True
        client.place_market_order.assert_called_with(
            "TEST_INSTRUMENT", "BUY", Decimal("8"), Decimal("95.0"), Decimal("105.0")
        )
    
    def test_place_bracket_order_limit(self, mock_webdriver_trading_client):
        """Test bracket order with limit execution"""
        client = mock_webdriver_trading_client
        client.place_limit_order = Mock(return_value={"success": True, "order_id": "22222"})
        
        result = client.place_bracket_order(
            "TEST_INSTRUMENT", "SELL", Decimal("6"), "LIMIT", 
            limit_price=Decimal("101.00"), stop_loss=Decimal("106.0"), take_profit=Decimal("96.0")
        )
        
        assert result["success"] is True
        client.place_limit_order.assert_called_with(
            "TEST_INSTRUMENT", "SELL", Decimal("6"), Decimal("101.00"), 
            Decimal("106.0"), Decimal("96.0")
        )
    
    def test_get_positions_success(self, mock_webdriver_trading_client, sample_position_data):
        """Test successful position retrieval"""
        client = mock_webdriver_trading_client
        client._navigate_to_positions = Mock()
        
        mock_table = Mock()
        mock_row = Mock()
        mock_table.find_elements.return_value = [mock_row]
        client.element_detector.find_element_robust.return_value = mock_table
        client._extract_position_from_row = Mock(return_value=sample_position_data)
        
        positions = client.get_positions()
        
        assert len(positions) == 1
        assert positions[0] == sample_position_data
        client._navigate_to_positions.assert_called_once()
    
    def test_get_positions_no_table(self, mock_webdriver_trading_client):
        """Test get_positions when no table found"""
        client = mock_webdriver_trading_client
        client._navigate_to_positions = Mock()
        client.element_detector.find_element_robust.return_value = None
        
        positions = client.get_positions()
        
        assert positions == []
    
    def test_close_position_success(self, mock_webdriver_trading_client):
        """Test successful position closure"""
        client = mock_webdriver_trading_client
        client._navigate_to_positions = Mock()
        client._find_position_row = Mock(return_value=Mock())
        client._confirm_position_close = Mock()
        
        mock_close_button = Mock()
        client._find_position_row().find_element.return_value = mock_close_button
        
        result = client.close_position("TEST_POSITION_123")
        
        assert result is True
        client._find_position_row.assert_called_with("TEST_POSITION_123")
    
    def test_close_position_partial(self, mock_webdriver_trading_client):
        """Test partial position closure"""
        client = mock_webdriver_trading_client
        client._navigate_to_positions = Mock()
        client._find_position_row = Mock(return_value=Mock())
        client._set_partial_close_quantity = Mock()
        client._confirm_position_close = Mock()
        
        mock_close_button = Mock()
        client._find_position_row().find_element.return_value = mock_close_button
        
        result = client.close_position("TEST_POSITION_123", Decimal("5"))
        
        assert result is True
        client._set_partial_close_quantity.assert_called_with(Decimal("5"))
    
    def test_close_position_not_found(self, mock_webdriver_trading_client):
        """Test close_position when position not found"""
        client = mock_webdriver_trading_client
        client._navigate_to_positions = Mock()
        client._find_position_row = Mock(return_value=None)
        
        result = client.close_position("NONEXISTENT_POSITION")
        
        assert result is False
    
    def test_set_stop_loss_success(self, mock_webdriver_trading_client):
        """Test successful stop loss setting"""
        client = mock_webdriver_trading_client
        client._find_position_row = Mock(return_value=Mock())
        client._confirm_risk_management_change = Mock()
        
        mock_sl_input = Mock()
        client.element_detector.find_element_robust.return_value = mock_sl_input
        
        with patch.object(client.utils, 'human_like_type') as mock_type:
            result = client.set_stop_loss("TEST_POSITION_123", Decimal("95.00"))
            
            assert result is True
            mock_type.assert_called_with(
                client.driver, mock_sl_input, "95.00"
            )
    
    def test_set_take_profit_success(self, mock_webdriver_trading_client):
        """Test successful take profit setting"""
        client = mock_webdriver_trading_client
        client._find_position_row = Mock(return_value=Mock())
        client._confirm_risk_management_change = Mock()
        
        mock_tp_input = Mock()
        client.element_detector.find_element_robust.return_value = mock_tp_input
        
        with patch.object(client.utils, 'human_like_type') as mock_type:
            result = client.set_take_profit("TEST_POSITION_123", Decimal("105.00"))
            
            assert result is True
            mock_type.assert_called_with(
                client.driver, mock_tp_input, "105.00"
            )
    
    def test_execute_partial_take_profit_success(self, mock_webdriver_trading_client):
        """Test successful partial take profit execution"""
        client = mock_webdriver_trading_client
        
        # Mock position with sufficient quantity
        position_data = {
            "id": "TEST_POSITION_123",
            "quantity": "10",
            "instrument": "TEST_INSTRUMENT"
        }
        client.get_positions = Mock(return_value=[position_data])
        client.close_position = Mock(return_value=True)
        
        result = client.execute_partial_take_profit("TEST_POSITION_123", Decimal("3"))
        
        assert result is True
        client.close_position.assert_called_with("TEST_POSITION_123", Decimal("3"))
    
    def test_execute_partial_take_profit_insufficient_quantity(self, mock_webdriver_trading_client):
        """Test partial take profit with insufficient quantity"""
        client = mock_webdriver_trading_client
        
        # Mock position with insufficient quantity
        position_data = {
            "id": "TEST_POSITION_123",
            "quantity": "1",  # Only 1 contract
            "instrument": "TEST_INSTRUMENT"
        }
        client.get_positions = Mock(return_value=[position_data])
        
        with pytest.raises(ValidationError, match="Partial take profit requires position > 1 contract"):
            client.execute_partial_take_profit("TEST_POSITION_123", Decimal("0.5"))
    
    def test_execute_partial_take_profit_leaves_insufficient_remaining(self, mock_webdriver_trading_client):
        """Test partial take profit that would leave insufficient remaining"""
        client = mock_webdriver_trading_client
        
        # Mock position 
        position_data = {
            "id": "TEST_POSITION_123",
            "quantity": "3",
            "instrument": "TEST_INSTRUMENT"
        }
        client.get_positions = Mock(return_value=[position_data])
        
        with pytest.raises(ValidationError, match="Partial TP would leave position with 0.5 contracts"):
            client.execute_partial_take_profit("TEST_POSITION_123", Decimal("2.5"))
    
    def test_execute_partial_take_profit_equal_to_position_size(self, mock_webdriver_trading_client):
        """Test partial take profit equal to position size"""
        client = mock_webdriver_trading_client
        
        position_data = {
            "id": "TEST_POSITION_123", 
            "quantity": "5",
            "instrument": "TEST_INSTRUMENT"
        }
        client.get_positions = Mock(return_value=[position_data])
        
        with pytest.raises(ValidationError, match="Partial quantity cannot be equal to or greater"):
            client.execute_partial_take_profit("TEST_POSITION_123", Decimal("5"))
    
    def test_execute_partial_take_profit_position_not_found(self, mock_webdriver_trading_client):
        """Test partial take profit when position not found"""
        client = mock_webdriver_trading_client
        client.get_positions = Mock(return_value=[])
        
        with pytest.raises(ValidationError, match="Position NONEXISTENT not found"):
            client.execute_partial_take_profit("NONEXISTENT", Decimal("2"))
    
    def test_monitor_position_pnl_success(self, mock_webdriver_trading_client):
        """Test successful P&L monitoring"""
        client = mock_webdriver_trading_client
        
        mock_position_row = Mock()
        mock_pnl_cell = Mock()
        mock_position_row.find_element.return_value = mock_pnl_cell
        client._find_position_row = Mock(return_value=mock_position_row)
        client.element_detector.extract_text_safe.return_value = "$125.50"
        client.utils.extract_number_from_text.return_value = 125.50
        
        pnl = client.monitor_position_pnl("TEST_POSITION_123")
        
        assert pnl == Decimal("125.50")
    
    def test_monitor_position_pnl_position_not_found(self, mock_webdriver_trading_client):
        """Test P&L monitoring when position not found"""
        client = mock_webdriver_trading_client
        client._find_position_row = Mock(return_value=None)
        
        pnl = client.monitor_position_pnl("NONEXISTENT")
        
        assert pnl is None
    
    def test_navigate_to_instrument(self, mock_webdriver_trading_client):
        """Test navigation to instrument"""
        client = mock_webdriver_trading_client
        
        mock_search_input = Mock()
        mock_instrument_link = Mock()
        client.element_detector.find_element_robust.return_value = mock_search_input
        client.driver.find_element.return_value = mock_instrument_link
        
        with patch.object(client.utils, 'human_like_type') as mock_type, \
             patch.object(client.utils, 'human_like_click') as mock_click:
            
            client._navigate_to_instrument("TEST_INSTRUMENT")
            
            mock_type.assert_called_with(
                client.driver, mock_search_input, "TEST_INSTRUMENT"
            )
            mock_click.assert_called_with(
                client.driver, mock_instrument_link
            )
    
    def test_submit_order_success(self, mock_webdriver_trading_client):
        """Test successful order submission"""
        client = mock_webdriver_trading_client
        
        mock_confirm_button = Mock()
        mock_success_msg = Mock()
        client.element_detector.find_element_robust.side_effect = [
            mock_confirm_button,  # Confirm button
            mock_success_msg,     # Success message
            None                  # No error message
        ]
        client._extract_order_id = Mock(return_value="ORDER_123")
        
        with patch.object(client.utils, 'human_like_click') as mock_click:
            result = client._submit_order()
            
            assert result["success"] is True
            assert result["order_id"] == "ORDER_123"
            mock_click.assert_called_with(client.driver, mock_confirm_button)
    
    def test_submit_order_button_not_found(self, mock_webdriver_trading_client):
        """Test order submission when confirm button not found"""
        client = mock_webdriver_trading_client
        client.element_detector.find_element_robust.return_value = None
        
        with pytest.raises(OrderRejectError, match="Could not find order confirmation button"):
            client._submit_order()
    
    def test_submit_order_error_message(self, mock_webdriver_trading_client):
        """Test order submission with error message"""
        client = mock_webdriver_trading_client
        
        mock_confirm_button = Mock()
        mock_error_msg = Mock()
        client.element_detector.find_element_robust.side_effect = [
            mock_confirm_button,  # Confirm button
            None,                 # No success message
            mock_error_msg        # Error message
        ]
        client.element_detector.extract_text_safe.return_value = "Insufficient funds"
        
        with pytest.raises(OrderRejectError, match="Order rejected: Insufficient funds"):
            client._submit_order()


@pytest.mark.webdriver
class TestWebDriverTradingClientIntegration:
    """Integration tests for WebDriverTradingClient"""
    
    @pytest.mark.slow
    def test_full_trading_workflow_simulation(self, real_browser_manager, test_config, browser_available):
        """Test complete trading workflow simulation"""
        if not browser_available:
            pytest.skip("Browser not available")
        
        driver = real_browser_manager.get_driver()
        client = WebDriverTradingClient(test_config, real_browser_manager)
        client.initialize()
        
        # Create a mock trading interface
        html = """
        <html><body>
        <input id="instrument-search" placeholder="Search instrument"/>
        <button id="buy-btn">BUY</button>
        <button id="sell-btn">SELL</button>
        <input id="quantity" type="number"/>
        <input id="price" type="number"/>
        <button id="confirm-order">Confirm Order</button>
        <div id="success-msg" style="display:none">Order placed successfully</div>
        </body></html>
        """
        driver.get(f"data:text/html,{html}")
        
        # Test that elements can be found
        search_input = client.element_detector.find_element_robust({
            'xpath': ["//input[@id='instrument-search']"],
            'css': ["#instrument-search"]
        })
        
        assert search_input is not None
        
        buy_button = client.element_detector.find_element_robust({
            'xpath': ["//button[@id='buy-btn']"],
            'css': ["#buy-btn"]
        })
        
        assert buy_button is not None
        assert client.element_detector.extract_text_safe(buy_button) == "BUY"