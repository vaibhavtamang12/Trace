from __future__ import annotations

import argparse
import json
from pathlib import Path

from recommendation_platform.training.train import train


def evaluate(
    data_dir: Path, model_path: Path, promotion_min_gain: float = 0.01
) -> dict[str, object]:
    report_path = model_path.with_name("evaluation_report.json")
    if not report_path.exists():
        report = train(data_dir, model_path.parent)
    else:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    metrics = report["metrics"]
    gain = float(metrics.get("test_ndcg", 0)) - float(metrics.get("baseline_ndcg", 0))
    approved = gain >= promotion_min_gain and float(metrics.get("test_ndcg", 0)) > 0
    decision = {
        "approved": approved,
        "ndcg_gain": round(gain, 6),
        "threshold": promotion_min_gain,
        "model_version": report["model_version"],
    }
    report["promotion_decision"] = decision
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--model-path", type=Path, default=Path("data/processed/model.joblib"))
    args = parser.parse_args()
    print(json.dumps(evaluate(args.data_dir, args.model_path), indent=2))


if __name__ == "__main__":
    main()
