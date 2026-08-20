from __future__ import annotations

import argparse
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import numpy as np
import pandas as pd

from recommendation_platform.common.schemas import EVENT_WEIGHTS

LOGGER = logging.getLogger(__name__)
CATEGORIES = ["electronics", "books", "home", "fitness", "beauty", "outdoors", "fashion", "grocery"]
DEVICES = ["mobile", "desktop", "tablet"]
COUNTRIES = ["US", "GB", "IN", "CA", "DE", "AU"]


def generate_dataset(
    users_count: int = 1000,
    items_count: int = 500,
    interactions_count: int = 20_000,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    now = datetime.now(UTC)
    user_categories = rng.choice(CATEGORIES, size=users_count)
    users = pd.DataFrame(
        {
            "user_id": [f"user_{i:06d}" for i in range(1, users_count + 1)],
            "age": rng.integers(18, 75, users_count),
            "country": rng.choice(COUNTRIES, users_count),
            "device_type": rng.choice(DEVICES, users_count, p=[0.60, 0.30, 0.10]),
            "signup_date": [
                now - timedelta(days=int(x)) for x in rng.integers(1, 730, users_count)
            ],
            "preferred_category": user_categories,
            "activity_level": np.round(rng.beta(2, 4, users_count), 4),
            "price_sensitivity": np.round(rng.beta(2, 2, users_count), 4),
        }
    )
    item_categories = rng.choice(CATEGORIES, items_count)
    popularity = rng.lognormal(mean=0.0, sigma=1.0, size=items_count)
    items = pd.DataFrame(
        {
            "item_id": [f"item_{i:06d}" for i in range(1, items_count + 1)],
            "category": item_categories,
            "subcategory": [
                f"{category}_sub_{int(rng.integers(1, 5))}" for category in item_categories
            ],
            "price": np.round(rng.lognormal(3.3, 0.65, items_count), 2),
            "brand": [f"brand_{int(x):03d}" for x in rng.integers(1, 80, items_count)],
            "rating": np.round(np.clip(rng.normal(4.0, 0.55, items_count), 1, 5), 2),
            "popularity_score": np.round(popularity, 5),
            "created_at": [now - timedelta(days=int(x)) for x in rng.integers(1, 900, items_count)],
        }
    )
    item_by_category = {
        category: items.index[items.category == category].to_numpy() for category in CATEGORIES
    }
    user_index = rng.integers(0, users_count, interactions_count)
    timestamps = [
        now - timedelta(minutes=int(x)) for x in rng.integers(0, 180 * 24 * 60, interactions_count)
    ]
    events: list[dict[str, object]] = []
    event_types = list(EVENT_WEIGHTS)
    event_probabilities = np.array([0.56, 0.22, 0.10, 0.035, 0.025, 0.03, 0.03])
    event_probabilities /= event_probabilities.sum()
    for index, user_idx in enumerate(user_index):
        user = users.iloc[user_idx]
        category = (
            str(user.preferred_category) if rng.random() < 0.75 else str(rng.choice(CATEGORIES))
        )
        choices = item_by_category[category]
        if len(choices) == 0:
            item_idx = int(rng.integers(0, items_count))
        else:
            weights = items.iloc[choices].popularity_score.to_numpy() ** 0.55
            weights = weights / weights.sum()
            item_idx = int(rng.choice(choices, p=weights))
        event_type = str(rng.choice(event_types, p=event_probabilities))
        events.append(
            {
                "event_id": str(uuid4()),
                "event_type": event_type,
                "user_id": user.user_id,
                "item_id": items.iloc[item_idx].item_id,
                "timestamp": timestamps[index].isoformat(),
                "session_id": f"session_{int(index / 4):08d}",
                "device_type": user.device_type,
                "position": int(rng.integers(0, 30)),
                "metadata": json.dumps({"synthetic": True, "seed": seed}),
            }
        )
    interactions = pd.DataFrame(events).sort_values("timestamp").reset_index(drop=True)
    return users, items, interactions


def write_dataset(
    users: pd.DataFrame, items: pd.DataFrame, interactions: pd.DataFrame, output: Path
) -> dict[str, object]:
    output.mkdir(parents=True, exist_ok=True)
    users.to_parquet(output / "users.parquet", index=False)
    items.to_parquet(output / "items.parquet", index=False)
    interactions.to_parquet(output / "interactions.parquet", index=False)
    profile = {
        "users": int(len(users)),
        "items": int(len(items)),
        "interactions": int(len(interactions)),
        "event_distribution": interactions.event_type.value_counts(normalize=True)
        .round(4)
        .to_dict(),
        "category_distribution": items.category.value_counts(normalize=True).round(4).to_dict(),
        "null_rates": interactions.isna().mean().round(6).to_dict(),
        "timestamp_min": str(interactions.timestamp.min()),
        "timestamp_max": str(interactions.timestamp.max()),
    }
    (output / "data_profile.json").write_text(json.dumps(profile, indent=2), encoding="utf-8")
    return profile


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic recommendation data")
    parser.add_argument("--users", type=int, default=1000)
    parser.add_argument("--items", type=int, default=500)
    parser.add_argument("--interactions", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("data"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    profile = write_dataset(
        *generate_dataset(args.users, args.items, args.interactions, args.seed), args.output
    )
    LOGGER.info("Generated dataset", extra={"profile": profile})


if __name__ == "__main__":
    main()
