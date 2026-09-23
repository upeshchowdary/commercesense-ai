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

-- ===================================================================
-- Intelligence modules (Listing / Pricing / Review / Inventory).
-- Same database, same product_id foreign key, same "one system of
-- record" rule as everything above -- these are additive, not a
-- second product model.
-- ===================================================================

CREATE TABLE IF NOT EXISTS listing_data (
    product_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    brand TEXT NOT NULL,
    product_type TEXT NOT NULL,
    bullets TEXT NOT NULL,           -- JSON array of strings
    description TEXT NOT NULL,
    backend_keywords TEXT,
    attributes TEXT NOT NULL,        -- JSON object
    image_urls TEXT NOT NULL,        -- JSON array of strings
    image_count INTEGER NOT NULL,
    listing_status TEXT NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS listing_audits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL,
    score INTEGER NOT NULL,
    category_scores TEXT NOT NULL,   -- JSON
    failed_rules TEXT NOT NULL,      -- JSON array
    warnings TEXT NOT NULL,          -- JSON array
    passed_rules TEXT NOT NULL,      -- JSON array
    analyzed_at TEXT NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS listing_recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL,
    audit_id INTEGER,
    field TEXT NOT NULL,
    current_value TEXT NOT NULL,
    proposed_value TEXT NOT NULL,
    changes TEXT NOT NULL,           -- JSON array of change descriptions
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (audit_id) REFERENCES listing_audits(id)
);

CREATE TABLE IF NOT EXISTS pricing_data (
    product_id TEXT PRIMARY KEY,
    cogs REAL NOT NULL,
    referral_fee_pct REAL NOT NULL,
    fulfillment_fee REAL NOT NULL,
    other_cost REAL NOT NULL DEFAULT 0,
    target_margin_pct REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS pricing_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL,
    competitor TEXT NOT NULL,
    price REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    source TEXT NOT NULL,            -- 'synthetic' | 'csv' | 'web'
    source_url TEXT,
    observed_at TEXT NOT NULL,
    confidence TEXT NOT NULL,        -- low/medium/high
    is_verified INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS pricing_analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL,
    current_price REAL NOT NULL,
    variable_cost REAL NOT NULL,
    contribution REAL NOT NULL,
    margin_pct REAL NOT NULL,
    breakeven_price REAL NOT NULL,
    target_margin_price REAL NOT NULL,
    price_state TEXT NOT NULL,
    recommended_low REAL,
    recommended_high REAL,
    analyzed_at TEXT NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS review_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL,
    rating INTEGER NOT NULL,
    review_text TEXT NOT NULL,
    review_date TEXT NOT NULL,
    verified_purchase INTEGER NOT NULL DEFAULT 1,
    source TEXT NOT NULL DEFAULT 'synthetic',
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS review_analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL,
    window_days INTEGER NOT NULL,
    total_reviews INTEGER NOT NULL,
    avg_rating REAL NOT NULL,
    rating_distribution TEXT NOT NULL,  -- JSON
    negative_pct REAL NOT NULL,
    velocity INTEGER NOT NULL,
    previous_velocity INTEGER NOT NULL,
    trend TEXT NOT NULL,
    themes TEXT NOT NULL,               -- JSON
    emerging_issues TEXT NOT NULL,      -- JSON
    analyzed_at TEXT NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS inventory_config (
    product_id TEXT PRIMARY KEY,
    lead_time_days INTEGER NOT NULL,
    safety_days INTEGER NOT NULL,
    moq INTEGER,
    reorder_multiple INTEGER,
    target_service_level REAL NOT NULL DEFAULT 0.95,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- Shared across all four modules: powers the Agents page + observability
-- counts for the new agents. Deliberately the only new "trace-like" table
-- -- individual decisions still go through decision_log.py, never here.
CREATE TABLE IF NOT EXISTS intelligence_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    module TEXT NOT NULL,
    status TEXT NOT NULL,
    provenance TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE INDEX IF NOT EXISTS idx_listing_audits_product ON listing_audits(product_id);
CREATE INDEX IF NOT EXISTS idx_pricing_observations_product ON pricing_observations(product_id);
CREATE INDEX IF NOT EXISTS idx_review_items_product ON review_items(product_id);
CREATE INDEX IF NOT EXISTS idx_review_items_date ON review_items(review_date);
CREATE INDEX IF NOT EXISTS idx_intelligence_runs_product ON intelligence_runs(product_id);
CREATE INDEX IF NOT EXISTS idx_intelligence_runs_module ON intelligence_runs(module);
