"""BizAI web server: serves the dashboard and the analysis endpoints."""
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd
from flask import Flask, jsonify, request, send_from_directory

from analytics import analyse, clean, load

BASE = Path(__file__).parent  # so the app works from any working directory
app = Flask(__name__, static_folder=str(BASE / "static"))
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB upload limit
app.config["USE_SUPABASE"] = True  # tests switch this off so they run without a network

# Supabase project that holds the live data. The publishable key is meant to be public:
# row level security on the table only lets it read. Never put the secret key here.
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://pckkvrafahqelkwiyucv.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_aZFg3JIGkQcQ2TcCu1T-5A_ApGCq5Wf")
TABLE = "financials"
PAGE = 1000  # Supabase returns at most 1000 rows per request


def load_live():
    """Every row of the Supabase table, fetched a page at a time."""
    rows = []
    while True:
        url = (f"{SUPABASE_URL}/rest/v1/{TABLE}?select=company,industry,date,revenue,expenses,project_success"
               f"&order=id&limit={PAGE}&offset={len(rows)}")
        for attempt in range(3):  # the connection is occasionally dropped, so try again before giving up
            try:
                with urlopen(Request(url, headers={"apikey": SUPABASE_KEY}), timeout=10) as response:
                    batch = json.load(response)
                break
            except OSError:
                if attempt == 2:
                    raise
        rows += batch
        if len(batch) < PAGE:
            return pd.DataFrame(rows)


def current_data():
    """Rows to analyse and where they came from: Supabase, or the bundled CSV if Supabase is unreachable or empty."""
    if app.config["USE_SUPABASE"]:
        try:
            live = load_live()
            if len(live):
                return live, "supabase"
        except Exception as problem:
            app.logger.warning("Supabase unavailable, using the bundled CSV: %s", problem)
    return load(BASE / "financial_data.csv"), "csv"


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


_cache = {"key": None, "result": None}


def analyse_cached(rows):
    """Analysis is slow (about 0.3 s a company), so reuse the last result while the data is unchanged."""
    key = pd.util.hash_pandas_object(rows, index=False).sum()
    if key != _cache["key"]:
        _cache.update(key=key, result=analyse(clean(rows)))
    return _cache["result"]


@app.get("/api/sample")
def sample():
    rows, source = current_data()
    response = jsonify(analyse_cached(rows))
    response.headers["X-Data-Source"] = source  # the page shows whether the data is live
    return response


@app.get("/api/config")
def config():
    """What the page needs to listen for live changes. Empty when Supabase is switched off."""
    if not app.config["USE_SUPABASE"]:
        return jsonify({})
    return jsonify(url=SUPABASE_URL, key=SUPABASE_KEY, table=TABLE)


@app.get("/api/sample.csv")
def sample_file():
    """Lets users download the demo file to see the expected columns."""
    return send_from_directory(BASE, "financial_data.csv", as_attachment=True)


@app.post("/api/analyze")
def analyze():
    file = request.files.get("file")
    if not file:
        return jsonify(error="No file uploaded."), 400
    try:
        return jsonify(analyse(clean(load(file))))
    except ValueError as e:
        return jsonify(error=str(e)), 400
    except Exception:
        return jsonify(error="Could not read that file. Upload a valid CSV or Excel file."), 400


if __name__ == "__main__":
    app.run()  # for auto-reload while developing: flask run --debug
