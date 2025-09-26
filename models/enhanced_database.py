#!/usr/bin/env python3
"""
Enhanced database models for Charles Schwab API Integration
Comprehensive schema based on actual Schwab API data structures
"""

from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, DateTime, Boolean, Text, 
    JSON, ForeignKey, Date, Numeric, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone
import json

Base = declarative_base()

# ============================================================================
# CORE TABLES
# ============================================================================

class Account(Base):
    """Enhanced account management"""
    __tablename__ = 'accounts'
    
    account_id = Column(BigInteger, primary_key=True)
    account_hash = Column(String(50), unique=True, nullable=False)
    account_number = Column(String(50), unique=True)
    display_name = Column(String(100))
    nickname = Column(String(100))
    account_type = Column(String(20))  # CASH, MARGIN, etc.
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    orders = relationship("Order", back_populates="account")
    transactions = relationship("Transaction", back_populates="account")
    
    __table_args__ = (
        Index('idx_accounts_hash', 'account_hash'),
        Index('idx_accounts_type', 'account_type'),
    )

class Symbol(Base):
    """Security master data"""
    __tablename__ = 'symbols'
    
    symbol_id = Column(BigInteger, primary_key=True)
    symbol = Column(String(10), unique=True, nullable=False)
    company_name = Column(String(200))
    description = Column(Text)
    asset_type = Column(String(20))  # EQUITY, OPTION, INDEX, etc.
    exchange = Column(String(10))
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_symbols_symbol', 'symbol'),
        Index('idx_symbols_type', 'asset_type'),
    )

# ============================================================================
# PRICE DATA TABLES
# ============================================================================

class PriceData(Base):
    """Historical price data with partitioning support"""
    __tablename__ = 'price_data'
    
    price_id = Column(BigInteger, primary_key=True)
    symbol = Column(String(10), nullable=False)
    
    # Timestamp handling (convert from milliseconds)
    datetime_ms = Column(BigInteger, nullable=False)  # Original millisecond timestamp
    datetime_utc = Column(DateTime(timezone=True), nullable=False)  # Converted timestamp
    
    # OHLCV data
    open_price = Column(Numeric(12,4), nullable=False)
    high_price = Column(Numeric(12,4), nullable=False)
    low_price = Column(Numeric(12,4), nullable=False)
    close_price = Column(Numeric(12,4), nullable=False)
    volume = Column(BigInteger, nullable=False)
    
    # Previous close context
    previous_close = Column(Numeric(12,4))
    previous_close_date_ms = Column(BigInteger)
    
    # Data quality flags
    is_empty = Column(Boolean, default=False)
    data_source = Column(String(20), default='schwab_api')
    frequency_type = Column(String(10))  # 'minute', 'daily', 'weekly'
    
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    __table_args__ = (
        UniqueConstraint('symbol', 'datetime_ms', 'frequency_type'),
        Index('idx_price_symbol_datetime', 'symbol', 'datetime_utc'),
        Index('idx_price_datetime', 'datetime_utc'),
        Index('idx_price_volume', 'volume'),
    )

# ============================================================================
# OPTIONS TABLES
# ============================================================================

class OptionsExpiration(Base):
    """Options expiration calendar"""
    __tablename__ = 'options_expirations'
    
    expiration_id = Column(BigInteger, primary_key=True)
    underlying_symbol = Column(String(10), nullable=False)
    expiration_date = Column(Date, nullable=False)
    days_to_expiration = Column(Integer)
    expiration_type = Column(String(1), nullable=False)  # W, S, Q, M
    is_standard = Column(Boolean, default=True)
    is_leap = Column(Boolean, default=False)  # For LEAPS (>1 year)
    
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    chains = relationship("OptionsChain", back_populates="expiration")
    
    __table_args__ = (
        UniqueConstraint('underlying_symbol', 'expiration_date'),
        Index('idx_exp_symbol_date', 'underlying_symbol', 'expiration_date'),
        Index('idx_exp_type_dte', 'expiration_type', 'days_to_expiration'),
        CheckConstraint("expiration_type IN ('W', 'S', 'Q', 'M')"),
    )

class OptionsChain(Base):
    """Options chain snapshots"""
    __tablename__ = 'options_chains'
    
    chain_id = Column(BigInteger, primary_key=True)
    underlying_symbol = Column(String(10), nullable=False)
    expiration_id = Column(BigInteger, ForeignKey('options_expirations.expiration_id'))
    
    # Snapshot metadata
    snapshot_datetime = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20))
    strategy = Column(String(20), default='SINGLE')
    
    # Underlying market data at snapshot time
    underlying_price = Column(Numeric(12,4))
    underlying_bid = Column(Numeric(12,4))
    underlying_ask = Column(Numeric(12,4))
    underlying_last = Column(Numeric(12,4))
    underlying_volume = Column(BigInteger)
    underlying_change = Column(Numeric(12,4))
    underlying_percent_change = Column(Numeric(8,4))
    
    # Market environment
    interest_rate = Column(Numeric(8,6))
    implied_volatility = Column(Numeric(8,4))
    is_delayed = Column(Boolean, default=False)
    is_index = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    expiration = relationship("OptionsExpiration", back_populates="chains")
    contracts = relationship("OptionsContract", back_populates="chain")
    
    __table_args__ = (
        Index('idx_chains_symbol_snapshot', 'underlying_symbol', 'snapshot_datetime'),
        Index('idx_chains_expiration', 'expiration_id'),
        UniqueConstraint('underlying_symbol', 'expiration_id', 'snapshot_datetime'),
    )

class OptionsContract(Base):
    """Individual option contracts"""
    __tablename__ = 'options_contracts'
    
    contract_id = Column(BigInteger, primary_key=True)
    chain_id = Column(BigInteger, ForeignKey('options_chains.chain_id', ondelete='CASCADE'))
    
    # Contract identification
    option_symbol = Column(String(50), nullable=False)
    put_call = Column(String(4), nullable=False)  # PUT, CALL
    strike_price = Column(Numeric(12,4), nullable=False)
    expiration_date = Column(Date, nullable=False)
    days_to_expiration = Column(Integer)
    
    # Pricing data
    bid_price = Column(Numeric(12,4))
    ask_price = Column(Numeric(12,4))
    last_price = Column(Numeric(12,4))
    mark_price = Column(Numeric(12,4))
    
    # Size data
    bid_size = Column(Integer)
    ask_size = Column(Integer)
    last_size = Column(Integer)
    
    # Daily OHLC
    high_price = Column(Numeric(12,4))
    low_price = Column(Numeric(12,4))
    open_price = Column(Numeric(12,4))
    close_price = Column(Numeric(12,4))
    
    # Volume and interest
    total_volume = Column(BigInteger)
    open_interest = Column(BigInteger)
    
    # Timestamps (stored as bigint from API)
    trade_date = Column(BigInteger)
    quote_time = Column(BigInteger)
    trade_time = Column(BigInteger)
    
    # Changes
    net_change = Column(Numeric(12,4))
    percent_change = Column(Numeric(8,4))
    mark_change = Column(Numeric(12,4))
    mark_percent_change = Column(Numeric(8,4))
    
    # Greeks
    volatility = Column(Numeric(8,4))
    delta = Column(Numeric(8,6))
    gamma = Column(Numeric(8,6))
    theta = Column(Numeric(8,6))
    vega = Column(Numeric(8,6))
    rho = Column(Numeric(8,6))
    
    # Option-specific metrics
    time_value = Column(Numeric(12,4))
    intrinsic_value = Column(Numeric(12,4))
    theoretical_option_value = Column(Numeric(12,4))
    theoretical_volatility = Column(Numeric(8,4))
    
    # Flags
    is_in_the_money = Column(Boolean)
    is_mini = Column(Boolean, default=False)
    is_non_standard = Column(Boolean, default=False)
    is_index_option = Column(Boolean, default=False)
    is_penny_pilot = Column(Boolean, default=False)
    
    # Contract specifications
    expiration_type = Column(String(1))  # M, W, Q
    last_trading_day = Column(BigInteger)
    multiplier = Column(Integer, default=100)
    settlement_type = Column(String(1))  # A, P
    deliverable_note = Column(Text)
    option_root = Column(String(10))
    
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    chain = relationship("OptionsChain", back_populates="contracts")
    deliverables = relationship("OptionDeliverable", back_populates="contract")
    
    __table_args__ = (
        Index('idx_contracts_chain_type_strike', 'chain_id', 'put_call', 'strike_price'),
        Index('idx_contracts_symbol_exp', 'option_symbol', 'expiration_date'),
        Index('idx_contracts_underlying_exp_strike', 'chain_id', 'expiration_date', 'strike_price'),
        Index('idx_contracts_volume', 'total_volume'),
        Index('idx_contracts_oi', 'open_interest'),
        CheckConstraint("put_call IN ('PUT', 'CALL')"),
        CheckConstraint("expiration_type IN ('M', 'W', 'Q')"),
        CheckConstraint("settlement_type IN ('A', 'P')"),
    )

class OptionDeliverable(Base):
    """Option contract deliverables"""
    __tablename__ = 'option_deliverables'
    
    deliverable_id = Column(BigInteger, primary_key=True)
    contract_id = Column(BigInteger, ForeignKey('options_contracts.contract_id', ondelete='CASCADE'))
    symbol = Column(String(20))
    asset_type = Column(String(20))
    deliverable_units = Column(String(50))
    currency_type = Column(String(10))
    
    # Relationships
    contract = relationship("OptionsContract", back_populates="deliverables")
    
    __table_args__ = (
        Index('idx_deliverables_contract', 'contract_id'),
    )

# ============================================================================
# ORDERS & EXECUTIONS TABLES
# ============================================================================

class Order(Base):
    """Master order records"""
    __tablename__ = 'orders'
    
    order_id = Column(BigInteger, primary_key=True)
    schwab_order_id = Column(BigInteger, unique=True, nullable=False)
    account_id = Column(BigInteger, ForeignKey('accounts.account_id'))
    
    # Order metadata
    session = Column(String(20))  # NORMAL, AM, PM, SEAMLESS
    duration = Column(String(20))  # DAY, GTC, IOC, FOK
    order_type = Column(String(20))  # MARKET, LIMIT, STOP, STOP_LIMIT
    order_strategy_type = Column(String(20))  # SINGLE, OCO, TRIGGER
    complex_order_strategy_type = Column(String(50))  # NONE, COVERED, BUTTERFLY
    
    # Quantities
    quantity = Column(Numeric(15,4))
    filled_quantity = Column(Numeric(15,4))
    remaining_quantity = Column(Numeric(15,4))
    
    # Pricing
    price = Column(Numeric(12,4))
    stop_price = Column(Numeric(12,4))
    activation_price = Column(Numeric(12,4))
    stop_price_offset = Column(Numeric(12,4))
    
    # Price linking
    price_link_basis = Column(String(20))  # MANUAL, BID, ASK, MARK
    price_link_type = Column(String(20))  # VALUE, PERCENT, TICK
    stop_price_link_basis = Column(String(20))
    stop_price_link_type = Column(String(20))
    
    # Order routing
    requested_destination = Column(String(20))
    destination_link_name = Column(String(50))
    
    # Special instructions
    special_instruction = Column(String(50))  # ALL_OR_NONE, DO_NOT_REDUCE
    tax_lot_method = Column(String(20))  # FIFO, LIFO, HIGH_COST
    stop_type = Column(String(20))  # STANDARD, BID, ASK, LAST, MARK
    
    # Status and timing
    status = Column(String(50))  # AWAITING_PARENT_ORDER, PENDING_ACTIVATION, FILLED
    status_description = Column(Text)
    entered_time = Column(DateTime(timezone=True))
    close_time = Column(DateTime(timezone=True))
    cancel_time = Column(DateTime(timezone=True))
    release_time = Column(DateTime(timezone=True))
    
    # Flags
    cancelable = Column(Boolean, default=False)
    editable = Column(Boolean, default=False)
    
    # Additional metadata
    tag = Column(String(100))
    
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    account = relationship("Account", back_populates="orders")
    legs = relationship("OrderLeg", back_populates="order")
    activities = relationship("OrderActivity", back_populates="order")
    
    __table_args__ = (
        Index('idx_orders_account_status', 'account_id', 'status'),
        Index('idx_orders_schwab_id', 'schwab_order_id'),
        Index('idx_orders_entered_time', 'entered_time'),
        Index('idx_orders_status', 'status'),
    )

class OrderLeg(Base):
    """Individual order legs"""
    __tablename__ = 'order_legs'
    
    leg_id = Column(BigInteger, primary_key=True)
    order_id = Column(BigInteger, ForeignKey('orders.order_id', ondelete='CASCADE'))
    schwab_leg_id = Column(Integer)
    
    # Leg details
    order_leg_type = Column(String(20))  # EQUITY, OPTION, INDEX
    instruction = Column(String(20))  # BUY, SELL, BUY_TO_OPEN, SELL_TO_CLOSE
    position_effect = Column(String(20))  # OPENING, CLOSING, AUTOMATIC
    
    # Quantities
    quantity = Column(Numeric(15,4))
    quantity_type = Column(String(20))  # ALL_SHARES, DOLLARS, SHARES
    
    # Instrument details (denormalized for performance)
    instrument_cusip = Column(String(20))
    instrument_symbol = Column(String(50))
    instrument_description = Column(Text)
    instrument_id = Column(BigInteger)
    instrument_type = Column(String(50))  # SWEEP_VEHICLE, EQUITY, OPTION
    instrument_net_change = Column(Numeric(12,4))
    
    # Options-specific
    to_symbol = Column(String(50))  # For option exercises/assignments
    
    # Dividend/capital gains
    div_cap_gains = Column(String(20))  # REINVEST, PAYOUT
    
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    order = relationship("Order", back_populates="legs")
    executions = relationship("ExecutionLeg", back_populates="leg")
    
    __table_args__ = (
        Index('idx_legs_order', 'order_id'),
        Index('idx_legs_symbol', 'instrument_symbol'),
        Index('idx_legs_instruction', 'instruction'),
    )

class OrderActivity(Base):
    """Order execution activities"""
    __tablename__ = 'order_activities'
    
    activity_id = Column(BigInteger, primary_key=True)
    order_id = Column(BigInteger, ForeignKey('orders.order_id', ondelete='CASCADE'))
    
    # Activity details
    activity_type = Column(String(20))  # EXECUTION, CANCEL, REPLACE
    execution_type = Column(String(20))  # FILL, PARTIAL_FILL
    
    # Quantities
    quantity = Column(Numeric(15,4))
    order_remaining_quantity = Column(Numeric(15,4))
    
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    order = relationship("Order", back_populates="activities")
    execution_legs = relationship("ExecutionLeg", back_populates="activity")
    
    __table_args__ = (
        Index('idx_activities_order', 'order_id'),
        Index('idx_activities_type', 'activity_type'),
    )

class ExecutionLeg(Base):
    """Individual leg executions"""
    __tablename__ = 'execution_legs'
    
    execution_id = Column(BigInteger, primary_key=True)
    activity_id = Column(BigInteger, ForeignKey('order_activities.activity_id', ondelete='CASCADE'))
    leg_id = Column(BigInteger, ForeignKey('order_legs.leg_id'))
    
    # Execution details
    price = Column(Numeric(12,4))
    quantity = Column(Numeric(15,4))
    mismarked_quantity = Column(Numeric(15,4))
    instrument_id = Column(BigInteger)
    execution_time = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    activity = relationship("OrderActivity", back_populates="execution_legs")
    leg = relationship("OrderLeg", back_populates="executions")
    
    __table_args__ = (
        Index('idx_executions_activity', 'activity_id'),
        Index('idx_executions_leg', 'leg_id'),
        Index('idx_executions_time', 'execution_time'),
    )

# ============================================================================
# TRANSACTIONS TABLES
# ============================================================================

class Transaction(Base):
    """Master transaction records"""
    __tablename__ = 'transactions'
    
    transaction_id = Column(BigInteger, primary_key=True)
    schwab_activity_id = Column(BigInteger, unique=True, nullable=False)
    account_id = Column(BigInteger, ForeignKey('accounts.account_id'))
    
    # Transaction metadata
    transaction_time = Column(DateTime(timezone=True), nullable=False)
    trade_date = Column(Date)
    settlement_date = Column(Date)
    description = Column(Text)
    
    # Transaction classification
    transaction_type = Column(String(50))  # TRADE, RECEIVE_AND_DELIVER, DIVIDEND
    activity_type = Column(String(50))  # ACTIVITY_CORRECTION
    status = Column(String(20))  # VALID, INVALID
    sub_account = Column(String(20))  # CASH, MARGIN, SHORT
    
    # Financial summary
    net_amount = Column(Numeric(15,4))
    
    # Related records
    position_id = Column(BigInteger)
    order_id = Column(BigInteger, ForeignKey('orders.order_id'))
    
    # User information (denormalized for performance)
    user_cd_domain_id = Column(String(50))
    user_login = Column(String(100))
    user_type = Column(String(20))  # ADVISOR_USER
    user_id = Column(BigInteger)
    user_system_name = Column(String(100))
    user_first_name = Column(String(100))
    user_last_name = Column(String(100))
    broker_rep_code = Column(String(20))
    
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    account = relationship("Account", back_populates="transactions")
    order = relationship("Order")
    items = relationship("TransactionItem", back_populates="transaction")
    
    __table_args__ = (
        Index('idx_transactions_account_time', 'account_id', 'transaction_time'),
        Index('idx_transactions_schwab_id', 'schwab_activity_id'),
        Index('idx_transactions_type_status', 'transaction_type', 'status'),
        Index('idx_transactions_trade_date', 'trade_date'),
        Index('idx_transactions_order_id', 'order_id'),
    )

class TransactionItem(Base):
    """Individual transfer items"""
    __tablename__ = 'transaction_items'
    
    item_id = Column(BigInteger, primary_key=True)
    transaction_id = Column(BigInteger, ForeignKey('transactions.transaction_id', ondelete='CASCADE'))
    
    # Item details
    amount = Column(Numeric(15,4))  # Quantity/shares
    cost = Column(Numeric(15,4))  # Total cost
    price = Column(Numeric(12,4))  # Price per share/unit
    position_effect = Column(String(20))  # OPENING, CLOSING, AUTOMATIC
    
    # Fee information
    fee_type = Column(String(20))  # COMMISSION, SEC_FEE, TAF_FEE
    
    # Instrument details (denormalized for performance)
    instrument_cusip = Column(String(20))
    instrument_symbol = Column(String(50))
    instrument_description = Column(Text)
    instrument_id = Column(BigInteger)
    instrument_type = Column(String(50))  # SWEEP_VEHICLE, EQUITY, OPTION
    instrument_net_change = Column(Numeric(12,4))
    
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    transaction = relationship("Transaction", back_populates="items")
    
    __table_args__ = (
        Index('idx_items_transaction', 'transaction_id'),
        Index('idx_items_symbol', 'instrument_symbol'),
        Index('idx_items_fee_type', 'fee_type'),
        Index('idx_items_position_effect', 'position_effect'),
    )

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def to_dict(self):
    """Convert model instance to dictionary"""
    return {c.name: getattr(self, c.name) for c in self.__table__.columns}

# Add to_dict method to all models
for cls in Base.registry._class_registry.values():
    if hasattr(cls, '__tablename__'):
        cls.to_dict = to_dict
