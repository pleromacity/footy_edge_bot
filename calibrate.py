"""
This is the "continually adapting" part of the bot.

The raw Poisson model's probabilities are a starting estimate, not gospel --
in practice these kinds of models tend to be systematically overconfident or
underconfident in predictable ways. Once you've accumulated enough GRADED
predictions (actual match results logged), this fits a simple logistic
recalibration: it learns the real-world relationship between "what the model
said" and "what actually happened," and corrects future predictions
accordingly.

Run this periodically (e.g. weekly) once you have at least ~50-100 graded
predictions. Before that, there isn't enough data for calibration to mean
anything, and it will just add noise -- the script will tell you if you're
not there yet.
"""

import json
import numpy as np
from sklearn.linear_model import LogisticRegression

from storage import get_graded_predictions

CALIBRATION_PATH = "data/calibration.json"
MIN_SAMPLES_FOR_CALIBRATION = 50


def fit_calibration():
    graded = get_graded_predictions()
    if len(graded) < MIN_SAMPLES_FOR_CALIBRATION:
        print(f"Only {len(graded)} graded predictions so far -- need at least "
              f"{MIN_SAMPLES_FOR_CALIBRATION} before calibration is meaningful. Skipping.")
        return None

    X = np.array([[p["model_prob"]] for p in graded])
    y = np.array([1 if p["result"] == "WON" else 0 for p in graded])

    if len(set(y.tolist())) < 2:
        print("All graded predictions have the same outcome so far -- can't calibrate yet.")
        return None

    clf = LogisticRegression()
    clf.fit(X, y)

    calibration = {
        "coef": clf.coef_[0][0],
        "intercept": clf.intercept_[0],
        "trained_on_n": len(graded),
    }
    with open(CALIBRATION_PATH, "w") as f:
        json.dump(calibration, f, indent=2)

    print(f"Calibration updated using {len(graded)} graded predictions.")
    return calibration


def apply_calibration(raw_prob: float) -> float:
    try:
        with open(CALIBRATION_PATH) as f:
            cal = json.load(f)
    except FileNotFoundError:
        return raw_prob  # no calibration fitted yet -- use raw model output

    z = cal["coef"] * raw_prob + cal["intercept"]
    calibrated = 1 / (1 + np.exp(-z))
    return float(calibrated)
