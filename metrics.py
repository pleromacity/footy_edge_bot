"""
The honesty dashboard. Run this any time to see whether the bot actually
has an edge, using graded (real, settled) predictions only.

Usage:
    python metrics.py
"""

from storage import get_graded_predictions


def brier_score(graded: list[dict]) -> float:
    """Lower is better. 0 = perfect, 0.25 = no better than random guessing
    on a binary outcome, 1 = perfectly wrong."""
    if not graded:
        return float("nan")
    total = 0.0
    for p in graded:
        actual = 1.0 if p["result"] == "WON" else 0.0
        prob = p["calibrated_prob"] if p.get("calibrated_prob") is not None else p["model_prob"]
        total += (prob - actual) ** 2
    return total / len(graded)


def roi_flat_stake(graded: list[dict], stake: float = 100.0) -> dict:
    """ROI if every bet had used a flat stake -- the simplest, most honest
    baseline. Kelly staking numbers can look better or worse than this
    depending on variance, but flat-stake ROI tells you if the PICKS
    themselves have edge, independent of staking strategy."""
    profit = 0.0
    for p in graded:
        if p["result"] == "WON":
            profit += stake * (p["best_odds"] - 1)
        elif p["result"] == "LOST":
            profit -= stake
    total_staked = stake * len(graded)
    roi_pct = (profit / total_staked * 100) if total_staked else 0.0
    return {"bets": len(graded), "profit": round(profit, 2), "roi_pct": round(roi_pct, 2)}


def roi_kelly_stake(graded: list[dict]) -> dict:
    profit = 0.0
    total_staked = 0.0
    for p in graded:
        stake = p["kelly_stake_amount"] or 0
        total_staked += stake
        if p["result"] == "WON":
            profit += stake * (p["best_odds"] - 1)
        elif p["result"] == "LOST":
            profit -= stake
    roi_pct = (profit / total_staked * 100) if total_staked else 0.0
    return {"bets": len(graded), "profit": round(profit, 2), "roi_pct": round(roi_pct, 2)}


def win_rate_by_market(graded: list[dict]) -> dict:
    by_market = {}
    for p in graded:
        m = p["market"]
        by_market.setdefault(m, {"wins": 0, "total": 0})
        by_market[m]["total"] += 1
        if p["result"] == "WON":
            by_market[m]["wins"] += 1
    return {
        m: {"win_rate": round(v["wins"] / v["total"] * 100, 1), "n": v["total"]}
        for m, v in by_market.items()
    }


def run():
    graded = get_graded_predictions()
    print(f"\n{'='*50}\nFOOTY EDGE BOT -- HONESTY DASHBOARD\n{'='*50}")
    print(f"Graded predictions: {len(graded)}")

    if len(graded) < 20:
        print("\nNot enough graded predictions yet for meaningful stats "
              "(want 50-100+ before drawing conclusions). Keep logging and grading.")
        return

    print(f"Brier score: {brier_score(graded):.4f}  (0.25 = no edge, lower = better)")

    flat = roi_flat_stake(graded)
    print(f"\nFlat-stake ROI:  {flat['roi_pct']}%  over {flat['bets']} bets  "
          f"(profit: {flat['profit']})")

    kelly = roi_kelly_stake(graded)
    print(f"Kelly-stake ROI: {kelly['roi_pct']}%  over {kelly['bets']} bets  "
          f"(profit: {kelly['profit']})")

    print("\nWin rate by market:")
    for market, stats in win_rate_by_market(graded).items():
        print(f"  {market:12s} {stats['win_rate']}%  (n={stats['n']})")

    print(f"\n{'='*50}")
    if flat["roi_pct"] <= 0:
        print("Flat-stake ROI is not positive. This model has not shown an edge "
              "yet on the graded sample. Do not increase real-money stakes based "
              "on hope -- keep collecting data.")
    else:
        print("Flat-stake ROI is positive on this sample. Still treat this "
              "cautiously until you have 100+ graded bets -- short samples "
              "vary hugely by luck alone.")


if __name__ == "__main__":
    run()
