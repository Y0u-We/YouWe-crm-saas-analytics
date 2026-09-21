-- ============================================================
-- YouWe CRM — Power BI Data Import Queries
-- ============================================================
-- Each query below becomes ONE table in Power BI. Paste the query
-- text (not this whole file) into the "SQL statement" box when you
-- connect via Get Data > PostgreSQL database > Advanced options.
--
-- All "active this month" logic here uses ONE consistent convention
-- throughout (a subscription counts as active in a month if it
-- started on or before that month's 1st) — the same convention as
-- Step 3's Query 2 and Step 5's Excel workbook. This resolves the
-- Query 2 vs Query 3 inconsistency flagged in STEP5_README.md by
-- standardizing on it here, project-wide, going forward.
--
-- Every query below has already been run and verified against the
-- live database — row counts and headline figures are documented
-- in STEP6_README.md.
-- ============================================================


-- ====== TABLE: dim_customer ======
SELECT customer_id, company_name, country, company_size_band, acquisition_channel, signup_date
FROM customers;


-- ====== TABLE: dim_plan ======
SELECT plan_id, plan_name, tier, monthly_price, annual_price
FROM plans;


-- ====== TABLE: fact_monthly_subscription ======
-- Grain: one row per customer per active month per plan. This is the
-- core fact table — drives the MRR trend, and can be sliced by any
-- dimension (plan tier, channel, country, month) once related to the
-- dim tables above.
WITH months AS (
    SELECT generate_series(
        DATE_TRUNC('month', (SELECT MIN(start_date) FROM subscriptions)),
        DATE_TRUNC('month', DATE '2025-12-31'),
        '1 month'
    )::date AS month
),
subscription_mrr AS (
    SELECT s.subscription_id, s.customer_id, s.plan_id, s.billing_cycle, s.start_date, s.end_date, s.status,
        CASE WHEN s.billing_cycle='monthly' THEN p.monthly_price ELSE ROUND(p.annual_price/12.0,2) END AS mrr
    FROM subscriptions s JOIN plans p ON p.plan_id=s.plan_id
)
SELECT m.month, sm.customer_id, sm.plan_id, SUM(sm.mrr) AS mrr
FROM months m
JOIN subscription_mrr sm ON sm.start_date <= m.month AND (sm.end_date IS NULL OR sm.end_date >= m.month)
GROUP BY m.month, sm.customer_id, sm.plan_id;


-- ====== TABLE: fact_mrr_waterfall ======
-- Grain: one row per customer per month, pre-classified as new/
-- expansion/contraction/unchanged (same logic as Step 3 Query 2).
-- Sum mrr_delta grouped by month + movement_type in Power BI to
-- build the waterfall chart — no DAX time-intelligence needed.
WITH months AS (
    SELECT generate_series(
        DATE_TRUNC('month', (SELECT MIN(start_date) FROM subscriptions)),
        DATE_TRUNC('month', DATE '2025-12-31'),
        '1 month'
    )::date AS month
),
subscription_mrr AS (
    SELECT s.subscription_id, s.customer_id, s.plan_id, s.billing_cycle, s.start_date, s.end_date, s.status,
        CASE WHEN s.billing_cycle='monthly' THEN p.monthly_price ELSE ROUND(p.annual_price/12.0,2) END AS mrr
    FROM subscriptions s JOIN plans p ON p.plan_id=s.plan_id
),
customer_month_mrr AS (
    SELECT m.month, sm.customer_id, SUM(sm.mrr) AS mrr
    FROM months m JOIN subscription_mrr sm ON sm.start_date <= m.month AND (sm.end_date IS NULL OR sm.end_date >= m.month)
    GROUP BY m.month, sm.customer_id
),
with_prev AS (
    SELECT month, customer_id, mrr, LAG(mrr) OVER (PARTITION BY customer_id ORDER BY month) AS prev_mrr
    FROM customer_month_mrr
)
SELECT month, customer_id, mrr, prev_mrr,
    CASE WHEN prev_mrr IS NULL THEN 'new' WHEN mrr>prev_mrr THEN 'expansion' WHEN mrr<prev_mrr THEN 'contraction' ELSE 'unchanged' END AS movement_type,
    mrr - COALESCE(prev_mrr,0) AS mrr_delta
FROM with_prev;


-- ====== TABLE: fact_churn_by_month ======
-- Grain: one row per month. customers_churned = customers active
-- THIS month who are NOT active next month (i.e., this was their
-- last active month). Uses the same "active at month start"
-- convention as fact_monthly_subscription, so it's internally
-- consistent with the MRR figures — unlike Step 3's Query 3.
--
-- IMPORTANT — right-censoring: the most recent month in the dataset
-- (Dec 2025) has no "next month" to check, so every active customer
-- would otherwise incorrectly show as "churned" (100% churn) simply
-- because the data ends there, not because they actually left. This
-- query explicitly excludes the final month from churn reporting —
-- standard practice for exactly this reason. Do not report a churn
-- rate for the most recent month in any dashboard built on this data.
WITH months AS (
    SELECT generate_series(
        DATE_TRUNC('month', (SELECT MIN(start_date) FROM subscriptions)),
        DATE_TRUNC('month', DATE '2025-12-31'),
        '1 month'
    )::date AS month
),
subscription_mrr AS (
    SELECT s.subscription_id, s.customer_id, s.plan_id, s.billing_cycle, s.start_date, s.end_date,
        CASE WHEN s.billing_cycle='monthly' THEN p.monthly_price ELSE ROUND(p.annual_price/12.0,2) END AS mrr
    FROM subscriptions s JOIN plans p ON p.plan_id=s.plan_id
),
customer_month AS (
    SELECT DISTINCT m.month, sm.customer_id, sm.mrr
    FROM months m JOIN subscription_mrr sm ON sm.start_date <= m.month AND (sm.end_date IS NULL OR sm.end_date >= m.month)
),
active_agg AS (
    SELECT month, customer_id, SUM(mrr) AS mrr FROM customer_month GROUP BY month, customer_id
),
with_next AS (
    SELECT month, customer_id, mrr,
        LEAD(month) OVER (PARTITION BY customer_id ORDER BY month) AS next_active_month
    FROM active_agg
),
churn_flagged AS (
    SELECT month, customer_id, mrr,
        (next_active_month IS NULL OR next_active_month <> (month + INTERVAL '1 month')::date) AS is_last_active_month
    FROM with_next
)
SELECT
    month,
    COUNT(DISTINCT customer_id) AS active_customers,
    COUNT(DISTINCT CASE WHEN is_last_active_month THEN customer_id END) AS customers_churned,
    ROUND(SUM(CASE WHEN is_last_active_month THEN mrr ELSE 0 END),2) AS churned_mrr,
    ROUND(COUNT(DISTINCT CASE WHEN is_last_active_month THEN customer_id END)::numeric / NULLIF(COUNT(DISTINCT customer_id),0) * 100, 2) AS logo_churn_rate_pct
FROM churn_flagged
WHERE month < (SELECT MAX(month) FROM months)   -- exclude the censored final month
GROUP BY month
ORDER BY month;


-- ====== TABLE: fact_cohort_retention ======
-- Grain: one row per cohort_month x months_since_signup (0/1/3/6/12).
-- Feeds the cohort retention heatmap matrix visual directly.
WITH cohorts AS (
    SELECT customer_id, DATE_TRUNC('month', signup_date)::date AS cohort_month FROM customers
),
customer_active_months AS (
    SELECT DISTINCT s.customer_id, DATE_TRUNC('month', gs)::date AS active_month
    FROM subscriptions s
    CROSS JOIN LATERAL generate_series(DATE_TRUNC('month', s.start_date), DATE_TRUNC('month', COALESCE(s.end_date, DATE '2025-12-31')), '1 month') AS gs
),
cohort_activity AS (
    SELECT c.cohort_month, c.customer_id, cam.active_month,
        (EXTRACT(YEAR FROM cam.active_month)-EXTRACT(YEAR FROM c.cohort_month))*12 + (EXTRACT(MONTH FROM cam.active_month)-EXTRACT(MONTH FROM c.cohort_month)) AS months_since_signup
    FROM cohorts c JOIN customer_active_months cam ON cam.customer_id=c.customer_id
),
cohort_sizes AS (SELECT cohort_month, COUNT(*) AS cohort_size FROM cohorts GROUP BY cohort_month)
SELECT ca.cohort_month, cs.cohort_size, ca.months_since_signup, COUNT(DISTINCT ca.customer_id) AS active_customers,
    ROUND(COUNT(DISTINCT ca.customer_id)::numeric/cs.cohort_size*100,1) AS retention_pct
FROM cohort_activity ca JOIN cohort_sizes cs ON cs.cohort_month=ca.cohort_month
WHERE ca.months_since_signup BETWEEN 0 AND 12
GROUP BY ca.cohort_month, cs.cohort_size, ca.months_since_signup
ORDER BY ca.cohort_month, ca.months_since_signup;


-- ====== TABLE: fact_customer_clv ======
-- Grain: one row per customer, with their lifetime revenue, tenure,
-- and segment attributes — feeds the CLV/segments and acquisition
-- channel pages directly (just drag acquisition_channel + AVERAGE
-- of total_revenue into a visual, no DAX needed for the headline number).
SELECT c.customer_id, c.country, c.company_size_band, c.acquisition_channel,
    SUM(i.amount) AS total_revenue,
    ROUND((MAX(COALESCE(s.end_date, DATE '2025-12-31')) - MIN(s.start_date))/30.44,1) AS tenure_months
FROM customers c
JOIN subscriptions s ON s.customer_id=c.customer_id
JOIN invoices i ON i.subscription_id=s.subscription_id AND i.payment_status='paid'
GROUP BY c.customer_id, c.country, c.company_size_band, c.acquisition_channel;
