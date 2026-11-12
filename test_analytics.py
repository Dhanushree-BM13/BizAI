"""Checks for the analytics engine and the server. Run: python test_analytics.py"""
import io

import numpy as np
import pandas as pd

from analytics import analyse, backtest, clean, find_unusual_months, forecast
from app import app
from generate_data import COMPANIES, build, to_seed_sql

app.config["USE_SUPABASE"] = False  # tests use the bundled CSV, no network

MONTHS_36 = np.tile(np.arange(1, 13), 3)


def test_forecast_continues_a_straight_line():
    y = 100 + 5 * np.arange(12.0)
    predicted, band, model = forecast(np.arange(1, 13), y)
    assert np.allclose(predicted, [160, 165, 170]) and band < 1e-6 and model == "Linear trend"


def test_seasonality_used_only_with_two_years():
    assert forecast(MONTHS_36, np.linspace(100, 200, 36))[2] == "Trend + seasonality"


def test_backtest_beats_naive_on_trending_data():
    result = backtest(MONTHS_36, 100 + 5 * np.arange(36.0))
    assert result["folds"] == 4 and result["mape"] < result["naive_mape"]
    assert backtest(np.arange(1, 9), np.arange(1.0, 9)) is None  # too short to test


def test_expense_spike_is_flagged_and_blamed_on_expenses():
    rng = np.random.default_rng(1)
    revenue = 1000 * rng.normal(1, 0.01, 24)
    expenses = 800 * rng.normal(1, 0.01, 24)
    expenses[10] *= 1.2
    flags = find_unusual_months(revenue, expenses)
    assert [(f["index"], f["cause"]) for f in flags if f["z"] < 0] == [(10, "expenses")]


def test_clean_rejects_missing_columns():
    try:
        clean(pd.DataFrame({"Company": ["A"], "Date": ["2025-01-01"]}))
    except ValueError as e:
        assert "revenue" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_sample_data_analyses_fully():
    result = analyse(clean(build()))
    assert len(result) == len(COMPANIES)
    for company in result.values():
        assert 0 <= company["health"]["score"] <= 100
        assert len(company["forecast"]["revenue"]) == 3 and company["backtest"]["folds"] == 4


def test_health_score_works_without_success_column():
    rows = clean(build().drop(columns="Project_Success_Rate_Pct"))
    company = next(iter(analyse(rows).values()))
    assert company["success"] is None
    assert "Delivery" not in [part["name"] for part in company["health"]["parts"]]


def test_seed_sql_has_every_company_and_month():
    sql = to_seed_sql(build())
    assert sql.count("\n  ('") == len(COMPANIES)
    assert sql.count("{") == 3 * len(COMPANIES) and "date '2021-11-01'" in sql


def test_server_endpoints():
    client = app.test_client()
    assert client.get("/").status_code == 200
    assert len(client.get("/api/sample").get_json()) == len(COMPANIES)
    assert client.get("/api/sample").headers["X-Data-Source"] == "csv" and client.get("/api/config").get_json() == {}
    assert client.get("/api/sample.csv").data.startswith(b"Date,Company")
    assert client.post("/api/analyze").status_code == 400
    bad = client.post("/api/analyze", data={"file": (io.BytesIO(b"a,b\n1,2\n"), "bad.csv")})
    assert bad.status_code == 400 and "Missing columns" in bad.get_json()["error"]
    good = client.post("/api/analyze", data={"file": (io.BytesIO(build().to_csv(index=False).encode()), "ok.csv")})
    assert good.status_code == 200 and len(good.get_json()) == len(COMPANIES)


if __name__ == "__main__":
    tests = [f for name, f in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok  ", test.__name__)
    print(f"{len(tests)} tests passed")
