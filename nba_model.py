"""
NBA moneyline model.

Basketball scores are much higher and more continuous than football goals,
so Poisson (built for rare, discrete events) isn't the right tool here.
Instead this uses the standard alternative from sports analytics: estimate
each team's expected points scored and allowed, combine into a projected
point margin for the matchup, and convert that margin into a win
probability using a normal distribution -- the standard, well-documented
approach (the same idea behind things like Pythagorean win expectancy and
most public NBA power ratings), not anything exotic or proprietary.

Scope note: this covers the moneyline (win/loss) market only for now.
Spreads and totals need a per-game line from the odds feed to grade against,
which adds real complexity -- worth adding later once moneyline is proven
out, not before.
"""

import statistics

LEAGUE_AVG_MARGIN_STDDEV = 12.0  # typical NBA game-to-game margin spread, points
HOME_COURT_ADVANTAGE = 2.5  # points, well-established long-run NBA average


def _safe_div(a, b, default=110.0):
    return a / b if b else default


def extract_team_strength(recent_games: list[dict], team_id: int) -> dict:
    """Pulls scoring/conceding averages out of a team's recent finished
    games (see nba_fetcher.get_team_recent_games)."""
    scored, conceded = [], []
    scored_home, conceded_home = [], []
    scored_away, conceded_away = [], []

    for g in recent_games:
        home_team_id = g.get("teams", {}).get("home", {}).get("id")
        away_team_id = g.get("teams", {}).get("visitors", {}).get("id")
        home_pts = g.get("scores", {}).get("home", {}).get("points")
        away_pts = g.get("scores", {}).get("visitors", {}).get("points")
        if home_pts is None or away_pts is None:
            continue

        if home_team_id == team_id:
            scored.append(home_pts)
            conceded.append(away_pts)
            scored_home.append(home_pts)
            conceded_home.append(away_pts)
        elif away_team_id == team_id:
            scored.append(away_pts)
            conceded.append(home_pts)
            scored_away.append(away_pts)
            conceded_away.append(home_pts)

    return {
        "avg_scored": _safe_div(sum(scored), len(scored)),
        "avg_conceded": _safe_div(sum(conceded), len(conceded)),
        "avg_scored_home": _safe_div(sum(scored_home), len(scored_home)),
        "avg_conceded_home": _safe_div(sum(conceded_home), len(conceded_home)),
        "avg_scored_away": _safe_div(sum(scored_away), len(scored_away)),
        "avg_conceded_away": _safe_div(sum(conceded_away), len(conceded_away)),
        "sample_size": len(scored),
    }


def expected_margin(home_strength: dict, away_strength: dict) -> float:
    """Projects the home team's expected margin of victory (negative =
    expected to lose) by averaging each side's offense-vs-opponent-defense
    read, plus home court advantage."""
    home_projected = (home_strength["avg_scored_home"] + away_strength["avg_conceded_away"]) / 2
    away_projected = (away_strength["avg_scored_away"] + home_strength["avg_conceded_home"]) / 2
    return (home_projected - away_projected) + HOME_COURT_ADVANTAGE


def outcome_probabilities(margin: float, stddev: float = LEAGUE_AVG_MARGIN_STDDEV) -> dict:
    """Converts a projected point margin into a home/away win probability
    via a normal distribution -- ties aren't possible in the NBA (games go
    to overtime), so this is a clean two-way market."""
    dist = statistics.NormalDist(mu=margin, sigma=stddev)
    p_home_win = 1 - dist.cdf(0)  # P(margin > 0)
    return {
        "home_win": p_home_win,
        "away_win": 1 - p_home_win,
        "projected_margin": margin,
    }
