import base64
import json
import os
import threading

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, abort, redirect, url_for, flash

import auth
import database
from agent.orchestrator import run_agent
from services.portfolio_service import run_portfolio_analysis

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-insecure-secret-change-me")
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8MB upload cap
database.init_db()

REPORT_JSON_COLUMNS = ("price_data", "fundamentals", "news_json", "analysis_json", "dcf_json", "report_json")
PORTFOLIO_JSON_COLUMNS = ("holdings_json", "enrichment_json", "analysis_json")


def _serialize(row, json_columns):
    row = dict(row)
    for col in json_columns:
        if row.get(col):
            try:
                row[col] = json.loads(row[col])
            except (TypeError, ValueError):
                row[col] = None
    return row


@app.context_processor
def inject_user():
    return {"current_user": auth.current_user()}


# --- Auth routes ---

@app.route("/signup", methods=["GET", "POST"])
def signup_page():
    if request.method == "POST":
        user_id, error = auth.signup(request.form.get("email", ""), request.form.get("password", ""))
        if error:
            flash(error)
            return render_template("signup.html")
        return redirect(url_for("index"))
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        user_id, error = auth.login(request.form.get("email", ""), request.form.get("password", ""))
        if error:
            flash(error)
            return render_template("login.html")
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout_page():
    auth.logout()
    return redirect(url_for("login_page"))


# --- Ticker research routes ---

@app.route("/")
@auth.login_required
def index():
    recent_reports = database.get_recent_reports(auth.current_user()["id"], limit=5)
    return render_template("index.html", recent_reports=recent_reports)


@app.route("/api/research", methods=["POST"])
@auth.login_required
def api_research():
    data = request.get_json(silent=True) or {}
    ticker = (data.get("ticker") or "").strip().upper()
    if not ticker:
        return jsonify({"error": "Ticker is required"}), 400

    report_id = database.create_report(ticker, auth.current_user()["id"])
    thread = threading.Thread(target=run_agent, args=(ticker, report_id), daemon=True)
    thread.start()

    return jsonify({"report_id": report_id})


@app.route("/api/report/<int:report_id>")
@auth.login_required
def api_report(report_id):
    report = database.get_report(report_id, auth.current_user()["id"])
    if not report:
        abort(404)
    return jsonify(_serialize(report, REPORT_JSON_COLUMNS))


@app.route("/report/<int:report_id>")
@auth.login_required
def report_page(report_id):
    report = database.get_report(report_id, auth.current_user()["id"])
    if not report:
        abort(404)
    return render_template("report.html", report=report)


@app.route("/api/report/<int:report_id>", methods=["DELETE"])
@auth.login_required
def api_delete_report(report_id):
    user_id = auth.current_user()["id"]
    if not database.get_report(report_id, user_id):
        abort(404)
    database.delete_report(report_id, user_id)
    return jsonify({"deleted": report_id})


@app.route("/history")
@auth.login_required
def history_page():
    user_id = auth.current_user()["id"]
    reports = database.get_recent_reports(user_id, limit=200)
    analyses = database.get_recent_portfolio_analyses(user_id, limit=200)
    return render_template(
        "history.html",
        reports=[_serialize(r, REPORT_JSON_COLUMNS) for r in reports],
        analyses=[_serialize(a, PORTFOLIO_JSON_COLUMNS) for a in analyses],
    )


# --- Portfolio analysis routes ---

@app.route("/analyze")
@auth.login_required
def analyze_page():
    return render_template("analyze.html")


@app.route("/api/analyze-portfolio", methods=["POST"])
@auth.login_required
def api_analyze_portfolio():
    user_id = auth.current_user()["id"]
    image_file = request.files.get("image")
    holdings_text = (request.form.get("holdings_text") or "").strip()

    if not image_file and not holdings_text:
        return jsonify({"error": "Upload a screenshot or paste your holdings."}), 400

    image_b64, mime_type = None, None
    if image_file and image_file.filename:
        image_b64 = base64.b64encode(image_file.read()).decode("ascii")
        mime_type = image_file.mimetype or "image/png"

    input_type = "image" if image_b64 else "text"
    analysis_id = database.create_portfolio_analysis(user_id, input_type)

    thread = threading.Thread(
        target=run_portfolio_analysis,
        args=(analysis_id,),
        kwargs={"image_b64": image_b64, "mime_type": mime_type, "raw_text": holdings_text},
        daemon=True,
    )
    thread.start()

    return jsonify({"analysis_id": analysis_id})


@app.route("/api/analysis/<int:analysis_id>")
@auth.login_required
def api_analysis(analysis_id):
    analysis = database.get_portfolio_analysis(analysis_id, auth.current_user()["id"])
    if not analysis:
        abort(404)
    return jsonify(_serialize(analysis, PORTFOLIO_JSON_COLUMNS))


@app.route("/analysis/<int:analysis_id>")
@auth.login_required
def analysis_page(analysis_id):
    analysis = database.get_portfolio_analysis(analysis_id, auth.current_user()["id"])
    if not analysis:
        abort(404)
    return render_template("analysis.html", analysis=analysis)


if __name__ == "__main__":
    app.run(debug=True)
