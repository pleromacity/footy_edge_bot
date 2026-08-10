"""
Pulls upcoming NBA games and team scoring history from API-Sports' NBA
product (same account as API-Football, separate free 100-req/day quota).

Docs: https://api-sports.io/documentation/nba/v2

Unlike API-Football's teams/statistics endpoint (which only gives a team's
own scoring, not what they conceded), we build both sides of the picture by
pulling each team's recent finished games directly and reading both scores
off each one. This also naturally gives us home/away splits.
"""

import datetime as dt

import requests

from config import API_SPORTS_KEY, NBA_SEASON

BASE_URL = "https://v2.nba.api-sports.io"
HEADERS = {"x-apisports-key": API_SPORTS_KEY}


def _get(path: str, params: dict) -> list[dict]:
    resp = requests.get(f"{BASE_URL}/{path}", headers=HEADERS, params=params, timeout=20)
    if resp.status_code != 200:
        print(f"  [nba] {path}: {resp.status_code} {resp.text[:200]}")
        return []
    return resp.json().get("response", [])


def get_upcoming_games(days_ahead: int = 3) -> list[dict]:
    """Returns raw game entries for the next `days_ahead` days, NS (not
    started) status only."""
    games = []
    today = dt.date.today()
    for offset in range(days_ahead + 1):
        day = (today + dt.timedelta(days=offset)).isoformat()
        for g in _get("games", {"date": day}):
            if g.get("status", {}).get("short") == "NS":
                games.append(g)
    return games


def get_team_recent_games(team_id: int, last_n: int = 20) -> list[dict]:
    """Finished games for a team this season, most recent last_n. Used to
    derive scoring averages (see nba_model.extract_team_strength)."""
    games = _get("games", {"team": team_id, "season": NBA_SEASON})
    finished = [g for g in games if g.get("status", {}).get("short") == "FT"]
    finished.sort(key=lambda g: g.get("date", {}).get("start", ""))
    return finished[-last_n:]


def get_finished_game_result(game_id: int) -> dict | None:
    """Returns {'home_points': int, 'away_points': int} once the game has
    finished, or None if it hasn't yet."""
    games = _get("games", {"id": game_id})
    if not games:
        return None
    g = games[0]
    if g.get("status", {}).get("short") != "FT":
        return None
    home_pts = g.get("scores", {}).get("home", {}).get("points")
    away_pts = g.get("scores", {}).get("visitors", {}).get("points")
    if home_pts is None or away_pts is None:
        return None
    return {"home_points": home_pts, "away_points": away_pts}
