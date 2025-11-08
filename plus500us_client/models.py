"""
Data models for the Plus500US API client.
Re-exports all model classes for backward compatibility.
"""

from .requests.models import (
    # Core trading models
    OrderDraft,
    Order,
    Position,
    BracketOrder,
    
    # Account models
    Account,
    
    # Market data models
    Instrument,
    Quote,
    
    # Plus500 specific models
    Plus500SessionInfo,
    Plus500InstrumentData,
    Plus500OrderRequest,
    Plus500OrderResponse,
    Plus500Position,
    Plus500ClosedPosition,
    Plus500AccountInfo,
    Plus500OrderInfo,
    Plus500ApiError,
    Plus500FundsInfo,
    Plus500InstrumentPrice,
    Plus500ChartData,
    
    # Risk management
    RiskManagementSettings,
    PartialTakeProfitRule,
    
    # Additional type literals
    OrderType,
    TimeInForce,
    Side,
)

__all__ = [
    'OrderDraft',
    'Order',
    'Position',
    'BracketOrder',
    'Account',
    'Instrument',
    'Quote',
    'Plus500SessionInfo',
    'Plus500InstrumentData',
    'Plus500OrderRequest',
    'Plus500OrderResponse',
    'Plus500Position',
    'Plus500ClosedPosition',
    'Plus500AccountInfo',
    'Plus500OrderInfo',
    'Plus500ApiError',
    'Plus500FundsInfo',
    'Plus500InstrumentPrice',
    'Plus500ChartData',
    'RiskManagementSettings',
    'PartialTakeProfitRule',
    'OrderType',
    'TimeInForce',
    'Side',
]