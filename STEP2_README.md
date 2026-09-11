# Step 2: Data Cleaning — Nimbus CRM SaaS Dataset

## What's in this step

- `clean_data.py` — the cleaning script (run against `raw_data/`)
- `clean_data/` — the six cleaned CSVs, ready to load into `schema.sql`
- `clean_data/cleaning_log.md` — auto-generated summary of every fix applied (paste relevant lines straight into your project write-up)

## What got fixed, and the reasoning (use this in your documentation / interviews)

| Issue | Decision made | Why |
|---|---|---|
| 16 country spellings ("USA"/"US"/"Bharat"/etc.) | Mapped to 5 canonical country names via a lookup dict | Standard practice: build the map once by inspecting `.unique()` on the raw column |
| 4 mixed date formats, some genuinely ambiguous (e.g. `03/04/2023`) | Parsed unambiguous dates directly; ambiguous ones defaulted to day-first **and flagged** with a `signup_date_ambiguous` column | Silently guessing wrong on ambiguous dates is worse than admitting you don't know — the flag keeps it auditable instead of hiding the uncertainty |
| ~530 missing `company_size_band` / `acquisition_channel` values | Left as real `NULL`, not filled with a fake "Unknown" string | Filling with a fake category would quietly distort channel- or size-based churn comparisons later |
| 80 near-duplicate customer records | Normalized company names (case, punctuation, "LLC" variants), matched, merged to the earliest `customer_id`, and **remapped every foreign key** (subscriptions, usage, tickets) that pointed at the duplicate | A duplicate customer isn't just a display issue — every related table has to be corrected too, or your churn/revenue numbers double-count that customer |
| ~45,000 invoice amounts, ~10% stored as strings like `"$1,234.00"` | Stripped symbols/commas, cast to numeric | Needed before any SQL aggregation will work |
| ~700 invoice amounts wildly off (>5x or <0.2x the expected plan price) | Flagged with an `is_outlier` column, **not auto-corrected** | You don't actually know if it's a data-entry error or a real discount/upsell without more context — flagging for review is the honest move, and it's what a real analyst would do rather than silently "fixing" someone else's billing data |

**Note on the ambiguous-dates decision:** this dataset is worth mentioning specifically in an interview — resolving `03/04/2023` as day-first vs. month-first is a genuinely unsolvable ambiguity without knowing the source system's locale. Flagging rather than silently picking one is the kind of judgment call that signals real analyst thinking, not just pandas syntax.

## Data integrity check (already verified for you)

After cleaning: **zero orphaned foreign keys** across subscriptions/invoices/usage/tickets, **zero duplicate customer_ids remaining**, **zero unparsed invoice amounts**. This data will load into `schema.sql` cleanly.

## Loading into PostgreSQL

```bash
createdb nimbus_crm
psql -d nimbus_crm -f schema.sql
```

Then, from `psql` connected to `nimbus_crm` (adjust the path to wherever `clean_data/` sits):

```sql
\copy customers        FROM 'clean_data/clean_customers.csv'        CSV HEADER;
\copy plans             FROM 'clean_data/clean_plans.csv'             CSV HEADER;
\copy subscriptions     FROM 'clean_data/clean_subscriptions.csv'     CSV HEADER;
\copy invoices          FROM 'clean_data/clean_invoices.csv'          CSV HEADER;
\copy usage_monthly     FROM 'clean_data/clean_usage_monthly.csv'     CSV HEADER;
\copy support_tickets   FROM 'clean_data/clean_support_tickets.csv'   CSV HEADER;
```

Run a quick check afterward:

```sql
SELECT count(*) FROM customers;       -- expect 4000
SELECT count(*) FROM subscriptions;   -- expect 4564
SELECT count(*) FROM invoices;        -- expect 45289
```

## Next step

Step 3 is SQL analysis: the MRR waterfall, churn rate, cohort retention, and CLV queries that turn this clean data into the actual business insights.
