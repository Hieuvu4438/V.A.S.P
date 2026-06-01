"""Phase 2 MVP — Platt scaling confidence calibration.

Applies sigmoid(A * raw + B) to map raw confidence scores to calibrated
probabilities.  A and B are fitted from the gold dataset via logistic
regression.

Default values (pre-training): A=2.5, B=-1.0 — these should be updated
after training on the annotated gold dataset.
"""

import math

# Platt scaling parameters (fit via logistic regression on gold dataset)
_PLATT_A = 2.5   # slope
_PLATT_B = -1.0  # intercept


def calibrate_confidence(raw_score: float) -> float:
    """Platt scaling: sigmoid(A * raw + B).

    Maps raw_score in [0, 1] to a calibrated probability in [0, 1].
    """
    bounded = max(0.0, min(1.0, raw_score))
    z = _PLATT_A * bounded + _PLATT_B
    return 1.0 / (1.0 + math.exp(-z))
