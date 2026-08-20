# ML Pipeline

The pipeline reads users, items, and interactions from Parquet, sorts interaction rows by event timestamp, and builds features from cumulative state that excludes the current event. This prevents future events from leaking into the feature vector for the prediction timestamp. The data is split chronologically into 70% training, 15% validation, and 15% test partitions.

The ranker is compared with a weighted popular-items baseline using Precision@10, Recall@10, MAP@10, NDCG@10, and Hit Rate@10. Every artifact includes model version, feature version, dataset version, Git commit, timestamps, feature columns, and metric values. When MLflow is reachable, the training run also logs parameters and metrics to the configured experiment; when it is not reachable, the local joblib artifact and JSON report remain the source of truth for the local demo.

Promotion is deliberately conservative. `evaluation.evaluate` requires a positive NDCG result and a configured gain over the baseline. A production deployment should additionally compare against the currently promoted model and enforce latency and error-rate safety limits before advancing a candidate through canary percentages.

```bash
make generate-data
make train
make evaluate
cat data/processed/evaluation_report.json
```

The retraining trigger is represented by `monitoring.monitor.detect_drift` and `check_performance`: a feature PSI above threshold or NDCG below threshold sets `recommendation_retraining_required` to one. An orchestrator can call the same deterministic training command on a schedule or after a data-volume event.
