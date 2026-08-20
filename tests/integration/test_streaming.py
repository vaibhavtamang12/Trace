from datetime import UTC, datetime

from recommendation_platform.common.schemas import EventType, UserEvent
from recommendation_platform.streaming.processor import StreamProcessor


def payload(event_id: str = "event-1234") -> dict[str, object]:
    return UserEvent(
        event_id=event_id,
        event_type=EventType.VIEW,
        user_id="user_1",
        item_id="item_1",
        timestamp=datetime.now(UTC),
        session_id="session",
        device_type="mobile",
    ).model_dump(mode="json")


def test_processor_deduplicates_and_dead_letters() -> None:
    processor = StreamProcessor()
    assert processor.process(payload()) is True
    assert processor.process(payload()) is False
    assert processor.process({"event_type": "not-valid"}) is False
    assert len(processor.dead_letters) == 1
    assert processor.store.get_user("user_1")["user_view_count"] == 1
