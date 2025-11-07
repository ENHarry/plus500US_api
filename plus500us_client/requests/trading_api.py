"""
Plus500 Trading API Client
Implements all discovered API methods from network capture analysis.
Integrated with the consolidated architecture.
"""

from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import time

from .config import Config
from .session import SessionManager
from .errors import AuthenticationError, AuthorizationError


class Plus500TradingAPI:
    """
    Complete Plus500 Trading API client implementing all discovered methods:
    
    Core Trading Methods:
    - FuturesCreateOrder
    - FuturesCloseInstrument
    - FuturesGetClosedPositions
    - FuturesInstrumentDetailsImm
    - FuturesBuySellInfoImm
    - FuturesAddRiskManagementToInstrument
    
    Account Management:
    - GetPostLoginInfoImm
    - SwitchToDemoImm
    - SwitchToRealImm
    - GetDemoEditFundsImm
    - GetFundsManagementInfoImm
    
    Market Data:
    - GetTradeInstruments
    - GetChartDataImm
    - UnsubscribeToVolumeBatchImm
    
    Generic:
    - GenericRequestImm
    """
    
    def __init__(self, cfg: Config, sm: SessionManager):
        """
        Initialize trading API with session manager
        
        Args:
            cfg: Configuration object
            sm: SessionManager with authenticated session
        """
        self.cfg = cfg
        self.sm = sm
        
        # Check if session is available
        if not hasattr(self.sm, 'session') or self.sm.session is None:
            raise AuthenticationError("Session manager must have an authenticated session")
    
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make a Plus500 API request using the session manager
        
        Args:
            endpoint: API endpoint name
            params: Request parameters
            
        Returns:
            API response as dictionary
            
        Raises:
            AuthenticationError: If request fails due to authentication
            AuthorizationError: If request fails due to authorization
        """
        try:
            response = self.sm.make_plus500_request(endpoint, params)
            
            if response.status_code == 401:
                raise AuthenticationError("Session expired or invalid")
            elif response.status_code == 403:
                raise AuthorizationError("Access denied")
            elif response.status_code >= 400:
                raise AuthenticationError(f"API request failed: {response.status_code}")
            
            return response.json()
            
        except Exception as e:
            if isinstance(e, (AuthenticationError, AuthorizationError)):
                raise
            raise AuthenticationError(f"API request failed: {str(e)}")
    
    # === Core Trading Methods ===
    
    def create_futures_order(self, instrument_id: str, amount: float, direction: str,
                           order_type: str = "Market", stop_loss: Optional[float] = None,
                           take_profit: Optional[float] = None, limit_price: Optional[float] = None,
                           **kwargs) -> Dict[str, Any]:
        """
        Create a futures order
        
        Args:
            instrument_id: Instrument ID to trade
            amount: Order amount/size
            direction: "Buy" or "Sell"
            order_type: "Market", "Limit", "Stop"
            stop_loss: Stop loss price (optional)
            take_profit: Take profit price (optional)
            limit_price: Limit price for limit orders (optional)
            **kwargs: Additional order parameters
            
        Returns:
            Order creation result
        """
        
        params = {
            "InstrumentId": instrument_id,
            "Amount": amount,
            "Direction": direction,
            "OrderType": order_type,
            **kwargs
        }
        
        # Add optional parameters
        if stop_loss is not None:
            params["StopLoss"] = stop_loss
        if take_profit is not None:
            params["TakeProfit"] = take_profit
        if limit_price is not None:
            params["LimitPrice"] = limit_price
            
        return self._make_request("FuturesCreateOrder", params)
    
    def close_futures_position(self, position_id: str, amount: Optional[float] = None,
                             close_type: str = "Full") -> Dict[str, Any]:
        """
        Close a futures position
        
        Args:
            position_id: Position ID to close
            amount: Partial close amount (None for full close)
            close_type: "Full" or "Partial"
            
        Returns:
            Position close result
        """
        
        params = {
            "PositionId": position_id,
            "CloseType": close_type
        }
        
        if amount is not None:
            params["Amount"] = str(amount)
            
        return self._make_request("FuturesCloseInstrument", params)
    
    def get_futures_closed_positions(self, limit: int = 50, 
                                   from_date: Optional[datetime] = None,
                                   to_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get closed futures positions
        
        Args:
            limit: Maximum number of positions to return
            from_date: Start date filter (optional)
            to_date: End date filter (optional)
            
        Returns:
            Closed positions data
        """
        
        params: Dict[str, Any] = {"Limit": limit}
        
        if from_date:
            params["FromDate"] = from_date.isoformat()
        if to_date:
            params["ToDate"] = to_date.isoformat()
            
        return self._make_request("FuturesGetClosedPositions", params)
    
    def get_futures_instrument_details(self, instrument_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a futures instrument
        
        Args:
            instrument_id: Instrument ID
            
        Returns:
            Instrument details
        """
        
        params = {"InstrumentId": instrument_id}
        return self._make_request("FuturesInstrumentDetailsImm", params)
    
    def get_futures_buy_sell_info(self, instrument_id: str, amount: float) -> Dict[str, Any]:
        """
        Get buy/sell information for a futures instrument
        
        Args:
            instrument_id: Instrument ID
            amount: Trading amount
            
        Returns:
            Buy/sell pricing information
        """
        
        params = {
            "InstrumentId": instrument_id,
            "Amount": amount
        }
        
        return self._make_request("FuturesBuySellInfoImm", params)
    
    def add_risk_management_to_instrument(self, position_id: str, 
                                        stop_loss: Optional[float] = None,
                                        take_profit: Optional[float] = None) -> Dict[str, Any]:
        """
        Add risk management (SL/TP) to an existing position
        
        Args:
            position_id: Position ID
            stop_loss: Stop loss price (optional)
            take_profit: Take profit price (optional)
            
        Returns:
            Risk management update result
        """
        
        params: Dict[str, Any] = {"PositionId": position_id}
        
        if stop_loss is not None:
            params["StopLoss"] = stop_loss
        if take_profit is not None:
            params["TakeProfit"] = take_profit
            
        return self._make_request("FuturesAddRiskManagementToInstrument", params)
    
    # === Account Management Methods ===
    
    def get_post_login_info(self) -> Dict[str, Any]:
        """
        Get post-login account information
        
        Returns:
            Account information and settings
        """
        return self._make_request("GetPostLoginInfoImm")
    
    def switch_to_demo(self) -> Dict[str, Any]:
        """
        Switch to demo account
        
        Returns:
            Switch operation result
        """
        return self._make_request("SwitchToDemoImm")
    
    def switch_to_real(self) -> Dict[str, Any]:
        """
        Switch to real account
        
        Returns:
            Switch operation result
        """
        return self._make_request("SwitchToRealImm")
    
    def get_demo_edit_funds(self) -> Dict[str, Any]:
        """
        Get demo account funds editing information
        
        Returns:
            Demo funds information
        """
        return self._make_request("GetDemoEditFundsImm")
    
    def get_funds_management_info(self) -> Dict[str, Any]:
        """
        Get funds management information
        
        Returns:
            Funds management data
        """
        return self._make_request("GetFundsManagementInfoImm")
    
    # === Market Data Methods ===
    
    def get_trade_instruments(self, product_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get available trading instruments
        
        Args:
            product_type: Filter by product type (optional)
            
        Returns:
            List of available instruments
        """
        
        params = {}
        if product_type:
            params["ProductType"] = product_type
            
        return self._make_request("GetTradeInstruments", params)
    
    def get_chart_data(self, instrument_id: str, timeframe: str = "1H",
                      from_time: Optional[datetime] = None, 
                      to_time: Optional[datetime] = None,
                      bars_count: int = 100) -> Dict[str, Any]:
        """
        Get chart data for an instrument
        
        Args:
            instrument_id: Instrument ID
            timeframe: Chart timeframe (1M, 5M, 15M, 1H, 4H, 1D, etc.)
            from_time: Start time (optional)
            to_time: End time (optional)
            bars_count: Number of bars to retrieve
            
        Returns:
            Chart data
        """
        
        params = {
            "InstrumentId": instrument_id,
            "Timeframe": timeframe,
            "BarsCount": bars_count
        }
        
        if from_time:
            params["FromTime"] = from_time.isoformat()
        if to_time:
            params["ToTime"] = to_time.isoformat()
            
        return self._make_request("GetChartDataImm", params)
    
    def unsubscribe_to_volume_batch(self, instrument_ids: List[str]) -> Dict[str, Any]:
        """
        Unsubscribe from volume data for multiple instruments
        
        Args:
            instrument_ids: List of instrument IDs to unsubscribe from
            
        Returns:
            Unsubscribe operation result
        """
        
        params = {"InstrumentIds": instrument_ids}
        return self._make_request("UnsubscribeToVolumeBatchImm", params)
    
    # === Generic Request Method ===
    
    def generic_request(self, request_type: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a generic API request
        
        Args:
            request_type: Type of request
            request_data: Request data
            
        Returns:
            Request result
        """
        
        params = {
            "RequestType": request_type,
            "RequestData": request_data
        }
        
        return self._make_request("GenericRequestImm", params)
    
    # === Convenience Methods ===
    
    def get_account_balance(self) -> Dict[str, Any]:
        """
        Get current account balance information
        
        Returns:
            Balance data from post-login info
        """
        
        account_info = self.get_post_login_info()
        
        # Extract balance information
        balance_info = {}
        if "Balance" in account_info:
            balance_info["balance"] = account_info["Balance"]
        if "Equity" in account_info:
            balance_info["equity"] = account_info["Equity"]
        if "Margin" in account_info:
            balance_info["margin"] = account_info["Margin"]
        if "FreeMargin" in account_info:
            balance_info["free_margin"] = account_info["FreeMargin"]
            
        return balance_info
    
    def get_open_positions(self) -> Dict[str, Any]:
        """
        Get all open positions
        
        Returns:
            Open positions data
        """
        
        # Use post-login info which typically includes position data
        account_info = self.get_post_login_info()
        
        if "Positions" in account_info:
            return {"positions": account_info["Positions"]}
        elif "OpenPositions" in account_info:
            return {"positions": account_info["OpenPositions"]}
        else:
            return {"positions": []}
    
    def search_instruments(self, search_term: str) -> List[Dict[str, Any]]:
        """
        Search for instruments by name or symbol
        
        Args:
            search_term: Search term (symbol, name, etc.)
            
        Returns:
            List of matching instruments
        """
        
        instruments_data = self.get_trade_instruments()
        instruments = instruments_data.get("InstrumentList", [])
        
        # Search in instrument name, symbol, and description
        matching_instruments = []
        search_term_lower = search_term.lower()
        
        for instrument in instruments:
            name = instrument.get("Name", "").lower()
            symbol = instrument.get("Symbol", "").lower()
            description = instrument.get("Description", "").lower()
            
            if (search_term_lower in name or 
                search_term_lower in symbol or 
                search_term_lower in description):
                matching_instruments.append(instrument)
                
        return matching_instruments
    
    def place_market_order(self, symbol: str, amount: float, direction: str,
                          stop_loss: Optional[float] = None,
                          take_profit: Optional[float] = None) -> Dict[str, Any]:
        """
        Convenience method to place a market order
        
        Args:
            symbol: Instrument symbol
            amount: Order amount
            direction: "Buy" or "Sell"
            stop_loss: Stop loss price (optional)
            take_profit: Take profit price (optional)
            
        Returns:
            Order result
        """
        
        # Find instrument by symbol
        instruments = self.search_instruments(symbol)
        if not instruments:
            raise ValueError(f"Instrument not found: {symbol}")
            
        instrument_id = instruments[0].get("InstrumentId")
        if not instrument_id:
            raise ValueError(f"No instrument ID found for: {symbol}")
            
        return self.create_futures_order(
            instrument_id=instrument_id,
            amount=amount,
            direction=direction,
            order_type="Market",
            stop_loss=stop_loss,
            take_profit=take_profit
        )
    
    def close_all_positions(self) -> List[Dict[str, Any]]:
        """
        Close all open positions
        
        Returns:
            List of close operation results
        """
        
        positions_data = self.get_open_positions()
        positions = positions_data.get("positions", [])
        
        results = []
        for position in positions:
            position_id = position.get("PositionId")
            if position_id:
                try:
                    result = self.close_futures_position(position_id)
                    results.append({
                        "position_id": position_id,
                        "status": "success",
                        "result": result
                    })
                except Exception as e:
                    results.append({
                        "position_id": position_id,
                        "status": "error",
                        "error": str(e)
                    })
                    
        return results
