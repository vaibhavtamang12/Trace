# Architecture Decision Records

## ADR-001: Kafka-compatible Redpanda for events

**Context:** The feedback loop needs durable, replayable, partitionable events. **Decision:** Use Redpanda locally because it preserves the Kafka protocol while keeping the Compose footprint small. **Alternatives:** RabbitMQ and direct HTTP. **Trade-offs:** Kafka operations add local complexity, but replay and consumer offsets are valuable for MLOps. **Consequence:** Producers and consumers use standard Kafka clients.

## ADR-002: Feast-compatible feature definitions

**Context:** Training and serving must share versioned features. **Decision:** Keep feature computation in reusable Python and include a Feast repository for the offline/online contract. **Alternatives:** Ad hoc SQL and model-specific feature code. **Trade-offs:** The local demo has a lightweight in-process store, while production can connect Feast to Redis and Parquet. **Consequence:** Feature names are explicit and point-in-time tests are mandatory.

## ADR-003: Supervised logistic ranking baseline

**Context:** The portfolio needs a measurable learned model without requiring native LightGBM binaries. **Decision:** Use scikit-learn logistic regression over temporal interaction features. **Alternatives:** LightGBM, XGBoost, matrix factorization. **Trade-offs:** It is less expressive than a gradient-boosted ranker, but reproducible and portable. **Consequence:** The model artifact can later be replaced behind the same interface.

## ADR-004: Redis-compatible online counters

**Context:** Inference needs low-latency online features. **Decision:** Use Redis keys for shared deployment and an in-memory implementation for zero-infrastructure development. **Alternatives:** PostgreSQL on every request. **Trade-offs:** Redis introduces another service, but it keeps hot counters separate from durable event storage. **Consequence:** Missing features default safely to zero.

## ADR-005: MLflow with local artifact fallback

**Context:** Runs need parameters, metrics, and model metadata. **Decision:** Attempt MLflow logging and always persist a local versioned artifact and JSON report. **Alternatives:** Files only or a managed registry. **Trade-offs:** The fallback keeps tests deterministic, while MLflow enables team workflows. **Consequence:** Registry connectivity is not required for local development.

## ADR-006: Bytewax-compatible stream boundary

**Context:** Stream processing is a real operational boundary. **Decision:** Encapsulate event validation, idempotency, feature updates, and DLQ logic in `StreamProcessor`; the Kafka adapter is isolated so Bytewax can be introduced without changing domain logic. **Consequence:** The core processor is directly testable.

## ADR-007: ONNX as an optional serving optimization

**Context:** Portable inference can reduce runtime overhead. **Decision:** Keep the model interface exportable and make ONNX benchmarking an optional deployment optimization rather than a hard local dependency. **Consequence:** Python inference remains the correctness path.

## ADR-008: Kubernetes and Helm templates

**Context:** The API should demonstrate production deployment concerns. **Decision:** Provide probes, resources, secrets, services, and HPA templates. **Consequence:** The repository documents intended deployment without falsely claiming a live cluster.
