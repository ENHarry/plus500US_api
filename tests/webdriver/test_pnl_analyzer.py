"""
Tests for WebDriver PnL Analyzer
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, date
from decimal import Decimal
from bs4 import BeautifulSoup

from plus500us_client.config import Config
from plus500us_client.webdriver.pnl_analyzer import WebDriverPnLAnalyzer
from plus500us_client.errors import ValidationError


class TestWebDriverPnLAnalyzer:
    """Test WebDriver PnL analysis functionality"""
    
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
    def pnl_analyzer(self, config):
        """Create PnL analyzer instance"""
        return WebDriverPnLAnalyzer(config)
    
    @pytest.fixture
    def sample_trade_html(self):
        """Sample trade row HTML for testing"""
        return '''
        <div class="history selected">
            <div class="date">
                <span>8/18/2025</span>
                <span>3:13 PM</span>
            </div>
            <div class="action">Sell</div>
            <div class="amount">1 <label class="regular">contract</label></div>
            <div class="name">
                <strong>Micro E-mini S&P 500 <span>Sep 25</span></strong>
            </div>
            <div class="open-price">6,469.50</div>
            <div class="close-price">6,468.50</div>
            <div class="pl green">$‪3.28‬</div>
        </div>
        '''
    
    @pytest.fixture
    def sample_losing_trade_html(self):
        """Sample losing trade row HTML for testing"""
        return '''
        <div class="history">
            <div class="date">
                <span>8/18/2025</span>
                <span>1:43 PM</span>
            </div>
            <div class="action">Buy</div>
            <div class="amount">1 <label class="regular">contract</label></div>
            <div class="name">
                <strong>Micro E-mini S&P 500 <span>Sep 25</span></strong>
            </div>
            <div class="open-price">6,463.75</div>
            <div class="close-price">6,463.00</div>
            <div class="pl red">$‪-5.47‬</div>
        </div>
        '''
    
    def test_initialization(self, pnl_analyzer, config):
        """Test PnL analyzer initialization"""
        assert pnl_analyzer.config == config
        assert pnl_analyzer.driver is None
        assert pnl_analyzer.element_detector is None
    
    def test_initialize_with_driver(self, pnl_analyzer, mock_driver):
        """Test initialization with WebDriver"""
        with patch('plus500us_client.webdriver.pnl_analyzer.ElementDetector') as MockDetector:
            mock_detector = Mock()
            MockDetector.return_value = mock_detector
            
            pnl_analyzer.initialize(mock_driver)
            
            assert pnl_analyzer.driver == mock_driver
            assert pnl_analyzer.element_detector == mock_detector
    
    def test_parse_trade_datetime_valid(self, pnl_analyzer):
        """Test parsing valid trade datetime"""
        result = pnl_analyzer._parse_trade_datetime("8/18/2025", "3:13 PM")
        
        assert result is not None
        assert result.date() == date(2025, 8, 18)
        assert result.hour == 15  # 3 PM in 24-hour format
        assert result.minute == 13
    
    def test_parse_trade_datetime_invalid(self, pnl_analyzer):
        """Test parsing invalid trade datetime"""
        result = pnl_analyzer._parse_trade_datetime("invalid", "invalid")
        assert result is None
        
        result = pnl_analyzer._parse_trade_datetime("", "")
        assert result is None
    
    def test_parse_quantity_valid(self, pnl_analyzer):
        """Test parsing valid quantity values"""
        result = pnl_analyzer._parse_quantity("1 contract")
        assert result == Decimal('1')
        
        result = pnl_analyzer._parse_quantity("5 contracts")
        assert result == Decimal('5')
    
    def test_parse_quantity_invalid(self, pnl_analyzer):
        """Test parsing invalid quantity values"""
        result = pnl_analyzer._parse_quantity("invalid")
        assert result is None
        
        result = pnl_analyzer._parse_quantity("")
        assert result is None
    
    def test_parse_price_valid(self, pnl_analyzer):
        """Test parsing valid price values"""
        result = pnl_analyzer._parse_price("6,469.50")
        assert result == Decimal('6469.50')
        
        result = pnl_analyzer._parse_price("$1,234.56")
        assert result == Decimal('1234.56')
    
    def test_parse_price_invalid(self, pnl_analyzer):
        """Test parsing invalid price values"""
        result = pnl_analyzer._parse_price("")
        assert result is None
        
        result = pnl_analyzer._parse_price("invalid")
        assert result is None
    
    def test_parse_pnl_valid(self, pnl_analyzer):
        """Test parsing valid P&L values"""
        # Positive P&L
        result = pnl_analyzer._parse_pnl("$‪3.28‬")
        assert result == Decimal('3.28')
        
        # Negative P&L
        result = pnl_analyzer._parse_pnl("$‪-5.47‬")
        assert result == Decimal('-5.47')
        
        # Another negative format
        result = pnl_analyzer._parse_pnl("-$12.34")
        assert result == Decimal('-12.34')
    
    def test_parse_pnl_invalid(self, pnl_analyzer):
        """Test parsing invalid P&L values"""
        result = pnl_analyzer._parse_pnl("")
        assert result is None
        
        result = pnl_analyzer._parse_pnl("invalid")
        assert result is None
    
    def test_extract_trade_from_row_winning(self, pnl_analyzer, sample_trade_html):
        """Test extracting winning trade data from HTML row"""
        soup = BeautifulSoup(sample_trade_html, 'html.parser')
        row = soup.find('div', class_='history')
        
        trade_data = pnl_analyzer._extract_trade_from_row(row)
        
        assert trade_data is not None
        assert trade_data['action'] == 'Sell'
        assert trade_data['quantity'] == Decimal('1')
        assert trade_data['instrument'] == 'Micro E-mini S&P 500Sep 25'
        assert trade_data['open_price'] == Decimal('6469.50')
        assert trade_data['close_price'] == Decimal('6468.50')
        assert trade_data['pnl'] == Decimal('3.28')
        assert trade_data['is_win'] is True
        assert trade_data['is_loss'] is False
        assert trade_data['datetime'].date() == date(2025, 8, 18)
        assert trade_data['datetime'].hour == 15
    
    def test_extract_trade_from_row_losing(self, pnl_analyzer, sample_losing_trade_html):
        """Test extracting losing trade data from HTML row"""
        soup = BeautifulSoup(sample_losing_trade_html, 'html.parser')
        row = soup.find('div', class_='history')
        
        trade_data = pnl_analyzer._extract_trade_from_row(row)
        
        assert trade_data is not None
        assert trade_data['action'] == 'Buy'
        assert trade_data['pnl'] == Decimal('-5.47')
        assert trade_data['is_win'] is False
        assert trade_data['is_loss'] is True
    
    def test_filter_trades_by_date(self, pnl_analyzer):
        """Test filtering trades by specific date"""
        target_date = date(2025, 8, 18)
        
        trades = [
            {'date': date(2025, 8, 18), 'pnl': Decimal('10.00')},
            {'date': date(2025, 8, 17), 'pnl': Decimal('5.00')},
            {'date': date(2025, 8, 18), 'pnl': Decimal('-3.00')},
            {'date': date(2025, 8, 19), 'pnl': Decimal('2.00')}
        ]
        
        filtered = pnl_analyzer._filter_trades_by_date(trades, target_date)
        
        assert len(filtered) == 2
        assert all(trade['date'] == target_date for trade in filtered)
        assert sum(trade['pnl'] for trade in filtered) == Decimal('7.00')
    
    def test_filter_trades_by_date_range(self, pnl_analyzer):
        """Test filtering trades by date range"""
        start_date = date(2025, 8, 17)
        end_date = date(2025, 8, 19)
        
        trades = [
            {'date': date(2025, 8, 16), 'pnl': Decimal('1.00')},  # Before range
            {'date': date(2025, 8, 17), 'pnl': Decimal('10.00')},  # Start of range
            {'date': date(2025, 8, 18), 'pnl': Decimal('5.00')},   # In range
            {'date': date(2025, 8, 19), 'pnl': Decimal('-3.00')},  # End of range
            {'date': date(2025, 8, 20), 'pnl': Decimal('2.00')}    # After range
        ]
        
        filtered = pnl_analyzer._filter_trades_by_date_range(trades, start_date, end_date)
        
        assert len(filtered) == 3
        assert all(start_date <= trade['date'] <= end_date for trade in filtered)
        assert sum(trade['pnl'] for trade in filtered) == Decimal('12.00')
    
    def test_analyze_trades_basic(self, pnl_analyzer):
        """Test basic trade analysis"""
        trades = [
            {'pnl': Decimal('10.00'), 'quantity': Decimal('1'), 'instrument': 'TEST1', 'time': None},
            {'pnl': Decimal('-5.00'), 'quantity': Decimal('1'), 'instrument': 'TEST2', 'time': None},
            {'pnl': Decimal('15.00'), 'quantity': Decimal('2'), 'instrument': 'TEST1', 'time': None},
            {'pnl': Decimal('-3.00'), 'quantity': Decimal('1'), 'instrument': 'TEST3', 'time': None},
            {'pnl': Decimal('0.00'), 'quantity': Decimal('1'), 'instrument': 'TEST4', 'time': None}  # Break-even
        ]
        
        analysis = pnl_analyzer._analyze_trades(trades)
        
        assert analysis['total_trades'] == 5
        assert analysis['net_pnl'] == Decimal('17.00')
        assert analysis['winning_trades'] == 2
        assert analysis['losing_trades'] == 2
        assert analysis['break_even_trades'] == 1
        assert analysis['gross_profit'] == Decimal('25.00')
        assert analysis['gross_loss'] == Decimal('8.00')
        assert analysis['win_rate'] == 40.0  # 2/5 * 100
        assert analysis['loss_rate'] == 40.0  # 2/5 * 100
        assert analysis['avg_win'] == Decimal('12.50')  # (10 + 15) / 2
        assert analysis['avg_loss'] == Decimal('4.00')   # (5 + 3) / 2
        assert analysis['largest_win'] == Decimal('15.00')
        assert analysis['largest_loss'] == Decimal('5.00')
        assert analysis['total_quantity_traded'] == Decimal('6')
        assert len(analysis['instruments_traded']) == 4
        assert analysis['profit_factor'] == 3.125  # 25 / 8
    
    def test_analyze_trades_empty(self, pnl_analyzer):
        """Test analysis with empty trades list"""
        analysis = pnl_analyzer._analyze_trades([])
        
        assert analysis['total_trades'] == 0
        assert analysis['net_pnl'] == Decimal('0')
        assert analysis['winning_trades'] == 0
        assert analysis['losing_trades'] == 0
        assert analysis['win_rate'] == 0.0
        assert analysis['profit_factor'] == 0.0
    
    def test_analyze_trades_only_wins(self, pnl_analyzer):
        """Test analysis with only winning trades"""
        trades = [
            {'pnl': Decimal('10.00'), 'quantity': Decimal('1'), 'instrument': 'TEST1', 'time': None},
            {'pnl': Decimal('5.00'), 'quantity': Decimal('1'), 'instrument': 'TEST2', 'time': None}
        ]
        
        analysis = pnl_analyzer._analyze_trades(trades)
        
        assert analysis['winning_trades'] == 2
        assert analysis['losing_trades'] == 0
        assert analysis['win_rate'] == 100.0
        assert analysis['profit_factor'] == float('inf')  # No losses
        assert analysis['win_loss_ratio'] == 0.0  # No losses to compare
    
    def test_analyze_trades_only_losses(self, pnl_analyzer):
        """Test analysis with only losing trades"""
        trades = [
            {'pnl': Decimal('-10.00'), 'quantity': Decimal('1'), 'instrument': 'TEST1', 'time': None},
            {'pnl': Decimal('-5.00'), 'quantity': Decimal('1'), 'instrument': 'TEST2', 'time': None}
        ]
        
        analysis = pnl_analyzer._analyze_trades(trades)
        
        assert analysis['winning_trades'] == 0
        assert analysis['losing_trades'] == 2
        assert analysis['win_rate'] == 0.0
        assert analysis['loss_rate'] == 100.0
        assert analysis['profit_factor'] == 0.0
        assert analysis['net_pnl'] == Decimal('-15.00')
    
    def test_create_daily_breakdown(self, pnl_analyzer):
        """Test creating daily breakdown of trades"""
        start_date = date(2025, 8, 17)
        end_date = date(2025, 8, 19)
        
        trades = [
            {
                'date': date(2025, 8, 17),
                'pnl': Decimal('10.00'),
                'quantity': Decimal('1'),
                'instrument': 'TEST1',
                'time': None
            },
            {
                'date': date(2025, 8, 17),
                'pnl': Decimal('-5.00'),
                'quantity': Decimal('1'),
                'instrument': 'TEST2',
                'time': None
            },
            {
                'date': date(2025, 8, 18),
                'pnl': Decimal('15.00'),
                'quantity': Decimal('1'),
                'instrument': 'TEST3',
                'time': None
            }
            # Note: 2025-8-19 has no trades
        ]
        
        breakdown = pnl_analyzer._create_daily_breakdown(trades, start_date, end_date)
        
        # Should have entries for all days in range
        assert '2025-08-17' in breakdown
        assert '2025-08-18' in breakdown
        assert '2025-08-19' in breakdown
        
        # Check 2025-08-17 (2 trades)
        day_17 = breakdown['2025-08-17']
        assert day_17['total_trades'] == 2
        assert day_17['net_pnl'] == Decimal('5.00')
        assert day_17['winning_trades'] == 1
        assert day_17['losing_trades'] == 1
        
        # Check 2025-08-18 (1 trade)
        day_18 = breakdown['2025-08-18']
        assert day_18['total_trades'] == 1
        assert day_18['net_pnl'] == Decimal('15.00')
        assert day_18['winning_trades'] == 1
        assert day_18['losing_trades'] == 0
        
        # Check 2025-08-19 (no trades)
        day_19 = breakdown['2025-08-19']
        assert day_19['total_trades'] == 0
        assert day_19['net_pnl'] == Decimal('0')
    
    @patch('plus500us_client.webdriver.pnl_analyzer.time')
    def test_navigate_to_closed_positions(self, mock_time, pnl_analyzer, mock_driver):
        """Test navigation to closed positions page"""
        with patch('plus500us_client.webdriver.pnl_analyzer.ElementDetector') as MockDetector:
            mock_detector = Mock()
            MockDetector.return_value = mock_detector
            
            # Mock finding closed positions link
            mock_link = Mock()
            mock_table = Mock()
            mock_detector.find_element_robust.side_effect = [mock_link, mock_table]
            
            with patch.object(pnl_analyzer.utils, 'human_like_click') as mock_click:
                pnl_analyzer.initialize(mock_driver)
                pnl_analyzer._navigate_to_closed_positions()
                
                mock_click.assert_called_once_with(mock_driver, mock_link)
    
    def test_navigate_to_closed_positions_link_not_found(self, pnl_analyzer, mock_driver):
        """Test navigation when closed positions link is not found"""
        with patch('plus500us_client.webdriver.pnl_analyzer.ElementDetector') as MockDetector:
            mock_detector = Mock()
            MockDetector.return_value = mock_detector
            
            # Mock not finding the link
            mock_detector.find_element_robust.return_value = None
            
            pnl_analyzer.initialize(mock_driver)
            
            with pytest.raises(ValidationError, match="Closed positions navigation link not found"):
                pnl_analyzer._navigate_to_closed_positions()