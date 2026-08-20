"""
Footy Edge Bot -- main entry point.

Fetches upcoming fixtures/games, computes model probabilities, compares
against de-vigged bookmaker odds, and logs every value bet found (paper
mode by default -- see config.PAPER_MODE). Runs whichever sports are
enabled in Settings (football always available; NBA once set up -- see
README).

Usage:
    python main.py
"""

import time

import config
import settings as settings_module
from data_fetcher import get_upcoming_fixtures, get_team_stats
from odds_fetcher import get_odds_for_sport, get_all_odds, find_best_odds
from model import extract_team_strength, expected_goals, outcome_probabilities
import nba_fetcher
import nba_model
from value_engine import find_value_bets
from kelly import stake_amount
from calibrate import apply_calibration
from storage import init_db, insert_prediction, latest_bankroll, log_bankroll
from logging_setup import setup_logging

logger = setup_logging()
LAST_SCAN_SUMMARY = {"status": "ok", "message": "", "count": 0}


def summarize_scan_result(value_bets: list[dict], source: str = "football", error: Exception | None = None, no_games: bool = False) -> dict:
    """Return a clear summary for UI/logging when a scan finds zero picks or fails."""
    if error is not None:
        message = f"Scan failed while fetching {source} data: {error}"
        logger.error(message)
        return {"status": "error", "message": message, "count": 0}
    if no_games:
        message = "No games available in the selected date range for the configured leagues."
        logger.info(message)
        return {"status": "no_games", "message": message, "count": 0}
    if not value_bets:
        message = "No value bets found this run. That's a normal, healthy result -- real edges are rare."
        logger.info(message)
        return {"status": "ok", "message": message, "count": 0}
    return {"status": "ok", "message": f"{len(value_bets)} value bet(s) found.", "count": len(value_bets)}


def market_key_to_prob_key(market: str) -> str:
    return market.lower()


def scan_football(bankroll: float, min_edge: float, paper_mode: bool) -> list[dict]:
    print("Fetching upcoming fixtures...")
    fixtures = get_upcoming_fixtures()
    print(f"  Found {len(fixtures)} fixtures across {len(settings_module.get('league_ids'))} leagues.")

    print("Fetching bookmaker odds...")
    odds_events = get_all_odds()
    print(f"  Found odds for {len(odds_events)} events.\n")

    value_bets = []

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

        for vb in find_value_bets(model_probs, best_odds, min_edge):
            calibrated = apply_calibration(vb["model_prob"], sport="football")
            frac, amount = stake_amount(bankroll, calibrated, vb["best_odds"])
            if amount <= 0:
                continue
            value_bets.append({
                "sport": "football", "fixture_id": fixture_id, "league": league_name,
                "home_team": home["name"], "away_team": away["name"], "kickoff": kickoff,
                "market": vb["market"], "model_prob": vb["model_prob"],
                "calibrated_prob": calibrated, "market_prob": vb["market_prob"],
                "best_odds": vb["best_odds"], "bookmaker": vb["bookmaker"],
                "edge": vb["edge"], "kelly_stake_fraction": frac, "kelly_stake_amount": amount,
            })

        time.sleep(0.3)  # be polite to the free API tier

    return value_bets


def scan_nba(bankroll: float, min_edge: float, paper_mode: bool) -> list[dict]:
    print("Fetching upcoming NBA games...")
    days_ahead = settings_module.get("days_ahead")
    games = nba_fetcher.get_upcoming_games(days_ahead=days_ahead)
    print(f"  Found {len(games)} upcoming games.")

    print("Fetching NBA bookmaker odds...")
    odds_events = get_odds_for_sport(config.NBA_ODDS_SPORT_KEY)
    print(f"  Found odds for {len(odds_events)} events.\n")

    value_bets = []

    for g in games:
        home = g.get("teams", {}).get("home", {})
        away = g.get("teams", {}).get("visitors", {})
        if not home.get("name") or not away.get("name"):
            continue
        game_id = g.get("id")
        kickoff = g.get("date", {}).get("start")

        best_odds = find_best_odds(odds_events, home["name"], away["name"])
        if not best_odds:
            continue

        try:
            home_games = nba_fetcher.get_team_recent_games(home["id"])
            away_games = nba_fetcher.get_team_recent_games(away["id"])
        except Exception as e:
            print(f"  [skip] {home['name']} vs {away['name']}: stats fetch failed ({e})")
            logger.warning(f"NBA stats fetch failed for {home['name']} vs {away['name']}: {e}")
            continue

        home_strength = nba_model.extract_team_strength(home_games, home["id"])
        away_strength = nba_model.extract_team_strength(away_games, away["id"])
        if home_strength["sample_size"] < 5 or away_strength["sample_size"] < 5:
            continue  # not enough games played yet this season to trust the averages

        margin = nba_model.expected_margin(home_strength, away_strength)
        probs = nba_model.outcome_probabilities(margin)
        model_probs = {"home_win": probs["home_win"], "away_win": probs["away_win"]}

        for vb in find_value_bets(model_probs, best_odds, min_edge):
            calibrated = apply_calibration(vb["model_prob"], sport="nba")
            frac, amount = stake_amount(bankroll, calibrated, vb["best_odds"])
            if amount <= 0:
                continue
            value_bets.append({
                "sport": "nba", "fixture_id": game_id, "league": "NBA",
                "home_team": home["name"], "away_team": away["name"], "kickoff": kickoff,
                "market": vb["market"], "model_prob": vb["model_prob"],
                "calibrated_prob": calibrated, "market_prob": vb["market_prob"],
                "best_odds": vb["best_odds"], "bookmaker": vb["bookmaker"],
                "edge": vb["edge"], "kelly_stake_fraction": frac, "kelly_stake_amount": amount,
            })

        time.sleep(0.3)

    return value_bets


SPORT_SCANNERS = {
    "football": scan_football,
    "nba": scan_nba,
}


def run():
    global LAST_SCAN_SUMMARY

    config.require_api_keys()
    init_db()
    bankroll = latest_bankroll(config.STARTING_BANKROLL)
    if bankroll == config.STARTING_BANKROLL:
        log_bankroll(bankroll, note="initial")

    paper_mode = settings_module.get("paper_mode")
    min_edge = settings_module.get("min_edge")
    enabled_sports = settings_module.get("enabled_sports") or ["football"]

    print(f"Bankroll: {bankroll}  |  Paper mode: {paper_mode}  |  Sports: {', '.join(enabled_sports)}\n")
    logger.info(f"Scan started. Bankroll={bankroll}, paper_mode={paper_mode}, min_edge={min_edge}, sports={enabled_sports}")

    all_value_bets = []
    scan_error = None
    no_games = False
    for sport in enabled_sports:
        scanner = SPORT_SCANNERS.get(sport)
        if not scanner:
            print(f"  [skip] Unknown sport '{sport}' in settings.")
            continue
        try:
            bets = scanner(bankroll, min_edge, paper_mode)
        except Exception as exc:
            scan_error = exc
            logger.exception(f"Scan failed for sport '{sport}'")
            break
        for row in bets:
            insert_prediction(row)
        all_value_bets.extend(bets)
        if not bets and sport == "football":
            no_games = True

    print(f"\n{'='*70}")
    if scan_error is not None:
        print(f"Scan failed: {scan_error}")
        LAST_SCAN_SUMMARY = summarize_scan_result([], source="football", error=scan_error)
    elif not all_value_bets:
        if no_games:
            print("No games available in the selected date range for the configured leagues.")
            LAST_SCAN_SUMMARY = summarize_scan_result([], source="football", no_games=True)
        else:
            print("No value bets found this run. That's a normal, healthy result --")
            print("real edges are rare. Don't force a bet that isn't there.")
            LAST_SCAN_SUMMARY = summarize_scan_result([])
    else:
        print(f"{len(all_value_bets)} value bet(s) found (edge >= {min_edge*100:.0f}%):\n")
        for b in all_value_bets:
            print(f"  [{b['sport'].upper()}] {b['home_team']} vs {b['away_team']}  [{b['league']}]")
            print(f"    Market: {b['market']}  |  Model: {b['calibrated_prob']*100:.1f}%  "
                  f"Market: {b['market_prob']*100:.1f}%  Edge: +{b['edge']*100:.1f}%")
            print(f"    Best odds: {b['best_odds']} ({b['bookmaker']})  |  "
                  f"Suggested stake: {b['kelly_stake_amount']} "
                  f"({'PAPER' if paper_mode else 'REAL'})")
            print()
        LAST_SCAN_SUMMARY = summarize_scan_result(all_value_bets)
    print(f"{'='*70}")
    if scan_error is None:
        print("Logged to the database. Run grade.py after matches finish, "
              "then metrics.py to see honest performance.")
        logger.info(f"Scan complete. {len(all_value_bets)} value bet(s) found and logged.")
    else:
        logger.error(f"Scan failed: {scan_error}")

    return all_value_bets


if __name__ == "__main__":
    run()
