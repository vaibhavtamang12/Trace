from pathlib import Path

from recommendation_platform.features.store import build_training_frame
from recommendation_platform.ingestion.generator import generate_dataset, write_dataset
from recommendation_platform.training.train import train


def test_training_frame_excludes_current_event() -> None:
    users, items, events = generate_dataset(8, 8, 32, seed=3)
    frame = build_training_frame(users, items, events)
    assert len(frame) == len(events)
    assert (frame.user_activity >= 0).all()
    assert frame.user_activity.iloc[0] == 0


def test_training_writes_artifacts(tmp_path: Path) -> None:
    users, items, events = generate_dataset(20, 20, 120, seed=4)
    data_dir = tmp_path / "data"
    write_dataset(users, items, events, data_dir)
    report = train(data_dir, data_dir / "processed")
    assert (data_dir / "processed/model.joblib").exists()
    assert (data_dir / "processed/evaluation_report.json").exists()
    assert "test_ndcg" in report["metrics"]
