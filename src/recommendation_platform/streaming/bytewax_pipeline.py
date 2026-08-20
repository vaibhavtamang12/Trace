from __future__ import annotations

from typing import Any

from recommendation_platform.streaming.processor import StreamProcessor


def build_flow() -> Any:
    """Build a Bytewax flow when the optional dependency is installed."""
    try:
        from bytewax import operators as op
        from bytewax.connectors.kafka import KafkaSource
        from bytewax.dataflow import Dataflow
    except ImportError as exc:
        raise RuntimeError("Install bytewax to run the production stream adapter") from exc

    processor = StreamProcessor()
    flow = Dataflow("recommendation-events")
    stream = op.input(
        "kafka-input",
        flow,
        KafkaSource(brokers=["localhost:19092"], topics=["user-events"], starting_offset=0),
    )
    op.map("validate-and-update-features", stream, processor.process)
    return flow
