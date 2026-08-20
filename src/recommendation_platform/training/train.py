from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from recommendation_platform.evaluation.metrics import ranking_report
from recommendation_platform.features.store import build_training_frame
from recommendation_platform.models.recommender import (
    RecommendationModel,
    popular_candidates,
    train_ranker,
)

LOGGER = logging.getLogger(__name__)


def temporal_split(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ordered = frame.sort_values("timestamp").reset_index(drop=True)
    first = int(len(ordered) * 0.70)
    second = int(len(ordered) * 0.85)
    return ordered.iloc[:first], ordered.iloc[first:second], ordered.iloc[second:]


def evaluate_model(
    model: RecommendationModel, test_frame: pd.DataFrame, items: pd.DataFrame, users: pd.DataFrame
) -> dict[str, float]:
    if test_frame.empty:
        return {"precision": 0.0, "recall": 0.0, "map": 0.0, "ndcg": 0.0, "hit_rate": 0.0}
    recommendations: dict[str, list[str]] = {}
    relevant: dict[str, set[str]] = {}
    for user_id, group in test_frame.groupby("user_id"):
        candidates = group.sort_values("timestamp").drop_duplicates("item_id").copy()
        candidates["score"] = model.predict_scores(candidates)
        recommendations[user_id] = (
            candidates.sort_values("score", ascending=False).item_id.head(10).tolist()
        )
        relevant[user_id] = set(group.loc[group.label > 0, "item_id"])
    return ranking_report(recommendations, relevant, 10)


def evaluate_baseline(
    test_events: pd.DataFrame, users: pd.DataFrame, items: pd.DataFrame, all_events: pd.DataFrame
) -> dict[str, float]:
    popular = popular_candidates(items, all_events, 50)
    recommendations = {user: popular for user in test_events.user_id.unique()}
    relevant = {
        user: set(
            group.loc[
                group.event_type.isin(["click", "purchase", "add_to_cart", "wishlist"]), "item_id"
            ]
        )
        for user, group in test_events.groupby("user_id")
    }
    return ranking_report(recommendations, relevant, 10)


def train(data_dir: Path, output_dir: Path, model_version: str = "ranker-v1") -> dict[str, object]:
    users = pd.read_parquet(data_dir / "users.parquet")
    items = pd.read_parquet(data_dir / "items.parquet")
    events = pd.read_parquet(data_dir / "interactions.parquet")
    features = build_training_frame(users, items, events)
    train_frame, validation_frame, test_frame = temporal_split(features)
    model = train_ranker(train_frame, model_version)
    metrics = evaluate_model(model, test_frame, items, users)
    baseline = evaluate_baseline(
        events.iloc[int(len(events) * 0.85) :], users, items, events.iloc[: int(len(events) * 0.85)]
    )
    model.metrics = {f"test_{key}": value for key, value in metrics.items()}
    model.metrics.update({f"baseline_{key}": value for key, value in baseline.items()})
    model.metrics["validation_rows"] = float(len(validation_frame))
    output_dir.mkdir(parents=True, exist_ok=True)
    model.save(output_dir / "model.joblib")
    report = {
        "model_version": model_version,
        "feature_version": "v1",
        "dataset_version": f"events-{len(events)}",
        "git_commit": os.getenv("GIT_COMMIT", "local"),
        "trained_at": datetime.now(UTC).isoformat(),
        "metrics": model.metrics,
        "temporal_split": {
            "train": len(train_frame),
            "validation": len(validation_frame),
            "test": len(test_frame),
        },
    }
    (output_dir / "evaluation_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    _try_log_mlflow(model, report)
    return report


def _try_log_mlflow(model: RecommendationModel, report: dict[str, object]) -> None:
    if os.getenv("ENABLE_MLFLOW", "false").lower() not in {"1", "true", "yes"}:
        return
    try:
        import mlflow

        mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
        mlflow.set_experiment(os.getenv("EXPERIMENT_NAME", "recommendation-platform"))
        with mlflow.start_run(run_name=str(report["model_version"])):
            mlflow.log_params(
                {
                    "feature_version": report["feature_version"],
                    "dataset_version": report["dataset_version"],
                }
            )
            mlflow.log_metrics({key: float(value) for key, value in model.metrics.items()})
            mlflow.log_artifact("data/processed/model.json") if Path(
                "data/processed/model.json"
            ).exists() else None
    except Exception as exc:  # MLflow is optional for the zero-dependency local path.
        LOGGER.info("MLflow unavailable; continuing with local artifact registry: %s", exc)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output", type=Path, default=Path("data/processed"))
    parser.add_argument("--model-version", default="ranker-v1")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    report = train(args.data_dir, args.output, args.model_version)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
