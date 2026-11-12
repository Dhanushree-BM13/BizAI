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


SCHEMA = """-- BizAI: run this once in the Supabase SQL Editor. Safe to run again.
create table if not exists public.financials (
  id bigint generated always as identity primary key,
  company text not null,
  industry text not null default 'Uploaded data',
  date date not null,
  revenue numeric not null check (revenue > 0),
  expenses numeric not null check (expenses >= 0),
  project_success numeric,
  unique (company, date)
);

-- Anyone may read. Nobody may write through the public API; edit rows in the Supabase dashboard.
alter table public.financials enable row level security;
drop policy if exists "Anyone can read financials" on public.financials;
create policy "Anyone can read financials" on public.financials for select to anon, authenticated using (true);

-- Send changes to the dashboard as they happen.
do $$ begin
  alter publication supabase_realtime add table public.financials;
exception when duplicate_object then null;
end $$;

insert into public.financials (company, industry, date, revenue, expenses, project_success) values
"""


def to_sql(data):
    """The table, its security rules and the demo rows as one SQL script."""
    quote = lambda text: "'" + str(text).replace("'", "''") + "'"
    values = ",\n".join(
        f"({quote(r.Company)}, {quote(r.Industry)}, {quote(r.Date)}, {r.Revenue_INR_Cr}, {r.Expenses_INR_Cr}, {r.Project_Success_Rate_Pct})"
        for r in data.itertuples())
    return (SCHEMA + values + "\non conflict (company, date) do update set industry = excluded.industry, "
            "revenue = excluded.revenue, expenses = excluded.expenses, project_success = excluded.project_success;\n")


if __name__ == "__main__":
    folder = Path(__file__).parent
    data = build()
    data.to_csv(folder / "financial_data.csv", index=False)
    (folder / "supabase_setup.sql").write_text(to_sql(data), encoding="utf-8")
    print(f"Wrote financial_data.csv and supabase_setup.sql in {folder}")
