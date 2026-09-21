# Case Study: SaaS Churn, Retention & Revenue Analytics
### YouWe CRM - End-to-End Data Analyst Project

---

## The Problem

A B2B SaaS company (simulated as "YouWe CRM" for this project) was growing new customer acquisition, but revenue growth was lagging behind signup growth. Leadership suspected churn and weak expansion revenue were quietly offsetting new business gains - but Finance, Customer Success, and Product each reported slightly different churn and retention numbers, with no single source of truth. This is one of the most common cross-functional data problems in subscription businesses, and exactly the kind of ambiguity a Data Analyst is hired to resolve.

## The Approach

Built the full pipeline end to end, each layer chosen for a specific reason:

1. **Python** - generated a realistic, deliberately messy multi-table dataset (4,000 customers, inconsistent country names, mixed date formats, string-formatted currency, near-duplicate records) rather than using a pre-cleaned dataset, to genuinely practice data cleaning
2. **PostgreSQL** - designed a normalized relational schema (customers, subscriptions, plans, invoices, usage, support tickets) and cleaned the data into it, documenting every cleaning decision (standardized country names, parsed 4 date formats, de-duplicated 80 near-identical customer records, flagged 701 outlier invoices for review rather than silently "fixing" them)
3. **SQL** - wrote the core analysis: MRR waterfall, churn rate, cohort retention, customer lifetime value (CLV), and Net Revenue Retention (NRR), using CTEs, window functions, and CASE-based classification
4. **Python (EDA)** - built supporting visualizations (cohort heatmap, usage-decline trend, missingness/outlier charts) and cross-validated every number against the SQL output
5. **Excel** - built a pivot-ready data source and a formula-driven Monthly Business Review one-pager with conditional formatting, cross-checked against the SQL MRR figures
6. **Power BI** - modeled a star schema (customer/plan dimensions, 5 fact tables) and built a 5-page executive dashboard with 12 DAX measures, validated against every prior layer

**A deliberate practice throughout: cross-checking every number across tools rather than trusting any single calculation.** This caught several real, non-trivial bugs before they reached the final numbers - including a Python cohort-retention masking error, a backwards usage-decay formula in the synthetic data generator, an inconsistency between two SQL queries using different definitions of "active this month," a right-censoring bug that would have shown a false 100% churn rate for the most recent month, and a Power BI auto-hierarchy bug that silently blended three years of cohorts together by month name. Each was found by comparing results across tools rather than trusting any single number in isolation, and each is documented rather than hidden.

## Key Insights

- **Net Revenue Retention: 90.5%** over the trailing 12 months - below the 100%+ threshold that signals a healthy, expanding customer base. This is the headline finding: growth is being partially offset by churn and contraction.
- **Logo churn rate improved substantially over time** - from roughly 4-5% monthly in early 2023 down to 1.4-2% by late 2025 - a genuinely positive trend worth investigating further to understand and reinforce what's driving it.
- **12-month cohort retention holds in a 71-84% range** (average 77.8%) across cohorts old enough to measure - a steady, gradual decline rather than a single bad cohort or launch problem.
- **CLV varies meaningfully, and counterintuitively, by acquisition channel**: Google Ads customers show the highest average lifetime value ($2,222), while Referral customers - often assumed to be highest-value - show the lowest ($1,619).
- **Usage decline is a genuine, usable early-warning signal**: customers who churn show login activity dropping from ~24/month to ~7/month in their final month before cancelling - a pattern strong enough to build a real "at-risk customer" alert list from.
- **~7% of customers have no recorded acquisition channel** - a real data-quality gap in the acquisition-tracking pipeline, not just a modeling inconvenience, worth fixing at the source.

## Recommendations

1. **Deploy a usage-based early-warning system** for Customer Success - the revenue-at-risk query already identifies currently-active customers with usage down more than 50% from their trailing average, ranked by MRR exposure, ready to route to outreach.
2. **Investigate and codify what's driving the churn-rate improvement** since 2023 - whatever changed (onboarding, pricing, support) is working, and understanding it prevents accidentally reversing it.
3. **Revisit marketing spend allocation** toward higher-CLV channels (Google Ads, Meta Ads) rather than assuming referral traffic is automatically highest-value - the data doesn't support that assumption here.
4. **Fix acquisition-channel tracking** so the ~7% "Unknown" gap shrinks - better attribution data directly improves every channel-level decision above it.

## Estimated Business Impact

At the current active base (~$212K MRR, 90.5% NRR), closing just the gap to 100% NRR - i.e., fully offsetting churn and contraction with expansion revenue from the existing customer base - would represent roughly **$20K/month in retained-and-recovered revenue**, before accounting for any new-customer growth at all. Even a partial improvement (e.g., halfway to 100% NRR) is a concrete, board-reportable target tied directly to the retention work above.

---

*Full technical documentation, including every SQL query, Python script, and the exact bugs found and fixed at each stage, is available in the project repository README files (Steps 1-6).*
