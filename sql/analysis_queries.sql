-- ============================================================
-- YouWe CRM — SaaS Churn & Revenue Analytics
-- Step 3: SQL Analysis
-- ============================================================
-- Every query below is written to answer one specific business
-- question from the project blueprint. Run them in order —
-- later queries build on patterns introduced earlier.
--
-- IMPORTANT — snapshot date: this dataset was generated as of
-- 2025-12-31 (see END_DATE in generate_data.py). Every query below
-- uses DATE '2025-12-31' instead of CURRENT_DATE for that reason —
-- using the real current date would make "active" subscriptions
-- look like they've had zero activity for the months between the
-- data's generation cutoff and today, which isn't a real trend,
-- just a gap between when the data was generated and when you're
-- running the analysis. Real companies deal with this same
-- "as-of date" concept in every reporting pipeline.
-- ============================================================


-- ============================================================
-- 1. NORMALIZED MRR PER SUBSCRIPTION
-- ============================================================
-- Business question: what is each active subscription actually
-- worth per month? (An annual plan needs its price divided by 12
-- to be comparable to a monthly plan — this is the single most
-- important normalization in subscription analytics.)

CREATE OR REPLACE VIEW subscription_mrr AS
SELECT
    s.subscription_id,
    s.customer_id,
    s.plan_id,
    s.billing_cycle,
    s.start_date,
    s.end_date,
    s.status,
    CASE
        WHEN s.billing_cycle = 'monthly' THEN p.monthly_price
        WHEN s.billing_cycle = 'annual'  THEN ROUND(p.annual_price / 12.0, 2)
    END AS mrr
FROM subscriptions s
JOIN plans p ON p.plan_id = s.plan_id;

-- Preview
SELECT * FROM subscription_mrr LIMIT 10;


-- ============================================================
-- 2. MONTHLY MRR WATERFALL (New / Expansion / Contraction / Churned)
-- ============================================================
-- Business question: is revenue growth healthy (driven by new +
-- expansion) or fragile (masked by churn)? This is the single
-- most-requested chart in any SaaS board deck.
--
-- Approach: build a month x customer grid of MRR, then use LAG()
-- to compare each customer's MRR this month vs last month.

WITH months AS (
    SELECT generate_series(
        DATE_TRUNC('month', (SELECT MIN(start_date) FROM subscriptions)),
        DATE_TRUNC('month', (SELECT MAX(COALESCE(end_date, DATE '2025-12-31')) FROM subscriptions)),
        '1 month'
    )::date AS month
),
customer_month_mrr AS (
    -- for every customer and every month, what was their total active MRR?
    SELECT
        m.month,
        sm.customer_id,
        SUM(sm.mrr) AS mrr
    FROM months m
    JOIN subscription_mrr sm
        ON sm.start_date <= m.month
        AND (sm.end_date IS NULL OR sm.end_date >= m.month)
    GROUP BY m.month, sm.customer_id
),
mrr_with_prev AS (
    SELECT
        month,
        customer_id,
        mrr,
        LAG(mrr) OVER (PARTITION BY customer_id ORDER BY month) AS prev_mrr
    FROM customer_month_mrr
),
movement AS (
    SELECT
        month,
        customer_id,
        mrr,
        prev_mrr,
        CASE
            WHEN prev_mrr IS NULL THEN 'new'
            WHEN mrr > prev_mrr THEN 'expansion'
            WHEN mrr < prev_mrr THEN 'contraction'
            ELSE 'unchanged'
        END AS movement_type,
        mrr - COALESCE(prev_mrr, 0) AS mrr_delta
    FROM mrr_with_prev
)
SELECT
    month,
    SUM(CASE WHEN movement_type = 'new' THEN mrr_delta ELSE 0 END) AS new_mrr,
    SUM(CASE WHEN movement_type = 'expansion' THEN mrr_delta ELSE 0 END) AS expansion_mrr,
    SUM(CASE WHEN movement_type = 'contraction' THEN mrr_delta ELSE 0 END) AS contraction_mrr,
    SUM(mrr) AS total_mrr
FROM movement
GROUP BY month
ORDER BY month;

-- Note: "churned MRR" (customers who existed last month, mrr=0 this
-- month) isn't visible in this grid since we only generate rows for
-- ACTIVE months. Query 3 below calculates churned MRR directly.


-- ============================================================
-- 3. CHURNED MRR AND LOGO CHURN RATE BY MONTH
-- ============================================================
-- Business question: how much revenue and how many customers are
-- we losing each month, and is it getting better or worse?

WITH cancellations AS (
    SELECT
        DATE_TRUNC('month', s.end_date)::date AS churn_month,
        s.customer_id,
        sm.mrr AS churned_mrr
    FROM subscriptions s
    JOIN subscription_mrr sm ON sm.subscription_id = s.subscription_id
    WHERE s.status = 'cancelled'
),
active_customers_by_month AS (
    SELECT
        DATE_TRUNC('month', gs)::date AS month,
        COUNT(DISTINCT s.customer_id) AS active_customers
    FROM subscriptions s
    CROSS JOIN LATERAL generate_series(
        DATE_TRUNC('month', s.start_date),
        DATE_TRUNC('month', COALESCE(s.end_date, DATE '2025-12-31')),
        '1 month'
    ) AS gs
    GROUP BY 1
)
SELECT
    a.month,
    a.active_customers,
    COALESCE(COUNT(DISTINCT c.customer_id), 0) AS customers_churned,
    ROUND(COALESCE(COUNT(DISTINCT c.customer_id), 0)::numeric / NULLIF(a.active_customers, 0) * 100, 2) AS logo_churn_rate_pct,
    ROUND(COALESCE(SUM(c.churned_mrr), 0), 2) AS churned_mrr
FROM active_customers_by_month a
LEFT JOIN cancellations c ON c.churn_month = a.month
GROUP BY a.month, a.active_customers
ORDER BY a.month;


-- ============================================================
-- 4. COHORT RETENTION (% of signup cohort still active at month N)
-- ============================================================
-- Business question: of customers who signed up in a given month,
-- what % are still active 1, 3, 6, 12 months later? This is the
-- classic cohort retention heatmap you'll rebuild in Power BI.

WITH cohorts AS (
    SELECT
        customer_id,
        DATE_TRUNC('month', signup_date)::date AS cohort_month
    FROM customers
),
customer_active_months AS (
    -- every month a customer had at least one active subscription
    SELECT DISTINCT
        s.customer_id,
        DATE_TRUNC('month', gs)::date AS active_month
    FROM subscriptions s
    CROSS JOIN LATERAL generate_series(
        DATE_TRUNC('month', s.start_date),
        DATE_TRUNC('month', COALESCE(s.end_date, DATE '2025-12-31')),
        '1 month'
    ) AS gs
),
cohort_activity AS (
    SELECT
        c.cohort_month,
        c.customer_id,
        cam.active_month,
        (EXTRACT(YEAR FROM cam.active_month) - EXTRACT(YEAR FROM c.cohort_month)) * 12
          + (EXTRACT(MONTH FROM cam.active_month) - EXTRACT(MONTH FROM c.cohort_month)) AS months_since_signup
    FROM cohorts c
    JOIN customer_active_months cam ON cam.customer_id = c.customer_id
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(*) AS cohort_size
    FROM cohorts
    GROUP BY cohort_month
)
SELECT
    ca.cohort_month,
    cs.cohort_size,
    ca.months_since_signup,
    COUNT(DISTINCT ca.customer_id) AS active_customers,
    ROUND(COUNT(DISTINCT ca.customer_id)::numeric / cs.cohort_size * 100, 1) AS retention_pct
FROM cohort_activity ca
JOIN cohort_sizes cs ON cs.cohort_month = ca.cohort_month
WHERE ca.months_since_signup IN (0, 1, 3, 6, 12)
GROUP BY ca.cohort_month, cs.cohort_size, ca.months_since_signup
ORDER BY ca.cohort_month, ca.months_since_signup;


-- ============================================================
-- 5. CUSTOMER LIFETIME VALUE (CLV) BY SEGMENT
-- ============================================================
-- Business question: which customer segments are worth the most
-- over their lifetime, and does that match where we're spending
-- on acquisition?

WITH customer_revenue AS (
    SELECT
        c.customer_id,
        c.country,
        c.company_size_band,
        c.acquisition_channel,
        SUM(i.amount) AS total_revenue,
        MIN(s.start_date) AS first_start,
        MAX(COALESCE(s.end_date, DATE '2025-12-31')) AS last_active,
        ROUND(
            (MAX(COALESCE(s.end_date, DATE '2025-12-31')) - MIN(s.start_date)) / 30.44
        , 1) AS tenure_months
    FROM customers c
    JOIN subscriptions s ON s.customer_id = c.customer_id
    JOIN invoices i ON i.subscription_id = s.subscription_id AND i.payment_status = 'paid'
    GROUP BY c.customer_id, c.country, c.company_size_band, c.acquisition_channel
)
SELECT
    COALESCE(acquisition_channel, 'Unknown') AS acquisition_channel,
    COUNT(*) AS customers,
    ROUND(AVG(total_revenue), 2) AS avg_clv,
    ROUND(AVG(tenure_months), 1) AS avg_tenure_months,
    ROUND(SUM(total_revenue), 2) AS total_revenue_from_segment
FROM customer_revenue
GROUP BY acquisition_channel
ORDER BY avg_clv DESC;

-- Same breakdown by company size band — swap the GROUP BY column
-- to reuse this pattern for any other segment (country, plan tier).


-- ============================================================
-- 6. REVENUE-AT-RISK: CUSTOMERS WITH DECLINING USAGE
-- ============================================================
-- Business question: which currently-active customers show an
-- early-warning usage decline, and how much MRR do they represent?
-- (This is the query that would feed a Customer Success "at-risk" list.)

WITH recent_usage AS (
    SELECT
        customer_id,
        usage_month,
        login_count,
        AVG(login_count) OVER (
            PARTITION BY customer_id
            ORDER BY usage_month
            ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
        ) AS trailing_avg_logins
    FROM usage_monthly
),
latest_month AS (
    SELECT MAX(usage_month) AS m FROM usage_monthly
),
declining_customers AS (
    SELECT
        ru.customer_id,
        ru.login_count AS latest_logins,
        ROUND(ru.trailing_avg_logins, 1) AS trailing_avg_logins,
        ROUND((ru.login_count - ru.trailing_avg_logins) / NULLIF(ru.trailing_avg_logins, 0) * 100, 1) AS pct_change
    FROM recent_usage ru, latest_month lm
    WHERE ru.usage_month = lm.m
      AND ru.trailing_avg_logins IS NOT NULL
      AND ru.login_count < ru.trailing_avg_logins * 0.5   -- usage dropped by more than half
)
SELECT
    dc.customer_id,
    c.company_name,
    dc.latest_logins,
    dc.trailing_avg_logins,
    dc.pct_change AS pct_change_in_usage,
    ROUND(SUM(sm.mrr), 2) AS at_risk_mrr
FROM declining_customers dc
JOIN customers c ON c.customer_id = dc.customer_id
JOIN subscription_mrr sm ON sm.customer_id = dc.customer_id AND sm.status = 'active'
GROUP BY dc.customer_id, c.company_name, dc.latest_logins, dc.trailing_avg_logins, dc.pct_change
ORDER BY at_risk_mrr DESC
LIMIT 20;


-- ============================================================
-- 7. NET REVENUE RETENTION (NRR) — a single headline number
-- ============================================================
-- Business question: excluding new customers, did our existing base
-- grow or shrink in revenue over the last 12 months? >100% is healthy.

WITH base_12mo_ago AS (
    SELECT customer_id, SUM(mrr) AS mrr
    FROM subscription_mrr
    WHERE start_date <= DATE '2025-12-31' - INTERVAL '12 months'
      AND (end_date IS NULL OR end_date >= DATE '2025-12-31' - INTERVAL '12 months')
    GROUP BY customer_id
),
same_customers_now AS (
    SELECT b.customer_id, COALESCE(SUM(sm.mrr), 0) AS mrr_now
    FROM base_12mo_ago b
    LEFT JOIN subscription_mrr sm
        ON sm.customer_id = b.customer_id
        AND sm.status = 'active'
    GROUP BY b.customer_id
)
SELECT
    ROUND(SUM(b.mrr), 2) AS starting_mrr_12mo_ago,
    ROUND(SUM(s.mrr_now), 2) AS same_customers_mrr_now,
    ROUND(SUM(s.mrr_now) / NULLIF(SUM(b.mrr), 0) * 100, 1) AS net_revenue_retention_pct
FROM base_12mo_ago b
JOIN same_customers_now s ON s.customer_id = b.customer_id;
