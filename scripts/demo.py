from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from recommendation_platform.common.schemas import EventType, UserEvent
from recommendation_platform.features.store import OnlineFeatureStore
from recommendation_platform.ingestion.generator import generate_dataset, write_dataset
from recommendation_platform.monitoring.monitor import check_performance, detect_drift
from recommendation_platform.streaming.processor import StreamProcessor
from recommendation_platform.training.train import train


def main() -> None:
    data_dir = Path("data")
    users, items, interactions = generate_dataset(100, 80, 1000, seed=42)
    write_dataset(users, items, interactions, data_dir)
    report = train(data_dir, data_dir / "processed")
    processor = StreamProcessor(OnlineFeatureStore())
    event = UserEvent(
        event_id="demo-event",
        event_type=EventType.CLICK,
        user_id="user_000001",
        item_id="item_000001",
        timestamp=datetime.now(UTC),
        session_id="demo-session",
        device_type="mobile",
    )
    processed = processor.process(event.model_dump(mode="json"))
    current = interactions.select_dtypes("number")
    drift = detect_drift(current, current.copy())
    performance = check_performance({"ndcg": float(report["metrics"].get("test_ndcg", 0.0))})
    print(
        json.dumps(
            {
                "event_processed": processed,
                "online_user_features": processor.store.get_user("user_000001"),
                "drift": drift,
                "performance": performance,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
