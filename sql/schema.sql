-- ============================================================
-- YouWe CRM — SaaS Churn & Revenue Analytics
-- Target relational schema (this is what your CLEANED data
-- loads into — the raw CSVs from generate_data.py do NOT match
-- this exactly on purpose; cleaning them into this shape is
-- part of the Python step).
-- ============================================================

DROP TABLE IF EXISTS support_tickets, usage_monthly, invoices, subscriptions, plans, customers CASCADE;

CREATE TABLE customers (
    customer_id           INTEGER PRIMARY KEY,
    company_name          TEXT NOT NULL,
    country               TEXT NOT NULL,          -- standardized to full country names
    company_size_band     TEXT,                    -- '1-10','11-50','51-200','201-1000','1000+' or NULL
    signup_date DATE NOT NULL,
    acquisition_channel TEXT,
    signup_date_ambiguous BOOLEAN DEFAULT FALSE -- TRUE = ambiguous d/m vs m/d date, defaulted to day-first
);

CREATE TABLE plans (
    plan_id        INTEGER PRIMARY KEY,
    plan_name      TEXT NOT NULL,
    tier           TEXT NOT NULL,
    monthly_price  NUMERIC(10,2) NOT NULL,
    annual_price   NUMERIC(10,2) NOT NULL
);

CREATE TABLE subscriptions (
    subscription_id  INTEGER PRIMARY KEY,
    customer_id      INTEGER NOT NULL REFERENCES customers(customer_id),
    plan_id          INTEGER NOT NULL REFERENCES plans(plan_id),
    start_date       DATE NOT NULL,
    end_date         DATE,                          -- NULL = still active
    billing_cycle    TEXT NOT NULL CHECK (billing_cycle IN ('monthly','annual')),
    status           TEXT NOT NULL CHECK (status IN ('active','cancelled'))
);

CREATE TABLE invoices (
    invoice_id       INTEGER PRIMARY KEY,
    subscription_id  INTEGER NOT NULL REFERENCES subscriptions(subscription_id),
    invoice_date     DATE NOT NULL,
    amount           NUMERIC(10,2) NOT NULL,         -- cast from messy string in Python cleaning step
    payment_status TEXT NOT NULL CHECK (payment_status IN ('paid','failed','refunded')),
    is_outlier       BOOLEAN DEFAULT FALSE           -- TRUE = amount is >5x or <0.2x the expected plan price; flagged for review, not auto-corrected
);

CREATE TABLE usage_monthly (
    customer_id           INTEGER NOT NULL REFERENCES customers(customer_id),
    usage_month           DATE NOT NULL,             -- first day of month
    login_count           INTEGER NOT NULL,
    feature_usage_count   INTEGER NOT NULL,
    PRIMARY KEY (customer_id, usage_month)
);

CREATE TABLE support_tickets (
    ticket_id       INTEGER PRIMARY KEY,
    customer_id     INTEGER NOT NULL REFERENCES customers(customer_id),
    created_date    DATE NOT NULL,
    resolved_date   DATE,                            -- NULL = still open
    priority        TEXT NOT NULL CHECK (priority IN ('Low','Medium','High','Urgent')),
    category        TEXT NOT NULL
);

-- Helpful indexes for the analysis queries you'll write next
CREATE INDEX idx_subscriptions_customer ON subscriptions(customer_id);
CREATE INDEX idx_invoices_subscription ON invoices(subscription_id);
CREATE INDEX idx_usage_customer_month ON usage_monthly(customer_id, usage_month);
CREATE INDEX idx_tickets_customer ON support_tickets(customer_id);
