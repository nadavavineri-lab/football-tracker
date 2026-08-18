"""
Quick diagnostic: summarizes what actually ended up in data/games.json,
plus a rundown of data/debug/ dumps (if you ran the scraper with --debug),
flagging pages that likely failed to yield any games so it's obvious where
the scraper's parsing needs fixing.

Usage:
    python inspect_data.py
"""
import json
import os

from config import DATA_FILE, DEBUG_DIR


def main():
    if not os.path.exists(DATA_FILE):
        print(f"{DATA_FILE} does not exist yet — run `python scraper.py --debug` first.")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    games = data.get("games", [])
    print(f"updated_at: {data.get('updated_at')}")
    print(f"total games: {len(games)}\n")

    by_club = {}
    for g in games:
        by_club.setdefault(g.get("club_name"), []).append(g)

    for club_name, club_games in sorted(by_club.items(), key=lambda kv: str(kv[0])):
        seasons = sorted({g.get("season_label") for g in club_games if g.get("season_label")})
        age_groups = sorted({g.get("age_group") for g in club_games if g.get("age_group")})
        team_ids = sorted({g.get("team_id") for g in club_games if g.get("team_id")})
        print(f"club: {club_name!r}  ({len(club_games)} games)")
        print(f"  team_ids scraped: {team_ids}")
        print(f"  age_groups found: {age_groups}")
        print(f"  seasons found:    {seasons}")
        print()

    if not games:
        print("No games at all were parsed from any page — almost certainly the")
        print("fallback text-parsing heuristics in scraper.py don't match this")
        print("site's actual rendered layout. Check data/debug/*.txt below.\n")

    if os.path.isdir(DEBUG_DIR):
        print("--- data/debug contents ---")
        files = sorted(os.listdir(DEBUG_DIR))
        if not files:
            print("(empty — re-run `python scraper.py --debug`)")
        for fn in files:
            path = os.path.join(DEBUG_DIR, fn)
            size = os.path.getsize(path)
            flag = "  <-- suspiciously small, page may not have loaded" if size < 500 else ""
            print(f"  {fn}  ({size} bytes){flag}")
    else:
        print(f"\nNo {DEBUG_DIR} folder found — run with `python scraper.py --debug` to get one.")


if __name__ == "__main__":
    main()
