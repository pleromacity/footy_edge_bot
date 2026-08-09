"""
Run this if main.py throws a 403 or empty-data error. It checks two things
that commonly cause that: (1) whether your API-Football subscription/key is
actually active, and (2) whether the SEASON year in config.py matches what
your plan is actually allowed to query.

Usage:
    python diagnose.py
"""

import requests
from config import API_FOOTBALL_KEY

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_FOOTBALL_KEY}


def check_status():
    print("Checking account status...")
    resp = requests.get(f"{BASE_URL}/status", headers=HEADERS, timeout=20)
    print(f"  HTTP {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json().get("response", {})
        acct = data.get("account", {})
        sub = data.get("subscription", {})
        reqs = data.get("requests", {})
        print(f"  Account: {acct.get('firstname')} {acct.get('lastname')} ({acct.get('email')})")
        print(f"  Plan: {sub.get('plan')}  Active: {sub.get('active')}  End: {sub.get('end')}")
        print(f"  Requests used today: {reqs.get('current')}/{reqs.get('limit_day')}")
    else:
        print(f"  Response: {resp.text[:300]}")
        print("  -> This usually means the key itself is wrong or the account isn't verified yet.")


def check_available_seasons(league_id: int = 39):
    print(f"\nChecking available seasons for league {league_id} (Premier League)...")
    resp = requests.get(f"{BASE_URL}/leagues", headers=HEADERS, params={"id": league_id}, timeout=20)
    print(f"  HTTP {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json().get("response", [])
        if not data:
            print("  No data returned -- your plan may not include this league.")
            return
        seasons = data[0].get("seasons", [])
        current = [s["year"] for s in seasons if s.get("current")]
        all_years = [s["year"] for s in seasons]
        print(f"  All seasons your plan can see: {all_years}")
        print(f"  Currently marked 'current' season: {current}")
        print(f"\n  -> If this differs from SEASON in config.py, update config.py to match.")
    else:
        print(f"  Response: {resp.text[:300]}")


if __name__ == "__main__":
    check_status()
    check_available_seasons()
