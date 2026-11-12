"""Builds the demo dataset, financial_data.csv.

Every company name and every figure here is invented. Run `python generate_data.py`
to rebuild the file; the fixed seed makes the output identical each time.
"""
from pathlib import Path

import numpy as np
import pandas as pd

MONTHS = pd.date_range(end="2026-10-01", periods=60, freq="MS")  # five years, up to the last full month

# name, industry, starting revenue (Rs crore), monthly growth, seasonal swing,
# starting profit margin, monthly change in margin
COMPANIES = [
    ("Aravali Energy", "Energy", 7200, 0.006, 0.05, 0.15, 0.0),
    ("Nilgiri Infotech", "IT Services", 1950, 0.010, 0.03, 0.24, 0.0),
    ("Kaveri Systems", "IT Services", 1300, 0.008, 0.03, 0.21, -0.001),
    ("Sahyadri Cloud", "Technology", 4500, 0.015, 0.02, 0.28, 0.0),
    ("Surya Kiran Solar", "Renewable Energy", 11.4, 0.018, 0.08, 0.17, 0.0),
    ("Vindhya Consulting", "Consulting", 820, -0.004, 0.04, 0.12, -0.001),
    ("Konkan Retail", "Retail", 640, 0.005, 0.12, 0.09, 0.0),
    ("Godavari Pharma", "Pharmaceuticals", 2100, 0.009, 0.03, 0.22, 0.0),
    ("Deccan Motors", "Automobile", 5600, 0.004, 0.07, 0.11, 0.0),
    ("Malabar Foods", "FMCG", 1500, 0.007, 0.06, 0.14, 0.0),
    ("Ganga Textiles", "Textiles", 430, -0.002, 0.09, 0.08, -0.0008),
    ("Himadri Cement", "Cement", 3200, 0.005, 0.10, 0.16, 0.0),
    ("Narmada Finserv", "Financial Services", 2700, 0.012, 0.02, 0.26, 0.0),
    ("Thar Logistics", "Logistics", 960, 0.008, 0.05, 0.10, 0.0005),
    ("Chenab Telecom", "Telecom", 6400, 0.003, 0.02, 0.13, -0.0005),
    ("Brahmaputra Steel", "Steel", 8900, 0.004, 0.06, 0.12, -0.0004),
    ("Kanchenjunga Hotels", "Hospitality", 380, 0.011, 0.18, 0.18, 0.0),
    ("Mahanadi Power", "Power Utilities", 5200, 0.005, 0.07, 0.19, 0.0),
    ("Tapti Chemicals", "Chemicals", 1750, 0.006, 0.04, 0.15, -0.0006),
    ("Satpura Agritech", "Agriculture", 290, 0.013, 0.20, 0.11, 0.0),
    ("Kaziranga Airways", "Aviation", 4100, 0.009, 0.14, 0.05, 0.0004),
    ("Palghat Paints", "Paints", 1150, 0.008, 0.08, 0.17, 0.0),
    ("Shivalik Realty", "Real Estate", 960, 0.003, 0.10, 0.21, -0.0012),
    ("Mysuru Silks", "Textiles", 145, 0.006, 0.15, 0.13, 0.0),
    ("Indus Bank Tech", "Fintech", 520, 0.020, 0.02, 0.09, 0.002),
    ("Coromandel Fertilisers", "Fertilisers", 2400, 0.004, 0.16, 0.10, 0.0),
    ("Nalanda EdTech", "Education", 210, 0.016, 0.12, 0.14, -0.0015),
    ("Sundarban Seafoods", "Food Exports", 330, 0.007, 0.11, 0.08, 0.0),
    ("Ajanta Healthcare", "Hospitals", 1350, 0.010, 0.03, 0.16, 0.0),
    ("Garuda Aerospace", "Defence", 1900, 0.012, 0.04, 0.20, 0.0),
    ("Chambal Tyres", "Auto Components", 1600, 0.005, 0.06, 0.11, 0.0),
    ("Lonavala Media", "Media", 470, -0.006, 0.08, 0.10, -0.001),
    ("Kutch Salt Works", "Commodities", 95, 0.004, 0.13, 0.07, 0.0),
    ("Vaigai Electronics", "Electronics", 2850, 0.014, 0.05, 0.09, 0.0006),
    ("Hampi Gaming", "Gaming", 120, 0.022, 0.06, 0.24, -0.002),
    ("Rann Wind Energy", "Renewable Energy", 640, 0.017, 0.12, 0.26, 0.0),
    ("Periyar Rubber", "Rubber", 410, -0.003, 0.09, 0.09, -0.0005),
    ("Darjeeling Tea Estates", "Plantations", 180, 0.002, 0.25, 0.12, 0.0),
    ("Bengaluru Biotech", "Biotechnology", 760, 0.015, 0.03, 0.18, 0.0),
    ("Mumbai Insure", "Insurance", 3600, 0.009, 0.02, 0.14, 0.0),
]


def build(seed=7):
    rng = np.random.default_rng(seed)
    t = np.arange(len(MONTHS))
    season = np.sin(2 * np.pi * (MONTHS.month.to_numpy() - 3) / 12)
    rows = []
    for name, industry, start, growth, swing, margin, drift in COMPANIES:
        revenue = start * (1 + growth) ** t * (1 + swing * season) * rng.normal(1, 0.012, len(t))
        expenses = revenue * (1 - margin - drift * t) * rng.normal(1, 0.008, len(t))
        success = np.clip(rng.normal(91, 2.5, len(t)), 82, 98)
        # Three unusual months per company, so the anomaly detector has something to find.
        for month in rng.choice(np.arange(3, len(t)), size=3, replace=False):
            if rng.random() < 0.5:
                expenses[month] *= rng.uniform(1.12, 1.20)  # cost overrun
            else:
                revenue[month] *= rng.uniform(0.86, 0.90)  # revenue dip
            success[month] -= rng.uniform(12, 18)
        for i, date in enumerate(MONTHS):
            rows.append({
                "Date": date.strftime("%Y-%m-%d"), "Company": name, "Industry": industry,
                "Revenue_INR_Cr": round(revenue[i], 2), "Expenses_INR_Cr": round(expenses[i], 2),
                "Project_Success_Rate_Pct": round(success[i], 1),
            })
    return pd.DataFrame(rows)


def to_seed_sql(data):
    """The demo data as SQL for supabase/seed.sql. Run supabase/schema.sql first.

    Each company is one line holding its monthly values as arrays, which Postgres unpacks
    into rows. The companies are inserted (or updated) first, then their months.
    Safe to run again: existing rows are updated, not duplicated.
    """
    quote = lambda text: "'" + str(text).replace("'", "''") + "'"
    array = lambda values: "'{" + ",".join(format(v, "g") for v in values) + "}'"
    lines = [f"  ({quote(company)}, {quote(rows.Industry.iloc[0])},\n   {array(rows.Revenue_INR_Cr)},\n"
             f"   {array(rows.Expenses_INR_Cr)},\n   {array(rows.Project_Success_Rate_Pct)})"
             for company, rows in data.groupby("Company", sort=False)]
    start = data.Date.min()
    return f"""-- BizAI demo data: {len(lines)} invented companies, monthly from {start}.
-- Run supabase/schema.sql first. Safe to run again.
with data (company, industry, revenue, expenses, success) as (values
{",\n".join(lines)}
),
saved_companies as (
  insert into public.companies (name, industry)
  select company, industry from data
  on conflict (name) do update set industry = excluded.industry
  returning id, name
)
insert into public.monthly_financials (company_id, month, revenue, expenses, project_success)
select saved_companies.id,
       (date '{start}' + (m.n - 1) * interval '1 month')::date,
       m.revenue, m.expenses, m.success
from data
join saved_companies on saved_companies.name = data.company
cross join lateral unnest(data.revenue::numeric[], data.expenses::numeric[], data.success::numeric[])
  with ordinality as m (revenue, expenses, success, n)
on conflict (company_id, month) do update
  set revenue = excluded.revenue, expenses = excluded.expenses, project_success = excluded.project_success;
"""


if __name__ == "__main__":
    folder = Path(__file__).parent
    data = build()
    data.to_csv(folder / "financial_data.csv", index=False)
    (folder / "supabase" / "seed.sql").write_text(to_seed_sql(data), encoding="utf-8")
    print(f"Wrote financial_data.csv and supabase/seed.sql in {folder}")
