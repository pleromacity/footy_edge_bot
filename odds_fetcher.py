"""
Pulls bookmaker odds from The Odds API (free tier) for value comparison.

Note: The Odds API aggregates major global bookmakers (Pinnacle, Bet365, etc.),
not SportyBet/Bet9ja directly -- there is no public odds API for Nigerian books.
We use this as a proxy "sharp market" consensus to compute fair, de-vigged
probabilities. You still place the actual bet on whichever Nigerian platform
you use, and it's worth spot-checking their price against what this shows --
prices move and local books sometimes lag or differ from the global market.
"""

import requests

from config import ODDS_API_KEY, ODDS_API_SPORT_KEYS

BASE_URL = "https://api.the-odds-api.com/v4/sports"


def get_odds_for_sport(sport_key: str) -> list[dict]:
    url = f"{BASE_URL}/{sport_key}/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "eu,uk",
        "markets": "h2h,totals",
        "oddsFormat": "decimal",
    }
    resp = requests.get(url, params=params, timeout=20)
    if resp.status_code != 200:
        print(f"  [odds] {sport_key}: {resp.status_code} {resp.text[:200]}")
        return []
    return resp.json()


def get_all_odds() -> list[dict]:
    all_events = []
    for sport_key in ODDS_API_SPORT_KEYS:
        events = get_odds_for_sport(sport_key)
        all_events.extend(events)
    return all_events


def find_best_odds(events: list[dict], home_team: str, away_team: str) -> dict | None:
    """Fuzzy-matches a fixture to an odds event by team names and returns the
    best available decimal odds per outcome across all listed bookmakers."""

    def norm(name: str) -> str:
        return name.lower().replace("fc", "").replace(".", "").strip()

    target_home, target_away = norm(home_team), norm(away_team)

    for event in events:
        eh, ea = norm(event.get("home_team", "")), norm(event.get("away_team", ""))
        if target_home in eh or eh in target_home:
            if target_away in ea or ea in target_away:
                return _extract_best_prices(event)
    return None


def _extract_best_prices(event: dict) -> dict:
    best = {
        "home_win": (0.0, None), "draw": (0.0, None), "away_win": (0.0, None),
        "over_2.5": (0.0, None), "under_2.5": (0.0, None),
    }
    for bookmaker in event.get("bookmakers", []):
        bk_name = bookmaker.get("title", "unknown")
        for market in bookmaker.get("markets", []):
            if market["key"] == "h2h":
                outcomes = {o["name"]: o["price"] for o in market["outcomes"]}
                mapping = {
                    event["home_team"]: "home_win",
                    event["away_team"]: "away_win",
                    "Draw": "draw",
                }
                for name, price in outcomes.items():
                    slot = mapping.get(name)
                    if slot and price > best[slot][0]:
                        best[slot] = (price, bk_name)
            elif market["key"] == "totals":
                for o in market["outcomes"]:
                    if o.get("point") == 2.5:
                        slot = "over_2.5" if o["name"] == "Over" else "under_2.5"
                        if o["price"] > best[slot][0]:
                            best[slot] = (o["price"], bk_name)
    return best
