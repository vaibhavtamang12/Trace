from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Iterable
from typing import Any

from recommendation_platform.common.schemas import UserEvent
from recommendation_platform.features.store import OnlineFeatureStore

LOGGER = logging.getLogger(__name__)


class StreamProcessor:
    """Processes valid events exactly once per event_id and routes malformed payloads to a DLQ."""

    def __init__(self, store: OnlineFeatureStore | None = None) -> None:
        self.store = store or OnlineFeatureStore()
        self.processed_ids: set[str] = set()
        self.dead_letters: list[dict[str, Any]] = []

    def process(self, payload: dict[str, Any]) -> bool:
        try:
            event = UserEvent.model_validate(payload)
            if event.event_id in self.processed_ids:
                return False
            self.store.update(event)
            self.processed_ids.add(event.event_id)
            return True
        except Exception as exc:
            self.dead_letters.append({"payload": payload, "error": str(exc)})
            LOGGER.warning("Malformed event routed to dead-letter queue: %s", exc)
            return False

    def process_many(self, payloads: Iterable[dict[str, Any]]) -> int:
        return sum(self.process(payload) for payload in payloads)


def consume_kafka(bootstrap_servers: str, topic: str, processor: StreamProcessor) -> None:
    from kafka import KafkaConsumer

    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        value_deserializer=lambda value: json.loads(value.decode()),
    )
    for message in consumer:
        processor.process(message.value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--bootstrap-servers", default="localhost:19092")
    parser.add_argument("--topic", default="user-events")
    args = parser.parse_args()
    processor = StreamProcessor()
    if args.demo:
        print(json.dumps({"processed": 0, "dead_letters": 0, "mode": "demo"}))
    else:
        consume_kafka(args.bootstrap_servers, args.topic, processor)


if __name__ == "__main__":
    main()
