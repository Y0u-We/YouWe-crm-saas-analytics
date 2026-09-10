# Step 5: Excel — YouWe CRM SaaS Dataset

## What's in `monthly_business_review.xlsx`

| Sheet | What it is | Purpose |
|---|---|---|
| `PivotSource` | 3,500 rows: month x plan tier x acquisition channel x country, with summed MRR and active customer counts | **Raw data — build a real PivotTable on this yourself** (see below) |
| `Cancellations` | 35 rows: month-level cancellation counts and churned MRR | Raw data, feeds the churn rate formula |
| `Monthly_Summary` | 36 rows, one per month, entirely formulas (`SUMIFS`, `INDEX`/`MATCH`) referencing the two sheets above | The "rollup" layer — recalculates automatically if you ever regenerate the underlying data |
| `Monthly_Business_Review` | The one-pager: a month dropdown, 4 KPI cards, an MRR trend chart | What you'd actually hand a stakeholder |

## Build a real PivotTable yourself (this is the actual Excel skill to practice)

I deliberately did **not** auto-generate a PivotTable in this file — building one yourself is the real, demonstrable skill, and it takes 2 minutes:

1. Click anywhere inside the `PivotSource` sheet's data
2. Insert → PivotTable → OK (default "New Worksheet" is fine)
3. Drag `month` to **Rows**
4. Drag `plan_tier` or `acquisition_channel` to **Columns**
5. Drag `mrr` to **Values** (it should default to Sum — if not, click the field → Value Field Settings → Sum)
6. You now have a live cross-tab of MRR by month and by segment — try swapping `plan_tier` for `country` to see it update instantly

This is worth a screenshot for your case study, and worth being able to rebuild from scratch out loud in an interview.

## Using the Monthly_Business_Review dropdown

Click cell C5 ("Reporting Month") — it's a dropdown (Data Validation) listing all 36 months. Pick any month and all 4 KPI cards and their conditional formatting (green/red) update immediately via `INDEX`/`MATCH` — nothing is hardcoded.

## Two real bugs found while building this (worth knowing for your write-up)

### Bug 1: A Python `or` gotcha silently dropped ~7% of rows
`row["acquisition_channel"] or "Unknown"` looks like a reasonable way to fill in missing values — but in Python, `NaN or "Unknown"` evaluates to `NaN`, not `"Unknown"`, because `NaN` is truthy. Left uncorrected, those `NaN` group keys got silently dropped by `pandas.groupby()` (which excludes `NaN` keys by default), understating total MRR by about 7%. Fixed with an explicit `pd.notna()` check instead of relying on `or`.

### Bug 2: Three different definitions of "active this month" were in use across the project
This is the more interesting one. Cross-checking Excel's December 2025 MRR against the validated Step 3 SQL figure ($212,181) surfaced a real discrepancy — and tracking it down found that **Step 3's own SQL file uses two different conventions internally**:
- `Query 2` (the MRR waterfall) counts a subscription as active in a month only if it started **on or before the 1st** of that month
- `Query 3` (the churn rate) counts a subscription as active in a month if it **overlaps that month at all** (via `DATE_TRUNC`/`generate_series`)

These produce different numbers for months with a lot of new signups, since a subscription that starts on, say, December 29th counts as "active in December" under Query 3's definition but not Query 2's. This Excel workbook was rebuilt to match Query 2's convention specifically (since that's the number being cross-checked), and now matches SQL exactly.

**This inconsistency between Query 2 and Query 3 has not been fixed in the Step 3 SQL file** — reconciling it would mean picking one convention and rewriting both queries, which is a reasonable next step but wasn't done here to avoid re-triggering another full pipeline rebuild. **This is genuinely worth mentioning in an interview** — noticing and articulating a real methodological inconsistency between two of your own queries is a stronger signal than pretending everything lined up perfectly the first time.

### Known minor limitation: Active_Customers is ~0.9% overcounted
44 customers in the dataset have two simultaneously-overlapping subscriptions (a minor Step 1 data-generation artifact — the cancel/resubscribe logic occasionally produces a small overlap instead of a clean gap). Where those two subscriptions differ in plan tier, this workbook's `active_customers` figure counts that customer twice (3,003 shown vs. 2,976 true unique customers for December 2025). The MRR figures are unaffected — this only touches the secondary customer-count metric.

## Next step

Step 6 is Power BI — the star-schema model and executive dashboard. Before starting it, decide (and document) which "active this month" convention you're standardizing on, since Power BI's DAX measures will need to pick one too, and it should match whichever you choose to reconcile Query 2/3 to, if you do.
