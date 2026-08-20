from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from prometheus_client import Gauge

FEATURE_DRIFT = Gauge("recommendation_feature_drift", "Feature drift score", ["feature"])
MODEL_NDCG = Gauge("recommendation_model_ndcg", "Latest model NDCG@10")
RETRAINING_REQUIRED = Gauge("recommendation_retraining_required", "Whether retraining is required")


def population_stability_index(reference: pd.Series, current: pd.Series, bins: int = 10) -> float:
    if reference.empty or current.empty:
        return 0.0
    edges = np.unique(np.quantile(reference.astype(float), np.linspace(0, 1, bins + 1)))
    if len(edges) < 3:
        return 0.0
    reference_dist = np.histogram(reference, bins=edges)[0] / max(len(reference), 1)
    current_dist = np.histogram(current, bins=edges)[0] / max(len(current), 1)
    reference_dist = np.clip(reference_dist, 1e-6, None)
    current_dist = np.clip(current_dist, 1e-6, None)
    return float(np.sum((current_dist - reference_dist) * np.log(current_dist / reference_dist)))


def detect_drift(
    reference: pd.DataFrame, current: pd.DataFrame, threshold: float = 0.20
) -> dict[str, float | bool]:
    numeric = [
        column
        for column in reference.columns
        if column in current.columns and pd.api.types.is_numeric_dtype(reference[column])
    ]
    scores = {
        column: population_stability_index(reference[column].dropna(), current[column].dropna())
        for column in numeric
    }
    for feature, score in scores.items():
        FEATURE_DRIFT.labels(feature).set(score)
    max_score = max(scores.values(), default=0.0)
    drifted = max_score >= threshold
    RETRAINING_REQUIRED.set(float(drifted))
    return {
        "drifted": drifted,
        "max_psi": round(max_score, 6),
        **{f"psi_{key}": round(value, 6) for key, value in scores.items()},
    }


def check_performance(metrics: dict[str, float], min_ndcg: float = 0.05) -> dict[str, object]:
    ndcg = float(metrics.get("ndcg", metrics.get("test_ndcg", 0.0)))
    MODEL_NDCG.set(ndcg)
    degraded = ndcg < min_ndcg
    RETRAINING_REQUIRED.set(float(degraded))
    return {"degraded": degraded, "ndcg": ndcg, "minimum_ndcg": min_ndcg}


def write_monitoring_report(
    output: Path, drift: dict[str, object], performance: dict[str, object]
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(UTC).isoformat(),
                "drift": drift,
                "performance": performance,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
