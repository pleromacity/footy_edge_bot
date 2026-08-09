"""
Tests for value_engine.py -- this is the piece that determines whether a
"prediction" is actually a bet worth making. If de-vigging is wrong, every
edge calculation downstream is wrong.
"""

from value_engine import implied_prob, devig_group, find_value_bets


def test_implied_prob_basic():
    assert abs(implied_prob(2.0) - 0.5) < 1e-9
    assert abs(implied_prob(4.0) - 0.25) < 1e-9


def test_implied_prob_zero_odds_returns_zero():
    assert implied_prob(0) == 0.0


def test_devig_group_removes_overround():
    """Raw bookmaker odds always imply >100% total probability (their
    margin). After de-vigging, the three outcomes should sum to exactly 1."""
    odds = {"home_win": (2.0, "Book"), "draw": (3.4, "Book"), "away_win": (4.5, "Book")}
    fair = devig_group(odds, ["home_win", "draw", "away_win"])
    assert abs(sum(fair.values()) - 1.0) < 1e-9


def test_devig_group_preserves_relative_ordering():
    """De-vigging shouldn't flip which outcome the market thinks is most
    likely -- it should only rescale, not reorder."""
    odds = {"home_win": (1.5, "Book"), "draw": (4.0, "Book"), "away_win": (6.0, "Book")}
    fair = devig_group(odds, ["home_win", "draw", "away_win"])
    assert fair["home_win"] > fair["draw"] > fair["away_win"]


def test_find_value_bets_flags_genuine_edge():
    """A model that thinks Home Win is far more likely than the de-vigged
    market does should be flagged as a value bet."""
    model_probs = {"home_win": 0.62, "draw": 0.23, "away_win": 0.15,
                   "over_2.5": 0.50, "under_2.5": 0.50}
    best_odds = {"home_win": (2.0, "Book"), "draw": (3.4, "Book"), "away_win": (6.0, "Book"),
                 "over_2.5": (2.0, "Book"), "under_2.5": (2.0, "Book")}
    bets = find_value_bets(model_probs, best_odds, min_edge=0.04)
    markets = [b["market"] for b in bets]
    assert "HOME_WIN" in markets


def test_find_value_bets_respects_threshold():
    """A tiny edge below min_edge should NOT be flagged -- this is what
    stops the bot from finding 'value' in every single match."""
    model_probs = {"home_win": 0.51, "draw": 0.29, "away_win": 0.20,
                   "over_2.5": 0.50, "under_2.5": 0.50}
    best_odds = {"home_win": (2.0, "Book"), "draw": (3.4, "Book"), "away_win": (4.5, "Book"),
                 "over_2.5": (2.0, "Book"), "under_2.5": (2.0, "Book")}
    bets = find_value_bets(model_probs, best_odds, min_edge=0.20)
    assert bets == []


def test_find_value_bets_no_edge_when_model_matches_market():
    """If the model's probability roughly equals the de-vigged market
    probability, there's no edge -- nothing should be flagged."""
    odds = {"home_win": (2.0, "Book"), "draw": (3.4, "Book"), "away_win": (4.5, "Book"),
            "over_2.5": (2.0, "Book"), "under_2.5": (2.0, "Book")}
    fair = devig_group(odds, ["home_win", "draw", "away_win"])
    model_probs = dict(fair)
    model_probs["over_2.5"] = 0.50
    model_probs["under_2.5"] = 0.50
    bets = find_value_bets(model_probs, odds, min_edge=0.04)
    assert bets == []
