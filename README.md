# YouWe CRM — SaaS Churn, Retention & Revenue Analytics

An end-to-end data analyst project simulating a real B2B SaaS company's analytics stack — from a deliberately messy raw dataset through to an executive Power BI dashboard, with every number cross-validated across Python, SQL, Excel, and Power BI.

**[Read the full case study →](case_study.md)**

## The headline finding

Net Revenue Retention is **90.5%** — below the 100% threshold that separates healthy growth from a customer base that's quietly shrinking underneath new-customer acquisition. Full reasoning and supporting numbers are in the case study above.

## What this project demonstrates

- Designing a normalized relational database from raw, messy, multi-table data
- Advanced SQL (CTEs, window functions, cohort analysis) for real business questions — MRR movement, churn, retention, CLV
- Python for data generation, cleaning, and exploratory analysis
- Excel for pivot-table analysis and a formula-driven stakeholder report
- Power BI: star-schema modeling, DAX, and a 5-page executive dashboard
- **Cross-tool validation as a discipline, not an afterthought** — every headline number was checked against at least one other tool, and several real bugs were caught and fixed this way rather than shipped

## Project structure

```
├── case_study.md              ← Start here: the business case, findings, and recommendations
├── docs/
├── python/                     Data generation, cleaning, and EDA scripts
├── sql/                        Schema and analysis queries
├── excel/                      Monthly Business Review workbook
├── powerbi/                    Dashboard file and Power BI import queries
├── raw_data/                   Generated messy source data
└── clean_data/                 Cleaned, analysis-ready data
```

## Step-by-step build

Each step has its own README with the reasoning, the exact bugs found, and how they were fixed — not just the final polished result:

| Step | What it covers |
|---|---|
| [Step 1](STEP1_README.md) | Data design, ERD, and a deliberately messy synthetic dataset generator |
| [Step 2](STEP2_README.md) | Python data cleaning — country standardization, date parsing, de-duplication, outlier flagging |
| [Step 3](STEP3_README.md) | SQL analysis — MRR waterfall, churn, cohort retention, CLV, Net Revenue Retention |
| [Step 4](STEP4_README.md) | Python EDA and visualizations, including 3 real bugs found by cross-checking against SQL |
| [Step 5](STEP5_README.md) | Excel — pivot-ready data, a formula-driven Monthly Business Review one-pager |
| [Step 6](STEP6_README.md) | Power BI — star schema, DAX measures, 5-page executive dashboard |

## Tech stack

**Python** (pandas, NumPy, Faker, matplotlib, seaborn) · **PostgreSQL** · **SQL** (CTEs, window functions, CASE-based classification) · **Excel** (pivot tables, SUMIFS/INDEX-MATCH, conditional formatting) · **Power BI** (star schema, DAX, live database connection)

## Dashboard preview
 Executive Overview
 <img width="592" height="332" alt="Executive Overview" src="https://github.com/user-attachments/assets/00d2505c-82e8-4914-8e65-0f031fa6f1b3" />
 Revenue Waterfall
<img width="593" height="334" alt="Revenue Waterfall" src="https://github.com/user-attachments/assets/5596a71d-e718-4198-89f6-f8aa24189c9b" />
Churn and Retention
<img width="593" height="335" alt="Churn and Retention" src="https://github.com/user-attachments/assets/0a57e6ea-e246-47c7-bd4e-ac293b85a2d6" />
Customer Segments and CLV
<img width="594" height="336" alt="Customer Segments and CLV" src="https://github.com/user-attachments/assets/d5d5b1e8-c992-40f4-82b5-dec22f4a4409" />
Acquisition Channel Performance
<img width="593" height="336" alt="Acquisition Channel Performance" src="https://github.com/user-attachments/assets/2cb98407-d068-4917-aaf1-9954f62e8010" />


## Why this project exists

Built as a portfolio piece to demonstrate genuine end-to-end analyst work — not a single-tool exercise, but the same kind of cross-functional, multi-tool workflow a Data Analyst actually uses at an MNC: raw data in, a validated database and analysis in the middle, a business-ready dashboard and case study out the other end.
