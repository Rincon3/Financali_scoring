from app.model import FEATURES, ScoringService, generate_synthetic_credit_data
from app.schemas import CreditApplication, DecisionThresholds


def test_synthetic_data_is_reproducible() -> None:
    first_x, first_y = generate_synthetic_credit_data(size=50, seed=7)
    second_x, second_y = generate_synthetic_credit_data(size=50, seed=7)

    assert list(first_x.columns) == FEATURES
    assert first_x.equals(second_x)
    assert first_y.equals(second_y)


def test_model_exposes_expected_baseline_metrics() -> None:
    service = ScoringService()

    assert 0.5 <= service.bundle.metrics["roc_auc"] <= 1
    assert service.bundle.metrics["test_records"] == 1_000
    assert len(service.bundle.metadata["dataset_hash"]) == 64
    assert service.bundle.metadata["model_version"].startswith("gb-")


def test_scoring_returns_bounded_result_and_evidence() -> None:
    service = ScoringService()
    result = service.score(CreditApplication(), DecisionThresholds())

    assert 0 <= result["score"] <= 100
    assert result["decision"] in {"reject", "review", "approve"}
    assert result["reason_codes"]
    assert len(result["sensitivity"]) == 4
    assert service.operational_metrics()["scoring_requests"] == 1
