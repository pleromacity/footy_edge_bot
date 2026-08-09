"""
Pulls fixtures and team statistics from API-Football.
"""

import datetime as dt
import requests

import settings as settings_module
from config import API_FOOTBALL_KEY, SEASON

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_FOOTBALL_KEY}


def _get(endpoint: str, params: dict) -> dict:
    resp = requests.get(f"{BASE_URL}/{endpoint}", headers=HEADERS, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()


def get_upcoming_fixtures() -> list[dict]:
    """Returns upcoming fixtures across all configured leagues for the next
    N days (N and the league list are read from settings.py, so changes made
    in the web dashboard apply without restarting anything)."""
    league_ids = settings_module.get("league_ids")
    days_ahead = settings_module.get("days_ahead")
    today = dt.date.today()
    end = today + dt.timedelta(days=days_ahead)
    fixtures = []
    for league_id in league_ids:
        data = _get(
            "fixtures",
            {
                "league": league_id,
                "season": SEASON,
                "from": today.isoformat(),
                "to": end.isoformat(),
            },
        )
        for item in data.get("response", []):
            fixtures.append(item)
    return fixtures


def get_team_stats(team_id: int, league_id: int) -> dict:
    """Returns season stats for a team within a specific league: goals for/against,
    home/away split, clean sheets, etc."""
    data = _get(
        "teams/statistics",
        {"team": team_id, "league": league_id, "season": SEASON},
    )
    return data.get("response", {})


def get_finished_fixture_result(fixture_id: int) -> dict | None:
    """Used by grade.py once a match has kicked off/finished, to fetch the final score."""
    data = _get("fixtures", {"id": fixture_id})
    response = data.get("response", [])
    if not response:
        return None
    fixture = response[0]
    status = fixture["fixture"]["status"]["short"]
    if status not in ("FT", "AET", "PEN"):
        return None  # not finished yet
    goals = fixture["goals"]
    return {"home_goals": goals["home"], "away_goals": goals["away"]}
