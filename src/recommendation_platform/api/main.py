from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import Counter, Histogram, generate_latest

from recommendation_platform.common.logging import configure_logging
from recommendation_platform.common.schemas import (
    EventAcceptedResponse,
    Recommendation,
    RecommendationResponse,
    UserEvent,
)
from recommendation_platform.config.settings import get_settings
from recommendation_platform.features.store import OnlineFeatureStore
from recommendation_platform.models.recommender import (
    RecommendationModel,
    category_candidates,
    deterministic_bucket,
    popular_candidates,
)

configure_logging()
LOGGER = logging.getLogger(__name__)
settings = get_settings()
app = FastAPI(title="Real-Time Recommendation Platform", version="0.1.0")
REQUESTS = Counter(
    "recommendation_api_requests_total", "Total API requests", ["endpoint", "status"]
)
LATENCY = Histogram("recommendation_api_latency_seconds", "API latency", ["endpoint"])
RECOMMENDATIONS = Counter(
    "recommendations_served_total", "Recommendations served", ["model_version", "fallback"]
)
EVENTS = Counter("events_ingested_total", "Events accepted by the API", ["event_type"])

DATA_DIR = Path("data")
MODEL_PATH = settings.model_path
feature_store = OnlineFeatureStore()
users = pd.DataFrame()
items = pd.DataFrame()
events: list[UserEvent] = []
model: RecommendationModel | None = None


def _load_artifacts() -> None:
    global users, items, model
    try:
        users = pd.read_parquet(DATA_DIR / "users.parquet")
        items = pd.read_parquet(DATA_DIR / "items.parquet")
    except FileNotFoundError:
        users = pd.DataFrame(columns=["user_id", "preferred_category", "age"])
        items = pd.DataFrame(columns=["item_id", "category", "rating", "popularity_score", "price"])
    if MODEL_PATH.exists():
        model = RecommendationModel.load(MODEL_PATH)


_load_artifacts()


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    status = "500"
    try:
        response = await call_next(request)
        status = str(response.status_code)
        return response
    finally:
        elapsed = time.perf_counter() - start
        REQUESTS.labels(request.url.path, status).inc()
        LATENCY.labels(request.url.path).observe(elapsed)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "recommendation-api"}


@app.get("/ready")
def ready() -> dict[str, object]:
    return {
        "ready": not users.empty and not items.empty,
        "catalog_items": len(items),
        "model_loaded": model is not None,
    }


@app.get("/metrics", response_class=PlainTextResponse)
def metrics() -> str:
    return generate_latest().decode("utf-8")


@app.get("/model")
def model_metadata() -> dict[str, object]:
    if model is None:
        return {"model_name": "popular-items", "model_version": "fallback-v1", "metrics": {}}
    return {
        "model_name": "recommendation-ranker",
        "model_version": model.model_version,
        "metrics": model.metrics,
    }


@app.get("/experiments")
def experiments() -> dict[str, object]:
    return {
        "experiment": "recommendations-v1",
        "control": "popular-items",
        "treatment": "ranker",
        "assignment": "sha256(user_id)",
    }


@app.get("/recommendations/{user_id}", response_model=RecommendationResponse)
def recommendations(
    user_id: str, limit: int = Query(default=10, ge=1, le=100)
) -> RecommendationResponse:
    request_id = str(uuid4())
    if users.empty or items.empty:
        raise HTTPException(status_code=503, detail="catalog is not loaded; run make generate-data")
    if user_id not in set(users.user_id):
        raise HTTPException(status_code=404, detail=f"unknown user: {user_id}")
    experiment = deterministic_bucket(user_id)
    candidates = list(
        dict.fromkeys(category_candidates(user_id, users, items, settings.candidate_limit))
    )
    fallback = False
    if experiment == "control" or model is None:
        candidates = list(
            dict.fromkeys(
                popular_candidates(items, _events_frame(), settings.candidate_limit) + candidates
            )
        )
        ranked = [
            (item_id, float(len(candidates) - idx), "popular")
            for idx, item_id in enumerate(candidates)
        ]
    else:
        candidates = list(
            dict.fromkeys(
                candidates + popular_candidates(items, _events_frame(), settings.candidate_limit)
            )
        )
        ranked = []
        user_row = users[users.user_id == user_id].iloc[0]
        as_of = datetime.now(UTC)
        for item_id in candidates:
            item_row = items[items.item_id == item_id].iloc[0]
            feature_row = _inference_features(user_row, item_row, user_id, item_id, as_of)
            score = float(model.predict_scores(pd.DataFrame([feature_row]))[0])
            ranked.append((item_id, score, "personalized"))
        ranked.sort(key=lambda row: row[1], reverse=True)
    result = [
        Recommendation(item_id=item_id, score=round(score, 6), rank=rank, reason=reason)
        for rank, (item_id, score, reason) in enumerate(ranked[:limit], start=1)
    ]
    if not result:
        fallback = True
    model_version = (
        model.model_version if model is not None and experiment == "treatment" else "popular-v1"
    )
    RECOMMENDATIONS.labels(model_version, str(fallback).lower()).inc()
    return RecommendationResponse(
        user_id=user_id,
        model_version=model_version,
        experiment=experiment,
        recommendations=result,
        fallback=fallback,
        candidate_count=len(candidates),
        request_id=request_id,
    )


@app.post("/events", response_model=EventAcceptedResponse, status_code=202)
def ingest_event(event: UserEvent) -> EventAcceptedResponse:
    if any(existing.event_id == event.event_id for existing in events):
        return EventAcceptedResponse(
            event_id=event.event_id, accepted=True, topic=settings.kafka_events_topic
        )
    events.append(event)
    feature_store.update(event)
    EVENTS.labels(event.event_type.value).inc()
    _append_raw_event(event)
    return EventAcceptedResponse(
        event_id=event.event_id, accepted=True, topic=settings.kafka_events_topic
    )


def _events_frame() -> pd.DataFrame:
    if not events:
        path = DATA_DIR / "interactions.parquet"
        if path.exists():
            return pd.read_parquet(path)
        return pd.DataFrame(columns=["item_id", "event_type", "timestamp", "user_id"])
    return pd.DataFrame([event.model_dump(mode="json") for event in events])


def _inference_features(
    user: pd.Series, item: pd.Series, user_id: str, item_id: str, as_of: datetime
) -> dict[str, float]:
    online_user = feature_store.get_user(user_id)
    online_item = feature_store.get_item(item_id)
    pair = feature_store.get_user_item(user_id, item_id)
    return {
        "user_click_count_1h": online_user.get("user_click_count", 0),
        "user_view_count_1h": online_user.get("user_view_count", 0),
        "user_purchase_count_24h": online_user.get("user_purchase_count_24h", 0),
        "user_cart_count_24h": online_user.get("user_add_to_cart_count", 0),
        "user_activity": online_user.get("user_engagement", 0),
        "user_engagement": online_user.get("user_engagement", 0),
        "item_views_1h": online_item.get("item_view_count", 0),
        "item_clicks_1h": online_item.get("item_click_count", 0),
        "item_purchases_1h": online_item.get("item_purchase_count", 0),
        "item_ctr_1h": online_item.get("item_click_count", 0)
        / max(online_item.get("item_view_count", 0), 1),
        "item_popularity_24h": online_item.get("item_weighted_popularity", item.popularity_score),
        "age": float(user.age),
        "price": float(item.price),
        "rating": float(item.rating),
        "item_popularity_score": float(item.popularity_score),
        "same_category": float(user.preferred_category == item.category),
        "hour": float(as_of.hour),
        "device_mobile": 1.0,
        "user_item_views": pair.get("user_item_view_count", 0),
        "user_item_clicks": pair.get("user_item_click_count", 0),
        "user_item_purchase_count": pair.get("user_item_purchase_count", 0),
        "user_item_interactions": sum(
            value for key, value in pair.items() if key.endswith("_count")
        ),
    }


def _append_raw_event(event: UserEvent) -> None:
    path = DATA_DIR / "raw" / f"events_{datetime.now(UTC).date().isoformat()}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event.model_dump(mode="json")) + "\n")


def run() -> None:
    import uvicorn

    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
