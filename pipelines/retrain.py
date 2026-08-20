from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from recommendation_platform.monitoring.monitor import (
    check_performance,
    detect_drift,
    write_monitoring_report,
)
from recommendation_platform.training.train import train


def run_retraining(data_dir: Path, output_dir: Path, threshold: float = 0.20) -> dict[str, object]:
    report_path = output_dir / "evaluation_report.json"
    previous = (
        json.loads(report_path.read_text(encoding="utf-8"))
        if report_path.exists()
        else {"metrics": {}}
    )
    events = pd.read_parquet(data_dir / "interactions.parquet")
    reference = events.iloc[: max(len(events) // 2, 1)].select_dtypes("number")
    current = events.iloc[max(len(events) // 2, 1) :].select_dtypes("number")
    drift = detect_drift(reference, current, threshold)
    performance = check_performance(previous.get("metrics", {}))
    write_monitoring_report(output_dir / "monitoring_report.json", drift, performance)
    triggered = bool(drift["drifted"] or performance["degraded"] or not report_path.exists())
    result: dict[str, object] = {"triggered": triggered, "drift": drift, "performance": performance}
    if triggered:
        result["training"] = train(data_dir, output_dir, model_version="ranker-retrained")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    args = parser.parse_args()
    print(json.dumps(run_retraining(args.data_dir, args.output_dir), indent=2))


if __name__ == "__main__":
    main()
