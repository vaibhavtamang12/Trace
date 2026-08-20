from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

FEATURE_COLUMNS = [
    "user_click_count_1h",
    "user_view_count_1h",
    "user_purchase_count_24h",
    "user_cart_count_24h",
    "user_activity",
    "user_engagement",
    "item_views_1h",
    "item_clicks_1h",
    "item_purchases_1h",
    "item_ctr_1h",
    "item_popularity_24h",
    "age",
    "price",
    "rating",
    "item_popularity_score",
    "same_category",
    "hour",
    "device_mobile",
    "user_item_views",
    "user_item_clicks",
    "user_item_purchase_count",
    "user_item_interactions",
]


@dataclass
class RecommendationModel:
    estimator: LogisticRegression
    feature_columns: list[str]
    model_version: str
    metrics: dict[str, float]

    def predict_scores(self, frame: pd.DataFrame) -> np.ndarray:
        values = frame.reindex(columns=self.feature_columns, fill_value=0.0).astype(float)
        return self.estimator.predict_proba(values)[:, 1]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        path.with_suffix(".json").write_text(
            json.dumps(
                {
                    "model_version": self.model_version,
                    "feature_columns": self.feature_columns,
                    "metrics": self.metrics,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> RecommendationModel:
        return joblib.load(path)


def train_ranker(training_frame: pd.DataFrame, version: str = "ranker-v1") -> RecommendationModel:
    if training_frame.empty:
        raise ValueError("training frame is empty")
    model = LogisticRegression(max_iter=300, class_weight="balanced", random_state=42)
    model.fit(training_frame[FEATURE_COLUMNS], training_frame["label"].astype(int))
    return RecommendationModel(model, FEATURE_COLUMNS, version, {})


def popular_candidates(items: pd.DataFrame, events: pd.DataFrame, limit: int = 100) -> list[str]:
    scores = (
        events.assign(
            weight=events.event_type.map(
                {
                    "impression": 0.01,
                    "view": 0.05,
                    "click": 0.20,
                    "wishlist": 0.35,
                    "add_to_cart": 0.60,
                    "purchase": 1.0,
                    "skip": -0.10,
                }
            )
        )
        .groupby("item_id")
        .weight.sum()
    )
    ranked = items.assign(popularity=items.item_id.map(scores).fillna(0) + items.popularity_score)
    return ranked.sort_values("popularity", ascending=False).item_id.head(limit).tolist()


def category_candidates(
    user_id: str, users: pd.DataFrame, items: pd.DataFrame, limit: int = 100
) -> list[str]:
    matches = users[users.user_id == user_id]
    if matches.empty:
        return []
    category = matches.iloc[0].preferred_category
    return (
        items[items.category == category]
        .sort_values("rating", ascending=False)
        .item_id.head(limit)
        .tolist()
    )


def deterministic_bucket(user_id: str, experiment: str = "recommendations-v1") -> str:
    digest = hashlib.sha256(f"{experiment}:{user_id}".encode()).hexdigest()
    return "treatment" if int(digest[:8], 16) % 2 else "control"
