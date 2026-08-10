"""
This is the "continually adapting" part of the bot.

The raw model probabilities are a starting estimate, not gospel -- in
practice these kinds of models tend to be systematically overconfident or
underconfident in predictable ways. Once you've accumulated enough GRADED
predictions (actual match/game results logged), this fits a simple logistic
recalibration: it learns the real-world relationship between "what the
model said" and "what actually happened," and corrects future predictions
accordingly.

Calibration is fitted separately per sport (football vs NBA use different
models with different probability distributions -- lumping them into one
curve would blur two different relationships together into a wrong one for
both).

Run this periodically (e.g. weekly) once you have at least ~50-100 graded
predictions FOR THAT SPORT. Before that, there isn't enough data for
calibration to mean anything, and it will just add noise -- the script will
tell you if you're not there yet.
"""

import json
import numpy as np
from sklearn.linear_model import LogisticRegression

from storage import get_graded_predictions

CALIBRATION_PATH_TEMPLATE = "data/calibration_{sport}.json"
MIN_SAMPLES_FOR_CALIBRATION = 50


def _path_for(sport: str) -> str:
    return CALIBRATION_PATH_TEMPLATE.format(sport=sport)


def fit_calibration(sport: str = "football"):
    graded = [p for p in get_graded_predictions() if p.get("sport", "football") == sport]
    if len(graded) < MIN_SAMPLES_FOR_CALIBRATION:
        print(f"Only {len(graded)} graded {sport} predictions so far -- need at least "
              f"{MIN_SAMPLES_FOR_CALIBRATION} before calibration is meaningful. Skipping.")
        return None

    X = np.array([[p["model_prob"]] for p in graded])
    y = np.array([1 if p["result"] == "WON" else 0 for p in graded])

    if len(set(y.tolist())) < 2:
        print(f"All graded {sport} predictions have the same outcome so far -- can't calibrate yet.")
        return None

    clf = LogisticRegression()
    clf.fit(X, y)

    calibration = {
        "coef": clf.coef_[0][0],
        "intercept": clf.intercept_[0],
        "trained_on_n": len(graded),
    }
    with open(_path_for(sport), "w") as f:
        json.dump(calibration, f, indent=2)

    print(f"Calibration updated for {sport} using {len(graded)} graded predictions.")
    return calibration


def apply_calibration(raw_prob: float, sport: str = "football") -> float:
    try:
        with open(_path_for(sport)) as f:
            cal = json.load(f)
    except FileNotFoundError:
        return raw_prob  # no calibration fitted yet for this sport -- use raw model output

    z = cal["coef"] * raw_prob + cal["intercept"]
    calibrated = 1 / (1 + np.exp(-z))
    return float(calibrated)
