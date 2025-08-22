from __future__ import annotations
import time
import threading
from decimal import Decimal
from typing import Dict, List, Optional, Callable
from .config import Config
from .session import SessionManager
from .models import Position, RiskManagementSettings, PartialTakeProfitRule
from .trading import TradingClient
from .errors import ValidationError
from .guards import tick_round

class PartialClosureValidator:
    """Validates partial take profit orders to ensure position integrity"""
    
    @staticmethod
    def validate_partial_tp(position: Position, partial_qty: Decimal) -> PartialTakeProfitRule:
        """
        CRITICAL SAFEGUARD: Ensure partial TP only executed when position > 1 contract
        Returns validation result with errors if any
        """
        rule = PartialTakeProfitRule(
            position_id=position.id,
            partial_qty=partial_qty,
            trigger_price=Decimal("0"),  # Will be set by caller
            remaining_qty_after=position.qty - partial_qty,
            is_valid=True,
            validation_errors=[]
        )
        
        # Check if position has more than 1 contract
        if position.qty <= Decimal("1"):
            rule.is_valid = False
            rule.validation_errors.append("Partial take profit requires position > 1 contract")
            return rule
        
        # Check if partial quantity is valid
        if partial_qty <= Decimal("0"):
            rule.is_valid = False
            rule.validation_errors.append("Partial quantity must be positive")
            return rule
            
        if partial_qty >= position.qty:
            rule.is_valid = False
            rule.validation_errors.append("Partial quantity cannot be equal to or greater than position size")
            return rule
        
        # Check if remaining quantity would be < 1 contract
        if rule.remaining_qty_after < Decimal("1"):
            rule.is_valid = False
            rule.validation_errors.append(
                f"Partial TP would leave position with {rule.remaining_qty_after} contracts. "
                f"Minimum remaining position must be ≥ 1 contract"
            )
            return rule
        
        # Additional safety: ensure partial quantity is at least 1 contract
        if partial_qty < Decimal("1"):
            rule.is_valid = False
            rule.validation_errors.append("Partial take profit quantity must be at least 1 contract")
            return rule
            
        return rule

class RiskManagementService:
    """Comprehensive risk management service with break-even protection and trailing stops"""
    
    def __init__(self, cfg: Config, sm: SessionManager, trading_client: TradingClient):
        self.cfg = cfg
        self.sm = sm
        self.trading_client = trading_client
        self.settings = RiskManagementSettings()
        self.position_monitors: Dict[str, PositionMonitor] = {}
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        
    def set_risk_settings(self, settings: RiskManagementSettings) -> None:
        """Update risk management settings"""
        self.settings = settings
        
    def start_monitoring(self) -> None:
        """Start position monitoring for break-even protection and trailing stops"""
        if self._running:
            return
            
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_positions, daemon=True)
        self._monitor_thread.start()
        
    def stop_monitoring(self) -> None:
        """Stop position monitoring"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
            
    def add_position_monitor(self, position: Position, entry_price: Decimal) -> None:
        """Add a position to risk management monitoring"""
        monitor = PositionMonitor(
            position=position,
            entry_price=entry_price,
            settings=self.settings,
            trading_client=self.trading_client
        )
        self.position_monitors[position.id] = monitor
        
    def remove_position_monitor(self, position_id: str) -> None:
        """Remove position from monitoring"""
        self.position_monitors.pop(position_id, None)
        
    def validate_partial_take_profit(self, position_id: str, partial_qty: Decimal) -> PartialTakeProfitRule:
        """Validate partial take profit with comprehensive safety checks"""
        # Get current position
        positions = self.trading_client.get_positions()
        position = next((p for p in positions if p.id == position_id), None)
        
        if not position:
            rule = PartialTakeProfitRule(
                position_id=position_id,
                partial_qty=partial_qty,
                trigger_price=Decimal("0"),
                remaining_qty_after=Decimal("0"),
                is_valid=False,
                validation_errors=["Position not found"]
            )
            return rule
            
        return PartialClosureValidator.validate_partial_tp(position, partial_qty)
        
    def execute_partial_take_profit(self, position_id: str, partial_qty: Decimal, 
                                   trigger_price: Decimal) -> bool:
        """Execute partial take profit with safety validation"""
        
        # Validate before execution
        validation = self.validate_partial_take_profit(position_id, partial_qty)
        if not validation.is_valid:
            raise ValidationError(f"Partial TP validation failed: {'; '.join(validation.validation_errors)}")
            
        # Get position for order details
        positions = self.trading_client.get_positions()
        position = next((p for p in positions if p.id == position_id), None)
        
        if not position:
            raise ValidationError("Position not found during execution")
            
        try:
            # Place partial close order
            close_side = "SELL" if position.side == "BUY" else "BUY"
            order = self.trading_client.place_take_profit_order(
                instrument_id=position.instrument_id,
                qty=partial_qty,
                limit_price=trigger_price,
                side=close_side
            )
            
            print(f"✓ Partial take profit order placed: {partial_qty} contracts at ${trigger_price}")
            print(f"  Remaining position: {validation.remaining_qty_after} contracts")
            
            return True
            
        except Exception as e:
            raise ValidationError(f"Failed to execute partial take profit: {e}")
            
    def _monitor_positions(self) -> None:
        """Background thread to monitor positions for risk management"""
        while self._running:
            try:
                # Update all position monitors
                for monitor in list(self.position_monitors.values()):
                    monitor.update()
                    
                time.sleep(1)  # Check every second
                
            except Exception as e:
                print(f"⚠ Risk management monitoring error: {e}")
                time.sleep(5)  # Wait longer on error

class PositionMonitor:
    """Monitors individual position for break-even protection and trailing stops"""
    
    def __init__(self, position: Position, entry_price: Decimal, 
                 settings: RiskManagementSettings, trading_client: TradingClient):
        self.position = position
        self.entry_price = entry_price
        self.settings = settings
        self.trading_client = trading_client
        self.break_even_activated = False
        self.trailing_activated = False
        self.highest_favorable_price = entry_price
        self.current_stop_loss_id: Optional[str] = None
        
    def update(self) -> None:
        """Update position monitoring and execute risk management logic"""
        try:
            # Get current position (it may have been closed)
            positions = self.trading_client.get_positions()
            current_pos = next((p for p in positions if p.id == self.position.id), None)
            
            if not current_pos:
                # Position closed, stop monitoring
                return
                
            self.position = current_pos
            current_price = self._get_current_price()
            
            if current_price is None:
                return
                
            # Update highest favorable price for trailing
            if self.position.side == "BUY" and current_price > self.highest_favorable_price:
                self.highest_favorable_price = current_price
            elif self.position.side == "SELL" and current_price < self.highest_favorable_price:
                self.highest_favorable_price = current_price
                
            # Check for break-even protection
            if self.settings.enable_break_even_protection and not self.break_even_activated:
                self._check_break_even_protection(current_price)
                
            # Check for trailing stop activation
            if self.settings.enable_trailing_stops and not self.trailing_activated:
                self._check_trailing_stop_activation(current_price)
            elif self.trailing_activated:
                self._update_trailing_stop(current_price)
                
        except Exception as e:
            print(f"⚠ Position monitor error for {self.position.id}: {e}")
            
    def _get_current_price(self) -> Optional[Decimal]:
        """Get current market price for the instrument"""
        try:
            from .marketdata import MarketDataClient
            market_client = MarketDataClient(self.trading_client.cfg, self.trading_client.sm)
            quote = market_client.get_quote(self.position.instrument_id)
            
            # Use bid for long positions, ask for short positions
            if self.position.side == "BUY":
                return Decimal(str(quote.bid)) if quote.bid else None
            else:
                return Decimal(str(quote.ask)) if quote.ask else None
                
        except Exception:
            return None
            
    def _check_break_even_protection(self, current_price: Decimal) -> None:
        """Check if break-even protection should be activated"""
        profit_pct = self._calculate_profit_percentage(current_price)
        
        if profit_pct >= self.settings.break_even_trigger_pct:
            try:
                self._move_stop_to_break_even()
                self.break_even_activated = True
                print(f"✓ Break-even protection activated for position {self.position.id}")
            except Exception as e:
                print(f"⚠ Failed to activate break-even protection: {e}")
                
    def _check_trailing_stop_activation(self, current_price: Decimal) -> None:
        """Check if trailing stop should be activated"""
        profit_pct = self._calculate_profit_percentage(current_price)
        
        if profit_pct >= self.settings.trailing_stop_trigger_pct:
            self.trailing_activated = True
            self._update_trailing_stop(current_price)
            print(f"✓ Trailing stop activated for position {self.position.id}")
            
    def _move_stop_to_break_even(self) -> None:
        """Move stop loss to break-even level"""
        # Calculate break-even price with buffer
        buffer_amount = Decimal(str(self.settings.break_even_buffer_ticks * 0.25))  # Assuming 0.25 tick size
        
        if self.position.side == "BUY":
            be_price = self.entry_price - buffer_amount
        else:
            be_price = self.entry_price + buffer_amount
            
        self._update_stop_loss(be_price)
        
    def _update_trailing_stop(self, current_price: Decimal) -> None:
        """Update trailing stop based on current price"""
        trail_distance = Decimal(str(self.settings.trailing_stop_distance_ticks * 0.25))
        
        if self.position.side == "BUY":
            new_stop = self.highest_favorable_price - trail_distance
        else:
            new_stop = self.highest_favorable_price + trail_distance
            
        self._update_stop_loss(new_stop)
        
    def _update_stop_loss(self, new_stop_price: Decimal) -> None:
        """Update or create stop loss order"""
        try:
            # Cancel existing stop loss if any
            if self.current_stop_loss_id:
                try:
                    self.trading_client.cancel_order(self.current_stop_loss_id)
                except:
                    pass
                    
            # Place new stop loss
            stop_side = "SELL" if self.position.side == "BUY" else "BUY"
            order = self.trading_client.place_stop_loss_order(
                instrument_id=self.position.instrument_id,
                qty=self.position.qty,
                stop_price=new_stop_price,
                side=stop_side
            )
            
            self.current_stop_loss_id = order.id
            
        except Exception as e:
            print(f"⚠ Failed to update stop loss: {e}")
            
    def _calculate_profit_percentage(self, current_price: Decimal) -> Decimal:
        """Calculate current profit percentage"""
        if self.position.side == "BUY":
            profit = current_price - self.entry_price
        else:
            profit = self.entry_price - current_price
            
        return (profit / self.entry_price) * Decimal("100")