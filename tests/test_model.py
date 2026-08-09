"""
Tests for model.py -- the Poisson prediction engine. These are the tests
that matter most: if this math is wrong, every downstream prediction is
wrong, silently, and nothing else in the system would catch it.
"""

from model import expected_goals, outcome_probabilities, extract_team_strength


def test_expected_goals_stays_within_sane_bounds():
    """Even with extreme/unusual input stats, expected goals should never
    blow up to something absurd (the clamp in model.py should catch it)."""
    strong = {"avg_scored_home": 5.0, "avg_conceded_home": 0.1,
              "avg_scored": 5.0, "avg_conceded": 0.1}
    weak = {"avg_scored_away": 0.1, "avg_conceded_away": 5.0,
            "avg_scored": 0.1, "avg_conceded": 5.0}
    home_xg, away_xg = expected_goals(strong, weak)
    assert 0.2 <= home_xg <= 4.5
    assert 0.2 <= away_xg <= 4.5


def test_expected_goals_handles_zero_stats_without_crashing():
    """A team with zero games played (fresh season) shouldn't divide by
    zero or crash -- extract_team_strength has _safe_div guards for this."""
    empty_stats = {"fixtures": {"played": {"total": 0, "home": 0, "away": 0}},
                   "goals": {"for": {"total": {"total": 0, "home": 0, "away": 0}},
                             "against": {"total": {"total": 0, "home": 0, "away": 0}}}}
    strength = extract_team_strength(empty_stats)
    home_xg, away_xg = expected_goals(strength, strength)
    assert home_xg > 0
    assert away_xg > 0


def test_outcome_probabilities_sum_to_one():
    """Home win + draw + away win must total ~1.0 -- if this fails, the
    whole probability model is broken. (Tolerance is 1e-3, not tighter,
    because outcome_probabilities sums a Poisson grid truncated at 8 goals
    per side, leaving a negligible truncation tail beyond that.)"""
    probs = outcome_probabilities(1.5, 1.1)
    total = probs["home_win"] + probs["draw"] + probs["away_win"]
    assert abs(total - 1.0) < 1e-3


def test_over_under_probabilities_sum_to_one():
    probs = outcome_probabilities(1.8, 1.3)
    assert abs(probs["over_2.5"] + probs["under_2.5"] - 1.0) < 1e-9


def test_higher_home_xg_favors_home_win():
    """Sanity check: if the model gives the home team a much higher
    expected-goals rate, it should predict them to win more often."""
    probs = outcome_probabilities(2.8, 0.6)
    assert probs["home_win"] > probs["away_win"]
    assert probs["home_win"] > probs["draw"]


def test_equal_xg_produces_roughly_symmetric_outcome():
    """When both teams have identical expected goals, home/away win
    probabilities should be close (home win slightly higher only due to
    the discrete nature of Poisson at low scores, not by a huge margin)."""
    probs = outcome_probabilities(1.4, 1.4)
    assert abs(probs["home_win"] - probs["away_win"]) < 0.05


def test_high_scoring_matchup_raises_over_25_probability():
    low_scoring = outcome_probabilities(0.8, 0.7)
    high_scoring = outcome_probabilities(2.2, 1.9)
    assert high_scoring["over_2.5"] > low_scoring["over_2.5"]
