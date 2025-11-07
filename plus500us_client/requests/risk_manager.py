"""
Advanced Risk Management Module for Plus500 API Client - Phase 3
Implements comprehensive risk management features and Tier 3 advanced operations
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import asyncio
from dataclasses import dataclass

from .config import Config
from .session import SessionManager
from .models import (
    Plus500OrderRequest, Plus500Position, Plus500AccountInfo,
    Plus500MarginCalculation, Plus500OrderValidation, RiskManagementSettings
)
from .errors import AuthenticationError, TradingError


@dataclass
class RiskAssessment:
    """Risk assessment result for trading decisions"""
    risk_score: float  # 0-100 scale
    risk_level: str   # 'LOW', 'MEDIUM', 'HIGH', 'EXTREME'
    max_position_size: Decimal
    recommended_position_size: Decimal
    risk_warnings: List[str]
    risk_factors: Dict[str, float]
    assessment_timestamp: datetime


@dataclass
class PositionRisk:
    """Individual position risk analysis"""
    position_id: str
    instrument_id: str
    current_risk_amount: Decimal
    max_loss_potential: Decimal
    risk_reward_ratio: Decimal
    margin_utilization: float
    overnight_exposure: bool
    risk_recommendations: List[str]


class AdvancedRiskManager:
    """Advanced Risk Management for Plus500 Trading Operations"""
    
    def __init__(self, cfg: Config, sm: SessionManager):
        self.cfg = cfg
        self.sm = sm
        self.risk_settings = RiskManagementSettings()
        self._risk_cache: Dict[str, RiskAssessment] = {}
        self._cache_ttl_minutes = 5

    def assess_account_risk(self, account_info: Plus500AccountInfo) -> RiskAssessment:
        """
        Comprehensive account risk assessment
        
        Args:
            account_info: Current account information
            
        Returns:
            RiskAssessment with detailed risk analysis
        """
        try:
            risk_factors = {}
            risk_warnings = []
            
            # Calculate leverage ratio
            leverage_ratio = float(account_info.margin_used / account_info.equity) if account_info.equity > 0 else 0
            risk_factors['leverage_ratio'] = leverage_ratio
            
            # Calculate margin utilization
            total_margin = account_info.margin_used + account_info.available_margin
            margin_utilization = float(account_info.margin_used / total_margin) if total_margin > 0 else 0
            risk_factors['margin_utilization'] = margin_utilization
            
            # Calculate unrealized P&L ratio
            unrealized_pnl_ratio = float(account_info.unrealized_pnl / account_info.equity) if account_info.equity > 0 else 0
            risk_factors['unrealized_pnl_ratio'] = abs(unrealized_pnl_ratio)
            
            # Daily P&L impact
            daily_pnl_ratio = 0
            if hasattr(account_info, 'daily_pnl') and account_info.daily_pnl and account_info.equity > 0:
                daily_pnl_ratio = float(account_info.daily_pnl / account_info.equity)
            risk_factors['daily_pnl_impact'] = abs(daily_pnl_ratio)
            
            # Calculate risk score (0-100)
            risk_score = self._calculate_risk_score(risk_factors)
            
            # Determine risk level
            risk_level = self._determine_risk_level(risk_score)
            
            # Generate warnings
            if leverage_ratio > 0.8:
                risk_warnings.append("High leverage ratio detected")
            if margin_utilization > 0.9:
                risk_warnings.append("Margin utilization approaching limits")
            if abs(unrealized_pnl_ratio) > 0.1:
                risk_warnings.append("Significant unrealized P&L exposure")
            
            # Calculate position size recommendations
            max_position_size = self._calculate_max_position_size(account_info)
            recommended_position_size = max_position_size * Decimal('0.5')  # Conservative 50%
            
            return RiskAssessment(
                risk_score=risk_score,
                risk_level=risk_level,
                max_position_size=max_position_size,
                recommended_position_size=recommended_position_size,
                risk_warnings=risk_warnings,
                risk_factors=risk_factors,
                assessment_timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            raise TradingError(f"Failed to assess account risk: {str(e)}")

    def _calculate_risk_score(self, risk_factors: Dict[str, float]) -> float:
        """Calculate composite risk score from individual factors"""
        weights = {
            'leverage_ratio': 0.3,
            'margin_utilization': 0.25,
            'unrealized_pnl_ratio': 0.25,
            'daily_pnl_impact': 0.2
        }
        
        score = 0.0
        for factor, value in risk_factors.items():
            weight = weights.get(factor, 0.1)
            normalized_value = min(value * 100, 100)  # Normalize to 0-100
            score += normalized_value * weight
        
        return min(score, 100.0)

    def _determine_risk_level(self, risk_score: float) -> str:
        """Determine risk level from risk score"""
        if risk_score < 25:
            return 'LOW'
        elif risk_score < 50:
            return 'MEDIUM'
        elif risk_score < 75:
            return 'HIGH'
        else:
            return 'EXTREME'

    def _calculate_max_position_size(self, account_info: Plus500AccountInfo) -> Decimal:
        """Calculate maximum recommended position size based on account equity"""
        max_risk_amount = account_info.equity * (self.risk_settings.max_risk_per_trade_pct / 100)
        # This would need instrument-specific margin requirements in a real implementation
        return max_risk_amount

    def validate_order_risk(self, order_request: Plus500OrderRequest, 
                          account_info: Plus500AccountInfo) -> Plus500OrderValidation:
        """
        Advanced order risk validation using ValidateOrderImm endpoint
        
        Args:
            order_request: Order to validate
            account_info: Current account state
            
        Returns:
            Plus500OrderValidation with enhanced risk checks
        """
        if not self.sm.has_valid_plus500_session():
            raise AuthenticationError("Valid Plus500 session required")
        
        session_info = self.sm._load_plus500_session()
        if not session_info:
            raise AuthenticationError("No active Plus500 session found")
        
        # Prepare validation payload
        payload = {
            'SessionID': session_info.session_id,
            'SubSessionID': session_info.sub_session_id,
            'SessionToken': session_info.session_token,
            'InstrumentId': order_request.instrument_id,
            'Amount': str(order_request.amount),
            'OperationType': order_request.operation_type,
            'OrderType': order_request.order_type
        }
        
        if order_request.limit_price:
            payload['LimitPrice'] = str(order_request.limit_price)
        if order_request.stop_price:
            payload['StopPrice'] = str(order_request.stop_price)
        
        response = self.sm.make_plus500_request('/ValidateOrderImm', payload)
        
        if response.status_code == 200:
            data = response.json()
            validation = Plus500OrderValidation(**data)
            
            # Add custom risk validation
            validation = self._enhance_order_validation(validation, order_request, account_info)
            return validation
        else:
            raise TradingError(f"Failed to validate order: {response.status_code}")

    def _enhance_order_validation(self, validation: Plus500OrderValidation,
                                order_request: Plus500OrderRequest,
                                account_info: Plus500AccountInfo) -> Plus500OrderValidation:
        """Enhance API validation with custom risk checks"""
        additional_errors = []
        
        # Check position size against account risk limits
        risk_assessment = self.assess_account_risk(account_info)
        
        if order_request.amount > risk_assessment.max_position_size:
            additional_errors.append(f"Position size exceeds recommended maximum: {risk_assessment.max_position_size}")
        
        if risk_assessment.risk_level in ['HIGH', 'EXTREME']:
            additional_errors.append(f"Account risk level is {risk_assessment.risk_level} - consider reducing exposure")
        
        # Check margin utilization
        if validation.estimated_margin:
            new_margin_used = account_info.margin_used + validation.estimated_margin
            total_margin = account_info.margin_used + account_info.available_margin
            new_utilization = float(new_margin_used / total_margin) if total_margin > 0 else 0
            
            if new_utilization > 0.95:
                additional_errors.append("Order would exceed safe margin utilization limits")
        
        # Add additional errors to validation
        validation.validation_errors.extend(additional_errors)
        validation.is_valid = validation.is_valid and len(additional_errors) == 0
        
        return validation

    def add_risk_management_to_position(self, instrument_id: str, 
                                      risk_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add risk management to instrument using FuturesAddRiskManagementToInstrument
        
        Args:
            instrument_id: Plus500 instrument ID
            risk_params: Risk management parameters
            
        Returns:
            Response from risk management operation
        """
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
            **risk_params
        }
        
        response = self.sm.make_plus500_request('/FuturesAddRiskManagementToInstrument', payload)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise TradingError(f"Failed to add risk management: {response.status_code}")

    def analyze_position_risks(self, positions: List[Plus500Position]) -> List[PositionRisk]:
        """
        Analyze risk for all open positions
        
        Args:
            positions: List of open positions
            
        Returns:
            List of PositionRisk analysis for each position
        """
        position_risks = []
        
        for position in positions:
            try:
                # Calculate position risk metrics
                risk_amount = position.amount * position.open_price if position.open_price else Decimal('0')
                
                # Calculate current P&L and potential loss
                current_pnl = position.unrealized_pnl or Decimal('0')
                
                # Estimate max loss (this would be enhanced with stop loss info)
                max_loss_potential = risk_amount * Decimal('0.1')  # Assume 10% max loss
                
                # Calculate risk-reward ratio (simplified)
                risk_reward_ratio = abs(current_pnl / max_loss_potential) if max_loss_potential > 0 else Decimal('0')
                
                # Margin utilization for this position
                margin_utilization = float(position.margin_used / risk_amount) if risk_amount > 0 else 0.0
                
                # Check overnight exposure (simplified - would check market hours)
                overnight_exposure = True  # Placeholder
                
                # Generate recommendations
                recommendations = []
                if margin_utilization > 0.5:
                    recommendations.append("Consider reducing position size")
                if current_pnl < -max_loss_potential * Decimal('0.5'):
                    recommendations.append("Position approaching stop loss levels")
                if overnight_exposure:
                    recommendations.append("Monitor overnight funding costs")
                
                position_risk = PositionRisk(
                    position_id=position.position_id,
                    instrument_id=position.instrument_id,
                    current_risk_amount=risk_amount,
                    max_loss_potential=max_loss_potential,
                    risk_reward_ratio=float(risk_reward_ratio),
                    margin_utilization=margin_utilization,
                    overnight_exposure=overnight_exposure,
                    risk_recommendations=recommendations
                )
                
                position_risks.append(position_risk)
                
            except Exception as e:
                # Log error but continue with other positions
                continue
        
        return position_risks

    def calculate_portfolio_risk(self, positions: List[Plus500Position], 
                               account_info: Plus500AccountInfo) -> Dict[str, Any]:
        """
        Calculate overall portfolio risk metrics
        
        Args:
            positions: All open positions
            account_info: Current account state
            
        Returns:
            Portfolio risk analysis
        """
        try:
            position_risks = self.analyze_position_risks(positions)
            
            # Portfolio-level calculations
            total_risk_amount = sum(pr.current_risk_amount for pr in position_risks)
            total_unrealized_pnl = sum(pos.unrealized_pnl or Decimal('0') for pos in positions)
            
            # Diversification analysis
            instruments = set(pos.instrument_id for pos in positions)
            diversification_score = min(len(instruments) / 10, 1.0)  # Normalized to 0-1
            
            # Correlation risk (simplified)
            correlation_risk = 1.0 - diversification_score
            
            # Overall portfolio risk score
            portfolio_risk_score = self._calculate_portfolio_risk_score(
                position_risks, account_info, correlation_risk
            )
            
            return {
                'portfolio_risk_score': portfolio_risk_score,
                'total_positions': len(positions),
                'total_risk_amount': float(total_risk_amount),
                'total_unrealized_pnl': float(total_unrealized_pnl),
                'diversification_score': diversification_score,
                'correlation_risk': correlation_risk,
                'high_risk_positions': len([pr for pr in position_risks if pr.margin_utilization > 0.7]),
                'positions_with_warnings': len([pr for pr in position_risks if pr.risk_recommendations]),
                'analysis_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            raise TradingError(f"Failed to calculate portfolio risk: {str(e)}")

    def _calculate_portfolio_risk_score(self, position_risks: List[PositionRisk],
                                      account_info: Plus500AccountInfo,
                                      correlation_risk: float) -> float:
        """Calculate overall portfolio risk score"""
        if not position_risks:
            return 0.0
        
        # Average position risk
        avg_margin_util = sum(pr.margin_utilization for pr in position_risks) / len(position_risks)
        
        # Account-level risk
        account_risk = self.assess_account_risk(account_info)
        
        # Combine factors
        portfolio_score = (
            avg_margin_util * 0.4 +
            account_risk.risk_score / 100 * 0.4 +
            correlation_risk * 0.2
        ) * 100
        
        return min(portfolio_score, 100.0)

    def get_risk_recommendations(self, account_info: Plus500AccountInfo,
                               positions: List[Plus500Position]) -> List[str]:
        """
        Generate comprehensive risk management recommendations
        
        Args:
            account_info: Current account state
            positions: Open positions
            
        Returns:
            List of risk management recommendations
        """
        recommendations = []
        
        try:
            # Account-level assessment
            account_risk = self.assess_account_risk(account_info)
            recommendations.extend(account_risk.risk_warnings)
            
            # Portfolio-level assessment
            portfolio_risk = self.calculate_portfolio_risk(positions, account_info)
            
            if portfolio_risk['portfolio_risk_score'] > 70:
                recommendations.append("Portfolio risk is high - consider reducing overall exposure")
            
            if portfolio_risk['diversification_score'] < 0.3:
                recommendations.append("Low diversification - consider spreading risk across more instruments")
            
            if portfolio_risk['high_risk_positions'] > 0:
                recommendations.append(f"{portfolio_risk['high_risk_positions']} positions have high margin utilization")
            
            # Position-specific recommendations
            position_risks = self.analyze_position_risks(positions)
            for pr in position_risks:
                if pr.risk_recommendations:
                    recommendations.append(f"Position {pr.instrument_id}: {', '.join(pr.risk_recommendations)}")
            
            return recommendations
            
        except Exception as e:
            return [f"Error generating recommendations: {str(e)}"]

    def update_risk_settings(self, new_settings: Dict[str, Any]) -> None:
        """Update risk management settings"""
        for key, value in new_settings.items():
            if hasattr(self.risk_settings, key):
                setattr(self.risk_settings, key, value)

    def get_risk_settings(self) -> Dict[str, Any]:
        """Get current risk management settings"""
        return {
            'break_even_trigger_pct': float(self.risk_settings.break_even_trigger_pct),
            'break_even_buffer_ticks': self.risk_settings.break_even_buffer_ticks,
            'trailing_stop_trigger_pct': float(self.risk_settings.trailing_stop_trigger_pct),
            'trailing_stop_distance_ticks': self.risk_settings.trailing_stop_distance_ticks,
            'max_risk_per_trade_pct': float(self.risk_settings.max_risk_per_trade_pct),
            'default_risk_reward_ratio': float(self.risk_settings.default_risk_reward_ratio),
            'enable_break_even_protection': self.risk_settings.enable_break_even_protection,
            'enable_trailing_stops': self.risk_settings.enable_trailing_stops
        }
