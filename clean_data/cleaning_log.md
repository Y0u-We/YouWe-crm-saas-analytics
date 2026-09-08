# Data Cleaning Log

- Standardized country names: 16 raw variants -> 5 canonical countries (0 rows didn't match the map and need review)
- Parsed signup_date across 4 mixed formats: 814 ambiguous day/month dates flagged (defaulted to day-first), 0 failed to parse
- Left 228 missing company_size_band and 302 missing acquisition_channel as NULL (documented as a real 'unknown', not imputed)
- Found and merged 80 near-duplicate customer records (same company, different formatting/capitalization) — kept the earliest customer_id, remapped their related records in subscriptions/usage/tickets
- customers: 4080 raw rows -> 4000 clean rows

- plans: no cleaning needed (clean lookup table)

- Parsed subscriptions.start_date: 900 ambiguous dates flagged (day-first default)
- subscriptions: 4564 rows -> 4564 rows (customer_id remapped for merged duplicates)

- Converted 45289 string-formatted amounts (e.g. '$1,234.00') to numeric
- Flagged 701 outlier invoices (amount >5x or <0.2x the expected plan price) for review
- invoices: 45289 rows -> 45289 rows

- usage_monthly: cleaned and re-aggregated after duplicate-customer merge -> 60496 rows

- support_tickets: 5744 rows (NULL resolved_date kept as-is = still open, not an error)
