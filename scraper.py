"""
Scrapes game schedules/results for tracked clubs from football.org.il
(the Israel Football Association's official site) across all of that
club's age-group teams, for a range of seasons.

football.org.il renders its club/team pages client-side, and blocks plain
HTTP fetches (no real browser => 403), so this uses Playwright to drive an
actual Chromium browser. It tries two extraction strategies per page:

  1. Sniff the JSON the page's own API calls return (most reliable).
  2. Fall back to reading the rendered page text and parsing it with
     heuristics (date/time/score patterns).

IMPORTANT: this scraper was written from the site's known URL patterns
(discovered via search-engine indexing) without the ability to load the
live site from the environment that authored it. Run with --debug on
first use: it dumps every team's raw HTML/JSON/text under data/debug/ so
that if 0 games are parsed for a team, you can inspect the dump and adjust
parse_team_page_from_text()/parse_json_for_games() accordingly.

Usage:
    python scraper.py                       # scrape default season range
    python scraper.py --years 2024 2026     # scrape seasons starting 2024..2026
    python scraper.py --clubs kadima_zoran  # only one club
    python scraper.py --debug               # dump raw pages to data/debug/
    python scraper.py --headful             # show the browser window
"""
import argparse
import json
import os
import re
from datetime import datetime

from config import (
    BASE_URL,
    CLUBS,
    DATA_FILE,
    DEBUG_DIR,
    DEFAULT_YEAR_RANGE,
    season_id_for_year,
    year_for_season_id,
)

DATE_RE = re.compile(r"^\s*(\d{1,2})[./](\d{1,2})[./](\d{2,4})\s*$")
TIME_RE = re.compile(r"^\s*([01]?\d|2[0-3]):([0-5]\d)\s*$")
SCORE_RE = re.compile(r"^\s*(\d{1,2})\s*[-:]\s*(\d{1,2})\s*$")
HEBREW_RE = re.compile(r"[֐-׿]")
NOISE_LINES = {
    "פרטים", "מגרש", "ליגה", "עונה", "תוצאה", "שחקנים", "סטטיסטיקה",
    "כניסה", "תפריט", "חיפוש", "טבלה", "לוח משחקים", "משחקים", "עמוד ראשי",
}


def log(msg):
    print(f"[scraper] {msg}")


def ensure_dirs():
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    os.makedirs(DEBUG_DIR, exist_ok=True)


def normalize_date(d, m, y):
    y = int(y)
    if y < 100:
        y += 2000
    try:
        return datetime(y, int(m), int(d)).strftime("%Y-%m-%d")
    except ValueError:
        return None


def looks_like_team_name(line):
    line = line.strip()
    if len(line) < 2 or len(line) > 40:
        return False
    if not HEBREW_RE.search(line):
        return False
    if line in NOISE_LINES:
        return False
    if DATE_RE.match(line) or TIME_RE.match(line) or SCORE_RE.match(line):
        return False
    return True


def parse_team_page_from_text(full_text):
    """Heuristic fallback parser: groups lines around each date occurrence."""
    lines = [l.strip() for l in full_text.splitlines() if l.strip()]
    date_idxs = [i for i, l in enumerate(lines) if DATE_RE.match(l)]
    games = []
    for n, idx in enumerate(date_idxs):
        end = date_idxs[n + 1] if n + 1 < len(date_idxs) else min(idx + 12, len(lines))
        block = lines[idx:end]
        m = DATE_RE.match(block[0])
        date_iso = normalize_date(*m.groups())
        time_str = None
        score = None
        team_names = []
        for l in block[1:]:
            if time_str is None and TIME_RE.match(l):
                time_str = l
                continue
            if score is None and SCORE_RE.match(l):
                score = l
                continue
            if looks_like_team_name(l):
                team_names.append(l)
        if not date_iso:
            continue
        home_team = team_names[0] if len(team_names) > 0 else None
        away_team = team_names[1] if len(team_names) > 1 else None
        home_score = away_score = None
        if score:
            sm = SCORE_RE.match(score)
            home_score, away_score = int(sm.group(1)), int(sm.group(2))
        games.append({
            "date": date_iso,
            "time": time_str,
            "home_team": home_team,
            "away_team": away_team,
            "home_score": home_score,
            "away_score": away_score,
            "raw_block": block,
        })
    return games


def parse_json_for_games(json_bodies):
    """Best-effort search through captured JSON API responses for a list of
    fixture-like objects (dicts containing a recognizable date field)."""
    games = []
    date_keys = {"date", "gameDate", "matchDate", "game_date", "eventDate"}
    for body in json_bodies:
        candidates = []
        if isinstance(body, list):
            candidates = body
        elif isinstance(body, dict):
            for v in body.values():
                if isinstance(v, list):
                    candidates.extend(v)
        for item in candidates:
            if not isinstance(item, dict):
                continue
            date_val = None
            for k in item:
                if k in date_keys or ("date" in k.lower()):
                    date_val = item[k]
                    break
            if not date_val:
                continue
            games.append(item)
    return games


def collect_team_links(page):
    """Return list of (team_id, season_id, label) from a club page."""
    anchors = page.query_selector_all("a[href*='team-details']")
    results = []
    seen = set()
    for a in anchors:
        href = a.get_attribute("href") or ""
        m = re.search(r"team_id=(\d+).*season_id=(\d+)", href)
        if not m:
            m2 = re.search(r"team_id=(\d+)", href)
            if not m2:
                continue
            team_id = m2.group(1)
            season_id = None
        else:
            team_id, season_id = m.group(1), m.group(2)
        label = (a.inner_text() or "").strip()
        key = (team_id, season_id)
        if key in seen:
            continue
        seen.add(key)
        results.append({"team_id": team_id, "season_id": season_id, "label": label})
    return results


def scrape_team(context, club, team_id, season_id, debug=False):
    page = context.new_page()
    json_bodies = []

    def on_response(response):
        try:
            ctype = response.headers.get("content-type", "")
            if "json" in ctype:
                json_bodies.append(response.json())
        except Exception:
            pass

    page.on("response", on_response)
    url = f"{BASE_URL}/team-details/?team_id={team_id}&season_id={season_id}"
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
    except Exception as e:
        log(f"  ! failed to load team {team_id}: {e}")
        page.close()
        return []

    full_text = page.inner_text("body")

    if debug:
        with open(f"{DEBUG_DIR}/team_{team_id}_{season_id}.html", "w", encoding="utf-8") as f:
            f.write(page.content())
        with open(f"{DEBUG_DIR}/team_{team_id}_{season_id}.txt", "w", encoding="utf-8") as f:
            f.write(full_text)
        with open(f"{DEBUG_DIR}/team_{team_id}_{season_id}.json", "w", encoding="utf-8") as f:
            json.dump(json_bodies, f, ensure_ascii=False, indent=2)

    page.close()

    games_from_json = parse_json_for_games(json_bodies)
    games = games_from_json if games_from_json else parse_team_page_from_text(full_text)

    for g in games:
        g["club_key"] = club["key"]
        g["club_name"] = club["name"]
        g["team_id"] = team_id
        g["season_id"] = season_id
        g["season_label"] = f"{year_for_season_id(int(season_id))}/{year_for_season_id(int(season_id)) + 1}"

    return games


def scrape_club_season(context, club, season_id, debug=False):
    page = context.new_page()
    url = f"{BASE_URL}/clubs/club/?club_id={club['club_id']}&season_id={season_id}"
    log(f"Club page: {club['name']} season_id={season_id} -> {url}")
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
    except Exception as e:
        log(f"  ! failed to load club page: {e}")
        page.close()
        return []

    if debug:
        with open(f"{DEBUG_DIR}/club_{club['club_id']}_{season_id}.html", "w", encoding="utf-8") as f:
            f.write(page.content())

    team_links = collect_team_links(page)
    page.close()
    log(f"  found {len(team_links)} team(s)")

    all_games = []
    for t in team_links:
        sid = t["season_id"] or str(season_id)
        log(f"  scraping team_id={t['team_id']} ({t['label']}) season_id={sid}")
        games = scrape_team(context, club, t["team_id"], sid, debug=debug)
        for g in games:
            g["age_group"] = t["label"]
        log(f"    -> {len(games)} game(s)")
        all_games.extend(games)
    return all_games


def merge_games(existing, new_games):
    def key(g):
        return (g.get("club_key"), g.get("team_id"), g.get("date"), g.get("time"),
                g.get("home_team"), g.get("away_team"))

    by_key = {key(g): g for g in existing}
    for g in new_games:
        by_key[key(g)] = g
    return list(by_key.values())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", nargs=2, type=int, metavar=("START", "END"),
                         default=list(DEFAULT_YEAR_RANGE),
                         help="Season start-year range to scrape, inclusive")
    parser.add_argument("--clubs", nargs="+", choices=[c["key"] for c in CLUBS],
                         help="Limit to specific club keys")
    parser.add_argument("--debug", action="store_true",
                         help="Dump raw HTML/JSON/text per page to data/debug/")
    parser.add_argument("--headful", action="store_true",
                         help="Show the browser window instead of running headless")
    args = parser.parse_args()

    ensure_dirs()

    from playwright.sync_api import sync_playwright

    clubs = [c for c in CLUBS if not args.clubs or c["key"] in args.clubs]
    start_year, end_year = args.years

    existing = []
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f).get("games", [])

    all_games = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headful)
        context = browser.new_context(locale="he-IL")
        for club in clubs:
            for year in range(start_year, end_year + 1):
                season_id = season_id_for_year(year)
                games = scrape_club_season(context, club, season_id, debug=args.debug)
                all_games.extend(games)
        browser.close()

    merged = merge_games(existing, all_games)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "games": merged,
        }, f, ensure_ascii=False, indent=2)

    log(f"Done. {len(all_games)} game(s) scraped this run, {len(merged)} total stored in {DATA_FILE}")


if __name__ == "__main__":
    main()
