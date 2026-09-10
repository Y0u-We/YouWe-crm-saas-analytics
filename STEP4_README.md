# Step 4: Python EDA & Visualizations - YouWe CRM SaaS Dataset

## What's in this step

- `eda_analysis.py` - generates 6 charts + a findings summary from `clean_data/`
- `eda_charts.zip` - the 6 PNG charts, already generated and checked (see below)

## Two real bugs found and fixed while building this step

Cross-checking Python against the SQL results from Step 3 surfaced two genuine issues - worth understanding both, since "my numbers don't match across tools" is exactly the kind of discrepancy a real analyst has to run down, not ignore.

### Bug 1: Cohort retention was being computed wrong in Python (not SQL)
The first version of the cohort retention code treated "this cohort hasn't reached month 12 yet" the same as "this cohort's retention dropped to 0% at month 12" - which dragged the average down to 52% instead of the correct ~78%. Fixed by explicitly masking out combinations where not enough time has actually elapsed. **Your SQL queries from Step 3 were already correct** - this was purely a Python-side bug.

### Bug 2: The README's "75-98%" retention claim was an eyeballing error, not a real number
Once the Python bug above was fixed, Python and SQL still needed a side-by-side check to be sure they agreed - and they did: **71.3%-84.0%, average 77.8%**, across the 24 cohorts old enough to actually measure at 12 months. The original "75-98%" figure in `STEP3_README.md` was me misreading a scrolled terminal output that mixed several different months-since-signup values together. `STEP3_README.md` has been corrected - replace your copy with the updated one attached here.

### Bug 3: The usage-decay formula in generate_data.py was backwards
This one is a genuine data-generation bug from Step 1, not a documentation error. The formula that was supposed to make usage decline in the 3 months before a customer churns was actually doing the opposite in the middle - usage dipped hardest 3 months out, then partially *recovered* right before cancellation, which contradicts the "usage tapers off before churn" story the dataset is supposed to tell. **This required regenerating your raw data, re-cleaning it, and reloading PostgreSQL** - see the fix-it steps below.

## What you need to do to your local project

1. **Replace `python\generate_data.py`** with the version attached here (fixes the decay formula)
2. **Replace `sql\STEP3_README.md`** with the version attached here (fixes the 75-98% → 71-84% retention claim)
3. **Re-run the full data pipeline**, in this exact order:
   ```
   python python\generate_data.py
   python python\clean_data.py
   ```
4. **Reload PostgreSQL** with the corrected data:
   - In pgAdmin, run `TRUNCATE customers, plans, subscriptions, invoices, usage_monthly, support_tickets RESTART IDENTITY CASCADE;` first (clears the old data without dropping the tables)
   - Re-import all 6 CSVs the same way you did in Step 3 (Import/Export Data, in the same customers → plans → subscriptions → invoices → usage_monthly → support_tickets order)
5. **Add `eda_analysis.py`** to your `python\` folder
6. **Extract `eda_charts.zip`** into a new `eda_charts\` folder at your project root

## Running the EDA script yourself

```
pip install pandas numpy matplotlib seaborn
python python\eda_analysis.py
```

This reads directly from `clean_data\` (no database connection needed) and writes 6 PNGs plus `eda_findings.md` into `eda_charts\`.

## What the charts show (already verified - use in your case study)

1. **Missingness** - company_size_band (5.6%) and acquisition_channel (7.4%) missing, left as real NULLs
2. **Tenure distribution** - median 12.7 months, right-skewed by long-tenured active accounts
3. **ARPU distribution** - median $72.87/month vs. mean $257.59/month, confirming a small number of high-value accounts skew the average. Note: this includes the ~1.5% flagged outlier invoices at face value - worth mentioning as a documented limitation, not silently fixing.
4. **Cohort retention heatmap** - clean staircase pattern, 71-84% retained at 12 months
5. **Usage before churn** - a real, monotonic decline from ~24 logins/month down to ~7/month in the final month before cancellation (this is the chart that was broken and got fixed)
6. **Outlier invoices scatter** - 701 flagged points clearly visible off the main diagonal

## Next step

Step 5 is Excel: a quick pivot-table cross-check of the SQL MRR numbers, plus a one-page "Monthly Business Review" stakeholder summary.
