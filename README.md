# BizAI – Smart Business Analytics

**Author: Dhanushree B.M**

A dashboard that reads monthly revenue and expense data for a set of companies and gives each one
a health score, a 3-month revenue forecast with an accuracy check, unusual-month detection, a what-if simulator,
recommendations, a league table and a question box. Data comes live from Supabase, or from your own CSV or Excel file.

## Run
    pip install -r requirements.txt
    python app.py              # open http://127.0.0.1:5000
    python test_analytics.py   # 8 checks of the analysis and the server

## Deploy to Vercel
1. Go to [vercel.com/new](https://vercel.com/new) and import the GitHub repository `Dhanushree-BM13/BizAI`.
2. Leave every setting as it is and click **Deploy**. Vercel finds the Flask `app` in `app.py`,
   installs `requirements.txt` with Python 3.12 (`.python-version`) and serves `public/` from its CDN.
3. Optional: under **Settings → Environment Variables** set `SUPABASE_URL` and `SUPABASE_KEY` to point
   at another Supabase project. Without them the app uses the project below.

Every push to `main` deploys again. `vercel.json` gives the function 60 seconds, enough for the first
request after a cold start, and leaves tests and scripts out of the bundle. Uploads are limited to 4 MB
because Vercel rejects request bodies over 4.5 MB.

## Live data (Supabase)
1. In the Supabase **SQL Editor**, run `supabase/schema.sql`. It creates the database (see below).
2. Then run `supabase/seed.sql`. It loads the 40 demo companies. The monthly rows are computed inside
   Postgres from each company's parameters, with the same formula as `generate_data.py`, so the script stays short.
3. Start the app. The masthead shows **Live** when it is reading Supabase.
4. Change any row in the Supabase **Table Editor**: the dashboard redraws within a second, no refresh needed.

### Schema

```
companies                         monthly_financials
---------                         ------------------
id          bigint  PK      1──*  id               bigint  PK
name        text    unique        company_id       bigint  FK → companies.id (cascade delete)
industry    text                  month            date    first day of month
created_at  timestamptz           revenue          numeric(14,2)  > 0
                                  expenses         numeric(14,2)  >= 0
                                  project_success  numeric(5,2)   0–100, optional
                                  created_at       timestamptz
                                  unique (company_id, month)
```

- **Normalised:** a company's name and industry are stored once, not on every month.
- **Constraints** reject bad data at the database: empty names, a month that is not the 1st,
  zero revenue, negative expenses, a success rate outside 0–100, two rows for the same company and month.
- **`company_financials`** is a view joining the two tables into the flat shape the app reads.
- **Row level security:** the public key can only read. Writes go through the Supabase dashboard.
- **Realtime** is on for both tables, so the dashboard updates when either changes.

Both scripts are safe to run again. Until they are run, or when there is no internet, or when there is no internet, the app falls back to the bundled `financial_data.csv`
and the masthead says **Bundled sample data**.

The app only uses the *publishable* key, which is safe to show in a browser. The secret key and the database
password are never needed by the app and must never be put in this repository.

## Files
- `analytics.py` – all the analysis. The page only draws what this returns.
- `app.py` – Flask server: `GET /api/sample` (live or bundled data), `POST /api/analyze` (file upload, 10 MB limit).
- `public/index.html` – the dashboard and the question box.
- `supabase/schema.sql` – the database: tables, constraints, view, security, realtime.
- `generate_data.py` – builds the demo data: `financial_data.csv` and `supabase/seed.sql`.
- `test_analytics.py` – tests.

## How it works
**Forecast.** scikit-learn `LinearRegression` on a time index. With 24 or more months it also gets a yearly
sine/cosine wave so it can learn seasonality. Two trend shapes are tried, a straight line and a steady-percentage
curve (a straight line in logs), and the one that fits the history better is kept. The shaded band is 1.28 residual
standard deviations, about an 80% range.

**Accuracy check (back-test).** The last 3 months are hidden, forecast from the earlier data and compared with what
really happened. This is repeated for 4 windows (12 hidden months). The error measure is MAPE, the mean absolute
percentage error. The baseline is the naive guess "same as the last known month".

Across the 40 demo companies the model beat the naive guess for all 40. Median error: **1.49%** for the model against **5.51%** for the naive guess (model range 0.51–2.97%). The Accuracy line under each company's chart shows its own figures.

**Unusual months.** Each month's profit margin is compared with the margin's own trend line. A month is flagged only
when two checks agree: that gap is beyond 1.8 standard deviations, and an `IsolationForest` ranks the month among
the most isolated 30%. The report then says whether expenses or revenue moved further from its own trend.

**Health score.** A weighted average of five 0–100 sub-scores: profitability 30%, growth 25%, delivery 20%,
stability 15%, cost control 10%. The weights are a design choice (profit first, then growth), not learned from data.
Delivery is left out when the file has no project-success column.

**Ask BizAI.** A rule-based answerer in `public/index.html`. It looks in the question for company names, a measure
(revenue, margin, growth, health...), a month and the kind of question, then fills in an answer from the analysis.
It can report a figure for any company or month, rank and compare companies, explain a health score and run
what-if scenarios. It is not a language model and says so when it cannot match a question.

## Limits
- The 40 demo companies and their 5 years of figures are invented. The model beats the naive baseline here partly
  because the demo data was generated with a trend and a yearly pattern; real data will be noisier.
- Forecasts are simple statistical projections, not financial advice.
- No login yet. Uploaded files are analysed in memory and not saved to Supabase.
