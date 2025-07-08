-- Crypto Analytics Dashboard - Redshift Views
-- This script creates optimized views for common analytics queries

-- Set search path
SET search_path TO analytics, public;

-- View for latest market data (last 24 hours)
CREATE OR REPLACE VIEW analytics.v_latest_market_data AS
SELECT 
    symbol,
    exchange,
    interval_start,
    interval_end,
    open,
    high,
    low,
    close,
    volume,
    trade_count,
    vwap,
    price_change,
    price_change_percentage,
    sma_5,
    sma_10,
    sma_20,
    rsi,
    volatility
FROM analytics.ohlcv_5min
WHERE interval_start >= CURRENT_DATE - INTERVAL '1 day'
ORDER BY symbol, interval_start DESC;

-- View for daily market summary
CREATE OR REPLACE VIEW analytics.v_daily_market_summary AS
SELECT 
    symbol,
    exchange,
    DATE(interval_start) as date,
    FIRST_VALUE(open) OVER (PARTITION BY symbol, exchange, DATE(interval_start) ORDER BY interval_start) as open_price,
    LAST_VALUE(close) OVER (PARTITION BY symbol, exchange, DATE(interval_start) ORDER BY interval_start ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as close_price,
    MAX(high) as high_price,
    MIN(low) as low_price,
    SUM(volume) as total_volume,
    SUM(trade_count) as total_trades,
    AVG(vwap) as avg_vwap,
    AVG(price_change_percentage) as avg_price_change_percentage,
    AVG(rsi) as avg_rsi,
    AVG(volatility) as avg_volatility
FROM analytics.ohlcv_5min
WHERE interval_start >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY symbol, exchange, DATE(interval_start);

-- View for exchange performance comparison
CREATE OR REPLACE VIEW analytics.v_exchange_performance AS
SELECT 
    exchange,
    DATE(interval_start) as date,
    COUNT(DISTINCT symbol) as symbols_traded,
    SUM(volume) as total_volume,
    SUM(trade_count) as total_trades,
    AVG(price_change_percentage) as avg_price_change,
    AVG(rsi) as avg_rsi,
    AVG(volatility) as avg_volatility,
    AVG(avg_spread_percentage) as avg_spread_percentage
FROM analytics.ohlcv_5min
WHERE interval_start >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY exchange, DATE(interval_start)
ORDER BY exchange, date DESC;

-- View for top performing symbols
CREATE OR REPLACE VIEW analytics.v_top_performing_symbols AS
SELECT 
    symbol,
    exchange,
    DATE(interval_start) as date,
    price_change_percentage,
    volume,
    rsi,
    volatility
FROM analytics.ohlcv_5min
WHERE interval_start >= CURRENT_DATE - INTERVAL '1 day'
    AND price_change_percentage IS NOT NULL
ORDER BY price_change_percentage DESC;

-- View for technical indicators summary
CREATE OR REPLACE VIEW analytics.v_technical_indicators AS
SELECT 
    symbol,
    exchange,
    interval_start,
    close,
    sma_5,
    sma_10,
    sma_20,
    ema_12,
    ema_26,
    macd,
    macd_signal,
    macd_histogram,
    bb_middle,
    bb_upper,
    bb_lower,
    rsi,
    volatility,
    CASE 
        WHEN close > sma_20 THEN 'BULLISH'
        WHEN close < sma_20 THEN 'BEARISH'
        ELSE 'NEUTRAL'
    END as trend_signal,
    CASE 
        WHEN rsi > 70 THEN 'OVERBOUGHT'
        WHEN rsi < 30 THEN 'OVERSOLD'
        ELSE 'NEUTRAL'
    END as rsi_signal
FROM analytics.ohlcv_5min
WHERE interval_start >= CURRENT_DATE - INTERVAL '7 days'
    AND sma_20 IS NOT NULL
    AND rsi IS NOT NULL;

-- View for data quality summary
CREATE OR REPLACE VIEW analytics.v_data_quality_summary AS
SELECT 
    exchange,
    symbol,
    date,
    total_records,
    valid_records,
    invalid_records,
    quality_score,
    ROUND((valid_records::DECIMAL / total_records) * 100, 2) as success_rate,
    avg_price,
    avg_volume,
    min_price,
    max_price
FROM analytics.data_quality_metrics
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY date DESC, quality_score DESC;

-- View for volume analysis
CREATE OR REPLACE VIEW analytics.v_volume_analysis AS
SELECT 
    symbol,
    exchange,
    DATE(interval_start) as date,
    HOUR(interval_start) as hour,
    SUM(volume) as hourly_volume,
    COUNT(*) as candle_count,
    AVG(volume) as avg_volume_per_candle,
    MAX(volume) as max_volume,
    MIN(volume) as min_volume
FROM analytics.ohlcv_5min
WHERE interval_start >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY symbol, exchange, DATE(interval_start), HOUR(interval_start)
ORDER BY symbol, date DESC, hour;

-- View for price volatility analysis
CREATE OR REPLACE VIEW analytics.v_volatility_analysis AS
SELECT 
    symbol,
    exchange,
    DATE(interval_start) as date,
    AVG(volatility) as avg_volatility,
    MAX(volatility) as max_volatility,
    MIN(volatility) as min_volatility,
    STDDEV(close) as price_stddev,
    (MAX(high) - MIN(low)) / AVG(close) * 100 as daily_range_percentage
FROM analytics.ohlcv_5min
WHERE interval_start >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY symbol, exchange, DATE(interval_start)
ORDER BY symbol, date DESC;

-- View for correlation analysis
CREATE OR REPLACE VIEW analytics.v_correlation_analysis AS
WITH price_data AS (
    SELECT 
        symbol,
        exchange,
        DATE(interval_start) as date,
        AVG(close) as avg_price,
        AVG(volume) as avg_volume,
        AVG(volatility) as avg_volatility
    FROM analytics.ohlcv_5min
    WHERE interval_start >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY symbol, exchange, DATE(interval_start)
)
SELECT 
    a.symbol as symbol1,
    b.symbol as symbol2,
    a.exchange,
    CORR(a.avg_price, b.avg_price) as price_correlation,
    CORR(a.avg_volume, b.avg_volume) as volume_correlation,
    CORR(a.avg_volatility, b.avg_volatility) as volatility_correlation
FROM price_data a
JOIN price_data b ON a.exchange = b.exchange 
    AND a.date = b.date 
    AND a.symbol < b.symbol
WHERE a.symbol IN ('btcusdt', 'ethusdt', 'bnbusdt')
    AND b.symbol IN ('btcusdt', 'ethusdt', 'bnbusdt');

-- View for market sentiment indicators
CREATE OR REPLACE VIEW analytics.v_market_sentiment AS
SELECT 
    symbol,
    exchange,
    interval_start,
    close,
    volume,
    rsi,
    macd,
    macd_signal,
    CASE 
        WHEN macd > macd_signal THEN 'BULLISH'
        WHEN macd < macd_signal THEN 'BEARISH'
        ELSE 'NEUTRAL'
    END as macd_signal,
    CASE 
        WHEN close > bb_upper THEN 'OVERBOUGHT'
        WHEN close < bb_lower THEN 'OVERSOLD'
        ELSE 'NORMAL'
    END as bb_signal,
    CASE 
        WHEN rsi > 70 AND macd > macd_signal THEN 'STRONG_SELL'
        WHEN rsi < 30 AND macd < macd_signal THEN 'STRONG_BUY'
        WHEN rsi > 70 THEN 'SELL'
        WHEN rsi < 30 THEN 'BUY'
        ELSE 'HOLD'
    END as overall_sentiment
FROM analytics.ohlcv_5min
WHERE interval_start >= CURRENT_DATE - INTERVAL '1 day'
    AND rsi IS NOT NULL
    AND macd IS NOT NULL
    AND bb_upper IS NOT NULL
ORDER BY symbol, interval_start DESC;

-- View for real-time alerts
CREATE OR REPLACE VIEW analytics.v_real_time_alerts AS
SELECT 
    symbol,
    exchange,
    interval_start,
    close,
    price_change_percentage,
    volume,
    rsi,
    volatility,
    CASE 
        WHEN ABS(price_change_percentage) > 5 THEN 'HIGH_VOLATILITY'
        WHEN rsi > 80 OR rsi < 20 THEN 'EXTREME_RSI'
        WHEN volatility > (SELECT AVG(volatility) * 2 FROM analytics.ohlcv_5min WHERE interval_start >= CURRENT_DATE - INTERVAL '1 day') THEN 'HIGH_VOLATILITY'
        ELSE 'NORMAL'
    END as alert_type,
    CASE 
        WHEN ABS(price_change_percentage) > 5 THEN 'Price change > 5%'
        WHEN rsi > 80 THEN 'RSI > 80 (Overbought)'
        WHEN rsi < 20 THEN 'RSI < 20 (Oversold)'
        WHEN volatility > (SELECT AVG(volatility) * 2 FROM analytics.ohlcv_5min WHERE interval_start >= CURRENT_DATE - INTERVAL '1 day') THEN 'High volatility detected'
        ELSE 'No alert'
    END as alert_message
FROM analytics.ohlcv_5min
WHERE interval_start >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
    AND (
        ABS(price_change_percentage) > 5 
        OR rsi > 80 
        OR rsi < 20 
        OR volatility > (SELECT AVG(volatility) * 2 FROM analytics.ohlcv_5min WHERE interval_start >= CURRENT_DATE - INTERVAL '1 day')
    )
ORDER BY interval_start DESC;

-- Grant permissions on views
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO crypto_analytics_user;

-- Create comments for views
COMMENT ON VIEW analytics.v_latest_market_data IS 'Latest market data for the last 24 hours';
COMMENT ON VIEW analytics.v_daily_market_summary IS 'Daily aggregated market summary';
COMMENT ON VIEW analytics.v_exchange_performance IS 'Exchange performance comparison';
COMMENT ON VIEW analytics.v_top_performing_symbols IS 'Top performing symbols by price change';
COMMENT ON VIEW analytics.v_technical_indicators IS 'Technical indicators with trend signals';
COMMENT ON VIEW analytics.v_data_quality_summary IS 'Data quality metrics summary';
COMMENT ON VIEW analytics.v_volume_analysis IS 'Volume analysis by hour';
COMMENT ON VIEW analytics.v_volatility_analysis IS 'Volatility analysis';
COMMENT ON VIEW analytics.v_correlation_analysis IS 'Correlation between different symbols';
COMMENT ON VIEW analytics.v_market_sentiment IS 'Market sentiment indicators';
COMMENT ON VIEW analytics.v_real_time_alerts IS 'Real-time trading alerts'; 