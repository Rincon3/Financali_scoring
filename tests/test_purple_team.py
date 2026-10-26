import csv
import json
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parents[1] / "purple-team" / "evidence"


def test_purple_team_summary_meets_acceptance_criterion() -> None:
    summary = json.loads((EVIDENCE / "evaluation-summary.json").read_text(encoding="utf-8"))

    assert summary["exercise"].startswith("AML.T0043.003")
    assert summary["cases"] == 24
    assert summary["threshold_crossings"] == 24
    assert summary["defended_rejections"] == 24
    assert summary["valid_defended_request_http"] == 200
    assert summary["acceptance_criterion_met"] is True


def test_purple_team_attempts_match_summary() -> None:
    with (EVIDENCE / "attack-attempts.csv").open(encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    assert len(rows) == 24
    assert all(row["baseline_decision"] != row["attacked_decision"] for row in rows)
    assert all(row["control_result"] == "blocked" for row in rows)
    assert all(row["defended_http"] == "422" for row in rows)


def test_evidently_report_flags_all_trusted_fields() -> None:
    report = json.loads((EVIDENCE / "evidently-report.json").read_text(encoding="utf-8"))
    drifted = next(
        metric
        for metric in report["metrics"]
        if metric["metric_name"].startswith("DriftedColumnsCount")
    )

    assert drifted["value"]["count"] == 4.0
    assert drifted["value"]["share"] == 1.0
