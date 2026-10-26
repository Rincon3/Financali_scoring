"""Ejercicio púrpura reproducible contra modificación manual de entradas.

La ruta ``/api/lab/vulnerable-score`` conserva deliberadamente el contrato
inseguro. ``/api/score`` representa el control posterior. No usa datos reales.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
from evidently import Report
from evidently.presets import DataDriftPreset
from fastapi.testclient import TestClient

from app.main import app
from app.model import service

EVIDENCE = Path(__file__).resolve().parent / "evidence"
THRESHOLDS = {"review_min": 40, "approval_min": 70}
TRUSTED_FIELDS = (
    "external_risk_score",
    "late_payments_12m",
    "credit_history_months",
    "debt_ratio",
)


def decision(score: int) -> str:
    if score >= THRESHOLDS["approval_min"]:
        return "approve"
    if score >= THRESHOLDS["review_min"]:
        return "review"
    return "reject"


def frame_value(value):
    return value.item() if hasattr(value, "item") else value


def vulnerable_payload(row: pd.Series) -> dict:
    return {
        "application": {key: frame_value(value) for key, value in row.items()},
        "thresholds": THRESHOLDS,
    }


def defended_payload(row: pd.Series, include_forbidden: bool = False) -> dict:
    applicant_fields = (
        "monthly_income",
        "employment_months",
        "requested_amount",
        "current_obligations",
        "savings_balance",
        "employment_type",
        "housing_type",
    )
    applicant = {key: frame_value(row[key]) for key in applicant_fields}
    if include_forbidden:
        applicant.update({key: frame_value(row[key]) for key in TRUSTED_FIELDS})
    return {"applicant": applicant, "trusted_profile_id": "stable"}


def select_cases(limit: int = 24) -> pd.DataFrame:
    # Regenerate the exact deterministic dataset used by the baseline model.
    from app.model import generate_synthetic_credit_data

    data, _ = generate_synthetic_credit_data()
    probabilities = service.bundle.pipeline.predict_proba(data)[:, 1]
    data = data.copy()
    data["_score"] = (probabilities * 100).round().astype(int)
    near = data[data["_score"].between(25, 69)].copy()
    near["_distance"] = near["_score"].map(lambda x: min(abs(x - 40), abs(x - 70)))
    return near.sort_values(["_distance", "_score"]).head(limit).drop(columns="_distance")


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    client = TestClient(app)
    cases = select_cases()
    attempts: list[dict] = []
    baseline_rows: list[dict] = []
    adversarial_rows: list[dict] = []
    crossings = 0
    rejected_by_control = 0

    for case_number, (_, case) in enumerate(cases.iterrows(), start=1):
        original = case.drop(labels="_score")
        baseline_response = client.post(
            "/api/lab/vulnerable-score", json=vulnerable_payload(original)
        )
        baseline_response.raise_for_status()
        baseline = baseline_response.json()

        manipulated = original.copy()
        manipulated["external_risk_score"] = 100
        manipulated["late_payments_12m"] = 0
        manipulated["credit_history_months"] = max(
            int(manipulated["credit_history_months"]), 240
        )
        manipulated["debt_ratio"] = min(float(manipulated["debt_ratio"]), 0.05)

        attack_response = client.post(
            "/api/lab/vulnerable-score", json=vulnerable_payload(manipulated)
        )
        attack_response.raise_for_status()
        attacked = attack_response.json()
        crossed = baseline["decision"] != attacked["decision"]
        crossings += int(crossed)

        blocked_response = client.post(
            "/api/score", json=defended_payload(manipulated, include_forbidden=True)
        )
        rejected_by_control += int(blocked_response.status_code == 422)

        attempts.append(
            {
                "case_id": case_number,
                "baseline_score": baseline["score"],
                "baseline_decision": baseline["decision"],
                "attacked_score": attacked["score"],
                "attacked_decision": attacked["decision"],
                "score_delta": attacked["score"] - baseline["score"],
                "threshold_crossed": crossed,
                "vulnerable_http": attack_response.status_code,
                "defended_http": blocked_response.status_code,
                "control_result": (
                    "blocked" if blocked_response.status_code == 422 else "not_blocked"
                ),
            }
        )
        baseline_rows.append({key: frame_value(original[key]) for key in TRUSTED_FIELDS})
        adversarial_rows.append(
            {key: frame_value(manipulated[key]) for key in TRUSTED_FIELDS}
        )

    valid_control = client.post("/api/score", json=defended_payload(cases.iloc[0]))
    valid_control.raise_for_status()

    baseline_df = pd.DataFrame(baseline_rows)
    adversarial_df = pd.DataFrame(adversarial_rows)
    snapshot = Report([DataDriftPreset()], include_tests=True).run(
        current_data=adversarial_df,
        reference_data=baseline_df,
        name="FinanCali - modificación manual de entradas",
    )
    html_path = EVIDENCE / "evidently-report.html"
    html_path.write_text(snapshot.get_html_str(as_iframe=False), encoding="utf-8")
    (EVIDENCE / "evidently-report.json").write_text(
        snapshot.json(), encoding="utf-8"
    )

    with (EVIDENCE / "attack-attempts.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=attempts[0].keys())
        writer.writeheader()
        writer.writerows(attempts)

    score_deltas = [row["score_delta"] for row in attempts]
    summary = {
        "exercise": "AML.T0043.003 - Manual Modification",
        "atlas_maturity": "Realized",
        "cases": len(attempts),
        "vulnerable_route": "/api/lab/vulnerable-score",
        "defended_route": "/api/score",
        "threshold_crossings": crossings,
        "crossing_rate": round(crossings / len(attempts), 4),
        "defended_rejections": rejected_by_control,
        "defended_rejection_rate": round(rejected_by_control / len(attempts), 4),
        "valid_defended_request_http": valid_control.status_code,
        "score_delta": {
            "minimum": min(score_deltas),
            "maximum": max(score_deltas),
            "mean": round(sum(score_deltas) / len(score_deltas), 2),
        },
        "acceptance_criterion_met": (
            crossings > 0
            and rejected_by_control == len(attempts)
            and valid_control.status_code == 200
        ),
        "trusted_fields_blocked": list(TRUSTED_FIELDS),
        "tool": {
            "name": "Evidently",
            "version": "0.7.23",
            "purpose": "Comparar distribuciones de entradas base y manipuladas.",
        },
        "limitations": [
            "Datos, perfiles externos y ataques completamente sintéticos.",
            "El selector de perfil confiable no está ligado a una identidad real.",
            "La ruta vulnerable sólo debe existir en el laboratorio.",
            "El reporte de deriva detecta cambios; no atribuye intención maliciosa.",
        ],
    }
    (EVIDENCE / "evaluation-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
