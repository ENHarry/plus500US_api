"""
Tests for enhanced Plus500US WebDriver selectors
"""

import pytest
from plus500us_client.webdriver.selectors import Plus500Selectors


class TestEnhancedSelectors:
    """Test enhanced selector definitions"""
    
    def test_account_management_selectors(self):
        """Test account management selector definitions"""
        selectors = Plus500Selectors()
        
        # Test account switch control selectors
        assert hasattr(selectors, 'ACCOUNT_SWITCH_CONTROL')
        assert 'xpath' in selectors.ACCOUNT_SWITCH_CONTROL
        assert 'css' in selectors.ACCOUNT_SWITCH_CONTROL
        assert len(selectors.ACCOUNT_SWITCH_CONTROL['xpath']) > 0
        assert len(selectors.ACCOUNT_SWITCH_CONTROL['css']) > 0
        
        # Test active account type selectors
        assert hasattr(selectors, 'ACTIVE_ACCOUNT_TYPE')
        assert 'xpath' in selectors.ACTIVE_ACCOUNT_TYPE
        assert 'css' in selectors.ACTIVE_ACCOUNT_TYPE
        
        # Test demo/real mode selectors
        assert hasattr(selectors, 'DEMO_MODE_SPAN')
        assert hasattr(selectors, 'REAL_MODE_SPAN')
    
    def test_balance_selectors(self):
        """Test account balance selector definitions"""
        selectors = Plus500Selectors()
        
        # Test equity value selectors
        assert hasattr(selectors, 'EQUITY_VALUE')
        equity_selectors = selectors.EQUITY_VALUE
        assert 'xpath' in equity_selectors
        assert 'css' in equity_selectors
        assert any('automation=\'equity\'' in xpath for xpath in equity_selectors['xpath'])
        
        # Test P&L selectors
        assert hasattr(selectors, 'TOTAL_PNL')
        pnl_selectors = selectors.TOTAL_PNL
        assert any('total-positions-pl' in xpath for xpath in pnl_selectors['xpath'])
        
        # Test margin selectors
        assert hasattr(selectors, 'LIVE_MARGIN_AVAILABLE')
        assert hasattr(selectors, 'FULL_MARGIN_AVAILABLE')
        
        live_margin = selectors.LIVE_MARGIN_AVAILABLE
        assert any('live-margin-available' in xpath for xpath in live_margin['xpath'])
        
        full_margin = selectors.FULL_MARGIN_AVAILABLE
        assert any('full-margin-available' in xpath for xpath in full_margin['xpath'])
    
    def test_instruments_selectors(self):
        """Test instruments discovery selector definitions"""
        selectors = Plus500Selectors()
        
        # Test categories container
        assert hasattr(selectors, 'INSTRUMENT_CATEGORIES_CONTAINER')
        categories = selectors.INSTRUMENT_CATEGORIES_CONTAINER
        assert any('categories' in xpath for xpath in categories['xpath'])
        
        # Test category links
        assert hasattr(selectors, 'INSTRUMENT_CATEGORY_LINKS')
        
        # Test instruments table
        assert hasattr(selectors, 'INSTRUMENTS_TABLE_CONTAINER')
        table = selectors.INSTRUMENTS_TABLE_CONTAINER
        assert any('instrumentsTable' in xpath for xpath in table['xpath'])
        
        # Test instrument rows
        assert hasattr(selectors, 'INSTRUMENT_ROWS')
        rows = selectors.INSTRUMENT_ROWS
        assert any('instrument-row' in xpath for xpath in rows['xpath'])
    
    def test_pnl_analysis_selectors(self):
        """Test P&L analysis selector definitions"""
        selectors = Plus500Selectors()
        
        # Test closed positions navigation
        assert hasattr(selectors, 'CLOSED_POSITIONS_NAV')
        nav = selectors.CLOSED_POSITIONS_NAV
        assert any('closedPositionsNav' in xpath for xpath in nav['xpath'])
        
        # Test trade history table
        assert hasattr(selectors, 'TRADE_HISTORY_TABLE')
        
        # Test trade history rows
        assert hasattr(selectors, 'TRADE_HISTORY_ROWS')
        rows = selectors.TRADE_HISTORY_ROWS
        assert any('history' in xpath for xpath in rows['xpath'])
        
        # Test trade data selectors
        assert hasattr(selectors, 'TRADE_DATE')
        assert hasattr(selectors, 'TRADE_ACTION')
        assert hasattr(selectors, 'TRADE_AMOUNT')
        assert hasattr(selectors, 'TRADE_INSTRUMENT')
        assert hasattr(selectors, 'TRADE_OPEN_PRICE')
        assert hasattr(selectors, 'TRADE_CLOSE_PRICE')
        assert hasattr(selectors, 'TRADE_PNL')
    
    def test_date_filter_selectors(self):
        """Test date filter selector definitions"""
        selectors = Plus500Selectors()
        
        # Test date filter inputs
        assert hasattr(selectors, 'DATE_FILTER_FROM')
        assert hasattr(selectors, 'DATE_FILTER_TO')
        assert hasattr(selectors, 'DATE_FILTER_SUBMIT')
        
        from_filter = selectors.DATE_FILTER_FROM
        assert any('from' in xpath.lower() for xpath in from_filter['xpath'])
        
        submit_filter = selectors.DATE_FILTER_SUBMIT
        assert any('date-filter-submit' in xpath for xpath in submit_filter['xpath'])
    
    def test_selector_structure_consistency(self):
        """Test that all selectors follow consistent structure"""
        selectors = Plus500Selectors()
        
        # Get all selector attributes
        selector_attrs = [attr for attr in dir(selectors) 
                         if not attr.startswith('_') and attr.isupper()]
        
        for attr_name in selector_attrs:
            if attr_name in ['get_dynamic_selector', 'get_all_selectors_for_element']:
                continue  # Skip methods
                
            selector_dict = getattr(selectors, attr_name)
            
            # Skip if it's not a dictionary (might be a method)
            if not isinstance(selector_dict, dict):
                continue
            
            # Each selector should have xpath and css keys
            assert 'xpath' in selector_dict, f"{attr_name} missing 'xpath' key"
            assert 'css' in selector_dict, f"{attr_name} missing 'css' key"
            
            # Each should have at least one selector
            assert len(selector_dict['xpath']) > 0, f"{attr_name} has empty xpath list"
            assert len(selector_dict['css']) > 0, f"{attr_name} has empty css list"
            
            # All xpath selectors should start with // or .//
            for xpath in selector_dict['xpath']:
                assert xpath.startswith('//') or xpath.startswith('.//'), \
                    f"{attr_name} xpath '{xpath}' doesn't start with // or .//"
    
    def test_get_all_selectors_for_element(self):
        """Test the get_all_selectors_for_element method"""
        selectors = Plus500Selectors()
        
        # Test with existing selector
        equity_selectors = selectors.get_all_selectors_for_element('EQUITY_VALUE')
        assert isinstance(equity_selectors, dict)
        assert 'xpath' in equity_selectors
        assert 'css' in equity_selectors
        
        # Test with non-existing selector
        empty_selectors = selectors.get_all_selectors_for_element('NON_EXISTING')
        assert empty_selectors == {}
    
    def test_get_dynamic_selector(self):
        """Test the get_dynamic_selector method"""
        selectors = Plus500Selectors()
        
        # Test dynamic selector generation
        base_selector = "//tr[contains(., '{position_id}')]"
        dynamic_selector = selectors.get_dynamic_selector(base_selector, position_id="12345")
        
        assert dynamic_selector == "//tr[contains(., '12345')]"
        
        # Test with multiple parameters
        base_selector = "//div[@id='{element_id}' and contains(@class, '{css_class}')]"
        dynamic_selector = selectors.get_dynamic_selector(
            base_selector, 
            element_id="testId",
            css_class="testClass"
        )
        
        assert dynamic_selector == "//div[@id='testId' and contains(@class, 'testClass')]"