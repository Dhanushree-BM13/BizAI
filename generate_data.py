"""Builds the demo dataset, financial_data.csv.

Every company name and every figure here is invented. Run `python generate_data.py`
to rebuild the file; the fixed seed makes the output identical each time.
"""
from pathlib import Path

import numpy as np
import pandas as pd

MONTHS = pd.date_range("2023-01-01", periods=36, freq="MS")

# name, industry, starting revenue (Rs crore), monthly growth, seasonal swing,
# starting profit margin, monthly change in margin
COMPANIES = [
    ("Aravali Energy", "Energy", 7200, 0.006, 0.05, 0.15, 0.0),
    ("Nilgiri Infotech", "IT Services", 1950, 0.010, 0.03, 0.24, 0.0),
    ("Kaveri Systems", "IT Services", 1300, 0.008, 0.03, 0.21, -0.001),
    ("Sahyadri Cloud", "Technology", 4500, 0.015, 0.02, 0.28, 0.0),
    ("Surya Kiran Solar", "Renewable Energy", 11.4, 0.018, 0.08, 0.17, 0.0),
    ("Vindhya Consulting", "Consulting", 820, -0.004, 0.04, 0.12, -0.0015),
    ("Konkan Retail", "Retail", 640, 0.005, 0.12, 0.09, 0.0),
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
        # Two unusual months per company, so the anomaly detector has something to find.
        for month in rng.choice(np.arange(3, len(t)), size=2, replace=False):
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


if __name__ == "__main__":
    out = Path(__file__).parent / "financial_data.csv"
    build().to_csv(out, index=False)
    print(f"Wrote {out}")
