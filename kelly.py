"""
Fractional Kelly Criterion staking.

Full Kelly maximizes long-run growth rate but is extremely high-variance --
a single misjudged edge can produce a large drawdown. Fractional Kelly
(betting e.g. 25% of what full Kelly suggests) sacrifices some growth for
a much smoother ride, which is what almost every professional bettor
actually uses in practice.
"""

import settings as settings_module


def kelly_stake_fraction(model_prob: float, decimal_odds: float) -> float:
    """Returns the fraction of bankroll to stake. b = net odds (decimal - 1)."""
    kelly_fraction = settings_module.get("kelly_fraction")
    b = decimal_odds - 1
    if b <= 0:
        return 0.0
    q = 1 - model_prob
    f_star = (b * model_prob - q) / b
    f_star = max(0.0, f_star)  # never bet on a negative-edge outcome
    return f_star * kelly_fraction


def stake_amount(bankroll: float, model_prob: float, decimal_odds: float) -> tuple[float, float]:
    frac = kelly_stake_fraction(model_prob, decimal_odds)
    return frac, round(frac * bankroll, 2)
