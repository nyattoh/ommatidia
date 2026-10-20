"""Regressions for review threads r4293701753 and r4296529355; synthetic records only."""

from dataclasses import replace

import pytest

from ommatidia.harness import TrialRecord
from ommatidia.ingestion import ingest_final_judgement
from ommatidia.scoring import score_saved_trial
from ommatidia.state import create_initial_state
from ommatidia.types import ConditionType
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
