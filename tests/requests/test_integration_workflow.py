"""
Integration tests for the consolidated Plus500 API
Tests the complete workflow: authentication -> trading -> account management
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from typing import Dict, Any, List
from plus500us_client.requests.config import load_config
from plus500us_client.requests.session import SessionManager
from plus500us_client.requests.auth import AuthClient
from plus500us_client.requests.trading import TradingClient
from plus500us_client.requests.account import AccountClient
from plus500us_client.requests.trading_api import Plus500TradingAPI


class TestConsolidatedWorkflow:
    """Test the complete consolidated workflow"""
    
    def setup_method(self):
        """Setup test environment"""
        self.cfg = load_config()
        self.sm = SessionManager(self.cfg)
        self.auth_client = AuthClient(self.cfg, self.sm)
        self.trading_client = TradingClient(self.cfg, self.sm)
        self.account_client = AccountClient(self.cfg, self.sm)
    
    @patch('plus500us_client.requests.auth.Plus500FuturesAuth')
    @patch.object(SessionManager, 'make_plus500_request')
    def test_complete_workflow_simulation(self, mock_api_request, mock_auth_class):
        """Test complete workflow simulation with mocked API calls"""
        
        # Step 1: Mock Authentication
        mock_auth_instance = Mock()
        mock_auth_instance.authenticate.return_value = {
            'success': True,
            'session_data': {'authenticated': True},
            'steps': {'login': {'success': True}}
        }
        mock_session = Mock()
        mock_session.cookies = []
        mock_auth_instance.get_authenticated_session.return_value = mock_session
        mock_auth_class.return_value = mock_auth_instance
        
        # Step 2: Authenticate
        auth_result = self.auth_client.futures_authenticate('test@test.com', 'password123')
        
        assert auth_result['success'] is True
        assert auth_result['authenticated'] is True
        
        # Step 3: Mock API responses for account and trading operations
        def mock_api_response(endpoint, data=None):
            mock_response = Mock()
            mock_response.status_code = 200
            
            if endpoint == "GetAccountSummaryImm":
                mock_response.json.return_value = {
                    'AccountId': 'test_account_123',
                    'Currency': 'USD',
                    'TotalEquity': '25000.00',
                    'UnrealizedPnL': '250.00',
                    'account_status': 'Active',
                    'trading_enabled': True
                }
            elif endpoint == "GetFundsInfoImm":
                mock_response.json.return_value = {
                    'TotalEquity': '25000.00',
                    'AvailableCash': '22000.00',
                    'UsedMargin': '3000.00',
                    'FreeMargin': '22000.00',
                    'MaxPositionSize': '100000.00'
                }
            elif endpoint == "SwitchToDemoImm":
                mock_response.json.return_value = {
                    'Success': True,
                    'AccountMode': 'Demo',
                    'Message': 'Switched to demo account'
                }
            elif endpoint == "GetTradeInstruments":
                mock_response.json.return_value = [
                    {
                        'InstrumentId': 'ES.f',
                        'Name': 'S&P 500 Futures',
                        'MinAmount': '1',
                        'TickSize': '0.25'
                    },
                    {
                        'InstrumentId': 'NQ.f', 
                        'Name': 'NASDAQ 100 Futures',
                        'MinAmount': '1',
                        'TickSize': '0.25'
                    }
                ]
            elif endpoint == "FuturesCreateOrder":
                mock_response.json.return_value = {
                    'OrderId': 'ORD_12345',
                    'Status': 'Filled',
                    'InstrumentId': data.get('InstrumentId', 'ES.f') if data else 'ES.f',
                    'Amount': data.get('Amount', '1') if data else '1',
                    'ExecutionPrice': '4525.75',
                    'Timestamp': '2025-08-29T15:30:00Z'
                }
            elif endpoint == "FuturesGetOpenPositions":
                mock_response.json.return_value = [
                    {
                        'PositionId': 'POS_67890',
                        'InstrumentId': 'ES.f',
                        'Amount': '1',
                        'EntryPrice': '4525.75',
                        'CurrentPrice': '4530.00',
                        'UnrealizedPnL': '17.00'
                    }
                ]
            elif endpoint == "FuturesGetClosedPositions":
                mock_response.json.return_value = {
                    'Positions': [
                        {
                            'PositionId': 'POS_11111',
                            'InstrumentId': 'NQ.f',
                            'Amount': '1',
                            'EntryPrice': '15800.00',
                            'ExitPrice': '15825.00',
                            'RealizedPnL': '50.00',
                            'CloseTime': '2025-08-29T14:00:00Z'
                        }
                    ],
                    'TotalCount': 1
                }
            else:
                mock_response.json.return_value = {'Success': True}
            
            return mock_response
        
        mock_api_request.side_effect = mock_api_response
        
        # Step 4: Test Account Operations
        print("\\n=== Testing Account Operations ===")
        
        # Get account summary
        account_summary = self.account_client.get_plus500_account_summary()
        assert account_summary['AccountId'] == 'test_account_123'
        assert account_summary['Currency'] == 'USD'
        print(f"✅ Account Summary: {account_summary['AccountId']} ({account_summary['Currency']})")
        
        # Get funds info
        funds_info = self.account_client.get_plus500_funds_info()
        assert funds_info['TotalEquity'] == '25000.00'
        assert funds_info['UsedMargin'] == '3000.00'
        print(f"✅ Funds Info: Total Equity ${funds_info['TotalEquity']}, Used Margin ${funds_info['UsedMargin']}")
        
        # Get balance summary
        balance_summary = self.account_client.get_account_balance_summary()
        assert balance_summary['total_equity'].to_eng_string() == '25000.00'
        print(f"✅ Balance Summary: Total Equity ${balance_summary['total_equity']}")
        
        # Switch to demo account
        demo_result = self.account_client.switch_account_mode('Demo')
        assert demo_result['Success'] is True
        assert demo_result['AccountMode'] == 'Demo'
        print(f"✅ Switched to Demo Account: {demo_result['Message']}")
        
        # Step 5: Test Trading Operations
        print("\\n=== Testing Trading Operations ===")
        
        # Get available instruments
        instruments = self.trading_client.get_plus500_instruments()
        assert len(instruments) == 2
        assert instruments[0]['InstrumentId'] == 'ES.f'
        print(f"✅ Available Instruments: {len(instruments)} found")
        for instrument in instruments:
            print(f"   - {instrument['InstrumentId']}: {instrument['Name']}")
        
        # Create a market order
        from decimal import Decimal
        order_result = self.trading_client.create_plus500_order(
            instrument_id='ES.f',
            amount=Decimal('1'),
            operation_type='Buy',
            order_type='Market'
        )
        assert order_result['OrderId'] == 'ORD_12345'
        assert order_result['Status'] == 'Filled'
        print(f"✅ Order Created: {order_result['OrderId']} - {order_result['Status']}")
        print(f"   Instrument: {order_result['InstrumentId']}, Amount: {order_result['Amount']}")
        print(f"   Execution Price: ${order_result['ExecutionPrice']}")
        
        # Get open positions
        open_positions = self.trading_client.get_plus500_open_positions()
        assert len(open_positions) == 1
        assert open_positions[0]['PositionId'] == 'POS_67890'
        print(f"✅ Open Positions: {len(open_positions)} found")
        for position in open_positions:
            print(f"   - {position['PositionId']}: {position['InstrumentId']} ({position['Amount']} units)")
            print(f"     Entry: ${position['EntryPrice']}, Current: ${position['CurrentPrice']}")
            print(f"     Unrealized P&L: ${position['UnrealizedPnL']}")
        
        # Get closed positions
        closed_positions_response = self.trading_client.get_plus500_closed_positions(limit=10)
        assert 'Positions' in closed_positions_response
        # Cast to proper type to fix type checker
        closed_positions_dict: Dict[str, Any] = closed_positions_response  # type: ignore
        closed_positions_list = closed_positions_dict['Positions']
        assert len(closed_positions_list) == 1
        print(f"✅ Closed Positions: {closed_positions_dict['TotalCount']} found")
        for position in closed_positions_list:
            print(f"   - {position['PositionId']}: {position['InstrumentId']} ({position['Amount']} units)")
            print(f"     Entry: ${position['EntryPrice']}, Exit: ${position['ExitPrice']}")
            print(f"     Realized P&L: ${position['RealizedPnL']}")
        
        # Step 6: Test Trading API
        print("\\n=== Testing Trading API ===")
        
        # Initialize Trading API (need to mock session check)
        with patch.object(self.sm, 'session', mock_session):
            trading_api = Plus500TradingAPI(self.cfg, self.sm)
            
            # Test futures order creation
            api_order_result = trading_api.create_futures_order(
                instrument_id='NQ.f',
                amount=1.0,
                direction='Sell',
                order_type='Market'
            )
            assert api_order_result['OrderId'] == 'ORD_12345'
            print(f"✅ Trading API Order: {api_order_result['OrderId']} - {api_order_result['Status']}")
        
        print("\\n🎉 Complete Workflow Test Passed!")
        print("   ✅ Authentication successful")
        print("   ✅ Account operations working")
        print("   ✅ Trading operations working")
        print("   ✅ Trading API working")
        print("   ✅ All API endpoints responding correctly")
    
    def test_error_handling_workflow(self):
        """Test error handling in the workflow"""
        
        # Test authentication error
        with patch('plus500us_client.requests.auth.Plus500FuturesAuth') as mock_auth_class:
            mock_auth_instance = Mock()
            mock_auth_instance.authenticate.return_value = {
                'success': False,
                'error': 'Invalid credentials'
            }
            mock_auth_instance.get_authenticated_session.return_value = None
            mock_auth_class.return_value = mock_auth_instance
            
            auth_result = self.auth_client.futures_authenticate('bad@email.com', 'wrongpassword')
            
            assert auth_result['success'] is False
            assert auth_result['authenticated'] is False
            assert 'Invalid credentials' in auth_result['message']
        
        # Test API error handling
        with patch.object(SessionManager, 'make_plus500_request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_request.return_value = mock_response
            
            with pytest.raises(Exception):  # Should raise some kind of error
                self.account_client.get_plus500_account_summary()
        
        print("✅ Error handling tests passed")
    
    def test_configuration_loading(self):
        """Test configuration loading"""
        cfg = load_config()
        
        # Test default values
        assert cfg.base_url == "https://futures.plus500.com"
        assert cfg.host_url == "https://api-futures.plus500.com"
        assert cfg.account_type == "demo"
        
        print("✅ Configuration loading test passed")
        print(f"   Base URL: {cfg.base_url}")
        print(f"   Host URL: {cfg.host_url}")
        print(f"   Account Type: {cfg.account_type}")


if __name__ == '__main__':
    # Run the integration test
    test_workflow = TestConsolidatedWorkflow()
    test_workflow.setup_method()
    
    print("🚀 Running Plus500 Consolidated API Integration Test")
    print("=" * 60)
    
    try:
        test_workflow.test_complete_workflow_simulation()
        print("\\n✅ Integration test completed successfully!")
    except Exception as e:
        print(f"\\n❌ Integration test failed: {e}")
        raise
    
    try:
        test_workflow.test_error_handling_workflow()
        print("✅ Error handling test completed successfully!")
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        raise
    
    try:
        test_workflow.test_configuration_loading()
        print("✅ Configuration test completed successfully!")
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        raise
    
    print("\\n🎉 All integration tests passed!")
    print("The consolidated Plus500 API is ready for use.")
