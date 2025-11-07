from __future__ import annotations
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from decimal import Decimal

from .config import Config
from .session import SessionManager
from .models import Account, Plus500AccountInfo, Plus500Position, Plus500ClosedPosition
from .errors import AuthenticationError, TradingError


class AccountClient:
    """Enhanced Account Client with Plus500-specific operations for Phase 2"""
    
    def __init__(self, cfg: Config, sm: SessionManager):
        self.cfg = cfg
        self.sm = sm

    def get_account(self) -> Account:
        """Legacy account method for backward compatibility"""
        s = self.sm.session
        host = self.cfg.host_url
        r = s.get(host + "/ClientRequest/account", timeout=15)
        r.raise_for_status()
        return Account(**r.json())

    # Phase 2 Enhanced Plus500 Account Operations
    
    def get_plus500_account_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive Plus500 account summary
        Uses GetAccountSummaryImm endpoint for detailed account information
        """
        response = self.sm.make_plus500_request("GetAccountSummaryImm")
        
        if response.status_code == 200:
            return response.json()
        else:
            raise TradingError(f"Failed to get account summary: {response.status_code}")

    def get_plus500_funds_info(self) -> Dict[str, Any]:
        """
        Get detailed Plus500 funds and balance information
        Uses GetFundsInfoImm endpoint for real-time balance data
        """
        response = self.sm.make_plus500_request("GetFundsInfoImm")
        
        if response.status_code == 200:
            return response.json()
        else:
            raise TradingError(f"Failed to get funds info: {response.status_code}")

    def get_funds_management_info(self) -> Dict[str, Any]:
        """
        Get funds management information using ClientRequest API
        Endpoint: POST /ClientRequest/GetFundsManagementInfoImm
        """
        response = self.sm.make_plus500_request("GetFundsManagementInfoImm")
        
        if response.status_code == 200:
            return response.json()
        else:
            raise TradingError(f"Failed to get funds management info: {response.status_code}")

    def get_account_balance_summary(self) -> Dict[str, Decimal]:
        """
        Get simplified account balance summary with key metrics
        Returns essential balance information in a clean format
        """
        try:
            funds_info = self.get_plus500_funds_info()
            account_summary = self.get_plus500_account_summary()
            
            balance_summary = {
                'total_equity': Decimal(str(funds_info.get('TotalEquity', 0))),
                'available_cash': Decimal(str(funds_info.get('AvailableCash', 0))),
                'used_margin': Decimal(str(funds_info.get('UsedMargin', 0))),
                'free_margin': Decimal(str(funds_info.get('FreeMargin', 0))),
                'unrealized_pnl': Decimal(str(account_summary.get('unrealized_pnl', 0))),
                'realized_pnl_today': Decimal(str(account_summary.get('realized_pnl', 0)))
            }
            
            return balance_summary
            
        except Exception as e:
            raise TradingError(f"Failed to get balance summary: {str(e)}")

    def get_account_performance_metrics(self) -> Dict[str, Any]:
        """
        Calculate account performance metrics from current account data
        Returns performance indicators and risk metrics
        """
        try:
            balance = self.get_account_balance_summary()
            account_info = self.get_plus500_account_summary()
            
            # Calculate key performance metrics
            total_equity = balance['total_equity']
            used_margin = balance['used_margin']
            free_margin = balance['free_margin']
            
            metrics = {
                'account_leverage': float(used_margin / total_equity) if total_equity > 0 else 0.0,
                'margin_utilization': float(used_margin / (used_margin + free_margin)) if (used_margin + free_margin) > 0 else 0.0,
                'equity_to_margin_ratio': float(total_equity / used_margin) if used_margin > 0 else float('inf'),
                'risk_percentage': float(used_margin / total_equity * 100) if total_equity > 0 else 0.0,
                'unrealized_pnl_ratio': float(balance['unrealized_pnl'] / total_equity * 100) if total_equity > 0 else 0.0,
                'account_currency': account_info.get('currency', 'USD'),
                'account_type': account_info.get('account_type', 'Unknown'),
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
            return metrics
            
        except Exception as e:
            raise TradingError(f"Failed to calculate performance metrics: {str(e)}")

    def switch_account_mode(self, mode: str) -> Dict[str, Any]:
        """
        Switch between Demo and Live trading modes
        
        Args:
            mode: 'Demo' or 'Live'
            
        Returns:
            Response from account mode switch operation
        """
        if mode not in ['Demo', 'Live']:
            raise ValueError("Mode must be 'Demo' or 'Live'")
        
        endpoint = "SwitchToDemoImm" if mode == 'Demo' else "SwitchToRealImm"
        response = self.sm.make_plus500_request(endpoint)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise TradingError(f"Failed to switch account mode to {mode}: {response.status_code}")

    def get_margin_requirements(self, instrument_id: str, amount: float) -> Dict[str, Any]:
        """
        Calculate margin requirements for a potential position
        
        Args:
            instrument_id: Plus500 instrument identifier
            amount: Position size
            
        Returns:
            Margin calculation details
        """
        if not self.sm.has_valid_plus500_session():
            raise AuthenticationError("Valid Plus500 session required")
        
        session_info = self.sm._load_plus500_session()
        if not session_info:
            raise AuthenticationError("No active Plus500 session found")
        
        payload = {
            'SessionID': session_info.session_id,
            'SubSessionID': session_info.sub_session_id,
            'SessionToken': session_info.session_token,
            'InstrumentId': instrument_id,
            'Amount': str(amount)
        }
        
        response = self.sm.make_plus500_request('/CalculateMarginImm', payload)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise TradingError(f"Failed to calculate margin requirements: {response.status_code}")

    def get_account_limits(self) -> Dict[str, Any]:
        """
        Get account trading limits and restrictions
        Returns position limits, maximum leverage, etc.
        """
        try:
            account_info = self.get_plus500_account_summary()
            funds_info = self.get_plus500_funds_info()
            
            limits = {
                'max_leverage': account_info.get('max_leverage'),
                'max_position_size': funds_info.get('MaxPositionSize'),
                'daily_loss_limit': funds_info.get('DailyLossLimit'),
                'max_open_positions': funds_info.get('MaxOpenPositions'),
                'account_status': account_info.get('account_status', 'Unknown'),
                'trading_enabled': account_info.get('trading_enabled', True)
            }
            
            return limits
            
        except Exception as e:
            raise TradingError(f"Failed to get account limits: {str(e)}")

    def validate_account_status(self) -> bool:
        """
        Validate that the account is in good standing for trading
        
        Returns:
            True if account is ready for trading, False otherwise
        """
        try:
            account_info = self.get_plus500_account_summary()
            funds_info = self.get_plus500_funds_info()
            
            # Check account status
            if account_info.get('account_status') != 'Active':
                return False
            
            # Check if there's available margin
            available_cash = Decimal(str(funds_info.get('AvailableCash', 0)))
            if available_cash <= 0:
                return False
            
            # Check if trading is enabled
            if not account_info.get('trading_enabled', True):
                return False
            
            return True
            
        except Exception:
            return False
