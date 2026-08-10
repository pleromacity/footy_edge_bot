"""
Run this after matches/games have finished (e.g. once a day) to fetch real
results and grade every pending prediction WON/LOST. This is what makes
the whole system honest -- without grading, "confidence %" numbers are
just unverified claims.

Every grading run also updates the (paper-mode) bankroll based on the
stakes that would have won or lost, and logs it -- this is what feeds the
bankroll chart on the dashboard.

Usage:
    python grade.py
"""

import config
from data_fetcher import get_finished_fixture_result
import nba_fetcher
from storage import get_ungraded_predictions, set_result, latest_bankroll, log_bankroll
from logging_setup import setup_logging

logger = setup_logging()


def grade_football_market(market: str, home_goals: int, away_goals: int) -> str:
    if market == "HOME_WIN":
        return "WON" if home_goals > away_goals else "LOST"
    if market == "AWAY_WIN":
        return "WON" if away_goals > home_goals else "LOST"
    if market == "DRAW":
        return "WON" if home_goals == away_goals else "LOST"
    if market == "OVER_2.5":
        return "WON" if (home_goals + away_goals) > 2.5 else "LOST"
    if market == "UNDER_2.5":
        return "WON" if (home_goals + away_goals) < 2.5 else "LOST"
    return "LOST"  # unknown market, fail safe


def grade_nba_market(market: str, home_points: int, away_points: int) -> str:
    if market == "HOME_WIN":
        return "WON" if home_points > away_points else "LOST"
    if market == "AWAY_WIN":
        return "WON" if away_points > home_points else "LOST"
    return "LOST"  # unknown market, fail safe


def _grade_one(pred: dict):
    """Returns (outcome, stake, best_odds) or None if the match/game hasn't
    finished yet or its result couldn't be fetched."""
    sport = pred.get("sport", "football")

    if sport == "football":
        result = get_finished_fixture_result(pred["fixture_id"])
        if result is None:
            return None
        outcome = grade_football_market(pred["market"], result["home_goals"], result["away_goals"])
    elif sport == "nba":
        result = nba_fetcher.get_finished_game_result(pred["fixture_id"])
        if result is None:
            return None
        outcome = grade_nba_market(pred["market"], result["home_points"], result["away_points"])
    else:
        logger.warning(f"Prediction #{pred['id']} has unknown sport '{sport}', skipping.")
        return None

    return outcome


def run():
    pending = get_ungraded_predictions()
    if not pending:
        print("No ungraded predictions found.")
        return {"graded": 0, "total_pending": 0}

    graded_count = 0
    bankroll_delta = 0.0

    for pred in pending:
        try:
            outcome = _grade_one(pred)
        except Exception:
            logger.exception(f"Failed to fetch result for prediction #{pred['id']} ({pred.get('sport')})")
            continue
        if outcome is None:
            continue  # match/game hasn't finished yet, or sport unrecognized

        set_result(pred["id"], outcome)

        stake = pred["kelly_stake_amount"] or 0.0
        if outcome == "WON":
            bankroll_delta += stake * (pred["best_odds"] - 1)
        elif outcome == "LOST":
            bankroll_delta -= stake

        graded_count += 1
        print(f"  Graded #{pred['id']} [{pred.get('sport','football').upper()}] "
              f"{pred['home_team']} vs {pred['away_team']} [{pred['market']}] -> {outcome}")

    if graded_count:
        new_bankroll = latest_bankroll(config.STARTING_BANKROLL) + bankroll_delta
        log_bankroll(new_bankroll, note=f"graded {graded_count} picks (delta {bankroll_delta:+.2f})")
        logger.info(f"Graded {graded_count} predictions, bankroll delta {bankroll_delta:+.2f}, "
                    f"new bankroll {new_bankroll:.2f}")

    print(f"\nGraded {graded_count} of {len(pending)} pending predictions "
          f"({len(pending) - graded_count} matches/games not finished yet).")

    return {"graded": graded_count, "total_pending": len(pending)}


if __name__ == "__main__":
    run()
