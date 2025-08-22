from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from .errors import ValidationError

def tick_round(price: Decimal, tick_size: float) -> Decimal:
    if tick_size <= 0:
        raise ValidationError("tick_size must be positive")
    q = Decimal(str(tick_size))
    return (price / q).to_integral_value(rounding=ROUND_HALF_UP) * q

def ensure_price_bands(last: Decimal, limit_price: Optional[Decimal], *, max_ticks: int, tick_size: float) -> None:
    if limit_price is None:
        return
    diff_ticks = abs((limit_price - last) / Decimal(str(tick_size)))
    if diff_ticks > max_ticks:
        raise ValidationError(f"Limit price {limit_price} is {diff_ticks} ticks from last {last}, exceeds {max_ticks}")

def ensure_qty_increment(qty: Decimal, min_qty: float) -> None:
    if qty < Decimal(str(min_qty)):
        raise ValidationError(f"Quantity {qty} below minimum {min_qty}")
