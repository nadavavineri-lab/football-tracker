"""
Local web UI for browsing scraped games: an "upcoming" tab and an
"archive" tab, filterable by club, age group and season/year.

Run `python scraper.py` at least once first to populate data/games.json,
then `python app.py` and open http://127.0.0.1:5000
"""
import json
import os
import subprocess
import sys
import threading
from datetime import datetime

from flask import Flask, jsonify, render_template, request

from config import CLUBS, DATA_FILE

app = Flask(__name__)

refresh_lock = threading.Lock()
refresh_state = {"running": False, "last_result": None}


def load_games():
    if not os.path.exists(DATA_FILE):
        return {"updated_at": None, "games": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


@app.route("/")
def index():
    return render_template("index.html", clubs=CLUBS)


@app.route("/api/games")
def api_games():
    data = load_games()
    games = data.get("games", [])

    club = request.args.get("club")
    age_group = request.args.get("age_group")
    season = request.args.get("season")

    def keep(g):
        if club and g.get("club_key") != club:
            return False
        if age_group and g.get("age_group") != age_group:
            return False
        if season and g.get("season_label") != season:
            return False
        return True

    games = [g for g in games if keep(g)]

    now_iso = datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%H:%M")

    def is_upcoming(g):
        d = g.get("date")
        if not d:
            return False
        if d > now_iso:
            return True
        if d == now_iso:
            return (g.get("time") or "00:00") >= now_time
        return False

    upcoming = sorted([g for g in games if is_upcoming(g)],
                       key=lambda g: (g.get("date") or "", g.get("time") or ""))
    archive = sorted([g for g in games if not is_upcoming(g)],
                      key=lambda g: (g.get("date") or "", g.get("time") or ""), reverse=True)

    return jsonify({
        "updated_at": data.get("updated_at"),
        "upcoming": upcoming,
        "archive": archive,
        "filters": {
            "clubs": sorted({g.get("club_name") for g in data.get("games", []) if g.get("club_name")}),
            "club_keys": {g.get("club_name"): g.get("club_key") for g in data.get("games", [])},
            "age_groups": sorted({g.get("age_group") for g in data.get("games", []) if g.get("age_group")}),
            "seasons": sorted({g.get("season_label") for g in data.get("games", []) if g.get("season_label")}),
        },
    })


def _run_refresh():
    with refresh_lock:
        refresh_state["running"] = True
    try:
        result = subprocess.run(
            [sys.executable, "scraper.py"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True, text=True, timeout=1800,
        )
        refresh_state["last_result"] = {
            "ok": result.returncode == 0,
            "stdout": result.stdout[-4000:],
            "stderr": result.stderr[-4000:],
        }
    except Exception as e:
        refresh_state["last_result"] = {"ok": False, "stdout": "", "stderr": str(e)}
    finally:
        refresh_state["running"] = False


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    if refresh_state["running"]:
        return jsonify({"started": False, "reason": "already running"}), 409
    thread = threading.Thread(target=_run_refresh, daemon=True)
    thread.start()
    return jsonify({"started": True})


@app.route("/api/refresh/status")
def api_refresh_status():
    return jsonify(refresh_state)


if __name__ == "__main__":
    app.run(debug=True)
