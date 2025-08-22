"""
Tests for WebDriver Account Manager
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from decimal import Decimal
from plus500us_client.config import Config
from plus500us_client.webdriver.account_manager import WebDriverAccountManager
from plus500us_client.errors import ValidationError


class TestWebDriverAccountManager:
    """Test WebDriver account management functionality"""
    
    @pytest.fixture
    def config(self):
        """Create test config"""
        cfg = Config()
        cfg.account_type = 'demo'
        return cfg
    
    @pytest.fixture
    def mock_driver(self):
        """Create mock WebDriver"""
        driver = Mock()
        driver.current_url = "https://app.plus500.com/trade"
        driver.page_source = "<html><body>Test</body></html>"
        return driver
    
    @pytest.fixture
    def mock_element_detector(self):
        """Create mock element detector"""
        detector = Mock()
        return detector
    
    @pytest.fixture
    def account_manager(self, config):
        """Create account manager instance"""
        return WebDriverAccountManager(config)
    
    def test_initialization(self, account_manager, config):
        """Test account manager initialization"""
        assert account_manager.config == config
        assert account_manager.driver is None
        assert account_manager.element_detector is None
        assert not account_manager._initialized if hasattr(account_manager, '_initialized') else True
    
    def test_initialize_with_driver(self, account_manager, mock_driver):
        """Test initialization with WebDriver"""
        with patch('plus500us_client.webdriver.account_manager.ElementDetector') as MockDetector:
            mock_detector = Mock()
            MockDetector.return_value = mock_detector
            
            account_manager.initialize(mock_driver)
            
            assert account_manager.driver == mock_driver
            assert account_manager.element_detector == mock_detector
            MockDetector.assert_called_once_with(mock_driver)
    
    def test_detect_current_account_type_demo(self, account_manager, mock_driver):
        """Test detecting demo account type"""
        with patch('plus500us_client.webdriver.account_manager.ElementDetector') as MockDetector:
            mock_detector = Mock()
            MockDetector.return_value = mock_detector
            
            # Mock finding switch control
            mock_switch_element = Mock()
            mock_detector.find_element_robust.side_effect = [mock_switch_element, None]
            
            # Mock active span with demo text
            mock_active_span = Mock()
            mock_detector.extract_text_safe.return_value = "Demo Mode"
            mock_detector.find_element_robust.side_effect = [mock_switch_element, mock_active_span]
            
            account_manager.initialize(mock_driver)
            account_type = account_manager.detect_current_account_type()
            
            assert account_type == 'demo'
    
    def test_detect_current_account_type_live(self, account_manager, mock_driver):
        """Test detecting live account type"""
        with patch('plus500us_client.webdriver.account_manager.ElementDetector') as MockDetector:
            mock_detector = Mock()
            MockDetector.return_value = mock_detector
            
            # Mock finding switch control
            mock_switch_element = Mock()
            mock_active_span = Mock()
            
            # Mock active span with real money text
            mock_detector.extract_text_safe.return_value = "Real Money"
            mock_detector.find_element_robust.side_effect = [mock_switch_element, mock_active_span]
            
            account_manager.initialize(mock_driver)
            account_type = account_manager.detect_current_account_type()
            
            assert account_type == 'live'
    
    def test_detect_current_account_type_fallback(self, account_manager, mock_driver, config):
        """Test fallback to config when detection fails"""
        with patch('plus500us_client.webdriver.account_manager.ElementDetector') as MockDetector:
            mock_detector = Mock()
            MockDetector.return_value = mock_detector
            
            # Mock no elements found
            mock_detector.find_element_robust.return_value = None
            
            account_manager.initialize(mock_driver)
            account_type = account_manager.detect_current_account_type()
            
            assert account_type == config.account_type
    
    @patch('plus500us_client.webdriver.account_manager.time')
    def test_switch_account_type_success(self, mock_time, account_manager, mock_driver):
        """Test successful account type switching"""
        with patch('plus500us_client.webdriver.account_manager.ElementDetector') as MockDetector:
            mock_detector = Mock()
            MockDetector.return_value = mock_detector
            
            # Mock current type detection and switch elements
            account_manager.detect_current_account_type = Mock(side_effect=['demo', 'live'])
            
            mock_target_span = Mock()
            mock_detector.find_element_robust.return_value = mock_target_span
            
            with patch.object(account_manager.utils, 'human_like_click') as mock_click:
                account_manager.initialize(mock_driver)
                result = account_manager.switch_account_type('live')
                
                assert result is True
                mock_click.assert_called_once_with(mock_driver, mock_target_span)
                assert account_manager.config.account_type == 'live'
    
    def test_switch_account_type_invalid(self, account_manager, mock_driver):
        """Test switching to invalid account type"""
        account_manager.initialize(mock_driver)
        
        with pytest.raises(ValidationError):
            account_manager.switch_account_type('invalid')
    
    def test_switch_account_type_already_current(self, account_manager, mock_driver):
        """Test switching to already current account type"""
        with patch('plus500us_client.webdriver.account_manager.ElementDetector'):
            account_manager.detect_current_account_type = Mock(return_value='demo')
            
            account_manager.initialize(mock_driver)
            result = account_manager.switch_account_type('demo')
            
            assert result is True
    
    def test_parse_currency_value_valid(self, account_manager):
        """Test parsing valid currency values"""
        # Test basic value
        result = account_manager._parse_currency_value("$123.45")
        assert result == Decimal('123.45')
        
        # Test with commas
        result = account_manager._parse_currency_value("$1,234.56")
        assert result == Decimal('1234.56')
        
        # Test negative value
        result = account_manager._parse_currency_value("-$45.67")
        assert result == Decimal('-45.67')
        
        # Test with special characters (Unicode)
        result = account_manager._parse_currency_value("$‪191.51‬")
        assert result == Decimal('191.51')
    
    def test_parse_currency_value_invalid(self, account_manager):
        """Test parsing invalid currency values"""
        # Test empty string
        result = account_manager._parse_currency_value("")
        assert result is None
        
        # Test None
        result = account_manager._parse_currency_value(None)
        assert result is None
        
        # Test non-numeric string
        result = account_manager._parse_currency_value("Not a number")
        assert result is None
    
    def test_extract_account_balance_data(self, account_manager, mock_driver):
        """Test extracting account balance data from WebDriver"""
        with patch('plus500us_client.webdriver.account_manager.ElementDetector') as MockDetector:
            mock_detector = Mock()
            MockDetector.return_value = mock_detector
            
            # Mock account type detection
            account_manager.detect_current_account_type = Mock(return_value='demo')
            
            # Mock balance elements
            mock_elements = {
                'equity': Mock(),
                'pnl': Mock(),
                'live_margin': Mock(),
                'full_margin': Mock()
            }
            
            # Mock element finding
            def mock_find_element(selector, **kwargs):
                if 'equity' in str(selector):
                    return mock_elements['equity']
                elif 'total-positions-pl' in str(selector):
                    return mock_elements['pnl']
                elif 'live-margin-available' in str(selector):
                    return mock_elements['live_margin']
                elif 'full-margin-available' in str(selector):
                    return mock_elements['full_margin']
                return None
            
            mock_detector.find_element_robust.side_effect = mock_find_element
            
            # Mock text extraction
            def mock_extract_text(element):
                if element == mock_elements['equity']:
                    return "$191.51"
                elif element == mock_elements['pnl']:
                    return "$5.25"
                elif element == mock_elements['live_margin']:
                    return "$186.26"
                elif element == mock_elements['full_margin']:
                    return "$186.26"
                return ""
            
            mock_detector.extract_text_safe.side_effect = mock_extract_text
            
            account_manager.initialize(mock_driver)
            balance_data = account_manager.extract_account_balance_data()
            
            assert balance_data['account_type'] == 'demo'
            assert balance_data['equity'] == Decimal('191.51')
            assert balance_data['total_pnl'] == Decimal('5.25')
            assert balance_data['live_margin_available'] == Decimal('186.26')
            assert balance_data['full_margin_available'] == Decimal('186.26')
            assert 'timestamp' in balance_data
    
    def test_detect_balance_changes(self, account_manager):
        """Test detecting balance changes"""
        old_data = {
            'equity': Decimal('100.00'),
            'total_pnl': Decimal('5.00'),
            'live_margin_available': Decimal('95.00')
        }
        
        new_data = {
            'equity': Decimal('105.00'),
            'total_pnl': Decimal('10.00'),
            'live_margin_available': Decimal('95.00')  # No change
        }
        
        changes = account_manager._detect_balance_changes(old_data, new_data)
        
        assert 'equity' in changes
        assert changes['equity']['old'] == Decimal('100.00')
        assert changes['equity']['new'] == Decimal('105.00')
        assert changes['equity']['change'] == Decimal('5.00')
        
        assert 'total_pnl' in changes
        assert changes['total_pnl']['change'] == Decimal('5.00')
        
        # No change should not be in results
        assert 'live_margin_available' not in changes
    
    def test_get_enhanced_account_info_with_api(self, account_manager, mock_driver):
        """Test getting enhanced account info with API client"""
        # Mock API client
        mock_api_client = Mock()
        mock_api_account = Mock()
        mock_api_account.model_dump.return_value = {
            'account_id': 'test_account',
            'account_type': 'demo',
            'balance': Decimal('100.00'),
            'available': Decimal('90.00'),
            'margin_used': Decimal('10.00'),
            'currency': 'USD'
        }
        mock_api_client.get_account.return_value = mock_api_account
        
        account_manager.account_client = mock_api_client
        
        # Mock WebDriver data extraction
        webdriver_data = {
            'account_type': 'demo',
            'equity': Decimal('105.00'),
            'total_pnl': Decimal('5.00'),
            'live_margin_available': Decimal('95.00'),
            'balance': Decimal('105.00'),
            'available': Decimal('95.00'),
            'margin_used': Decimal('10.00')
        }
        
        account_manager.extract_account_balance_data = Mock(return_value=webdriver_data)
        account_manager.initialize(mock_driver)
        
        # Import Account model for the test
        from plus500us_client.models import Account
        
        with patch('plus500us_client.webdriver.account_manager.Account', Account):
            enhanced_account = account_manager.get_enhanced_account_info()
            
            # Should prefer WebDriver data over API data
            assert enhanced_account.equity == Decimal('105.00')
            assert enhanced_account.balance == Decimal('105.00')
            assert enhanced_account.available == Decimal('95.00')
            assert enhanced_account.account_type == 'demo'
    
    def test_get_enhanced_account_info_webdriver_only(self, account_manager, mock_driver):
        """Test getting enhanced account info without API client"""
        account_manager.account_client = None
        
        # Mock WebDriver data extraction
        webdriver_data = {
            'account_type': 'demo',
            'equity': Decimal('105.00'),
            'total_pnl': Decimal('5.00'),
            'balance': Decimal('105.00'),
            'available': Decimal('95.00'),
            'margin_used': Decimal('10.00')
        }
        
        account_manager.extract_account_balance_data = Mock(return_value=webdriver_data)
        account_manager.initialize(mock_driver)
        
        # Import Account model for the test
        from plus500us_client.models import Account
        
        with patch('plus500us_client.webdriver.account_manager.Account', Account):
            enhanced_account = account_manager.get_enhanced_account_info()
            
            assert enhanced_account.balance == Decimal('105.00')
            assert enhanced_account.available == Decimal('95.00')
            assert enhanced_account.account_type == 'demo'