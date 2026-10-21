from __future__ import annotations

import hashlib
import io
import threading
from dataclasses import dataclass
from datetime import UTC, datetime

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from app.schemas import CreditApplication, DecisionThresholds

RANDOM_SEED = 2026
DATASET_SIZE = 4_000

NUMERIC_FEATURES = [
    "monthly_income",
    "debt_ratio",
    "employment_months",
    "requested_amount",
    "credit_history_months",
    "late_payments_12m",
    "current_obligations",
    "savings_balance",
    "external_risk_score",
]
CATEGORICAL_FEATURES = ["employment_type", "housing_type"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES

FEATURE_LABELS = {
    "monthly_income": "Ingreso mensual",
    "debt_ratio": "Relación deuda/ingreso",
    "employment_months": "Antigüedad laboral",
    "requested_amount": "Monto solicitado",
    "credit_history_months": "Historia crediticia",
    "late_payments_12m": "Moras en 12 meses",
    "current_obligations": "Obligaciones actuales",
    "savings_balance": "Saldo de ahorros",
    "external_risk_score": "Indicador externo",
}


def generate_synthetic_credit_data(
    size: int = DATASET_SIZE, seed: int = RANDOM_SEED
) -> tuple[pd.DataFrame, pd.Series]:
    """Create a deterministic dataset with credit-like relationships.

    It is intentionally synthetic: it supports security and observability exercises,
    not conclusions about Colombian applicants or real underwriting.
    """

    rng = np.random.default_rng(seed)
    income = np.clip(rng.lognormal(np.log(3_800_000), 0.58, size), 650_000, 35_000_000)
    debt_ratio = np.clip(rng.beta(2.2, 4.3, size), 0.01, 0.98)
    employment_months = np.clip(rng.gamma(2.1, 27, size), 0, 480).round()
    requested_amount = np.clip(
        income * rng.lognormal(np.log(2.1), 0.72, size), 200_000, 80_000_000
    )
    credit_history_months = np.clip(rng.gamma(2.0, 34, size), 0, 480).round()
    late_lambda = 0.2 + debt_ratio * 1.7
    late_payments = np.clip(rng.poisson(late_lambda), 0, 12)
    current_obligations = np.clip(
        income * debt_ratio * rng.uniform(0.65, 1.35, size), 0, 45_000_000
    )
    savings = np.clip(
        income * rng.lognormal(np.log(0.55), 1.0, size), 0, 150_000_000
    )
    external_score = np.clip(
        68
        - debt_ratio * 30
        - late_payments * 5
        + np.log1p(credit_history_months) * 4
        + rng.normal(0, 9, size),
        0,
        100,
    ).round()
    employment_type = rng.choice(
        ["salaried", "independent", "business_owner", "other"],
        p=[0.57, 0.25, 0.12, 0.06],
        size=size,
    )
    housing_type = rng.choice(["own", "rent", "family"], p=[0.33, 0.45, 0.22], size=size)

    data = pd.DataFrame(
        {
            "monthly_income": income.round().astype(int),
            "debt_ratio": debt_ratio.round(4),
            "employment_months": employment_months.astype(int),
            "requested_amount": requested_amount.round().astype(int),
            "credit_history_months": credit_history_months.astype(int),
            "late_payments_12m": late_payments.astype(int),
            "current_obligations": current_obligations.round().astype(int),
            "savings_balance": savings.round().astype(int),
            "external_risk_score": external_score.astype(int),
            "employment_type": employment_type,
            "housing_type": housing_type,
        }
    )

    amount_to_income = data["requested_amount"] / data["monthly_income"]
    savings_to_income = data["savings_balance"] / data["monthly_income"]
    logit = (
        -0.8
        + (data["external_risk_score"] - 50) * 0.055
        - data["debt_ratio"] * 2.1
        - data["late_payments_12m"] * 0.38
        - np.clip(amount_to_income - 2, 0, None) * 0.16
        + np.log1p(data["credit_history_months"]) * 0.18
        + np.clip(savings_to_income, 0, 4) * 0.13
        + (data["employment_months"] >= 24) * 0.22
        + (data["employment_type"] == "salaried") * 0.12
        + rng.normal(0, 0.45, size)
    )
    probability_good = 1 / (1 + np.exp(-logit))
    target = pd.Series(
        rng.binomial(1, probability_good), name="good_outcome", dtype=int
    )
    return data, target


@dataclass
class ModelBundle:
    pipeline: Pipeline
    metrics: dict
    metadata: dict


def train_baseline_model() -> ModelBundle:
    x, y = generate_synthetic_credit_data()
    dataset_bytes = pd.concat([x, y], axis=1).to_csv(index=False).encode()
    dataset_hash = hashlib.sha256(dataset_bytes).hexdigest()

    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.25, random_state=RANDOM_SEED, stratify=y
    )
    processor = ColumnTransformer(
        [
            ("numeric", "passthrough", NUMERIC_FEATURES),
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
        ]
    )
    pipeline = Pipeline(
        [
            ("preprocess", processor),
            (
                "classifier",
                GradientBoostingClassifier(
                    n_estimators=120,
                    learning_rate=0.055,
                    max_depth=2,
                    random_state=RANDOM_SEED,
                ),
            ),
        ]
    )
    pipeline.fit(x_train, y_train)

    probability = pipeline.predict_proba(x_test)[:, 1]
    prediction = (probability >= 0.5).astype(int)
    score = np.rint(probability * 100).astype(int)
    matrix = confusion_matrix(y_test, prediction).tolist()

    artifact = io.BytesIO()
    joblib.dump(pipeline, artifact)
    model_hash = hashlib.sha256(artifact.getvalue()).hexdigest()
    version = f"gb-{model_hash[:10]}"

    metrics = {
        "roc_auc": round(float(roc_auc_score(y_test, probability)), 3),
        "accuracy": round(float(accuracy_score(y_test, prediction)), 3),
        "precision": round(float(precision_score(y_test, prediction)), 3),
        "recall": round(float(recall_score(y_test, prediction)), 3),
        "f1": round(float(f1_score(y_test, prediction)), 3),
        "brier_score": round(float(brier_score_loss(y_test, probability)), 3),
        "confusion_matrix": {
            "true_negative": matrix[0][0],
            "false_positive": matrix[0][1],
            "false_negative": matrix[1][0],
            "true_positive": matrix[1][1],
        },
        "decision_distribution": {
            "reject": round(float(np.mean(score < 40)), 3),
            "review": round(float(np.mean((score >= 40) & (score < 70))), 3),
            "approve": round(float(np.mean(score >= 70)), 3),
        },
        "test_records": len(x_test),
        "positive_rate": round(float(y_test.mean()), 3),
    }
    metadata = {
        "model_version": version,
        "algorithm": "GradientBoostingClassifier",
        "dataset": "Synthetic FinanCali baseline",
        "dataset_records": len(x),
        "dataset_hash": dataset_hash,
        "model_hash": model_hash,
        "random_seed": RANDOM_SEED,
        "trained_at": datetime.now(UTC).isoformat(),
        "features": FEATURES,
        "feature_labels": FEATURE_LABELS,
        "limitations": [
            "Datos sintéticos sin representación de la población colombiana.",
            "Umbrales académicos, no política de originación.",
            "Las sensibilidades locales no constituyen explicaciones causales.",
        ],
    }
    return ModelBundle(pipeline=pipeline, metrics=metrics, metadata=metadata)


class ScoringService:
    def __init__(self) -> None:
        self.bundle = train_baseline_model()
        self._lock = threading.Lock()
        self._requests = 0
        self._invalid_requests = 0
        self._decisions = {"reject": 0, "review": 0, "approve": 0}
        self._last_scored_at: str | None = None

    def register_invalid_request(self) -> None:
        with self._lock:
            self._invalid_requests += 1

    def operational_metrics(self) -> dict:
        with self._lock:
            return {
                "scoring_requests": self._requests,
                "invalid_requests": self._invalid_requests,
                "decisions": self._decisions.copy(),
                "last_scored_at": self._last_scored_at,
            }

    def predict_probability(self, values: dict) -> float:
        frame = pd.DataFrame([{feature: values[feature] for feature in FEATURES}])
        return float(self.bundle.pipeline.predict_proba(frame)[0, 1])

    def score(
        self, application: CreditApplication, thresholds: DecisionThresholds
    ) -> dict:
        values = application.model_dump(mode="json")
        probability = self.predict_probability(values)
        score = int(round(probability * 100))
        if score >= thresholds.approval_min:
            decision = "approve"
        elif score >= thresholds.review_min:
            decision = "review"
        else:
            decision = "reject"

        with self._lock:
            self._requests += 1
            self._decisions[decision] += 1
            self._last_scored_at = datetime.now(UTC).isoformat()

        return {
            "score": score,
            "probability_good": round(probability, 4),
            "decision": decision,
            "model_version": self.bundle.metadata["model_version"],
            "reason_codes": self._reason_codes(values),
            "sensitivity": self._local_sensitivity(values, probability),
            "disclaimer": (
                "Resultado académico sobre datos sintéticos. No usar para aprobar, "
                "rechazar ni ofrecer crédito real."
            ),
        }

    def _reason_codes(self, values: dict) -> list[str]:
        reasons: list[str] = []
        if values["external_risk_score"] < 55:
            reasons.append("Indicador externo por debajo de la referencia")
        if values["debt_ratio"] > 0.5:
            reasons.append("Relación deuda/ingreso elevada")
        if values["late_payments_12m"] > 1:
            reasons.append("Moras recientes registradas")
        if values["requested_amount"] / values["monthly_income"] > 4:
            reasons.append("Monto solicitado alto frente al ingreso")
        if values["credit_history_months"] < 12:
            reasons.append("Historia crediticia limitada")
        if not reasons:
            reasons.append("Sin alertas simples en las reglas de referencia")
        return reasons[:3]

    def _local_sensitivity(self, values: dict, baseline: float) -> list[dict]:
        scenarios = {
            "external_risk_score": min(values["external_risk_score"] + 5, 100),
            "debt_ratio": max(values["debt_ratio"] - 0.05, 0),
            "monthly_income": min(round(values["monthly_income"] * 1.1), 50_000_000),
            "requested_amount": max(round(values["requested_amount"] * 0.9), 200_000),
            "late_payments_12m": max(values["late_payments_12m"] - 1, 0),
            "savings_balance": min(
                round(values["savings_balance"] * 1.1 + 100_000), 200_000_000
            ),
        }
        impacts = []
        for feature, favorable_value in scenarios.items():
            changed = values.copy()
            changed[feature] = favorable_value
            effect = (self.predict_probability(changed) - baseline) * 100
            impacts.append(
                {
                    "feature": FEATURE_LABELS[feature],
                    "effect_points": round(float(effect), 2),
                    "direction": "escenario favorable de referencia",
                }
            )
        return sorted(impacts, key=lambda item: abs(item["effect_points"]), reverse=True)[
            :4
        ]


service = ScoringService()
