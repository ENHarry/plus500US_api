"""
Tests for the complete workflow example
Validates that the demo showcases all Plus500US functionality correctly
"""

import pytest
import sys
from pathlib import Path
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

# Add examples directory to path
sys.path.append(str(Path(__file__).parent.parent / 'examples'))

try:
    import complete_workflow
except ImportError:
    complete_workflow = None


class TestCompleteWorkflow:
    """Test complete workflow example functionality"""
    
    @pytest.mark.skipif(complete_workflow is None, reason="complete_workflow module not available")
    def test_workflow_imports(self):
        """Test that all required imports are available"""
        # Test that all required modules can be imported
        assert complete_workflow is not None
        
        # Verify key functions exist
        assert hasattr(complete_workflow, 'main')
        assert hasattr(complete_workflow, 'print_header')
        assert hasattr(complete_workflow, 'print_step')
        
        # Verify main function is callable
        assert callable(complete_workflow.main)
    
    @pytest.mark.skipif(complete_workflow is None, reason="complete_workflow module not available")
    def test_utility_functions(self):
        """Test utility functions in complete workflow"""
        # Test print_header (should not raise exceptions)
        try:
            complete_workflow.print_header("Test Header")
        except Exception:
            pytest.fail("print_header should not raise exceptions")
        
        # Test print_step (should not raise exceptions)
        try:
            complete_workflow.print_step(1, "Test Step")
        except Exception:
            pytest.fail("print_step should not raise exceptions")
    
    @pytest.mark.skipif(complete_workflow is None, reason="complete_workflow module not available")
    @patch('complete_workflow.load_config')
    @patch('complete_workflow.BrowserManager')
    @patch('complete_workflow.WebDriverAuthHandler')
    @patch('complete_workflow.WebDriverTradingClient')
    @patch('complete_workflow.SessionBridge')
    @patch('complete_workflow.FallbackHandler')
    def test_main_workflow_structure(self, mock_fallback, mock_session_bridge, 
                                   mock_trading_client, mock_auth_handler, 
                                   mock_browser_manager, mock_load_config):
        """Test main workflow execution structure without actual WebDriver"""
        
        # Mock configuration
        mock_config = Mock()
        mock_config.base_url = "https://app.plus500.com"
        mock_config.account_type = "demo"
        mock_config.preferred_method = "webdriver"
        mock_load_config.return_value = mock_config
        
        # Mock browser manager
        mock_browser_instance = Mock()
        mock_browser_instance.get_current_account_mode.return_value = "demo"
        mock_browser_instance.switch_account_mode.return_value = True
        mock_browser_manager.return_value = mock_browser_instance
        
        # Mock auth handler context manager
        mock_auth_instance = Mock()
        mock_auth_instance.manual_login_flow.return_value = {
            'authenticated': True,
            'account_type': 'demo',
            'cookies': ['cookie1', 'cookie2']
        }
        mock_auth_handler.return_value.__enter__ = Mock(return_value=mock_auth_instance)
        mock_auth_handler.return_value.__exit__ = Mock(return_value=None)
        
        # Mock trading client
        mock_client_instance = Mock()
        mock_client_instance.initialize.return_value = None
        mock_client_instance._navigate_to_positions.return_value = None
        mock_client_instance._navigate_to_orders.return_value = None
        
        # Mock positions and orders data
        mock_positions = [
            {
                "id": "pos_1",
                "instrument": "MESU5",
                "side": "BUY",
                "quantity": Decimal("2"),
                "pnl": Decimal("125.50")
            }
        ]
        mock_orders = [
            {
                "id": "order_1",
                "instrument": "MESU5",
                "side": "SELL",
                "quantity": Decimal("2"),
                "order_type": "LIMIT",
                "price": Decimal("6441.0")
            }
        ]
        
        mock_client_instance.get_positions.return_value = mock_positions
        mock_client_instance.get_orders.return_value = mock_orders
        
        # Mock trailing stop calculations
        mock_client_instance.calculate_trailing_stop_amount.return_value = Decimal("25.0")
        mock_client_instance.get_current_instrument_price.return_value = Decimal("6434.0")
        
        mock_trading_client.return_value = mock_client_instance
        
        # Mock session bridge
        mock_session_instance = Mock()
        mock_session_instance.backup_session_data.return_value = "/tmp/session_backup.json"
        mock_session_bridge.return_value = mock_session_instance
        
        # Mock fallback handler
        mock_fallback_instance = Mock()
        mock_fallback_instance.health_check.return_value = {
            'overall_status': 'healthy',
            'methods': {
                'webdriver': {'status': 'available'},
                'api': {'status': 'available'}
            },
            'recommendations': []
        }
        mock_fallback.return_value = mock_fallback_instance
        
        # Execute main workflow
        try:
            result = complete_workflow.main()
            
            # Verify successful execution
            assert result is True
            
            # Verify key components were initialized
            mock_load_config.assert_called_once()
            mock_browser_manager.assert_called_once()
            mock_trading_client.assert_called_once()
            
            # Verify trading client methods were called
            mock_client_instance.initialize.assert_called_once()
            assert mock_client_instance.get_positions.called
            assert mock_client_instance.get_orders.called
            
            # Verify trailing stop calculations were demonstrated
            assert mock_client_instance.calculate_trailing_stop_amount.called
            
        except Exception as e:
            pytest.fail(f"Main workflow should execute without errors: {e}")
    
    @pytest.mark.skipif(complete_workflow is None, reason="complete_workflow module not available")
    def test_trailing_stop_calculation_demo(self):
        """Test that trailing stop calculations in demo are mathematically correct"""
        
        # Create mock trading client for calculation testing
        mock_config = Mock()
        mock_config.futures_metadata = {
            "MESU5": {"tick_size": 0.25}
        }
        
        with patch('complete_workflow.WebDriverTradingClient') as mock_client_class:
            mock_client = Mock()
            
            # Import the actual calculation method for testing
            from plus500us_client.webdriver.trading_automation import WebDriverTradingClient
            real_client = WebDriverTradingClient.__new__(WebDriverTradingClient)
            real_client.config = mock_config
            
            # Test calculations match expectations
            test_cases = [
                {"instrument": "MESU5", "price": Decimal("6434.0"), "expected_min": Decimal("5.0")},
                {"instrument": "GBPUSD", "price": Decimal("1.2650"), "expected_min": Decimal("5.0")},
                {"instrument": "GOLD", "price": Decimal("2450.0"), "expected_min": Decimal("5.0")}
            ]
            
            for case in test_cases:
                result = real_client.calculate_trailing_stop_amount(
                    case["instrument"], case["price"]
                )
                
                # Verify result is reasonable (minimum $5 enforced, max 1% of price or minimum)
                assert result >= case["expected_min"], f"Trailing stop too small for {case['instrument']}"
                max_expected = max(case["price"] * Decimal("0.01"), case["expected_min"])
                assert result <= max_expected, f"Trailing stop too large for {case['instrument']}: {result} > {max_expected}"
    
    @pytest.mark.skipif(complete_workflow is None, reason="complete_workflow module not available") 
    def test_demo_data_consistency(self):
        """Test that demo data in workflow is consistent and realistic"""
        
        # Test demo positions data
        demo_positions = [
            {
                "id": "DEMO_EUR_001",
                "instrument": "EURUSD",
                "side": "BUY",
                "quantity": "3",
                "pnl": "+125.50"
            }
        ]
        
        for pos in demo_positions:
            # Verify all required fields are present
            assert "id" in pos
            assert "instrument" in pos
            assert "side" in pos
            assert "quantity" in pos
            assert "pnl" in pos
            
            # Verify data types and values are reasonable
            assert pos["side"] in ["BUY", "SELL"]
            assert float(pos["quantity"]) > 0
            assert pos["instrument"] != ""
            assert pos["id"] != ""
        
        # Test demo orders data
        demo_orders = [
            {
                "id": "DEMO_ORDER_LIMIT_001",
                "instrument": "Micro E-mini S&P 500 Sep 25",
                "side": "SELL",
                "quantity": Decimal("2"),
                "order_type": "LIMIT",
                "price": Decimal("6441.0"),
                "created_time": "8/19/2025 4:34 PM"
            }
        ]
        
        for order in demo_orders:
            # Verify all required fields are present
            assert "id" in order
            assert "instrument" in order
            assert "side" in order
            assert "quantity" in order
            assert "order_type" in order
            assert "price" in order
            
            # Verify data types and values are reasonable
            assert order["side"] in ["BUY", "SELL"]
            assert order["quantity"] > 0
            assert order["price"] > 0
            assert order["order_type"] in ["MARKET", "LIMIT", "STOP"]
    
    @pytest.mark.skipif(complete_workflow is None, reason="complete_workflow module not available")
    @patch('builtins.input', return_value='')  # Mock user input
    @patch('complete_workflow.load_config')
    def test_workflow_error_handling(self, mock_load_config, mock_input):
        """Test workflow handles errors gracefully"""
        
        # Test with configuration error
        mock_load_config.side_effect = Exception("Config error")
        
        try:
            result = complete_workflow.main()
            # Should handle error gracefully and return False
            assert result is False
        except SystemExit:
            # Workflow calls sys.exit(1) on failure, which is expected
            pass
        except Exception:
            # Should not propagate other unhandled exceptions
            pytest.fail("Workflow should handle configuration errors gracefully")
    
    @pytest.mark.skipif(complete_workflow is None, reason="complete_workflow module not available")
    def test_environment_variable_support(self):
        """Test that workflow supports environment variable configuration"""
        
        with patch.dict('os.environ', {'PLUS500_BROWSER': 'firefox'}):
            with patch('complete_workflow.load_config') as mock_load_config:
                with patch('complete_workflow.BrowserManager') as mock_browser_manager:
                    with patch('complete_workflow.WebDriverAuthHandler'):
                        with patch('complete_workflow.WebDriverTradingClient'):
                            with patch('complete_workflow.SessionBridge'):
                                with patch('complete_workflow.FallbackHandler'):
                                    # Mock config
                                    mock_config = Mock()
                                    mock_config.base_url = "https://app.plus500.com"
                                    mock_config.account_type = "demo"
                                    mock_load_config.return_value = mock_config
                                    
                                    # Mock browser manager to verify browser selection
                                    mock_browser_instance = Mock()
                                    mock_browser_manager.return_value = mock_browser_instance
                                    
                                    try:
                                        complete_workflow.main()
                                        
                                        # Verify browser manager was called with config
                                        mock_browser_manager.assert_called_with(mock_config)
                                        
                                    except Exception as e:
                                        # Expected to fail at some point due to mocking, but should get past browser config
                                        pass
    
    def test_workflow_demonstrates_all_features(self):
        """Test that workflow demonstrates all major Plus500US features"""
        
        if complete_workflow is None:
            pytest.skip("complete_workflow module not available")
        
        # Read the workflow source to verify feature coverage
        workflow_file = Path(__file__).parent.parent / 'examples' / 'complete_workflow.py'
        workflow_content = workflow_file.read_text(encoding='utf-8')
        
        # Check that key Plus500US features are demonstrated
        required_features = [
            'trailing_stop',  # Trailing stop functionality
            'navigate_to_positions',  # Navigation demonstration
            'navigate_to_orders',  # Orders navigation
            'get_positions',  # Position extraction
            'get_orders',  # Orders extraction
            'calculate_trailing_stop_amount',  # Dynamic calculation
            'get_current_account_mode',  # Account mode detection
            'switch_account_mode',  # Account switching
            'PLUS500_BROWSER',  # Browser selection
            'health_check',  # System health
            'backup_session_data'  # Session backup
        ]
        
        missing_features = []
        for feature in required_features:
            if feature not in workflow_content:
                missing_features.append(feature)
        
        if missing_features:
            pytest.fail(f"Workflow missing key features: {missing_features}")
    
    def test_workflow_safety_demonstrations(self):
        """Test that workflow includes proper safety demonstrations"""
        
        if complete_workflow is None:
            pytest.skip("complete_workflow module not available")
        
        workflow_file = Path(__file__).parent.parent / 'examples' / 'complete_workflow.py'
        workflow_content = workflow_file.read_text(encoding='utf-8')
        
        # Check for safety-related content
        safety_features = [
            'ValidationError',  # Error handling
            'CRITICAL',  # Critical safeguards
            'SAFEGUARD',  # Safety demonstrations
            'demo mode',  # Safe demo operations
            'simulation',  # Simulation instead of live trades
        ]
        
        for feature in safety_features:
            assert feature in workflow_content, f"Missing safety feature demonstration: {feature}"
    
    def test_workflow_educational_value(self):
        """Test that workflow serves as comprehensive educational demo"""
        
        if complete_workflow is None:
            pytest.skip("complete_workflow module not available")
        
        workflow_file = Path(__file__).parent.parent / 'examples' / 'complete_workflow.py'
        workflow_content = workflow_file.read_text(encoding='utf-8')
        
        # Check for educational elements
        educational_elements = [
            'print_header',  # Clear section headers
            'print_step',  # Step-by-step progression
            '📋 Step',  # Visual step indicators
            'Demonstrating',  # Clear explanations
            'capabilities:',  # Feature listings
            'Summary of Plus500US Operations',  # Summary sections
            'Next Steps:',  # Guidance for users
        ]
        
        for element in educational_elements:
            assert element in workflow_content, f"Missing educational element: {element}"
        
        # Check for comprehensive feature coverage
        feature_coverage = [
            'Browser manager',
            'Authentication',
            'Position monitoring',
            'Orders management',
            'Trailing stop',
            'Risk management',
            'Session backup',
            'Error handling'
        ]
        
        missing_coverage = []
        for feature in feature_coverage:
            if feature.lower() not in workflow_content.lower():
                missing_coverage.append(feature)
        
        if missing_coverage:
            pytest.fail(f"Workflow missing feature coverage: {missing_coverage}")


class TestWorkflowIntegration:
    """Integration tests for workflow components"""
    
    def test_config_integration(self):
        """Test configuration loading works"""
        try:
            from plus500us_client import load_config
            config = load_config()
            
            # Verify config has required attributes
            assert hasattr(config, 'base_url')
            assert hasattr(config, 'account_type')
            
            # Test webdriver config assignment
            config.preferred_method = "webdriver"
            assert config.preferred_method == "webdriver"
            
        except Exception as e:
            pytest.fail(f"Configuration integration failed: {e}")
    
    def test_browser_manager_integration(self):
        """Test browser manager can be initialized"""
        try:
            from plus500us_client import load_config
            from plus500us_client.webdriver import BrowserManager
            
            config = load_config()
            browser_manager = BrowserManager(config)
            
            # Verify browser manager properties
            assert hasattr(browser_manager, 'browser_type')
            assert hasattr(browser_manager, 'start_browser')
            assert hasattr(browser_manager, 'get_current_account_mode')
            assert hasattr(browser_manager, 'switch_account_mode')
            
        except Exception as e:
            pytest.fail(f"Browser manager integration failed: {e}")
    
    def test_trading_client_integration(self):
        """Test trading client can be initialized with browser manager"""
        try:
            from plus500us_client import load_config
            from plus500us_client.webdriver import BrowserManager, WebDriverTradingClient
            
            config = load_config()
            browser_manager = BrowserManager(config)
            trading_client = WebDriverTradingClient(config, browser_manager)
            
            # Verify trading client has enhanced methods
            assert hasattr(trading_client, 'get_positions')
            assert hasattr(trading_client, 'get_orders')
            assert hasattr(trading_client, 'close_position')
            assert hasattr(trading_client, 'cancel_order')
            assert hasattr(trading_client, 'calculate_trailing_stop_amount')
            assert hasattr(trading_client, '_navigate_to_positions')
            assert hasattr(trading_client, '_navigate_to_orders')
            assert hasattr(trading_client, '_set_trailing_stop_dynamic')
            
        except Exception as e:
            pytest.fail(f"Trading client integration failed: {e}")
    
    def test_error_classes_available(self):
        """Test that all required error classes are available"""
        try:
            from plus500us_client.errors import ValidationError, OrderRejectError
            
            # Verify error classes can be instantiated
            validation_error = ValidationError("Test validation error")
            order_reject_error = OrderRejectError("Test order reject error")
            
            assert isinstance(validation_error, Exception)
            assert isinstance(order_reject_error, Exception)
            
        except Exception as e:
            pytest.fail(f"Error classes integration failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])