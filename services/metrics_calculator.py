#!/usr/bin/env python3
"""
Metrics Calculator Service
Calculates P/L, risk metrics, and trading statistics
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func, and_, desc
import logging

from models.database import db, Trade, Position, DailyMetrics, MarketData

logger = logging.getLogger(__name__)

class MetricsCalculator:
    """
    Service for calculating trading metrics and risk statistics
    """
    
    def __init__(self, db_session=None):
        """
        Initialize the metrics calculator
        
        Args:
            db_session: Database session (optional)
        """
        self.db_session = db_session or db.session
    
    def calculate_daily_metrics(self, target_date: date = None) -> Dict:
        """
        Calculate daily trading metrics for a specific date
        
        Args:
            target_date: Date to calculate metrics for (defaults to today)
            
        Returns:
            Dictionary containing daily metrics
        """
        if target_date is None:
            target_date = date.today()
        
        try:
            # Get all trades for the target date
            trades = self.db_session.query(Trade).filter(
                func.date(Trade.timestamp) == target_date,
                Trade.status == 'filled'
            ).all()
            
            # Get current positions
            positions = self.db_session.query(Position).all()
            
            # Calculate basic metrics
            total_trades = len(trades)
            realized_pl = sum(self._calculate_trade_pl(trade) for trade in trades)
            unrealized_pl = sum(pos.unrealized_pl or 0 for pos in positions)
            total_pl = realized_pl + unrealized_pl
            
            # Calculate win/loss statistics
            winning_trades = 0
            losing_trades = 0
            for trade in trades:
                trade_pl = self._calculate_trade_pl(trade)
                if trade_pl > 0:
                    winning_trades += 1
                elif trade_pl < 0:
                    losing_trades += 1
            
            # Portfolio metrics
            portfolio_value = sum(pos.market_value or 0 for pos in positions)
            
            # Calculate risk metrics
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            profit_factor = self._calculate_profit_factor(trades)
            expectancy = self._calculate_expectancy(trades)
            
            # Options-specific metrics
            options_positions = [pos for pos in positions if pos.is_option]
            total_theta_decay = sum(pos.theta or 0 for pos in options_positions)
            total_delta_exposure = sum((pos.delta or 0) * pos.quantity for pos in options_positions)
            iv_rank_avg = self._calculate_average_iv_rank(options_positions)
            
            metrics = {
                'date': target_date,
                'total_pl': total_pl,
                'realized_pl': realized_pl,
                'unrealized_pl': unrealized_pl,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'portfolio_value': portfolio_value,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'expectancy': expectancy,
                'total_theta_decay': total_theta_decay,
                'total_delta_exposure': total_delta_exposure,
                'iv_rank_avg': iv_rank_avg
            }
            
            # Save to database
            self._save_daily_metrics(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating daily metrics: {e}")
            return {}
    
    def calculate_portfolio_metrics(self, days: int = 30) -> Dict:
        """
        Calculate portfolio-wide metrics over a specified period
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary containing portfolio metrics
        """
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            # Get daily metrics for the period
            daily_metrics = self.db_session.query(DailyMetrics).filter(
                and_(
                    DailyMetrics.date >= start_date,
                    DailyMetrics.date <= end_date
                )
            ).order_by(DailyMetrics.date).all()
            
            if not daily_metrics:
                return {}
            
            # Convert to DataFrame for easier calculations
            df = pd.DataFrame([metric.to_dict() for metric in daily_metrics])
            
            # Calculate cumulative metrics
            total_realized_pl = df['realized_pl'].sum()
            total_unrealized_pl = df['unrealized_pl'].iloc[-1] if len(df) > 0 else 0
            total_pl = total_realized_pl + total_unrealized_pl
            
            # Calculate returns series
            portfolio_values = df['portfolio_value'].dropna()
            if len(portfolio_values) > 1:
                returns = portfolio_values.pct_change().dropna()
                
                # Risk metrics
                sharpe_ratio = self._calculate_sharpe_ratio(returns)
                max_drawdown = self._calculate_max_drawdown(portfolio_values)
                volatility = returns.std() * np.sqrt(252)  # Annualized volatility
            else:
                sharpe_ratio = 0
                max_drawdown = 0
                volatility = 0
            
            # Trading statistics
            total_trades = df['total_trades'].sum()
            total_winning_trades = df['winning_trades'].sum()
            total_losing_trades = df['losing_trades'].sum()
            
            overall_win_rate = (total_winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Average daily metrics
            avg_daily_pl = df['total_pl'].mean()
            avg_daily_trades = df['total_trades'].mean()
            
            return {
                'period_days': days,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'total_pl': total_pl,
                'total_realized_pl': total_realized_pl,
                'total_unrealized_pl': total_unrealized_pl,
                'total_trades': int(total_trades),
                'winning_trades': int(total_winning_trades),
                'losing_trades': int(total_losing_trades),
                'win_rate': overall_win_rate,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'volatility': volatility,
                'avg_daily_pl': avg_daily_pl,
                'avg_daily_trades': avg_daily_trades,
                'current_portfolio_value': portfolio_values.iloc[-1] if len(portfolio_values) > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error calculating portfolio metrics: {e}")
            return {}
    
    def calculate_position_metrics(self, symbol: str = None) -> List[Dict]:
        """
        Calculate metrics for current positions
        
        Args:
            symbol: Optional symbol to filter by
            
        Returns:
            List of position metrics
        """
        try:
            query = self.db_session.query(Position)
            if symbol:
                query = query.filter(Position.symbol == symbol)
            
            positions = query.all()
            position_metrics = []
            
            for position in positions:
                # Basic position metrics
                unrealized_pl_percent = 0
                if position.average_cost and position.current_price:
                    unrealized_pl_percent = ((position.current_price - position.average_cost) / position.average_cost) * 100
                
                # Days held calculation
                first_trade = self.db_session.query(Trade).filter(
                    Trade.symbol == position.symbol,
                    Trade.status == 'filled'
                ).order_by(Trade.timestamp).first()
                
                days_held = 0
                if first_trade:
                    days_held = (datetime.now() - first_trade.timestamp).days
                
                # Risk metrics for the position
                position_risk = self._calculate_position_risk(position)
                
                metrics = {
                    'symbol': position.symbol,
                    'quantity': position.quantity,
                    'average_cost': position.average_cost,
                    'current_price': position.current_price,
                    'market_value': position.market_value,
                    'unrealized_pl': position.unrealized_pl,
                    'unrealized_pl_percent': unrealized_pl_percent,
                    'realized_pl': position.realized_pl,
                    'days_held': days_held,
                    'position_risk': position_risk,
                    'is_option': position.is_option,
                    'last_updated': position.last_updated.isoformat() if position.last_updated else None
                }
                
                # Add options-specific metrics
                if position.is_option:
                    metrics.update({
                        'option_type': position.option_type,
                        'strike_price': position.strike_price,
                        'expiration_date': position.expiration_date.isoformat() if position.expiration_date else None,
                        'implied_volatility': position.implied_volatility,
                        'delta': position.delta,
                        'gamma': position.gamma,
                        'theta': position.theta,
                        'vega': position.vega,
                        'days_to_expiration': self._calculate_days_to_expiration(position.expiration_date)
                    })
                
                position_metrics.append(metrics)
            
            return position_metrics
            
        except Exception as e:
            logger.error(f"Error calculating position metrics: {e}")
            return []
    
    def calculate_options_metrics(self) -> Dict:
        """
        Calculate options-specific portfolio metrics
        
        Returns:
            Dictionary containing options metrics
        """
        try:
            options_positions = self.db_session.query(Position).filter(
                Position.is_option == True,
                Position.quantity != 0
            ).all()
            
            if not options_positions:
                return {
                    'total_positions': 0,
                    'total_delta': 0,
                    'total_gamma': 0,
                    'total_theta': 0,
                    'total_vega': 0,
                    'net_delta_exposure': 0,
                    'theta_decay_per_day': 0,
                    'avg_iv': 0,
                    'positions_by_expiration': {},
                    'positions_by_type': {'calls': 0, 'puts': 0}
                }
            
            # Calculate aggregate Greeks
            total_delta = sum((pos.delta or 0) * pos.quantity for pos in options_positions)
            total_gamma = sum((pos.gamma or 0) * pos.quantity for pos in options_positions)
            total_theta = sum((pos.theta or 0) * pos.quantity for pos in options_positions)
            total_vega = sum((pos.vega or 0) * pos.quantity for pos in options_positions)
            
            # Net delta exposure (delta * quantity * 100 * current_price)
            net_delta_exposure = sum(
                (pos.delta or 0) * pos.quantity * 100 * (pos.current_price or 0)
                for pos in options_positions
            )
            
            # Theta decay per day
            theta_decay_per_day = total_theta
            
            # Average IV
            iv_values = [pos.implied_volatility for pos in options_positions if pos.implied_volatility]
            avg_iv = sum(iv_values) / len(iv_values) if iv_values else 0
            
            # Positions by expiration
            positions_by_expiration = {}
            for pos in options_positions:
                if pos.expiration_date:
                    exp_str = pos.expiration_date.isoformat()
                    if exp_str not in positions_by_expiration:
                        positions_by_expiration[exp_str] = 0
                    positions_by_expiration[exp_str] += abs(pos.quantity)
            
            # Positions by type
            calls = sum(1 for pos in options_positions if pos.option_type == 'CALL')
            puts = sum(1 for pos in options_positions if pos.option_type == 'PUT')
            
            return {
                'total_positions': len(options_positions),
                'total_delta': total_delta,
                'total_gamma': total_gamma,
                'total_theta': total_theta,
                'total_vega': total_vega,
                'net_delta_exposure': net_delta_exposure,
                'theta_decay_per_day': theta_decay_per_day,
                'avg_iv': avg_iv,
                'positions_by_expiration': positions_by_expiration,
                'positions_by_type': {'calls': calls, 'puts': puts}
            }
            
        except Exception as e:
            logger.error(f"Error calculating options metrics: {e}")
            return {}
    
    def _calculate_trade_pl(self, trade: Trade) -> float:
        """Calculate P/L for a single trade"""
        if not trade.fill_price or not trade.shares:
            return 0.0
        
        # For simplicity, assume we're calculating against average cost
        # In a real implementation, you'd match buy/sell pairs
        if trade.action_type in ['SELL', 'BUY_TO_COVER']:
            # This is a closing trade - calculate P/L
            # You'd need to implement proper trade matching logic here
            return trade.fill_price * trade.shares - (trade.commission or 0) - (trade.fees or 0)
        
        return 0.0
    
    def _calculate_profit_factor(self, trades: List[Trade]) -> float:
        """Calculate profit factor (gross profit / gross loss)"""
        gross_profit = 0
        gross_loss = 0
        
        for trade in trades:
            trade_pl = self._calculate_trade_pl(trade)
            if trade_pl > 0:
                gross_profit += trade_pl
            elif trade_pl < 0:
                gross_loss += abs(trade_pl)
        
        return gross_profit / gross_loss if gross_loss > 0 else 0
    
    def _calculate_expectancy(self, trades: List[Trade]) -> float:
        """Calculate expectancy (average win * win rate - average loss * loss rate)"""
        if not trades:
            return 0
        
        wins = []
        losses = []
        
        for trade in trades:
            trade_pl = self._calculate_trade_pl(trade)
            if trade_pl > 0:
                wins.append(trade_pl)
            elif trade_pl < 0:
                losses.append(abs(trade_pl))
        
        total_trades = len(trades)
        win_rate = len(wins) / total_trades if total_trades > 0 else 0
        loss_rate = len(losses) / total_trades if total_trades > 0 else 0
        
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        
        return (avg_win * win_rate) - (avg_loss * loss_rate)
    
    def _calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio"""
        if len(returns) == 0 or returns.std() == 0:
            return 0
        
        excess_returns = returns.mean() - (risk_free_rate / 252)  # Daily risk-free rate
        return (excess_returns / returns.std()) * np.sqrt(252)  # Annualized
    
    def _calculate_max_drawdown(self, values: pd.Series) -> float:
        """Calculate maximum drawdown"""
        if len(values) == 0:
            return 0
        
        peak = values.expanding().max()
        drawdown = (values - peak) / peak
        return drawdown.min() * 100  # Return as percentage
    
    def _calculate_position_risk(self, position: Position) -> float:
        """Calculate risk for a position (as percentage of portfolio)"""
        if not position.market_value:
            return 0
        
        # Get total portfolio value
        total_portfolio_value = self.db_session.query(
            func.sum(Position.market_value)
        ).scalar() or 0
        
        if total_portfolio_value == 0:
            return 0
        
        return (abs(position.market_value) / total_portfolio_value) * 100
    
    def _calculate_average_iv_rank(self, options_positions: List[Position]) -> float:
        """Calculate average IV rank for options positions"""
        iv_values = [pos.implied_volatility for pos in options_positions if pos.implied_volatility]
        return sum(iv_values) / len(iv_values) if iv_values else 0
    
    def _calculate_days_to_expiration(self, expiration_date: date) -> int:
        """Calculate days to expiration"""
        if not expiration_date:
            return 0
        return (expiration_date - date.today()).days
    
    def _save_daily_metrics(self, metrics: Dict):
        """Save daily metrics to database"""
        try:
            # Check if metrics for this date already exist
            existing = self.db_session.query(DailyMetrics).filter(
                DailyMetrics.date == metrics['date']
            ).first()
            
            if existing:
                # Update existing record
                for key, value in metrics.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
            else:
                # Create new record
                daily_metrics = DailyMetrics(**metrics)
                self.db_session.add(daily_metrics)
            
            self.db_session.commit()
            
        except Exception as e:
            logger.error(f"Error saving daily metrics: {e}")
            self.db_session.rollback()
    
    def get_performance_summary(self, days: int = 30) -> Dict:
        """
        Get a comprehensive performance summary
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary containing performance summary
        """
        try:
            portfolio_metrics = self.calculate_portfolio_metrics(days)
            options_metrics = self.calculate_options_metrics()
            position_metrics = self.calculate_position_metrics()
            
            # Current positions summary
            total_positions = len(position_metrics)
            total_market_value = sum(pos.get('market_value', 0) or 0 for pos in position_metrics)
            total_unrealized_pl = sum(pos.get('unrealized_pl', 0) or 0 for pos in position_metrics)
            
            return {
                'summary': {
                    'total_positions': total_positions,
                    'total_market_value': total_market_value,
                    'total_unrealized_pl': total_unrealized_pl,
                    'period_days': days
                },
                'portfolio_metrics': portfolio_metrics,
                'options_metrics': options_metrics,
                'top_positions': sorted(
                    position_metrics, 
                    key=lambda x: abs(x.get('market_value', 0) or 0), 
                    reverse=True
                )[:10]
            }
            
        except Exception as e:
            logger.error(f"Error generating performance summary: {e}")
            return {}
