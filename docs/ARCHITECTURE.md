# Architecture

The platform follows an event-driven feedback loop. Clients emit `UserEvent` records to the Kafka-compatible `user-events` topic. The stream processor validates the event, deduplicates by `event_id`, updates user, item, and user-item features, and routes malformed payloads to `dead-letter-events`. The same event is persisted as partitionable raw data so offline training can reproduce the feature state.

The recommendation API uses a two-stage flow. Candidate generation merges category candidates and weighted popular items. The treatment arm scores candidates with the trained ranker, while the control arm uses the popular-items baseline. Business rules are represented by deduplication and bounded `limit` validation; further rules can be added without changing the model interface.

| Boundary | Responsibility | Failure behavior |
| --- | --- | --- |
| Producer | Create or publish validated JSON events | Retry Kafka publish; spool locally if unavailable |
| Stream processor | Validate, deduplicate, update online features | Dead-letter malformed events |
| Raw event lake | Store reproducible historical events | Date-partitioned JSONL demo path; Parquet batch path |
| Feature layer | Point-in-time offline features and online counters | In-memory fallback; Redis-compatible persistence |
| Training | Temporal split, feature construction, model fitting | Fail on empty or invalid training data |
| Registry | Save versioned artifacts and MLflow metadata | Local artifact remains usable if MLflow is unavailable |
| Serving | Candidate retrieval, scoring, metrics, API contract | Fallback to popular items |
| Monitoring | API, recommendation, drift, and quality signals | Retraining flag when thresholds are crossed |

The local path is intentionally useful without infrastructure. Docker Compose supplies the external services when the full topology is desired, while Kubernetes and Helm are templates for a real deployment and are not represented as already deployed.
