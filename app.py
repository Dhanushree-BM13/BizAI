"""BizAI web server: serves the dashboard and the analysis endpoints."""
import json
import os
import time
from functools import wraps
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd
from flask import Flask, g, jsonify, request, send_from_directory

from analytics import analyse, clean, load

BASE = Path(__file__).parent  # so the app works from any working directory
# The page lives in public/, which Vercel serves from its CDN. Locally Flask serves it instead.
app = Flask(__name__, static_folder=str(BASE / "public"), static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024  # 4 MB: Vercel rejects request bodies over 4.5 MB
app.config["USE_SUPABASE"] = True  # tests switch this off so they run without a network

# Supabase project that holds the data and the user accounts. The publishable key is meant to be
# public: row level security only lets signed-in users read. Never put the secret key here.
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://pckkvrafahqelkwiyucv.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_aZFg3JIGkQcQ2TcCu1T-5A_ApGCq5Wf")
VIEW = "company_financials"    # what the app reads: companies joined to their months
TABLE = "monthly_financials"   # what the page listens to for live changes
PAGE = 1000  # Supabase returns at most 1000 rows per request


def supabase_headers(token):
    """Headers for a Supabase request made on behalf of a signed-in user."""
    return {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {token}"}


_verified = {}  # access token -> time it was last confirmed, so each request does not ask Supabase again


def signed_in_token():
    """The caller's Supabase access token if it belongs to a signed-in user, otherwise None."""
    header = request.headers.get("Authorization", "")
    token = header[len("Bearer "):] if header.startswith("Bearer ") else ""
    if not token:
        return None
    if time.time() - _verified.get(token, 0) < 300:
        return token
    try:
        with urlopen(Request(f"{SUPABASE_URL}/auth/v1/user", headers=supabase_headers(token)), timeout=10):
            pass  # Supabase answers 200 only for a valid, unexpired session
    except OSError:
        return None
    if len(_verified) > 1000:
        _verified.clear()
    _verified[token] = time.time()
    return token


def login_required(view):
    """Reject requests from anyone not signed in. Skipped when Supabase is switched off (tests)."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        g.token = None
        if app.config["USE_SUPABASE"]:
            g.token = signed_in_token()
            if not g.token:
                return jsonify(error="Please sign in."), 401
        return view(*args, **kwargs)
    return wrapper


def load_live(token):
    """Every row of the Supabase view, fetched a page at a time as the signed-in user."""
    rows = []
    while True:
        url = (f"{SUPABASE_URL}/rest/v1/{VIEW}?select=company,industry,date,revenue,expenses,project_success"
               f"&order=id&limit={PAGE}&offset={len(rows)}")
        for attempt in range(3):  # the connection is occasionally dropped, so try again before giving up
            try:
                with urlopen(Request(url, headers=supabase_headers(token)), timeout=10) as response:
                    batch = json.load(response)
                break
            except OSError:
                if attempt == 2:
                    raise
        rows += batch
        if len(batch) < PAGE:
            return pd.DataFrame(rows)


def current_data(token):
    """Rows to analyse and where they came from: Supabase, or the bundled CSV if Supabase is unreachable or empty."""
    if app.config["USE_SUPABASE"]:
        try:
            live = load_live(token)
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
@login_required
def sample():
    rows, source = current_data(g.token)
    response = jsonify(analyse_cached(rows))
    response.headers["X-Data-Source"] = source  # the page shows whether the data is live
    return response


@app.get("/api/config")
def config():
    """What the pages need to sign in and listen for live changes. Empty when Supabase is switched off."""
    if not app.config["USE_SUPABASE"]:
        return jsonify({})
    return jsonify(url=SUPABASE_URL, key=SUPABASE_KEY, table=TABLE)


@app.get("/api/sample.csv")
def sample_file():
    """A file of companies not in the database, for trying the upload."""
    return send_from_directory(BASE, "sample_upload.csv", as_attachment=True, download_name="bizai_sample_upload.csv")


@app.errorhandler(413)
def too_large(_):
    return jsonify(error="That file is over 4 MB. Upload a smaller CSV or Excel file."), 413


@app.post("/api/analyze")
@login_required
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
