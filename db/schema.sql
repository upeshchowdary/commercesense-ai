CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    base_price REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_metrics (
    product_id TEXT NOT NULL,
    date TEXT NOT NULL,
    units_sold INTEGER NOT NULL,
    inventory_level INTEGER NOT NULL,
    rank INTEGER NOT NULL,
    has_buy_box INTEGER NOT NULL,
    ad_spend REAL NOT NULL,
    ad_clicks INTEGER NOT NULL,
    ad_sales REAL NOT NULL,
    PRIMARY KEY (product_id, date),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS detected_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL,
    date TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    evidence TEXT NOT NULL,
    detected_at TEXT NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);
