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
