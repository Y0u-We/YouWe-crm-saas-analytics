"""
YouWe CRM — Data Cleaning Script
------------------------------------------------
Cleans the messy raw CSVs from generate_data.py into a shape that
loads cleanly into schema.sql. Every cleaning decision is commented —
these comments are exactly what you should describe in your project
documentation / README / interview answers.

Input:  ./raw_data/*.csv
Output: ./clean_data/*.csv   (ready for \\copy into PostgreSQL)
        ./clean_data/cleaning_log.md  (summary of what was fixed)

Run:
    python clean_data.py
"""

import os
import re
import pandas as pd
import numpy as np

RAW_DIR = "raw_data"
OUT_DIR = "clean_data"
os.makedirs(OUT_DIR, exist_ok=True)

log_lines = ["# Data Cleaning Log\n"]


def log(msg):
    print(msg)
    log_lines.append(f"- {msg}")


# ============================================================
# 1. CUSTOMERS
# ============================================================
customers = pd.read_csv(f"{RAW_DIR}/customers.csv")
n_start = len(customers)

# --- 1a. Standardize country names ---
# Decision: map every observed variant to one canonical country name.
# In a real job you'd build this map by running .unique() on the raw
# column and eyeballing it once — that's exactly how this list was built.
COUNTRY_MAP = {
    "usa": "United States", "us": "United States", "u.s.a": "United States",
    "united states": "United States",
    "uk": "United Kingdom", "u.k.": "United Kingdom", "britain": "United Kingdom",
    "united kingdom": "United Kingdom",
    "india": "India", "in": "India", "bharat": "India",
    "australia": "Australia", "aus": "Australia", "au": "Australia",
    "canada": "Canada", "ca": "Canada",
}
before = customers["country"].nunique()
customers["country"] = customers["country"].astype(str).str.strip().str.lower().map(COUNTRY_MAP)
after_unmapped = customers["country"].isna().sum()
log(f"Standardized country names: {before} raw variants -> {customers['country'].nunique()} canonical countries "
    f"({after_unmapped} rows didn't match the map and need review)")

# --- 1b. Parse mixed date formats in signup_date ---
def parse_messy_date(s):
    """Handles the 4 formats used across this dataset:
    %Y-%m-%d, %d/%m/%Y, %m/%d/%Y, %d-%b-%Y (e.g. 13-Sep-2023).
    Returns (parsed_date, was_ambiguous) — ambiguous means a slash-date
    where both day-first and month-first interpretations are valid
    calendar dates (e.g. 03/04/2023), which is a genuine real-world
    problem you can only resolve with more context (e.g. knowing the
    source system's locale). We default ambiguous cases to day-first
    (non-US convention) since most of this customer base is non-US,
    and flag them so they're auditable rather than silently guessed.
    """
    s = str(s).strip()
    # ISO format
    try:
        return pd.Timestamp(pd.to_datetime(s, format="%Y-%m-%d")), False
    except (ValueError, TypeError):
        pass
    # Day-Month(name)-Year, e.g. 13-Sep-2023 — unambiguous, has a month name
    try:
        return pd.Timestamp(pd.to_datetime(s, format="%d-%b-%Y")), False
    except (ValueError, TypeError):
        pass
    # Slash format — ambiguous between d/m/Y and m/d/Y
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", s)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        a_valid = a <= 31 and b <= 12          # a/b as day/month
        b_valid = b <= 31 and a <= 12          # a/b as month/day
        if a_valid and not b_valid:
            return pd.Timestamp(year=y, month=b, day=a), False
        elif b_valid and not a_valid:
            return pd.Timestamp(year=y, month=a, day=b), False
        elif a_valid and b_valid:
            return pd.Timestamp(year=y, month=b, day=a), True   # ambiguous -> day-first default, flagged
    return pd.NaT, False


parsed = customers["signup_date"].apply(parse_messy_date)
customers["signup_date"] = parsed.apply(lambda x: x[0])
customers["signup_date_ambiguous"] = parsed.apply(lambda x: x[1])
n_ambig = customers["signup_date_ambiguous"].sum()
n_failed = customers["signup_date"].isna().sum()
log(f"Parsed signup_date across 4 mixed formats: {n_ambig} ambiguous day/month dates flagged "
    f"(defaulted to day-first), {n_failed} failed to parse")

# --- 1c. Missing values ---
# Decision: NULL company_size_band and acquisition_channel are left as
# genuine NULLs (not filled with a fake "Unknown" string) — for this
# analysis, "we don't know the channel" is a real and important state,
# and coding it as a fake category would quietly bias channel-level
# churn/CLV comparisons.
n_missing_size = customers["company_size_band"].isna().sum()
n_missing_channel = customers["acquisition_channel"].isna().sum()
log(f"Left {n_missing_size} missing company_size_band and {n_missing_channel} missing "
    f"acquisition_channel as NULL (documented as a real 'unknown', not imputed)")

# --- 1d. De-duplicate near-identical customers ---
def normalize_name(name):
    name = str(name).lower().strip()
    name = re.sub(r"[.\-,]", "", name)
    name = re.sub(r"\bl\.?l\.?c\.?\b", "llc", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name

customers["_norm_name"] = customers["company_name"].apply(normalize_name)
dupe_groups = customers.groupby("_norm_name")["customer_id"].apply(list)
id_remap = {}  # duplicate_customer_id -> canonical_customer_id
for ids in dupe_groups:
    if len(ids) > 1:
        canonical = min(ids)
        for dup_id in ids:
            if dup_id != canonical:
                id_remap[dup_id] = canonical

n_dupes = len(id_remap)
customers_clean = customers[~customers["customer_id"].isin(id_remap.keys())].copy()
customers_clean = customers_clean.drop(columns=["_norm_name"])
log(f"Found and merged {n_dupes} near-duplicate customer records (same company, different "
    f"formatting/capitalization) — kept the earliest customer_id, remapped their related "
    f"records in subscriptions/usage/tickets")

customers_clean.to_csv(f"{OUT_DIR}/clean_customers.csv", index=False)
log(f"customers: {n_start} raw rows -> {len(customers_clean)} clean rows\n")


def remap_customer_id(cid):
    return id_remap.get(cid, cid)


# ============================================================
# 2. PLANS (already clean — copy through)
# ============================================================
plans = pd.read_csv(f"{RAW_DIR}/plans.csv")
plans.to_csv(f"{OUT_DIR}/clean_plans.csv", index=False)
log("plans: no cleaning needed (clean lookup table)\n")

# ============================================================
# 3. SUBSCRIPTIONS
# ============================================================
subs = pd.read_csv(f"{RAW_DIR}/subscriptions.csv")
n_start = len(subs)

subs["customer_id"] = subs["customer_id"].apply(remap_customer_id)

parsed = subs["start_date"].apply(parse_messy_date)
subs["start_date"] = parsed.apply(lambda x: x[0])
n_ambig = parsed.apply(lambda x: x[1]).sum()
log(f"Parsed subscriptions.start_date: {n_ambig} ambiguous dates flagged (day-first default)")

subs["end_date"] = pd.to_datetime(subs["end_date"], errors="coerce")

subs.to_csv(f"{OUT_DIR}/clean_subscriptions.csv", index=False)
log(f"subscriptions: {n_start} rows -> {len(subs)} rows (customer_id remapped for merged duplicates)\n")

# ============================================================
# 4. INVOICES
# ============================================================
invoices = pd.read_csv(f"{RAW_DIR}/invoices.csv")
n_start = len(invoices)


def clean_amount(val):
    """Strips $ and , from string-formatted amounts, e.g. '$1,234.00' -> 1234.00"""
    if isinstance(val, str):
        cleaned = val.replace("$", "").replace(",", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return np.nan
    return float(val)


n_string_amounts = invoices["amount"].apply(lambda v: isinstance(v, str)).sum()
invoices["amount"] = invoices["amount"].apply(clean_amount)
log(f"Converted {n_string_amounts} string-formatted amounts (e.g. '$1,234.00') to numeric")

# --- Outlier detection ---
# Decision: an invoice is flagged as an outlier if its amount is more than
# 5x or less than 1/5th of the median amount for its subscription's plan.
# Flagged rows are kept but marked (is_outlier=True) rather than silently
# dropped or corrected — in a real job you'd escalate these to Finance
# rather than guess the "right" number yourself.
plan_lookup2 = plans.set_index("plan_id")
sub_to_plan = subs.set_index("subscription_id")["plan_id"]
sub_to_cycle = subs.set_index("subscription_id")["billing_cycle"]

def expected_price(row):
    plan_id = sub_to_plan.get(row["subscription_id"])
    cycle = sub_to_cycle.get(row["subscription_id"])
    if plan_id is None:
        return np.nan
    return plan_lookup2.loc[plan_id, "monthly_price" if cycle == "monthly" else "annual_price"]

invoices["_expected_price"] = invoices.apply(expected_price, axis=1)
invoices["is_outlier"] = (
    (invoices["amount"] > invoices["_expected_price"] * 5) |
    (invoices["amount"] < invoices["_expected_price"] * 0.2)
)
n_outliers = invoices["is_outlier"].sum()
log(f"Flagged {n_outliers} outlier invoices (amount >5x or <0.2x the expected plan price) for review")
invoices = invoices.drop(columns=["_expected_price"])

invoices["invoice_date"] = invoices["invoice_date"].apply(lambda x: parse_messy_date(x)[0])

invoices.to_csv(f"{OUT_DIR}/clean_invoices.csv", index=False)
log(f"invoices: {n_start} rows -> {len(invoices)} rows\n")

# ============================================================
# 5. USAGE_MONTHLY
# ============================================================
usage = pd.read_csv(f"{RAW_DIR}/usage_monthly.csv")
usage["customer_id"] = usage["customer_id"].apply(remap_customer_id)
usage["usage_month"] = pd.to_datetime(usage["month"], format="%Y-%m").dt.to_period("M").dt.to_timestamp()
usage = usage.drop(columns=["month"])
# a customer merged from a duplicate can now have two usage rows for the
# same month (one from each of their original customer_ids) — sum them
usage = usage.groupby(["customer_id", "usage_month"], as_index=False).agg(
    login_count=("login_count", "sum"),
    feature_usage_count=("feature_usage_count", "sum"),
)
usage.to_csv(f"{OUT_DIR}/clean_usage_monthly.csv", index=False)
log(f"usage_monthly: cleaned and re-aggregated after duplicate-customer merge -> {len(usage)} rows\n")

# ============================================================
# 6. SUPPORT_TICKETS
# ============================================================
tickets = pd.read_csv(f"{RAW_DIR}/support_tickets.csv")
tickets["customer_id"] = tickets["customer_id"].apply(remap_customer_id)
tickets["created_date"] = pd.to_datetime(tickets["created_date"], errors="coerce")
tickets["resolved_date"] = pd.to_datetime(tickets["resolved_date"], errors="coerce")
tickets.to_csv(f"{OUT_DIR}/clean_support_tickets.csv", index=False)
log(f"support_tickets: {len(tickets)} rows (NULL resolved_date kept as-is = still open, not an error)\n")

# ============================================================
with open(f"{OUT_DIR}/cleaning_log.md", "w") as f:
    f.write("\n".join(log_lines))

print("\nDone. Clean files written to ./clean_data/")
