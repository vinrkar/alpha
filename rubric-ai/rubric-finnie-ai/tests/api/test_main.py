# tests/api/test_main.py

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)

def test_health_check() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "Rubric AI Financial Assistant API"}

def test_get_all_user_profiles() -> None:
    response = client.get("/api/v1/profiles")
    assert response.status_code == 200
    profiles = response.json()
    assert isinstance(profiles, dict)
    assert len(profiles) > 0

def test_get_single_profile_not_found() -> None:
    response = client.get("/api/v1/profiles/NONEXISTENT_ID")
    assert response.status_code == 404
    assert response.json()["detail"] == "Profile not found"

def test_post_mock_trade_invalid_boundary() -> None:
    payload = {
        "user_id": "C4820198",
        "ticker": "AAPL",
        "action": "BUY",
        "shares": 10.0,
        "execution_price": 99999.0,
    }
    response = client.post("/api/v1/trade", json=payload)
    assert response.status_code in [400, 500]