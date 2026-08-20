from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from recommendation_platform.common.schemas import UserEvent


def persist_events(events: list[UserEvent], root: Path = Path("data/raw")) -> list[Path]:
    """Persist validated, deduplicated events into UTC date partitions as Parquet."""
    if not events:
        return []
    frame = pd.DataFrame([event.model_dump(mode="json") for event in events]).drop_duplicates(
        "event_id"
    )
    frame["metadata"] = frame["metadata"].map(json.dumps)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    written: list[Path] = []
    for event_date, group in frame.groupby(frame.timestamp.dt.date):
        partition = (
            root
            / f"year={event_date.year}"
            / f"month={event_date.month:02d}"
            / f"day={event_date.day:02d}"
        )
        partition.mkdir(parents=True, exist_ok=True)
        path = partition / "events.parquet"
        group.to_parquet(path, index=False)
        written.append(path)
    metadata = {
        "events_received": len(events),
        "events_persisted": len(frame),
        "partitions": [str(path) for path in written],
    }
    (root / "ingestion_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return written


def read_partitioned_events(root: Path = Path("data/raw")) -> pd.DataFrame:
    files = sorted(root.glob("year=*/month=*/day=*/events.parquet"))
    if not files:
        return pd.DataFrame()
    frame = pd.concat([pd.read_parquet(path) for path in files], ignore_index=True)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    return frame.drop_duplicates("event_id").sort_values("timestamp").reset_index(drop=True)
