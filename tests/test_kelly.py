"""
Tests for kelly.py -- the staking math. If this is wrong, it either
recommends betting too much (risk of ruin) or too little (leaving edge on
the table). Both are real financial consequences, so this gets tested
directly against the known Kelly formula.
"""

import settings
from kelly import kelly_stake_fraction


def setup_module(module):
    # Pin kelly_fraction to a known value so these tests aren't affected
    # by whatever is currently saved in data/settings.json
    settings.save_settings({"kelly_fraction": 0.25})


def test_kelly_is_zero_when_no_edge():
    """At true odds (model probability == market implied probability),
    Kelly should recommend staking nothing -- there's no edge to exploit."""
    frac = kelly_stake_fraction(0.5, 2.0)  # 2.0 decimal odds implies 50%
    assert frac == 0.0


def test_kelly_is_positive_with_real_edge():
    frac = kelly_stake_fraction(0.6, 2.0)  # model says 60%, market implies 50%
    assert frac > 0.0


def test_kelly_never_negative():
    """Kelly should never suggest a negative stake, even with a bad
    (negative-edge) probability/odds combination."""
    frac = kelly_stake_fraction(0.1, 1.5)
    assert frac >= 0.0


def test_kelly_fraction_scales_down_full_kelly():
    """With KELLY_FRACTION=0.25 (quarter Kelly), the suggested stake should
    be exactly 25% of what full Kelly would suggest."""
    model_prob, odds = 0.6, 2.0
    b = odds - 1
    q = 1 - model_prob
    full_kelly = max(0.0, (b * model_prob - q) / b)
    quarter_kelly = kelly_stake_fraction(model_prob, odds)
    assert abs(quarter_kelly - full_kelly * 0.25) < 1e-9


def test_kelly_handles_odds_of_one_without_crashing():
    """Decimal odds of 1.0 (b=0) should return 0, not divide by zero."""
    frac = kelly_stake_fraction(0.9, 1.0)
    assert frac == 0.0
