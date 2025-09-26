# Database Architecture Documentation

## Overview

This document provides comprehensive documentation of the enhanced database architecture for the Charles Schwab API Integration system. The database is designed to efficiently store and query trading data, options chains, orders, transactions, and market data with optimal performance for real-time trading applications.

## Database Technology Stack

- **Database Engine**: PostgreSQL 13+
- **ORM**: SQLAlchemy 2.0+
- **Migration Management**: Alembic
- **Connection Pooling**: SQLAlchemy connection pooling
- **Timezone Handling**: UTC with timezone awareness

## Architecture Principles

### 1. **Normalized Design**
- Third Normal Form (3NF) compliance
- Elimination of data redundancy
- Referential integrity through foreign keys
- Optimized for data consistency

### 2. **Performance Optimization**
- Strategic indexing for query performance
- Composite indexes for complex queries
- Partitioning-ready structure for time-series data
- Denormalization where appropriate for read performance

### 3. **Scalability**
- BigInteger primary keys for high-volume data
- Time-based partitioning support
- Efficient bulk insert capabilities
- Read replica support ready

### 4. **Data Integrity**
- Comprehensive constraints and validations
- Cascade delete relationships
- Audit trails with timestamps
- Data quality flags

## Database Schema

### Core Tables (4 tables)

#### 1. `accounts` - Account Management
Stores secure account information with hash-based identification.

```sql
CREATE TABLE accounts (
    account_id BIGINT PRIMARY KEY,
    account_hash VARCHAR(50) UNIQUE NOT NULL,
    account_number VARCHAR(50) UNIQUE,
    display_name VARCHAR(100),
    nickname VARCHAR(100),
    account_type VARCHAR(20),  -- CASH, MARGIN, etc.
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Key Features:**
- Hash-based account identification for security
- Support for multiple account types
- Soft delete capability with `is_active` flag

**Indexes:**
- `idx_accounts_hash` - Fast hash lookups
- `idx_accounts_type` - Account type filtering

#### 2. `symbols` - Security Master Data
Central repository for all tradeable symbols.

```sql
CREATE TABLE symbols (
    symbol_id BIGINT PRIMARY KEY,
    symbol VARCHAR(10) UNIQUE NOT NULL,
    company_name VARCHAR(200),
    description TEXT,
    asset_type VARCHAR(20),  -- EQUITY, OPTION, INDEX, etc.
    exchange VARCHAR(10),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Key Features:**
- Centralized symbol management
- Asset type classification
- Exchange information tracking

**Indexes:**
- `idx_symbols_symbol` - Primary symbol lookups
- `idx_symbols_type` - Asset type filtering

#### 3. `price_data` - Time-Series Price Data
High-performance storage for OHLCV data with partitioning support.

```sql
CREATE TABLE price_data (
    price_id BIGINT PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    datetime_ms BIGINT NOT NULL,  -- Original millisecond timestamp
    datetime_utc TIMESTAMP WITH TIME ZONE NOT NULL,  -- Converted timestamp
    open_price NUMERIC(12,4) NOT NULL,
    high_price NUMERIC(12,4) NOT NULL,
    low_price NUMERIC(12,4) NOT NULL,
    close_price NUMERIC(12,4) NOT NULL,
    volume BIGINT NOT NULL,
    previous_close NUMERIC(12,4),
    previous_close_date_ms BIGINT,
    is_empty BOOLEAN DEFAULT FALSE,
    data_source VARCHAR(20) DEFAULT 'schwab_api',
    frequency_type VARCHAR(10),  -- 'minute', 'daily', 'weekly'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(symbol, datetime_ms, frequency_type)
);
```

**Key Features:**
- Dual timestamp storage (milliseconds + UTC)
- Multiple frequency support
- Data quality flags
- Previous close context

**Indexes:**
- `idx_price_symbol_datetime` - Primary query pattern
- `idx_price_datetime` - Time-based queries
- `idx_price_volume` - Volume analysis

#### 4. `options_expirations` - Options Expiration Calendar
Manages options expiration cycles and DTE calculations.

```sql
CREATE TABLE options_expirations (
    expiration_id BIGINT PRIMARY KEY,
    underlying_symbol VARCHAR(10) NOT NULL,
    expiration_date DATE NOT NULL,
    days_to_expiration INTEGER,
    expiration_type VARCHAR(1) NOT NULL,  -- W, S, Q, M
    is_standard BOOLEAN DEFAULT TRUE,
    is_leap BOOLEAN DEFAULT FALSE,  -- For LEAPS (>1 year)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(underlying_symbol, expiration_date),
    CHECK (expiration_type IN ('W', 'S', 'Q', 'M'))
);
```

**Key Features:**
- Expiration type classification (Weekly, Standard, Quarterly, Monthly)
- LEAPS identification
- Days to expiration tracking

**Indexes:**
- `idx_exp_symbol_date` - Symbol-date lookups
- `idx_exp_type_dte` - Type and DTE filtering

### Options Trading Tables (3 tables)

#### 5. `options_chains` - Options Chain Snapshots
Stores point-in-time options chain data with market context.

```sql
CREATE TABLE options_chains (
    chain_id BIGINT PRIMARY KEY,
    underlying_symbol VARCHAR(10) NOT NULL,
    expiration_id BIGINT REFERENCES options_expirations(expiration_id),
    snapshot_datetime TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(20),
    strategy VARCHAR(20) DEFAULT 'SINGLE',
    underlying_price NUMERIC(12,4),
    underlying_bid NUMERIC(12,4),
    underlying_ask NUMERIC(12,4),
    underlying_last NUMERIC(12,4),
    underlying_volume BIGINT,
    underlying_change NUMERIC(12,4),
    underlying_percent_change NUMERIC(8,4),
    interest_rate NUMERIC(8,6),
    implied_volatility NUMERIC(8,4),
    is_delayed BOOLEAN DEFAULT FALSE,
    is_index BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(underlying_symbol, expiration_id, snapshot_datetime)
);
```

**Key Features:**
- Point-in-time chain snapshots
- Underlying market data context
- Market environment indicators

**Indexes:**
- `idx_chains_symbol_snapshot` - Time-series queries
- `idx_chains_expiration` - Expiration-based filtering

#### 6. `options_contracts` - Individual Option Contracts
Comprehensive storage for individual option contract data including Greeks.

```sql
CREATE TABLE options_contracts (
    contract_id BIGINT PRIMARY KEY,
    chain_id BIGINT REFERENCES options_chains(chain_id) ON DELETE CASCADE,
    option_symbol VARCHAR(50) NOT NULL,
    put_call VARCHAR(4) NOT NULL,  -- PUT, CALL
    strike_price NUMERIC(12,4) NOT NULL,
    expiration_date DATE NOT NULL,
    days_to_expiration INTEGER,
    -- Pricing data
    bid_price NUMERIC(12,4),
    ask_price NUMERIC(12,4),
    last_price NUMERIC(12,4),
    mark_price NUMERIC(12,4),
    -- Size data
    bid_size INTEGER,
    ask_size INTEGER,
    last_size INTEGER,
    -- Daily OHLC
    high_price NUMERIC(12,4),
    low_price NUMERIC(12,4),
    open_price NUMERIC(12,4),
    close_price NUMERIC(12,4),
    -- Volume and interest
    total_volume BIGINT,
    open_interest BIGINT,
    -- Greeks
    volatility NUMERIC(8,4),
    delta NUMERIC(8,6),
    gamma NUMERIC(8,6),
    theta NUMERIC(8,6),
    vega NUMERIC(8,6),
    rho NUMERIC(8,6),
    -- Option-specific metrics
    time_value NUMERIC(12,4),
    intrinsic_value NUMERIC(12,4),
    theoretical_option_value NUMERIC(12,4),
    theoretical_volatility NUMERIC(8,4),
    -- Flags
    is_in_the_money BOOLEAN,
    is_mini BOOLEAN DEFAULT FALSE,
    is_non_standard BOOLEAN DEFAULT FALSE,
    is_index_option BOOLEAN DEFAULT FALSE,
    is_penny_pilot BOOLEAN DEFAULT FALSE,
    -- Contract specifications
    expiration_type VARCHAR(1),  -- M, W, Q
    multiplier INTEGER DEFAULT 100,
    settlement_type VARCHAR(1),  -- A, P
    deliverable_note TEXT,
    option_root VARCHAR(10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CHECK (put_call IN ('PUT', 'CALL')),
    CHECK (expiration_type IN ('M', 'W', 'Q')),
    CHECK (settlement_type IN ('A', 'P'))
);
```

**Key Features:**
- Complete options pricing data
- Full Greeks calculation support
- Contract specification details
- Volume and open interest tracking

**Indexes:**
- `idx_contracts_chain_type_strike` - Chain filtering with strike
- `idx_contracts_symbol_exp` - Symbol-expiration lookups
- `idx_contracts_underlying_exp_strike` - Complex queries
- `idx_contracts_volume` - Volume analysis
- `idx_contracts_oi` - Open interest analysis

#### 7. `option_deliverables` - Contract Deliverables
Stores deliverable specifications for option contracts.

```sql
CREATE TABLE option_deliverables (
    deliverable_id BIGINT PRIMARY KEY,
    contract_id BIGINT REFERENCES options_contracts(contract_id) ON DELETE CASCADE,
    symbol VARCHAR(20),
    asset_type VARCHAR(20),
    deliverable_units VARCHAR(50),
    currency_type VARCHAR(10)
);
```

**Indexes:**
- `idx_deliverables_contract` - Contract-based lookups

### Order Management Tables (4 tables)

#### 8. `orders` - Master Order Records
Comprehensive order tracking with full lifecycle support.

```sql
CREATE TABLE orders (
    order_id BIGINT PRIMARY KEY,
    schwab_order_id BIGINT UNIQUE NOT NULL,
    account_id BIGINT REFERENCES accounts(account_id),
    session VARCHAR(20),  -- NORMAL, AM, PM, SEAMLESS
    duration VARCHAR(20),  -- DAY, GTC, IOC, FOK
    order_type VARCHAR(20),  -- MARKET, LIMIT, STOP, STOP_LIMIT
    order_strategy_type VARCHAR(20),  -- SINGLE, OCO, TRIGGER
    complex_order_strategy_type VARCHAR(50),  -- NONE, COVERED, BUTTERFLY
    quantity NUMERIC(15,4),
    filled_quantity NUMERIC(15,4),
    remaining_quantity NUMERIC(15,4),
    price NUMERIC(12,4),
    stop_price NUMERIC(12,4),
    -- Status and timing
    status VARCHAR(50),
    status_description TEXT,
    entered_time TIMESTAMP WITH TIME ZONE,
    close_time TIMESTAMP WITH TIME ZONE,
    cancel_time TIMESTAMP WITH TIME ZONE,
    release_time TIMESTAMP WITH TIME ZONE,
    -- Flags
    cancelable BOOLEAN DEFAULT FALSE,
    editable BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Key Features:**
- Complete order lifecycle tracking
- Complex order strategy support
- Price linking capabilities
- Status management

**Indexes:**
- `idx_orders_account_status` - Account-status queries
- `idx_orders_schwab_id` - Schwab ID lookups
- `idx_orders_entered_time` - Time-based queries
- `idx_orders_status` - Status filtering

#### 9. `order_legs` - Multi-Leg Order Components
Supports complex multi-leg orders with detailed instrument information.

```sql
CREATE TABLE order_legs (
    leg_id BIGINT PRIMARY KEY,
    order_id BIGINT REFERENCES orders(order_id) ON DELETE CASCADE,
    schwab_leg_id INTEGER,
    order_leg_type VARCHAR(20),  -- EQUITY, OPTION, INDEX
    instruction VARCHAR(20),  -- BUY, SELL, BUY_TO_OPEN, SELL_TO_CLOSE
    position_effect VARCHAR(20),  -- OPENING, CLOSING, AUTOMATIC
    quantity NUMERIC(15,4),
    quantity_type VARCHAR(20),  -- ALL_SHARES, DOLLARS, SHARES
    -- Instrument details (denormalized for performance)
    instrument_cusip VARCHAR(20),
    instrument_symbol VARCHAR(50),
    instrument_description TEXT,
    instrument_id BIGINT,
    instrument_type VARCHAR(50),
    instrument_net_change NUMERIC(12,4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Indexes:**
- `idx_legs_order` - Order-based queries
- `idx_legs_symbol` - Symbol filtering
- `idx_legs_instruction` - Instruction filtering

#### 10. `order_activities` - Order Execution Activities
Tracks order lifecycle events and executions.

```sql
CREATE TABLE order_activities (
    activity_id BIGINT PRIMARY KEY,
    order_id BIGINT REFERENCES orders(order_id) ON DELETE CASCADE,
    activity_type VARCHAR(20),  -- EXECUTION, CANCEL, REPLACE
    execution_type VARCHAR(20),  -- FILL, PARTIAL_FILL
    quantity NUMERIC(15,4),
    order_remaining_quantity NUMERIC(15,4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Indexes:**
- `idx_activities_order` - Order-based queries
- `idx_activities_type` - Activity type filtering

#### 11. `execution_legs` - Individual Leg Executions
Detailed execution information for each order leg.

```sql
CREATE TABLE execution_legs (
    execution_id BIGINT PRIMARY KEY,
    activity_id BIGINT REFERENCES order_activities(activity_id) ON DELETE CASCADE,
    leg_id BIGINT REFERENCES order_legs(leg_id),
    price NUMERIC(12,4),
    quantity NUMERIC(15,4),
    mismarked_quantity NUMERIC(15,4),
    instrument_id BIGINT,
    execution_time TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Indexes:**
- `idx_executions_activity` - Activity-based queries
- `idx_executions_leg` - Leg-based queries
- `idx_executions_time` - Time-based queries

### Transaction Processing Tables (2 tables)

#### 12. `transactions` - Master Transaction Records
Comprehensive transaction tracking with user context.

```sql
CREATE TABLE transactions (
    transaction_id BIGINT PRIMARY KEY,
    schwab_activity_id BIGINT UNIQUE NOT NULL,
    account_id BIGINT REFERENCES accounts(account_id),
    transaction_time TIMESTAMP WITH TIME ZONE NOT NULL,
    trade_date DATE,
    settlement_date DATE,
    description TEXT,
    transaction_type VARCHAR(50),  -- TRADE, RECEIVE_AND_DELIVER, DIVIDEND
    activity_type VARCHAR(50),  -- ACTIVITY_CORRECTION
    status VARCHAR(20),  -- VALID, INVALID
    sub_account VARCHAR(20),  -- CASH, MARGIN, SHORT
    net_amount NUMERIC(15,4),
    position_id BIGINT,
    order_id BIGINT REFERENCES orders(order_id),
    -- User information (denormalized for performance)
    user_cd_domain_id VARCHAR(50),
    user_login VARCHAR(100),
    user_type VARCHAR(20),  -- ADVISOR_USER
    user_id BIGINT,
    user_system_name VARCHAR(100),
    user_first_name VARCHAR(100),
    user_last_name VARCHAR(100),
    broker_rep_code VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Key Features:**
- Complete transaction lifecycle
- User context preservation
- Settlement tracking
- Order linkage

**Indexes:**
- `idx_transactions_account_time` - Account-time queries
- `idx_transactions_schwab_id` - Schwab ID lookups
- `idx_transactions_type_status` - Type-status filtering
- `idx_transactions_trade_date` - Trade date queries
- `idx_transactions_order_id` - Order linkage

#### 13. `transaction_items` - Transaction Line Items
Detailed breakdown of transaction components including fees.

```sql
CREATE TABLE transaction_items (
    item_id BIGINT PRIMARY KEY,
    transaction_id BIGINT REFERENCES transactions(transaction_id) ON DELETE CASCADE,
    amount NUMERIC(15,4),  -- Quantity/shares
    cost NUMERIC(15,4),  -- Total cost
    price NUMERIC(12,4),  -- Price per share/unit
    position_effect VARCHAR(20),  -- OPENING, CLOSING, AUTOMATIC
    fee_type VARCHAR(20),  -- COMMISSION, SEC_FEE, TAF_FEE
    -- Instrument details (denormalized for performance)
    instrument_cusip VARCHAR(20),
    instrument_symbol VARCHAR(50),
    instrument_description TEXT,
    instrument_id BIGINT,
    instrument_type VARCHAR(50),
    instrument_net_change NUMERIC(12,4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Indexes:**
- `idx_items_transaction` - Transaction-based queries
- `idx_items_symbol` - Symbol filtering
- `idx_items_fee_type` - Fee analysis
- `idx_items_position_effect` - Position effect filtering

## Database Relationships

### Entity Relationship Diagram

```
accounts (1) ←→ (M) orders ←→ (M) order_legs ←→ (M) execution_legs
    ↓                ↓              ↓
    └─→ transactions ←┘              └─→ order_activities
            ↓
        transaction_items

options_expirations (1) ←→ (M) options_chains (1) ←→ (M) options_contracts (1) ←→ (M) option_deliverables

symbols (1) ←→ (M) price_data
```

### Key Relationships

1. **Account → Orders → Transactions**: Complete trading lifecycle
2. **Options Chain → Contracts**: Hierarchical options data
3. **Orders → Legs → Executions**: Multi-leg order support
4. **Transactions → Items**: Detailed transaction breakdown

## Performance Optimization

### Indexing Strategy

#### Primary Indexes (25+ indexes)
- **Unique Constraints**: Prevent data duplication
- **Foreign Key Indexes**: Optimize join performance
- **Composite Indexes**: Support complex query patterns
- **Time-based Indexes**: Optimize temporal queries

#### Query Optimization Patterns

1. **Symbol + DateTime**: Most common query pattern
2. **Account + Status**: Order and transaction filtering
3. **Chain + Strike + Type**: Options analysis
4. **Volume/OI Analysis**: Market data queries

### Partitioning Strategy

#### Time-based Partitioning (Ready for Implementation)
- `price_data`: Monthly partitions by `datetime_utc`
- `options_chains`: Weekly partitions by `snapshot_datetime`
- `transactions`: Monthly partitions by `transaction_time`

#### Benefits
- Improved query performance
- Efficient data archival
- Parallel processing support

## Data Migration & Management

### Alembic Configuration

```python
# alembic.ini configuration
[alembic]
script_location = migrations
sqlalchemy.url = postgresql://schwab_user:secure_password@localhost:5432/schwab_trading

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic
```

### Migration Commands

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history
```

### Current Migration Status
- **Current Revision**: `4b6b797adaeb`
- **Migration File**: `20250925_2108_4b6b797adaeb_create_enhanced_trading_database_schema.py`
- **Status**: Applied successfully
- **Tables Created**: 14 tables with 25+ indexes

## Data Types & Precision

### Numeric Precision Standards
- **Prices**: `NUMERIC(12,4)` - Up to $99,999,999.9999
- **Quantities**: `NUMERIC(15,4)` - Up to 99,999,999,999.9999 shares
- **Greeks**: `NUMERIC(8,6)` - High precision for derivatives
- **Percentages**: `NUMERIC(8,4)` - Up to 9999.9999%
- **Interest Rates**: `NUMERIC(8,6)` - High precision rates

### String Length Standards
- **Symbols**: `VARCHAR(10)` - Standard symbol length
- **Option Symbols**: `VARCHAR(50)` - Extended option notation
- **Descriptions**: `TEXT` - Unlimited length
- **Status Fields**: `VARCHAR(20-50)` - Controlled vocabulary

### Timestamp Handling
- **Storage**: `TIMESTAMP WITH TIME ZONE` (UTC)
- **API Timestamps**: Stored as `BIGINT` (milliseconds) + converted `TIMESTAMP`
- **Audit Fields**: Automatic `created_at`/`updated_at`

## Security Considerations

### Data Protection
- **Account Hashing**: Secure account identification
- **No Sensitive Data**: No SSNs, passwords, or PII
- **Audit Trails**: Complete change tracking
- **Access Control**: Database-level permissions

### Connection Security
- **SSL/TLS**: Encrypted connections required
- **Connection Pooling**: Secure connection management
- **Environment Variables**: Credential management

## Usage Examples

### Common Query Patterns

#### 1. Get Latest Options Chain
```sql
SELECT oc.*, oe.expiration_date, oe.days_to_expiration
FROM options_chains oc
JOIN options_expirations oe ON oc.expiration_id = oe.expiration_id
WHERE oc.underlying_symbol = 'AAPL'
  AND oc.snapshot_datetime = (
    SELECT MAX(snapshot_datetime) 
    FROM options_chains 
    WHERE underlying_symbol = 'AAPL'
  );
```

#### 2. Get Account Order History
```sql
SELECT o.*, ol.instruction, ol.instrument_symbol, ol.quantity
FROM orders o
JOIN order_legs ol ON o.order_id = ol.order_id
JOIN accounts a ON o.account_id = a.account_id
WHERE a.account_hash = 'user_account_hash'
  AND o.entered_time >= NOW() - INTERVAL '30 days'
ORDER BY o.entered_time DESC;
```

#### 3. Options Volume Analysis
```sql
SELECT 
    underlying_symbol,
    put_call,
    SUM(total_volume) as total_volume,
    AVG(implied_volatility) as avg_iv
FROM options_contracts oc
JOIN options_chains och ON oc.chain_id = och.chain_id
WHERE och.snapshot_datetime >= CURRENT_DATE
  AND oc.total_volume > 0
GROUP BY underlying_symbol, put_call
ORDER BY total_volume DESC;
```

#### 4. Price Data Time Series
```sql
SELECT 
    symbol,
    datetime_utc,
    close_price,
    volume,
    LAG(close_price) OVER (PARTITION BY symbol ORDER BY datetime_utc) as prev_close
FROM price_data
WHERE symbol = 'SPY'
  AND datetime_utc >= NOW() - INTERVAL '1 day'
  AND frequency_type = 'minute'
ORDER BY datetime_utc;
```

## Monitoring & Maintenance

### Performance Monitoring
- **Query Performance**: Monitor slow queries
- **Index Usage**: Track index effectiveness
- **Connection Pooling**: Monitor connection health
- **Disk Usage**: Track table growth

### Maintenance Tasks
- **VACUUM/ANALYZE**: Regular table maintenance
- **Index Rebuilding**: Periodic index optimization
- **Partition Management**: Automated partition creation/cleanup
- **Backup Strategy**: Regular database backups

### Health Checks
```sql
-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

## Future Enhancements

### Planned Improvements
1. **Time-series Optimization**: Implement TimescaleDB extension
2. **Real-time Streaming**: Add change data capture (CDC)
3. **Analytics Views**: Materialized views for common queries
4. **Data Archival**: Automated historical data management
5. **Replication**: Read replica setup for analytics

### Scalability Roadmap
1. **Horizontal Partitioning**: Distribute by account/symbol
2. **Caching Layer**: Redis integration for hot data
3. **Connection Pooling**: PgBouncer implementation
4. **Monitoring**: Comprehensive observability stack

## Troubleshooting

### Common Issues

#### Migration Failures
```bash
# Check current state
alembic current

# Show pending migrations
alembic show

# Manual migration repair
alembic stamp head
```

#### Performance Issues
```sql
-- Find slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- Check for missing indexes
SELECT * FROM pg_stat_user_tables 
WHERE seq_scan > 1000 AND seq_tup_read/seq_scan > 10000;
```

#### Connection Issues
- Check PostgreSQL service status
- Verify connection parameters
- Monitor connection pool usage
- Review firewall settings

## Conclusion

This database architecture provides a robust, scalable foundation for the Charles Schwab API Integration system. The design emphasizes:

- **Performance**: Strategic indexing and query optimization
- **Scalability**: Partitioning-ready structure
- **Data Integrity**: Comprehensive constraints and relationships
- **Maintainability**: Clear documentation and migration management
- **Security**: Secure data handling and access control

The architecture supports real-time trading operations while maintaining data consistency and providing comprehensive audit trails for regulatory compliance.
