# API

The FastAPI service generates OpenAPI documentation at `/docs` and `/redoc`.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Process liveness |
| GET | `/ready` | Catalog and model readiness |
| GET | `/metrics` | Prometheus exposition |
| GET | `/recommendations/{user_id}?limit=10` | Candidate generation and ranking |
| POST | `/events` | Validate, deduplicate, persist, and update features |
| GET | `/model` | Active model version and metrics |
| GET | `/experiments` | Control/treatment assignment metadata |

Example recommendation response:

```json
{
  "user_id": "user_000001",
  "model_version": "ranker-v1",
  "experiment": "treatment",
  "recommendations": [{"item_id": "item_000123", "score": 0.91, "rank": 1, "reason": "personalized"}],
  "fallback": false,
  "candidate_count": 100,
  "request_id": "generated-request-id"
}
```

Events require timezone-aware timestamps. Duplicate event IDs are accepted idempotently, while malformed payloads receive FastAPI validation errors before entering the application.
