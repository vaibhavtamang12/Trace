from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EventType(StrEnum):
    IMPRESSION = "impression"
    VIEW = "view"
    CLICK = "click"
    ADD_TO_CART = "add_to_cart"
    PURCHASE = "purchase"
    WISHLIST = "wishlist"
    SKIP = "skip"


EVENT_WEIGHTS: dict[EventType, float] = {
    EventType.IMPRESSION: 0.01,
    EventType.VIEW: 0.05,
    EventType.CLICK: 0.20,
    EventType.WISHLIST: 0.35,
    EventType.ADD_TO_CART: 0.60,
    EventType.PURCHASE: 1.00,
    EventType.SKIP: -0.10,
}


class User(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(pattern=r"^user_[0-9]+$")
    age: int = Field(ge=13, le=100)
    country: str = Field(min_length=2, max_length=2)
    device_type: str = Field(pattern=r"^(mobile|desktop|tablet)$")
    signup_date: datetime
    preferred_category: str
    activity_level: float = Field(ge=0, le=1)
    price_sensitivity: float = Field(ge=0, le=1)


class Item(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(pattern=r"^item_[0-9]+$")
    category: str
    subcategory: str
    price: float = Field(gt=0)
    brand: str
    rating: float = Field(ge=1, le=5)
    popularity_score: float = Field(ge=0)
    created_at: datetime


class UserEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=8)
    event_type: EventType
    user_id: str
    item_id: str
    timestamp: datetime
    session_id: str
    device_type: str = Field(pattern=r"^(mobile|desktop|tablet)$")
    position: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return value


class Recommendation(BaseModel):
    item_id: str
    score: float
    rank: int
    reason: str = "personalized"


class RecommendationResponse(BaseModel):
    user_id: str
    model_version: str
    experiment: str
    recommendations: list[Recommendation]
    fallback: bool = False
    candidate_count: int
    request_id: str


class EventAcceptedResponse(BaseModel):
    event_id: str
    accepted: bool
    topic: str


class ModelMetadata(BaseModel):
    model_name: str
    model_version: str
    feature_version: str
    dataset_version: str
    git_commit: str
    metrics: dict[str, float]
    trained_at: datetime
