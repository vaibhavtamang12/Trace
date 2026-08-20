# Experiments

Users are assigned deterministically with SHA-256 of `experiment_name:user_id`, so the same user remains in the same bucket across requests and process restarts. The control arm uses weighted popular items; the treatment arm uses the trained ranker after candidate generation.

A production canary should start at 10% treatment traffic, then advance through 25%, 50%, and 100% only after comparing latency, error rate, CTR, conversion, and recommendation quality. Roll back to the prior model when safety or quality thresholds regress. Offline ranking metrics are useful gates but do not replace online CTR, conversion, revenue/session, and engagement measurements.
