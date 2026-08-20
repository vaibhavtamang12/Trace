from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

import pandas as pd

from recommendation_platform.models.recommender import RecommendationModel


def main() -> None:
    model_path = Path("data/processed/model.joblib")
    if not model_path.exists():
        raise SystemExit("Run make train before make benchmark")
    model = RecommendationModel.load(model_path)
    frame = (
        pd.read_parquet("data/processed/benchmark_features.parquet")
        if Path("data/processed/benchmark_features.parquet").exists()
        else pd.DataFrame([{column: 0.0 for column in model.feature_columns}])
    )
    durations = []
    for _ in range(100):
        start = time.perf_counter()
        model.predict_scores(frame)
        durations.append((time.perf_counter() - start) * 1000)
    result = {
        "samples": len(durations),
        "p50_ms": statistics.median(durations),
        "p95_ms": sorted(durations)[94],
        "p99_ms": sorted(durations)[98],
        "throughput_per_second": 1000 / statistics.mean(durations),
    }
    Path("data/processed/benchmark.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
