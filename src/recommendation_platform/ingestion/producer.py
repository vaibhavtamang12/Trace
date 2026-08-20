from __future__ import annotations

import argparse
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd

from recommendation_platform.common.schemas import EventType, UserEvent
from recommendation_platform.config.settings import get_settings

LOGGER = logging.getLogger(__name__)


def sample_events(count: int, data_dir: Path = Path("data")) -> list[UserEvent]:
    users = pd.read_parquet(data_dir / "users.parquet")
    items = pd.read_parquet(data_dir / "items.parquet")
    events: list[UserEvent] = []
    for index in range(count):
        user = users.iloc[index % len(users)]
        item = items.iloc[index % len(items)]
        events.append(
            UserEvent(
                event_id=str(uuid4()),
                event_type=EventType.CLICK,
                user_id=user.user_id,
                item_id=item.item_id,
                timestamp=datetime.now(UTC),
                session_id=f"demo-session-{index}",
                device_type=user.device_type,
                metadata={"producer": "cli"},
            )
        )
    return events


def publish(events: list[UserEvent], bootstrap_servers: str, topic: str) -> int:
    try:
        from kafka import KafkaProducer

        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            acks="all",
            retries=3,
            value_serializer=lambda value: json.dumps(value).encode(),
        )
        for event in events:
            producer.send(topic, event.model_dump(mode="json"))
        producer.flush()
        return len(events)
    except Exception as exc:
        LOGGER.warning("Kafka unavailable; writing local event spool instead: %s", exc)
        spool = Path("data/raw/event_spool.jsonl")
        spool.parent.mkdir(parents=True, exist_ok=True)
        with spool.open("a", encoding="utf-8") as handle:
            for event in events:
                handle.write(json.dumps(event.model_dump(mode="json")) + "\n")
        return len(events)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--bootstrap-servers", default=None)
    parser.add_argument("--topic", default=None)
    args = parser.parse_args()
    settings = get_settings()
    published = publish(
        sample_events(args.count),
        args.bootstrap_servers or settings.kafka_bootstrap_servers,
        args.topic or settings.kafka_events_topic,
    )
    print(json.dumps({"published": published, "topic": args.topic or settings.kafka_events_topic}))


if __name__ == "__main__":
    main()
