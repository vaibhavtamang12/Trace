from datetime import timedelta

from feast import Entity, FeatureView, Field
from feast.infra.offline_stores.file_source import FileSource
from feast.types import Float32, Int64

user = Entity(name="user", join_keys=["user_id"])
item = Entity(name="item", join_keys=["item_id"])
user_item = Entity(name="user_item", join_keys=["user_id", "item_id"])

user_source = FileSource(path="data/processed/user_features.parquet", timestamp_field="event_timestamp")
item_source = FileSource(path="data/processed/item_features.parquet", timestamp_field="event_timestamp")

user_features = FeatureView(
    name="user_features",
    entities=[user],
    ttl=timedelta(days=30),
    schema=[Field(name="user_click_count_1h", dtype=Int64), Field(name="user_purchase_count_24h", dtype=Int64), Field(name="user_engagement", dtype=Float32)],
    source=user_source,
)
item_features = FeatureView(
    name="item_features",
    entities=[item],
    ttl=timedelta(days=30),
    schema=[Field(name="item_views_1h", dtype=Int64), Field(name="item_ctr_1h", dtype=Float32), Field(name="item_popularity_24h", dtype=Float32)],
    source=item_source,
)
