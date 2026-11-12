# BizAI – Smart Business Analytics

Upload a CSV or Excel file (Company, Date, Revenue, Expenses; optional Industry, Project_Success) and get a dashboard with
a business health score, a 3-month revenue forecast with an 80% range, an accuracy check of that forecast,
unusual-month detection, a what-if simulator, recommendations and quick answers.

## Run
    pip install -r requirements.txt
    python app.py              # open http://127.0.0.1:5000
    python test_analytics.py   # 8 checks of the analysis and the server

## Files
- `analytics.py` – all the analysis. The page only draws what this returns.
- `app.py` – Flask server: `GET /api/sample` (demo data), `POST /api/analyze` (file upload, 10 MB limit).
- `static/index.html` – the dashboard.
- `generate_data.py` – builds the demo data in `financial_data.csv`.
- `test_analytics.py` – tests.

## How it works
**Forecast.** scikit-learn `LinearRegression` on a time index. With 24 or more months it also gets a yearly
sine/cosine wave so it can learn seasonality. The shaded band is 1.28 residual standard deviations, about an 80% range.

**Accuracy check (back-test).** The last 3 months are hidden, forecast from the earlier data and compared with what
really happened. This is repeated for 4 windows (12 hidden months). The error measure is MAPE, the mean absolute
percentage error. The baseline is the naive guess "same as the last known month".

| Company | Model MAPE | Naive MAPE |
|---|---|---|
| Aravali Energy | 2.56% | 5.05% |
| Kaveri Systems | 2.86% | 3.95% |
| Konkan Retail | 1.59% | 7.68% |
| Nilgiri Infotech | 2.06% | 3.94% |
| Sahyadri Cloud | 3.18% | 4.14% |
| Surya Kiran Solar | 2.54% | 5.16% |
| Vindhya Consulting | 2.50% | 3.76% |

**Unusual months.** A month is flagged only when two checks agree: its profit-margin z-score is beyond 1.8, and an
`IsolationForest` ranks it among the most isolated 30% of months. The report then says whether expenses or revenue
moved further from its own trend line.

**Health score.** A weighted average of five 0–100 sub-scores: profitability 30%, growth 25%, delivery 20%,
stability 15%, cost control 10%. The weights are a design choice (profit first, then growth), not learned from data.
Delivery is left out when the file has no project-success column.

## Limits
- The demo companies and figures are invented. The model beats the naive baseline here partly because the demo data
  was generated with a trend and a yearly pattern; real data will be noisier.
- Forecasts are simple statistical projections, not financial advice.
- Recommendations and quick answers are fixed rules filled in with the numbers. No language model is used.
- No login and no database yet; uploads are analysed in memory and not stored.
