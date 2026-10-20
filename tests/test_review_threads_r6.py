"""Regressions for review threads r4293701753 and r4296529355; synthetic records only."""

from dataclasses import replace

import pytest

from ommatidia.harness import TrialRecord
from ommatidia.ingestion import ingest_final_judgement
from ommatidia.scoring import analyse_saved_trials, score_saved_trial
from ommatidia.state import create_initial_state
from ommatidia.types import ConditionType, Usage
from tests.fixtures.synthetic_dev_cases import get_mechanism_check_fixtures

TASK = get_mechanism_check_fixtures()[0][0]
RUBRIC = {
    "taskId": TASK.task_id,
    "targetVerdict": "inconclusive",
    "criticalEvidenceHashes": ["a" * 64],
}


def saved_trial(condition):
    return TrialRecord(
        task_id=TASK.task_id,
        condition=condition,
        run_id="synthetic_final_only",
        final_state=create_initial_state(TASK).to_dict(),
        final_judgement=ingest_final_judgement(
            {
                "taskId": TASK.task_id,
                "verdict": "inconclusive",
                "confidenceScore": 0.0,
                "justification": "Synthetic final-only answer.",
                "citedEvidence": [],
                "unresolvedGaps": [],
                "resourceUsage": {
                    "modelCalls": 1,
                    "toolCalls": 0,
                    "elapsedMs": 1,
                    "inputCharsEstimated": 0,
                },
            }
        ),
        usage_known=True,
        wall_elapsed_ms=1000.0,
    )


RETRIEVAL = ("recallCrit", "dsc", "efficiencyTool", "efficiencyTime")


@pytest.mark.parametrize("condition", [ConditionType.A, ConditionType.B])
def test_final_only_retrieval_metrics_are_unavailable_not_zero(condition):
    # r4293701753: A/B return only a final answer, so retrieval cannot be verified.
    record = saved_trial(condition)
    record.usage.tool_calls = 1
    metrics = score_saved_trial(record, RUBRIC, ("fda",) + RETRIEVAL)
    assert metrics["fda"] == 1
    assert all(metrics[name] is None for name in RETRIEVAL)
    assert set(metrics["unavailableMetrics"]) == set(RETRIEVAL)


def test_observing_conditions_still_score_retrieval():
    record = saved_trial(ConditionType.C)
    metrics = score_saved_trial(record, RUBRIC, ("recallCrit", "dsc"))
    assert (metrics["recallCrit"], metrics["dsc"]) == (0.0, 0)
    assert "unavailableMetrics" not in metrics


METRICS = {"fda": 1, "dsc": 1, "far": 0.0, "recallCrit": 1.0}


def resource_matrix():
    from tests.test_scoring_task_hash_provenance import synthetic_matrix

    records = []
    for record in synthetic_matrix():
        primary = record.condition == ConditionType.E
        record = replace(record, metrics=dict(METRICS), usage_known=True)
        record.usage = Usage(
            model_calls=6 if primary else 2,
            tool_calls=9 if primary else 3,
            elapsed_ms=9999.0,  # summed step time; concurrent E roles overlap
            input_chars=4000 if primary else 1000,
        )
        record.wall_elapsed_ms = 3000.0 if primary else 1000.0
        records.append(record)
    return records


def test_paired_analysis_reports_descriptive_resource_differences():
    # r4296529355: every comparison carries the protocol section 6.2 host units, E minus baseline.
    from tests.test_scoring_task_hash_provenance import TASK_IDS

    report = analyse_saved_trials(resource_matrix(), TASK_IDS, TASK_IDS[:12])
    assert report["familySize"] == 4 and len(report["hypotheses"]) == 4
    comparisons = {item["baseline"]: item for item in report["resourceComparisons"]}
    assert set(comparisons) == {"B", "C", "D"}
    for item in comparisons.values():
        assert (item["primary"], item["sampleSize"], item["descriptiveOnly"]) == ("E", 24, True)
        assert item["units"] == {
            "elapsedMs": {"available": True, "primaryMean": 3000.0, "baselineMean": 1000.0, "meanDifference": 2000.0},
            "modelCalls": {"available": True, "primaryMean": 6.0, "baselineMean": 2.0, "meanDifference": 4.0},
            "toolCalls": {"available": True, "primaryMean": 9.0, "baselineMean": 3.0, "meanDifference": 6.0},
            "inputChars": {"available": True, "primaryMean": 4000.0, "baselineMean": 1000.0, "meanDifference": 3000.0},
        }


def test_unknown_usage_marks_resource_units_unavailable_without_failing():
    from tests.test_scoring_task_hash_provenance import TASK_IDS

    records = resource_matrix()
    index = next(i for i, r in enumerate(records) if r.condition == ConditionType.D)
    records[index] = replace(records[index], usage_known=False)
    report = analyse_saved_trials(records, TASK_IDS, TASK_IDS[:12])
    comparisons = {item["baseline"]: item for item in report["resourceComparisons"]}
    assert all(not unit["available"] for unit in comparisons["D"]["units"].values())
    assert all("usage_known" in unit["reason"] for unit in comparisons["D"]["units"].values())
    assert all(unit["available"] for unit in comparisons["C"]["units"].values())
    assert len(report["hypotheses"]) == 4


def test_resource_time_uses_wall_clock_and_marks_missing_wall_time_unavailable():
    # Bugbot r4324341611: protocol section 6.2 elapsed time is wall-clock, not summed step time.
    from tests.test_scoring_task_hash_provenance import TASK_IDS

    records = resource_matrix()
    index = next(i for i, r in enumerate(records) if r.condition == ConditionType.C)
    records[index] = replace(records[index], wall_elapsed_ms=None)
    report = analyse_saved_trials(records, TASK_IDS, TASK_IDS[:12])
    comparisons = {item["baseline"]: item for item in report["resourceComparisons"]}
    assert comparisons["D"]["units"]["elapsedMs"]["meanDifference"] == 2000.0
    assert comparisons["C"]["units"]["elapsedMs"]["available"] is False
    assert "wall" in comparisons["C"]["units"]["elapsedMs"]["reason"]
    assert comparisons["C"]["units"]["modelCalls"]["available"] is True
