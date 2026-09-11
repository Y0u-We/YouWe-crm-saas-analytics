# Step 3: SQL Analysis - YouWe CRM SaaS Dataset

## What's in this step

- `analysis_queries.sql` - 7 queries/views, already tested against the real dataset (see results below)

## Install PostgreSQL (Windows)

1. Download from postgresql.org/download/windows - get the installer, run it.
2. During setup, set a password for the `postgres` user (you'll need it constantly - write it down).
3. Keep the default port (5432).
4. It installs **pgAdmin** alongside - that's the GUI you'll use to run these queries.

## Create the database and load your data

Open pgAdmin, connect with your password, then open a **Query Tool** on a new database:

1. Right-click Databases → Create → Database → name it `youwe_crm`
2. Open a Query Tool on `youwe_crm`, paste in your `schema.sql`, run it
3. Run these six lines one at a time (adjust the path to wherever your `clean_data` folder is - use forward slashes even on Windows, pgAdmin handles it):

```sql
\copy customers        FROM 'C:/Users/HP/Downloads/YouWe-crm-analytics/clean_data/clean_customers.csv'        CSV HEADER;
\copy plans             FROM 'C:/Users/HP/Downloads/YouWe-crm-analytics/clean_data/clean_plans.csv'             CSV HEADER;
\copy subscriptions     FROM 'C:/Users/HP/Downloads/YouWe-crm-analytics/clean_data/clean_subscriptions.csv'     CSV HEADER;
\copy invoices          FROM 'C:/Users/HP/Downloads/YouWe-crm-analytics/clean_data/clean_invoices.csv'          CSV HEADER;
\copy usage_monthly     FROM 'C:/Users/HP/Downloads/YouWe-crm-analytics/clean_data/clean_usage_monthly.csv'     CSV HEADER;
\copy support_tickets   FROM 'C:/Users/HP/Downloads/YouWe-crm-analytics/clean_data/clean_support_tickets.csv'   CSV HEADER;
```

`\copy` only works in the pgAdmin Query Tool or `psql` - it's a client command, not real SQL, so it won't work if you try to run it any other way.

Expected row counts after loading: customers 4000, plans 3, subscriptions 4564, invoices 45289, usage_monthly 60496, support_tickets 5744.

## Run the analysis

Open `analysis_queries.sql` in the pgAdmin Query Tool and run each numbered section one at a time (not all at once - some are `SELECT`s meant to be inspected individually, not just executed in bulk).

## What the analysis actually found (already run and verified - use these numbers in your case study)

- **Net Revenue Retention: 90.5%** over the trailing 12 months - below the 100%+ that indicates a healthy, expanding customer base. This is the headline finding: growth is being partially offset by churn and contraction, exactly the ambiguous signal the business problem describes.
- **Logo churn rate declined from ~4-5% monthly in 2023 down to ~1.6-2% by late 2025** - worth flagging as a positive trend, likely worth investigating *why* (better onboarding? pricing changes?) as a follow-up question.
- **CLV varies meaningfully by acquisition channel**: Google Ads customers average $2,222 lifetime value vs. $1,619 for Referral - the opposite of what you'd often expect (referrals are usually assumed to be higher-value). This is a genuinely interesting, slightly counterintuitive finding worth highlighting - and it's the natural bridge back to your ads/marketing background in an interview.
- **Cohort retention at the 12-month mark holds in the 71-84% range** (average 77.8%) across the 24 cohorts old enough to measure - a steady, gradual decline rather than one bad cohort or a sharp cliff.
- The **revenue-at-risk query** surfaces a concrete, actionable list: 20 currently-active customers with usage down 53-100% from their trailing average, worth $79-199/month each - this is exactly the kind of list a Customer Success team would want emailed to them weekly.

## Next step

Step 4 is Python: EDA and visualizations that make these same findings visual (cohort heatmap, usage-decline distribution), plus the optional lightweight churn-risk scoring. After that, Excel validation, then Power BI.
