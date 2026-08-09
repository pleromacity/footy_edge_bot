"""
Poisson-based match outcome model.

This is a standard, well-established approach in football analytics
(not exotic or proprietary) -- it estimates each team's expected goals
based on attack/defense strength relative to league average, then uses
the Poisson distribution to derive probabilities for match outcomes,
over/under goals, and BTTS.

It is deliberately simple and transparent. Simple models that you can
audit and backtest beat complex ones you have to trust blindly.
"""

from scipy.stats import poisson


def _safe_div(a, b, default=1.0):
    return a / b if b else default


def extract_team_strength(stats: dict) -> dict:
    """Pulls attack/defense rates out of an API-Football team-statistics response."""
    fixtures_played = stats.get("fixtures", {}).get("played", {}).get("total", 1) or 1
    goals_for_total = stats.get("goals", {}).get("for", {}).get("total", {}).get("total", 0)
    goals_against_total = stats.get("goals", {}).get("against", {}).get("total", {}).get("total", 0)

    goals_for_home = stats.get("goals", {}).get("for", {}).get("total", {}).get("home", 0)
    goals_for_away = stats.get("goals", {}).get("for", {}).get("total", {}).get("away", 0)
    goals_against_home = stats.get("goals", {}).get("against", {}).get("total", {}).get("home", 0)
    goals_against_away = stats.get("goals", {}).get("against", {}).get("total", {}).get("away", 0)

    played_home = stats.get("fixtures", {}).get("played", {}).get("home", 1) or 1
    played_away = stats.get("fixtures", {}).get("played", {}).get("away", 1) or 1

    return {
        "avg_scored": _safe_div(goals_for_total, fixtures_played),
        "avg_conceded": _safe_div(goals_against_total, fixtures_played),
        "avg_scored_home": _safe_div(goals_for_home, played_home),
        "avg_conceded_home": _safe_div(goals_against_home, played_home),
        "avg_scored_away": _safe_div(goals_for_away, played_away),
        "avg_conceded_away": _safe_div(goals_against_away, played_away),
    }


def expected_goals(home_strength: dict, away_strength: dict,
                    league_avg_home_goals: float = 1.5,
                    league_avg_away_goals: float = 1.2) -> tuple[float, float]:
    """Computes expected goals for each side using attack/defense strength ratios."""
    home_attack = _safe_div(home_strength["avg_scored_home"], league_avg_home_goals)
    home_defense = _safe_div(home_strength["avg_conceded_home"], league_avg_away_goals)
    away_attack = _safe_div(away_strength["avg_scored_away"], league_avg_away_goals)
    away_defense = _safe_div(away_strength["avg_conceded_away"], league_avg_home_goals)

    home_xg = home_attack * away_defense * league_avg_home_goals
    away_xg = away_attack * home_defense * league_avg_away_goals

    # Clamp to sane bounds -- guards against division artifacts from small samples
    home_xg = max(0.2, min(home_xg, 4.5))
    away_xg = max(0.2, min(away_xg, 4.5))
    return home_xg, away_xg


def outcome_probabilities(home_xg: float, away_xg: float, max_goals: int = 8) -> dict:
    """Builds the full scoreline probability matrix from independent Poisson
    distributions, then aggregates into market probabilities."""
    home_probs = [poisson.pmf(i, home_xg) for i in range(max_goals + 1)]
    away_probs = [poisson.pmf(i, away_xg) for i in range(max_goals + 1)]

    p_home_win = p_draw = p_away_win = 0.0
    p_over_25 = p_btts_yes = 0.0

    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            p = home_probs[h] * away_probs[a]
            if h > a:
                p_home_win += p
            elif h == a:
                p_draw += p
            else:
                p_away_win += p
            if h + a > 2.5:
                p_over_25 += p
            if h > 0 and a > 0:
                p_btts_yes += p

    return {
        "home_win": p_home_win,
        "draw": p_draw,
        "away_win": p_away_win,
        "over_2.5": p_over_25,
        "under_2.5": 1 - p_over_25,
        "btts_yes": p_btts_yes,
        "btts_no": 1 - p_btts_yes,
        "home_xg": home_xg,
        "away_xg": away_xg,
    }
