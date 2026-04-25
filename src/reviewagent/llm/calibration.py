def calibrate_confidence(raw_score: float) -> float:
    bounded = max(0.0, min(1.0, raw_score))
    return bounded
