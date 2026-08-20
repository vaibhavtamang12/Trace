from fastapi.testclient import TestClient

from recommendation_platform.api.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_shape() -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    assert "ready" in response.json()


def test_unknown_user_is_404_when_catalog_exists() -> None:
    response = client.get("/recommendations/user_999999")
    assert response.status_code in {404, 503}


def test_event_validation() -> None:
    response = client.post("/events", json={"event_type": "click"})
    assert response.status_code == 422
