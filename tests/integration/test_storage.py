from datetime import UTC, datetime
from pathlib import Path

from recommendation_platform.common.schemas import EventType, UserEvent
from recommendation_platform.ingestion.storage import persist_events, read_partitioned_events


def test_partitioned_storage_deduplicates(tmp_path: Path) -> None:
    event = UserEvent(
        event_id="event-storage",
        event_type=EventType.VIEW,
        user_id="user_1",
        item_id="item_1",
        timestamp=datetime(2026, 8, 20, tzinfo=UTC),
        session_id="session",
        device_type="mobile",
    )
    written = persist_events([event, event], tmp_path)
    assert len(written) == 1
    restored = read_partitioned_events(tmp_path)
    assert len(restored) == 1
    assert restored.iloc[0].event_id == "event-storage"
