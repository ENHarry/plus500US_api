from __future__ import annotations
from decimal import Decimal
from typing import Optional, Literal, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

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

# ===============================
# Plus500 API Endpoint Models
# ===============================

class Plus500SessionInfo(BaseModel):
    """Plus500 session authentication data"""
    session_id: str = Field(alias="SessionID")
    sub_session_id: str = Field(alias="SubSessionID") 
    session_token: str = Field(alias="SessionToken")
    user_id: Optional[str] = None
    account_id: Optional[str] = None
    account_type: Optional[str] = None
    
    class Config:
        allow_population_by_field_name = True

class Plus500InstrumentData(BaseModel):
    """Plus500 instrument information from GetTradeInstruments"""
    instrument_id: str = Field(alias="InstrumentID")
    symbol: str = Field(alias="Symbol")
    name: str = Field(alias="Name")
    category: Optional[str] = Field(default=None, alias="Category")
    subcategory: Optional[str] = Field(default=None, alias="SubCategory")
    bid_price: Optional[Decimal] = Field(default=None, alias="BidPrice")
    ask_price: Optional[Decimal] = Field(default=None, alias="AskPrice")
    last_price: Optional[Decimal] = Field(default=None, alias="LastPrice")
    change_percent: Optional[Decimal] = Field(default=None, alias="ChangePercent")
    high_price: Optional[Decimal] = Field(default=None, alias="HighPrice")
    low_price: Optional[Decimal] = Field(default=None, alias="LowPrice")
    is_tradable: bool = Field(default=True, alias="IsTradable")
    market_status: Optional[str] = Field(default=None, alias="MarketStatus")
    
    class Config:
        allow_population_by_field_name = True

class Plus500OrderRequest(BaseModel):
    """Plus500 order creation request"""
    instrument_id: str = Field(alias="InstrumentId")
    amount: Decimal = Field(alias="Amount")
    operation_type: Literal["Buy", "Sell"] = Field(alias="OperationType")
    order_type: Literal["Market", "Limit", "Stop"] = Field(alias="OrderType")
    duration_type: Literal["Day", "GTC"] = Field(default="Day", alias="DurationType")
    limit_price: Optional[Decimal] = Field(default=None, alias="LimitPrice")
    stop_price: Optional[Decimal] = Field(default=None, alias="StopPrice")
    take_profit_price_diff: Optional[Decimal] = Field(default=None, alias="TakeProfitPriceDiff")
    stop_loss_price_diff: Optional[Decimal] = Field(default=None, alias="StopLossPriceDiff")
    trailing_stop_price_diff: Optional[Decimal] = Field(default=None, alias="TrailingStopPriceDiff")
    session_id: str = Field(alias="SessionID")
    sub_session_id: str = Field(alias="SubSessionID")
    session_token: str = Field(alias="SessionToken")
    
    class Config:
        allow_population_by_field_name = True

class Plus500OrderResponse(BaseModel):
    """Plus500 order response"""
    order_id: Optional[str] = Field(default=None, alias="OrderId")
    status: str = Field(alias="Status")
    message: Optional[str] = Field(default=None, alias="Message")
    execution_price: Optional[Decimal] = Field(default=None, alias="ExecutionPrice")
    filled_amount: Optional[Decimal] = Field(default=None, alias="FilledAmount")
    remaining_amount: Optional[Decimal] = Field(default=None, alias="RemainingAmount")
    
    class Config:
        allow_population_by_field_name = True

class Plus500Position(BaseModel):
    """Plus500 position data"""
    position_id: str = Field(alias="PositionId")
    instrument_id: str = Field(alias="InstrumentId")
    instrument_name: str = Field(alias="InstrumentName")
    amount: Decimal = Field(alias="Amount")
    operation_type: Literal["Buy", "Sell"] = Field(alias="OperationType")
    open_price: Decimal = Field(alias="OpenPrice")
    current_price: Optional[Decimal] = Field(default=None, alias="CurrentPrice")
    unrealized_pnl: Optional[Decimal] = Field(default=None, alias="UnrealizedPnL")
    open_time: Optional[datetime] = Field(default=None, alias="OpenTime")
    margin_used: Optional[Decimal] = Field(default=None, alias="MarginUsed")
    
    class Config:
        allow_population_by_field_name = True

class Plus500ClosedPosition(BaseModel):
    """Plus500 closed position data"""
    position_id: str = Field(alias="PositionId")
    instrument_id: str = Field(alias="InstrumentId")
    instrument_name: str = Field(alias="InstrumentName")
    amount: Decimal = Field(alias="Amount")
    operation_type: Literal["Buy", "Sell"] = Field(alias="OperationType")
    open_price: Decimal = Field(alias="OpenPrice")
    close_price: Decimal = Field(alias="ClosePrice")
    realized_pnl: Decimal = Field(alias="RealizedPnL")
    open_time: datetime = Field(alias="OpenTime")
    close_time: datetime = Field(alias="CloseTime")
    
    class Config:
        allow_population_by_field_name = True

class Plus500AccountInfo(BaseModel):
    """Plus500 account information - Enhanced for Phase 2"""
    account_id: str = Field(alias="AccountId")
    account_type: str = Field(alias="AccountType")
    balance: Decimal = Field(alias="Balance")
    equity: Decimal = Field(alias="Equity")
    margin_used: Decimal = Field(alias="MarginUsed")
    available_margin: Decimal = Field(alias="AvailableMargin")
    unrealized_pnl: Decimal = Field(alias="UnrealizedPnL")
    currency: str = Field(default="USD", alias="Currency")
    
    # Phase 2 Enhanced Fields
    realized_pnl: Optional[Decimal] = Field(default=None, alias="RealizedPnL")
    daily_pnl: Optional[Decimal] = Field(default=None, alias="DailyPnL")
    max_leverage: Optional[Decimal] = Field(default=None, alias="MaxLeverage")
    account_status: str = Field(default="Active", alias="AccountStatus")
    trading_enabled: bool = Field(default=True, alias="TradingEnabled")
    risk_level: Optional[str] = Field(default=None, alias="RiskLevel")
    margin_level: Optional[Decimal] = Field(default=None, alias="MarginLevel")
    free_margin: Optional[Decimal] = Field(default=None, alias="FreeMargin")
    credit_line: Optional[Decimal] = Field(default=None, alias="CreditLine")
    total_orders: Optional[int] = Field(default=None, alias="TotalOrders")
    total_positions: Optional[int] = Field(default=None, alias="TotalPositions")
    last_login: Optional[datetime] = Field(default=None, alias="LastLogin")
    account_created: Optional[datetime] = Field(default=None, alias="AccountCreated")
    
    class Config:
        allow_population_by_field_name = True

class Plus500OrderInfo(BaseModel):
    """Plus500 pending order information"""
    order_id: str = Field(alias="OrderId")
    instrument_id: str = Field(alias="InstrumentId")
    instrument_name: str = Field(alias="InstrumentName")
    amount: Decimal = Field(alias="Amount")
    operation_type: Literal["Buy", "Sell"] = Field(alias="OperationType")
    order_type: str = Field(alias="OrderType")
    limit_price: Optional[Decimal] = Field(default=None, alias="LimitPrice")
    stop_price: Optional[Decimal] = Field(default=None, alias="StopPrice")
    status: str = Field(alias="Status")
    creation_time: datetime = Field(alias="CreationTime")
    
    class Config:
        allow_population_by_field_name = True

class Plus500ApiError(BaseModel):
    """Plus500 API error response"""
    error_code: str = Field(alias="ErrorCode")
    error_message: str = Field(alias="ErrorMessage")
    details: Optional[Dict[str, Any]] = Field(default=None, alias="Details")
    
    class Config:
        allow_population_by_field_name = True

# ===============================
# Phase 2 Enhanced Models
# ===============================

class Plus500FundsInfo(BaseModel):
    """Plus500 detailed funds information from GetFundsInfoImm"""
    total_equity: Decimal = Field(alias="TotalEquity")
    available_cash: Decimal = Field(alias="AvailableCash")
    used_margin: Decimal = Field(alias="UsedMargin")
    free_margin: Decimal = Field(alias="FreeMargin")
    maintenance_margin: Optional[Decimal] = Field(default=None, alias="MaintenanceMargin")
    overnight_funding: Optional[Decimal] = Field(default=None, alias="OvernightFunding")
    credit_limit: Optional[Decimal] = Field(default=None, alias="CreditLimit")
    margin_level: Optional[Decimal] = Field(default=None, alias="MarginLevel")
    buying_power: Optional[Decimal] = Field(default=None, alias="BuyingPower")
    max_position_size: Optional[Decimal] = Field(default=None, alias="MaxPositionSize")
    daily_loss_limit: Optional[Decimal] = Field(default=None, alias="DailyLossLimit")
    max_open_positions: Optional[int] = Field(default=None, alias="MaxOpenPositions")
    
    class Config:
        allow_population_by_field_name = True

class Plus500InstrumentPrice(BaseModel):
    """Plus500 real-time instrument pricing from GetInstrumentPricesImm"""
    instrument_id: str = Field(alias="InstrumentID")
    symbol: str = Field(alias="Symbol")
    bid_price: Decimal = Field(alias="BidPrice")
    ask_price: Decimal = Field(alias="AskPrice")
    last_price: Optional[Decimal] = Field(default=None, alias="LastPrice")
    change: Optional[Decimal] = Field(default=None, alias="Change")
    change_percent: Optional[Decimal] = Field(default=None, alias="ChangePercent")
    high_price: Optional[Decimal] = Field(default=None, alias="HighPrice")
    low_price: Optional[Decimal] = Field(default=None, alias="LowPrice")
    volume: Optional[int] = Field(default=None, alias="Volume")
    timestamp: Optional[datetime] = Field(default=None, alias="Timestamp")
    market_status: Optional[str] = Field(default=None, alias="MarketStatus")
    spread: Optional[Decimal] = Field(default=None, alias="Spread")
    
    class Config:
        allow_population_by_field_name = True

class Plus500ChartData(BaseModel):
    """Plus500 chart data from GetChartDataImm"""
    instrument_id: str = Field(alias="InstrumentID")
    timeframe: str = Field(alias="Timeframe")
    timestamp: datetime = Field(alias="Timestamp")
    open_price: Decimal = Field(alias="OpenPrice")
    high_price: Decimal = Field(alias="HighPrice")
    low_price: Decimal = Field(alias="LowPrice")
    close_price: Decimal = Field(alias="ClosePrice")
    volume: Optional[int] = Field(default=None, alias="Volume")
    
    class Config:
        allow_population_by_field_name = True

class Plus500MarginCalculation(BaseModel):
    """Plus500 margin calculation from CalculateMarginImm"""
    instrument_id: str = Field(alias="InstrumentID")
    amount: Decimal = Field(alias="Amount")
    required_margin: Decimal = Field(alias="RequiredMargin")
    leverage: Decimal = Field(alias="Leverage")
    margin_rate: Decimal = Field(alias="MarginRate")
    overnight_fee: Optional[Decimal] = Field(default=None, alias="OvernightFee")
    minimum_amount: Optional[Decimal] = Field(default=None, alias="MinimumAmount")
    maximum_amount: Optional[Decimal] = Field(default=None, alias="MaximumAmount")
    
    class Config:
        allow_population_by_field_name = True

class Plus500OrderValidation(BaseModel):
    """Plus500 order validation from ValidateOrderImm"""
    is_valid: bool = Field(alias="IsValid")
    validation_errors: List[str] = Field(default=[], alias="ValidationErrors")
    estimated_margin: Optional[Decimal] = Field(default=None, alias="EstimatedMargin")
    estimated_overnight_fee: Optional[Decimal] = Field(default=None, alias="EstimatedOvernightFee")
    minimum_distance: Optional[Decimal] = Field(default=None, alias="MinimumDistance")
    maximum_amount: Optional[Decimal] = Field(default=None, alias="MaximumAmount")
    leverage_available: Optional[Decimal] = Field(default=None, alias="LeverageAvailable")
    
    class Config:
        allow_population_by_field_name = True

class Plus500BuySellInfo(BaseModel):
    """Plus500 pre-trade information from FuturesBuySellInfoImm"""
    instrument_id: str = Field(alias="InstrumentID")
    symbol: str = Field(alias="Symbol")
    bid_price: Decimal = Field(alias="BidPrice")
    ask_price: Decimal = Field(alias="AskPrice")
    spread: Decimal = Field(alias="Spread")
    leverage: Decimal = Field(alias="Leverage")
    margin_rate: Decimal = Field(alias="MarginRate")
    overnight_fee_buy: Optional[Decimal] = Field(default=None, alias="OvernightFeeBuy")
    overnight_fee_sell: Optional[Decimal] = Field(default=None, alias="OvernightFeeSell")
    minimum_amount: Decimal = Field(alias="MinimumAmount")
    maximum_amount: Decimal = Field(alias="MaximumAmount")
    pip_value: Optional[Decimal] = Field(default=None, alias="PipValue")
    tick_size: Optional[Decimal] = Field(default=None, alias="TickSize")
    market_hours: Optional[str] = Field(default=None, alias="MarketHours")
    
    class Config:
        allow_population_by_field_name = True
