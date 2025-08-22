"""
Tests for WebDriver Instruments Discovery
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch
from decimal import Decimal
from bs4 import BeautifulSoup

from plus500us_client.config import Config
from plus500us_client.webdriver.instruments_discovery import WebDriverInstrumentsDiscovery
from plus500us_client.errors import ValidationError


class TestWebDriverInstrumentsDiscovery:
    """Test WebDriver instruments discovery functionality"""
    
    @pytest.fixture
    def config(self):
        """Create test config"""
        return Config()
    
    @pytest.fixture
    def mock_driver(self):
        """Create mock WebDriver"""
        driver = Mock()
        driver.current_url = "https://app.plus500.com/trade"
        return driver
    
    @pytest.fixture
    def instruments_discovery(self, config):
        """Create instruments discovery instance"""
        return WebDriverInstrumentsDiscovery(config)
    
    @pytest.fixture
    def sample_instrument_html(self):
        """Sample instrument row HTML for testing"""
        return '''
        <div class="instrument-row instrument red-change" data-instrument-id="1074659">
            <div class="name">
                <strong>Micro Corn <span>Dec 25</span></strong>
            </div>
            <div class="change">‎-0.37%‎</div>
            <div class="sell" data-no-trading="true">404.500</div>
            <div class="buy" data-no-trading="true">405.500</div>
            <div class="high-low"><span>407.500/399.500</span></div>
            <div class="market-closed"><span class="icon-moon"></span></div>
        </div>
        '''
    
    @pytest.fixture
    def sample_categories_html(self):
        """Sample categories HTML for testing"""
        return '''
        <div id="categories">
            <ul>
                <li>
                    <h3>Most Popular</h3>
                    <ul>
                        <li><a class="">All Popular</a></li>
                        <li><a class="selected">Micro</a></li>
                    </ul>
                </li>
                <li>
                    <h3>By Sector</h3>
                    <ul>
                        <li><a class="">Agriculture</a></li>
                        <li><a class="">Crypto</a></li>
                        <li><a class="">Forex</a></li>
                    </ul>
                </li>
            </ul>
        </div>
        '''
    
    def test_initialization(self, instruments_discovery, config):
        """Test instruments discovery initialization"""
        assert instruments_discovery.config == config
        assert instruments_discovery.driver is None
        assert instruments_discovery.element_detector is None
        assert instruments_discovery._instruments_cache == {}
        assert instruments_discovery._last_cache_update == {}
    
    def test_initialize_with_driver(self, instruments_discovery, mock_driver):
        """Test initialization with WebDriver"""
        with patch('plus500us_client.webdriver.instruments_discovery.ElementDetector') as MockDetector:
            mock_detector = Mock()
            MockDetector.return_value = mock_detector
            
            instruments_discovery.initialize(mock_driver)
            
            assert instruments_discovery.driver == mock_driver
            assert instruments_discovery.element_detector == mock_detector
    
    def test_extract_instrument_from_row(self, instruments_discovery, sample_instrument_html):
        """Test extracting instrument data from HTML row"""
        soup = BeautifulSoup(sample_instrument_html, 'html.parser')
        row = soup.find('div', class_='instrument-row')
        
        instrument_data = instruments_discovery._extract_instrument_from_row(row)
        
        assert instrument_data is not None
        assert instrument_data['id'] == '1074659'
        assert instrument_data['name'] == 'Micro Corn'
        assert instrument_data['expiry'] == 'Dec 25'
        assert instrument_data['change_pct'] == -0.37
        assert instrument_data['bid'] == 404.5
        assert instrument_data['ask'] == 405.5
        assert instrument_data['high'] == 407.5
        assert instrument_data['low'] == 399.5
        assert instrument_data['market_closed'] is True
        assert instrument_data['spread'] == 1.0  # 405.5 - 404.5
        assert 'timestamp' in instrument_data
    
    def test_parse_price_valid(self, instruments_discovery):
        """Test parsing valid price values"""
        assert instruments_discovery._parse_price("404.500") == 404.5
        assert instruments_discovery._parse_price("1,234.56") == 1234.56
        assert instruments_discovery._parse_price("23,772.00") == 23772.0
    
    def test_parse_price_invalid(self, instruments_discovery):
        """Test parsing invalid price values"""
        assert instruments_discovery._parse_price("") is None
        assert instruments_discovery._parse_price(None) is None
        assert instruments_discovery._parse_price("invalid") is None
    
    def test_parse_percentage_valid(self, instruments_discovery):
        """Test parsing valid percentage values"""
        assert instruments_discovery._parse_percentage("‎-0.37%‎") == -0.37
        assert instruments_discovery._parse_percentage("0.34%") == 0.34
        assert instruments_discovery._parse_percentage("-1.51%") == -1.51
    
    def test_parse_percentage_invalid(self, instruments_discovery):
        """Test parsing invalid percentage values"""
        assert instruments_discovery._parse_percentage("") is None
        assert instruments_discovery._parse_percentage(None) is None
        assert instruments_discovery._parse_percentage("invalid%") is None
    
    def test_parse_high_low_valid(self, instruments_discovery):
        """Test parsing valid high/low values"""
        high, low = instruments_discovery._parse_high_low("407.500/399.500")
        assert high == 407.5
        assert low == 399.5
        
        high, low = instruments_discovery._parse_high_low("1,048.000/1,035.000")
        assert high == 1048.0
        assert low == 1035.0
    
    def test_parse_high_low_invalid(self, instruments_discovery):
        """Test parsing invalid high/low values"""
        high, low = instruments_discovery._parse_high_low("")
        assert high is None
        assert low is None
        
        high, low = instruments_discovery._parse_high_low("invalid")
        assert high is None
        assert low is None
    
    def test_get_available_categories(self, instruments_discovery, mock_driver, sample_categories_html):
        """Test getting available categories"""
        with patch('plus500us_client.webdriver.instruments_discovery.ElementDetector') as MockDetector:
            mock_detector = Mock()
            MockDetector.return_value = mock_detector
            
            # Mock categories container
            mock_container = Mock()
            mock_detector.find_element_robust.return_value = mock_container
            
            # Create mock category links
            soup = BeautifulSoup(sample_categories_html, 'html.parser')
            links = soup.find_all('a')
            
            # Filter out selected links and create mocks
            mock_links = []
            for link in links:
                if 'selected' not in link.get('class', []):
                    mock_link = Mock()
                    mock_link.get_attribute.return_value = ''
                    mock_detector.extract_text_safe.return_value = link.get_text()
                    mock_links.append(mock_link)
            
            mock_container.find_elements.return_value = mock_links
            
            instruments_discovery.initialize(mock_driver)
            categories = instruments_discovery._get_available_categories()
            
            # Should have categories but not the selected ones
            assert len(categories) > 0
            # Selected "Micro" should not be included
            assert "Micro" not in categories
    
    def test_cache_functionality(self, instruments_discovery):
        """Test caching functionality"""
        category = "TestCategory"
        test_data = [{'id': '1', 'name': 'Test Instrument'}]
        
        # Initially no cache
        assert not instruments_discovery._is_cache_valid(category)
        
        # Add to cache
        instruments_discovery._instruments_cache[category] = test_data
        instruments_discovery._last_cache_update[category] = time.time()
        
        # Should be valid now
        assert instruments_discovery._is_cache_valid(category)
        
        # Test cache stats
        stats = instruments_discovery.get_cache_stats()
        assert category in stats['cached_categories']
        assert stats['total_cached_instruments'] == 1
        assert category in stats['cache_ages']
        
        # Clear cache
        instruments_discovery.clear_cache()
        assert instruments_discovery._instruments_cache == {}
        assert instruments_discovery._last_cache_update == {}
    
    @patch('time.time')
    def test_cache_expiration(self, mock_time, instruments_discovery):
        """Test cache expiration"""
        category = "TestCategory"
        
        # Set initial time
        mock_time.return_value = 1000.0
        instruments_discovery._last_cache_update[category] = 1000.0
        
        # Should be valid immediately
        assert instruments_discovery._is_cache_valid(category)
        
        # Advance time beyond cache duration
        mock_time.return_value = 1000.0 + instruments_discovery.cache_duration + 1
        
        # Should be invalid now
        assert not instruments_discovery._is_cache_valid(category)
    
    def test_search_instruments(self, instruments_discovery):
        """Test instrument searching"""
        # Mock cache with test data
        instruments_discovery._instruments_cache = {
            'Crypto': [
                {'id': '1', 'name': 'Micro Bitcoin', 'symbol': 'BTC'},
                {'id': '2', 'name': 'Micro Ether', 'symbol': 'ETH'}
            ],
            'Forex': [
                {'id': '3', 'name': 'EUR/USD', 'symbol': 'EURUSD'},
                {'id': '4', 'name': 'GBP/USD', 'symbol': 'GBPUSD'}
            ]
        }
        
        # Mock the discover_all_instruments_by_category method
        instruments_discovery.discover_all_instruments_by_category = Mock(
            return_value=instruments_discovery._instruments_cache
        )
        
        # Search for Bitcoin
        results = instruments_discovery.search_instruments('Bitcoin')
        assert len(results) == 1
        assert results[0]['name'] == 'Micro Bitcoin'
        assert results[0]['category'] == 'Crypto'
        
        # Search for USD (should find multiple)
        results = instruments_discovery.search_instruments('USD')
        assert len(results) == 2
        
        # Search for non-existent instrument
        results = instruments_discovery.search_instruments('NonExistent')
        assert len(results) == 0
    
    def test_get_instrument_details(self, instruments_discovery):
        """Test getting detailed instrument information"""
        # Mock cached instruments
        test_instrument = {
            'id': 'test_id',
            'name': 'Test Instrument',
            'symbol': 'TEST'
        }
        
        instruments_discovery._instruments_cache = {
            'TestCategory': [test_instrument]
        }
        
        # Mock the discover method
        instruments_discovery.discover_all_instruments_by_category = Mock(
            return_value=instruments_discovery._instruments_cache
        )
        
        # Mock enhanced details
        enhanced_details = {
            'tick_size': 0.25,
            'min_qty': 1.0
        }
        instruments_discovery._get_enhanced_instrument_details = Mock(
            return_value=enhanced_details
        )
        
        details = instruments_discovery.get_instrument_details('test_id')
        
        assert details is not None
        assert details['id'] == 'test_id'
        assert details['category'] == 'TestCategory'
        assert details['tick_size'] == 0.25
        assert details['min_qty'] == 1.0
    
    def test_get_enhanced_instrument_details(self, instruments_discovery):
        """Test getting enhanced instrument details"""
        # Test with micro instrument
        micro_instrument = {'name': 'Micro Bitcoin'}
        enhanced = instruments_discovery._get_enhanced_instrument_details(micro_instrument)
        
        assert enhanced is not None
        assert enhanced['tick_size'] == 0.25
        assert enhanced['min_qty'] == 1.0
        
        # Test with forex instrument
        forex_instrument = {'name': 'EUR/USD'}
        enhanced = instruments_discovery._get_enhanced_instrument_details(forex_instrument)
        
        assert enhanced is not None
        assert enhanced['tick_size'] == 0.0001
        assert enhanced['tick_value'] == 0.1