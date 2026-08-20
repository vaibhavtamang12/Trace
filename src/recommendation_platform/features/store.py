from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

import pandas as pd

from recommendation_platform.common.schemas import EVENT_WEIGHTS, EventType, UserEvent

LOGGER = logging.getLogger(__name__)


class OnlineFeatureStore:
    """Small online store with an optional Redis backend for local and Compose modes."""

    def __init__(self, redis_client: Any | None = None) -> None:
        self.redis = redis_client
        self.users: dict[str, dict[str, float]] = defaultdict(dict)
        self.items: dict[str, dict[str, float]] = defaultdict(dict)
        self.user_items: dict[str, dict[str, float]] = defaultdict(dict)

    def update(self, event: UserEvent) -> None:
        event_time = event.timestamp.astimezone(UTC)
        user = self.users[event.user_id]
        item = self.items[event.item_id]
        pair = self.user_items[f"{event.user_id}:{event.item_id}"]
        event_name = event.event_type.value
        user[f"user_{event_name}_count"] = user.get(f"user_{event_name}_count", 0.0) + 1
        item[f"item_{event_name}_count"] = item.get(f"item_{event_name}_count", 0.0) + 1
        pair[f"user_item_{event_name}_count"] = pair.get(f"user_item_{event_name}_count", 0.0) + 1
        user["user_engagement"] = user.get("user_engagement", 0.0) + EVENT_WEIGHTS[event.event_type]
        item["item_weighted_popularity"] = (
            item.get("item_weighted_popularity", 0.0) + EVENT_WEIGHTS[event.event_type]
        )
        user["last_event_timestamp"] = event_time.timestamp()
        pair["user_item_last_interaction"] = event_time.timestamp()
        if event.event_type == EventType.PURCHASE:
            user["user_purchase_count_24h"] = user.get("user_purchase_count_24h", 0.0) + 1
            pair["user_item_purchase_count"] = pair.get("user_item_purchase_count", 0.0) + 1
        self._persist(event.user_id, "user", user)
        self._persist(event.item_id, "item", item)
        self._persist(f"{event.user_id}:{event.item_id}", "user_item", pair)

    def get_user(self, user_id: str) -> dict[str, float]:
        return dict(self.users.get(user_id, {}))

    def get_item(self, item_id: str) -> dict[str, float]:
        return dict(self.items.get(item_id, {}))

    def get_user_item(self, user_id: str, item_id: str) -> dict[str, float]:
        return dict(self.user_items.get(f"{user_id}:{item_id}", {}))

    def _persist(self, key: str, entity: str, values: dict[str, float]) -> None:
        if self.redis is not None:
            self.redis.set(f"features:{entity}:{key}", json.dumps(values))


class FeatureComputer:
    """Computes windowed features without using events newer than the as-of timestamp."""

    @staticmethod
    def user_features(events: pd.DataFrame, user_id: str, as_of: datetime) -> dict[str, float]:
        frame = _as_of(events, as_of)
        frame = frame[frame.user_id == user_id]
        one_hour = frame[frame.timestamp >= as_of - timedelta(hours=1)]
        one_day = frame[frame.timestamp >= as_of - timedelta(hours=24)]
        return {
            "user_click_count_1h": float((one_hour.event_type == EventType.CLICK.value).sum()),
            "user_view_count_1h": float((one_hour.event_type == EventType.VIEW.value).sum()),
            "user_purchase_count_24h": float(
                (one_day.event_type == EventType.PURCHASE.value).sum()
            ),
            "user_cart_count_24h": float((one_day.event_type == EventType.ADD_TO_CART.value).sum()),
            "user_activity": float(len(frame)),
            "user_engagement": float(sum(EVENT_WEIGHTS[EventType(e)] for e in frame.event_type)),
        }

    @staticmethod
    def item_features(events: pd.DataFrame, item_id: str, as_of: datetime) -> dict[str, float]:
        frame = _as_of(events, as_of)
        frame = frame[frame.item_id == item_id]
        one_hour = frame[frame.timestamp >= as_of - timedelta(hours=1)]
        one_day = frame[frame.timestamp >= as_of - timedelta(hours=24)]
        views = float((one_hour.event_type == EventType.VIEW.value).sum())
        clicks = float((one_hour.event_type == EventType.CLICK.value).sum())
        return {
            "item_views_1h": views,
            "item_clicks_1h": clicks,
            "item_purchases_1h": float((one_hour.event_type == EventType.PURCHASE.value).sum()),
            "item_ctr_1h": clicks / max(views, 1.0),
            "item_popularity_24h": float(
                sum(EVENT_WEIGHTS[EventType(e)] for e in one_day.event_type)
            ),
        }

    @staticmethod
    def user_item_features(
        events: pd.DataFrame, user_id: str, item_id: str, as_of: datetime
    ) -> dict[str, float]:
        frame = _as_of(events, as_of)
        frame = frame[(frame.user_id == user_id) & (frame.item_id == item_id)]
        return {
            "user_item_views": float((frame.event_type == EventType.VIEW.value).sum()),
            "user_item_clicks": float((frame.event_type == EventType.CLICK.value).sum()),
            "user_item_purchase_count": float((frame.event_type == EventType.PURCHASE.value).sum()),
            "user_item_interactions": float(len(frame)),
        }


def build_training_frame(
    users: pd.DataFrame, items: pd.DataFrame, events: pd.DataFrame
) -> pd.DataFrame:
    """Build leakage-safe features with cumulative state that excludes the current event."""
    frame = events.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame = frame.sort_values("timestamp").reset_index(drop=True)
    weights = frame.event_type.map(
        {event.value: weight for event, weight in EVENT_WEIGHTS.items()}
    ).astype(float)
    positive = frame.event_type.isin(["click", "wishlist", "add_to_cart", "purchase"]).astype(float)
    frame["user_click_count_1h"] = frame.groupby("user_id").event_type.transform(
        lambda x: x.eq("click").cumsum().shift(fill_value=0)
    )
    frame["user_view_count_1h"] = frame.groupby("user_id").event_type.transform(
        lambda x: x.eq("view").cumsum().shift(fill_value=0)
    )
    frame["user_purchase_count_24h"] = frame.groupby("user_id").event_type.transform(
        lambda x: x.eq("purchase").cumsum().shift(fill_value=0)
    )
    frame["user_cart_count_24h"] = frame.groupby("user_id").event_type.transform(
        lambda x: x.eq("add_to_cart").cumsum().shift(fill_value=0)
    )
    frame["user_activity"] = frame.groupby("user_id").cumcount()
    frame["user_engagement"] = weights.groupby(frame.user_id).cumsum().shift(fill_value=0)
    frame["item_views_1h"] = frame.groupby("item_id").event_type.transform(
        lambda x: x.eq("view").cumsum().shift(fill_value=0)
    )
    frame["item_clicks_1h"] = frame.groupby("item_id").event_type.transform(
        lambda x: x.eq("click").cumsum().shift(fill_value=0)
    )
    frame["item_purchases_1h"] = frame.groupby("item_id").event_type.transform(
        lambda x: x.eq("purchase").cumsum().shift(fill_value=0)
    )
    frame["item_ctr_1h"] = frame.item_clicks_1h / frame.item_views_1h.replace(0, 1)
    frame["item_popularity_24h"] = weights.groupby(frame.item_id).cumsum().shift(fill_value=0)
    pair = frame.user_id + ":" + frame.item_id
    frame["user_item_views"] = frame.groupby(pair).event_type.transform(
        lambda x: x.eq("view").cumsum().shift(fill_value=0)
    )
    frame["user_item_clicks"] = frame.groupby(pair).event_type.transform(
        lambda x: x.eq("click").cumsum().shift(fill_value=0)
    )
    frame["user_item_purchase_count"] = frame.groupby(pair).event_type.transform(
        lambda x: x.eq("purchase").cumsum().shift(fill_value=0)
    )
    frame["user_item_interactions"] = frame.groupby(pair).cumcount()
    users_lookup = users.set_index("user_id")
    items_lookup = items.set_index("item_id")
    frame["age"] = frame.user_id.map(users_lookup.age).astype(float)
    frame["price"] = frame.item_id.map(items_lookup.price).astype(float)
    frame["rating"] = frame.item_id.map(items_lookup.rating).astype(float)
    frame["item_popularity_score"] = frame.item_id.map(items_lookup.popularity_score).astype(float)
    frame["same_category"] = (
        frame.user_id.map(users_lookup.preferred_category)
        == frame.item_id.map(items_lookup.category)
    ).astype(float)
    frame["hour"] = frame.timestamp.dt.hour.astype(float)
    frame["device_mobile"] = (frame.device_type == "mobile").astype(float)
    frame["label"] = positive
    return frame


def _as_of(events: pd.DataFrame, as_of: datetime) -> pd.DataFrame:
    timestamp = pd.to_datetime(events["timestamp"], utc=True)
    cutoff = pd.Timestamp(as_of if as_of.tzinfo else as_of.replace(tzinfo=UTC))
    mask = timestamp < cutoff
    return events.loc[mask].copy().assign(timestamp=timestamp.loc[mask])
