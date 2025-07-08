-- Crypto Analytics Dashboard - Redshift Table Creation Scripts
-- This script creates optimized tables for cryptocurrency market data analytics

-- Create schema
CREATE SCHEMA IF NOT EXISTS analytics;

-- Set search path
SET search_path TO analytics, public;

-- Create symbol mapping table
CREATE TABLE IF NOT EXISTS analytics.symbol_mapping (
    symbol_id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    base_currency VARCHAR(10) NOT NULL,
    quote_currency VARCHAR(10) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, exchange)
)
DISTSTYLE KEY
DISTKEY (symbol)
SORTKEY (exchange, symbol);

-- Create 5-minute OHLCV table (main table for real-time analytics)
CREATE TABLE IF NOT EXISTS analytics.ohlcv_5min (
    id BIGINT IDENTITY(1,1),
    symbol VARCHAR(20) NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    interval_start TIMESTAMP NOT NULL,
    interval_end TIMESTAMP NOT NULL,
    open DECIMAL(20,8) NOT NULL,
    high DECIMAL(20,8) NOT NULL,
    low DECIMAL(20,8) NOT NULL,
    close DECIMAL(20,8) NOT NULL,
    volume DECIMAL(20,8) NOT NULL,
    trade_count INTEGER,
    vwap DECIMAL(20,8),
    avg_spread DECIMAL(20,8),
    avg_spread_percentage DECIMAL(10,4),
    price_change DECIMAL(20,8),
    price_change_percentage DECIMAL(10,4),
    sma_5 DECIMAL(20,8),
    sma_10 DECIMAL(20,8),
    sma_20 DECIMAL(20,8),
    ema_12 DECIMAL(20,8),
    ema_26 DECIMAL(20,8),
    macd DECIMAL(20,8),
    macd_signal DECIMAL(20,8),
    macd_histogram DECIMAL(20,8),
    bb_middle DECIMAL(20,8),
    bb_upper DECIMAL(20,8),
    bb_lower DECIMAL(20,8),
    bb_std DECIMAL(20,8),
    rsi DECIMAL(10,4),
    volatility DECIMAL(20,8),
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    hour INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
DISTSTYLE KEY
DISTKEY (symbol)
COMPOUND SORTKEY (interval_start, symbol)
ENCODE ZSTD;

-- Create 1-minute OHLCV table
CREATE TABLE IF NOT EXISTS analytics.ohlcv_1min (
    id BIGINT IDENTITY(1,1),
    symbol VARCHAR(20) NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    interval_start TIMESTAMP NOT NULL,
    interval_end TIMESTAMP NOT NULL,
    open DECIMAL(20,8) NOT NULL,
    high DECIMAL(20,8) NOT NULL,
    low DECIMAL(20,8) NOT NULL,
    close DECIMAL(20,8) NOT NULL,
    volume DECIMAL(20,8) NOT NULL,
    trade_count INTEGER,
    vwap DECIMAL(20,8),
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    hour INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
DISTSTYLE KEY
DISTKEY (symbol)
COMPOUND SORTKEY (interval_start, symbol)
ENCODE ZSTD;

-- Create 15-minute OHLCV table
CREATE TABLE IF NOT EXISTS analytics.ohlcv_15min (
    id BIGINT IDENTITY(1,1),
    symbol VARCHAR(20) NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    interval_start TIMESTAMP NOT NULL,
    interval_end TIMESTAMP NOT NULL,
    open DECIMAL(20,8) NOT NULL,
    high DECIMAL(20,8) NOT NULL,
    low DECIMAL(20,8) NOT NULL,
    close DECIMAL(20,8) NOT NULL,
    volume DECIMAL(20,8) NOT NULL,
    trade_count INTEGER,
    vwap DECIMAL(20,8),
    price_change DECIMAL(20,8),
    price_change_percentage DECIMAL(10,4),
    sma_5 DECIMAL(20,8),
    sma_10 DECIMAL(20,8),
    sma_20 DECIMAL(20,8),
    rsi DECIMAL(10,4),
    volatility DECIMAL(20,8),
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    hour INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
DISTSTYLE KEY
DISTKEY (symbol)
COMPOUND SORTKEY (interval_start, symbol)
ENCODE ZSTD;

-- Create hourly OHLCV table
CREATE TABLE IF NOT EXISTS analytics.ohlcv_1h (
    id BIGINT IDENTITY(1,1),
    symbol VARCHAR(20) NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    interval_start TIMESTAMP NOT NULL,
    interval_end TIMESTAMP NOT NULL,
    open DECIMAL(20,8) NOT NULL,
    high DECIMAL(20,8) NOT NULL,
    low DECIMAL(20,8) NOT NULL,
    close DECIMAL(20,8) NOT NULL,
    volume DECIMAL(20,8) NOT NULL,
    trade_count INTEGER,
    vwap DECIMAL(20,8),
    price_change DECIMAL(20,8),
    price_change_percentage DECIMAL(10,4),
    sma_5 DECIMAL(20,8),
    sma_10 DECIMAL(20,8),
    sma_20 DECIMAL(20,8),
    ema_12 DECIMAL(20,8),
    ema_26 DECIMAL(20,8),
    macd DECIMAL(20,8),
    macd_signal DECIMAL(20,8),
    macd_histogram DECIMAL(20,8),
    bb_middle DECIMAL(20,8),
    bb_upper DECIMAL(20,8),
    bb_lower DECIMAL(20,8),
    bb_std DECIMAL(20,8),
    rsi DECIMAL(10,4),
    volatility DECIMAL(20,8),
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    hour INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
DISTSTYLE KEY
DISTKEY (symbol)
COMPOUND SORTKEY (interval_start, symbol)
ENCODE ZSTD;

-- Create 4-hour OHLCV table
CREATE TABLE IF NOT EXISTS analytics.ohlcv_4h (
    id BIGINT IDENTITY(1,1),
    symbol VARCHAR(20) NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    interval_start TIMESTAMP NOT NULL,
    interval_end TIMESTAMP NOT NULL,
    open DECIMAL(20,8) NOT NULL,
    high DECIMAL(20,8) NOT NULL,
    low DECIMAL(20,8) NOT NULL,
    close DECIMAL(20,8) NOT NULL,
    volume DECIMAL(20,8) NOT NULL,
    trade_count INTEGER,
    vwap DECIMAL(20,8),
    price_change DECIMAL(20,8),
    price_change_percentage DECIMAL(10,4),
    sma_5 DECIMAL(20,8),
    sma_10 DECIMAL(20,8),
    sma_20 DECIMAL(20,8),
    ema_12 DECIMAL(20,8),
    ema_26 DECIMAL(20,8),
    macd DECIMAL(20,8),
    macd_signal DECIMAL(20,8),
    macd_histogram DECIMAL(20,8),
    bb_middle DECIMAL(20,8),
    bb_upper DECIMAL(20,8),
    bb_lower DECIMAL(20,8),
    bb_std DECIMAL(20,8),
    rsi DECIMAL(10,4),
    volatility DECIMAL(20,8),
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    hour INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
DISTSTYLE KEY
DISTKEY (symbol)
COMPOUND SORTKEY (interval_start, symbol)
ENCODE ZSTD;

-- Create daily OHLCV table
CREATE TABLE IF NOT EXISTS analytics.ohlcv_daily (
    id BIGINT IDENTITY(1,1),
    symbol VARCHAR(20) NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    interval_start TIMESTAMP NOT NULL,
    interval_end TIMESTAMP NOT NULL,
    open DECIMAL(20,8) NOT NULL,
    high DECIMAL(20,8) NOT NULL,
    low DECIMAL(20,8) NOT NULL,
    close DECIMAL(20,8) NOT NULL,
    volume DECIMAL(20,8) NOT NULL,
    trade_count INTEGER,
    vwap DECIMAL(20,8),
    price_change DECIMAL(20,8),
    price_change_percentage DECIMAL(10,4),
    sma_5 DECIMAL(20,8),
    sma_10 DECIMAL(20,8),
    sma_20 DECIMAL(20,8),
    ema_12 DECIMAL(20,8),
    ema_26 DECIMAL(20,8),
    macd DECIMAL(20,8),
    macd_signal DECIMAL(20,8),
    macd_histogram DECIMAL(20,8),
    bb_middle DECIMAL(20,8),
    bb_upper DECIMAL(20,8),
    bb_lower DECIMAL(20,8),
    bb_std DECIMAL(20,8),
    rsi DECIMAL(10,4),
    volatility DECIMAL(20,8),
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
DISTSTYLE KEY
DISTKEY (symbol)
COMPOUND SORTKEY (interval_start, symbol)
ENCODE ZSTD;

-- Create data quality metrics table
CREATE TABLE IF NOT EXISTS analytics.data_quality_metrics (
    id BIGINT IDENTITY(1,1),
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    total_records INTEGER NOT NULL,
    valid_records INTEGER NOT NULL,
    invalid_records INTEGER NOT NULL,
    quality_score DECIMAL(5,4) NOT NULL,
    avg_price DECIMAL(20,8),
    avg_volume DECIMAL(20,8),
    min_price DECIMAL(20,8),
    max_price DECIMAL(20,8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
DISTSTYLE KEY
DISTKEY (symbol)
COMPOUND SORTKEY (date, exchange)
ENCODE ZSTD;

-- Create daily statistics table
CREATE TABLE IF NOT EXISTS analytics.daily_stats (
    id BIGINT IDENTITY(1,1),
    symbol VARCHAR(20) NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    open_price DECIMAL(20,8) NOT NULL,
    close_price DECIMAL(20,8) NOT NULL,
    high_price DECIMAL(20,8) NOT NULL,
    low_price DECIMAL(20,8) NOT NULL,
    total_volume DECIMAL(20,8) NOT NULL,
    total_trades INTEGER NOT NULL,
    price_change DECIMAL(20,8) NOT NULL,
    price_change_percentage DECIMAL(10,4) NOT NULL,
    avg_spread DECIMAL(20,8),
    avg_spread_percentage DECIMAL(10,4),
    volatility DECIMAL(20,8),
    rsi_avg DECIMAL(10,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
DISTSTYLE KEY
DISTKEY (symbol)
COMPOUND SORTKEY (date, symbol)
ENCODE ZSTD;

-- Create exchange performance table
CREATE TABLE IF NOT EXISTS analytics.exchange_performance (
    id BIGINT IDENTITY(1,1),
    exchange VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    total_volume DECIMAL(20,8) NOT NULL,
    total_trades INTEGER NOT NULL,
    avg_spread DECIMAL(20,8),
    avg_spread_percentage DECIMAL(10,4),
    data_quality_score DECIMAL(5,4) NOT NULL,
    uptime_percentage DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
DISTSTYLE KEY
DISTKEY (exchange)
COMPOUND SORTKEY (date, exchange)
ENCODE ZSTD;

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_ohlcv_5min_symbol_time 
ON analytics.ohlcv_5min (symbol, interval_start);

CREATE INDEX IF NOT EXISTS idx_ohlcv_5min_exchange_time 
ON analytics.ohlcv_5min (exchange, interval_start);

CREATE INDEX IF NOT EXISTS idx_ohlcv_daily_symbol_date 
ON analytics.ohlcv_daily (symbol, date);

CREATE INDEX IF NOT EXISTS idx_data_quality_date 
ON analytics.data_quality_metrics (date);

CREATE INDEX IF NOT EXISTS idx_daily_stats_date 
ON analytics.daily_stats (date);

-- Insert initial symbol mappings
INSERT INTO analytics.symbol_mapping (symbol, exchange, base_currency, quote_currency) VALUES
('btcusdt', 'binance', 'BTC', 'USDT'),
('ethusdt', 'binance', 'ETH', 'USDT'),
('bnbusdt', 'binance', 'BNB', 'USDT'),
('adausdt', 'binance', 'ADA', 'USDT'),
('btc-USD', 'coinbase', 'BTC', 'USD'),
('eth-USD', 'coinbase', 'ETH', 'USD'),
('ltc-USD', 'coinbase', 'LTC', 'USD'),
('bch-USD', 'coinbase', 'BCH', 'USD')
ON CONFLICT (symbol, exchange) DO NOTHING;

-- Create comments for documentation
COMMENT ON TABLE analytics.ohlcv_5min IS '5-minute OHLCV candlestick data with technical indicators';
COMMENT ON TABLE analytics.ohlcv_daily IS 'Daily OHLCV candlestick data with technical indicators';
COMMENT ON TABLE analytics.data_quality_metrics IS 'Data quality metrics by exchange and symbol';
COMMENT ON TABLE analytics.daily_stats IS 'Daily aggregated statistics by symbol';
COMMENT ON TABLE analytics.exchange_performance IS 'Exchange performance metrics';

-- Grant permissions (adjust as needed for your setup)
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA analytics TO crypto_analytics_user;
GRANT USAGE ON SCHEMA analytics TO crypto_analytics_user; 