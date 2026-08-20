"""
Central configuration for Footy Edge Bot.

Get your free API keys here:
  - API-Football (fixtures, team stats): https://www.api-football.com/  (free tier: 100 req/day)
  - The Odds API (bookmaker odds):        https://the-odds-api.com/     (free tier: 500 req/month)

Set them as environment variables or in a local .env file. Do not commit real
keys to source control.
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

base_dir = Path(__file__).resolve().parent
if load_dotenv is not None and "PYTEST_CURRENT_TEST" not in os.environ:
    load_dotenv(base_dir / ".env")


def _require_env(name: str) -> str:
    """Read an env var without raising. Missing/blank values are validated
    later, only in the code paths that actually need them (see
    require_api_keys() below) -- not at import time, since config.py gets
    imported by modules (settings, storage) that have nothing to do with
    these two APIs, including the test suite."""
    return os.environ.get(name, "")


API_FOOTBALL_KEY = _require_env("API_FOOTBALL_KEY")
ODDS_API_KEY = _require_env("ODDS_API_KEY")

missing = [
    name for name, value in [
        ("API_FOOTBALL_KEY", API_FOOTBALL_KEY),
        ("ODDS_API_KEY", ODDS_API_KEY),
    ] if not value
]
if missing:
    raise RuntimeError(
        f"Missing required environment variable(s): {', '.join(missing)}. "
        "Add them to your shell, a local .env file, or Render's Environment tab."
    )

# API-Sports (the company behind API-Football) provides NBA data under the
# same account -- https://v2.nba.api-sports.io -- so the same key works for
# both. It's tracked as a separate 100-req/day free quota from API-Football,
# so using NBA doesn't eat into your football requests or vice versa. You do
# need to add the (free) NBA API to your api-sports.io dashboard once before
# it'll accept requests -- see README.
API_SPORTS_KEY = API_FOOTBALL_KEY
NBA_SEASON = 2025  # API-Sports NBA uses the year the season starts (2025 = 2025-26)
NBA_ODDS_SPORT_KEY = "basketball_nba"  # The Odds API's sport key for NBA


def require_api_keys():
    """Call this before anything that actually hits API-Football or The Odds
    API (e.g. at the start of a scan). Raises a clear error if a key is
    missing, instead of the request failing later with a confusing 401."""
    missing = [
        name for name, value in [
            ("API_FOOTBALL_KEY", API_FOOTBALL_KEY),
            ("ODDS_API_KEY", ODDS_API_KEY),
        ] if not value
    ]
    if missing:
        raise RuntimeError(
            f"Missing required environment variable(s): {', '.join(missing)}. "
            "Add them to your shell, a local .env file, or Render's Environment tab."
        )

LEAGUE_IDS = [39, 140, 78, 135, 61, 88, 94]
SEASON = 2025
DAYS_AHEAD = 3
ODDS_API_SPORT_KEYS = [
    "soccer_epl", "soccer_spain_la_liga", "soccer_germany_bundesliga",
    "soccer_italy_serie_a", "soccer_france_ligue_one",
    "soccer_netherlands_eredivisie", "soccer_portugal_primeira_liga",
]
MIN_EDGE = 0.04
KELLY_FRACTION = 0.25
STARTING_BANKROLL = 100000
PAPER_MODE = True
DB_PATH = "data/footy_edge.db"
