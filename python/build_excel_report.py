"""
YouWe CRM — Build the Step 5 Excel deliverable
------------------------------------------------
Builds monthly_business_review.xlsx with:
  - PivotSource: aggregated month x plan_tier x channel x country data,
    ready for YOU to build a real PivotTable on in Excel
  - Cancellations: month-level cancellation counts/MRR (raw data)
  - Monthly_Summary: formula-driven rollup (SUMIFS/INDEX/MATCH against
    the two data sheets above — recalculates if the data changes)
  - Monthly_Business_Review: one-pager KPI dashboard with a month
    dropdown (data validation), INDEX/MATCH-driven KPI cards,
    conditional formatting, and a trend chart

Run:
    python build_excel_report.py
Then recalc it (see STEP5_README.md) before opening in Excel.
"""

import pandas as pd
import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import CellIsRule, ColorScaleRule
from openpyxl.chart import LineChart, Reference
from openpyxl.utils import get_column_letter

IN_DIR = "clean_data"
SNAPSHOT = pd.Timestamp("2025-12-31")

# ============================================================
# Load and prep data (same logic as the SQL/Python analysis)
# ============================================================
customers = pd.read_csv(f"{IN_DIR}/clean_customers.csv", parse_dates=["signup_date"])
plans = pd.read_csv(f"{IN_DIR}/clean_plans.csv")
subs = pd.read_csv(f"{IN_DIR}/clean_subscriptions.csv", parse_dates=["start_date", "end_date"])

subs = subs.merge(plans, on="plan_id")
subs["mrr"] = np.where(
    subs["billing_cycle"] == "monthly", subs["monthly_price"], (subs["annual_price"] / 12).round(2)
)
subs = subs.merge(customers[["customer_id", "country", "acquisition_channel"]], on="customer_id")

# expand each subscription into active months using the SAME "active-at-
# month-start" convention as the Step 3 SQL customer_month_mrr view
# (start_date <= month_start AND (end_date IS NULL OR end_date >= month_start)).
# Note: this deliberately does NOT match Query 3's active_customers_by_month
# CTE, which uses DATE_TRUNC/generate_series (an "any overlap with the
# month" convention) — that inconsistency between Query 2 and Query 3 in
# Step 3 is a known, documented limitation (see STEP5_README.md), not
# something silently reconciled here. This script matches Query 2 specifically
# since that's the number being cross-checked against.
all_month_starts = pd.period_range(subs["start_date"].min(), SNAPSHOT, freq="M").to_timestamp()

rows = []
for _, s in subs.iterrows():
    qualifying_months = [m for m in all_month_starts if s["start_date"] <= m and (pd.isna(s["end_date"]) or s["end_date"] >= m)]
    channel = s["acquisition_channel"] if pd.notna(s["acquisition_channel"]) else "Unknown"
    for m in qualifying_months:
        rows.append((
            m, s["tier"], channel,
            s["country"], s["mrr"], s["customer_id"]
        ))
active_df = pd.DataFrame(rows, columns=["month", "plan_tier", "acquisition_channel", "country", "mrr", "customer_id"])

# ============================================================
# PivotSource: aggregated, ready for a real Excel PivotTable
# ============================================================
pivot_source = (
    active_df.groupby(["month", "plan_tier", "acquisition_channel", "country"])
    .agg(mrr=("mrr", "sum"), active_customers=("customer_id", "nunique"))
    .reset_index()
    .sort_values(["month", "plan_tier", "acquisition_channel", "country"])
)

# ============================================================
# Cancellations: month-level, raw data
# ============================================================
cancelled = subs[subs["status"] == "cancelled"].copy()
cancelled["cancel_month"] = cancelled["end_date"].dt.to_period("M").dt.to_timestamp()
cancellations = (
    cancelled.groupby("cancel_month")
    .agg(customers_cancelled=("customer_id", "nunique"), churned_mrr=("mrr", "sum"))
    .reset_index()
    .rename(columns={"cancel_month": "month"})
    .sort_values("month")
)

# full month list for the summary sheet
all_months = pd.period_range(active_df["month"].min(), active_df["month"].max(), freq="M").to_timestamp()

print(f"PivotSource: {len(pivot_source)} rows")
print(f"Cancellations: {len(cancellations)} rows")
print(f"Months: {len(all_months)}")


# ============================================================
# Build the workbook
# ============================================================
wb = Workbook()

FONT = "Arial"
HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
HEADER_FONT = Font(name=FONT, bold=True, color="FFFFFF")
TITLE_FONT = Font(name=FONT, bold=True, size=16)
LABEL_FONT = Font(name=FONT, size=10, color="666666")
KPI_FONT = Font(name=FONT, bold=True, size=20)
thin = Side(style="thin", color="CCCCCC")
BOX_BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)


def style_header_row(ws, row, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center")


# ---- Sheet 1: PivotSource ----
ws1 = wb.active
ws1.title = "PivotSource"
headers1 = ["month", "plan_tier", "acquisition_channel", "country", "mrr", "active_customers"]
ws1.append(headers1)
style_header_row(ws1, 1, len(headers1))
for _, r in pivot_source.iterrows():
    ws1.append([r["month"], r["plan_tier"], r["acquisition_channel"], r["country"], round(r["mrr"], 2), int(r["active_customers"])])
ws1.column_dimensions["A"].width = 12
for col in "BCDEF":
    ws1.column_dimensions[col].width = 18
ws1.cell(row=1, column=1).comment = None
ws1.freeze_panes = "A2"
for row in ws1.iter_rows(min_row=2, min_col=1, max_col=1):
    row[0].number_format = "mmm-yyyy"

# ---- Sheet 2: Cancellations ----
ws2 = wb.create_sheet("Cancellations")
headers2 = ["month", "customers_cancelled", "churned_mrr"]
ws2.append(headers2)
style_header_row(ws2, 1, len(headers2))
for _, r in cancellations.iterrows():
    ws2.append([r["month"], int(r["customers_cancelled"]), round(r["churned_mrr"], 2)])
ws2.column_dimensions["A"].width = 12
ws2.column_dimensions["B"].width = 20
ws2.column_dimensions["C"].width = 16
ws2.freeze_panes = "A2"
for row in ws2.iter_rows(min_row=2, min_col=1, max_col=1):
    row[0].number_format = "mmm-yyyy"

# ---- Sheet 3: Monthly_Summary (all formulas) ----
ws3 = wb.create_sheet("Monthly_Summary")
headers3 = ["Month", "Total_MRR", "Active_Customers", "Customers_Cancelled", "Churned_MRR", "Logo_Churn_Rate", "MoM_Growth_Pct"]
ws3.append(headers3)
style_header_row(ws3, 1, len(headers3))

n_pivot_rows = len(pivot_source) + 1
n_cancel_rows = len(cancellations) + 1

for i, m in enumerate(all_months):
    r = i + 2
    ws3.cell(row=r, column=1, value=m.to_pydatetime()).number_format = "mmm-yyyy"
    ws3.cell(row=r, column=2, value=f"=ROUND(SUMIFS(PivotSource!$E$2:$E${n_pivot_rows},PivotSource!$A$2:$A${n_pivot_rows},A{r}),2)")
    ws3.cell(row=r, column=3, value=f"=SUMIFS(PivotSource!$F$2:$F${n_pivot_rows},PivotSource!$A$2:$A${n_pivot_rows},A{r})")
    ws3.cell(row=r, column=4, value=f"=IFERROR(INDEX(Cancellations!$B$2:$B${n_cancel_rows},MATCH(A{r},Cancellations!$A$2:$A${n_cancel_rows},0)),0)")
    ws3.cell(row=r, column=5, value=f"=IFERROR(INDEX(Cancellations!$C$2:$C${n_cancel_rows},MATCH(A{r},Cancellations!$A$2:$A${n_cancel_rows},0)),0)")
    ws3.cell(row=r, column=6, value=f"=IFERROR(D{r}/C{r},0)").number_format = "0.0%"
    if i == 0:
        ws3.cell(row=r, column=7, value="")
    else:
        ws3.cell(row=r, column=7, value=f"=IFERROR((B{r}-B{r-1})/B{r-1},\"\")").number_format = "0.0%"

for col, width in zip("ABCDEFG", [12, 14, 16, 18, 14, 14, 14]):
    ws3.column_dimensions[col].width = width
ws3.freeze_panes = "A2"

last_row = len(all_months) + 1

# conditional formatting: data bars-ish via color scale on churn rate, MRR growth
ws3.conditional_formatting.add(
    f"F2:F{last_row}",
    ColorScaleRule(start_type="min", start_color="63BE7B", end_type="max", end_color="F8696B"),
)
ws3.conditional_formatting.add(
    f"G2:G{last_row}",
    ColorScaleRule(start_type="min", start_color="F8696B", end_type="max", end_color="63BE7B"),
)

# ---- Sheet 4: Monthly_Business_Review (the one-pager) ----
ws4 = wb.create_sheet("Monthly_Business_Review")
ws4.sheet_view.showGridLines = False
for col, width in zip("ABCDEFG", [4, 22, 22, 22, 22, 4, 4]):
    ws4.column_dimensions[col].width = width

ws4["B2"] = "YouWe CRM — Monthly Business Review"
ws4["B2"].font = TITLE_FONT
ws4["B3"] = "Select a month below — every figure on this page updates automatically."
ws4["B3"].font = LABEL_FONT

ws4["B5"] = "Reporting Month:"
ws4["B5"].font = Font(name=FONT, bold=True)
ws4["C5"] = all_months[-1].to_pydatetime()
ws4["C5"].number_format = "mmm-yyyy"
ws4["C5"].fill = PatternFill("solid", fgColor="FFF2CC")
ws4["C5"].border = BOX_BORDER
ws4["C5"].font = Font(name=FONT, bold=True)

dv = DataValidation(type="list", formula1=f"=Monthly_Summary!$A$2:$A${last_row}", allow_blank=False)
ws4.add_data_validation(dv)
dv.add(ws4["C5"])

# KPI cards
kpi_defs = [
    ("Total MRR", f'=INDEX(Monthly_Summary!$B$2:$B${last_row},MATCH($C$5,Monthly_Summary!$A$2:$A${last_row},0))', '"$"#,##0'),
    ("Active Customers", f'=INDEX(Monthly_Summary!$C$2:$C${last_row},MATCH($C$5,Monthly_Summary!$A$2:$A${last_row},0))', '#,##0'),
    ("Logo Churn Rate", f'=INDEX(Monthly_Summary!$F$2:$F${last_row},MATCH($C$5,Monthly_Summary!$A$2:$A${last_row},0))', '0.0%'),
    ("MoM MRR Growth", f'=INDEX(Monthly_Summary!$G$2:$G${last_row},MATCH($C$5,Monthly_Summary!$A$2:$A${last_row},0))', '0.0%'),
]
kpi_cols = ["B", "C", "D", "E"]
for col, (label, formula, fmt) in zip(kpi_cols, kpi_defs):
    ws4[f"{col}7"] = label
    ws4[f"{col}7"].font = LABEL_FONT
    cell = ws4[f"{col}8"]
    cell.value = formula
    cell.number_format = fmt
    cell.font = KPI_FONT
    cell.border = BOX_BORDER
    cell.alignment = Alignment(horizontal="left")
    ws4.merge_cells(f"{col}8:{col}9")

# conditional formatting on the KPI cards themselves
ws4.conditional_formatting.add("D8:D9", CellIsRule(operator="greaterThan", formula=["0.05"], fill=PatternFill("solid", fgColor="F8696B")))
ws4.conditional_formatting.add("D8:D9", CellIsRule(operator="lessThanOrEqual", formula=["0.05"], fill=PatternFill("solid", fgColor="C6E0B4")))
ws4.conditional_formatting.add("E8:E9", CellIsRule(operator="lessThan", formula=["0"], fill=PatternFill("solid", fgColor="F8696B")))
ws4.conditional_formatting.add("E8:E9", CellIsRule(operator="greaterThanOrEqual", formula=["0"], fill=PatternFill("solid", fgColor="C6E0B4")))

ws4["B11"] = "MRR Trend (Jan 2023 – Dec 2025)"
ws4["B11"].font = Font(name=FONT, bold=True, size=12)

# small hidden helper table feeding the chart (references Monthly_Summary directly, chart needs a sheet range)
chart = LineChart()
chart.title = None
chart.y_axis.title = "Total MRR ($)"
chart.x_axis.title = "Month"
chart.height = 8
chart.width = 18
data_ref = Reference(ws3, min_col=2, min_row=1, max_row=last_row)
cats_ref = Reference(ws3, min_col=1, min_row=2, max_row=last_row)
chart.add_data(data_ref, titles_from_data=True)
chart.set_categories(cats_ref)
ws4.add_chart(chart, "B12")

ws4["B30"] = "Source: PivotSource + Cancellations sheets (raw data) → Monthly_Summary (formulas) → this page (INDEX/MATCH on selected month)."
ws4["B30"].font = Font(name=FONT, size=9, italic=True, color="999999")

ws4.print_area = "A1:H32"
ws4.page_setup.orientation = "landscape"
ws4.page_setup.fitToWidth = 1
ws4.page_setup.fitToHeight = 1
ws4.sheet_properties.pageSetUpPr.fitToPage = True

wb.active = wb.sheetnames.index("Monthly_Business_Review")

wb.save("monthly_business_review.xlsx")
print("\nSaved monthly_business_review.xlsx")
