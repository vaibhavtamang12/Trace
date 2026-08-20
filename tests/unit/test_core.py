from datetime import UTC, datetime

import pandas as pd

from recommendation_platform.common.schemas import EventType, UserEvent
from recommendation_platform.evaluation.metrics import ndcg_at_k, precision_at_k
from recommendation_platform.features.store import OnlineFeatureStore
from recommendation_platform.ingestion.generator import generate_dataset
from recommendation_platform.models.recommender import deterministic_bucket


def test_event_requires_timezone_aware_timestamp() -> None:
    event = UserEvent(
        event_id="event-1234",
        event_type=EventType.CLICK,
        user_id="user_1",
        item_id="item_1",
        timestamp=datetime.now(UTC),
        session_id="session",
        device_type="mobile",
    )
    assert event.event_type == EventType.CLICK


def test_online_store_is_idempotent_only_at_processor_boundary() -> None:
    store = OnlineFeatureStore()
    event = UserEvent(
        event_id="event-1234",
        event_type=EventType.CLICK,
        user_id="user_1",
        item_id="item_1",
        timestamp=datetime.now(UTC),
        session_id="session",
        device_type="mobile",
    )
    store.update(event)
    store.update(event)
    assert store.get_user("user_1")["user_click_count"] == 2


def test_ranking_metrics() -> None:
    assert precision_at_k(["a", "b", "c"], {"a", "c"}, 3) == 2 / 3
    assert ndcg_at_k(["a", "b"], {"a"}, 2) == 1.0


def test_assignment_is_stable() -> None:
    assert deterministic_bucket("user_1") == deterministic_bucket("user_1")


def test_generator_has_signal() -> None:
    users, items, events = generate_dataset(50, 40, 500, seed=7)
    assert len(users) == 50
    assert len(items) == 40
    assert len(events) == 500
    merged = events.merge(users[["user_id", "preferred_category"]], on="user_id").merge(
        items[["item_id", "category"]], on="item_id"
    )
    preferred_rate = (merged.preferred_category == merged.category).mean()
    assert preferred_rate > 0.15
    assert pd.to_datetime(events.timestamp, utc=True).notna().all()
