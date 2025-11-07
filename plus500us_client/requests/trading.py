from __future__ import annotations
import uuid
from decimal import Decimal
from typing import Optional, List, Dict, Any
from .config import Config
from .session import SessionManager
from .models import OrderDraft, Order, BracketOrder, Position
from .guards import tick_round, ensure_qty_increment
from .errors import OrderRejectError, ValidationError

class TradingClient:
    def __init__(self, cfg: Config, sm: SessionManager):
        self.cfg = cfg
        self.sm = sm

    def place_order(self, draft: OrderDraft, *, idempotency_key: Optional[str] = None) -> Order:
        meta = self.cfg.futures_metadata.get(draft.instrument_id.split()[0], {})
        tick_size = float(meta.get("tick_size", 0.25))
        min_qty = float(meta.get("min_qty", 1))
        if draft.limit_price:
            draft.limit_price = tick_round(draft.limit_price, tick_size)
        if draft.stop_price:
            draft.stop_price = tick_round(draft.stop_price, tick_size)
        ensure_qty_increment(draft.qty, min_qty)

        s = self.sm.session
        base = self.cfg.base_url
        headers = self.sm.inject_csrf({"X-Idempotency-Key": idempotency_key or str(uuid.uuid4())})
        payload = draft.model_dump()
        r = s.post(base + "/api/orders", json=payload, headers=headers, timeout=20)
        if r.status_code >= 400:
            raise OrderRejectError(f"Order rejected: {r.text}")
        data = r.json()
        return Order(**data)

    def modify_order(self, order_id: str, changes: dict) -> Order:
        s = self.sm.session
        base = self.cfg.base_url
        headers = self.sm.inject_csrf({})
        r = s.patch(base + f"/api/orders/{order_id}", json=changes, headers=headers, timeout=20)
        r.raise_for_status()
        return Order(**r.json())

    def cancel_order(self, order_id: str) -> None:
        s = self.sm.session
        base = self.cfg.base_url
        headers = self.sm.inject_csrf({})
        r = s.delete(base + f"/api/orders/{order_id}", headers=headers, timeout=20)
        r.raise_for_status()

    def place_bracket_order(self, draft: OrderDraft, stop_loss_price: Optional[Decimal] = None, 
                           take_profit_price: Optional[Decimal] = None, *, idempotency_key: Optional[str] = None) -> BracketOrder:
        """Place a bracket order with automatic SL/TP setup"""
        
        # Generate OCO group ID for bracket
        oco_group_id = str(uuid.uuid4())
        
        # Place parent order first
        parent_order = self.place_order(draft, idempotency_key=idempotency_key)
        
        bracket = BracketOrder(
            parent_order_id=parent_order.id,
            oco_group_id=oco_group_id
        )
        
        try:
            # Place stop loss order if specified
            if stop_loss_price:
                sl_draft = self._create_stop_loss_order(draft, stop_loss_price, oco_group_id)
                sl_order = self.place_order(sl_draft)
                bracket.stop_loss_order_id = sl_order.id
            
            # Place take profit order if specified  
            if take_profit_price:
                tp_draft = self._create_take_profit_order(draft, take_profit_price, oco_group_id)
                tp_order = self.place_order(tp_draft)
                bracket.take_profit_order_id = tp_order.id
                
            # Calculate risk/reward amounts
            if stop_loss_price and take_profit_price:
                entry_price = draft.limit_price or Decimal("0")  # Will be filled price in reality
                bracket.risk_amount = abs(entry_price - stop_loss_price) * draft.qty
                bracket.reward_amount = abs(take_profit_price - entry_price) * draft.qty
                
        except Exception as e:
            # If SL/TP placement fails, cancel parent order
            try:
                self.cancel_order(parent_order.id)
            except:
                pass
            raise OrderRejectError(f"Bracket order setup failed: {e}")
            
        return bracket

    def place_stop_loss_order(self, instrument_id: str, qty: Decimal, stop_price: Decimal, 
                             side: str = "SELL", *, idempotency_key: Optional[str] = None) -> Order:
        """Place a standalone stop loss order"""
        
        draft = OrderDraft(
            instrument_id=instrument_id,
            side=side,  # type: ignore
            order_type="STOP",
            qty=qty,
            stop_price=stop_price,
            time_in_force="GTC"
        )
        
        return self.place_order(draft, idempotency_key=idempotency_key)

    def place_take_profit_order(self, instrument_id: str, qty: Decimal, limit_price: Decimal,
                               side: str = "SELL", *, idempotency_key: Optional[str] = None) -> Order:
        """Place a standalone take profit order"""
        
        draft = OrderDraft(
            instrument_id=instrument_id,
            side=side,  # type: ignore
            order_type="LIMIT",
            qty=qty,
            limit_price=limit_price,
            time_in_force="GTC"
        )
        
        return self.place_order(draft, idempotency_key=idempotency_key)

    def place_trailing_stop_order(self, instrument_id: str, qty: Decimal, trailing_amount: Decimal,
                                  side: str = "SELL", *, idempotency_key: Optional[str] = None) -> Order:
        """Place a trailing stop order"""
        
        draft = OrderDraft(
            instrument_id=instrument_id,
            side=side,  # type: ignore
            order_type="TRAILING_STOP",
            qty=qty,
            trailing=trailing_amount,
            time_in_force="GTC"
        )
        
        return self.place_order(draft, idempotency_key=idempotency_key)

    def get_positions(self) -> List[Position]:
        """Get all open positions"""
        s = self.sm.session
        base = self.cfg.base_url
        r = s.get(base + "/api/positions", timeout=15)
        r.raise_for_status()
        
        positions_data = r.json() if isinstance(r.json(), list) else r.json().get("positions", [])
        return [Position(**pos) for pos in positions_data]

    def get_orders(self, status: Optional[str] = None) -> List[Order]:
        """Get orders, optionally filtered by status"""
        s = self.sm.session
        base = self.cfg.base_url
        
        params = {}
        if status:
            params["status"] = status
            
        r = s.get(base + "/api/orders", params=params, timeout=15)
        r.raise_for_status()
        
        orders_data = r.json() if isinstance(r.json(), list) else r.json().get("orders", [])
        return [Order(**order) for order in orders_data]

    def _create_stop_loss_order(self, parent_draft: OrderDraft, stop_price: Decimal, oco_group_id: str) -> OrderDraft:
        """Create stop loss order draft"""
        sl_side = "SELL" if parent_draft.side == "BUY" else "BUY"
        
        return OrderDraft(
            instrument_id=parent_draft.instrument_id,
            side=sl_side,  # type: ignore
            order_type="STOP",
            qty=parent_draft.qty,
            stop_price=stop_price,
            time_in_force="GTC"
        )

    def _create_take_profit_order(self, parent_draft: OrderDraft, tp_price: Decimal, oco_group_id: str) -> OrderDraft:
        """Create take profit order draft"""
        tp_side = "SELL" if parent_draft.side == "BUY" else "BUY"
        
        return OrderDraft(
            instrument_id=parent_draft.instrument_id,
            side=tp_side,  # type: ignore
            order_type="LIMIT",
            qty=parent_draft.qty,
            limit_price=tp_price,
            time_in_force="GTC"
        )

    # ===============================
    # Plus500-Specific API Methods
    # ===============================

    def get_plus500_instruments(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get Plus500 trading instruments using ClientRequest API
        Endpoint: POST /ClientRequest/GetTradeInstruments
        """
        payload = {}
        if category:
            payload["SpecificCategory"] = category
            
        response = self.sm.make_plus500_request("GetTradeInstruments", payload)
        if response.status_code == 200:
            return response.json()
        else:
            raise OrderRejectError(f"Failed to get instruments: {response.status_code}")

    def create_plus500_order(self, instrument_id: str, amount: Decimal, operation_type: str,
                            order_type: str = "Market", limit_price: Optional[Decimal] = None,
                            stop_price: Optional[Decimal] = None) -> Dict[str, Any]:
        """
        Create Plus500 futures order using ClientRequest API
        Endpoint: POST /ClientRequest/FuturesCreateOrder
        """
        payload = {
            "InstrumentId": str(instrument_id),
            "Amount": str(amount),
            "OperationType": operation_type,  # "Buy" or "Sell"
            "OrderType": order_type,  # "Market", "Limit", "Stop"
        }
        
        if limit_price is not None:
            payload["LimitPrice"] = str(limit_price)
        if stop_price is not None:
            payload["StopPrice"] = str(stop_price)
            
        response = self.sm.make_plus500_request("FuturesCreateOrder", payload)
        if response.status_code == 200:
            return response.json()
        else:
            raise OrderRejectError(f"Failed to create order: {response.status_code}")

    def cancel_plus500_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel Plus500 order using ClientRequest API
        Endpoint: POST /ClientRequest/FuturesCancelOrder
        """
        payload = {"OrderId": str(order_id)}
        response = self.sm.make_plus500_request("FuturesCancelOrder", payload)
        if response.status_code == 200:
            return response.json()
        else:
            raise OrderRejectError(f"Failed to cancel order: {response.status_code}")

    def close_plus500_position(self, position_id: str, amount: Optional[Decimal] = None) -> Dict[str, Any]:
        """
        Close Plus500 position using ClientRequest API
        Endpoint: POST /ClientRequest/FuturesClosePosition
        """
        payload = {"PositionId": str(position_id)}
        if amount is not None:
            payload["Amount"] = str(amount)
            
        response = self.sm.make_plus500_request("FuturesClosePosition", payload)
        if response.status_code == 200:
            return response.json()
        else:
            raise OrderRejectError(f"Failed to close position: {response.status_code}")

    def get_plus500_open_positions(self) -> List[Dict[str, Any]]:
        """
        Get Plus500 open positions using ClientRequest API
        Endpoint: POST /ClientRequest/FuturesGetOpenPositions
        """
        response = self.sm.make_plus500_request("FuturesGetOpenPositions")
        if response.status_code == 200:
            return response.json()
        else:
            raise OrderRejectError(f"Failed to get open positions: {response.status_code}")

    def get_plus500_orders(self) -> List[Dict[str, Any]]:
        """
        Get Plus500 pending orders using ClientRequest API
        Endpoint: POST /ClientRequest/FuturesGetOrders
        """
        response = self.sm.make_plus500_request("FuturesGetOrders")
        if response.status_code == 200:
            return response.json()
        else:
            raise OrderRejectError(f"Failed to get orders: {response.status_code}")

    def get_plus500_closed_positions(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get Plus500 closed positions using ClientRequest API
        Endpoint: POST /ClientRequest/FuturesGetClosedPositions
        """
        payload = {
            "Limit": str(limit),
            "Offset": str(offset)
        }
        
        response = self.sm.make_plus500_request("FuturesGetClosedPositions", payload)
        if response.status_code == 200:
            return response.json()
        else:
            raise OrderRejectError(f"Failed to get closed positions: {response.status_code}")

    def get_plus500_buy_sell_info(self, instrument_id: str, amount: Decimal) -> Dict[str, Any]:
        """
        Get Plus500 buy/sell pricing info using ClientRequest API
        Endpoint: POST /ClientRequest/FuturesBuySellInfoImm
        """
        payload = {
            "InstrumentId": str(instrument_id),
            "Amount": str(amount)
        }
        
        response = self.sm.make_plus500_request("FuturesBuySellInfoImm", payload)
        if response.status_code == 200:
            return response.json()
        else:
            raise OrderRejectError(f"Failed to get buy/sell info: {response.status_code}")

    def edit_plus500_order(self, order_id: str, **changes) -> Dict[str, Any]:
        """
        Edit Plus500 order using ClientRequest API
        Endpoint: POST /ClientRequest/FuturesEditOrder
        
        Args:
            order_id: Order ID to edit
            **changes: Order parameters to change (amount, limit_price, stop_price, etc.)
        """
        payload = {"OrderId": str(order_id)}
        
        # Add any specified changes to the payload
        if 'amount' in changes:
            payload["Amount"] = str(changes['amount'])
        if 'limit_price' in changes:
            payload["LimitPrice"] = str(changes['limit_price'])
        if 'stop_price' in changes:
            payload["StopPrice"] = str(changes['stop_price'])
        if 'order_type' in changes:
            payload["OrderType"] = str(changes['order_type'])
            
        response = self.sm.make_plus500_request("FuturesEditOrder", payload)
        if response.status_code == 200:
            return response.json()
        else:
            raise OrderRejectError(f"Failed to edit order: {response.status_code}")

    def close_instrument_positions(self, instrument_id: str) -> Dict[str, Any]:
        """
        Close all positions for a specific instrument using ClientRequest API
        Endpoint: POST /ClientRequest/FuturesCloseInstrument
        
        Args:
            instrument_id: Instrument ID to close all positions for
        """
        payload = {"InstrumentId": str(instrument_id)}
        
        response = self.sm.make_plus500_request("FuturesCloseInstrument", payload)
        if response.status_code == 200:
            return response.json()
        else:
            raise OrderRejectError(f"Failed to close instrument positions: {response.status_code}")

    def add_risk_management_to_instrument(self, instrument_id: str, 
                                        stop_loss: Optional[Decimal] = None, 
                                        take_profit: Optional[Decimal] = None) -> Dict[str, Any]:
        """
        Add risk management (stop loss/take profit) to instrument using ClientRequest API
        Endpoint: POST /ClientRequest/FuturesAddRiskManagementToInstrument
        
        Args:
            instrument_id: Instrument ID to add risk management to
            stop_loss: Stop loss price (optional)
            take_profit: Take profit price (optional)
        """
        payload = {"InstrumentId": str(instrument_id)}
        
        if stop_loss is not None:
            payload["StopLoss"] = str(stop_loss)
        if take_profit is not None:
            payload["TakeProfit"] = str(take_profit)
            
        response = self.sm.make_plus500_request("FuturesAddRiskManagementToInstrument", payload)
        if response.status_code == 200:
            return response.json()
        else:
            raise OrderRejectError(f"Failed to add risk management: {response.status_code}")

    def get_edit_order_screen_data(self, order_id: str) -> Dict[str, Any]:
        """
        Get order edit screen data using ClientRequest API
        Endpoint: POST /ClientRequest/FuturesEditOrderScreenDataImm
        
        Args:
            order_id: Order ID to get edit screen data for
        """
        payload = {"OrderId": str(order_id)}
        
        response = self.sm.make_plus500_request("FuturesEditOrderScreenDataImm", payload)
        if response.status_code == 200:
            return response.json()
        else:
            raise OrderRejectError(f"Failed to get edit order screen data: {response.status_code}")

    def send_closed_positions_by_email(self, email: str, from_date: Optional[str] = None, 
                                     to_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Send closed positions report by email using ClientRequest API
        Endpoint: POST /ClientRequest/FuturesSendClosedPositionsByEmail
        
        Args:
            email: Email address to send report to
            from_date: Start date for report (YYYY-MM-DD format, optional)
            to_date: End date for report (YYYY-MM-DD format, optional)
        """
        payload = {"Email": str(email)}
        
        if from_date is not None:
            payload["FromDate"] = str(from_date)
        if to_date is not None:
            payload["ToDate"] = str(to_date)
            
        response = self.sm.make_plus500_request("FuturesSendClosedPositionsByEmail", payload)
        if response.status_code == 200:
            return response.json()
        else:
            raise OrderRejectError(f"Failed to send email report: {response.status_code}")
