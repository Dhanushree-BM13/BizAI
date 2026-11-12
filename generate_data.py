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

-- Each company: one value per month, oldest first
insert into public.financials (company, industry, date, revenue, expenses, project_success)
select c.company, c.industry, (date '{start}' + (m.i - 1) * interval '1 month')::date, m.r, m.e, m.s
from (values
""".replace("{start}", MONTHS[0].strftime("%Y-%m-%d"))


def to_sql(data):
    """The table, its security rules and the demo rows as one SQL script.

    Each company is one line holding its monthly values as arrays, which Postgres unpacks
    into rows. This keeps the script short enough to paste into the Supabase SQL Editor.
    """
    quote = lambda text: "'" + str(text).replace("'", "''") + "'"
    array = lambda values: "'{" + ",".join(format(v, "g") for v in values) + "}'"
    lines = []
    for company, rows in data.groupby("Company", sort=False):
        lines.append(f"({quote(company)},{quote(rows.Industry.iloc[0])},{array(rows.Revenue_INR_Cr)},"
                     f"{array(rows.Expenses_INR_Cr)},{array(rows.Project_Success_Rate_Pct)})")
    return (SCHEMA + ",\n".join(lines) +
            "\n) as c(company, industry, rev, exp, succ)\n"
            "cross join lateral unnest(c.rev::numeric[], c.exp::numeric[], c.succ::numeric[]) with ordinality as m(r, e, s, i)\n"
            "on conflict (company, date) do update set industry = excluded.industry, revenue = excluded.revenue,\n"
            "  expenses = excluded.expenses, project_success = excluded.project_success;\n")


if __name__ == "__main__":
    folder = Path(__file__).parent
    data = build()
    data.to_csv(folder / "financial_data.csv", index=False)
    (folder / "supabase_setup.sql").write_text(to_sql(data), encoding="utf-8")
    print(f"Wrote financial_data.csv and supabase_setup.sql in {folder}")
