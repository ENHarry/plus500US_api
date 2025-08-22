from __future__ import annotations
import time
import logging
from decimal import Decimal
from typing import Optional, List, Dict, Any, Union
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .browser_manager import BrowserManager
from .element_detector import ElementDetector
from .selectors import Plus500Selectors
from .utils import WebDriverUtils
from ..config import Config
from ..models import OrderDraft, Order, Position, BracketOrder
from ..errors import OrderRejectError, ValidationError

logger = logging.getLogger(__name__)

class WebDriverTradingClient:
    """Complete WebDriver-based trading automation with XPath/CSS selectors"""
    
    def __init__(self, config: Config, browser_manager: Optional[BrowserManager] = None):
        self.config = config
        self.browser_manager = browser_manager
        self.driver = None
        self.element_detector: Optional[ElementDetector] = None
        self.selectors = Plus500Selectors()
        self.utils = WebDriverUtils()
        
    def initialize(self, driver=None) -> None:
        """Initialize with WebDriver instance"""
        if driver:
            self.driver = driver
        elif self.browser_manager:
            self.driver = self.browser_manager.get_driver()
        else:
            raise RuntimeError("No WebDriver available. Provide driver or browser_manager.")
        
        self.element_detector = ElementDetector(self.driver)
        logger.info("WebDriver trading client initialized")
    
    def place_market_order(self, instrument_id: str, side: str, quantity: int,
                          stop_loss: Optional[Decimal] = None, 
                          take_profit: Optional[Decimal] = None,
                          trailing_stop: Optional[bool] = False,
                          trailing_stop_percentage: Optional[Decimal] = None) -> Dict[str, Any]:
        """
        Place market order via DOM interaction with enhanced risk management
        
        Args:
            instrument_id: Instrument to trade
            side: "BUY" or "SELL"
            quantity: Order quantity
            stop_loss: Optional stop loss price
            take_profit: Optional take profit price
            trailing_stop: Enable dynamic trailing stop
            trailing_stop_percentage: Custom trailing stop percentage
            
        Returns:
            Order result dictionary
        """
        logger.info(f"Placing market order: {side} {quantity} {instrument_id}")
        
        try:
            # Navigate to instrument
            self._navigate_to_instrument(instrument_id)
            
            # Select market order type
            self._select_order_type("MARKET")
            
            # Click buy or sell button
            if side.upper() == "BUY":
                button = self.element_detector.find_element_from_selector(
                    self.selectors.BUY_BUTTON, timeout=10
                )
            else:
                button = self.element_detector.find_element_from_selector(
                    self.selectors.SELL_BUTTON, timeout=10
                )
            
            if not button:
                raise OrderRejectError(f"Could not find {side} button for {instrument_id}")
            
            # Click the button using human-like interaction
            self.utils.human_like_click(self.driver, button)
            
            # Set quantity
            self._set_quantity(quantity)
            
            # Set risk management parameters
            if stop_loss:
                self._set_stop_loss(stop_loss)
            if take_profit:
                self._set_take_profit(take_profit)
            if trailing_stop:
                self._set_trailing_stop_dynamic(instrument_id, trailing_stop_percentage)
            
            # Submit order
            order_result = self._submit_order()
            
            logger.info(f"Market order placed successfully: {order_result}")
            return order_result
            
        except Exception as e:
            logger.error(f"Market order failed: {e}")
            raise OrderRejectError(f"Market order failed: {e}")
    
    def place_limit_order(self, instrument_id: str, side: str, quantity: Decimal, 
                         limit_price: Decimal, stop_loss: Optional[Decimal] = None,
                         take_profit: Optional[Decimal] = None,
                         trailing_stop: Optional[bool] = False,
                         trailing_stop_percentage: Optional[Decimal] = None) -> Dict[str, Any]:
        """
        Place limit order with price input automation and enhanced risk management
        
        Args:
            instrument_id: Instrument to trade
            side: "BUY" or "SELL"
            quantity: Order quantity
            limit_price: Limit price
            stop_loss: Optional stop loss price
            take_profit: Optional take profit price
            trailing_stop: Enable dynamic trailing stop
            trailing_stop_percentage: Custom trailing stop percentage
            
        Returns:
            Order result dictionary
        """
        logger.info(f"Placing limit order: {side} {quantity} {instrument_id} @ {limit_price}")
        
        try:
            # Navigate to instrument
            self._navigate_to_instrument(instrument_id)
            
            # Select limit order type
            self._select_order_type("LIMIT")
            
            # Set limit price
            self._set_limit_price(limit_price)
            
            # Click buy or sell button
            if side.upper() == "BUY":
                button = self.element_detector.find_element_from_selector(
                    self.selectors.BUY_BUTTON, timeout=10
                )
            else:
                button = self.element_detector.find_element_from_selector(
                    self.selectors.SELL_BUTTON, timeout=10
                )
            
            if not button:
                raise OrderRejectError(f"Could not find {side} button for limit order")
            
            self.utils.human_like_click(self.driver, button)
            
            # Set quantity
            self._set_quantity(quantity)
            
            # Set risk management orders
            if stop_loss:
                self._set_stop_loss(stop_loss)
            if take_profit:
                self._set_take_profit(take_profit)
            if trailing_stop:
                self._set_trailing_stop_dynamic(instrument_id, trailing_stop_percentage)
            
            # Submit order
            order_result = self._submit_order()
            
            logger.info(f"Limit order placed successfully: {order_result}")
            return order_result
            
        except Exception as e:
            logger.error(f"Limit order failed: {e}")
            raise OrderRejectError(f"Limit order failed: {e}")
    
    def place_stop_order(self, instrument_id: str, side: str, quantity: Decimal,
                        stop_price: Decimal) -> Dict[str, Any]:
        """
        Place stop order
        
        Args:
            instrument_id: Instrument to trade
            side: "BUY" or "SELL"
            quantity: Order quantity
            stop_price: Stop trigger price
            
        Returns:
            Order result dictionary
        """
        logger.info(f"Placing stop order: {side} {quantity} {instrument_id} @ {stop_price}")
        
        try:
            # Navigate to instrument
            self._navigate_to_instrument(instrument_id)
            
            # Select stop order type
            self._select_order_type("STOP")
            
            # Set stop price
            self._set_stop_price(stop_price)
            
            # Click buy or sell button
            if side.upper() == "BUY":
                button = self.element_detector.find_element_from_selector(
                    self.selectors.BUY_BUTTON, timeout=10
                )
            else:
                button = self.element_detector.find_element_from_selector(
                    self.selectors.SELL_BUTTON, timeout=10
                )
            
            if not button:
                raise OrderRejectError(f"Could not find {side} button for stop order")
            
            self.utils.human_like_click(self.driver, button)
            
            # Set quantity
            self._set_quantity(quantity)
            
            # Submit order
            order_result = self._submit_order()
            
            logger.info(f"Stop order placed successfully: {order_result}")
            return order_result
            
        except Exception as e:
            logger.error(f"Stop order failed: {e}")
            raise OrderRejectError(f"Stop order failed: {e}")
    
    def place_bracket_order(self, instrument_id: str, side: str, quantity: Decimal,
                           order_type: str = "MARKET", limit_price: Optional[Decimal] = None,
                           stop_loss: Optional[Decimal] = None, 
                           take_profit: Optional[Decimal] = None) -> Dict[str, Any]:
        """
        Place bracket order (parent order with SL/TP)
        
        Args:
            instrument_id: Instrument to trade
            side: "BUY" or "SELL"  
            quantity: Order quantity
            order_type: "MARKET" or "LIMIT"
            limit_price: Limit price (if limit order)
            stop_loss: Stop loss price
            take_profit: Take profit price
            
        Returns:
            Bracket order result
        """
        logger.info(f"Placing bracket order: {order_type} {side} {quantity} {instrument_id}")
        
        if order_type.upper() == "MARKET":
            return self.place_market_order(instrument_id, side, quantity, stop_loss, take_profit)
        else:
            return self.place_limit_order(instrument_id, side, quantity, limit_price, stop_loss, take_profit)
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """
        Extract positions from Plus500US trading interface
        
        Returns:
            List of position dictionaries with enhanced metadata
        """
        if not self.element_detector:
            raise RuntimeError("Trading client not initialized. Call initialize() first.")
            
        logger.info("Extracting positions from Plus500US interface")
        
        try:
            # Navigate to positions view
            self._navigate_to_positions()
            
            # Find Plus500US positions table container
            positions_container = self.element_detector.find_element_from_selector(
                self.selectors.POSITIONS_TABLE_CONTAINER, timeout=10
            )
            
            if not positions_container:
                logger.warning("No positions table container found")
                return []
            
            # Extract position rows using Plus500US specific selectors
            position_rows = self.element_detector.find_elements_robust(
                self.selectors.POSITION_ROWS, timeout=5
            )
            
            positions = []
            
            for row in position_rows:
                try:
                    position_data = self._extract_plus500_position_from_row(row)
                    if position_data:
                        positions.append(position_data)
                except Exception as e:
                    logger.warning(f"Failed to extract position from row: {e}")
                    continue
            
            logger.info(f"Found {len(positions)} positions")
            return positions
            
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []
    
    def close_position(self, position_id: str, quantity: Optional[Decimal] = None) -> bool:
        """
        Close position via Plus500US interface
        
        Args:
            position_id: Position identifier or instrument name
            quantity: Partial quantity to close (None for full close)
            
        Returns:
            True if successful
        """
        logger.info(f"Closing position: {position_id} (quantity: {quantity})")
        
        try:
            # Navigate to positions
            self._navigate_to_positions()
            
            # Find position using enhanced search
            position_data = self._find_position_by_identifier(position_id)
            if not position_data:
                raise ValidationError(f"Position {position_id} not found")
            
            position_row = position_data.get("row_element")
            if not position_row:
                raise ValidationError(f"Position row not available for {position_id}")
            
            # Find close button using Plus500US selectors
            close_button = self.element_detector.find_element_robust(
                self.selectors.POSITION_CLOSE_BUTTON, 
                parent=position_row, 
                timeout=5
            )
            
            if not close_button:
                # Try alternative close patterns
                close_button = position_row.find_element(
                    By.XPATH, ".//button[contains(text(), 'Close') or contains(@title, 'Close')]"
                )
            
            if not close_button:
                raise ValidationError(f"Close button not found for position {position_id}")
            
            # Click close button with human-like behavior
            self.utils.human_like_click(self.driver, close_button)
            time.sleep(1)
            
            # Handle partial quantity if specified
            if quantity:
                success = self._set_partial_close_quantity(quantity)
                if not success:
                    logger.warning("Failed to set partial close quantity, proceeding with full close")
            
            # Confirm closure
            self._confirm_position_close()
            
            # Verify position was closed
            time.sleep(2)
            verification_position = self._find_position_by_identifier(position_id)
            if verification_position:
                logger.warning(f"Position {position_id} may not have been fully closed")
            
            logger.info(f"Position {position_id} closed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to close position {position_id}: {e}")
            return False

    def close_all_positions(self) -> List[Dict[str, Any]]:
        """
        Close all open positions
        
        Returns:
            List of closure results
        """
        logger.info("Closing all open positions")
        
        try:
            # Get all current positions
            positions = self.get_positions()
            if not positions:
                logger.info("No positions to close")
                return []
            
            results = []
            
            for position in positions:
                try:
                    position_id = position.get("id") or position.get("instrument")
                    if position_id:
                        success = self.close_position(position_id)
                        results.append({
                            "position_id": position_id,
                            "instrument": position.get("instrument"),
                            "success": success,
                            "timestamp": time.time()
                        })
                        
                        # Add delay between closures
                        if success:
                            time.sleep(2)
                            
                except Exception as e:
                    logger.error(f"Failed to close position {position.get('id', 'unknown')}: {e}")
                    results.append({
                        "position_id": position.get("id", "unknown"),
                        "instrument": position.get("instrument"),
                        "success": False,
                        "error": str(e),
                        "timestamp": time.time()
                    })
            
            successful_closures = len([r for r in results if r.get("success")])
            logger.info(f"Closed {successful_closures}/{len(results)} positions")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to close all positions: {e}")
            return []
    
    def set_stop_loss(self, position_id: str, stop_loss_price: Decimal) -> bool:
        """
        Add/modify stop loss for existing position
        
        Args:
            position_id: Position identifier
            stop_loss_price: Stop loss price
            
        Returns:
            True if successful
        """
        logger.info(f"Setting stop loss for position {position_id} at {stop_loss_price}")
        
        try:
            # Find position row
            position_row = self._find_position_row(position_id)
            if not position_row:
                raise ValidationError(f"Position {position_id} not found")
            
            # Find stop loss input in row
            sl_input = self.element_detector.find_element_from_selector(
                self.selectors.STOP_LOSS_INPUT, timeout=5
            )
            
            if not sl_input:
                # Look for add SL button/link
                add_sl_button = position_row.find_element(
                    By.XPATH, ".//button[contains(text(), 'Add SL') or contains(@class, 'add-sl')]"
                )
                if add_sl_button:
                    self.utils.human_like_click(self.driver, add_sl_button)
                    time.sleep(1)
                    
                    # Try finding input again
                    sl_input = self.element_detector.find_element_from_selector(
                        self.selectors.STOP_LOSS_INPUT, timeout=5
                    )
            
            if not sl_input:
                raise ValidationError("Could not find stop loss input field")
            
            # Set stop loss price
            self.utils.human_like_type(self.driver, sl_input, str(stop_loss_price))
            
            # Confirm/save
            self._confirm_risk_management_change()
            
            logger.info(f"Stop loss set successfully for position {position_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set stop loss for position {position_id}: {e}")
            return False
    
    def set_take_profit(self, position_id: str, take_profit_price: Decimal) -> bool:
        """
        Add/modify take profit for existing position
        
        Args:
            position_id: Position identifier
            take_profit_price: Take profit price
            
        Returns:
            True if successful
        """
        logger.info(f"Setting take profit for position {position_id} at {take_profit_price}")
        
        try:
            # Find position row
            position_row = self._find_position_row(position_id)
            if not position_row:
                raise ValidationError(f"Position {position_id} not found")
            
            # Find take profit input
            tp_input = self.element_detector.find_element_from_selector(
                self.selectors.TAKE_PROFIT_INPUT, timeout=5
            )
            
            if not tp_input:
                # Look for add TP button/link
                add_tp_button = position_row.find_element(
                    By.XPATH, ".//button[contains(text(), 'Add TP') or contains(@class, 'add-tp')]"
                )
                if add_tp_button:
                    self.utils.human_like_click(self.driver, add_tp_button)
                    time.sleep(1)
                    
                    # Try finding input again
                    tp_input = self.element_detector.find_element_from_selector(
                        self.selectors.TAKE_PROFIT_INPUT, timeout=5
                    )
            
            if not tp_input:
                raise ValidationError("Could not find take profit input field")
            
            # Set take profit price
            self.utils.human_like_type(self.driver, tp_input, str(take_profit_price))
            
            # Confirm/save
            self._confirm_risk_management_change()
            
            logger.info(f"Take profit set successfully for position {position_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set take profit for position {position_id}: {e}")
            return False
    
    def execute_partial_take_profit(self, position_id: str, partial_quantity: Decimal) -> bool:
        """
        Execute partial position closure with quantity validation
        
        Args:
            position_id: Position identifier
            partial_quantity: Quantity to close partially
            
        Returns:
            True if successful
        """
        logger.info(f"Executing partial take profit: {position_id}, quantity: {partial_quantity}")
        
        try:
            # Get current position to validate quantity
            positions = self.get_positions()
            current_position = None
            
            for pos in positions:
                if pos.get('id') == position_id or pos.get('instrument') == position_id:
                    current_position = pos
                    break
            
            if not current_position:
                raise ValidationError(f"Position {position_id} not found")
            
            # Validate partial quantity (CRITICAL SAFEGUARD)
            current_qty = Decimal(str(current_position.get('quantity', 0)))
            
            if current_qty <= Decimal("1"):
                raise ValidationError("Partial take profit requires position > 1 contract")
            
            if partial_quantity >= current_qty:
                raise ValidationError("Partial quantity cannot be equal to or greater than position size")
            
            remaining_qty = current_qty - partial_quantity
            if remaining_qty < Decimal("1"):
                raise ValidationError(f"Partial TP would leave position with {remaining_qty} contracts. Minimum remaining position must be ≥ 1 contract")
            
            # Execute partial close
            return self.close_position(position_id, partial_quantity)
            
        except Exception as e:
            logger.error(f"Partial take profit failed: {e}")
            raise ValidationError(f"Partial take profit failed: {e}")
    
    def monitor_position_pnl(self, position_id: str) -> Optional[Decimal]:
        """
        Get real-time P&L for position
        
        Args:
            position_id: Position identifier
            
        Returns:
            Current P&L or None if not found
        """
        try:
            position_row = self._find_position_row(position_id)
            if not position_row:
                return None
            
            # Find P&L cell
            pnl_cell = position_row.find_element(
                By.XPATH, ".//td[contains(@class, 'pnl') or contains(@class, 'profit')]"
            )
            
            if pnl_cell:
                pnl_text = self.element_detector.extract_text_safe(pnl_cell)
                pnl_value = self.utils.extract_number_from_text(pnl_text)
                
                if pnl_value is not None:
                    return Decimal(str(pnl_value))
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to get P&L for position {position_id}: {e}")
            return None
    
    # Helper methods
    
    def _navigate_to_instrument(self, instrument_id: str) -> None:
        """Navigate to specific instrument trading page"""
        try:
            # Try to find instrument search
            search_input = self.element_detector.find_element_from_selector(
                self.selectors.INSTRUMENT_SEARCH, timeout=10
            )
            
            if search_input:
                self.utils.human_like_type(self.driver, search_input, instrument_id)
                time.sleep(2)
                
                # Look for instrument in results and click
                instrument_link = self.driver.find_element(
                    By.XPATH, f"//a[contains(text(), '{instrument_id}') or contains(@title, '{instrument_id}')]"
                )
                
                if instrument_link:
                    self.utils.human_like_click(self.driver, instrument_link)
                    time.sleep(2)
                    
        except Exception as e:
            logger.warning(f"Could not navigate to instrument {instrument_id}: {e}")
    
    def _navigate_to_positions(self) -> None:
        """Navigate to Plus500US positions view"""
        if not self.element_detector:
            raise RuntimeError("Trading client not initialized. Call initialize() first.")
            
        try:
            # Use Plus500US specific positions navigation
            positions_link = self.element_detector.find_element_from_selector(
                self.selectors.POSITIONS_NAV, timeout=10
            )
            
            if positions_link:
                self.utils.human_like_click(self.driver, positions_link)
                time.sleep(3)  # Allow time for table to load
                logger.info("Navigated to positions view")
            else:
                logger.warning("Could not find positions navigation link")
                
        except Exception as e:
            logger.error(f"Failed to navigate to positions: {e}")

    def _navigate_to_orders(self) -> None:
        """Navigate to Plus500US orders view"""
        if not self.element_detector:
            raise RuntimeError("Trading client not initialized. Call initialize() first.")
            
        try:
            # Use Plus500US specific orders navigation
            orders_link = self.element_detector.find_element_from_selector(
                self.selectors.ORDERS_NAV, timeout=10
            )
            
            if orders_link:
                self.utils.human_like_click(self.driver, orders_link)
                time.sleep(3)  # Allow time for table to load
                logger.info("Navigated to orders view")
            else:
                logger.warning("Could not find orders navigation link")
                
        except Exception as e:
            logger.error(f"Failed to navigate to orders: {e}")
    
    def _select_order_type(self, order_type: str) -> None:
        """Select order type (MARKET, LIMIT, STOP)"""
        try:
            if order_type.upper() == "MARKET":
                selector = self.selectors.MARKET_ORDER
            elif order_type.upper() == "LIMIT":
                selector = self.selectors.LIMIT_ORDER
            elif order_type.upper() == "STOP":
                selector = self.selectors.STOP_ORDER
            else:
                return
            
            order_type_element = self.element_detector.find_element_from_selector(selector, timeout=5)
            if order_type_element:
                self.utils.human_like_click(self.driver, order_type_element)
                time.sleep(0.5)
                
        except Exception as e:
            logger.debug(f"Could not select order type {order_type}: {e}")
    
    def _set_quantity(self, quantity: Decimal) -> None:
        """Set order quantity"""
        qty_input = self.element_detector.find_element_from_selector(
            self.selectors.QUANTITY_INPUT, timeout=5
        )
        
        if qty_input:
            self.utils.human_like_type(self.driver, qty_input, str(quantity))
    
    def _set_limit_price(self, price: Decimal) -> None:
        """Set limit price"""
        price_input = self.element_detector.find_element_from_selector(
            self.selectors.PRICE_INPUT, timeout=5
        )
        
        if price_input:
            self.utils.human_like_type(self.driver, price_input, str(price))
    
    def _set_stop_price(self, price: Decimal) -> None:
        """Set stop price"""
        # Use price input or look for specific stop price input
        stop_input = self.element_detector.find_element_from_selector(
            self.selectors.PRICE_INPUT, timeout=5
        )
        
        if stop_input:
            self.utils.human_like_type(self.driver, stop_input, str(price))
    
    def _set_stop_loss(self, stop_loss: Decimal) -> None:
        """Set stop loss price"""
        sl_input = self.element_detector.find_element_from_selector(
            self.selectors.STOP_LOSS_INPUT, timeout=5
        )
        
        if sl_input:
            self.utils.human_like_type(self.driver, sl_input, str(stop_loss))
    
    def _set_take_profit(self, take_profit: Decimal) -> None:
        """Set take profit price"""
        tp_input = self.element_detector.find_element_from_selector(
            self.selectors.TAKE_PROFIT_INPUT, timeout=5
        )
        
        if tp_input:
            self.utils.human_like_type(self.driver, tp_input, str(take_profit))
    
    def _submit_order(self) -> Dict[str, Any]:
        """Submit the order and wait for confirmation"""
        try:
            # Find and click confirm/submit button
            confirm_button = self.element_detector.find_element_from_selector(
                self.selectors.CONFIRM_ORDER, timeout=10
            )
            
            if not confirm_button:
                raise OrderRejectError("Could not find order confirmation button")
            
            # Click submit
            self.utils.human_like_click(self.driver, confirm_button)
            
            # Wait for order processing
            time.sleep(2)
            
            # Check for success/error messages
            success_msg = self.element_detector.find_element_from_selector(
                self.selectors.SUCCESS_MESSAGE, timeout=5
            )
            
            error_msg = self.element_detector.find_element_from_selector(
                self.selectors.ERROR_MESSAGE, timeout=2
            )
            
            if error_msg:
                error_text = self.element_detector.extract_text_safe(error_msg)
                raise OrderRejectError(f"Order rejected: {error_text}")
            
            # Extract order ID if available
            order_id = self._extract_order_id()
            
            return {
                "success": True,
                "order_id": order_id,
                "message": "Order placed successfully",
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Order submission failed: {e}")
            raise OrderRejectError(f"Order submission failed: {e}")
    
    def _extract_order_id(self) -> Optional[str]:
        """Extract order ID from confirmation message"""
        try:
            # Look for order ID in various formats
            order_id_patterns = [
                "//span[contains(text(), 'Order ID') or contains(text(), 'Reference')]",
                "//div[contains(@class, 'order-id')]",
                "//span[contains(@class, 'reference')]"
            ]
            
            for pattern in order_id_patterns:
                try:
                    element = self.driver.find_element(By.XPATH, pattern)
                    text = self.element_detector.extract_text_safe(element)
                    
                    # Extract ID from text
                    import re
                    id_match = re.search(r'(\d+)', text)
                    if id_match:
                        return id_match.group(1)
                except:
                    continue
            
            return None
            
        except Exception:
            return None
    
    def _find_position_by_identifier(self, identifier: str) -> Optional[Dict[str, Any]]:
        """
        Find position by ID or instrument name in Plus500US interface
        
        Args:
            identifier: Position ID or instrument name
            
        Returns:
            Position data dict or None if not found
        """
        try:
            # Get all current positions
            positions = self.get_positions()
            
            # Search by exact ID match first
            for position in positions:
                if position.get("id") == identifier:
                    return position
            
            # Search by instrument name
            for position in positions:
                instrument = position.get("instrument", "")
                if instrument and identifier.lower() in instrument.lower():
                    return position
            
            # Search by partial instrument match
            for position in positions:
                instrument = position.get("instrument", "")
                if instrument:
                    # Clean identifier and instrument for comparison
                    clean_identifier = identifier.replace(" ", "").lower()
                    clean_instrument = instrument.replace(" ", "").lower()
                    if clean_identifier in clean_instrument or clean_instrument in clean_identifier:
                        return position
            
            logger.debug(f"Position not found: {identifier}")
            return None
            
        except Exception as e:
            logger.debug(f"Error finding position {identifier}: {e}")
            return None

    def _find_position_row(self, position_id: str) -> Optional[object]:
        """Legacy method - find position row"""
        position_data = self._find_position_by_identifier(position_id)
        return position_data.get("row_element") if position_data else None
    
    def _extract_plus500_position_from_row(self, row) -> Optional[Dict[str, Any]]:
        """Extract position data from Plus500US table row"""
        try:
            # Plus500US uses div-based structure, not traditional table cells
            position_data = {
                "id": None,
                "instrument": None,
                "side": None,
                "quantity": None,
                "entry_price": None,
                "current_price": None,
                "pnl": None,
                "margin_used": None,
                "timestamp": time.time(),
                "row_element": row  # Store reference for actions
            }
            
            # Extract instrument name
            name_element = row.find_element(By.XPATH, ".//div[@class='name']/strong")
            if name_element:
                instrument_text = self.element_detector.extract_text_safe(name_element)
                position_data["instrument"] = instrument_text
                position_data["id"] = f"pos_{hash(instrument_text)}_{int(time.time())}"
            
            # Extract side (Buy/Sell)
            try:
                action_element = row.find_element(By.XPATH, ".//div[@class='action']")
                if action_element:
                    side_text = self.element_detector.extract_text_safe(action_element)
                    position_data["side"] = side_text.upper()
            except:
                pass
            
            # Extract quantity
            try:
                amount_element = row.find_element(By.XPATH, ".//div[@class='amount']")
                if amount_element:
                    amount_text = self.element_detector.extract_text_safe(amount_element)
                    # Extract number from text like "2 Contracts"
                    qty_number = self.utils.extract_number_from_text(amount_text)
                    if qty_number:
                        position_data["quantity"] = Decimal(str(qty_number))
            except:
                pass
            
            # Extract entry price
            try:
                entry_price_element = row.find_element(By.XPATH, ".//div[@class='entry-price']")
                if entry_price_element:
                    price_text = self.element_detector.extract_text_safe(entry_price_element)
                    price_number = self.utils.extract_number_from_text(price_text)
                    if price_number:
                        position_data["entry_price"] = Decimal(str(price_number))
            except:
                pass
            
            # Extract current price
            try:
                current_price_element = row.find_element(By.XPATH, ".//div[@class='last-rate']")
                if current_price_element:
                    price_text = self.element_detector.extract_text_safe(current_price_element)
                    price_number = self.utils.extract_number_from_text(price_text)
                    if price_number:
                        position_data["current_price"] = Decimal(str(price_number))
            except:
                pass
            
            # Extract P&L
            try:
                pnl_element = row.find_element(By.XPATH, ".//div[contains(@class, 'pl') or contains(@class, 'pnl')]")
                if pnl_element:
                    pnl_text = self.element_detector.extract_text_safe(pnl_element)
                    pnl_number = self.utils.extract_number_from_text(pnl_text)
                    if pnl_number:
                        # Handle negative values based on class
                        if 'red' in pnl_element.get_attribute('class') or 'negative' in pnl_element.get_attribute('class'):
                            pnl_number = -abs(pnl_number)
                        position_data["pnl"] = Decimal(str(pnl_number))
            except:
                pass
            
            # Extract margin used if available
            try:
                margin_element = row.find_element(By.XPATH, ".//div[@class='margin']")
                if margin_element:
                    margin_text = self.element_detector.extract_text_safe(margin_element)
                    margin_number = self.utils.extract_number_from_text(margin_text)
                    if margin_number:
                        position_data["margin_used"] = Decimal(str(margin_number))
            except:
                pass
            
            # Validate required fields
            if position_data["instrument"] and position_data["side"] and position_data["quantity"]:
                logger.debug(f"Extracted position: {position_data['instrument']} {position_data['side']} {position_data['quantity']}")
                return position_data
            else:
                logger.debug("Position row missing required fields, skipping")
                return None
            
        except Exception as e:
            logger.debug(f"Failed to extract Plus500US position data: {e}")
            return None

    def _extract_position_from_row(self, row) -> Optional[Dict[str, Any]]:
        """Legacy method - kept for compatibility"""
        return self._extract_plus500_position_from_row(row)
    
    def _extract_cell_text(self, cells: List, index: int) -> str:
        """Safely extract text from table cell"""
        try:
            if index < len(cells):
                return self.element_detector.extract_text_safe(cells[index])
            return ""
        except:
            return ""
    
    def _set_partial_close_quantity(self, quantity: Decimal) -> None:
        """Set partial close quantity"""
        try:
            qty_input = self.element_detector.find_element_from_selector(
                self.selectors.QUANTITY_INPUT, timeout=5
            )
            
            if qty_input:
                self.utils.human_like_type(self.driver, qty_input, str(quantity))
                
        except Exception as e:
            logger.debug(f"Could not set partial close quantity: {e}")
    
    def _confirm_position_close(self) -> None:
        """Confirm position closure"""
        try:
            confirm_button = self.element_detector.find_element_from_selector(
                self.selectors.CONFIRM_ORDER, timeout=5
            )
            
            if confirm_button:
                self.utils.human_like_click(self.driver, confirm_button)
                time.sleep(1)
                
        except Exception as e:
            logger.debug(f"Could not confirm position close: {e}")
    
    def _confirm_risk_management_change(self) -> None:
        """Confirm SL/TP changes"""
        try:
            # Look for save/confirm button
            save_patterns = [
                "//button[contains(text(), 'Save') or contains(text(), 'Confirm')]",
                "//button[contains(@class, 'save') or contains(@class, 'confirm')]"
            ]
            
            for pattern in save_patterns:
                try:
                    button = self.driver.find_element(By.XPATH, pattern)
                    if button.is_displayed():
                        self.utils.human_like_click(self.driver, button)
                        time.sleep(1)
                        return
                except:
                    continue
                    
        except Exception as e:
            logger.debug(f"Could not confirm risk management change: {e}")
    
    def calculate_trailing_stop_amount(self, instrument_id: str, current_price: Decimal, 
                                      percentage: Optional[Decimal] = None) -> Decimal:
        """
        Calculate appropriate trailing stop amount based on instrument and price
        
        Args:
            instrument_id: Instrument identifier
            current_price: Current market price
            percentage: Optional percentage (default: 0.1-0.5% based on instrument)
            
        Returns:
            Calculated trailing stop amount in price units
        """
        try:
            # Get instrument metadata if available
            instrument_metadata = None
            if hasattr(self.config, 'futures_metadata'):
                instrument_metadata = self.config.futures_metadata.get(instrument_id)
            
            # Default percentage based on instrument type or price level
            if percentage is None:
                if current_price >= Decimal("1000"):  # High-priced instruments
                    percentage = Decimal("0.1")  # 0.1%
                elif current_price >= Decimal("100"):  # Medium-priced instruments
                    percentage = Decimal("0.2")  # 0.2%
                else:  # Lower-priced instruments
                    percentage = Decimal("0.5")  # 0.5%
            
            # Calculate base trailing stop amount
            trailing_amount = current_price * (percentage / Decimal("100"))
            
            # Apply tick size rounding if available
            if instrument_metadata and instrument_metadata.get('tick_size'):
                tick_size = Decimal(str(instrument_metadata['tick_size']))
                # Round to nearest tick
                trailing_amount = round(trailing_amount / tick_size) * tick_size
            else:
                # Default rounding to 2 decimal places
                trailing_amount = round(trailing_amount, 2)
            
            # Ensure minimum trailing stop amount
            min_amount = Decimal("5.0")  # Minimum $5 trailing stop
            if trailing_amount < min_amount:
                trailing_amount = min_amount
            
            logger.debug(f"Calculated trailing stop for {instrument_id}: ${trailing_amount} ({percentage}% of ${current_price})")
            return trailing_amount
            
        except Exception as e:
            logger.error(f"Failed to calculate trailing stop amount: {e}")
            # Return default amount
            return Decimal("25.0")

    def get_current_instrument_price(self) -> Optional[Decimal]:
        """
        Get current instrument price from trading interface
        
        Returns:
            Current price or None if not available
        """
        try:
            # Look for current price display in trading interface
            price_element = self.element_detector.find_element_from_selector(
                self.selectors.CURRENT_PRICE_DISPLAY, timeout=5
            )
            
            if price_element:
                price_text = self.element_detector.extract_text_safe(price_element)
                price_number = self.utils.extract_number_from_text(price_text)
                if price_number:
                    return Decimal(str(price_number))
            
            # Fallback: try to extract from rate display
            rate_patterns = [
                "//div[contains(@class, 'rate') and not(contains(@class, 'change'))]",
                "//span[contains(@class, 'price') or contains(@class, 'rate')]",
                "//div[@title='Last Traded Rate']"
            ]
            
            for pattern in rate_patterns:
                try:
                    element = self.driver.find_element(By.XPATH, pattern)
                    if element and element.is_displayed():
                        price_text = self.element_detector.extract_text_safe(element)
                        price_number = self.utils.extract_number_from_text(price_text)
                        if price_number and price_number > 0:
                            return Decimal(str(price_number))
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to get current instrument price: {e}")
            return None

    def _set_trailing_stop_dynamic(self, instrument_id: str, percentage: Optional[Decimal] = None) -> bool:
        """
        Set trailing stop with dynamic calculation based on current price
        
        Args:
            instrument_id: Instrument identifier for metadata lookup
            percentage: Optional custom percentage (default: auto-calculated)
            
        Returns:
            True if trailing stop was set successfully
        """
        try:
            # Get current price from interface
            current_price = self.get_current_instrument_price()
            if not current_price:
                logger.error("Could not determine current instrument price for trailing stop calculation")
                return False
            
            # Calculate appropriate trailing stop amount
            trailing_amount = self.calculate_trailing_stop_amount(instrument_id, current_price, percentage)
            
            # Find and activate trailing stop switch
            trailing_switch = self.element_detector.find_element_from_selector(
                self.selectors.TRAILING_STOP_SWITCH, timeout=5
            )
            
            if not trailing_switch:
                logger.error("Could not find trailing stop switch")
                return False
            
            # Check if already enabled
            is_enabled = self._is_switch_enabled(trailing_switch)
            if not is_enabled:
                # Click to enable trailing stop
                self.utils.human_like_click(self.driver, trailing_switch)
                time.sleep(0.5)
            
            # Find trailing stop input field
            trailing_input = self.element_detector.find_element_from_selector(
                self.selectors.TRAILING_STOP_INPUT, timeout=5
            )
            
            if not trailing_input:
                logger.error("Could not find trailing stop input field")
                return False
            
            # Clear and set the trailing stop amount
            trailing_input.clear()
            time.sleep(0.2)
            
            # Format amount for Plus500US (no currency symbol in input)
            amount_str = f"{trailing_amount:.2f}"
            self.utils.human_like_type(self.driver, trailing_input, amount_str)
            
            logger.info(f"Set trailing stop: ${trailing_amount} for {instrument_id} at ${current_price}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set dynamic trailing stop: {e}")
            return False

    def _is_switch_enabled(self, switch_element) -> bool:
        """Check if a Plus500 switch element is enabled"""
        try:
            # Check for active/enabled class or attribute
            class_attr = switch_element.get_attribute('class') or ''
            if 'active' in class_attr or 'enabled' in class_attr:
                return True
            
            # Check for checked state
            checked_attr = switch_element.get_attribute('checked')
            if checked_attr:
                return True
            
            # Check for aria-checked
            aria_checked = switch_element.get_attribute('aria-checked')
            if aria_checked and aria_checked.lower() == 'true':
                return True
            
            return False
            
        except Exception:
            return False

    def get_orders(self) -> List[Dict[str, Any]]:
        """
        Extract pending orders from Plus500US trading interface
        
        Returns:
            List of order dictionaries with enhanced metadata
        """
        if not self.element_detector:
            raise RuntimeError("Trading client not initialized. Call initialize() first.")
            
        logger.info("Extracting orders from Plus500US interface")
        
        try:
            # Navigate to orders view
            self._navigate_to_orders()
            
            # Find Plus500US orders table container
            orders_container = self.element_detector.find_element_from_selector(
                self.selectors.ORDERS_TABLE_CONTAINER, timeout=10
            )
            
            if not orders_container:
                logger.warning("No orders table container found")
                return []
            
            # Extract order rows using Plus500US specific selectors
            order_rows = self.element_detector.find_elements_robust(
                self.selectors.ORDER_ROWS, timeout=5
            )
            
            orders = []
            
            for row in order_rows:
                try:
                    order_data = self._extract_plus500_order_from_row(row)
                    if order_data:
                        orders.append(order_data)
                except Exception as e:
                    logger.warning(f"Failed to extract order from row: {e}")
                    continue
            
            logger.info(f"Found {len(orders)} pending orders")
            return orders
            
        except Exception as e:
            logger.error(f"Failed to get orders: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel pending order via Plus500US interface
        
        Args:
            order_id: Order identifier or instrument name
            
        Returns:
            True if successful
        """
        logger.info(f"Cancelling order: {order_id}")
        
        try:
            # Navigate to orders
            self._navigate_to_orders()
            
            # Find order using enhanced search
            order_data = self._find_order_by_identifier(order_id)
            if not order_data:
                raise ValidationError(f"Order {order_id} not found")
            
            order_row = order_data.get("row_element")
            if not order_row:
                raise ValidationError(f"Order row not available for {order_id}")
            
            # Find cancel button using Plus500US selectors
            cancel_button = self.element_detector.find_element_robust(
                self.selectors.ORDER_CANCEL_BUTTON, 
                parent=order_row, 
                timeout=5
            )
            
            if not cancel_button:
                # Try alternative cancel patterns
                cancel_button = order_row.find_element(
                    By.XPATH, ".//button[contains(text(), 'Cancel') or contains(@title, 'Cancel')]"
                )
            
            if not cancel_button:
                raise ValidationError(f"Cancel button not found for order {order_id}")
            
            # Click cancel button with human-like behavior
            self.utils.human_like_click(self.driver, cancel_button)
            time.sleep(1)
            
            # Confirm cancellation if needed
            self._confirm_order_cancellation()
            
            # Verify order was cancelled
            time.sleep(2)
            verification_order = self._find_order_by_identifier(order_id)
            if verification_order:
                logger.warning(f"Order {order_id} may not have been cancelled")
            
            logger.info(f"Order {order_id} cancelled successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False

    def edit_order(self, order_id: str, new_quantity: Optional[Decimal] = None,
                   new_price: Optional[Decimal] = None, 
                   new_stop_loss: Optional[Decimal] = None,
                   new_take_profit: Optional[Decimal] = None) -> bool:
        """
        Edit pending order via Plus500US interface
        
        Args:
            order_id: Order identifier
            new_quantity: New order quantity
            new_price: New limit/stop price
            new_stop_loss: New stop loss price
            new_take_profit: New take profit price
            
        Returns:
            True if successful
        """
        logger.info(f"Editing order: {order_id}")
        
        try:
            # Navigate to orders
            self._navigate_to_orders()
            
            # Find order using enhanced search
            order_data = self._find_order_by_identifier(order_id)
            if not order_data:
                raise ValidationError(f"Order {order_id} not found")
            
            order_row = order_data.get("row_element")
            if not order_row:
                raise ValidationError(f"Order row not available for {order_id}")
            
            # Find edit button
            edit_button = self.element_detector.find_element_robust(
                self.selectors.ORDER_EDIT_BUTTON, 
                parent=order_row, 
                timeout=5
            )
            
            if not edit_button:
                # Try alternative edit patterns
                edit_button = order_row.find_element(
                    By.XPATH, ".//a[contains(text(), 'Edit') or contains(@title, 'Edit')]"
                )
            
            if not edit_button:
                raise ValidationError(f"Edit button not found for order {order_id}")
            
            # Click edit button
            self.utils.human_like_click(self.driver, edit_button)
            time.sleep(2)  # Wait for edit form to load
            
            # Update order parameters
            if new_quantity:
                self._set_quantity(new_quantity)
            if new_price:
                self._set_limit_price(new_price)
            if new_stop_loss:
                self._set_stop_loss(new_stop_loss)
            if new_take_profit:
                self._set_take_profit(new_take_profit)
            
            # Confirm changes
            self._confirm_order_edit()
            
            logger.info(f"Order {order_id} edited successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to edit order {order_id}: {e}")
            return False

    def cancel_all_orders(self) -> List[Dict[str, Any]]:
        """
        Cancel all pending orders
        
        Returns:
            List of cancellation results
        """
        logger.info("Cancelling all pending orders")
        
        try:
            # Get all current orders
            orders = self.get_orders()
            if not orders:
                logger.info("No orders to cancel")
                return []
            
            results = []
            
            for order in orders:
                try:
                    order_id = order.get("id") or order.get("instrument")
                    if order_id:
                        success = self.cancel_order(order_id)
                        results.append({
                            "order_id": order_id,
                            "instrument": order.get("instrument"),
                            "success": success,
                            "timestamp": time.time()
                        })
                        
                        # Add delay between cancellations
                        if success:
                            time.sleep(1)
                            
                except Exception as e:
                    logger.error(f"Failed to cancel order {order.get('id', 'unknown')}: {e}")
                    results.append({
                        "order_id": order.get("id", "unknown"),
                        "instrument": order.get("instrument"),
                        "success": False,
                        "error": str(e),
                        "timestamp": time.time()
                    })
            
            successful_cancellations = len([r for r in results if r.get("success")])
            logger.info(f"Cancelled {successful_cancellations}/{len(results)} orders")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to cancel all orders: {e}")
            return []

    def _extract_plus500_order_from_row(self, row) -> Optional[Dict[str, Any]]:
        """Extract order data from Plus500US order table row"""
        try:
            # Plus500US uses div-based structure for orders
            order_data = {
                "id": None,
                "instrument": None,
                "side": None,
                "quantity": None,
                "order_type": None,
                "price": None,
                "stop_loss": None,
                "take_profit": None,
                "created_time": None,
                "timestamp": time.time(),
                "row_element": row  # Store reference for actions
            }
            
            # Extract instrument name
            name_element = row.find_element(By.XPATH, ".//div[@class='name']/strong")
            if name_element:
                instrument_text = self.element_detector.extract_text_safe(name_element)
                order_data["instrument"] = instrument_text
                order_data["id"] = f"order_{hash(instrument_text)}_{int(time.time())}"
            
            # Extract side (Buy/Sell)
            try:
                action_element = row.find_element(By.XPATH, ".//div[@class='action']")
                if action_element:
                    side_text = self.element_detector.extract_text_safe(action_element)
                    order_data["side"] = side_text.upper()
            except:
                pass
            
            # Extract quantity
            try:
                amount_element = row.find_element(By.XPATH, ".//div[@class='amount']")
                if amount_element:
                    amount_text = self.element_detector.extract_text_safe(amount_element)
                    qty_number = self.utils.extract_number_from_text(amount_text)
                    if qty_number:
                        order_data["quantity"] = Decimal(str(qty_number))
            except:
                pass
            
            # Extract order type and price from limit-stop section
            try:
                limit_stop_element = row.find_element(By.XPATH, ".//div[@class='limit-stop']")
                if limit_stop_element:
                    limit_stop_text = self.element_detector.extract_text_safe(limit_stop_element)
                    if "Limit" in limit_stop_text:
                        order_data["order_type"] = "LIMIT"
                        # Extract limit price
                        price_number = self.utils.extract_number_from_text(limit_stop_text)
                        if price_number:
                            order_data["price"] = Decimal(str(price_number))
                    elif "Stop" in limit_stop_text:
                        order_data["order_type"] = "STOP"
                        price_number = self.utils.extract_number_from_text(limit_stop_text)
                        if price_number:
                            order_data["price"] = Decimal(str(price_number))
            except:
                pass
            
            # Extract creation time
            try:
                time_element = row.find_element(By.XPATH, ".//div[@class='creation-time']")
                if time_element:
                    time_text = self.element_detector.extract_text_safe(time_element)
                    order_data["created_time"] = time_text
            except:
                pass
            
            # Validate required fields
            if order_data["instrument"] and order_data["side"] and order_data["quantity"]:
                logger.debug(f"Extracted order: {order_data['instrument']} {order_data['side']} {order_data['quantity']}")
                return order_data
            else:
                logger.debug("Order row missing required fields, skipping")
                return None
            
        except Exception as e:
            logger.debug(f"Failed to extract Plus500US order data: {e}")
            return None

    def _find_order_by_identifier(self, identifier: str) -> Optional[Dict[str, Any]]:
        """
        Find order by ID or instrument name in Plus500US interface
        
        Args:
            identifier: Order ID or instrument name
            
        Returns:
            Order data dict or None if not found
        """
        try:
            # Get all current orders
            orders = self.get_orders()
            
            # Search by exact ID match first
            for order in orders:
                if order.get("id") == identifier:
                    return order
            
            # Search by instrument name
            for order in orders:
                instrument = order.get("instrument", "")
                if instrument and identifier.lower() in instrument.lower():
                    return order
            
            # Search by partial instrument match
            for order in orders:
                instrument = order.get("instrument", "")
                if instrument:
                    clean_identifier = identifier.replace(" ", "").lower()
                    clean_instrument = instrument.replace(" ", "").lower()
                    if clean_identifier in clean_instrument or clean_instrument in clean_identifier:
                        return order
            
            logger.debug(f"Order not found: {identifier}")
            return None
            
        except Exception as e:
            logger.debug(f"Error finding order {identifier}: {e}")
            return None

    def _confirm_order_cancellation(self) -> None:
        """Confirm order cancellation if confirmation dialog appears"""
        try:
            # Look for confirmation dialog or button
            confirm_patterns = [
                "//button[contains(text(), 'Confirm') or contains(text(), 'Yes')]",
                "//button[contains(@class, 'confirm') and contains(text(), 'Cancel')]"
            ]
            
            for pattern in confirm_patterns:
                try:
                    button = self.driver.find_element(By.XPATH, pattern)
                    if button.is_displayed():
                        self.utils.human_like_click(self.driver, button)
                        time.sleep(1)
                        return
                except:
                    continue
                    
        except Exception as e:
            logger.debug(f"Could not confirm order cancellation: {e}")

    def _confirm_order_edit(self) -> None:
        """Confirm order edit changes"""
        try:
            # Look for save/update button
            save_patterns = [
                "//button[contains(text(), 'Save') or contains(text(), 'Update')]",
                "//button[contains(@class, 'save') or contains(@class, 'update')]",
                "//button[@type='submit']"
            ]
            
            for pattern in save_patterns:
                try:
                    button = self.driver.find_element(By.XPATH, pattern)
                    if button.is_displayed():
                        self.utils.human_like_click(self.driver, button)
                        time.sleep(1)
                        return
                except:
                    continue
                    
        except Exception as e:
            logger.debug(f"Could not confirm order edit: {e}")

    def get_driver(self):
        """Get the WebDriver instance"""
        return self.driver