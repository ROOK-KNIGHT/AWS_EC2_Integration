#!/usr/bin/env python3
"""
Database models for trading dashboard
Tracks trades, positions, metrics, alerts, and watchlists
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import json

db = SQLAlchemy()

class Trade(db.Model):
    """Model for individual trades"""
    __tablename__ = 'trades'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    symbol = db.Column(db.String(10), nullable=False)
    action_type = db.Column(db.String(20), nullable=False)  # BUY, SELL, SELL_SHORT, BUY_TO_COVER
    order_type = db.Column(db.String(20), nullable=False)   # market, limit, stop, etc.
    shares = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=True)
    limit_price = db.Column(db.Float, nullable=True)
    stop_price = db.Column(db.Float, nullable=True)
    fill_price = db.Column(db.Float, nullable=True)
    dollar_amount = db.Column(db.Float, nullable=True)
    order_id = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20), nullable=False)       # submitted, filled, rejected, cancelled
    account_number = db.Column(db.String(50), nullable=True)
    commission = db.Column(db.Float, default=0.0)
    fees = db.Column(db.Float, default=0.0)
    
    # Relationships
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id'), nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'symbol': self.symbol,
            'action_type': self.action_type,
            'order_type': self.order_type,
            'shares': self.shares,
            'price': self.price,
            'limit_price': self.limit_price,
            'stop_price': self.stop_price,
            'fill_price': self.fill_price,
            'dollar_amount': self.dollar_amount,
            'order_id': self.order_id,
            'status': self.status,
            'account_number': self.account_number,
            'commission': self.commission,
            'fees': self.fees
        }

class Position(db.Model):
    """Model for current positions"""
    __tablename__ = 'positions'
    
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), nullable=False, unique=True)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    average_cost = db.Column(db.Float, nullable=True)
    current_price = db.Column(db.Float, nullable=True)
    market_value = db.Column(db.Float, nullable=True)
    unrealized_pl = db.Column(db.Float, nullable=True)
    unrealized_pl_percent = db.Column(db.Float, nullable=True)
    realized_pl = db.Column(db.Float, default=0.0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    account_number = db.Column(db.String(50), nullable=True)
    
    # Options-specific fields
    is_option = db.Column(db.Boolean, default=False)
    option_type = db.Column(db.String(10), nullable=True)  # CALL, PUT
    strike_price = db.Column(db.Float, nullable=True)
    expiration_date = db.Column(db.Date, nullable=True)
    implied_volatility = db.Column(db.Float, nullable=True)
    delta = db.Column(db.Float, nullable=True)
    gamma = db.Column(db.Float, nullable=True)
    theta = db.Column(db.Float, nullable=True)
    vega = db.Column(db.Float, nullable=True)
    
    # Relationships
    trades = relationship("Trade", backref="position")
    
    def to_dict(self):
        return {
            'id': self.id,
            'symbol': self.symbol,
            'quantity': self.quantity,
            'average_cost': self.average_cost,
            'current_price': self.current_price,
            'market_value': self.market_value,
            'unrealized_pl': self.unrealized_pl,
            'unrealized_pl_percent': self.unrealized_pl_percent,
            'realized_pl': self.realized_pl,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'account_number': self.account_number,
            'is_option': self.is_option,
            'option_type': self.option_type,
            'strike_price': self.strike_price,
            'expiration_date': self.expiration_date.isoformat() if self.expiration_date else None,
            'implied_volatility': self.implied_volatility,
            'delta': self.delta,
            'gamma': self.gamma,
            'theta': self.theta,
            'vega': self.vega
        }

class DailyMetrics(db.Model):
    """Model for daily trading metrics"""
    __tablename__ = 'daily_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True)
    total_pl = db.Column(db.Float, default=0.0)
    realized_pl = db.Column(db.Float, default=0.0)
    unrealized_pl = db.Column(db.Float, default=0.0)
    total_trades = db.Column(db.Integer, default=0)
    winning_trades = db.Column(db.Integer, default=0)
    losing_trades = db.Column(db.Integer, default=0)
    portfolio_value = db.Column(db.Float, nullable=True)
    cash_balance = db.Column(db.Float, nullable=True)
    margin_used = db.Column(db.Float, default=0.0)
    buying_power = db.Column(db.Float, nullable=True)
    
    # Risk metrics
    max_drawdown = db.Column(db.Float, nullable=True)
    sharpe_ratio = db.Column(db.Float, nullable=True)
    win_rate = db.Column(db.Float, nullable=True)
    profit_factor = db.Column(db.Float, nullable=True)
    expectancy = db.Column(db.Float, nullable=True)
    
    # Options-specific metrics
    total_theta_decay = db.Column(db.Float, default=0.0)
    total_delta_exposure = db.Column(db.Float, default=0.0)
    iv_rank_avg = db.Column(db.Float, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'total_pl': self.total_pl,
            'realized_pl': self.realized_pl,
            'unrealized_pl': self.unrealized_pl,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'portfolio_value': self.portfolio_value,
            'cash_balance': self.cash_balance,
            'margin_used': self.margin_used,
            'buying_power': self.buying_power,
            'max_drawdown': self.max_drawdown,
            'sharpe_ratio': self.sharpe_ratio,
            'win_rate': self.win_rate,
            'profit_factor': self.profit_factor,
            'expectancy': self.expectancy,
            'total_theta_decay': self.total_theta_decay,
            'total_delta_exposure': self.total_delta_exposure,
            'iv_rank_avg': self.iv_rank_avg
        }

class Watchlist(db.Model):
    """Model for watchlists"""
    __tablename__ = 'watchlists'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    items = relationship("WatchlistItem", backref="watchlist", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active,
            'items': [item.to_dict() for item in self.items]
        }

class WatchlistItem(db.Model):
    """Model for watchlist items"""
    __tablename__ = 'watchlist_items'
    
    id = db.Column(db.Integer, primary_key=True)
    watchlist_id = db.Column(db.Integer, db.ForeignKey('watchlists.id'), nullable=False)
    symbol = db.Column(db.String(10), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)
    target_price = db.Column(db.Float, nullable=True)
    stop_loss = db.Column(db.Float, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'watchlist_id': self.watchlist_id,
            'symbol': self.symbol,
            'added_at': self.added_at.isoformat() if self.added_at else None,
            'notes': self.notes,
            'target_price': self.target_price,
            'stop_loss': self.stop_loss
        }

class Alert(db.Model):
    """Model for trading alerts"""
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    alert_type = db.Column(db.String(50), nullable=False)  # price, pl_loss, volatility, etc.
    symbol = db.Column(db.String(10), nullable=True)
    condition = db.Column(db.String(50), nullable=False)   # above, below, equals
    threshold_value = db.Column(db.Float, nullable=False)
    current_value = db.Column(db.Float, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    is_triggered = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    triggered_at = db.Column(db.DateTime, nullable=True)
    last_checked = db.Column(db.DateTime, nullable=True)
    
    # Notification settings
    email_enabled = db.Column(db.Boolean, default=True)
    telegram_enabled = db.Column(db.Boolean, default=False)
    slack_enabled = db.Column(db.Boolean, default=False)
    
    # Alert message
    message = db.Column(db.Text, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'alert_type': self.alert_type,
            'symbol': self.symbol,
            'condition': self.condition,
            'threshold_value': self.threshold_value,
            'current_value': self.current_value,
            'is_active': self.is_active,
            'is_triggered': self.is_triggered,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'triggered_at': self.triggered_at.isoformat() if self.triggered_at else None,
            'last_checked': self.last_checked.isoformat() if self.last_checked else None,
            'email_enabled': self.email_enabled,
            'telegram_enabled': self.telegram_enabled,
            'slack_enabled': self.slack_enabled,
            'message': self.message
        }

class NotificationLog(db.Model):
    """Model for notification history"""
    __tablename__ = 'notification_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    alert_id = db.Column(db.Integer, db.ForeignKey('alerts.id'), nullable=True)
    notification_type = db.Column(db.String(20), nullable=False)  # email, telegram, slack
    recipient = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(200), nullable=True)
    message = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')  # pending, sent, failed
    error_message = db.Column(db.Text, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'alert_id': self.alert_id,
            'notification_type': self.notification_type,
            'recipient': self.recipient,
            'subject': self.subject,
            'message': self.message,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'status': self.status,
            'error_message': self.error_message
        }

class MarketData(db.Model):
    """Model for storing market data snapshots"""
    __tablename__ = 'market_data'
    
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    price = db.Column(db.Float, nullable=False)
    volume = db.Column(db.Integer, nullable=True)
    bid = db.Column(db.Float, nullable=True)
    ask = db.Column(db.Float, nullable=True)
    high = db.Column(db.Float, nullable=True)
    low = db.Column(db.Float, nullable=True)
    open_price = db.Column(db.Float, nullable=True)
    previous_close = db.Column(db.Float, nullable=True)
    
    # Options-specific data
    implied_volatility = db.Column(db.Float, nullable=True)
    iv_rank = db.Column(db.Float, nullable=True)
    iv_percentile = db.Column(db.Float, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'price': self.price,
            'volume': self.volume,
            'bid': self.bid,
            'ask': self.ask,
            'high': self.high,
            'low': self.low,
            'open_price': self.open_price,
            'previous_close': self.previous_close,
            'implied_volatility': self.implied_volatility,
            'iv_rank': self.iv_rank,
            'iv_percentile': self.iv_percentile
        }

class Configuration(db.Model):
    """Model for storing application configuration"""
    __tablename__ = 'configurations'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), nullable=False, unique=True)
    value = db.Column(db.Text, nullable=True)
    data_type = db.Column(db.String(20), default='string')  # string, int, float, bool, json
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_value(self):
        """Get the value with proper type conversion"""
        if self.value is None:
            return None
        
        if self.data_type == 'int':
            return int(self.value)
        elif self.data_type == 'float':
            return float(self.value)
        elif self.data_type == 'bool':
            return self.value.lower() in ('true', '1', 'yes', 'on')
        elif self.data_type == 'json':
            return json.loads(self.value)
        else:
            return self.value
    
    def set_value(self, value):
        """Set the value with proper type conversion"""
        if self.data_type == 'json':
            self.value = json.dumps(value)
        else:
            self.value = str(value)
    
    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'value': self.get_value(),
            'data_type': self.data_type,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
