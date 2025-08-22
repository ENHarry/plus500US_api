"""
Tests for Plus500US-specific selectors and element detection
"""

import pytest
from plus500us_client.webdriver.selectors import Plus500Selectors


class TestPlus500Selectors:
    """Test Plus500US-specific selector functionality"""
    
    def test_navigation_selectors(self):
        """Test navigation selector definitions"""
        selectors = Plus500Selectors()
        
        # Test positions navigation
        assert hasattr(selectors, 'POSITIONS_NAV')
        assert 'xpath' in selectors.POSITIONS_NAV
        assert 'css' in selectors.POSITIONS_NAV
        assert "#positionsFuturesNav" in selectors.POSITIONS_NAV['css']
        
        # Test orders navigation
        assert hasattr(selectors, 'ORDERS_NAV')
        assert 'xpath' in selectors.ORDERS_NAV
        assert 'css' in selectors.ORDERS_NAV
        assert "#ordersFuturesNav" in selectors.ORDERS_NAV['css']
    
    def test_table_selectors(self):
        """Test table container selectors"""
        selectors = Plus500Selectors()
        
        # Test positions table
        assert hasattr(selectors, 'POSITIONS_TABLE_CONTAINER')
        assert ".futures-positions" in selectors.POSITIONS_TABLE_CONTAINER['css']
        assert ".section-table" in selectors.POSITIONS_TABLE_CONTAINER['css']
        
        # Test orders table
        assert hasattr(selectors, 'ORDERS_TABLE_CONTAINER')
        assert ".futures-orders" in selectors.ORDERS_TABLE_CONTAINER['css']
        
        # Test row selectors
        assert hasattr(selectors, 'POSITION_ROWS')
        assert hasattr(selectors, 'ORDER_ROWS')
    
    def test_trading_interface_selectors(self):
        """Test trading interface selectors"""
        selectors = Plus500Selectors()
        
        # Test trading sidebar
        assert hasattr(selectors, 'TRADING_SIDEBAR')
        assert ".sidebar-trade" in selectors.TRADING_SIDEBAR['css']
        
        # Test buy/sell selector
        assert hasattr(selectors, 'BUY_SELL_SELECTOR')
        assert ".buysell-selection select" in selectors.BUY_SELL_SELECTOR['css']
        
        # Test current price display
        assert hasattr(selectors, 'CURRENT_PRICE_DISPLAY')
        assert ".data .rate" in selectors.CURRENT_PRICE_DISPLAY['css']
    
    def test_risk_management_selectors(self):
        """Test risk management selectors"""
        selectors = Plus500Selectors()
        
        # Test trailing stop selectors
        assert hasattr(selectors, 'TRAILING_STOP_SWITCH')
        assert "plus500-switch[data-testid='trailingStop']" in selectors.TRAILING_STOP_SWITCH['css']
        
        assert hasattr(selectors, 'TRAILING_STOP_INPUT')
        xpath_contains_testid = any(
            "trailingStop" in xpath for xpath in selectors.TRAILING_STOP_INPUT['xpath']
        )
        assert xpath_contains_testid
        
        # Test stop loss and take profit
        assert hasattr(selectors, 'STOP_LOSS_SWITCH')
        assert "plus500-switch[data-testid='stopLoss']" in selectors.STOP_LOSS_SWITCH['css']
        
        assert hasattr(selectors, 'TAKE_PROFIT_SWITCH')
        assert "plus500-switch[data-testid='takeProfit']" in selectors.TAKE_PROFIT_SWITCH['css']
    
    def test_action_selectors(self):
        """Test action button selectors"""
        selectors = Plus500Selectors()
        
        # Test order placement
        assert hasattr(selectors, 'PLACE_ORDER_BUTTON')
        assert "#trade-button" in selectors.PLACE_ORDER_BUTTON['css']
        
        # Test position management
        assert hasattr(selectors, 'POSITION_CLOSE_BUTTON')
        assert hasattr(selectors, 'POSITION_EDIT_BUTTON')
        
        # Test order management
        assert hasattr(selectors, 'ORDER_CANCEL_BUTTON')
        assert hasattr(selectors, 'ORDER_EDIT_BUTTON')
    
    def test_account_management_selectors(self):
        """Test account management selectors"""
        selectors = Plus500Selectors()
        
        # Test account switch control
        assert hasattr(selectors, 'ACCOUNT_SWITCH_CONTROL')
        assert "#switchModeSubNav" in selectors.ACCOUNT_SWITCH_CONTROL['css']
        
        # Test account type detection
        assert hasattr(selectors, 'ACTIVE_ACCOUNT_TYPE')
        assert hasattr(selectors, 'DEMO_MODE_SPAN')
        assert hasattr(selectors, 'REAL_MODE_SPAN')
    
    def test_account_balance_selectors(self):
        """Test account balance and margin selectors"""
        selectors = Plus500Selectors()
        
        # Test equity value
        assert hasattr(selectors, 'EQUITY_VALUE')
        xpath_contains_automation = any(
            "automation='equity'" in xpath for xpath in selectors.EQUITY_VALUE['xpath']
        )
        assert xpath_contains_automation
        
        # Test total P&L
        assert hasattr(selectors, 'TOTAL_PNL')
        xpath_contains_automation = any(
            "automation='total-positions-pl'" in xpath for xpath in selectors.TOTAL_PNL['xpath']
        )
        assert xpath_contains_automation
        
        # Test margin available
        assert hasattr(selectors, 'LIVE_MARGIN_AVAILABLE')
        assert hasattr(selectors, 'FULL_MARGIN_AVAILABLE')
    
    def test_instrument_discovery_selectors(self):
        """Test instrument discovery selectors"""
        selectors = Plus500Selectors()
        
        # Test categories container
        assert hasattr(selectors, 'INSTRUMENT_CATEGORIES_CONTAINER')
        assert "#categories" in selectors.INSTRUMENT_CATEGORIES_CONTAINER['css']
        
        # Test category links
        assert hasattr(selectors, 'INSTRUMENT_CATEGORY_LINKS')
        assert hasattr(selectors, 'SELECTED_CATEGORY')
        
        # Test instruments table
        assert hasattr(selectors, 'INSTRUMENTS_TABLE_CONTAINER')
        assert "#instrumentsTable" in selectors.INSTRUMENTS_TABLE_CONTAINER['css']
        
        # Test instrument rows and details
        assert hasattr(selectors, 'INSTRUMENT_ROWS')
        assert hasattr(selectors, 'INSTRUMENT_NAME')
        assert hasattr(selectors, 'INSTRUMENT_PRICES')
        assert hasattr(selectors, 'INSTRUMENT_INFO_BUTTON')
    
    def test_closed_positions_selectors(self):
        """Test closed positions and P&L analysis selectors"""
        selectors = Plus500Selectors()
        
        # Test closed positions navigation
        assert hasattr(selectors, 'CLOSED_POSITIONS_NAV')
        assert "#closedPositionsNav" in selectors.CLOSED_POSITIONS_NAV['css']
        
        # Test trade history table
        assert hasattr(selectors, 'TRADE_HISTORY_TABLE')
        assert ".futures-closed-positions" in selectors.TRADE_HISTORY_TABLE['css']
        
        # Test trade history rows and data
        assert hasattr(selectors, 'TRADE_HISTORY_ROWS')
        assert hasattr(selectors, 'TRADE_DATE')
        assert hasattr(selectors, 'TRADE_ACTION')
        assert hasattr(selectors, 'TRADE_AMOUNT')
        assert hasattr(selectors, 'TRADE_INSTRUMENT')
        assert hasattr(selectors, 'TRADE_OPEN_PRICE')
        assert hasattr(selectors, 'TRADE_CLOSE_PRICE')
        assert hasattr(selectors, 'TRADE_PNL')
    
    def test_date_filter_selectors(self):
        """Test date filter selectors"""
        selectors = Plus500Selectors()
        
        # Test date filter inputs
        assert hasattr(selectors, 'DATE_FILTER_FROM')
        assert hasattr(selectors, 'DATE_FILTER_TO')
        assert hasattr(selectors, 'DATE_FILTER_SUBMIT')
        
        # Verify submit button selector
        assert "#date-filter-submit" in selectors.DATE_FILTER_SUBMIT['css']
    
    def test_dynamic_selector_method(self):
        """Test dynamic selector generation"""
        base_selector = "//tr[contains(@data-position-id, '{position_id}')]"
        result = Plus500Selectors.get_dynamic_selector(base_selector, position_id="123")
        expected = "//tr[contains(@data-position-id, '123')]"
        assert result == expected
    
    def test_get_all_selectors_method(self):
        """Test getting all selectors for an element"""
        selectors = Plus500Selectors()
        
        # Test existing element
        positions_nav_selectors = selectors.get_all_selectors_for_element('POSITIONS_NAV')
        assert 'xpath' in positions_nav_selectors
        assert 'css' in positions_nav_selectors
        assert isinstance(positions_nav_selectors['xpath'], list)
        assert isinstance(positions_nav_selectors['css'], list)
        
        # Test non-existing element
        empty_selectors = selectors.get_all_selectors_for_element('NON_EXISTENT')
        assert empty_selectors == {}
    
    def test_selector_structure_consistency(self):
        """Test that all major selectors follow consistent structure"""
        selectors = Plus500Selectors()
        
        # List of major selector attributes to test
        major_selectors = [
            'POSITIONS_NAV', 'ORDERS_NAV', 'TRADING_SIDEBAR',
            'TRAILING_STOP_SWITCH', 'STOP_LOSS_SWITCH', 'TAKE_PROFIT_SWITCH',
            'PLACE_ORDER_BUTTON', 'POSITION_CLOSE_BUTTON', 'ORDER_CANCEL_BUTTON'
        ]
        
        for selector_name in major_selectors:
            if hasattr(selectors, selector_name):
                selector_dict = getattr(selectors, selector_name)
                
                # Check structure
                assert isinstance(selector_dict, dict), f"{selector_name} should be a dictionary"
                assert 'xpath' in selector_dict or 'css' in selector_dict, f"{selector_name} should have xpath or css"
                
                # Check xpath format if present
                if 'xpath' in selector_dict:
                    assert isinstance(selector_dict['xpath'], list), f"{selector_name} xpath should be a list"
                    assert len(selector_dict['xpath']) > 0, f"{selector_name} xpath should not be empty"
                    
                    for xpath in selector_dict['xpath']:
                        assert isinstance(xpath, str), f"{selector_name} xpath items should be strings"
                        assert xpath.startswith('//'), f"{selector_name} xpath should start with '//' : {xpath}"
                
                # Check css format if present
                if 'css' in selector_dict:
                    assert isinstance(selector_dict['css'], list), f"{selector_name} css should be a list"
                    assert len(selector_dict['css']) > 0, f"{selector_name} css should not be empty"
                    
                    for css in selector_dict['css']:
                        assert isinstance(css, str), f"{selector_name} css items should be strings"
    
    def test_plus500_specific_patterns(self):
        """Test Plus500US-specific selector patterns"""
        selectors = Plus500Selectors()
        
        # Test plus500-switch components
        trailing_stop_css = selectors.TRAILING_STOP_SWITCH['css']
        assert any('plus500-switch' in css for css in trailing_stop_css)
        assert any('data-testid' in css for css in trailing_stop_css)
        
        # Test futures-specific classes
        positions_table_css = selectors.POSITIONS_TABLE_CONTAINER['css']
        assert any('futures-positions' in css for css in positions_table_css)
        
        orders_table_css = selectors.ORDERS_TABLE_CONTAINER['css']
        assert any('futures-orders' in css for css in orders_table_css)
        
        # Test automation attributes
        equity_xpath = selectors.EQUITY_VALUE['xpath']
        assert any("automation='equity'" in xpath for xpath in equity_xpath)
    
    def test_selector_fallback_patterns(self):
        """Test that selectors have fallback patterns"""
        selectors = Plus500Selectors()
        
        # Test that critical selectors have multiple strategies
        critical_selectors = [
            'POSITIONS_NAV', 'ORDERS_NAV', 'TRAILING_STOP_SWITCH',
            'POSITION_CLOSE_BUTTON', 'ORDER_CANCEL_BUTTON'
        ]
        
        for selector_name in critical_selectors:
            selector_dict = getattr(selectors, selector_name)
            
            # Should have both xpath and css, or multiple patterns in one
            has_multiple_strategies = (
                ('xpath' in selector_dict and 'css' in selector_dict) or
                ('xpath' in selector_dict and len(selector_dict['xpath']) > 1) or
                ('css' in selector_dict and len(selector_dict['css']) > 1)
            )
            
            assert has_multiple_strategies, f"{selector_name} should have multiple selection strategies for robustness"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])