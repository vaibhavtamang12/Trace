# Feature Store

The feature model has three entities: `user`, `item`, and `user_item`. Offline features are generated from historical events with a timestamp cutoff. Online features are updated by the stream processor and can be persisted to Redis using keys such as `features:user:user_000001`.

| Feature | Entity | Type | Source / transformation | TTL | Version |
| --- | --- | --- | --- | --- | --- |
| `user_click_count_1h` | user | float | prior user clicks in the one-hour window | 1h | v1 |
| `user_purchase_count_24h` | user | float | prior user purchases in the 24-hour window | 24h | v1 |
| `item_views_1h` | item | float | prior item views in the one-hour window | 1h | v1 |
| `item_ctr_1h` | item | float | prior clicks divided by prior views | 1h | v1 |
| `user_item_clicks` | user_item | float | prior clicks for the pair | 30d | v1 |
| `user_item_purchase_count` | user_item | float | prior purchases for the pair | 90d | v1 |
| `same_category` | user-item | float | user preferred category equals item category | catalog | v1 |

The important invariant is `event.timestamp < as_of` for every event used by an offline feature row. The vector used by inference uses the same feature names and defaults missing online counters to zero, which keeps training and serving schemas aligned.
