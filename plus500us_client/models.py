from __future__ import annotations
from decimal import Decimal
from typing import Optional, Literal
from pydantic import BaseModel

class Instrument(BaseModel):
    id: str
    symbol: str
    name: str
    market: Optional[str] = None
    exchange: Optional[str] = None
    root: Optional[str] = None
    expiry: Optional[str] = None
    tick_size: Optional[float] = None
    tick_value: Optional[float] = None
    min_qty: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    
    # Commission and margin data
    commission_rate: Optional[Decimal] = None
    commission_min: Optional[Decimal] = None
    overnight_fee_long: Optional[Decimal] = None
    overnight_fee_short: Optional[Decimal] = None
    initial_margin: Optional[Decimal] = None
    maintenance_margin: Optional[Decimal] = None
    max_position_size: Optional[Decimal] = None
    spread_typical: Optional[float] = None
    trading_hours_start: Optional[str] = None
    trading_hours_end: Optional[str] = None

class Quote(BaseModel):
    instrument_id: str
    bid: Optional[float] = None
    ask: Optional[float] = None
    last: Optional[float] = None
    timestamp: Optional[int] = None
    session: Optional[str] = None
    halted: Optional[bool] = None

OrderType = Literal["MARKET", "LIMIT", "STOP", "TRAILING_STOP"]
TimeInForce = Literal["DAY", "GTC", "FOK", "IOC"]
Side = Literal["BUY", "SELL"]

class OrderDraft(BaseModel):
    instrument_id: str
    side: Side
    order_type: OrderType
    qty: Decimal
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    time_in_force: TimeInForce = "DAY"
    tp: Optional[Decimal] = None
    sl: Optional[Decimal] = None
    trailing: Optional[Decimal] = None
    max_slippage_ticks: Optional[int] = None

class Order(BaseModel):
    id: str
    status: str
    filled_qty: Decimal = Decimal("0")
    avg_price: Optional[Decimal] = None
    create_time: Optional[int] = None
    update_time: Optional[int] = None
    oco_group_id: Optional[str] = None

class Position(BaseModel):
    id: str
    instrument_id: str
    side: Side
    qty: Decimal
    avg_price: Decimal
    unrealized_pnl: Optional[Decimal] = None
    realized_pnl: Optional[Decimal] = None
    margin_used: Optional[Decimal] = None

class Account(BaseModel):
    account_id: str
    account_type: str
    balance: Decimal
    available: Decimal
    margin_used: Decimal
    maintenance_margin: Optional[Decimal] = None
    pnl: Optional[Decimal] = None
    
    # Enhanced account information
    equity: Optional[Decimal] = None
    buying_power: Optional[Decimal] = None
    day_trading_buying_power: Optional[Decimal] = None
    initial_margin_req: Optional[Decimal] = None
    maintenance_margin_req: Optional[Decimal] = None
    currency: str = "USD"
    
    # Trading limits
    max_position_value: Optional[Decimal] = None
    max_daily_loss_limit: Optional[Decimal] = None
    max_orders_per_day: Optional[int] = None
    
    # Commission and fee rates
    commission_per_contract: Optional[Decimal] = None
    commission_percentage: Optional[Decimal] = None
    overnight_fee_rate: Optional[Decimal] = None

class RiskManagementSettings(BaseModel):
    """Risk management configuration"""
    break_even_trigger_pct: Decimal = Decimal("2.0")  # Move SL to BE when profit > 2%
    break_even_buffer_ticks: int = 1  # Buffer above/below entry price
    trailing_stop_trigger_pct: Decimal = Decimal("3.0")  # Start trailing at 3% profit
    trailing_stop_distance_ticks: int = 5  # Trail distance in ticks
    max_risk_per_trade_pct: Decimal = Decimal("2.0")  # Max 2% account risk per trade
    default_risk_reward_ratio: Decimal = Decimal("2.0")  # 1:2 risk reward
    enable_break_even_protection: bool = True
    enable_trailing_stops: bool = True

class BracketOrder(BaseModel):
    """OCO group for SL/TP management"""
    parent_order_id: str
    stop_loss_order_id: Optional[str] = None
    take_profit_order_id: Optional[str] = None
    oco_group_id: str
    risk_amount: Optional[Decimal] = None
    reward_amount: Optional[Decimal] = None

class PartialTakeProfitRule(BaseModel):
    """Rules for partial profit taking"""
    position_id: str
    partial_qty: Decimal
    trigger_price: Decimal
    remaining_qty_after: Decimal
    is_valid: bool = True
    validation_errors: list[str] = []
