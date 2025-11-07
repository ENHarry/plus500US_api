from __future__ import annotations
import time
import logging
import uuid
from decimal import Decimal
from typing import Dict, Any, Optional, List
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .browser_manager import BrowserManager
from .element_detector import ElementDetector
from .selectors import Plus500Selectors
from .utils import WebDriverUtils
from ..config import Config
from ..trading import TradingClient
from ..session import SessionManager
from ..models import OrderDraft, Order, Position
from ..errors import ValidationError, OrderRejectError

logger = logging.getLogger(__name__)

class WebDriverTradeManager:
    """Enhanced trade management with running take profit order handling for Plus500US"""
    
    def __init__(self, config: Config, trading_client: TradingClient, 
                 session_manager: SessionManager, browser_manager: Optional[BrowserManager] = None):
        self.config = config
        self.trading_client = trading_client
        self.session_manager = session_manager
        self.browser_manager = browser_manager
        self.driver = None
        self.element_detector: Optional[ElementDetector] = None
        self.selectors = Plus500Selectors()
        self.utils = WebDriverUtils()
        
        # Cache for position and order tracking
        self._position_cache: Dict[str, Dict[str, Any]] = {}
        self._order_cache: Dict[str, Order] = {}
        self._pnl_history: Dict[str, List[Decimal]] = {}  # Track P&L history per position
        self._monitoring_active: Dict[str, bool] = {}  # Track active monitoring sessions
        
    def initialize(self, driver=None) -> None:
        """Initialize with WebDriver instance"""
        if driver:
            self.driver = driver
        elif self.browser_manager:
            self.driver = self.browser_manager.get_driver()
        else:
            raise RuntimeError("No WebDriver available. Provide driver or browser_manager.")
        
        self.element_detector = ElementDetector(self.driver)
        logger.info("WebDriver trade manager initialized")
    
    def extract_current_positions(self) -> List[Dict[str, Any]]:
        """
        Extract current positions from WebDriver interface
        
        Returns:
            List of position data dictionaries
        """
        logger.info("Extracting current positions from WebDriver")
        
        try:
            # Navigate to positions view
            self._navigate_to_positions()
            
            # Find positions table
            positions_table = self.element_detector.find_element_from_selector(
                self.selectors.POSITIONS_TABLE, timeout=10
            )
            
            if not positions_table:
                logger.warning("No positions table found")
                return []
            
            # Extract position rows
            rows = positions_table.find_elements(By.XPATH, ".//tr[td and not(th)]")
            positions = []
            
            for row in rows:
                try:
                    position_data = self._extract_position_from_row(row)
                    if position_data:
                        positions.append(position_data)
                        # Update cache
                        self._position_cache[position_data['id']] = position_data
                        
                except Exception as e:
                    logger.warning(f"Failed to extract position from row: {e}")
                    continue
            
            logger.info(f"Extracted {len(positions)} positions from WebDriver")
            return positions
            
        except Exception as e:
            logger.error(f"Failed to extract positions: {e}")
            return []
    
    def update_running_take_profit(self, position_id: str, new_tp_price: Decimal, use_edit_button: bool = True) -> bool:
        """
        Update running take profit using edit functionality or cancel/recreate method
        
        Args:
            position_id: Position identifier
            new_tp_price: New take profit price
            use_edit_button: Whether to use edit button (True) or cancel/recreate (False)
            
        Returns:
            True if update was successful
        """
        logger.info(f"Updating running take profit for position {position_id} to ${new_tp_price}")
        
        try:
            if use_edit_button:
                # Try using the edit button approach first
                success = self._edit_take_profit_via_webdriver(position_id, new_tp_price)
                if success:
                    logger.info(f"Successfully updated TP via edit button for position {position_id}")
                    return True
                else:
                    logger.warning("Edit button approach failed, falling back to cancel/recreate method")
            
            # Fallback to original cancel/recreate method
            return self._update_take_profit_cancel_recreate(position_id, new_tp_price)
            
        except Exception as e:
            logger.error(f"Failed to update running take profit for position {position_id}: {e}")
            return False
    
    def _edit_take_profit_via_webdriver(self, position_id: str, new_tp_price: Decimal) -> bool:
        """
        Edit take profit order using the WebDriver edit button interface
        
        Args:
            position_id: Position identifier
            new_tp_price: New take profit price
            
        Returns:
            True if edit was successful
        """
        logger.info(f"Editing take profit via WebDriver for position {position_id}")
        
        try:
            # Navigate to orders/positions view
            self._navigate_to_orders_view()
            
            # Find the take profit order row
            tp_order_row = self._find_take_profit_order_row_webdriver(position_id)
            if not tp_order_row:
                logger.warning(f"Take profit order row not found for position {position_id}")
                return False
            
            # Find the edit button in the order row
            edit_button = tp_order_row.find_element(
                By.XPATH, ".//button[contains(@class, 'edit-order') and contains(@class, 'icon-pencil')]"
            )
            
            if not edit_button:
                logger.warning("Edit button not found in take profit order row")
                return False
            
            # Click the edit button
            self.utils.human_like_click(self.driver, edit_button)
            time.sleep(1)  # Wait for edit dialog to open
            
            # Find and update the price input field
            price_input = self.element_detector.find_element_from_selector(
                self.selectors.EDIT_ORDER_PRICE_INPUT, timeout=5
            )
            
            if not price_input:
                logger.error("Price input field not found in edit dialog")
                return False
            
            # Clear existing price and enter new price
            price_input.clear()
            self.utils.human_like_type(self.driver, price_input, str(new_tp_price))
            time.sleep(0.5)
            
            # Find and click the save/confirm button
            save_button = self.element_detector.find_element_from_selector(
                self.selectors.SAVE_ORDER_CHANGES, timeout=3
            )
            
            if not save_button:
                logger.error("Save button not found in edit dialog")
                return False
            
            self.utils.human_like_click(self.driver, save_button)
            time.sleep(2)  # Wait for changes to be saved
            
            # Verify the change was successful
            success = self._verify_tp_price_update(position_id, new_tp_price)
            if success:
                logger.info(f"Take profit successfully updated to ${new_tp_price} via edit button")
                return True
            else:
                logger.warning("Price update verification failed")
                return False
            
        except Exception as e:
            logger.error(f"Failed to edit take profit via WebDriver: {e}")
            return False
    
    def _update_take_profit_cancel_recreate(self, position_id: str, new_tp_price: Decimal) -> bool:
        """
        Original method: Update take profit by canceling existing order and creating new one
        
        Args:
            position_id: Position identifier
            new_tp_price: New take profit price
            
        Returns:
            True if update was successful
        """
        logger.info(f"Updating take profit via cancel/recreate for position {position_id}")
        
        try:
            # 1. Get current position details
            position_data = self._get_position_details(position_id)
            if not position_data:
                raise ValidationError(f"Position {position_id} not found")
            
            # 2. Find and cancel existing TP order
            existing_tp_order = self._find_take_profit_order(position_id)
            if existing_tp_order:
                logger.info(f"Canceling existing TP order: {existing_tp_order.id}")
                self.trading_client.cancel_order(existing_tp_order.id)
                
                # Remove from cache
                if existing_tp_order.id in self._order_cache:
                    del self._order_cache[existing_tp_order.id]
                
                # Wait for cancellation to process
                time.sleep(1)
            else:
                logger.info("No existing TP order found, creating new one")
            
            # 3. Create new TP order using existing _create_take_profit_order method
            parent_draft = self._position_to_order_draft(position_data)
            oco_group_id = str(uuid.uuid4())
            
            tp_draft = self.trading_client._create_take_profit_order(
                parent_draft=parent_draft,
                tp_price=new_tp_price,
                oco_group_id=oco_group_id
            )
            
            # 4. Place the new TP order
            new_tp_order = self.trading_client.place_order(tp_draft)
            
            # Update cache
            self._order_cache[new_tp_order.id] = new_tp_order
            
            logger.info(f"Successfully updated running TP for position {position_id}. New TP order: {new_tp_order.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update running take profit for position {position_id}: {e}")
            return False
    
    def update_running_stop_loss(self, position_id: str, new_sl_price: Decimal) -> bool:
        """
        Update running stop loss by canceling existing SL order and creating new one
        
        Args:
            position_id: Position identifier
            new_sl_price: New stop loss price
            
        Returns:
            True if update was successful
        """
        logger.info(f"Updating running stop loss for position {position_id} to ${new_sl_price}")
        
        try:
            # 1. Get current position details
            position_data = self._get_position_details(position_id)
            if not position_data:
                raise ValidationError(f"Position {position_id} not found")
            
            # 2. Find and cancel existing SL order
            existing_sl_order = self._find_stop_loss_order(position_id)
            if existing_sl_order:
                logger.info(f"Canceling existing SL order: {existing_sl_order.id}")
                self.trading_client.cancel_order(existing_sl_order.id)
                
                # Remove from cache
                if existing_sl_order.id in self._order_cache:
                    del self._order_cache[existing_sl_order.id]
                
                # Wait for cancellation to process
                time.sleep(1)
            else:
                logger.info("No existing SL order found, creating new one")
            
            # 3. Create new SL order using existing method pattern
            parent_draft = self._position_to_order_draft(position_data)
            oco_group_id = str(uuid.uuid4())
            
            sl_draft = self.trading_client._create_stop_loss_order(
                parent_draft=parent_draft,
                stop_price=new_sl_price,
                oco_group_id=oco_group_id
            )
            
            # 4. Place the new SL order
            new_sl_order = self.trading_client.place_order(sl_draft)
            
            # Update cache
            self._order_cache[new_sl_order.id] = new_sl_order
            
            logger.info(f"Successfully updated running SL for position {position_id}. New SL order: {new_sl_order.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update running stop loss for position {position_id}: {e}")
            return False
    
    def monitor_position_pnl_and_update_tp(self, position_id: str, 
                                          tp_update_rules: List[Dict[str, Any]]) -> None:
        """
        Monitor position P&L and automatically update take profit based on rules
        
        Args:
            position_id: Position to monitor
            tp_update_rules: List of rules for TP updates
                           Each rule: {'trigger_pnl': Decimal, 'new_tp_price': Decimal}
        """
        logger.info(f"Starting P&L monitoring for position {position_id} with {len(tp_update_rules)} TP rules")
        
        applied_rules = set()
        
        try:
            while True:
                # Get current position P&L from WebDriver
                current_pnl = self._get_position_pnl_from_webdriver(position_id)
                
                if current_pnl is None:
                    logger.warning(f"Could not get P&L for position {position_id}, stopping monitoring")
                    break
                
                # Check each rule
                for i, rule in enumerate(tp_update_rules):
                    rule_id = f"{position_id}_{i}"
                    
                    if rule_id in applied_rules:
                        continue  # Rule already applied
                    
                    trigger_pnl = rule.get('trigger_pnl')
                    new_tp_price = rule.get('new_tp_price')
                    
                    if trigger_pnl and new_tp_price and current_pnl >= trigger_pnl:
                        logger.info(f"P&L trigger met: ${current_pnl} >= ${trigger_pnl}. Updating TP to ${new_tp_price}")
                        
                        success = self.update_running_take_profit(position_id, new_tp_price)
                        if success:
                            applied_rules.add(rule_id)
                            logger.info(f"Successfully applied TP update rule {i}")
                        else:
                            logger.error(f"Failed to apply TP update rule {i}")
                
                # Check if position still exists
                position_exists = self._position_exists(position_id)
                if not position_exists:
                    logger.info(f"Position {position_id} no longer exists, stopping monitoring")
                    break
                
                # Wait before next check
                time.sleep(5)  # Check every 5 seconds
                
        except KeyboardInterrupt:
            logger.info(f"P&L monitoring stopped by user for position {position_id}")
        except Exception as e:
            logger.error(f"P&L monitoring failed for position {position_id}: {e}")
    
    def close_position_via_webdriver(self, position_id: str, quantity: Optional[Decimal] = None) -> bool:
        """
        Close position via WebDriver DOM interaction
        
        Args:
            position_id: Position identifier
            quantity: Partial quantity to close (None for full close)
            
        Returns:
            True if successful
        """
        logger.info(f"Closing position via WebDriver: {position_id} (quantity: {quantity})")
        
        try:
            # Navigate to positions
            self._navigate_to_positions()
            
            # Find position row
            position_row = self._find_position_row_webdriver(position_id)
            if not position_row:
                raise ValidationError(f"Position {position_id} not found in WebDriver")
            
            # Find close button in row
            close_button = position_row.find_element(
                By.XPATH, ".//button[contains(@class, 'close') or contains(text(), 'Close')]"
            )
            
            if not close_button:
                raise ValidationError(f"Close button not found for position {position_id}")
            
            # Click close button
            self.utils.human_like_click(self.driver, close_button)
            
            # Set partial quantity if specified
            if quantity:
                self._set_partial_close_quantity(quantity)
            
            # Confirm closure
            self._confirm_position_close()
            
            logger.info(f"Position {position_id} closed successfully via WebDriver")
            return True
            
        except Exception as e:
            logger.error(f"Failed to close position {position_id} via WebDriver: {e}")
            return False
    
    def get_position_orders(self, position_id: str) -> Dict[str, List[Order]]:
        """
        Get all orders related to a position (TP, SL, etc.)
        
        Args:
            position_id: Position identifier
            
        Returns:
            Dictionary with order types as keys and lists of orders as values
        """
        logger.info(f"Getting orders for position {position_id}")
        
        try:
            # Get all active orders
            all_orders = self.trading_client.get_orders(status="ACTIVE")
            
            position_data = self._get_position_details(position_id)
            if not position_data:
                return {}
            
            instrument_id = position_data.get('instrument_id')
            
            # Group orders by type
            position_orders = {
                'take_profit': [],
                'stop_loss': [],
                'other': []
            }
            
            for order in all_orders:
                if order.instrument_id == instrument_id:
                    if order.order_type == "LIMIT":
                        position_orders['take_profit'].append(order)
                    elif order.order_type == "STOP":
                        position_orders['stop_loss'].append(order)
                    else:
                        position_orders['other'].append(order)
            
            return position_orders
            
        except Exception as e:
            logger.error(f"Failed to get orders for position {position_id}: {e}")
            return {}
    
    def _get_position_details(self, position_id: str) -> Optional[Dict[str, Any]]:
        """Get position details from cache or WebDriver"""
        
        # Check cache first
        if position_id in self._position_cache:
            cached_position = self._position_cache[position_id]
            # Check if cache is recent (within 30 seconds)
            if time.time() - cached_position.get('timestamp', 0) < 30:
                return cached_position
        
        # Extract fresh data from WebDriver
        positions = self.extract_current_positions()
        
        for position in positions:
            if position.get('id') == position_id:
                return position
        
        return None
    
    def _find_take_profit_order(self, position_id: str) -> Optional[Order]:
        """Find existing take profit order for position"""
        try:
            position_orders = self.get_position_orders(position_id)
            tp_orders = position_orders.get('take_profit', [])
            
            # Return the first active TP order (there should only be one)
            return tp_orders[0] if tp_orders else None
            
        except Exception as e:
            logger.debug(f"Failed to find TP order for position {position_id}: {e}")
            return None
    
    def _find_stop_loss_order(self, position_id: str) -> Optional[Order]:
        """Find existing stop loss order for position"""
        try:
            position_orders = self.get_position_orders(position_id)
            sl_orders = position_orders.get('stop_loss', [])
            
            # Return the first active SL order (there should only be one)
            return sl_orders[0] if sl_orders else None
            
        except Exception as e:
            logger.debug(f"Failed to find SL order for position {position_id}: {e}")
            return None
    
    def _position_to_order_draft(self, position_data: Dict[str, Any]) -> OrderDraft:
        """Convert position data to OrderDraft for order creation"""
        
        # Determine the opposite side for exit orders
        position_side = position_data.get('side', 'BUY')
        exit_side = 'SELL' if position_side == 'BUY' else 'BUY'
        
        return OrderDraft(
            instrument_id=position_data.get('instrument_id', ''),
            side=exit_side,  # type: ignore
            order_type="LIMIT",  # Will be overridden by specific order creation methods
            qty=position_data.get('quantity', Decimal('1')),
            time_in_force="GTC"
        )
    
    def _get_position_pnl_from_webdriver(self, position_id: str) -> Optional[Decimal]:
        """Get real-time position P&L from WebDriver"""
        try:
            position_row = self._find_position_row_webdriver(position_id)
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
    
    def _position_exists(self, position_id: str) -> bool:
        """Check if position still exists"""
        try:
            current_positions = self.extract_current_positions()
            return any(pos.get('id') == position_id for pos in current_positions)
        except Exception:
            return False
    
    def _navigate_to_positions(self) -> None:
        """Navigate to positions view"""
        try:
            # Look for positions tab/link using new selectors
            positions_link = self.element_detector.find_element_from_selector(
                self.selectors.POSITIONS_SECTION, timeout=3
            )
            
            if not positions_link:
                # Fallback: try generic navigation patterns
                try:
                    positions_link = self.driver.find_element(
                        By.XPATH, "//a[contains(text(), 'Positions') or contains(@href, 'position') or contains(text(), 'Open Trades')]"
                    )
                except:
                    positions_link = None
            
            if positions_link:
                self.utils.human_like_click(self.driver, positions_link)
                time.sleep(2)
            else:
                logger.debug("Positions navigation link not found")
                
        except Exception as e:
            logger.debug(f"Could not navigate to positions: {e}")
    
    def _find_position_row_webdriver(self, position_id: str) -> Optional[object]:
        """Find position row in WebDriver positions table"""
        try:
            # Navigate to positions if not already there
            self._navigate_to_positions()
            
            # Find position row using Plus500US structure
            positions_table = self.element_detector.find_element_from_selector(
                self.selectors.POSITIONS_TABLE, timeout=5
            )
            
            if not positions_table:
                return None
            
            # Find position row by ID or instrument using improved patterns
            position_patterns = [
                f"//tr[contains(., '{position_id}')]",
                f"//tr[.//td[contains(text(), '{position_id}')]]",
                f"//tr[contains(@data-position-id, '{position_id}')]",
                f"//div[contains(@class, 'position-row') and contains(., '{position_id}')]",
                f"//tr[.//div[contains(text(), '{position_id}')]]"
            ]
            
            for pattern in position_patterns:
                try:
                    row = positions_table.find_element(By.XPATH, pattern)
                    if row.is_displayed():
                        return row
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.debug(f"Could not find position row for {position_id}: {e}")
            return None
    
    def _extract_position_from_row(self, row) -> Optional[Dict[str, Any]]:
        """Extract position data from WebDriver table row using Plus500US structure"""
        try:
            # Try both traditional table cells and div-based structure
            cells = row.find_elements(By.TAG_NAME, "td")
            
            if not cells:
                # Fallback to div-based structure
                cells = row.find_elements(By.XPATH, ".//div[contains(@class, 'cell') or contains(@class, 'column')]")
            
            if len(cells) < 3:
                logger.debug(f"Insufficient cells found in position row: {len(cells)}")
                return None
            
            # Enhanced extraction with better parsing
            row_text = self.element_detector.extract_text_safe(row)
            
            # Extract basic position data with improved parsing
            position_data = {
                "id": self._extract_cell_text(cells, 0) or self._extract_position_id_from_row(row),
                "instrument_id": self._extract_instrument_from_row(row),
                "side": self._extract_side_from_row(row),
                "quantity": self._extract_quantity_from_row(row),
                "avg_price": self._extract_avg_price_from_row(row),
                "current_price": self._extract_current_price_from_row(row),
                "unrealized_pnl": self._extract_pnl_from_row(row),
                "timestamp": time.time(),
                "raw_text": row_text  # For debugging
            }
            
            # Validate essential fields
            if not position_data["id"] or not position_data["instrument_id"]:
                logger.debug(f"Missing essential position data: {position_data}")
                return None
            
            return position_data
            
        except Exception as e:
            logger.debug(f"Failed to extract position data from row: {e}")
            return None
    
    def _extract_cell_text(self, cells: List, index: int) -> str:
        """Safely extract text from table cell"""
        try:
            if index < len(cells):
                return self.element_detector.extract_text_safe(cells[index])
            return ""
        except:
            return ""
    
    def _extract_position_id_from_row(self, row) -> str:
        """Extract position ID from row using various strategies"""
        try:
            # Try data attributes
            for attr in ['data-position-id', 'data-id', 'id']:
                value = row.get_attribute(attr)
                if value:
                    return value
            
            # Generate from timestamp and instrument
            return f"pos_{int(time.time())}"
            
        except:
            return f"pos_{int(time.time())}"
    
    def _extract_instrument_from_row(self, row) -> str:
        """Extract instrument identifier from position row"""
        try:
            row_text = self.element_detector.extract_text_safe(row)
            
            # Look for common instrument patterns
            import re
            
            # Try to find instrument symbols (3-6 uppercase letters)
            symbol_match = re.search(r'\b([A-Z]{3,6})\b', row_text)
            if symbol_match:
                return symbol_match.group(1)
            
            # Try to extract first meaningful text
            words = row_text.split()
            for word in words:
                if len(word) >= 3 and not word.replace('.', '').replace('-', '').isdigit():
                    return word
            
            return "UNKNOWN"
            
        except:
            return "UNKNOWN"
    
    def _extract_side_from_row(self, row) -> str:
        """Extract position side (BUY/SELL) from row"""
        try:
            row_text = self.element_detector.extract_text_safe(row).upper()
            
            if 'BUY' in row_text or 'LONG' in row_text:
                return 'BUY'
            elif 'SELL' in row_text or 'SHORT' in row_text:
                return 'SELL'
            
            return 'BUY'  # Default
            
        except:
            return 'BUY'
    
    def _extract_quantity_from_row(self, row) -> Decimal:
        """Extract quantity from position row"""
        try:
            row_text = self.element_detector.extract_text_safe(row)
            
            # Look for quantity patterns (numbers that could be quantities)
            import re
            numbers = re.findall(r'\b(\d+(?:\.\d+)?)\b', row_text)
            
            for num in numbers:
                qty = Decimal(num)
                # Reasonable quantity range
                if Decimal('0.1') <= qty <= Decimal('10000'):
                    return qty
            
            return Decimal('1')  # Default
            
        except:
            return Decimal('1')
    
    def _extract_avg_price_from_row(self, row) -> Decimal:
        """Extract average price from position row"""
        try:
            row_text = self.element_detector.extract_text_safe(row)
            
            # Look for price patterns
            import re
            price_patterns = [
                r'\$([\d,]+\.\d{2})',  # $1,234.56
                r'([\d,]+\.\d{2})',    # 1,234.56
                r'([\d,]+\.\d{1})',    # 1,234.5
            ]
            
            for pattern in price_patterns:
                matches = re.findall(pattern, row_text)
                for match in matches:
                    price = Decimal(match.replace(',', ''))
                    # Reasonable price range
                    if Decimal('0.01') <= price <= Decimal('100000'):
                        return price
            
            return Decimal('0')
            
        except:
            return Decimal('0')
    
    def _extract_current_price_from_row(self, row) -> Decimal:
        """Extract current price from position row"""
        try:
            # Similar to avg_price but might be in different location
            return self._extract_avg_price_from_row(row)
            
        except:
            return Decimal('0')
    
    def _extract_pnl_from_row(self, row) -> Optional[Decimal]:
        """Extract P&L from position row"""
        try:
            row_text = self.element_detector.extract_text_safe(row)
            
            # Look for P&L indicators and values
            import re
            
            # Look for negative/positive currency amounts
            pnl_patterns = [
                r'[+-]\s*\$([\d,]+\.\d{2})',  # +$1,234.56 or -$1,234.56
                r'\$([+-]?[\d,]+\.\d{2})',   # $+1,234.56 or $-1,234.56
                r'([+-][\d,]+\.\d{2})',      # +1,234.56 or -1,234.56
            ]
            
            for pattern in pnl_patterns:
                matches = re.findall(pattern, row_text)
                for match in matches:
                    return self._parse_pnl_from_text(match)
            
            return None
            
        except:
            return None
    
    def _parse_pnl_from_text(self, pnl_text: str) -> Optional[Decimal]:
        """Parse P&L value from text"""
        try:
            if not pnl_text:
                return None
            
            # Remove currency symbols and whitespace
            cleaned = pnl_text.replace('$', '').replace(',', '').strip()
            
            # Handle negative values
            is_negative = cleaned.startswith('-') or 'red' in pnl_text.lower()
            if is_negative:
                cleaned = cleaned.lstrip('-')
            
            # Extract numeric value
            import re
            match = re.search(r'(\d+\.?\d*)', cleaned)
            if match:
                value = Decimal(match.group(1))
                return -value if is_negative else value
            
            return None
            
        except Exception:
            return None
    
    def _set_partial_close_quantity(self, quantity: Decimal) -> None:
        """Set partial close quantity in WebDriver"""
        try:
            qty_input = self.element_detector.find_element_from_selector(
                self.selectors.QUANTITY_INPUT, timeout=5
            )
            
            if qty_input:
                self.utils.human_like_type(self.driver, qty_input, str(quantity))
                
        except Exception as e:
            logger.debug(f"Could not set partial close quantity: {e}")
    
    def _confirm_position_close(self) -> None:
        """Confirm position closure in WebDriver"""
        try:
            confirm_button = self.element_detector.find_element_from_selector(
                self.selectors.CONFIRM_ORDER, timeout=5
            )
            
            if confirm_button:
                self.utils.human_like_click(self.driver, confirm_button)
                time.sleep(1)
                
        except Exception as e:
            logger.debug(f"Could not confirm position close: {e}")
    
    def _navigate_to_orders_view(self) -> None:
        """Navigate to orders view in WebDriver"""
        try:
            # Look for orders tab/link
            orders_link = self.driver.find_element(
                By.XPATH, "//a[contains(text(), 'Orders') or contains(@href, 'order') or contains(text(), 'Pending')]"
            )
            
            if orders_link:
                self.utils.human_like_click(self.driver, orders_link)
                time.sleep(2)
            else:
                # Alternative: look for orders section in sidebar
                orders_section = self.element_detector.find_element_from_selector(
                    self.selectors.ORDERS_SECTION, timeout=3
                )
                if orders_section:
                    self.utils.human_like_click(self.driver, orders_section)
                    time.sleep(2)
                
        except Exception as e:
            logger.debug(f"Could not navigate to orders view: {e}")
    
    def _find_take_profit_order_row_webdriver(self, position_id: str) -> Optional[object]:
        """
        Find take profit order row in WebDriver orders table
        
        Args:
            position_id: Position identifier to find TP order for
            
        Returns:
            WebDriver element for the order row or None
        """
        try:
            # Navigate to orders view if not already there
            self._navigate_to_orders_view()
            
            # Find orders table
            orders_table = self.element_detector.find_element_from_selector(
                self.selectors.ORDERS_TABLE, timeout=5
            )
            
            if not orders_table:
                logger.debug("Orders table not found")
                return None
            
            # Find all order rows
            order_rows = orders_table.find_elements(By.XPATH, ".//tr[td]")
            
            for row in order_rows:
                try:
                    # Check if this row contains take profit order info
                    row_text = self.element_detector.extract_text_safe(row).lower()
                    
                    # Look for take profit indicators
                    if any(tp_indicator in row_text for tp_indicator in ['take profit', 'limit', 'tp']):
                        # Check if this order is related to our position
                        if position_id.lower() in row_text:
                            return row
                        
                        # Alternative: check for instrument match
                        position_data = self._get_position_details(position_id)
                        if position_data:
                            instrument_id = position_data.get('instrument_id', '').lower()
                            if instrument_id and instrument_id in row_text:
                                return row
                                
                except Exception as e:
                    logger.debug(f"Error processing order row: {e}")
                    continue
            
            logger.debug(f"Take profit order row not found for position {position_id}")
            return None
            
        except Exception as e:
            logger.debug(f"Could not find TP order row for {position_id}: {e}")
            return None
    
    def _verify_tp_price_update(self, position_id: str, expected_price: Decimal) -> bool:
        """
        Verify that the take profit price was successfully updated
        
        Args:
            position_id: Position identifier
            expected_price: Expected new price
            
        Returns:
            True if price was updated successfully
        """
        try:
            # Wait a moment for changes to propagate
            time.sleep(1)
            
            # Find the updated order row
            tp_order_row = self._find_take_profit_order_row_webdriver(position_id)
            
            if not tp_order_row:
                return False
            
            # Extract the price from the row
            row_text = self.element_detector.extract_text_safe(tp_order_row)
            
            # Look for price patterns in the row text
            import re
            price_patterns = [
                r'\$([\d,]+\.\d{2})',  # $1,234.56
                r'([\d,]+\.\d{2})',    # 1,234.56
                r'([\d,]+\.\d{1})',    # 1,234.5
                r'([\d,]+)'            # 1,234
            ]
            
            for pattern in price_patterns:
                matches = re.findall(pattern, row_text)
                for match in matches:
                    try:
                        price_value = Decimal(match.replace(',', ''))
                        # Allow for small rounding differences
                        if abs(price_value - expected_price) < Decimal('0.01'):
                            logger.debug(f"Price verification successful: {price_value} ≈ {expected_price}")
                            return True
                    except:
                        continue
            
            logger.debug(f"Price verification failed. Expected {expected_price}, found prices in text: {row_text}")
            return False
            
        except Exception as e:
            logger.debug(f"Price verification failed: {e}")
            return False
    
    def get_driver(self):
        """Get the WebDriver instance"""
        return self.driver