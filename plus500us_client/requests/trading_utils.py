"""
Advanced Trading Utilities for Plus500 API Client - Phase 3
Implements advanced trading features, automation, and analysis tools
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Tuple, Callable
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import asyncio
from dataclasses import dataclass
from enum import Enum

from .config import Config
from .session import SessionManager
from .models import (
    Plus500OrderRequest, Plus500OrderResponse, Plus500Position,
    Plus500InstrumentData, Plus500ChartData, Plus500BuySellInfo
)
from .errors import AuthenticationError, TradingError


class OrderExecutionStrategy(Enum):
    """Order execution strategies"""
    IMMEDIATE = "immediate"
    TWAP = "time_weighted_average_price"
    VWAP = "volume_weighted_average_price"
    ICEBERG = "iceberg"
    SMART_ROUTING = "smart_routing"


@dataclass
class TradingSignal:
    """Trading signal with analysis"""
    instrument_id: str
    symbol: str
    signal_type: str  # 'BUY', 'SELL', 'HOLD'
    strength: float   # 0-1 signal strength
    confidence: float # 0-1 confidence level
    entry_price: Optional[Decimal]
    stop_loss: Optional[Decimal]
    take_profit: Optional[Decimal]
    reasoning: List[str]
    timestamp: datetime


@dataclass
class MarketAnalysis:
    """Market analysis result"""
    instrument_id: str
    trend_direction: str  # 'UP', 'DOWN', 'SIDEWAYS'
    trend_strength: float # 0-1
    volatility: float     # 0-1
    support_levels: List[Decimal]
    resistance_levels: List[Decimal]
    technical_indicators: Dict[str, float]
    analysis_timestamp: datetime


class AdvancedTradingUtils:
    """Advanced Trading Utilities and Automation"""
    
    def __init__(self, cfg: Config, sm: SessionManager):
        self.cfg = cfg
        self.sm = sm
        self._signal_cache: Dict[str, TradingSignal] = {}
        self._analysis_cache: Dict[str, MarketAnalysis] = {}
        self._execution_strategies: Dict[str, Callable] = {
            OrderExecutionStrategy.IMMEDIATE.value: self._execute_immediate,
            OrderExecutionStrategy.TWAP.value: self._execute_twap,
            OrderExecutionStrategy.ICEBERG.value: self._execute_iceberg
        }

    def analyze_market_conditions(self, instrument_id: str, 
                                timeframe: str = '1H',
                                periods: int = 50) -> MarketAnalysis:
        """
        Comprehensive market analysis using chart data
        
        Args:
            instrument_id: Plus500 instrument ID
            timeframe: Chart timeframe for analysis
            periods: Number of periods to analyze
            
        Returns:
            MarketAnalysis with technical analysis
        """
        try:
            # Get chart data for analysis
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=periods)
            
            chart_data = self._get_chart_data(instrument_id, timeframe, start_time, end_time)
            
            if not chart_data:
                raise TradingError(f"No chart data available for {instrument_id}")
            
            # Perform technical analysis
            trend_analysis = self._analyze_trend(chart_data)
            volatility = self._calculate_volatility(chart_data)
            support_resistance = self._find_support_resistance_levels(chart_data)
            technical_indicators = self._calculate_technical_indicators(chart_data)
            
            return MarketAnalysis(
                instrument_id=instrument_id,
                trend_direction=trend_analysis['direction'],
                trend_strength=trend_analysis['strength'],
                volatility=volatility,
                support_levels=support_resistance['support'],
                resistance_levels=support_resistance['resistance'],
                technical_indicators=technical_indicators,
                analysis_timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            raise TradingError(f"Failed to analyze market conditions: {str(e)}")

    def _get_chart_data(self, instrument_id: str, timeframe: str,
                       start_time: datetime, end_time: datetime) -> List[Plus500ChartData]:
        """Get chart data for analysis"""
        if not self.sm.has_valid_plus500_session():
            raise AuthenticationError("Valid Plus500 session required")
        
        session_info = self.sm._load_plus500_session()
        if not session_info:
            raise AuthenticationError("No active Plus500 session found")
        
        payload = {
            'SessionID': session_info.session_id,
            'SubSessionID': session_info.sub_session_id,
            'SessionToken': session_info.session_token,
            'InstrumentId': instrument_id,
            'Timeframe': timeframe,
            'StartTime': start_time.isoformat(),
            'EndTime': end_time.isoformat()
        }
        
        response = self.sm.make_plus500_request('/GetChartDataImm', payload)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                return [Plus500ChartData(**item) for item in data]
            else:
                return [Plus500ChartData(**data)]
        else:
            raise TradingError(f"Failed to get chart data: {response.status_code}")

    def _analyze_trend(self, chart_data: List[Plus500ChartData]) -> Dict[str, Any]:
        """Analyze price trend from chart data"""
        if len(chart_data) < 10:
            return {'direction': 'SIDEWAYS', 'strength': 0.0}
        
        # Simple trend analysis using moving averages
        prices = [float(candle.close_price) for candle in chart_data]
        
        # Calculate short and long moving averages
        short_ma = sum(prices[-10:]) / 10
        long_ma = sum(prices[-20:]) / 20 if len(prices) >= 20 else sum(prices) / len(prices)
        
        # Determine trend direction
        if short_ma > long_ma * 1.02:  # 2% threshold
            direction = 'UP'
            strength = min((short_ma - long_ma) / long_ma * 10, 1.0)
        elif short_ma < long_ma * 0.98:  # 2% threshold
            direction = 'DOWN'
            strength = min((long_ma - short_ma) / long_ma * 10, 1.0)
        else:
            direction = 'SIDEWAYS'
            strength = 0.0
        
        return {'direction': direction, 'strength': strength}

    def _calculate_volatility(self, chart_data: List[Plus500ChartData]) -> float:
        """Calculate price volatility"""
        if len(chart_data) < 2:
            return 0.0
        
        # Calculate price changes
        price_changes = []
        for i in range(1, len(chart_data)):
            prev_close = float(chart_data[i-1].close_price)
            curr_close = float(chart_data[i].close_price)
            change = abs(curr_close - prev_close) / prev_close
            price_changes.append(change)
        
        # Average volatility
        avg_volatility = sum(price_changes) / len(price_changes)
        return min(avg_volatility * 10, 1.0)  # Normalize to 0-1

    def _find_support_resistance_levels(self, chart_data: List[Plus500ChartData]) -> Dict[str, List[Decimal]]:
        """Find support and resistance levels"""
        if len(chart_data) < 10:
            return {'support': [], 'resistance': []}
        
        highs = [candle.high_price for candle in chart_data]
        lows = [candle.low_price for candle in chart_data]
        
        # Simple support/resistance detection
        support_levels = []
        resistance_levels = []
        
        # Find local minima (support) and maxima (resistance)
        for i in range(2, len(chart_data) - 2):
            # Support level
            if (lows[i] <= lows[i-1] and lows[i] <= lows[i-2] and 
                lows[i] <= lows[i+1] and lows[i] <= lows[i+2]):
                support_levels.append(lows[i])
            
            # Resistance level
            if (highs[i] >= highs[i-1] and highs[i] >= highs[i-2] and 
                highs[i] >= highs[i+1] and highs[i] >= highs[i+2]):
                resistance_levels.append(highs[i])
        
        return {
            'support': sorted(set(support_levels))[-3:],  # Top 3 support levels
            'resistance': sorted(set(resistance_levels), reverse=True)[:3]  # Top 3 resistance levels
        }

    def _calculate_technical_indicators(self, chart_data: List[Plus500ChartData]) -> Dict[str, float]:
        """Calculate technical indicators"""
        if len(chart_data) < 14:
            return {}
        
        prices = [float(candle.close_price) for candle in chart_data]
        highs = [float(candle.high_price) for candle in chart_data]
        lows = [float(candle.low_price) for candle in chart_data]
        
        indicators = {}
        
        # Simple RSI calculation
        rsi = self._calculate_rsi(prices, 14)
        if rsi is not None:
            indicators['rsi'] = rsi
        
        # Moving average convergence
        sma_10 = sum(prices[-10:]) / 10
        sma_20 = sum(prices[-20:]) / 20 if len(prices) >= 20 else sma_10
        indicators['sma_10'] = sma_10
        indicators['sma_20'] = sma_20
        indicators['ma_convergence'] = (sma_10 - sma_20) / sma_20
        
        # Price position relative to recent range
        recent_high = max(highs[-10:])
        recent_low = min(lows[-10:])
        current_price = prices[-1]
        
        if recent_high != recent_low:
            indicators['price_position'] = (current_price - recent_low) / (recent_high - recent_low)
        
        return indicators

    def _calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return None
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        if len(gains) < period:
            return None
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi

    def generate_trading_signal(self, instrument_id: str) -> TradingSignal:
        """
        Generate trading signal based on market analysis
        
        Args:
            instrument_id: Plus500 instrument ID
            
        Returns:
            TradingSignal with recommendation
        """
        try:
            # Get market analysis
            analysis = self.analyze_market_conditions(instrument_id)
            
            # Get current pricing
            buy_sell_info = self._get_buy_sell_info(instrument_id)
            
            # Generate signal based on analysis
            signal_type = 'HOLD'
            strength = 0.0
            confidence = 0.0
            reasoning = []
            
            # Trend-based signals
            if analysis.trend_direction == 'UP' and analysis.trend_strength > 0.6:
                signal_type = 'BUY'
                strength += analysis.trend_strength * 0.4
                reasoning.append(f"Strong uptrend detected (strength: {analysis.trend_strength:.2f})")
            elif analysis.trend_direction == 'DOWN' and analysis.trend_strength > 0.6:
                signal_type = 'SELL'
                strength += analysis.trend_strength * 0.4
                reasoning.append(f"Strong downtrend detected (strength: {analysis.trend_strength:.2f})")
            
            # RSI-based signals
            rsi = analysis.technical_indicators.get('rsi')
            if rsi:
                if rsi < 30 and signal_type != 'SELL':
                    signal_type = 'BUY'
                    strength += 0.3
                    reasoning.append(f"RSI oversold condition (RSI: {rsi:.1f})")
                elif rsi > 70 and signal_type != 'BUY':
                    signal_type = 'SELL'
                    strength += 0.3
                    reasoning.append(f"RSI overbought condition (RSI: {rsi:.1f})")
            
            # Support/resistance signals
            current_price = buy_sell_info.bid_price
            if analysis.support_levels:
                nearest_support = min(analysis.support_levels, key=lambda x: abs(x - current_price))
                if abs(current_price - nearest_support) / current_price < 0.02:  # Within 2%
                    if signal_type != 'SELL':
                        signal_type = 'BUY'
                        strength += 0.2
                        reasoning.append("Price near support level")
            
            if analysis.resistance_levels:
                nearest_resistance = min(analysis.resistance_levels, key=lambda x: abs(x - current_price))
                if abs(current_price - nearest_resistance) / current_price < 0.02:  # Within 2%
                    if signal_type != 'BUY':
                        signal_type = 'SELL'
                        strength += 0.2
                        reasoning.append("Price near resistance level")
            
            # Calculate confidence based on multiple factors
            confidence = min(strength, 1.0)
            if len(reasoning) > 1:
                confidence *= 1.2  # Boost confidence for multiple confirming signals
            
            # Calculate entry, stop loss, and take profit
            entry_price = buy_sell_info.ask_price if signal_type == 'BUY' else buy_sell_info.bid_price
            stop_loss = None
            take_profit = None
            
            if signal_type == 'BUY' and analysis.support_levels:
                stop_loss = max(analysis.support_levels) * Decimal('0.995')  # Just below support
                take_profit = entry_price * Decimal('1.02')  # 2% profit target
            elif signal_type == 'SELL' and analysis.resistance_levels:
                stop_loss = min(analysis.resistance_levels) * Decimal('1.005')  # Just above resistance
                take_profit = entry_price * Decimal('0.98')  # 2% profit target
            
            return TradingSignal(
                instrument_id=instrument_id,
                symbol=buy_sell_info.symbol,
                signal_type=signal_type,
                strength=min(strength, 1.0),
                confidence=min(confidence, 1.0),
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reasoning=reasoning,
                timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            raise TradingError(f"Failed to generate trading signal: {str(e)}")

    def _get_buy_sell_info(self, instrument_id: str) -> Plus500BuySellInfo:
        """Get buy/sell information for instrument"""
        if not self.sm.has_valid_plus500_session():
            raise AuthenticationError("Valid Plus500 session required")
        
        session_info = self.sm._load_plus500_session()
        if not session_info:
            raise AuthenticationError("No active Plus500 session found")
        
        payload = {
            'SessionID': session_info.session_id,
            'SubSessionID': session_info.sub_session_id,
            'SessionToken': session_info.session_token,
            'InstrumentId': instrument_id
        }
        
        response = self.sm.make_plus500_request('/FuturesBuySellInfoImm', payload)
        
        if response.status_code == 200:
            data = response.json()
            return Plus500BuySellInfo(**data)
        else:
            raise TradingError(f"Failed to get buy/sell info: {response.status_code}")

    def execute_smart_order(self, order_request: Plus500OrderRequest,
                          strategy: OrderExecutionStrategy = OrderExecutionStrategy.IMMEDIATE,
                          strategy_params: Optional[Dict[str, Any]] = None) -> Plus500OrderResponse:
        """
        Execute order using specified strategy
        
        Args:
            order_request: Order to execute
            strategy: Execution strategy to use
            strategy_params: Strategy-specific parameters
            
        Returns:
            Plus500OrderResponse from execution
        """
        try:
            strategy_func = self._execution_strategies.get(strategy.value)
            if not strategy_func:
                raise TradingError(f"Unsupported execution strategy: {strategy}")
            
            return strategy_func(order_request, strategy_params or {})
            
        except Exception as e:
            raise TradingError(f"Failed to execute smart order: {str(e)}")

    def _execute_immediate(self, order_request: Plus500OrderRequest, 
                         params: Dict[str, Any]) -> Plus500OrderResponse:
        """Execute order immediately"""
        if not self.sm.has_valid_plus500_session():
            raise AuthenticationError("Valid Plus500 session required")
        
        session_info = self.sm._load_plus500_session()
        if not session_info:
            raise AuthenticationError("No active Plus500 session found")
        
        # Build order payload
        payload = {
            'SessionID': session_info.session_id,
            'SubSessionID': session_info.sub_session_id,
            'SessionToken': session_info.session_token,
            'InstrumentId': order_request.instrument_id,
            'Amount': str(order_request.amount),
            'OperationType': order_request.operation_type,
            'OrderType': order_request.order_type,
            'DurationType': order_request.duration_type
        }
        
        if order_request.limit_price:
            payload['LimitPrice'] = str(order_request.limit_price)
        if order_request.stop_price:
            payload['StopPrice'] = str(order_request.stop_price)
        if order_request.take_profit_price_diff:
            payload['TakeProfitPriceDiff'] = str(order_request.take_profit_price_diff)
        if order_request.stop_loss_price_diff:
            payload['StopLossPriceDiff'] = str(order_request.stop_loss_price_diff)
        
        response = self.sm.make_plus500_request('/FuturesCreateOrder', payload)
        
        if response.status_code == 200:
            data = response.json()
            return Plus500OrderResponse(**data)
        else:
            raise TradingError(f"Failed to create order: {response.status_code}")

    def _execute_twap(self, order_request: Plus500OrderRequest, 
                    params: Dict[str, Any]) -> Plus500OrderResponse:
        """Execute order using Time Weighted Average Price strategy"""
        # This would implement TWAP execution by splitting the order over time
        # For now, fall back to immediate execution
        return self._execute_immediate(order_request, params)

    def _execute_iceberg(self, order_request: Plus500OrderRequest, 
                       params: Dict[str, Any]) -> Plus500OrderResponse:
        """Execute order using Iceberg strategy (split into smaller orders)"""
        # This would implement iceberg execution by splitting large orders
        # For now, fall back to immediate execution
        return self._execute_immediate(order_request, params)

    def scan_instruments_for_signals(self, instrument_ids: List[str],
                                   min_confidence: float = 0.6) -> List[TradingSignal]:
        """
        Scan multiple instruments for trading signals
        
        Args:
            instrument_ids: List of instruments to scan
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of signals meeting confidence criteria
        """
        signals = []
        
        for instrument_id in instrument_ids:
            try:
                signal = self.generate_trading_signal(instrument_id)
                if signal.confidence >= min_confidence:
                    signals.append(signal)
            except Exception:
                # Continue with other instruments if one fails
                continue
        
        # Sort by confidence and strength
        signals.sort(key=lambda s: (s.confidence, s.strength), reverse=True)
        return signals

    def optimize_position_sizing(self, signal: TradingSignal, 
                               account_balance: Decimal,
                               max_risk_percent: float = 2.0) -> Decimal:
        """
        Calculate optimal position size based on risk management
        
        Args:
            signal: Trading signal
            account_balance: Available account balance
            max_risk_percent: Maximum risk percentage per trade
            
        Returns:
            Optimal position size
        """
        if not signal.entry_price or not signal.stop_loss:
            # Default to small position if no risk levels defined
            return account_balance * Decimal(str(max_risk_percent / 100)) / signal.entry_price
        
        # Calculate risk per unit
        risk_per_unit = abs(signal.entry_price - signal.stop_loss)
        
        # Calculate maximum risk amount
        max_risk_amount = account_balance * Decimal(str(max_risk_percent / 100))
        
        # Calculate position size
        position_size = max_risk_amount / risk_per_unit
        
        # Apply confidence scaling
        position_size *= Decimal(str(signal.confidence))
        
        return position_size

    def backtest_strategy(self, instrument_ids: List[str],
                         start_date: datetime,
                         end_date: datetime,
                         initial_balance: Decimal = Decimal('10000')) -> Dict[str, Any]:
        """
        Simple backtesting framework for trading strategies
        
        Args:
            instrument_ids: Instruments to test
            start_date: Backtest start date
            end_date: Backtest end date
            initial_balance: Initial account balance
            
        Returns:
            Backtest results
        """
        # This would implement a comprehensive backtesting framework
        # For now, return a placeholder structure
        return {
            'instruments_tested': len(instrument_ids),
            'test_period_days': (end_date - start_date).days,
            'initial_balance': float(initial_balance),
            'final_balance': float(initial_balance),  # Placeholder
            'total_return': 0.0,
            'win_rate': 0.0,
            'max_drawdown': 0.0,
            'total_trades': 0,
            'avg_trade_duration': 0.0,
            'sharpe_ratio': 0.0,
            'backtest_timestamp': datetime.now(timezone.utc).isoformat()
        }
