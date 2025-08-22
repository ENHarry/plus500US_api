from __future__ import annotations
import time
import logging
import re
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, Optional, List, Tuple
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
from ..errors import ValidationError

logger = logging.getLogger(__name__)

class WebDriverPnLAnalyzer:
    """Advanced PnL analysis with closed positions extraction for Plus500US"""
    
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
        logger.info("WebDriver PnL analyzer initialized")
    
    def analyze_daily_pnl(self, target_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Analyze P&L for a specific day with comprehensive win/loss breakdown
        
        Args:
            target_date: Date to analyze (defaults to today)
            
        Returns:
            Comprehensive P&L analysis dictionary
        """
        if target_date is None:
            target_date = date.today()
        
        logger.info(f"Analyzing daily P&L for {target_date}")
        
        try:
            # Navigate to closed positions
            self._navigate_to_closed_positions()
            
            # Set date filter if needed
            self._set_date_filter(target_date, target_date)
            
            # Extract all trades for the day
            trades = self._extract_closed_trades()
            
            # Filter trades for the target date
            daily_trades = self._filter_trades_by_date(trades, target_date)
            
            # Perform comprehensive analysis
            analysis = self._analyze_trades(daily_trades)
            analysis['target_date'] = target_date.isoformat()
            analysis['total_trades'] = len(daily_trades)
            
            logger.info(f"Analyzed {len(daily_trades)} trades for {target_date}")
            logger.info(f"Net P&L: ${analysis['net_pnl']:.2f} | Wins: {analysis['winning_trades']} | Losses: {analysis['losing_trades']}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Daily P&L analysis failed: {e}")
            raise ValidationError(f"Daily P&L analysis failed: {e}")
    
    def analyze_date_range_pnl(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """
        Analyze P&L for a date range with daily breakdown
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            P&L analysis with daily breakdown
        """
        logger.info(f"Analyzing P&L for date range: {start_date} to {end_date}")
        
        try:
            # Navigate to closed positions
            self._navigate_to_closed_positions()
            
            # Set date filter for the range
            self._set_date_filter(start_date, end_date)
            
            # Extract all trades in the range
            trades = self._extract_closed_trades()
            
            # Filter trades for the date range
            range_trades = self._filter_trades_by_date_range(trades, start_date, end_date)
            
            # Overall analysis
            overall_analysis = self._analyze_trades(range_trades)
            overall_analysis['start_date'] = start_date.isoformat()
            overall_analysis['end_date'] = end_date.isoformat()
            overall_analysis['total_trades'] = len(range_trades)
            
            # Daily breakdown
            daily_breakdown = self._create_daily_breakdown(range_trades, start_date, end_date)
            overall_analysis['daily_breakdown'] = daily_breakdown
            
            logger.info(f"Analyzed {len(range_trades)} trades over {(end_date - start_date).days + 1} days")
            
            return overall_analysis
            
        except Exception as e:
            logger.error(f"Date range P&L analysis failed: {e}")
            raise ValidationError(f"Date range P&L analysis failed: {e}")
    
    def get_recent_trades(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent closed trades with full details
        
        Args:
            limit: Maximum number of trades to retrieve
            
        Returns:
            List of recent trade data
        """
        logger.info(f"Getting {limit} recent trades")
        
        try:
            # Navigate to closed positions
            self._navigate_to_closed_positions()
            
            # Extract trades (no date filter for recent trades)
            all_trades = self._extract_closed_trades(limit=limit)
            
            logger.info(f"Retrieved {len(all_trades)} recent trades")
            return all_trades
            
        except Exception as e:
            logger.error(f"Failed to get recent trades: {e}")
            return []
    
    def analyze_instrument_performance(self, instrument_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze performance by instrument
        
        Args:
            instrument_name: Specific instrument to analyze (None for all)
            
        Returns:
            Performance analysis by instrument
        """
        logger.info(f"Analyzing instrument performance for: {instrument_name or 'all instruments'}")
        
        try:
            # Get all recent trades
            trades = self.get_recent_trades(limit=200)  # Get more trades for instrument analysis
            
            # Filter by instrument if specified
            if instrument_name:
                trades = [trade for trade in trades if instrument_name.lower() in trade.get('instrument', '').lower()]
            
            # Group trades by instrument
            instrument_stats = {}
            
            for trade in trades:
                instrument = trade.get('instrument', 'Unknown')
                
                if instrument not in instrument_stats:
                    instrument_stats[instrument] = {
                        'trades': [],
                        'total_pnl': Decimal('0'),
                        'winning_trades': 0,
                        'losing_trades': 0,
                        'total_wins_amount': Decimal('0'),
                        'total_losses_amount': Decimal('0')
                    }
                
                stats = instrument_stats[instrument]
                stats['trades'].append(trade)
                
                pnl = trade.get('pnl', Decimal('0'))
                stats['total_pnl'] += pnl
                
                if pnl > 0:
                    stats['winning_trades'] += 1
                    stats['total_wins_amount'] += pnl
                elif pnl < 0:
                    stats['losing_trades'] += 1
                    stats['total_losses_amount'] += abs(pnl)
            
            # Calculate additional metrics for each instrument
            for instrument, stats in instrument_stats.items():
                total_trades = len(stats['trades'])
                
                if total_trades > 0:
                    stats['win_rate'] = (stats['winning_trades'] / total_trades) * 100
                    stats['avg_win'] = stats['total_wins_amount'] / max(stats['winning_trades'], 1)
                    stats['avg_loss'] = stats['total_losses_amount'] / max(stats['losing_trades'], 1)
                    
                    if stats['avg_loss'] > 0:
                        stats['win_loss_ratio'] = float(stats['avg_win'] / stats['avg_loss'])
                    else:
                        stats['win_loss_ratio'] = float('inf') if stats['avg_win'] > 0 else 0
                else:
                    stats['win_rate'] = 0
                    stats['avg_win'] = Decimal('0')
                    stats['avg_loss'] = Decimal('0')
                    stats['win_loss_ratio'] = 0
            
            # Sort by total P&L
            sorted_instruments = dict(sorted(instrument_stats.items(), 
                                           key=lambda x: x[1]['total_pnl'], reverse=True))
            
            analysis = {
                'instrument_stats': sorted_instruments,
                'total_instruments': len(sorted_instruments),
                'analysis_timestamp': time.time()
            }
            
            if instrument_name:
                analysis['target_instrument'] = instrument_name
            
            logger.info(f"Analyzed performance for {len(sorted_instruments)} instruments")
            return analysis
            
        except Exception as e:
            logger.error(f"Instrument performance analysis failed: {e}")
            return {}
    
    def _navigate_to_closed_positions(self) -> None:
        """Navigate to the closed positions page"""
        try:
            # Find and click the closed positions navigation link
            closed_positions_link = self.element_detector.find_element_robust(
                self.selectors.CLOSED_POSITIONS_NAV, timeout=10
            )
            
            if not closed_positions_link:
                raise ValidationError("Closed positions navigation link not found")
            
            # Click the link
            self.utils.human_like_click(self.driver, closed_positions_link)
            
            # Wait for the page to load
            time.sleep(3)
            
            # Wait for the trade history table to be present
            trade_table = self.element_detector.find_element_robust(
                self.selectors.TRADE_HISTORY_TABLE, timeout=15
            )
            
            if not trade_table:
                raise ValidationError("Trade history table not found on closed positions page")
            
            logger.info("Successfully navigated to closed positions page")
            
        except Exception as e:
            logger.error(f"Failed to navigate to closed positions: {e}")
            raise ValidationError(f"Failed to navigate to closed positions: {e}")
    
    def _set_date_filter(self, from_date: date, to_date: date) -> None:
        """
        Set the date filter for closed positions
        
        Args:
            from_date: Start date for filter
            to_date: End date for filter
        """
        try:
            logger.debug(f"Setting date filter: {from_date} to {to_date}")
            
            # Find date filter inputs
            from_input = self.element_detector.find_element_robust(
                self.selectors.DATE_FILTER_FROM, timeout=5
            )
            
            to_input = self.element_detector.find_element_robust(
                self.selectors.DATE_FILTER_TO, timeout=5
            )
            
            if not from_input or not to_input:
                logger.warning("Date filter inputs not found, proceeding without date filter")
                return
            
            # Format dates for input (adjust format as needed)
            from_date_str = from_date.strftime('%m/%d/%Y')
            to_date_str = to_date.strftime('%m/%d/%Y')
            
            # Set the date values
            self.utils.human_like_type(self.driver, from_input, from_date_str)
            time.sleep(0.5)
            self.utils.human_like_type(self.driver, to_input, to_date_str)
            time.sleep(0.5)
            
            # Click the submit button
            submit_button = self.element_detector.find_element_robust(
                self.selectors.DATE_FILTER_SUBMIT, timeout=5
            )
            
            if submit_button:
                self.utils.human_like_click(self.driver, submit_button)
                time.sleep(3)  # Wait for results to load
                logger.debug("Date filter applied successfully")
            else:
                logger.warning("Date filter submit button not found")
                
        except Exception as e:
            logger.warning(f"Failed to set date filter: {e}, proceeding without filter")
    
    def _extract_closed_trades(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Extract closed trades from the page using BeautifulSoup
        
        Args:
            limit: Maximum number of trades to extract
            
        Returns:
            List of trade data dictionaries
        """
        logger.debug("Extracting closed trades from page")
        
        trades = []
        
        try:
            # Get page source and parse with BeautifulSoup
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Find all trade history rows
            trade_rows = soup.find_all('div', class_='history')
            
            logger.debug(f"Found {len(trade_rows)} trade rows")
            
            for i, row in enumerate(trade_rows):
                if limit and i >= limit:
                    break
                
                try:
                    trade_data = self._extract_trade_from_row(row)
                    if trade_data:
                        trades.append(trade_data)
                        
                except Exception as e:
                    logger.debug(f"Failed to extract trade from row {i}: {e}")
                    continue
            
            logger.info(f"Successfully extracted {len(trades)} trades")
            return trades
            
        except Exception as e:
            logger.error(f"Failed to extract closed trades: {e}")
            return trades
    
    def _extract_trade_from_row(self, row) -> Optional[Dict[str, Any]]:
        """
        Extract trade data from a BeautifulSoup row element
        
        Args:
            row: BeautifulSoup element representing a trade row
            
        Returns:
            Dictionary of trade data or None
        """
        try:
            # Extract date and time
            date_element = row.find('div', class_='date')
            trade_datetime = None
            if date_element:
                date_spans = date_element.find_all('span')
                if len(date_spans) >= 2:
                    date_str = date_spans[0].get_text(strip=True)
                    time_str = date_spans[1].get_text(strip=True)
                    trade_datetime = self._parse_trade_datetime(date_str, time_str)
            
            # Extract action (Buy/Sell)
            action_element = row.find('div', class_='action')
            action = action_element.get_text(strip=True) if action_element else None
            
            # Extract amount/quantity
            amount_element = row.find('div', class_='amount')
            quantity = None
            if amount_element:
                amount_text = amount_element.get_text(strip=True)
                quantity = self._parse_quantity(amount_text)
            
            # Extract instrument name
            name_element = row.find('div', class_='name')
            instrument = None
            if name_element:
                strong_element = name_element.find('strong')
                if strong_element:
                    instrument = strong_element.get_text(strip=True)
            
            # Extract open price
            open_price_element = row.find('div', class_='open-price')
            open_price = None
            if open_price_element:
                open_price_text = open_price_element.get_text(strip=True)
                open_price = self._parse_price(open_price_text)
            
            # Extract close price
            close_price_element = row.find('div', class_='close-price')
            close_price = None
            if close_price_element:
                close_price_text = close_price_element.get_text(strip=True)
                close_price = self._parse_price(close_price_text)
            
            # Extract P&L
            pnl_element = row.find('div', class_='pl')
            pnl = None
            is_win = False
            if pnl_element:
                pnl_text = pnl_element.get_text(strip=True)
                pnl = self._parse_pnl(pnl_text)
                
                # Determine if it's a win or loss from CSS classes
                pnl_classes = pnl_element.get('class', [])
                is_win = 'green' in pnl_classes
            
            # Create trade data
            trade_data = {
                'datetime': trade_datetime,
                'date': trade_datetime.date() if trade_datetime else None,
                'time': trade_datetime.time() if trade_datetime else None,
                'action': action,
                'quantity': quantity,
                'instrument': instrument,
                'open_price': open_price,
                'close_price': close_price,
                'pnl': pnl,
                'is_win': is_win,
                'is_loss': pnl is not None and pnl < 0,
                'timestamp': time.time()
            }
            
            # Calculate additional metrics
            if open_price and close_price and quantity:
                if action == 'Buy':
                    trade_data['price_change'] = close_price - open_price
                else:  # Sell
                    trade_data['price_change'] = open_price - close_price
                
                trade_data['price_change_pct'] = (trade_data['price_change'] / open_price) * 100 if open_price > 0 else 0
            
            return trade_data
            
        except Exception as e:
            logger.debug(f"Failed to extract trade data from row: {e}")
            return None
    
    def _parse_trade_datetime(self, date_str: str, time_str: str) -> Optional[datetime]:
        """Parse trade datetime from date and time strings"""
        try:
            # Remove any extra characters and parse
            clean_date = date_str.replace('\u00a0', ' ').strip()
            clean_time = time_str.strip()
            
            # Parse date (format: M/D/YYYY)
            date_obj = datetime.strptime(clean_date, '%m/%d/%Y').date()
            
            # Parse time (format: H:MM AM/PM)
            time_obj = datetime.strptime(clean_time, '%I:%M %p').time()
            
            # Combine date and time
            return datetime.combine(date_obj, time_obj)
            
        except Exception as e:
            logger.debug(f"Failed to parse datetime '{date_str}' '{time_str}': {e}")
            return None
    
    def _parse_quantity(self, quantity_text: str) -> Optional[Decimal]:
        """Parse quantity from text like '1 contract'"""
        try:
            # Extract numeric part
            match = re.search(r'(\d+)', quantity_text)
            if match:
                return Decimal(match.group(1))
            return None
        except Exception:
            return None
    
    def _parse_price(self, price_text: str) -> Optional[Decimal]:
        """Parse price from text"""
        try:
            # Remove commas and currency symbols
            cleaned = re.sub(r'[$,\s]', '', price_text.strip())
            
            # Extract numeric value
            match = re.search(r'(\d+\.?\d*)', cleaned)
            if match:
                return Decimal(match.group(1))
            return None
        except Exception:
            return None
    
    def _parse_pnl(self, pnl_text: str) -> Optional[Decimal]:
        """Parse P&L from text"""
        try:
            # Remove currency symbols and special characters
            cleaned = re.sub(r'[$,\s‪‬]', '', pnl_text.strip())
            
            # Handle negative values
            is_negative = cleaned.startswith('-')
            if is_negative:
                cleaned = cleaned[1:]
            
            # Extract numeric value
            match = re.search(r'(\d+\.?\d*)', cleaned)
            if match:
                value = Decimal(match.group(1))
                return -value if is_negative else value
            return None
        except Exception:
            return None
    
    def _filter_trades_by_date(self, trades: List[Dict[str, Any]], target_date: date) -> List[Dict[str, Any]]:
        """Filter trades for a specific date"""
        return [trade for trade in trades if trade.get('date') == target_date]
    
    def _filter_trades_by_date_range(self, trades: List[Dict[str, Any]], 
                                    start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Filter trades for a date range"""
        filtered_trades = []
        for trade in trades:
            trade_date = trade.get('date')
            if trade_date and start_date <= trade_date <= end_date:
                filtered_trades.append(trade)
        return filtered_trades
    
    def _analyze_trades(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Perform comprehensive analysis on a list of trades
        
        Args:
            trades: List of trade data dictionaries
            
        Returns:
            Comprehensive analysis dictionary
        """
        analysis = {
            'net_pnl': Decimal('0'),
            'gross_profit': Decimal('0'),
            'gross_loss': Decimal('0'),
            'winning_trades': 0,
            'losing_trades': 0,
            'break_even_trades': 0,
            'total_trades': len(trades),
            'win_rate': 0.0,
            'loss_rate': 0.0,
            'avg_win': Decimal('0'),
            'avg_loss': Decimal('0'),
            'largest_win': Decimal('0'),
            'largest_loss': Decimal('0'),
            'win_loss_ratio': 0.0,
            'profit_factor': 0.0,
            'total_quantity_traded': Decimal('0'),
            'instruments_traded': set(),
            'trade_times': [],
            'analysis_timestamp': time.time()
        }
        
        if not trades:
            return analysis
        
        winning_pnls = []
        losing_pnls = []
        
        for trade in trades:
            pnl = trade.get('pnl')
            if pnl is None:
                continue
            
            analysis['net_pnl'] += pnl
            
            quantity = trade.get('quantity', Decimal('0'))
            analysis['total_quantity_traded'] += quantity
            
            instrument = trade.get('instrument')
            if instrument:
                analysis['instruments_traded'].add(instrument)
            
            trade_time = trade.get('time')
            if trade_time:
                analysis['trade_times'].append(trade_time)
            
            if pnl > 0:
                analysis['winning_trades'] += 1
                analysis['gross_profit'] += pnl
                winning_pnls.append(pnl)
                analysis['largest_win'] = max(analysis['largest_win'], pnl)
            elif pnl < 0:
                analysis['losing_trades'] += 1
                analysis['gross_loss'] += abs(pnl)
                losing_pnls.append(abs(pnl))
                analysis['largest_loss'] = max(analysis['largest_loss'], abs(pnl))
            else:
                analysis['break_even_trades'] += 1
        
        # Calculate ratios and averages
        total_trades = analysis['total_trades']
        
        if total_trades > 0:
            analysis['win_rate'] = (analysis['winning_trades'] / total_trades) * 100
            analysis['loss_rate'] = (analysis['losing_trades'] / total_trades) * 100
        
        if winning_pnls:
            analysis['avg_win'] = sum(winning_pnls) / len(winning_pnls)
        
        if losing_pnls:
            analysis['avg_loss'] = sum(losing_pnls) / len(losing_pnls)
        
        # Win/Loss ratio
        if analysis['avg_loss'] > 0:
            analysis['win_loss_ratio'] = float(analysis['avg_win'] / analysis['avg_loss'])
        
        # Profit factor
        if analysis['gross_loss'] > 0:
            analysis['profit_factor'] = float(analysis['gross_profit'] / analysis['gross_loss'])
        else:
            analysis['profit_factor'] = float('inf') if analysis['gross_profit'] > 0 else 0
        
        # Convert sets to lists for JSON serialization
        analysis['instruments_traded'] = list(analysis['instruments_traded'])
        analysis['unique_instruments_count'] = len(analysis['instruments_traded'])
        
        return analysis
    
    def _create_daily_breakdown(self, trades: List[Dict[str, Any]], 
                               start_date: date, end_date: date) -> Dict[str, Dict[str, Any]]:
        """Create daily breakdown of P&L"""
        daily_breakdown = {}
        
        # Group trades by date
        trades_by_date = {}
        for trade in trades:
            trade_date = trade.get('date')
            if trade_date:
                date_str = trade_date.isoformat()
                if date_str not in trades_by_date:
                    trades_by_date[date_str] = []
                trades_by_date[date_str].append(trade)
        
        # Analyze each day
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.isoformat()
            day_trades = trades_by_date.get(date_str, [])
            
            daily_breakdown[date_str] = self._analyze_trades(day_trades)
            daily_breakdown[date_str]['date'] = date_str
            
            current_date = date(current_date.year, current_date.month, current_date.day + 1)
        
        return daily_breakdown
    
    def get_driver(self):
        """Get the WebDriver instance"""
        return self.driver