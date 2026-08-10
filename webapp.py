"""
Footy Edge Bot -- Web Dashboard

Run scans, grade results, and see honest performance from a browser instead
of the terminal. Works fully offline on your local network (LAN/hotspot).

Usage:
    python webapp.py

Then open http://localhost:5000 on the host PC, or
http://<host-pc-local-ip>:5000 from any other device on the same network.
"""

import csv
import io
import os
import threading

from flask import Flask, render_template, redirect, url_for, flash, request, Response, jsonify

import auth
import config
import settings as settings_module
import job_state
import scheduler as scheduler_module
from storage import (
    init_db, get_all_predictions, get_graded_predictions, latest_bankroll,
    get_bankroll_history,
)
import main as scan_module
import grade as grade_module
import calibrate as calibrate_module
import metrics as metrics_module
from logging_setup import setup_logging

logger = setup_logging()

app = Flask(__name__)
# On Render, set SECRET_KEY in the environment (Dashboard -> Environment).
# Falls back to a fixed value for local/LAN use where this doesn't matter.
app.secret_key = os.environ.get("SECRET_KEY", "footy-edge-bot-local-only")

app.permanent_session_lifetime = auth.SESSION_LIFETIME

init_db()


@app.before_request
def require_login():
    if request.endpoint in ("login", "static") or request.endpoint is None:
        return
    if not auth.is_logged_in():
        return redirect(url_for("login", next=request.path))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if auth.check_passcode(request.form.get("passcode", "")):
            auth.log_in()
            dest = request.args.get("next") or url_for("dashboard")
            return redirect(dest)
        flash("Wrong passcode.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    auth.log_out()
    return redirect(url_for("login"))


@app.context_processor
def inject_globals():
    return {"paper_mode": settings_module.get("paper_mode"), "auth_enabled": auth.auth_enabled()}


@app.route("/")
def dashboard():
    bankroll = latest_bankroll(config.STARTING_BANKROLL)
    all_preds = get_all_predictions(limit=10)
    graded = get_graded_predictions()
    ungraded_count = len([p for p in get_all_predictions() if p["result"] is None])
    bankroll_history = get_bankroll_history()

    summary = None
    if len(graded) >= 20:
        summary = {
            "flat": metrics_module.roi_flat_stake(graded),
            "kelly": metrics_module.roi_kelly_stake(graded),
            "brier": round(metrics_module.brier_score(graded), 4),
        }

    return render_template(
        "dashboard.html",
        bankroll=bankroll,
        recent_predictions=all_preds,
        ungraded_count=ungraded_count,
        graded_count=len(graded),
        summary=summary,
        min_edge=settings_module.get("min_edge"),
        leagues=len(settings_module.get("league_ids")),
        bankroll_history=bankroll_history,
        scan_status=job_state.get("scan"),
        grade_status=job_state.get("grade"),
    )


def _background_scan():
    job_state.start("scan")
    try:
        value_bets = scan_module.run()
        job_state.finish("scan", result={"count": len(value_bets)})
    except Exception as e:
        logger.exception("Manual scan failed")
        job_state.finish("scan", error=str(e))


@app.route("/scan", methods=["POST"])
def run_scan():
    if job_state.is_running("scan"):
        flash("A scan is already running -- check back in a moment.", "info")
        return redirect(url_for("dashboard"))
    threading.Thread(target=_background_scan, daemon=True).start()
    flash("Scan started in the background. This page will update automatically.", "info")
    return redirect(url_for("dashboard"))


def _background_grade():
    job_state.start("grade")
    try:
        result = grade_module.run()
        job_state.finish("grade", result=result)
    except Exception as e:
        logger.exception("Manual grading failed")
        job_state.finish("grade", error=str(e))


@app.route("/grade", methods=["POST"])
def run_grade():
    if job_state.is_running("grade"):
        flash("Grading is already running -- check back in a moment.", "info")
        return redirect(url_for("dashboard"))
    threading.Thread(target=_background_grade, daemon=True).start()
    flash("Grading started in the background. This page will update automatically.", "info")
    return redirect(url_for("dashboard"))


@app.route("/job-status/<job_name>")
def job_status(job_name):
    if job_name not in ("scan", "grade"):
        return jsonify({"error": "unknown job"}), 404
    return jsonify(job_state.get(job_name))


@app.route("/calibrate", methods=["POST"])
def run_calibrate():
    try:
        enabled_sports = settings_module.get("enabled_sports") or ["football"]
        messages = []
        for sport in enabled_sports:
            result = calibrate_module.fit_calibration(sport=sport)
            if result:
                messages.append(f"{sport}: updated using {result['trained_on_n']} graded predictions.")
            else:
                messages.append(f"{sport}: not enough graded predictions yet (need 50+).")
        flash(" | ".join(messages), "info")
    except Exception as e:
        logger.exception("Calibration failed")
        flash(f"Calibration failed: {e}", "error")
    return redirect(url_for("dashboard"))


@app.route("/predictions")
def predictions():
    result_filter = request.args.get("result", "all")
    market_filter = request.args.get("market", "all")

    preds = get_all_predictions()

    if result_filter == "pending":
        preds = [p for p in preds if p["result"] is None]
    elif result_filter in ("WON", "LOST"):
        preds = [p for p in preds if p["result"] == result_filter]

    if market_filter != "all":
        preds = [p for p in preds if p["market"] == market_filter]

    all_markets = sorted({p["market"] for p in get_all_predictions()})

    return render_template(
        "predictions.html",
        predictions=preds,
        result_filter=result_filter,
        market_filter=market_filter,
        all_markets=all_markets,
    )


@app.route("/predictions/export.csv")
def export_csv():
    preds = get_all_predictions()
    output = io.StringIO()
    if preds:
        writer = csv.DictWriter(output, fieldnames=list(preds[0].keys()))
        writer.writeheader()
        writer.writerows(preds)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=footy_edge_predictions.csv"},
    )


@app.route("/metrics")
def metrics_page():
    graded = get_graded_predictions()
    data = None
    if len(graded) >= 20:
        data = {
            "brier": round(metrics_module.brier_score(graded), 4),
            "flat": metrics_module.roi_flat_stake(graded),
            "kelly": metrics_module.roi_kelly_stake(graded),
            "by_market": metrics_module.win_rate_by_market(graded),
        }
    return render_template("metrics.html", data=data, graded_count=len(graded))


@app.route("/settings", methods=["GET", "POST"])
def settings_page():
    if request.method == "POST":
        selected_leagues = [int(lid) for lid in request.form.getlist("league_ids")]
        selected_sports = request.form.getlist("enabled_sports")
        updates = {
            "min_edge": float(request.form.get("min_edge", 4)) / 100,
            "kelly_fraction": float(request.form.get("kelly_fraction", 25)) / 100,
            "days_ahead": int(request.form.get("days_ahead", 3)),
            "league_ids": selected_leagues or settings_module.DEFAULTS["league_ids"],
            "enabled_sports": selected_sports or settings_module.DEFAULTS["enabled_sports"],
            "auto_scan_enabled": request.form.get("auto_scan_enabled") == "on",
            "scan_time": request.form.get("scan_time", "08:00"),
            "grade_time": request.form.get("grade_time", "23:00"),
        }
        settings_module.save_settings(updates)
        scheduler_module.reload_scheduler()
        flash("Settings saved. Changes apply on your next scan (schedule changes apply immediately).", "success")
        return redirect(url_for("settings_page"))

    current = settings_module.load_settings()
    return render_template(
        "settings.html",
        current=current,
        all_leagues=settings_module.ALL_LEAGUES,
        all_sports=settings_module.ALL_SPORTS,
    )


scheduler_module.init_scheduler()

if __name__ == "__main__":
    if os.environ.get("FOOTY_EDGE_DEBUG") == "1":
        logger.info("Starting in Flask debug mode (development server).")
        app.run(host="0.0.0.0", port=5000, debug=True)
    else:
        from waitress import serve
        logger.info("Starting Footy Edge Bot on http://0.0.0.0:5000 (waitress production server)")
        print("Footy Edge Bot running at http://localhost:5000")
        print("On your LAN: http://<this-pc-local-ip>:5000")
        serve(app, host="0.0.0.0", port=5000)
