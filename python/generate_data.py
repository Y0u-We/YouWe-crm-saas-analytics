"""
YouWe CRM — Synthetic SaaS Dataset Generator
------------------------------------------------
Generates a realistic, DELIBERATELY MESSY multi-table dataset simulating
a B2B SaaS company's customer/subscription/billing/usage/support data.

Why messy on purpose: the point of this project is to demonstrate real
data-cleaning skill, not to analyze a dataset that's already clean.
Every "flaw" below is commented so you can describe it in your
documentation as something you found and fixed.

Output: 6 CSV files written to ./raw_data/
    customers.csv
    plans.csv
    subscriptions.csv
    invoices.csv
    usage_monthly.csv
    support_tickets.csv

Run:
    python generate_data.py
"""

import os
import random
import numpy as np
import pandas as pd
from faker import Faker
from datetime import timedelta

fake = Faker()
Faker.seed(42)
random.seed(42)
np.random.seed(42)

OUT_DIR = "raw_data"
os.makedirs(OUT_DIR, exist_ok=True)

N_CUSTOMERS = 4000
START_DATE = pd.Timestamp("2023-01-01")
END_DATE = pd.Timestamp("2025-12-31")

# ---------------------------------------------------------------------
# 1. PLANS (small clean lookup table — this one should NOT be messy;
#    real reference/lookup tables in a company are usually clean)
# ---------------------------------------------------------------------
plans = pd.DataFrame([
    {"plan_id": 1, "plan_name": "Starter",      "tier": "Starter",      "monthly_price": 29,  "annual_price": 290},
    {"plan_id": 2, "plan_name": "Professional",  "tier": "Professional", "monthly_price": 79,  "annual_price": 790},
    {"plan_id": 3, "plan_name": "Enterprise",    "tier": "Enterprise",   "monthly_price": 199, "annual_price": 1990},
])
plans.to_csv(f"{OUT_DIR}/plans.csv", index=False)

# ---------------------------------------------------------------------
# 2. CUSTOMERS (messy: inconsistent country names, missing values,
#    mixed date formats, a handful of near-duplicate rows)
# ---------------------------------------------------------------------
COUNTRY_VARIANTS = {
    "United States": ["United States", "USA", "US", "U.S.A"],
    "United Kingdom": ["United Kingdom", "UK", "U.K.", "Britain"],
    "India": ["India", "IN", "Bharat"],
    "Australia": ["Australia", "AUS", "AU"],
    "Canada": ["Canada", "CA"],
}
COUNTRIES = list(COUNTRY_VARIANTS.keys())
COUNTRY_WEIGHTS = [0.40, 0.20, 0.20, 0.10, 0.10]

SIZE_BANDS = ["1-10", "11-50", "51-200", "201-1000", "1000+"]
SIZE_WEIGHTS = [0.35, 0.30, 0.20, 0.10, 0.05]

CHANNELS = ["Google Ads", "Meta Ads", "LinkedIn Ads", "Organic Search", "Referral", "Direct"]
CHANNEL_WEIGHTS = [0.25, 0.15, 0.15, 0.20, 0.15, 0.10]

DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%b-%Y", "%m/%d/%Y"]


def messy_date(ts):
    """Return the date as a string in a randomly chosen real-world format."""
    fmt = random.choice(DATE_FORMATS)
    return ts.strftime(fmt)


def random_signup_date():
    days_range = (END_DATE - START_DATE).days
    return START_DATE + timedelta(days=random.randint(0, days_range))


customers = []
for i in range(1, N_CUSTOMERS + 1):
    country_clean = random.choices(COUNTRIES, weights=COUNTRY_WEIGHTS)[0]
    country_display = random.choice(COUNTRY_VARIANTS[country_clean])  # messy variant
    signup_ts = random_signup_date()

    company_size = random.choices(SIZE_BANDS, weights=SIZE_WEIGHTS)[0]
    channel = random.choices(CHANNELS, weights=CHANNEL_WEIGHTS)[0]

    # inject missingness (~6% company_size, ~8% acquisition_channel)
    if random.random() < 0.06:
        company_size = np.nan
    if random.random() < 0.08:
        channel = np.nan

    customers.append({
        "customer_id": i,
        "company_name":fake.unique.company(),
        "country": country_display,
        "company_size_band": company_size,
        "signup_date": messy_date(signup_ts),
        "acquisition_channel": channel,
    })

customers_df = pd.DataFrame(customers)

# Inject ~2% near-duplicate rows (same real company, new customer_id,
# slightly different name formatting — a classic dedup problem)
dupe_sample = customers_df.sample(frac=0.02, random_state=1).copy()
dupe_sample["customer_id"] = range(N_CUSTOMERS + 1, N_CUSTOMERS + 1 + len(dupe_sample))
def mangle_name(name):
    variants = [name.upper(), name.lower(), name + " ", " " + name, name.replace("LLC", "L.L.C.")]
    return random.choice(variants)
dupe_sample["company_name"] = dupe_sample["company_name"].apply(mangle_name)
customers_df = pd.concat([customers_df, dupe_sample], ignore_index=True)

customers_df.to_csv(f"{OUT_DIR}/customers.csv", index=False)

# ---------------------------------------------------------------------
# 3. SUBSCRIPTIONS (models cancel -> resubscribe patterns so churn
#    isn't a clean one-way state; tier loosely correlated with size)
# ---------------------------------------------------------------------
def pick_plan_for_size(size_band):
    if size_band in ("1-10", "11-50") or pd.isna(size_band):
        return random.choices([1, 2, 3], weights=[0.6, 0.35, 0.05])[0]
    elif size_band == "51-200":
        return random.choices([1, 2, 3], weights=[0.25, 0.55, 0.20])[0]
    else:
        return random.choices([1, 2, 3], weights=[0.05, 0.35, 0.60])[0]


subscriptions = []
sub_id = 1
for _, cust in customers_df.iterrows():
    try:
        signup = pd.to_datetime(cust["signup_date"], dayfirst=False, errors="coerce")
        if pd.isna(signup):
            signup = pd.to_datetime(cust["signup_date"], dayfirst=True, errors="coerce")
    except Exception:
        signup = START_DATE
    if pd.isna(signup):
        signup = START_DATE

    plan_id = pick_plan_for_size(cust["company_size_band"])
    billing_cycle = random.choices(["monthly", "annual"], weights=[0.7, 0.3])[0]

    # decide overall fate: still active, churned once, or churned + resubscribed
    fate = random.choices(["active", "churned", "churned_resub"], weights=[0.55, 0.30, 0.15])[0]

    cur_start = signup
    if fate == "active":
        subscriptions.append([sub_id, cust["customer_id"], plan_id, cur_start, pd.NaT, billing_cycle, "active"])
        sub_id += 1
    elif fate == "churned":
        tenure_days = int(np.random.exponential(scale=240)) + 30
        end = cur_start + timedelta(days=tenure_days)
        if end > END_DATE:
            end = END_DATE
            status = "active"
        else:
            status = "cancelled"
        subscriptions.append([sub_id, cust["customer_id"], plan_id, cur_start, end if status == "cancelled" else pd.NaT, billing_cycle, status])
        sub_id += 1
    else:  # churned then resubscribed
        tenure_days = int(np.random.exponential(scale=150)) + 20
        end1 = cur_start + timedelta(days=tenure_days)
        if end1 >= END_DATE:
            subscriptions.append([sub_id, cust["customer_id"], plan_id, cur_start, pd.NaT, billing_cycle, "active"])
            sub_id += 1
        else:
            subscriptions.append([sub_id, cust["customer_id"], plan_id, cur_start, end1, billing_cycle, "cancelled"])
            sub_id += 1
            gap_days = random.randint(10, 120)
            start2 = end1 + timedelta(days=gap_days)
            if start2 < END_DATE:
                new_plan = pick_plan_for_size(cust["company_size_band"])
                subscriptions.append([sub_id, cust["customer_id"], new_plan, start2, pd.NaT, billing_cycle, "active"])
                sub_id += 1

subs_df = pd.DataFrame(subscriptions, columns=[
    "subscription_id", "customer_id", "plan_id", "start_date", "end_date", "billing_cycle", "status"
])
# messy date formatting on start_date only (end_date left ISO/blank — mixing is realistic:
# different source systems format dates differently)
subs_df["start_date"] = subs_df["start_date"].apply(lambda d: messy_date(pd.Timestamp(d)))
subs_df.to_csv(f"{OUT_DIR}/subscriptions.csv", index=False)

# ---------------------------------------------------------------------
# 4. INVOICES (messy: amount stored as string with currency symbols/
#    commas for a subset, a handful of clear data-entry outliers,
#    occasional failed payments)
# ---------------------------------------------------------------------
plan_lookup = plans.set_index("plan_id")

invoices = []
inv_id = 1
for _, sub in subs_df.iterrows():
    start = pd.to_datetime(sub["start_date"], errors="coerce", dayfirst=False)
    if pd.isna(start):
        start = pd.to_datetime(sub["start_date"], errors="coerce", dayfirst=True)
    if pd.isna(start):
        continue
    end = sub["end_date"] if pd.notna(sub["end_date"]) else END_DATE
    end = pd.to_datetime(end)

    price = plan_lookup.loc[sub["plan_id"], "monthly_price"] if sub["billing_cycle"] == "monthly" else plan_lookup.loc[sub["plan_id"], "annual_price"]
    step = pd.DateOffset(months=1) if sub["billing_cycle"] == "monthly" else pd.DateOffset(years=1)

    cur = start
    while cur <= end and cur <= END_DATE:
        amount = float(price)

        # ~1.5% chance of a data-entry outlier
        if random.random() < 0.015:
            amount = amount * random.choice([0.01, 100])

        # ~10% chance amount is stored messily as a string
        amount_out = amount
        if random.random() < 0.10:
            amount_out = f"${amount:,.2f}"

        payment_status = random.choices(["paid", "failed", "refunded"], weights=[0.93, 0.05, 0.02])[0]

        invoices.append({
            "invoice_id": inv_id,
            "subscription_id": sub["subscription_id"],
            "invoice_date": messy_date(cur) if random.random() < 0.5 else cur.strftime("%Y-%m-%d"),
            "amount": amount_out,
            "payment_status": payment_status,
        })
        inv_id += 1
        cur = cur + step

invoices_df = pd.DataFrame(invoices)
invoices_df.to_csv(f"{OUT_DIR}/invoices.csv", index=False)

# ---------------------------------------------------------------------
# 5. USAGE (monthly aggregated — an event-level log would be huge;
#    aggregated-to-month is realistic and keeps this analyzable.
#    Usage trends DOWN in the months before a churned subscription ends,
#    so there's a real signal to find in the analysis phase.)
# ---------------------------------------------------------------------
usage_rows = []
for _, sub in subs_df.iterrows():
    start = pd.to_datetime(sub["start_date"], errors="coerce", dayfirst=False)
    if pd.isna(start):
        start = pd.to_datetime(sub["start_date"], errors="coerce", dayfirst=True)
    if pd.isna(start):
        continue
    end = sub["end_date"] if pd.notna(sub["end_date"]) else END_DATE
    end = pd.to_datetime(end)
    months = pd.period_range(start, end, freq="M")
    n_months = len(months)
    base_logins = np.random.randint(8, 40)

    for idx, m in enumerate(months):
        if sub["status"] == "cancelled" and idx >= n_months - 3:
            months_before_end = (n_months - 1) - idx
            decay = 0.25 + 0.25 * months_before_end
            decay = max(decay, 0.1)
        else:
            decay = 1.0
        logins = max(0, int(np.random.normal(base_logins * decay, 4)))
        feature_uses = max(0, int(np.random.normal(base_logins * decay * 0.6, 3)))
        usage_rows.append({
            "customer_id": sub["customer_id"],
            "month": str(m),
            "login_count": logins,
            "feature_usage_count": feature_uses,
        })

usage_df = pd.DataFrame(usage_rows)
usage_df.to_csv(f"{OUT_DIR}/usage_monthly.csv", index=False)

# ---------------------------------------------------------------------
# 6. SUPPORT TICKETS (0-5 per customer, occasional missing resolved_date
#    for still-open tickets — a real and meaningful NULL, not an error)
# ---------------------------------------------------------------------
CATEGORIES = ["Billing", "Bug Report", "Feature Request", "Onboarding", "Login Issue"]
PRIORITIES = ["Low", "Medium", "High", "Urgent"]

tickets = []
tick_id = 1
for cid in customers_df["customer_id"]:
    n_tickets = random.choices([0, 1, 2, 3, 4, 5], weights=[0.35, 0.25, 0.18, 0.12, 0.07, 0.03])[0]
    for _ in range(n_tickets):
        created = random_signup_date()
        priority = random.choices(PRIORITIES, weights=[0.4, 0.35, 0.18, 0.07])[0]
        resolved_days = int(np.random.exponential(scale=4)) + 1
        resolved = created + timedelta(days=resolved_days)
        still_open = random.random() < 0.05
        tickets.append({
            "ticket_id": tick_id,
            "customer_id": cid,
            "created_date": created.strftime("%Y-%m-%d"),
            "resolved_date": np.nan if still_open else resolved.strftime("%Y-%m-%d"),
            "priority": priority,
            "category": random.choice(CATEGORIES),
        })
        tick_id += 1

tickets_df = pd.DataFrame(tickets)
tickets_df.to_csv(f"{OUT_DIR}/support_tickets.csv", index=False)

# ---------------------------------------------------------------------
print("Done. Files written to ./raw_data/")
print(f"customers:        {len(customers_df):,} rows")
print(f"plans:            {len(plans):,} rows")
print(f"subscriptions:    {len(subs_df):,} rows")
print(f"invoices:         {len(invoices_df):,} rows")
print(f"usage_monthly:    {len(usage_df):,} rows")
print(f"support_tickets:  {len(tickets_df):,} rows")
