from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def valid_payload() -> dict:
    return {
        "application": {
            "monthly_income": 3_800_000,
            "debt_ratio": 0.32,
            "employment_months": 36,
            "requested_amount": 8_000_000,
            "credit_history_months": 48,
            "late_payments_12m": 0,
            "current_obligations": 1_200_000,
            "savings_balance": 2_500_000,
            "external_risk_score": 72,
            "employment_type": "salaried",
            "housing_type": "rent",
        },
        "thresholds": {"review_min": 40, "approval_min": 70},
    }


def test_health_and_model_card() -> None:
    health = client.get("/health")
    card = client.get("/api/model-card")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert card.status_code == 200
    assert card.json()["metadata"]["dataset"] == "Synthetic FinanCali baseline"


def test_score_contract() -> None:
    response = client.post("/api/score", json=valid_payload())

    assert response.status_code == 200
    body = response.json()
    assert 0 <= body["score"] <= 100
    assert body["decision"] in {"reject", "review", "approve"}
    assert body["model_version"]


def test_invalid_input_is_rejected_and_counted() -> None:
    before = client.get("/api/metrics").json()["operations"]["invalid_requests"]
    payload = valid_payload()
    payload["application"]["debt_ratio"] = 1.5

    response = client.post("/api/score", json=payload)
    after = client.get("/api/metrics").json()["operations"]["invalid_requests"]

    assert response.status_code == 422
    assert after == before + 1


def test_threshold_order_is_validated() -> None:
    payload = valid_payload()
    payload["thresholds"] = {"review_min": 80, "approval_min": 70}

    response = client.post("/api/score", json=payload)

    assert response.status_code == 422
