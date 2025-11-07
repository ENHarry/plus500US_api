"""
Comprehensive tests for the consolidated Plus500 requests API
Tests all core functionality: authentication, trading, account management
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from decimal import Decimal

from plus500us_client.requests.config import Config
from plus500us_client.requests.session import SessionManager
from plus500us_client.requests.auth import AuthClient
from plus500us_client.requests.trading import TradingClient
from plus500us_client.requests.account import AccountClient
from plus500us_client.requests.trading_api import Plus500TradingAPI
from plus500us_client.requests.errors import AuthenticationError, TradingError


class TestConsolidatedAuthentication:
    """Test the consolidated authentication system"""
    
    def setup_method(self):
        """Setup test environment"""
        self.cfg = Config()
        self.sm = SessionManager(self.cfg)
        self.auth_client = AuthClient(self.cfg, self.sm)
    
    def test_auth_client_initialization(self):
        """Test AuthClient initializes correctly"""
        assert self.auth_client.cfg == self.cfg
        assert self.auth_client.sm == self.sm
    
    @patch('plus500us_client.requests.auth.Plus500FuturesAuth')
    def test_futures_authenticate_success(self, mock_auth_class):
        """Test successful futures authentication"""
        # Mock the authentication client
        mock_auth_instance = Mock()
        mock_auth_instance.authenticate.return_value = {
            'success': True,
            'session_data': {'test': 'data'},
            'steps': {'login': {'success': True}}
        }
        mock_auth_instance.get_authenticated_session.return_value = Mock()
        mock_auth_class.return_value = mock_auth_instance
        
        # Test authentication
        result = self.auth_client.futures_authenticate('test@test.com', 'password123')
        
        assert result['success'] is True
        assert result['authenticated'] is True
        assert 'session_data' in result
        assert 'steps' in result
    
    @patch('plus500us_client.requests.auth.Plus500FuturesAuth')
    def test_futures_authenticate_failure(self, mock_auth_class):
        """Test failed futures authentication"""
        # Mock failed authentication
        mock_auth_instance = Mock()
        mock_auth_instance.authenticate.return_value = {
            'success': False,
            'error': 'Invalid credentials'
        }
        mock_auth_instance.get_authenticated_session.return_value = None
        mock_auth_class.return_value = mock_auth_instance
        
        # Test authentication failure
        result = self.auth_client.futures_authenticate('test@test.com', 'wrongpassword')
        
        assert result['success'] is False
        assert result['authenticated'] is False
        assert 'Invalid credentials' in result['message']
    
    def test_plus500_authenticate_redirect(self):
        """Test that plus500_authenticate redirects to futures_authenticate"""
        with patch.object(self.auth_client, 'futures_authenticate') as mock_futures_auth:
            mock_futures_auth.return_value = {'success': True}
            
            result = self.auth_client.plus500_authenticate('test@test.com', 'password123')
            
            mock_futures_auth.assert_called_once_with('test@test.com', 'password123', debug=False)
            assert result['success'] is True


class TestConsolidatedTrading:
    """Test the consolidated trading system"""
    
    def setup_method(self):
        """Setup test environment"""
        self.cfg = Config()
        self.sm = SessionManager(self.cfg)
        self.trading_client = TradingClient(self.cfg, self.sm)
    
    def test_trading_client_initialization(self):
        """Test TradingClient initializes correctly"""
        assert self.trading_client.cfg == self.cfg
        assert self.trading_client.sm == self.sm
    
    @patch.object(SessionManager, 'make_plus500_request')
    def test_get_plus500_instruments(self, mock_request):
        """Test getting Plus500 instruments"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {'id': 'ES.f', 'name': 'S&P 500 Futures'},
            {'id': 'NQ.f', 'name': 'NASDAQ 100 Futures'}
        ]
        mock_request.return_value = mock_response
        
        instruments = self.trading_client.get_plus500_instruments()
        
        assert len(instruments) == 2
        assert instruments[0]['id'] == 'ES.f'
        mock_request.assert_called_once_with("GetTradeInstruments", {})
    
    @patch.object(SessionManager, 'make_plus500_request')
    def test_create_plus500_order(self, mock_request):
        """Test creating Plus500 order"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'OrderId': '12345',
            'Status': 'Pending',
            'InstrumentId': 'ES.f',
            'Amount': '1'
        }
        mock_request.return_value = mock_response
        
        result = self.trading_client.create_plus500_order(
            instrument_id='ES.f',
            amount=Decimal('1'),
            operation_type='Buy',
            order_type='Market'
        )
        
        assert result['OrderId'] == '12345'
        assert result['Status'] == 'Pending'
        mock_request.assert_called_once()
        
        # Check the payload structure
        call_args = mock_request.call_args
        payload = call_args[0][1]  # Second argument (first is endpoint name)
        assert payload['InstrumentId'] == 'ES.f'
        assert payload['Amount'] == '1'
        assert payload['OperationType'] == 'Buy'
        assert payload['OrderType'] == 'Market'
    
    @patch.object(SessionManager, 'make_plus500_request')
    def test_get_plus500_open_positions(self, mock_request):
        """Test getting open positions"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                'PositionId': '67890',
                'InstrumentId': 'ES.f',
                'Amount': '2',
                'UnrealizedPnL': '150.00'
            }
        ]
        mock_request.return_value = mock_response
        
        positions = self.trading_client.get_plus500_open_positions()
        
        assert len(positions) == 1
        assert positions[0]['PositionId'] == '67890'
        mock_request.assert_called_once_with("FuturesGetOpenPositions")
    
    @patch.object(SessionManager, 'make_plus500_request')
    def test_get_plus500_closed_positions(self, mock_request):
        """Test getting closed positions"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                'PositionId': '11111',
                'InstrumentId': 'NQ.f',
                'Amount': '1',
                'RealizedPnL': '75.50',
                'CloseTime': '2025-08-29T10:30:00Z'
            }
        ]
        mock_request.return_value = mock_response
        
        positions = self.trading_client.get_plus500_closed_positions(limit=10)
        
        assert len(positions) == 1
        assert positions[0]['RealizedPnL'] == '75.50'
        
        # Check payload
        call_args = mock_request.call_args
        payload = call_args[0][1]
        assert payload['Limit'] == '10'
        assert payload['Offset'] == '0'


class TestConsolidatedAccount:
    """Test the consolidated account management system"""
    
    def setup_method(self):
        """Setup test environment"""
        self.cfg = Config()
        self.sm = SessionManager(self.cfg)
        self.account_client = AccountClient(self.cfg, self.sm)
    
    def test_account_client_initialization(self):
        """Test AccountClient initializes correctly"""
        assert self.account_client.cfg == self.cfg
        assert self.account_client.sm == self.sm
    
    @patch.object(SessionManager, 'make_plus500_request')
    def test_get_plus500_account_summary(self, mock_request):
        """Test getting account summary"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'AccountId': 'test_account',
            'Currency': 'USD',
            'TotalEquity': '10000.00',
            'UnrealizedPnL': '150.00'
        }
        mock_request.return_value = mock_response
        
        summary = self.account_client.get_plus500_account_summary()
        
        assert summary['AccountId'] == 'test_account'
        assert summary['Currency'] == 'USD'
        mock_request.assert_called_once_with("GetAccountSummaryImm")
    
    @patch.object(SessionManager, 'make_plus500_request')
    def test_get_plus500_funds_info(self, mock_request):
        """Test getting funds information"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'TotalEquity': '10000.00',
            'AvailableCash': '8500.00',
            'UsedMargin': '1500.00',
            'FreeMargin': '8500.00'
        }
        mock_request.return_value = mock_response
        
        funds = self.account_client.get_plus500_funds_info()
        
        assert funds['TotalEquity'] == '10000.00'
        assert funds['UsedMargin'] == '1500.00'
        mock_request.assert_called_once_with("GetFundsInfoImm")
    
    @patch.object(AccountClient, 'get_plus500_funds_info')
    @patch.object(AccountClient, 'get_plus500_account_summary')
    def test_get_account_balance_summary(self, mock_account_summary, mock_funds_info):
        """Test getting account balance summary"""
        # Mock responses
        mock_funds_info.return_value = {
            'TotalEquity': '10000.00',
            'AvailableCash': '8500.00',
            'UsedMargin': '1500.00',
            'FreeMargin': '8500.00'
        }
        mock_account_summary.return_value = {
            'unrealized_pnl': '150.00',
            'realized_pnl': '250.00'
        }
        
        balance = self.account_client.get_account_balance_summary()
        
        assert balance['total_equity'] == Decimal('10000.00')
        assert balance['used_margin'] == Decimal('1500.00')
        assert balance['unrealized_pnl'] == Decimal('150.00')
    
    @patch.object(SessionManager, 'make_plus500_request')
    def test_switch_account_mode_to_demo(self, mock_request):
        """Test switching to demo account"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'Success': True,
            'AccountMode': 'Demo'
        }
        mock_request.return_value = mock_response
        
        result = self.account_client.switch_account_mode('Demo')
        
        assert result['Success'] is True
        assert result['AccountMode'] == 'Demo'
        mock_request.assert_called_once_with("SwitchToDemoImm")
    
    @patch.object(SessionManager, 'make_plus500_request')
    def test_switch_account_mode_to_live(self, mock_request):
        """Test switching to live account"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'Success': True,
            'AccountMode': 'Live'
        }
        mock_request.return_value = mock_response
        
        result = self.account_client.switch_account_mode('Live')
        
        assert result['Success'] is True
        assert result['AccountMode'] == 'Live'
        mock_request.assert_called_once_with("SwitchToRealImm")
    
    def test_switch_account_mode_invalid(self):
        """Test switching to invalid account mode"""
        with pytest.raises(ValueError, match="Mode must be 'Demo' or 'Live'"):
            self.account_client.switch_account_mode('Invalid')


class TestConsolidatedTradingAPI:
    """Test the Plus500TradingAPI class"""
    
    def setup_method(self):
        """Setup test environment"""
        self.cfg = Config()
        self.sm = SessionManager(self.cfg)
        # Mock the session property check
        with patch.object(self.sm, 'session', Mock()):
            self.trading_api = Plus500TradingAPI(self.cfg, self.sm)
    
    def test_trading_api_initialization(self):
        """Test Plus500TradingAPI initializes correctly"""
        assert self.trading_api.cfg == self.cfg
        assert self.trading_api.sm == self.sm
    
    def test_trading_api_initialization_no_session(self):
        """Test Plus500TradingAPI fails without session"""
        sm_no_session = SessionManager(self.cfg)
        
        # Mock the session to be None to trigger the error
        with patch.object(sm_no_session, 'session', None):
            with pytest.raises(AuthenticationError, match="Session manager must have an authenticated session"):
                Plus500TradingAPI(self.cfg, sm_no_session)
    
    @patch.object(SessionManager, 'make_plus500_request')
    def test_create_futures_order(self, mock_request):
        """Test creating futures order through TradingAPI"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'OrderId': '98765',
            'Status': 'Filled',
            'ExecutionPrice': '4500.00'
        }
        mock_request.return_value = mock_response
        
        result = self.trading_api.create_futures_order(
            instrument_id='ES.f',
            amount=2.0,
            direction='Buy',
            order_type='Market'
        )
        
        assert result['OrderId'] == '98765'
        assert result['Status'] == 'Filled'
        mock_request.assert_called_once()
    
    @patch.object(SessionManager, 'make_plus500_request')
    def test_get_futures_closed_positions(self, mock_request):
        """Test getting closed positions through TradingAPI"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'Positions': [
                {
                    'PositionId': '55555',
                    'InstrumentId': 'NQ.f',
                    'PnL': '125.75'
                }
            ],
            'TotalCount': 1
        }
        mock_request.return_value = mock_response
        
        result = self.trading_api.get_futures_closed_positions(limit=10)
        
        assert 'Positions' in result
        assert len(result['Positions']) == 1
        assert result['Positions'][0]['PnL'] == '125.75'
        mock_request.assert_called_once()


class TestSessionManager:
    """Test the SessionManager functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.cfg = Config()
        self.sm = SessionManager(self.cfg)
    
    def test_session_manager_initialization(self):
        """Test SessionManager initializes correctly"""
        assert self.sm.cfg == self.cfg
        assert hasattr(self.sm, 'session')
    
    def test_set_authenticated_session(self):
        """Test setting authenticated session"""
        mock_session = Mock()
        self.sm.set_authenticated_session(mock_session)
        
        assert self.sm._external_session == mock_session
        assert self.sm.session == mock_session
    
    @patch('requests.Session.post')
    def test_make_plus500_request(self, mock_post):
        """Test making Plus500 request"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': True}
        mock_post.return_value = mock_response
        
        # Set up authenticated session
        mock_session = Mock()
        mock_session.cookies = []
        self.sm.set_authenticated_session(mock_session)
        
        # Test request
        result = self.sm.make_plus500_request('TestEndpoint', {'test': 'data'})
        
        assert result.status_code == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
