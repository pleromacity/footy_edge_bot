"""
Footy Edge Bot -- main entry point.

Fetches upcoming fixtures, computes model probabilities, compares against
de-vigged bookmaker odds, and logs every value bet found (paper mode by
default -- see config.PAPER_MODE).

Usage:
    python main.py
"""

import time

import config
import settings as settings_module
from data_fetcher import get_upcoming_fixtures, get_team_stats
from odds_fetcher import get_all_odds, find_best_odds
from model import extract_team_strength, expected_goals, outcome_probabilities
from value_engine import find_value_bets
from kelly import stake_amount
from calibrate import apply_calibration
from storage import init_db, insert_prediction, latest_bankroll, log_bankroll
from logging_setup import setup_logging

logger = setup_logging()


def market_key_to_prob_key(market: str) -> str:
    return market.lower()


def run():
    init_db()
    bankroll = latest_bankroll(config.STARTING_BANKROLL)
    if bankroll == config.STARTING_BANKROLL:
        log_bankroll(bankroll, note="initial")

    paper_mode = settings_module.get("paper_mode")
    min_edge = settings_module.get("min_edge")

    print(f"Bankroll: {bankroll}  |  Paper mode: {paper_mode}\n")
    logger.info(f"Scan started. Bankroll={bankroll}, paper_mode={paper_mode}, min_edge={min_edge}")

    print("Fetching upcoming fixtures...")
    fixtures = get_upcoming_fixtures()
    print(f"  Found {len(fixtures)} fixtures across {len(settings_module.get('league_ids'))} leagues.")

    print("Fetching bookmaker odds...")
    odds_events = get_all_odds()
    print(f"  Found odds for {len(odds_events)} events.\n")

    all_value_bets = []

    for fx in fixtures:
        league_id = fx["league"]["id"]
        league_name = fx["league"]["name"]
        home = fx["teams"]["home"]
        away = fx["teams"]["away"]
        fixture_id = fx["fixture"]["id"]
        kickoff = fx["fixture"]["date"]

        best_odds = find_best_odds(odds_events, home["name"], away["name"])
        if not best_odds:
            continue  # no odds available for this match yet, skip

        try:
            home_stats = get_team_stats(home["id"], league_id)
            away_stats = get_team_stats(away["id"], league_id)
        except Exception as e:
            print(f"  [skip] {home['name']} vs {away['name']}: stats fetch failed ({e})")
            logger.warning(f"Stats fetch failed for {home['name']} vs {away['name']}: {e}")
            continue

        home_strength = extract_team_strength(home_stats)
        away_strength = extract_team_strength(away_stats)
        home_xg, away_xg = expected_goals(home_strength, away_strength)
        probs = outcome_probabilities(home_xg, away_xg)

        model_probs = {
            "home_win": probs["home_win"], "draw": probs["draw"], "away_win": probs["away_win"],
            "over_2.5": probs["over_2.5"], "under_2.5": probs["under_2.5"],
        }

        value_bets = find_value_bets(model_probs, best_odds, min_edge)

        for vb in value_bets:
            calibrated = apply_calibration(vb["model_prob"])
            frac, amount = stake_amount(bankroll, calibrated, vb["best_odds"])
            if amount <= 0:
                continue

            row = {
                "fixture_id": fixture_id, "league": league_name,
                "home_team": home["name"], "away_team": away["name"], "kickoff": kickoff,
                "market": vb["market"], "model_prob": vb["model_prob"],
                "calibrated_prob": calibrated, "market_prob": vb["market_prob"],
                "best_odds": vb["best_odds"], "bookmaker": vb["bookmaker"],
                "edge": vb["edge"], "kelly_stake_fraction": frac, "kelly_stake_amount": amount,
            }
            insert_prediction(row)
            all_value_bets.append(row)

        time.sleep(0.3)  # be polite to the free API tier

    print(f"\n{'='*70}")
    if not all_value_bets:
        print("No value bets found this run. That's a normal, healthy result --")
        print("real edges are rare. Don't force a bet that isn't there.")
    else:
        print(f"{len(all_value_bets)} value bet(s) found (edge >= {min_edge*100:.0f}%):\n")
        for b in all_value_bets:
            print(f"  {b['home_team']} vs {b['away_team']}  [{b['league']}]")
            print(f"    Market: {b['market']}  |  Model: {b['calibrated_prob']*100:.1f}%  "
                  f"Market: {b['market_prob']*100:.1f}%  Edge: +{b['edge']*100:.1f}%")
            print(f"    Best odds: {b['best_odds']} ({b['bookmaker']})  |  "
                  f"Suggested stake: {b['kelly_stake_amount']} "
                  f"({'PAPER' if paper_mode else 'REAL'})")
            print()
    print(f"{'='*70}")
    print("Logged to data/footy_edge.db. Run grade.py after matches finish, "
          "then metrics.py to see honest performance.")
    logger.info(f"Scan complete. {len(all_value_bets)} value bet(s) found and logged.")

    return all_value_bets


if __name__ == "__main__":
    run()
