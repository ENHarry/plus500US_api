from __future__ import annotations
import time
import logging
import re
from decimal import Decimal
from typing import Dict, Any, Optional, List, Set
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup

from .browser_manager import BrowserManager
from .element_detector import ElementDetector
from .selectors import Plus500Selectors
from .utils import WebDriverUtils
from ..config import Config
from ..instruments import InstrumentsClient
from ..models import Instrument
from ..errors import ValidationError

logger = logging.getLogger(__name__)

class WebDriverInstrumentsDiscovery:
    """Enhanced instruments discovery with category-based navigation for Plus500US"""
    
    def __init__(self, config: Config, browser_manager: Optional[BrowserManager] = None,
                 instruments_client: Optional[InstrumentsClient] = None):
        self.config = config
        self.browser_manager = browser_manager
        self.instruments_client = instruments_client
        self.driver = None
        self.element_detector: Optional[ElementDetector] = None
        self.selectors = Plus500Selectors()
        self.utils = WebDriverUtils()
        
        # Cache for discovered instruments
        self._instruments_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._last_cache_update: Dict[str, float] = {}
        self.cache_duration = 300  # 5 minutes
        
    def initialize(self, driver=None) -> None:
        """Initialize with WebDriver instance"""
        if driver:
            self.driver = driver
        elif self.browser_manager:
            self.driver = self.browser_manager.get_driver()
        else:
            raise RuntimeError("No WebDriver available. Provide driver or browser_manager.")
        
        self.element_detector = ElementDetector(self.driver)
        logger.info("WebDriver instruments discovery initialized")
    
    def get_all_instruments(self, force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Discover all available instruments by navigating through categories
        
        Args:
            force_refresh: Force refresh cache even if still valid
            
        Returns:
            Dictionary mapping instrument_id to instrument data with category info
        """
        logger.info("Starting comprehensive instruments discovery by category")
        
        try:
            # Navigate to instruments page if not already there
            self._navigate_to_instruments_page()
            
            # Get all available categories
            categories = self._get_available_categories()
            logger.info(f"Found {len(categories)} instrument categories")
            
            all_instruments = {}
            
            for category_name, category_element in categories.items():
                # Check cache first
                if not force_refresh and self._is_cache_valid(category_name):
                    logger.debug(f"Using cached data for category: {category_name}")
                    cached_instruments = self._instruments_cache[category_name]
                    # Add cached instruments to the main dictionary with instrument_id as key
                    for instrument in cached_instruments:
                        instrument_id = instrument.get('id')
                        if instrument_id:
                            all_instruments[instrument_id] = instrument
                    continue
                
                logger.info(f"Discovering instruments for category: {category_name}")
                
                try:
                    # Try URL navigation first, then fallback to click
                    category_instruments = self._discover_category_instruments_enhanced(category_name, category_element)
                    
                    # Store instruments with instrument_id as key
                    for instrument in category_instruments:
                        instrument_id = instrument.get('id')
                        if instrument_id:
                            instrument['category'] = category_name
                            all_instruments[instrument_id] = instrument
                    
                    # Update cache
                    self._instruments_cache[category_name] = category_instruments
                    self._last_cache_update[category_name] = time.time()
                    
                    logger.info(f"Discovered {len(category_instruments)} instruments in {category_name}")
                    
                    # Add small delay between categories to be respectful
                    time.sleep(1)
                    
                except Exception as e:
                    logger.warning(f"Failed to discover instruments for category {category_name}: {e}")
            
            total_instruments = len(all_instruments)
            logger.info(f"Total instruments discovered: {total_instruments} across {len(categories)} categories")
            
            return all_instruments
            
        except Exception as e:
            logger.error(f"Instruments discovery failed: {e}")
            raise ValidationError(f"Instruments discovery failed: {e}")
    
    def discover_category_instruments(self, category_name: str, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Discover instruments for a specific category
        
        Args:
            category_name: Name of the category (e.g., "Agriculture", "Crypto", "Forex")
            force_refresh: Force refresh cache even if still valid
            
        Returns:
            List of instrument data dictionaries
        """
        logger.info(f"Discovering instruments for category: {category_name}")
        
        # Check cache first
        if not force_refresh and self._is_cache_valid(category_name):
            logger.debug(f"Using cached data for category: {category_name}")
            return self._instruments_cache[category_name]
        
        try:
            # Navigate to instruments page
            self._navigate_to_instruments_page()
            
            # Find the category element
            categories = self._get_available_categories()
            
            if category_name not in categories:
                available_categories = list(categories.keys())
                raise ValidationError(f"Category '{category_name}' not found. Available: {available_categories}")
            
            category_element = categories[category_name]
            
            # Discover instruments in this category
            instruments = self._discover_category_instruments(category_name, category_element)
            
            # Update cache
            self._instruments_cache[category_name] = instruments
            self._last_cache_update[category_name] = time.time()
            
            logger.info(f"Discovered {len(instruments)} instruments in {category_name}")
            return instruments
            
        except Exception as e:
            logger.error(f"Category instruments discovery failed for {category_name}: {e}")
            raise ValidationError(f"Category instruments discovery failed: {e}")
    
    def get_instrument_details(self, instrument_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific instrument
        
        Args:
            instrument_id: Instrument identifier or name
            
        Returns:
            Detailed instrument information or None if not found
        """
        logger.info(f"Getting detailed information for instrument: {instrument_id}")
        
        try:
            # First, find the instrument in our discovery data
            all_instruments = self.get_all_instruments()
            
            target_instrument = None
            for category_name, instruments in all_instruments.items():
                for instrument in instruments:
                    if (instrument.get('id') == instrument_id or 
                        instrument.get('symbol') == instrument_id or
                        instrument.get('name') == instrument_id):
                        target_instrument = instrument
                        target_instrument['category'] = category_name
                        break
                if target_instrument:
                    break
            
            if not target_instrument:
                logger.warning(f"Instrument {instrument_id} not found in discovery data")
                return None
            
            # Try to get additional details by clicking the info button
            enhanced_details = self._get_enhanced_instrument_details(target_instrument)
            
            if enhanced_details:
                target_instrument.update(enhanced_details)
            
            logger.info(f"Retrieved detailed information for {instrument_id}")
            return target_instrument
            
        except Exception as e:
            logger.error(f"Failed to get instrument details for {instrument_id}: {e}")
            return None
    
    def search_instruments(self, search_term: str) -> List[Dict[str, Any]]:
        """
        Search for instruments across all categories
        
        Args:
            search_term: Term to search for in instrument names
            
        Returns:
            List of matching instruments
        """
        logger.info(f"Searching for instruments matching: {search_term}")
        
        search_term_lower = search_term.lower()
        matching_instruments = []
        
        try:
            all_instruments = self.get_all_instruments()
            
            for category_name, instruments in all_instruments.items():
                for instrument in instruments:
                    name = instrument.get('name', '').lower()
                    symbol = instrument.get('symbol', '').lower()
                    
                    if (search_term_lower in name or 
                        search_term_lower in symbol or
                        search_term_lower == instrument.get('id', '').lower()):
                        
                        instrument_copy = instrument.copy()
                        instrument_copy['category'] = category_name
                        matching_instruments.append(instrument_copy)
            
            logger.info(f"Found {len(matching_instruments)} instruments matching '{search_term}'")
            return matching_instruments
            
        except Exception as e:
            logger.error(f"Instrument search failed: {e}")
            return []
    
    def _navigate_to_instruments_page(self) -> None:
        """Navigate to the instruments trading page"""
        try:
            current_url = self.driver.current_url
            
            # Check if we're already on a trading page
            if 'trade' in current_url.lower() or 'instruments' in current_url.lower():
                logger.debug("Already on trading/instruments page")
                return
            
            # Navigate to the trading page
            trading_url = f"{self.config.base_url}/trade"
            logger.debug(f"Navigating to trading page: {trading_url}")
            self.driver.get(trading_url)
            
            # Wait for page load
            self.element_detector.wait_for_page_load()
            time.sleep(2)
            
        except Exception as e:
            logger.debug(f"Could not navigate to instruments page: {e}")
    
    def _get_available_categories(self) -> Dict[str, Any]:
        """
        Get all available instrument categories
        
        Returns:
            Dictionary mapping category names to their WebDriver elements
        """
        categories = {}
        
        try:
            # Find the categories container
            categories_container = self.element_detector.find_element_from_selector(
                self.selectors.INSTRUMENT_CATEGORIES_CONTAINER, timeout=10
            )
            
            if not categories_container:
                logger.warning("Categories container not found")
                return categories
            
            # Find all category links
            category_links = categories_container.find_elements(By.XPATH, ".//a")
            
            for link in category_links:
                try:
                    category_text = self.element_detector.extract_text_safe(link).strip()
                    
                    # Skip empty or invalid categories
                    if not category_text or category_text in ['', 'My Watchlist']:
                        continue
                    
                    # Skip if already selected
                    if 'selected' in (link.get_attribute('class') or ''):
                        continue
                    
                    categories[category_text] = link
                    logger.debug(f"Found category: {category_text}")
                    
                except Exception as e:
                    logger.debug(f"Failed to process category link: {e}")
                    continue
            
            logger.info(f"Found {len(categories)} available categories")
            return categories
            
        except Exception as e:
            logger.error(f"Failed to get available categories: {e}")
            return categories
    
    def _discover_category_instruments_enhanced(self, category_name: str, category_element) -> List[Dict[str, Any]]:
        """
        Enhanced discovery with URL navigation fallback and comprehensive extraction
        
        Args:
            category_name: Name of the category
            category_element: WebDriver element for the category
            
        Returns:
            List of instrument data with detailed info
        """
        instruments = []
        
        try:
            # Try URL navigation first
            category_url = self.selectors.get_category_url(category_name)
            if category_url:
                full_url = f"{self.config.base_url}{category_url}"
                logger.debug(f"Trying URL navigation: {full_url}")
                try:
                    self.driver.get(full_url)
                    self.element_detector.wait_for_page_load()
                    time.sleep(2)
                except Exception as e:
                    logger.debug(f"URL navigation failed, using click method: {e}")
                    # Fallback to click navigation
                    self.utils.human_like_click(self.driver, category_element)
                    time.sleep(3)
            else:
                # Click on the category to load instruments
                self.utils.human_like_click(self.driver, category_element)
                time.sleep(3)
            
            # Find the instruments table using new selectors
            instruments_table = self.element_detector.find_element_from_selector(
                self.selectors.INSTRUMENTS_REPEATER, timeout=10
            )
            
            if not instruments_table:
                logger.warning(f"Instruments table not found for category: {category_name}")
                return instruments
            
            # Find instrument rows using new HTML structure
            instrument_rows = instruments_table.find_elements(
                By.XPATH, ".//div[@class='instrument-row instrument']"
            )
            
            logger.debug(f"Found {len(instrument_rows)} instrument rows for {category_name}")
            
            for row in instrument_rows:
                try:
                    instrument_data = self._extract_instrument_from_row_enhanced(row)
                    if instrument_data:
                        # Extract detailed info by clicking info button
                        detailed_info = self._extract_detailed_instrument_info(row)
                        if detailed_info:
                            instrument_data.update(detailed_info)
                        instruments.append(instrument_data)
                        
                except Exception as e:
                    logger.debug(f"Failed to extract instrument from row: {e}")
                    continue
            
            return instruments
            
        except Exception as e:
            logger.error(f"Failed to discover instruments for category {category_name}: {e}")
            return instruments
    
    def _discover_category_instruments(self, category_name: str, category_element) -> List[Dict[str, Any]]:
        """Legacy method - calls enhanced version"""
        return self._discover_category_instruments_enhanced(category_name, category_element)
    
    def _extract_instrument_from_row_enhanced(self, row) -> Optional[Dict[str, Any]]:
        """
        Extract instrument data from WebDriver row element using new HTML structure
        
        Args:
            row: WebDriver element representing an instrument row
            
        Returns:
            Dictionary of instrument data or None
        """
        try:
            # Extract instrument ID from data attribute
            instrument_id = row.get_attribute('data-instrument-id')
            
            # Extract instrument name and expiry using new selectors
            name_element = row.find_element(By.XPATH, ".//div[@class='name']//strong")
            base_name = ""
            expiry = None
            
            if name_element:
                full_name_text = self.element_detector.extract_text_safe(name_element)
                
                # Extract expiry date if present (span within strong)
                try:
                    span_element = name_element.find_element(By.XPATH, ".//span")
                    if span_element:
                        expiry = self.element_detector.extract_text_safe(span_element)
                        base_name = full_name_text.replace(expiry, '').strip()
                    else:
                        base_name = full_name_text
                except:
                    base_name = full_name_text
            
            if not base_name:
                logger.debug("No instrument name found in row")
                return None
            
            # Extract change percentage
            change_pct = None
            try:
                change_element = row.find_element(By.XPATH, ".//div[@class='change']//span")
                if change_element:
                    change_text = self.element_detector.extract_text_safe(change_element)
                    change_pct = self._parse_percentage(change_text)
            except:
                pass
            
            # Extract bid (sell) price
            bid_price = None
            try:
                sell_element = row.find_element(By.XPATH, ".//div[@class='sell']")
                if sell_element:
                    bid_text = self.element_detector.extract_text_safe(sell_element)
                    bid_price = self._parse_price(bid_text)
            except:
                pass
            
            # Extract ask (buy) price
            ask_price = None
            try:
                buy_element = row.find_element(By.XPATH, ".//div[@class='buy']")
                if buy_element:
                    ask_text = self.element_detector.extract_text_safe(buy_element)
                    ask_price = self._parse_price(ask_text)
            except:
                pass
            
            # Extract high/low data
            high_price = None
            low_price = None
            try:
                high_low_element = row.find_element(By.XPATH, ".//div[@class='high-low']//span")
                if high_low_element:
                    high_low_text = self.element_detector.extract_text_safe(high_low_element)
                    high_price, low_price = self._parse_high_low(high_low_text)
            except:
                pass
            
            # Check if market is closed
            is_market_closed = False
            try:
                market_closed_element = row.find_element(By.XPATH, ".//span[@class='icon-moon']")
                is_market_closed = market_closed_element is not None
            except:
                pass
            
            # Create comprehensive instrument data
            instrument_data = {
                'id': instrument_id,
                'symbol': base_name.split()[0] if base_name else '',
                'name': base_name,
                'expiry': expiry,
                'change_pct': change_pct,
                'bid': bid_price,
                'ask': ask_price,
                'high': high_price,
                'low': low_price,
                'market_closed': is_market_closed,
                'timestamp': time.time(),
                'row_element': row  # Store for info extraction
            }
            
            # Calculate spread if both bid and ask are available
            if bid_price is not None and ask_price is not None:
                spread = ask_price - bid_price
                instrument_data['spread'] = spread
                if ask_price > 0:
                    instrument_data['spread_pct'] = (spread / ask_price) * 100
            
            return instrument_data
            
        except Exception as e:
            logger.debug(f"Failed to extract instrument data from row: {e}")
            return None
    
    def _extract_instrument_from_row(self, row) -> Optional[Dict[str, Any]]:
        """Legacy method for BeautifulSoup compatibility"""
        # Convert BeautifulSoup to WebDriver approach if needed
        return self._extract_instrument_from_row_enhanced(row)
    
    def _extract_detailed_instrument_info(self, row) -> Optional[Dict[str, Any]]:
        """
        Extract detailed instrument information by clicking the info button
        
        Args:
            row: WebDriver element representing instrument row
            
        Returns:
            Dictionary with detailed instrument info or None
        """
        detailed_info = {}
        
        try:
            # Find info button in the row
            info_button = row.find_element(By.XPATH, ".//button[@class='open-info icon-info-circle']")
            
            if not info_button:
                logger.debug("Info button not found in instrument row")
                return None
            
            # Click the info button to open sidebar
            self.utils.human_like_click(self.driver, info_button)
            time.sleep(2)  # Wait for sidebar to load
            
            # Wait for sidebar to appear
            sidebar = self.element_detector.find_element_from_selector(
                self.selectors.SIDEBAR_CONTAINER, timeout=5
            )
            
            if not sidebar:
                logger.debug("Sidebar not found after clicking info button")
                return None
            
            # Click on Info tab to ensure we're on the right tab
            info_tab = self.element_detector.find_element_from_selector(
                self.selectors.INFO_TAB, timeout=3
            )
            if info_tab:
                self.utils.human_like_click(self.driver, info_tab)
                time.sleep(1)
            
            # Extract instrument symbol (in parentheses)
            try:
                symbol_element = self.element_detector.find_element_from_selector(
                    self.selectors.INSTRUMENT_SYMBOL, timeout=2
                )
                if symbol_element:
                    symbol_text = self.element_detector.extract_text_safe(symbol_element)
                    # Extract text within parentheses
                    if '(' in symbol_text and ')' in symbol_text:
                        detailed_info['symbol_full'] = symbol_text.strip('()')
            except:
                pass
            
            # Extract commission information
            try:
                commission_element = self.element_detector.find_element_from_selector(
                    self.selectors.COMMISSION_INFO, timeout=2
                )
                if commission_element:
                    commission_text = self.element_detector.extract_text_safe(commission_element)
                    detailed_info['commission'] = self._parse_currency_value(commission_text)
            except:
                pass
            
            # Extract margin information
            try:
                day_margin = self.element_detector.find_element_from_selector(
                    self.selectors.DAY_MARGIN_INFO, timeout=2
                )
                if day_margin:
                    day_margin_text = self.element_detector.extract_text_safe(day_margin)
                    detailed_info['day_margin'] = self._parse_currency_value(day_margin_text)
                    
                place_order_margin = self.element_detector.find_element_from_selector(
                    self.selectors.PLACE_ORDER_MARGIN_INFO, timeout=2
                )
                if place_order_margin:
                    place_order_text = self.element_detector.extract_text_safe(place_order_margin)
                    detailed_info['place_order_margin'] = self._parse_currency_value(place_order_text)
                    
                full_margin = self.element_detector.find_element_from_selector(
                    self.selectors.FULL_MARGIN_INFO, timeout=2
                )
                if full_margin:
                    full_margin_text = self.element_detector.extract_text_safe(full_margin)
                    detailed_info['full_margin'] = self._parse_currency_value(full_margin_text)
            except:
                pass
            
            # Extract expiry and trading session info
            try:
                expiry_element = self.element_detector.find_element_from_selector(
                    self.selectors.EXPIRY_DATE_INFO, timeout=2
                )
                if expiry_element:
                    expiry_text = self.element_detector.extract_text_safe(expiry_element)
                    detailed_info['expiry_date'] = expiry_text
                    
                current_session = self.element_detector.find_element_from_selector(
                    self.selectors.CURRENT_TRADING_SESSION, timeout=2
                )
                if current_session:
                    session_text = self.element_detector.extract_text_safe(current_session)
                    detailed_info['current_trading_session'] = session_text
            except:
                pass
            
            # Extract contract and exchange info
            try:
                contract_value = self.element_detector.find_element_from_selector(
                    self.selectors.SINGLE_CONTRACT_VALUE, timeout=2
                )
                if contract_value:
                    contract_text = self.element_detector.extract_text_safe(contract_value)
                    detailed_info['contract_value'] = self._parse_currency_value(contract_text)
                    
                units_per_contract = self.element_detector.find_element_from_selector(
                    self.selectors.UNITS_PER_CONTRACT, timeout=2
                )
                if units_per_contract:
                    units_text = self.element_detector.extract_text_safe(units_per_contract)
                    detailed_info['units_per_contract'] = self._parse_number_value(units_text)
                    
                exchange_element = self.element_detector.find_element_from_selector(
                    self.selectors.EXCHANGE_INFO, timeout=2
                )
                if exchange_element:
                    exchange_text = self.element_detector.extract_text_safe(exchange_element)
                    detailed_info['exchange'] = exchange_text.strip()
                    
                tick_size = self.element_detector.find_element_from_selector(
                    self.selectors.TICK_SIZE_INFO, timeout=2
                )
                if tick_size:
                    tick_size_text = self.element_detector.extract_text_safe(tick_size)
                    detailed_info['tick_size'] = self._parse_number_value(tick_size_text)
                    
                tick_value = self.element_detector.find_element_from_selector(
                    self.selectors.TICK_VALUE_INFO, timeout=2
                )
                if tick_value:
                    tick_value_text = self.element_detector.extract_text_safe(tick_value)
                    detailed_info['tick_value'] = self._parse_currency_value(tick_value_text)
            except:
                pass
            
            # Extract live statistics if available
            try:
                change_5min = self.element_detector.find_element_from_selector(
                    self.selectors.CHANGE_5MIN, timeout=2
                )
                if change_5min:
                    change_5min_text = self.element_detector.extract_text_safe(change_5min)
                    detailed_info['change_5min'] = self._parse_percentage(change_5min_text)
                    
                change_1hour = self.element_detector.find_element_from_selector(
                    self.selectors.CHANGE_1HOUR, timeout=2
                )
                if change_1hour:
                    change_1hour_text = self.element_detector.extract_text_safe(change_1hour)
                    detailed_info['change_1hour'] = self._parse_percentage(change_1hour_text)
                    
                change_1day = self.element_detector.find_element_from_selector(
                    self.selectors.CHANGE_1DAY, timeout=2
                )
                if change_1day:
                    change_1day_text = self.element_detector.extract_text_safe(change_1day)
                    detailed_info['change_1day'] = self._parse_percentage(change_1day_text)
            except:
                pass
            
            # Close sidebar by clicking outside or finding close button
            try:
                # Click outside the sidebar to close it
                self.driver.execute_script("document.body.click();")
                time.sleep(0.5)
            except:
                pass
            
            logger.debug(f"Extracted detailed info: {len(detailed_info)} fields")
            return detailed_info
            
        except Exception as e:
            logger.debug(f"Failed to extract detailed instrument info: {e}")
            return None
    
    def _parse_currency_value(self, text: str) -> Optional[float]:
        """Parse currency value from text"""
        if not text:
            return None
        
        try:
            # Remove currency symbols, commas, and whitespace
            import re
            cleaned = re.sub(r'[$,\s‪‬]', '', text.strip())
            
            # Extract numeric value
            match = re.search(r'(\d+\.?\d*)', cleaned)
            if match:
                return float(match.group(1))
            
            return None
        except:
            return None
    
    def _parse_number_value(self, text: str) -> Optional[float]:
        """Parse numeric value from text"""
        if not text:
            return None
        
        try:
            import re
            # Extract numeric value
            match = re.search(r'(\d+\.?\d*)', text.strip())
            if match:
                return float(match.group(1))
            
            return None
        except:
            return None
    
    def _get_enhanced_instrument_details(self, instrument: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get enhanced instrument details by clicking the info button
        
        Args:
            instrument: Basic instrument data
            
        Returns:
            Enhanced details or None
        """
        try:
            # This would involve clicking the info button and extracting margin/commission data
            # For now, return basic enhancement based on existing patterns
            enhanced = {}
            
            # Try to determine some basic metadata based on instrument name
            name = instrument.get('name', '').lower()
            
            # Set some defaults based on instrument type
            if 'micro' in name:
                enhanced['tick_size'] = 0.25
                enhanced['min_qty'] = 1.0
                enhanced['tick_value'] = 0.25
            elif any(forex_term in name for forex_term in ['eur', 'usd', 'gbp', 'aud', 'cad']):
                enhanced['tick_size'] = 0.0001
                enhanced['min_qty'] = 1.0
                enhanced['tick_value'] = 0.1
            elif 'bitcoin' in name or 'ether' in name or 'crypto' in name:
                enhanced['tick_size'] = 0.25
                enhanced['min_qty'] = 1.0
                enhanced['tick_value'] = 0.25
            else:
                enhanced['tick_size'] = 0.25
                enhanced['min_qty'] = 1.0
                enhanced['tick_value'] = 0.25
            
            return enhanced
            
        except Exception as e:
            logger.debug(f"Failed to get enhanced details: {e}")
            return None
    
    def _parse_price(self, price_text: str) -> Optional[float]:
        """Parse price from text"""
        if not price_text:
            return None
        
        try:
            # Remove commas and whitespace
            cleaned = re.sub(r'[,\s]', '', price_text.strip())
            
            # Extract numeric value
            match = re.search(r'(\d+\.?\d*)', cleaned)
            if match:
                return float(match.group(1))
            
            return None
            
        except Exception:
            return None
    
    def _parse_percentage(self, pct_text: str) -> Optional[float]:
        """Parse percentage from text"""
        if not pct_text:
            return None
        
        try:
            # Remove % symbol and whitespace
            cleaned = pct_text.replace('%', '').replace('‎', '').strip()
            
            # Handle negative values
            if cleaned.startswith('-'):
                return -float(cleaned[1:])
            else:
                return float(cleaned)
            
        except Exception:
            return None
    
    def _parse_high_low(self, high_low_text: str) -> tuple[Optional[float], Optional[float]]:
        """Parse high/low prices from text like '407.500/399.500'"""
        if not high_low_text or '/' not in high_low_text:
            return None, None
        
        try:
            parts = high_low_text.split('/')
            if len(parts) >= 2:
                high = self._parse_price(parts[0])
                low = self._parse_price(parts[1])
                return high, low
            
            return None, None
            
        except Exception:
            return None, None
    
    def _is_cache_valid(self, category_name: str) -> bool:
        """Check if cached data for category is still valid"""
        if category_name not in self._last_cache_update:
            return False
        
        last_update = self._last_cache_update[category_name]
        return (time.time() - last_update) < self.cache_duration
    
    def clear_cache(self) -> None:
        """Clear the instruments cache"""
        self._instruments_cache.clear()
        self._last_cache_update.clear()
        logger.info("Instruments cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'cached_categories': list(self._instruments_cache.keys()),
            'total_cached_instruments': sum(len(instruments) for instruments in self._instruments_cache.values()),
            'cache_ages': {
                category: time.time() - last_update 
                for category, last_update in self._last_cache_update.items()
            }
        }
    
    def get_driver(self):
        """Get the WebDriver instance"""
        return self.driver