# Step 1: Data Design & Generation — Nimbus CRM SaaS Dataset

## What's in this step

- `generate_data.py` — generates the raw, deliberately messy dataset
- `raw_data/` — the generated CSVs (already run once for you; re-run any time for a fresh dataset)
- `schema.sql` — the **target** PostgreSQL schema your cleaned data should load into

## The ERD (entity relationships)

```
customers (1) ───< subscriptions (many) ───< invoices (many)
customers (1) ───< usage_monthly (many)
customers (1) ───< support_tickets (many)
plans (1) ───< subscriptions (many)
```

- One customer can have multiple subscriptions over time (cancel → resubscribe is modeled)
- One subscription generates many invoices (one per billing period)
- One customer has many monthly usage rows and many support tickets
- `plans` is a small clean lookup table joined into subscriptions

This is intentionally a proper **star-ish schema**: `customers` and `plans` are dimension-like, `subscriptions`, `invoices`, `usage_monthly`, and `support_tickets` are fact-like tables. This is the same shape you'll later model as a real star schema in Power BI.

## The messiness — and why each piece is there

| Table | Issue injected | Why it matters |
|---|---|---|
| `customers` | Country stored inconsistently ("USA"/"US"/"United States"/"Bharat" for India) | Standardizing categorical values is one of the most common real cleaning tasks |
| `customers` | ~6-8% missing `company_size_band` / `acquisition_channel` | Forces a real missing-value-handling decision, not just `dropna()` |
| `customers` | Mixed date formats in `signup_date` (`2024-07-17`, `03/03/2023`, `13-Sep-2023`) | Multi-source exports rarely agree on date format |
| `customers` | ~2% near-duplicate rows (same company, mangled name, new ID) | Simulates duplicate lead/customer records from multiple systems |
| `subscriptions` | Same mixed-date-format issue on `start_date` | Same reasoning, different table |
| `invoices` | ~10% of `amount` stored as a string like `"$1,234.00"` | You'll need to strip symbols/commas and cast to numeric |
| `invoices` | ~1.5% clear data-entry outliers (amount off by 100x or 0.01x) | Outlier detection is a named requirement — this gives you real ones to find |
| `usage_monthly` | Usage tapers off in the 3 months before a cancelled subscription ends | Gives your EDA/churn analysis a genuine signal to discover, not a random dataset |
| `support_tickets` | `resolved_date` is NULL for ~5% of tickets | A meaningful NULL (still open), different from a data-quality NULL — worth distinguishing in your write-up |

## Next steps (don't do these yet — just context)

1. Python cleaning script: standardize country names, parse all date formats, strip currency symbols and cast `amount` to numeric, decide on and document a missing-value strategy, flag/handle the outlier invoices, and de-duplicate customers (e.g., fuzzy match on normalized company name).
2. Load the cleaned tables into PostgreSQL using `schema.sql`.
3. Move to SQL analysis (MRR waterfall, churn, cohort retention, CLV).

## How to load into PostgreSQL once your data is cleaned

```bash
# create the database
createdb nimbus_crm

# create the tables
psql -d nimbus_crm -f schema.sql

# load each cleaned CSV (run from psql, adjust paths)
\copy customers        FROM 'clean_customers.csv'        CSV HEADER;
\copy plans             FROM 'clean_plans.csv'             CSV HEADER;
\copy subscriptions     FROM 'clean_subscriptions.csv'     CSV HEADER;
\copy invoices          FROM 'clean_invoices.csv'          CSV HEADER;
\copy usage_monthly     FROM 'clean_usage_monthly.csv'     CSV HEADER;
\copy support_tickets   FROM 'clean_support_tickets.csv'   CSV HEADER;
```

(You'll produce the `clean_*.csv` files in the Python cleaning step — that's Step 2.)

## Regenerating the raw data

```bash
pip install faker pandas numpy
python generate_data.py
```

This is seeded (`random_state=42` / `Faker.seed(42)`), so re-running produces the same dataset unless you change the seed or the row counts at the top of the script.
