-- ============================================
-- TradingIA Database Initialization
-- ============================================

-- Crear schema
CREATE SCHEMA IF NOT EXISTS trading;

-- Tabla de trades
CREATE TABLE IF NOT EXISTS trading.trades (
    id SERIAL PRIMARY KEY,
    trade_id VARCHAR(255) UNIQUE NOT NULL,
    token_symbol VARCHAR(50) NOT NULL,
    entry_price DECIMAL(20, 8) NOT NULL,
    entry_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    qty DECIMAL(20, 8) NOT NULL,
    amount_usd DECIMAL(20, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'OPEN', -- OPEN, CLOSED, STOPPED
    exit_price DECIMAL(20, 8),
    exit_date TIMESTAMP,
    pnl_usd DECIMAL(20, 2),
    pnl_pct DECIMAL(10, 4),
    stop_loss_price DECIMAL(20, 8),
    take_profit_price DECIMAL(20, 8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de transacciones en exchange
CREATE TABLE IF NOT EXISTS trading.exchange_orders (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(255) UNIQUE NOT NULL,
    trade_id INTEGER REFERENCES trading.trades(id) ON DELETE CASCADE,
    order_type VARCHAR(20), -- MARKET, LIMIT, STOP
    side VARCHAR(10), -- BUY, SELL
    symbol VARCHAR(50),
    quantity DECIMAL(20, 8),
    price DECIMAL(20, 8),
    status VARCHAR(20),
    exchange VARCHAR(50),
    exchange_response JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de señales generadas
CREATE TABLE IF NOT EXISTS trading.signals (
    id SERIAL PRIMARY KEY,
    signal_id VARCHAR(255) UNIQUE NOT NULL,
    token_symbol VARCHAR(50) NOT NULL,
    score DECIMAL(10, 4),
    netflow_usd DECIMAL(20, 2),
    trader_count INTEGER,
    signal_type VARCHAR(20), -- BUY, SELL, HOLD
    confidence DECIMAL(5, 2),
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    executed BOOLEAN DEFAULT FALSE,
    executed_at TIMESTAMP
);

-- Tabla de eventos del sistema
CREATE TABLE IF NOT EXISTS trading.system_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50), -- ERROR, WARNING, INFO, TRADE
    level VARCHAR(20),
    message TEXT,
    context JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_trades_status ON trading.trades(status);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trading.trades(token_symbol);
CREATE INDEX IF NOT EXISTS idx_trades_entry_date ON trading.trades(entry_date DESC);
CREATE INDEX IF NOT EXISTS idx_signals_token ON trading.signals(token_symbol);
CREATE INDEX IF NOT EXISTS idx_signals_generated_at ON trading.signals(generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_trade_id ON trading.exchange_orders(trade_id);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON trading.system_events(timestamp DESC);

-- Crear vista para dashboard
CREATE OR REPLACE VIEW trading.open_positions AS
SELECT 
    id,
    trade_id,
    token_symbol,
    entry_price,
    entry_date,
    qty,
    amount_usd,
    (SELECT ROUND((pnl_pct)::numeric, 2)) as current_pnl_pct,
    stop_loss_price,
    take_profit_price
FROM trading.trades
WHERE status = 'OPEN'
ORDER BY entry_date DESC;

-- Crear vista para P&L
CREATE OR REPLACE VIEW trading.daily_pnl AS
SELECT 
    DATE(exit_date) as trade_date,
    COUNT(*) as trades_closed,
    SUM(CASE WHEN pnl_usd > 0 THEN pnl_usd ELSE 0 END) as total_profit,
    SUM(CASE WHEN pnl_usd < 0 THEN ABS(pnl_usd) ELSE 0 END) as total_loss,
    SUM(pnl_usd) as net_pnl,
    AVG(pnl_pct) as avg_pnl_pct,
    COUNT(CASE WHEN pnl_usd > 0 THEN 1 END) as winning_trades,
    COUNT(CASE WHEN pnl_usd < 0 THEN 1 END) as losing_trades
FROM trading.trades
WHERE status = 'CLOSED' AND exit_date IS NOT NULL
GROUP BY DATE(exit_date)
ORDER BY trade_date DESC;

-- Grants para usuario trading_user
GRANT USAGE ON SCHEMA trading TO trading_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA trading TO trading_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA trading TO trading_user;
GRANT SELECT ON ALL VIEWS IN SCHEMA trading TO trading_user;