"""
Runtime-adjustable settings. config.py holds the hardcoded defaults (used
the first time the app runs); this module lets you change min edge, Kelly
fraction, and which leagues to scan from the web dashboard without editing
code or restarting anything -- changes take effect on the next scan.

Settings are stored in data/settings.json and layered on top of config.py's
defaults, so anything you haven't changed just falls back to config.py.
"""

import json
import os

import config

SETTINGS_PATH = "data/settings.json"

DEFAULTS = {
    "min_edge": config.MIN_EDGE,
    "kelly_fraction": config.KELLY_FRACTION,
    "paper_mode": config.PAPER_MODE,
    "league_ids": config.LEAGUE_IDS,
    "days_ahead": config.DAYS_AHEAD,
    "auto_scan_enabled": False,
    "scan_time": "08:00",
    "grade_time": "23:00",
    "enabled_sports": ["football"],  # add "nba" once you've set it up -- see README
}

ALL_SPORTS = {
    "football": "Football (soccer)",
    "nba": "Basketball (NBA)",
}

ALL_LEAGUES = {
    39: "English Premier League",
    140: "Spanish La Liga",
    78: "German Bundesliga",
    135: "Italian Serie A",
    61: "French Ligue 1",
    88: "Dutch Eredivisie",
    94: "Portuguese Primeira Liga",
    40: "English Championship",
    203: "Turkish Super Lig",
    71: "Brazilian Serie A",
    128: "Argentine Primera Division",
}


def load_settings() -> dict:
    if not os.path.exists(SETTINGS_PATH):
        return dict(DEFAULTS)
    try:
        with open(SETTINGS_PATH) as f:
            saved = json.load(f)
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULTS)
    merged = dict(DEFAULTS)
    merged.update(saved)
    return merged


def save_settings(updates: dict):
    current = load_settings()
    current.update(updates)
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w") as f:
        json.dump(current, f, indent=2)
    return current


def get(key: str):
    return load_settings().get(key, DEFAULTS.get(key))
