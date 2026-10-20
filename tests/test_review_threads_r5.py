"""Regressions for open PR #1 review threads; synthetic executors and records only."""

from dataclasses import replace
import hashlib

import pytest

from ommatidia.runtime import execute_graph
from ommatidia.types import ConditionType, Decision, Usage
from tests.fixtures.synthetic_dev_cases import get_mechanism_check_fixtures

GAP = {
    "id": "gap_required",
    "kind": "missing_fact",
    "lensId": "lens_synthetic",
    "question": "Synthetic required question",
    "triggerRefs": ["synthetic_trigger"],
    "whyItMatters": "Synthetic",
    "importance": "required",
}
PROBE = {
    "id": "probe_required",
    "gapIds": ["gap_required"],
    "method": "boundary",
    "question": "Synthetic probe question",
    "requiredCapability": "document_read",
    "sourceGroups": ["public_source"],
    "successCondition": "found",
    "refutationCondition": "refuted",
    "inconclusiveCondition": "unavailable",
}
PASSAGE = "Synthetic public passage observed by the probe."
EVIDENCE = {
    "id": "ev_synthetic",
    "kind": "document",
    "locator": "public/synthetic_source.txt",
    "sourceGroup": "public_source",
    "retrievedAt": "2026-01-01T00:00:00Z",
    "version": "1",
    "scope": "synthetic",
    "passage": PASSAGE,
    "contentHash": hashlib.sha256(PASSAGE.encode()).hexdigest(),
    "validity": "current",
}
RESOLUTION = {
    "gapId": "gap_required",
    "reason": "supported",
    "evidenceIds": ["ev_synthetic"],
    "explanation": "Synthetic resolution after observing the probe",
}


def final(task_id):
    return {
        "taskId": task_id,
        "verdict": "inconclusive",
        "confidenceScore": 0.0,
        "justification": "Synthetic mechanism output.",
        "citedEvidence": [],
        "unresolvedGaps": [],
        "resourceUsage": {
            "modelCalls": 1,
            "toolCalls": 0,
            "elapsedMs": 1,
            "inputCharsEstimated": 0,
        },
    }


def run(condition, plans, yen_per_call=0.0, observation_cost=None, max_cost_yen=None):
    """Run the graph against a host meter that charges every dispatched step."""
    task = get_mechanism_check_fixtures()[0][0]
    task = replace(task, budget=replace(task.budget, max_cost_yen=max_cost_yen))
    calls = []

    def meter():
        return Usage(
            model_calls=len(calls),
            elapsed_ms=float(len(calls)),
            cost_yen=yen_per_call * len(calls),
            total_tokens=0,
        )

    def executor(step, payload):
        calls.append((step, payload))
        kind = payload["responseSchema"]["required"][0]
        if kind == "proposal":
            planned = sum(1 for _, p in calls if "proposal" in p["responseSchema"]["required"])
            body = {"claims": [], "lenses": [], "gaps": [], "probes": []}
            body.update(plans[min(planned, len(plans)) - 1])
            return {"proposal": body}
        if kind == "observations":
            observation = {
                "executionId": payload["clientRequestId"],
                "probeId": payload["context"]["probe"]["id"],
                "outcome": "completed",
                "evidence": [EVIDENCE],
                "toolCalls": 0,
                "elapsedMs": 0,
            }
            if observation_cost is not None:
                observation["costYen"] = observation_cost
            return {"observations": [observation]}
        return final(payload["taskId"])

    state, invalid = execute_graph(task, condition, "review-threads", executor, meter)
    assert invalid == []
    return state, calls


ADAPTIVE = [ConditionType.D, ConditionType.E]


@pytest.mark.parametrize("condition", ADAPTIVE)
def test_coordinator_updates_state_after_investigators_finish(condition):
    # r4293701747: probe exhaustion must not end the loop before a planning pass sees the result.
    state, calls = run(
        condition,
        [{"gaps": [GAP], "probes": [PROBE]}, {"resolutions": [RESOLUTION]}],
    )
    planning = [p for _, p in calls if "proposal" in p["responseSchema"]["required"]]
    assert len(planning) == 2
    assert planning[1]["context"]["state"]["probes"][0]["status"] == "complete"
    assert state.gaps[0].status.value == "resolved"
    assert (state.stop_reason, state.decision) == (
        "required_gaps_resolved",
        Decision.READY_FOR_REQUESTED_STEP,
    )


@pytest.mark.parametrize("condition", ADAPTIVE)
def test_unresolved_probe_exhaustion_stays_blocked_after_synthesis(condition):
    # r4293701771: a valid synthesis must not overwrite the blocking stop decision.
    state, calls = run(condition, [{"gaps": [GAP], "probes": [PROBE]}, {}])
    assert "synthesis" in calls[-1][0]
    assert (state.stop_reason, state.decision) == (
        "probes_exhausted_unresolved_gaps",
        Decision.BLOCKED,
    )


@pytest.mark.parametrize("condition", ADAPTIVE)
def test_budget_exhaustion_stays_blocked_after_synthesis(condition):
    # r4293701771: budget_exhausted keeps Decision.BLOCKED through synthesis.
    state, calls = run(
        condition,
        [{"gaps": [GAP], "probes": [PROBE]}],
        yen_per_call=4.0,
        max_cost_yen=5.0,
    )
    assert "synthesis" in calls[-1][0]
    assert (state.stop_reason, state.decision) == ("budget_exhausted", Decision.BLOCKED)
