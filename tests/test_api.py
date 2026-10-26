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


def defended_payload() -> dict:
    vulnerable = valid_payload()["application"]
    return {
        "applicant": {
            key: vulnerable[key]
            for key in (
                "monthly_income",
                "employment_months",
                "requested_amount",
                "current_obligations",
                "savings_balance",
                "employment_type",
                "housing_type",
            )
        },
        "trusted_profile_id": "stable",
    }


def test_health_and_model_card() -> None:
    health = client.get("/health")
    card = client.get("/api/model-card")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert card.status_code == 200
    assert card.json()["metadata"]["dataset"] == "Synthetic FinanCali baseline"


def test_score_contract() -> None:
    response = client.post("/api/score", json=defended_payload())

    assert response.status_code == 200
    body = response.json()
    assert 0 <= body["score"] <= 100
    assert body["decision"] in {"reject", "review", "approve"}
    assert body["model_version"]


def test_invalid_input_is_rejected_and_counted() -> None:
    before = client.get("/api/metrics").json()["operations"]["invalid_requests"]
    payload = defended_payload()
    payload["applicant"]["external_risk_score"] = 100

    response = client.post("/api/score", json=payload)
    after = client.get("/api/metrics").json()["operations"]["invalid_requests"]

    assert response.status_code == 422
    assert after == before + 1


def test_threshold_order_is_validated() -> None:
    payload = valid_payload()
    payload["thresholds"] = {"review_min": 80, "approval_min": 70}

    response = client.post("/api/lab/vulnerable-score", json=payload)

    assert response.status_code == 422


def test_vulnerable_lab_accepts_client_controlled_trusted_fields() -> None:
    response = client.post("/api/lab/vulnerable-score", json=valid_payload())

    assert response.status_code == 200


def test_defended_route_records_forbidden_field_event() -> None:
    before = client.get("/api/metrics").json()["operations"]["blocked_manipulations"]
    payload = defended_payload()
    payload["applicant"]["late_payments_12m"] = 0

    response = client.post("/api/score", json=payload)
    metrics = client.get("/api/metrics").json()["operations"]
    events = client.get("/api/security-events").json()["events"]

    assert response.status_code == 422
    assert metrics["blocked_manipulations"] == before + 1
    assert events[-1]["event"] == "blocked_input_manipulation"


def test_vulnerable_trusted_field_manipulation_increases_score() -> None:
    baseline = valid_payload()
    attacked = valid_payload()
    attacked["application"]["external_risk_score"] = 100
    attacked["application"]["late_payments_12m"] = 0
    attacked["application"]["credit_history_months"] = 240
    attacked["application"]["debt_ratio"] = 0.05

    baseline_body = client.post("/api/lab/vulnerable-score", json=baseline).json()
    attacked_body = client.post("/api/lab/vulnerable-score", json=attacked).json()

    assert attacked_body["score"] > baseline_body["score"]


def test_valid_defended_request_does_not_accept_client_debt_ratio() -> None:
    payload = defended_payload()
    payload["applicant"]["debt_ratio"] = 0.01

    response = client.post("/api/score", json=payload)

    assert response.status_code == 422
