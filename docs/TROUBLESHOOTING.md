# Troubleshooting

If recommendations return a catalog-not-loaded error, run `make generate-data` from the repository root and restart the API so it reloads Parquet artifacts. If no trained model exists, the API remains usable with the popular-items control path; run `make train` to enable treatment scoring.

If Kafka is unavailable, `make produce-events` retries through the local JSONL spool at `data/raw/event_spool.jsonl`. In Compose mode, verify Redpanda health with `docker compose ps` and inspect `docker compose logs redpanda`. Redis is optional for the local API path; the in-memory online store is used when no Redis client is configured.

If Parquet support is missing, reinstall the project dependencies with `pip install -e '.[dev]'`. If Docker Compose fails validation, run `docker compose config` and check that the working directory is the repository root and that no secret values were added to source control.
