"""BizAI analytics engine.

Cleans the uploaded data, forecasts revenue, back-tests that forecast, flags unusual
months, scores business health and writes recommendations. All numbers shown on the
dashboard are produced here; the page only draws them.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression

# Column headings we accept. A heading matches if it starts with one of these words.
COLUMN_ALIASES = {
    "company": ("company", "name"),
    "date": ("date", "month", "period"),
    "revenue": ("revenue", "sales", "income"),
    "expenses": ("expenses", "expense", "cost"),
    "industry": ("industry", "sector"),
    "success": ("project_success", "success"),
}
REQUIRED = ("company", "date", "revenue", "expenses")

HORIZON = 3                # months forecast ahead
MIN_MONTHS = 6             # a company needs this much history to be analysed
SEASONAL_MIN_MONTHS = 24   # two full years before we trust a yearly pattern
BACKTEST_MIN_TRAIN = 9     # smallest history a back-test fold may train on
BACKTEST_MAX_FOLDS = 4
Z_LIMIT = 1.8              # margin this many standard deviations from normal is "unusual"

# Health score = weighted average of five 0-100 sub-scores. The weights are a design
# choice (profitability first, then growth), not something learned from data.
HEALTH_WEIGHTS = {
    "Profitability": 0.30,    # recent profit margin; 25% margin or more scores 100
    "Growth": 0.25,           # revenue trend; flat scores 50
    "Delivery": 0.20,         # recent project success rate
    "Stability": 0.15,        # loses 25 points per bad unusual month in the last year
    "Cost control": 0.10,     # penalised when expenses grow faster than revenue
}


def load(source):
    """Read a CSV or Excel file (a path or an uploaded file object)."""
    name = str(getattr(source, "filename", source)).lower()
    return pd.read_excel(source) if name.endswith((".xlsx", ".xls")) else pd.read_csv(source)


def clean(df):
    """Pick out the columns we need, fix their types and drop unusable rows."""
    found = {
        key: next((c for c in df.columns if str(c).strip().lower().startswith(aliases)), None)
        for key, aliases in COLUMN_ALIASES.items()
    }
    missing = [key for key in REQUIRED if found[key] is None]
    if missing:
        raise ValueError("Missing columns: " + ", ".join(missing) + ". Need Company, Date, Revenue and Expenses.")
    rows = pd.DataFrame({
        "company": df[found["company"]].astype(str).str.strip(),
        "date": pd.to_datetime(df[found["date"]], errors="coerce"),
        "revenue": pd.to_numeric(df[found["revenue"]], errors="coerce"),
        "expenses": pd.to_numeric(df[found["expenses"]], errors="coerce"),
        "industry": df[found["industry"]].astype(str) if found["industry"] is not None else "Uploaded data",
        "success": pd.to_numeric(df[found["success"]], errors="coerce") if found["success"] is not None else np.nan,
    })
    return rows.dropna(subset=["date", "revenue", "expenses"])


def _features(t, months, seasonal):
    """Model inputs: a time index, plus a yearly sine/cosine wave when seasonal."""
    columns = [t]
    if seasonal:
        angle = 2 * np.pi * months / 12
        columns += [np.sin(angle), np.cos(angle)]
    return np.column_stack(columns)


def forecast(months, y, horizon=HORIZON):
    """Linear trend (plus yearly seasonality with 24+ months) projected `horizon` months ahead.

    Returns the predictions, the half-width of an approximate 80% range, and the model name.
    """
    n = len(y)
    seasonal = n >= SEASONAL_MIN_MONTHS
    X = _features(np.arange(n), months, seasonal)
    future_months = (months[-1] + np.arange(1, horizon + 1) - 1) % 12 + 1
    future = _features(np.arange(n, n + horizon), future_months, seasonal)

    def fit(transform, inverse):
        model = LinearRegression().fit(X, transform(y))
        return inverse(model.predict(future)), y - inverse(model.predict(X))

    # Try a straight-line trend and, for positive values, a steady-percentage trend
    # (a straight line in logs). Keep whichever fits the history more closely.
    candidates = [fit(lambda v: v, lambda v: v)]
    if (y > 0).all():
        candidates.append(fit(np.log, np.exp))
    predicted, residuals = min(candidates, key=lambda c: (c[1] ** 2).sum())
    spread = np.sqrt((residuals ** 2).sum() / max(1, n - X.shape[1] - 1))
    # 1.28 standard deviations either side covers about 80% of a normal distribution.
    return predicted, 1.28 * spread, "Trend + seasonality" if seasonal else "Linear trend"


def backtest(months, y):
    """Check the forecast against months it has not seen.

    Hide the last 3 months, forecast them from the earlier data and measure the error;
    repeat further back for up to 4 folds. The naive baseline predicts "same as the last
    known month". MAPE = mean absolute percentage error, lower is better.
    """
    model_errors, naive_errors, folds = [], [], 0
    for fold in range(1, BACKTEST_MAX_FOLDS + 1):
        cut = len(y) - HORIZON * fold
        if cut < BACKTEST_MIN_TRAIN:
            break
        actual = y[cut:cut + HORIZON]
        predicted, _, _ = forecast(months[:cut], y[:cut])
        model_errors += list(np.abs(predicted - actual) / actual)
        naive_errors += list(np.abs(y[cut - 1] - actual) / actual)
        folds += 1
    if not folds:
        return None
    return {"folds": folds, "mape": round(100 * float(np.mean(model_errors)), 2),
            "naive_mape": round(100 * float(np.mean(naive_errors)), 2)}


def monthly_growth(y):
    """Slope of a straight-line fit, as a percentage of the average value per month."""
    return float(np.polyfit(np.arange(len(y)), y, 1)[0] / y.mean() * 100)


def find_unusual_months(revenue, expenses):
    """Flag months whose profit margin is far from normal.

    A month is flagged only when two checks agree: its margin z-score is beyond Z_LIMIT,
    and an Isolation Forest ranks it in the most isolated 30% of months. We then say
    whether expenses or revenue strayed further from its own trend line.
    """
    n = len(revenue)
    margin = (revenue - expenses) / revenue * 100
    t = np.arange(n)
    # Compare each month with the margin's own trend line, so a slow drift over the years is not mistaken for a shock.
    gap = margin - np.polyval(np.polyfit(t, margin, 1), t)
    z = gap / (gap.std() or 1)
    X = np.column_stack([
        margin,
        np.r_[0, np.diff(revenue) / revenue[:-1]],
        np.r_[0, np.diff(expenses) / expenses[:-1]],
    ])
    X = (X - X.mean(0)) / (X.std(0) + 1e-9)
    isolation = -IsolationForest(n_estimators=200, random_state=0).fit(X).score_samples(X)
    revenue_trend = np.polyval(np.polyfit(t, revenue, 1), t)
    expense_trend = np.polyval(np.polyfit(t, expenses, 1), t)
    flags = []
    for i in range(n):
        if abs(z[i]) > Z_LIMIT and isolation[i] >= np.quantile(isolation, 0.7):
            revenue_gap = (revenue[i] - revenue_trend[i]) / revenue_trend[i]
            expense_gap = (expenses[i] - expense_trend[i]) / expense_trend[i]
            expenses_caused_it = abs(expense_gap) > abs(revenue_gap)
            flags.append({
                "index": i, "z": round(float(z[i]), 2), "margin": round(float(margin[i]), 2),
                "cause": "expenses" if expenses_caused_it else "revenue",
                "deviation": round(float(expense_gap if expenses_caused_it else revenue_gap) * 100, 1),
            })
    return flags


def health_score(margin, growth, expense_growth, success, flags):
    """Combine the sub-scores using HEALTH_WEIGHTS. Delivery is left out when no success data exists."""
    def clamp(x):
        return float(max(0, min(100, x)))

    recent_bad = [f for f in flags if f["z"] < 0 and f["index"] >= len(margin) - 12]
    values = {
        "Profitability": clamp(margin[-3:].mean() / 25 * 100),
        "Growth": clamp(50 + growth * 30),
        "Delivery": None if success is None else clamp(success[-3:].mean()),
        "Stability": clamp(100 - 25 * len(recent_bad)),
        "Cost control": clamp(100 - 60 * max(0, expense_growth - growth)),
    }
    parts = [{"name": k, "weight": HEALTH_WEIGHTS[k], "value": round(v)} for k, v in values.items() if v is not None]
    score = round(sum(p["weight"] * p["value"] for p in parts) / sum(p["weight"] for p in parts))
    label = "Strong" if score >= 70 else "Watch" if score >= 50 else "At risk"
    return {"score": score, "label": label, "parts": parts}


def recommend(flags, growth, expense_growth, success):
    """Plain rules that turn the findings into suggested actions."""
    actions = []
    for f in flags:
        if f["z"] >= 0:
            continue
        if f["cause"] == "expenses":
            actions.append(f"Review expense lines for {f['month']}: spending ran {f['deviation']:+.1f}% "
                           f"against trend and cut margin to {f['margin']:.1f}%.")
        else:
            actions.append(f"Investigate the revenue dip in {f['month']}, which was {f['deviation']:+.1f}% "
                           "against trend. Check lost clients or delayed billing.")
    if expense_growth > growth + 0.2:
        actions.append(f"Expenses are growing faster ({expense_growth:.1f}% a month) than revenue "
                       f"({growth:.1f}%). Review budgets before margins shrink.")
    if growth < 0:
        actions.append("Revenue is trending down. Look at client retention and pipeline for the coming quarter.")
    if success is not None and (success[-3:] < 80).any():
        actions.append("Project success fell below 80% recently. Audit delivery on the affected projects.")
    return actions or ["Performance is steady. Consider reinvesting part of the margin in growth projects, "
                       "and keep monitoring monthly."]


def analyse_company(history):
    """Full analysis for one company's rows, sorted by date."""
    revenue = history.revenue.to_numpy(float)
    expenses = history.expenses.to_numpy(float)
    months = history.date.dt.month.to_numpy()
    success = None if history.success.isna().all() else history.success.fillna(history.success.mean()).to_numpy(float)
    margin = (revenue - expenses) / revenue * 100

    revenue_forecast, band, model = forecast(months, revenue)
    expense_forecast, _, _ = forecast(months, expenses)
    growth, expense_growth = monthly_growth(revenue), monthly_growth(expenses)
    flags = find_unusual_months(revenue, expenses)
    for f in flags:
        f["month"] = history.date.iloc[f["index"]].strftime("%B %Y")
        f["success"] = None if success is None else round(float(success[f["index"]]), 1)
    future = pd.date_range(history.date.iloc[-1], periods=HORIZON + 1, freq="MS")[1:]

    return {
        "industry": str(history.industry.iloc[0]),
        "months": history.date.dt.strftime("%b %y").tolist(),
        "latest_month": history.date.iloc[-1].strftime("%B %Y"),
        "revenue": revenue.round(2).tolist(),
        "expenses": expenses.round(2).tolist(),
        "margin": margin.round(2).tolist(),
        "success": None if success is None else success.round(1).tolist(),
        "growth": round(growth, 2),
        "expense_growth": round(expense_growth, 2),
        "forecast": {
            "months": future.strftime("%b %y").tolist(),
            "revenue": revenue_forecast.round(2).tolist(),
            "expenses": expense_forecast.round(2).tolist(),
            "band": round(float(band), 2),
            "model": model,
        },
        "backtest": backtest(months, revenue),
        "flags": flags,
        "health": health_score(margin, growth, expense_growth, success, flags),
        "actions": recommend(flags, growth, expense_growth, success),
    }


def analyse(rows):
    """Analyse every company in cleaned rows. Returns {company name: analysis}."""
    result = {}
    for company, history in rows.groupby("company"):
        history = history.sort_values("date")
        if len(history) < MIN_MONTHS or (history.revenue <= 0).any():
            continue
        result[company] = analyse_company(history)
    if not result:
        raise ValueError(f"No company has {MIN_MONTHS} or more months of valid data.")
    return result
