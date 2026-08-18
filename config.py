# Clubs to track on football.org.il (site of the Israel Football Association).
# club_id values were found via search-engine indexing of football.org.il pages:
#   - Kadima-Zoran: https://www.football.org.il/clubs/club/?club_id=4015
#   - Pro Soccer HaSharon: https://www.football.org.il/clubs/club/?club_id=8555
# If "פרו סוקר" refers to a different branch/club than "Pro Soccer HaSharon",
# find its club_id (open its page on football.org.il and read club_id from the
# URL) and update it below.
CLUBS = [
    {"key": "kadima_zoran", "name": "קדימה-צורן", "club_id": 4015},
    {"key": "pro_soccer", "name": "פרו סוקר", "club_id": 8555},
]

BASE_URL = "https://www.football.org.il"

# football.org.il season_id appears to equal (season_start_year - 1998),
# e.g. season 2025/2026 -> season_id 27, season 2013/2014 -> season_id 15.
SEASON_ID_YEAR_OFFSET = 1998


def season_id_for_year(start_year: int) -> int:
    return start_year - SEASON_ID_YEAR_OFFSET


def year_for_season_id(season_id: int) -> int:
    return season_id + SEASON_ID_YEAR_OFFSET


# Default range of seasons (by start year) to scrape when none is specified.
DEFAULT_YEAR_RANGE = (2023, 2026)  # inclusive start, inclusive end

DATA_FILE = "data/games.json"
DEBUG_DIR = "data/debug"
