# BizAI — Smart Business Analytics

BizAI is a web dashboard that turns monthly revenue and expense data into a clear picture of each company's
financial health. For every company it gives a health score, a three-month revenue forecast with a measured
accuracy check, automatic detection of unusual months, a what-if simulator and plain-language recommendations.
Data is read live from a Supabase (PostgreSQL) database, and users can also upload their own CSV or Excel file.

**Author:** Dhanushree B.M

---

## Contents

1. [Features](#features)
2. [Technology](#technology)
3. [Getting started](#getting-started)
4. [Database setup (Supabase)](#database-setup-supabase)
5. [Deployment (Vercel)](#deployment-vercel)
6. [Project structure](#project-structure)
7. [API](#api)
8. [Methodology](#methodology)
9. [Results](#results)
10. [Testing](#testing)
11. [Limitations and future work](#limitations-and-future-work)

---

## Features

| Area | What it does |
|---|---|
| **Overview** | Headline summary, health score from 0 to 100, key figures with trend lines, and a revenue and expense chart with a three-month forecast and an 80% range |
| **Risks** | Months whose profit margin broke from the company's normal pattern, with the cause (revenue or expenses), and recommended actions |
| **What-if** | Sliders to cut expenses or change revenue growth, showing the effect on profit and margin over the next quarter, plus a breakdown of how the health score is built |
| **Ask** | A question box that answers in plain English: figures for any company or month, rankings, comparisons, score explanations and what-if scenarios |
| **All companies** | A league table ranking every company by health, and upload of your own data file |
| **Live data** | Reads from Supabase and redraws automatically when the database changes |
| **Reporting** | Light and dark themes, and a print-ready report |

## Technology

| Layer | Tools |
|---|---|
| Analysis | Python 3.12, pandas, NumPy, scikit-learn (`LinearRegression`, `IsolationForest`) |
| Server | Flask |
| Interface | HTML, CSS and JavaScript, Chart.js |
| Database | Supabase (PostgreSQL) with row level security and realtime |
| Hosting | Vercel |

## Getting started

**Requirements:** Python 3.12 or later.

```bash
git clone https://github.com/Dhanushree-BM13/BizAI.git
cd BizAI
pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000>. The bar at the top of the page shows **Live** when the app is reading from Supabase.
If the database cannot be reached, the app falls back to the bundled demo file `financial_data.csv` and shows
**Bundled sample data** instead.

### Configuration

| Variable | Purpose | Default |
|---|---|---|
| `SUPABASE_URL` | Supabase project URL | The project's own Supabase instance |
| `SUPABASE_KEY` | Supabase **publishable** key | The project's publishable key |

Only the publishable key is used. It is designed to be public, and the database's security rules allow it to
read data and nothing else. The secret key and the database password are never needed by the app and must
never be committed to this repository.

## Database setup (Supabase)

Run these two scripts once, in order, in the Supabase **SQL Editor**. Both are safe to run again.

1. **`supabase/schema.sql`** creates the tables, constraints, view, security policies and realtime publication.
2. **`supabase/seed.sql`** loads the demo data: 40 companies with five years of monthly figures (2,400 rows).
   The rows are computed inside PostgreSQL from each company's parameters, so the script stays short.

### Schema

```
companies                          monthly_financials
---------                          ------------------
id          bigint  PK       1──*  id               bigint         PK
name        text    UNIQUE         company_id       bigint         FK → companies.id, cascade delete
industry    text                   month            date           first day of the month
created_at  timestamptz            revenue          numeric(14,2)  greater than 0
                                   expenses         numeric(14,2)  0 or more
                                   project_success  numeric(5,2)   0 to 100, optional
                                   created_at       timestamptz
                                   UNIQUE (company_id, month)
```

- **Normalised design:** each company's name and industry are stored once, not repeated on every month.
- **Constraints** reject invalid data at the database: empty names, dates that are not the first of a month,
  zero revenue, negative expenses, success rates outside 0–100 and duplicate company months.
- **`company_financials`** is a view that joins the two tables into the flat form the app reads.
- **Row level security:** the public key can only read. Data is changed through the Supabase dashboard.
- **Realtime** is enabled on both tables, so open dashboards update when figures change.

## Deployment (Vercel)

1. Sign in at [vercel.com/new](https://vercel.com/new) and import the GitHub repository.
2. Keep the default settings and click **Deploy**. Vercel detects the Flask `app` in `app.py`, installs
   `requirements.txt` on Python 3.12 (set in `.python-version`) and serves the `public/` folder from its CDN.
3. *Optional:* set `SUPABASE_URL` and `SUPABASE_KEY` under **Settings → Environment Variables** to use a
   different Supabase project.

Every push to `main` triggers a new deployment. `vercel.json` allows each request up to 60 seconds, which covers
the first request after a cold start, and leaves tests and data scripts out of the deployed bundle. Uploads are
limited to 4 MB because Vercel does not accept request bodies over 4.5 MB.

## Project structure

```
BizAI/
├── app.py                 Flask server and API
├── analytics.py           Data cleaning, forecasting, back-testing, anomaly detection, scoring
├── public/
│   └── index.html         Dashboard interface and the Ask feature
├── supabase/
│   ├── schema.sql         Database tables, view, security and realtime
│   └── seed.sql           Demo data (generated)
├── generate_data.py       Builds financial_data.csv and supabase/seed.sql
├── financial_data.csv     Demo data, used when the database is unreachable
├── test_analytics.py      Automated tests
├── requirements.txt       Python dependencies (pinned)
├── .python-version        Python version for Vercel
└── vercel.json            Vercel function settings
```

## API

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/sample` | Full analysis of the live data. The `X-Data-Source` header is `supabase` or `csv`. |
| `POST` | `/api/analyze` | Analysis of an uploaded file (form field `file`, CSV or Excel, up to 4 MB) |
| `GET` | `/api/sample.csv` | Download the demo data file, showing the expected column layout |
| `GET` | `/api/config` | Supabase details the page needs to listen for live changes |

Uploaded files need **Company**, **Date**, **Revenue** and **Expenses** columns; **Industry** and
**Project_Success** are optional. Each company needs at least six months of data.

## Methodology

### Forecast
A scikit-learn `LinearRegression` is fitted to each company's revenue against time. With 24 or more months of
history, sine and cosine terms are added so the model can learn a yearly seasonal pattern. Two trend shapes are
tried, a straight line and a constant percentage growth (a straight line on the log scale), and the one that fits
the history more closely is kept. The shaded band on the chart is ±1.28 residual standard deviations, an
approximate 80% range.

### Accuracy check (back-testing)
To measure how reliable the forecast is, the last three months are hidden, forecast from the earlier data and
compared with the actual figures. This is repeated over four windows, covering the last twelve months. Accuracy is
reported as MAPE (mean absolute percentage error) and compared with a naive baseline that predicts "the same as the
last known month".

### Unusual-month detection
Each month's profit margin is compared with the trend of the company's own margin. A month is flagged only when
two independent checks agree: its deviation is more than 1.8 standard deviations, and an `IsolationForest` ranks it
among the 30% most unusual months. The report states whether revenue or expenses moved further from their trend,
which points to the likely cause.

### Health score
A weighted average of five sub-scores, each from 0 to 100:

| Component | Weight | Based on |
|---|---|---|
| Profitability | 30% | Profit margin over the last three months |
| Growth | 25% | Monthly revenue trend |
| Delivery | 20% | Project success rate over the last three months |
| Stability | 15% | Unusual low-margin months in the last year |
| Cost control | 10% | Whether expenses grow faster than revenue |

The weights are a design choice that puts profitability first, not values learned from data. When a file has no
project success column, Delivery is left out and the other weights are rescaled.

### Ask
A rule-based question answerer. It identifies company names, a measure (revenue, margin, growth, health and others),
a month and the type of question in the user's text, then builds the answer from the analysis. It is not a language
model, and it says so when a question falls outside what it can answer.

## Results

Back-testing on the 40 demo companies:

| Measure | Model | Naive baseline |
|---|---|---|
| Median forecast error (MAPE) | **1.49%** | 5.51% |
| Companies where the model is more accurate | **40 of 40** | — |
| Model error range | 0.51% to 2.97% | — |

Each company's own figures are shown under its chart on the dashboard.

## Testing

```bash
python test_analytics.py
```

Ten automated tests cover forecasting, back-testing, anomaly detection, input validation, health scoring without
optional columns, repeatable demo data, the generated seed script, and every API endpoint including upload errors
and the size limit.

## Limitations and future work

- **Demo data is synthetic.** The 40 companies and their figures are invented. The data was generated with a trend
  and a yearly pattern, which favours the forecasting model; results on real company data will be less precise.
- **Forecasts are statistical projections,** not financial advice.
- **No user accounts yet.** Uploaded files are analysed in memory and are not stored.
- **Possible extensions:** sign-in with Supabase Auth, saving uploaded data per user, and a language model for
  free-form questions.
