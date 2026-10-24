"""Metric helpers for evaluation."""

from __future__ import annotations


def accuracy(correct: int, total: int) -> float:
    return round(correct / total, 4) if total else 0.0


def brier_score(pairs: list[tuple[float, bool]]) -> float:
    """Mean squared error between predicted confidence and correctness.

    Lower is better-calibrated. `pairs` is [(confidence, was_correct)].
    """
    if not pairs:
        return 0.0
    return round(sum((c - (1.0 if ok else 0.0)) ** 2 for c, ok in pairs) / len(pairs), 4)


def reliability_bins(
    pairs: list[tuple[float, bool]], bins: int = 5
) -> list[dict]:
    """Group predictions into confidence bins and report mean confidence vs.
    observed accuracy — the basis of a calibration (reliability) curve."""
    buckets: list[list[tuple[float, bool]]] = [[] for _ in range(bins)]
    for conf, ok in pairs:
        idx = min(bins - 1, int(conf * bins))
        buckets[idx].append((conf, ok))
    out = []
    for i, b in enumerate(buckets):
        lo, hi = i / bins, (i + 1) / bins
        if not b:
            out.append({"range": f"{lo:.1f}-{hi:.1f}", "n": 0,
                        "mean_confidence": None, "accuracy": None})
            continue
        mean_conf = round(sum(c for c, _ in b) / len(b), 3)
        acc = round(sum(1 for _, ok in b if ok) / len(b), 3)
        out.append({"range": f"{lo:.1f}-{hi:.1f}", "n": len(b),
                    "mean_confidence": mean_conf, "accuracy": acc})
    return out
