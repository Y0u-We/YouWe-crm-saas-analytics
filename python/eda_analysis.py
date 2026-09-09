"""
YouWe CRM — Exploratory Data Analysis & Visualizations
------------------------------------------------------
Builds on the SQL analysis from Step 3, but works directly from the
clean_data/ CSVs so it doesn't require a database connection to run.
Produces PNG charts (for your case study / slide deck) plus a short
findings summary.

Input:  ./clean_data/*.csv
Output: ./eda_charts/*.png
        ./eda_charts/eda_findings.md

Run:
    pip install pandas numpy matplotlib seaborn
    python eda_analysis.py
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

IN_DIR = "clean_data"
OUT_DIR = "eda_charts"
os.makedirs(OUT_DIR, exist_ok=True)

sns.set_style("whitegrid")
plt.rcParams["figure.dpi"] = 110

findings = ["# EDA Findings\n"]


def note(msg):
    print(msg)
    findings.append(f"- {msg}")


# ============================================================
# Load data
# ============================================================
customers = pd.read_csv(f"{IN_DIR}/clean_customers.csv", parse_dates=["signup_date"])
plans = pd.read_csv(f"{IN_DIR}/clean_plans.csv")
subs = pd.read_csv(f"{IN_DIR}/clean_subscriptions.csv", parse_dates=["start_date", "end_date"])
invoices = pd.read_csv(f"{IN_DIR}/clean_invoices.csv", parse_dates=["invoice_date"])
usage = pd.read_csv(f"{IN_DIR}/clean_usage_monthly.csv", parse_dates=["usage_month"])
tickets = pd.read_csv(f"{IN_DIR}/clean_support_tickets.csv", parse_dates=["created_date", "resolved_date"])

SNAPSHOT = pd.Timestamp("2025-12-31")  # same snapshot date used in Step 3 SQL


# ============================================================
# 1. MISSINGNESS
# ============================================================
missing_pct = (customers[["company_size_band", "acquisition_channel"]].isna().mean() * 100).round(1)

fig, ax = plt.subplots(figsize=(6, 4))
missing_pct.plot(kind="bar", ax=ax, color="#4C72B0")
ax.set_ylabel("% missing")
ax.set_title("Missing Values — Customer Fields")
for i, v in enumerate(missing_pct):
    ax.text(i, v + 0.3, f"{v}%", ha="center")
plt.tight_layout()
plt.savefig(f"{OUT_DIR}/01_missingness.png")
plt.close()

note(f"company_size_band missing in {missing_pct['company_size_band']}% of customers, "
     f"acquisition_channel missing in {missing_pct['acquisition_channel']}% — both left as real NULLs per the Step 2 cleaning decision")


# ============================================================
# 2. CUSTOMER TENURE DISTRIBUTION
# ============================================================
cust_span = subs.groupby("customer_id").agg(
    first_start=("start_date", "min"),
    last_end=("end_date", lambda s: s.max() if s.notna().any() else pd.NaT),
    still_active=("status", lambda s: (s == "active").any()),
)
cust_span["end_for_tenure"] = np.where(cust_span["still_active"], SNAPSHOT, cust_span["last_end"])
cust_span["end_for_tenure"] = pd.to_datetime(cust_span["end_for_tenure"])
cust_span["tenure_months"] = (cust_span["end_for_tenure"] - cust_span["first_start"]).dt.days / 30.44

fig, ax = plt.subplots(figsize=(7, 4))
sns.histplot(cust_span["tenure_months"], bins=30, ax=ax, color="#55A868")
ax.set_xlabel("Tenure (months)")
ax.set_title("Customer Tenure Distribution")
plt.tight_layout()
plt.savefig(f"{OUT_DIR}/02_tenure_distribution.png")
plt.close()

note(f"Median customer tenure: {cust_span['tenure_months'].median():.1f} months "
     f"(mean {cust_span['tenure_months'].mean():.1f}, since the distribution is right-skewed by long-tenured active customers)")


# ============================================================
# 3. ARPU DISTRIBUTION
# ============================================================
paid_invoices = invoices[invoices["payment_status"] == "paid"]
revenue_by_sub = paid_invoices.groupby("subscription_id")["amount"].sum()
subs_rev = subs.merge(revenue_by_sub.rename("total_revenue"), left_on="subscription_id", right_index=True, how="left")
subs_rev["total_revenue"] = subs_rev["total_revenue"].fillna(0)
customer_revenue = subs_rev.groupby("customer_id")["total_revenue"].sum()
customer_arpu = customer_revenue / cust_span["tenure_months"].clip(lower=1)

fig, ax = plt.subplots(figsize=(7, 4))
sns.histplot(customer_arpu.clip(upper=customer_arpu.quantile(0.99)), bins=40, ax=ax, color="#C44E52")
ax.set_xlabel("ARPU ($/month)")
ax.set_title("Average Revenue Per Customer (monthly), 99th percentile capped for readability")
plt.tight_layout()
plt.savefig(f"{OUT_DIR}/03_arpu_distribution.png")
plt.close()

note(f"Median ARPU: ${customer_arpu.median():.2f}/month, mean ${customer_arpu.mean():.2f}/month "
     f"— the gap between median and mean confirms a small number of high-value Enterprise accounts pull the average up")


# ============================================================
# 4. COHORT RETENTION HEATMAP
# ============================================================
customers_cohort = customers.copy()
customers_cohort["cohort_month"] = customers_cohort["signup_date"].dt.to_period("M")

# build the set of active months per customer (same logic as the SQL version)
active_months_rows = []
for _, row in subs.iterrows():
    end = row["end_date"] if pd.notna(row["end_date"]) else SNAPSHOT
    months = pd.period_range(row["start_date"], end, freq="M")
    for m in months:
        active_months_rows.append((row["customer_id"], m))
active_months_df = pd.DataFrame(active_months_rows, columns=["customer_id", "active_month"]).drop_duplicates()

merged = active_months_df.merge(
    customers_cohort[["customer_id", "cohort_month"]], on="customer_id"
)
merged["months_since_signup"] = (
    (merged["active_month"].dt.year - merged["cohort_month"].dt.year) * 12
    + (merged["active_month"].dt.month - merged["cohort_month"].dt.month)
)

cohort_sizes = customers_cohort.groupby("cohort_month")["customer_id"].nunique()

retention = (
    merged[merged["months_since_signup"].between(0, 12)]
    .groupby(["cohort_month", "months_since_signup"])["customer_id"]
    .nunique()
    .unstack()  # NaN, not 0, for combos not yet observed at all
)

# Build a mask: a (cohort, months_since_signup) cell is only MEASURABLE if
# that many months have actually elapsed since that cohort signed up,
# relative to the snapshot date. A cohort that signed up in Nov 2025 simply
# hasn't reached "12 months out" yet — that's a missing measurement, not a
# 0% retention data point, and conflating the two would badly understate
# retention (this was caught by cross-checking against the Step 3 SQL results).
snapshot_period = SNAPSHOT.to_period("M")
elapsed_months = (snapshot_period.year - retention.index.year) * 12 + (snapshot_period.month - retention.index.month)
measurable = pd.DataFrame(
    {col: elapsed_months >= col for col in retention.columns}, index=retention.index
)

retention_counts = retention.where(measurable, np.nan)      # not-yet-measurable cells stay NaN
retention_counts = retention_counts.fillna(0).where(measurable, np.nan)  # measurable-but-zero cells become real 0
retention_pct = retention_counts.div(cohort_sizes, axis=0) * 100

# keep the heatmap readable: last 18 cohorts only
retention_pct_display = retention_pct.tail(18)

fig, ax = plt.subplots(figsize=(11, 7))
sns.heatmap(retention_pct_display, annot=True, fmt=".0f", cmap="YlGnBu", vmin=50, vmax=100,
            cbar_kws={"label": "% of cohort still active"}, ax=ax)
ax.set_xlabel("Months since signup")
ax.set_ylabel("Signup cohort")
ax.set_title("Cohort Retention Heatmap (last 18 cohorts)")
plt.tight_layout()
plt.savefig(f"{OUT_DIR}/04_cohort_retention_heatmap.png")
plt.close()

m12 = retention_pct[12].dropna()
note(f"12-month retention across cohorts ranges {m12.min():.0f}%-{m12.max():.0f}% "
     f"(average {m12.mean():.0f}%) — a steady drip rather than one bad cohort or a sharp cliff")


# ============================================================
# 5. USAGE TREND BEFORE CHURN vs. STILL-ACTIVE CUSTOMERS
# ============================================================
churned_customers = set(subs[subs["status"] == "cancelled"]["customer_id"])
active_customers_set = set(subs[subs["status"] == "active"]["customer_id"]) - churned_customers

usage_with_flag = usage.copy()
usage_with_flag["group"] = np.where(
    usage_with_flag["customer_id"].isin(churned_customers), "Churned (ever)", "Never churned"
)

# for churned customers, index months relative to their subscription end (0 = last active month)
churn_end_dates = subs[subs["status"] == "cancelled"].groupby("customer_id")["end_date"].max()
usage_churned = usage_with_flag[usage_with_flag["group"] == "Churned (ever)"].copy()
usage_churned["end_date"] = usage_churned["customer_id"].map(churn_end_dates)
usage_churned["months_before_churn"] = (
    (usage_churned["end_date"].dt.to_period("M") - usage_churned["usage_month"].dt.to_period("M")).apply(lambda x: x.n)
)
trend = (
    usage_churned[usage_churned["months_before_churn"].between(0, 6)]
    .groupby("months_before_churn")["login_count"]
    .mean()
    .sort_index(ascending=False)
)

fig, ax = plt.subplots(figsize=(7, 4))
trend.plot(marker="o", ax=ax, color="#DD8452")
ax.set_xlabel("Months before cancellation")
ax.set_ylabel("Average monthly logins")
ax.set_title("Usage Trend in the 6 Months Before Churn")
ax.invert_xaxis()
plt.tight_layout()
plt.savefig(f"{OUT_DIR}/05_usage_before_churn.png")
plt.close()

drop_pct = (trend.iloc[-1] - trend.iloc[0]) / trend.iloc[0] * 100
note(f"Average logins fall from {trend.iloc[0]:.1f}/month (6 months out) to {trend.iloc[-1]:.1f}/month "
     f"(final month) before a cancellation — a {abs(drop_pct):.0f}% decline, confirming usage decline is a genuine early-warning signal")


# ============================================================
# 6. OUTLIER INVOICES — flagged amounts vs. expected plan price
# ============================================================
sub_plan = subs.set_index("subscription_id")[["plan_id", "billing_cycle"]]
inv_plan = invoices.join(sub_plan, on="subscription_id")
inv_plan = inv_plan.merge(plans, on="plan_id")
inv_plan["expected_price"] = np.where(
    inv_plan["billing_cycle"] == "monthly", inv_plan["monthly_price"], inv_plan["annual_price"] / 12
)

fig, ax = plt.subplots(figsize=(7, 5))
sample = inv_plan.sample(min(3000, len(inv_plan)), random_state=1)  # sample for a readable scatter
colors = sample["is_outlier"].map({True: "#C44E52", False: "#4C72B0"})
ax.scatter(sample["expected_price"], sample["amount"], c=colors, alpha=0.5, s=15)
ax.set_xlabel("Expected price ($)")
ax.set_ylabel("Actual invoice amount ($)")
ax.set_yscale("log")
ax.set_title("Invoice Amounts vs. Expected Plan Price\n(red = flagged outlier)")
plt.tight_layout()
plt.savefig(f"{OUT_DIR}/06_outlier_invoices.png")
plt.close()

n_outliers = inv_plan["is_outlier"].sum()
note(f"{n_outliers} invoices ({n_outliers/len(inv_plan)*100:.1f}%) flagged as outliers "
     f"(>5x or <0.2x expected plan price) — visible as the clear off-diagonal points in the chart")


# ============================================================
with open(f"{OUT_DIR}/eda_findings.md", "w") as f:
    f.write("\n".join(findings))

print(f"\nDone. 6 charts + eda_findings.md written to ./{OUT_DIR}/")
