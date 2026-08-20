# Monitoring

The API exposes Prometheus metrics at `/metrics`. Request counters and latency histograms are labeled by endpoint and status. Recommendation counters record model version and fallback usage, while event counters record accepted event types. The Compose topology scrapes these metrics with Prometheus and provides a Grafana dashboard definition.

The drift module computes a population stability index for numeric reference and current distributions. A configured threshold of `0.20` marks a feature as drifted and raises `recommendation_retraining_required`. Quality monitoring uses NDCG@10 when ground truth becomes available and applies the configured minimum threshold. Both signals are deterministic and can be run in a scheduled batch job or an event-triggered orchestration step.

Recommended first alerts are API p95 above 200 ms, API error rate above 1%, empty or fallback recommendations above an agreed business threshold, feature PSI above 0.20, and production NDCG below 0.05. These are engineering defaults, not measured claims. Use `make benchmark` and production telemetry to calibrate them.
