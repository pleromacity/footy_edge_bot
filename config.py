"""
Central configuration for Footy Edge Bot.

Get your free API keys here:
  - API-Football (fixtures, team stats): https://www.api-football.com/  (free tier: 100 req/day)
  - The Odds API (bookmaker odds):        https://the-odds-api.com/     (free tier: 500 req/month)

Paste your keys below, or set them as environment variables of the same name
(recommended if you don't want the key sitting in a plain text file).
"""

import os

API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY", "PASTE_YOUR_API_FOOTBALL_KEY_HERE")
ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "PASTE_YOUR_ODDS_API_KEY_HERE")

# API-Football league IDs to scan. Add/remove as you like.
# 39=EPL, 140=La Liga, 78=Bundesliga, 135=Serie A, 61=Ligue 1, 88=Eredivisie, 94=Primeira Liga
LEAGUE_IDS = [39, 140, 78, 135, 61, 88, 94]

# Current season year (API-Football uses the start year of the season, e.g. 2025 for 2025/26)
SEASON = 2025

# How many days ahead to pull fixtures for
DAYS_AHEAD = 3

# The Odds API sport key for soccer (it splits by competition; "soccer_epl" etc.
# also exist, but this pulls upcoming soccer broadly across supported leagues)
ODDS_API_SPORT_KEYS = [
    "soccer_epl",
    "soccer_spain_la_liga",
    "soccer_germany_bundesliga",
    "soccer_italy_serie_a",
    "soccer_france_ligue_one",
    "soccer_netherlands_eredivisie",
    "soccer_portugal_primeira_liga",
]

# Minimum edge (model probability minus de-vigged market probability) required
# to flag a bet as "value". Keep this conservative — small samples lie.
MIN_EDGE = 0.04  # 4 percentage points

# Fractional Kelly multiplier. 1.0 = full Kelly (aggressive, high variance).
# 0.25-0.5 is what most professional bettors actually use.
KELLY_FRACTION = 0.25

# Starting bankroll for paper-mode simulation (in your currency of choice, e.g. NGN)
STARTING_BANKROLL = 100000

# PAPER MODE: when True, the bot only logs picks and simulated stakes.
# It never assumes real money was staked. Flip to False once you've
# validated the model with real graded results (see grade.py + README).
PAPER_MODE = True

DB_PATH = "data/footy_edge.db"
