from fastapi.testclient import TestClient

from src.api.app import app


def valid_payload():
    return {
        "date": "2025-01-15",
        "forecast_j_1": 55000.0,
        "forecast_j": 55200.0,
        "lag_1d": 54800.0,
        "lag_7d": 56000.0,
        "lag_14d": 55800.0,
        "rolling_mean_7d": 55200.0,
        "rolling_mean_30d": 55500.0,
        "fioul": 100.0,
        "coal": 50.0,
        "gas": 3000.0,
        "nuclear": 40000.0,
        "wind": 5000.0,
        "solar": 1000.0,
        "hydraulic": 8000.0,
        "pumping": -1000.0,
        "bioenergy": 1000.0,
        "physical_exchanges": 0.0,
        "co2_rate": 30.0,
    }


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_model_info_comes_from_real_training_metadata():
    with TestClient(app) as client:
        response = client.get("/api/model-info")
        assert response.status_code == 200
        body = response.json()
        assert "RTE Eco2mix" in body["data_source"]
        assert body["best_model"] == "RandomForest"
        assert body["raw_rows_after_cleaning"] > 100000


def test_create_and_read_prediction():
    with TestClient(app) as client:
        created = client.post("/api/predictions", json=valid_payload())
        assert created.status_code == 201
        body = created.json()
        assert body["prediction_mw"] > 0
        assert body["model_used"]
        assert body["forecast_j"] == 55200.0

        fetched = client.get(f"/api/predictions/{body['id']}")
        assert fetched.status_code == 200
        assert fetched.json()["id"] == body["id"]


def test_prediction_is_persisted_in_history():
    with TestClient(app) as client:
        created = client.post("/api/predictions", json=valid_payload())
        assert created.status_code == 201

        history = client.get("/api/predictions?limit=10")
        assert history.status_code == 200
        assert any(item["id"] == created.json()["id"] for item in history.json())


def test_validation_rejects_negative_forecast():
    payload = valid_payload()
    payload["forecast_j"] = -1
    with TestClient(app) as client:
        response = client.post("/api/predictions", json=payload)
        assert response.status_code == 422


def test_unknown_prediction_returns_404():
    with TestClient(app) as client:
        response = client.get("/api/predictions/999999")
        assert response.status_code == 404
