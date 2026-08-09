"""
Value detection: this is the piece that was missing from the "pick whichever
market has the highest confidence" approach. A prediction is only a good BET
if your probability estimate beats what the market is already pricing in.

We de-vig (remove the bookmaker's built-in margin) from the odds first, so
we're comparing our model against the market's *fair* probability, not the
inflated one that guarantees the bookmaker profit.
"""

MARKET_PAIRS = {
    "1x2": ["home_win", "draw", "away_win"],
    "ou25": ["over_2.5", "under_2.5"],
}


def implied_prob(decimal_odds: float) -> float:
    return 1.0 / decimal_odds if decimal_odds else 0.0


def devig_group(odds_dict: dict, keys: list[str]) -> dict:
    """Proportional de-vig across a market group (e.g. home/draw/away)."""
    implied = {k: implied_prob(odds_dict[k][0]) for k in keys if odds_dict.get(k) and odds_dict[k][0]}
    overround = sum(implied.values())
    if overround == 0:
        return {k: 0.0 for k in keys}
    return {k: v / overround for k, v in implied.items()}


def find_value_bets(model_probs: dict, best_odds: dict, min_edge: float) -> list[dict]:
    """Compares model probabilities to de-vigged market probabilities for every
    market and returns any bet where the model's edge exceeds min_edge."""
    value_bets = []

    for group_name, keys in MARKET_PAIRS.items():
        fair_probs = devig_group(best_odds, keys)
        for k in keys:
            if k not in fair_probs or not best_odds.get(k) or not best_odds[k][0]:
                continue
            model_p = model_probs.get(k)
            if model_p is None:
                continue
            market_p = fair_probs[k]
            edge = model_p - market_p
            if edge >= min_edge:
                odds, bookmaker = best_odds[k]
                value_bets.append({
                    "market": k.upper(),
                    "model_prob": model_p,
                    "market_prob": market_p,
                    "edge": edge,
                    "best_odds": odds,
                    "bookmaker": bookmaker,
                })

    return value_bets
