# BizAI – Smart Business Analytics

**Author: Dhanushree B.M**

A dashboard that reads monthly revenue and expense data for a set of companies and gives each one
a health score, a 3-month revenue forecast with an accuracy check, unusual-month detection, a what-if simulator,
recommendations, a league table and a question box. Data comes live from Supabase, or from your own CSV or Excel file.

## Run
    pip install -r requirements.txt
    python app.py              # open http://127.0.0.1:5000
    python test_analytics.py   # 8 checks of the analysis and the server

## Live data (Supabase)
1. Open the Supabase project, go to **SQL Editor**, paste the contents of `supabase_setup.sql` and run it.
   It creates the `financials` table, lets the public key read it (and nothing else), switches on realtime
   and loads the demo rows.
2. Start the app. The masthead shows **Live** when it is reading Supabase.
3. Change any row in the Supabase **Table Editor**: the dashboard redraws within a second, no refresh needed.

Until step 1 is done, or when there is no internet, the app falls back to the bundled `financial_data.csv`
and the masthead says **Bundled sample data**.

The app only uses the *publishable* key, which is safe to show in a browser. The secret key and the database
password are never needed by the app and must never be put in this repository.

## Files
- `analytics.py` – all the analysis. The page only draws what this returns.
- `app.py` – Flask server: `GET /api/sample` (live or bundled data), `POST /api/analyze` (file upload, 10 MB limit).
- `static/index.html` – the dashboard and the question box.
- `generate_data.py` – builds the demo data: `financial_data.csv` and `supabase_setup.sql`.
- `test_analytics.py` – tests.

## How it works
**Forecast.** scikit-learn `LinearRegression` on a time index. With 24 or more months it also gets a yearly
sine/cosine wave so it can learn seasonality. Two trend shapes are tried, a straight line and a steady-percentage
curve (a straight line in logs), and the one that fits the history better is kept. The shaded band is 1.28 residual
standard deviations, about an 80% range.

**Accuracy check (back-test).** The last 3 months are hidden, forecast from the earlier data and compared with what
really happened. This is repeated for 4 windows (12 hidden months). The error measure is MAPE, the mean absolute
percentage error. The baseline is the naive guess "same as the last known month".

| Company | Model MAPE | Naive MAPE |
|---|---|---|
| Aravali Energy | 0.98% | 2.66% |
| Chenab Telecom | 2.21% | 2.81% |
| Deccan Motors | 1.18% | 4.90% |
| Ganga Textiles | 1.02% | 4.86% |
| Godavari Pharma | 1.91% | 2.73% |
| Himadri Cement | 2.44% | 8.21% |
| Kaveri Systems | 1.13% | 2.08% |
| Konkan Retail | 0.93% | 6.99% |
| Malabar Foods | 2.35% | 4.30% |
| Narmada Finserv | 2.53% | 3.85% |
| Nilgiri Infotech | 2.07% | 3.65% |
| Sahyadri Cloud | 1.05% | 3.26% |
| Surya Kiran Solar | 1.16% | 5.27% |
| Thar Logistics | 1.87% | 2.64% |
| Vindhya Consulting | 0.96% | 3.46% |

**Unusual months.** Each month's profit margin is compared with the margin's own trend line. A month is flagged only
when two checks agree: that gap is beyond 1.8 standard deviations, and an `IsolationForest` ranks the month among
the most isolated 30%. The report then says whether expenses or revenue moved further from its own trend.

**Health score.** A weighted average of five 0–100 sub-scores: profitability 30%, growth 25%, delivery 20%,
stability 15%, cost control 10%. The weights are a design choice (profit first, then growth), not learned from data.
Delivery is left out when the file has no project-success column.

**Ask BizAI.** A rule-based answerer in `static/index.html`. It looks in the question for company names, a measure
(revenue, margin, growth, health...), a month and the kind of question, then fills in an answer from the analysis.
It can report a figure for any company or month, rank and compare companies, explain a health score and run
what-if scenarios. It is not a language model and says so when it cannot match a question.

## Limits
- The 15 demo companies and their 5 years of figures are invented. The model beats the naive baseline here partly
  because the demo data was generated with a trend and a yearly pattern; real data will be noisier.
- Forecasts are simple statistical projections, not financial advice.
- No login yet. Uploaded files are analysed in memory and not saved to Supabase.
