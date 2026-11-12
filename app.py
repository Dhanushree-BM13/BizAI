"""BizAI web server: serves the dashboard and the two analysis endpoints."""
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from analytics import analyse, clean, load

BASE = Path(__file__).parent  # so the app works from any working directory
app = Flask(__name__, static_folder=str(BASE / "static"))
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB upload limit


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/sample")
def sample():
    return jsonify(analyse(clean(load(BASE / "financial_data.csv"))))


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
