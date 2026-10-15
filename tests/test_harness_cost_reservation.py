"""Per-call cost reservation through the single metered harness route; synthetic data only."""

import json
import threading

import pytest

from ommatidia.campaign import atomic_json
from ommatidia.harness import ResearchHarness
from ommatidia.integrity import fingerprints
from ommatidia.seal import create_seal_manifest
from ommatidia.types import ConditionType
from scripts.run_harness import dummy_synthetic_executor
from tests.fixtures.synthetic_dev_cases import get_mechanism_check_fixtures


@pytest.fixture
def setup(tmp_path):
    protocol = tmp_path / "protocol.md"
    protocol.write_text("Synthetic protocol", encoding="utf-8")
    manifest = tmp_path / "seal.json"
    create_seal_manifest(protocol, [], manifest)
    freeze = tmp_path / "freeze.json"
    atomic_json(freeze, {**fingerprints(), "baseCommit": "HEAD"})
    return tmp_path / "output", manifest, freeze, get_mechanism_check_fixtures()[0][0]


def harness(setup):
    output, manifest, freeze, _ = setup
    return ResearchHarness(
        output, seal_manifest_path=manifest, runtime_freeze_path=freeze
    )


def registry(output):
    return json.loads((output / "resource_registry.json").read_text(encoding="utf-8"))


def capped(cap, cost_yen=1.5, respond=dummy_synthetic_executor):
    calls = []

    def executor(step, payload):
        calls.append(payload["clientRequestId"])
        result = respond(step, payload)
        usage = {k: v for k, v in result["usage"].items() if k != "costYen"}
        if cost_yen is not None:
            usage["costYen"] = cost_yen
        result["usage"] = usage
        return result

    executor.enforced_cost_cap_yen = cap
    executor.calls = calls
    return executor


def test_executor_without_cost_cap_is_refused_before_any_call(setup):
    output, _, _, task = setup
    calls = []

    def uncapped(step, payload):
        calls.append(step)
        return dummy_synthetic_executor(step, payload)

    with pytest.raises(ValueError, match="enforced_cost_cap_yen"):
        harness(setup).run_cohort(
            [task], [ConditionType.A], "uncapped", uncapped, executor_name="paid_probe"
        )
    assert calls == []
    assert not (output / "dev/trials").exists()


@pytest.mark.parametrize("cap", [None, -1.0, float("nan"), float("inf"), True, "50"])
def test_invalid_cost_cap_is_refused_before_any_call(setup, cap):
    output, _, _, task = setup
    executor = capped(cap)
    with pytest.raises(ValueError, match="enforced_cost_cap_yen"):
        harness(setup).run_cohort(
            [task],
            [ConditionType.A],
            "invalid_cap",
            executor,
            executor_name="paid_probe",
        )
    assert executor.calls == []
    assert not (output / "dev/trials").exists()


def test_cap_beyond_campaign_ceiling_stops_before_dispatch(setup):
    output, _, _, task = setup
    executor = capped(600.0)
    record = harness(setup).run_cohort(
        [task], [ConditionType.A], "too_big", executor, executor_name="paid_probe"
    )[0]
    assert executor.calls == []
    assert record.status == "failed"
    assert record.error_message == "Campaign cost ceiling would be exceeded"
    assert registry(output)["calls"] == {}


def test_each_call_reserves_cap_before_dispatch_and_settles_actual_cost(setup):
    output, _, _, task = setup
    seen = []

    def respond(step, payload):
        call = registry(output)["calls"][payload["clientRequestId"]]
        seen.append(
            (
                call["status"],
                call["reservedCostYen"],
                call["settledCostYen"],
                registry(output)["committedCostYen"],
            )
        )
        return dummy_synthetic_executor(step, payload)

    executor = capped(50.0, cost_yen=1.5, respond=respond)
    record = harness(setup).run_cohort(
        [task], [ConditionType.B], "metered", executor, executor_name="paid_probe"
    )[0]
    assert record.status == "completed", record.error_message
    assert seen == [("reserved", 50.0, None, 50.0), ("reserved", 50.0, None, 51.5)]
    saved = registry(output)
    assert saved["committedCostYen"] == 3.0
    assert [call["settledCostYen"] for call in saved["calls"].values()] == [1.5, 1.5]


@pytest.mark.parametrize("cost_yen", [None, 50.01])
def test_unknown_or_over_cap_cost_keeps_reservation_and_stops_campaign(setup, cost_yen):
    output, _, _, task = setup
    executor = capped(50.0, cost_yen=cost_yen)
    with pytest.raises(ValueError, match="audit required"):
        harness(setup).run_cohort(
            [task],
            [ConditionType.A, ConditionType.B],
            "audit",
            executor,
            executor_name="paid_probe",
        )
    assert len(executor.calls) == 1
    saved = registry(output)
    assert saved["committedCostYen"] == 50.0
    call = saved["calls"][executor.calls[0]]
    assert (call["status"], call["settledCostYen"], call["auditRequired"]) == (
        "failed",
        50.0,
        True,
    )
    with pytest.raises(ValueError, match="audit"):
        harness(setup).run_cohort(
            [task], [ConditionType.B], "audit", executor, executor_name="paid_probe"
        )
    assert len(executor.calls) == 1


def test_transport_error_with_unknown_cost_is_not_retried(setup):
    output, _, _, task = setup

    def lost(step, payload):
        raise ConnectionError("Synthetic lost acknowledgement")

    executor = capped(50.0, respond=lost)
    with pytest.raises(ValueError, match="audit required"):
        harness(setup).run_cohort(
            [task], [ConditionType.A], "retry", executor, executor_name="paid_probe"
        )
    assert len(executor.calls) == 1
    saved = registry(output)
    assert saved["committedCostYen"] == 50.0
    assert saved["calls"][executor.calls[0]]["auditRequired"] is True


def test_parallel_roles_each_hold_a_reservation_until_settled(setup):
    output, _, _, task = setup
    barrier = threading.Barrier(2, timeout=3)
    committed_at_barrier = []

    def respond(step, payload):
        result = dummy_synthetic_executor(step, payload)
        kind = payload["responseSchema"]["required"][0]
        if kind == "proposal":
            result["proposal"]["probes"] = [
                {
                    "id": f"parallel_{i}",
                    "gapIds": ["synthetic_gap"],
                    "method": "boundary",
                    "question": str(i),
                    "requiredCapability": "document_read",
                    "sourceGroups": [],
                    "successCondition": "yes",
                    "refutationCondition": "no",
                    "inconclusiveCondition": "unknown",
                }
                for i in range(2)
            ]
        elif kind == "observations":
            barrier.wait()
            committed_at_barrier.append(registry(output)["committedCostYen"])
            barrier.wait()
            result["observations"] = [
                {
                    "executionId": payload["clientRequestId"],
                    "probeId": payload["context"]["probe"]["id"],
                    "outcome": "completed",
                    "evidence": [],
                }
            ]
        return result

    executor = capped(50.0, cost_yen=1.5, respond=respond)
    record = harness(setup).run_cohort(
        [task], [ConditionType.E], "parallel", executor, executor_name="paid_probe"
    )[0]
    assert record.status == "completed", record.error_message
    assert committed_at_barrier == [101.5, 101.5]
    assert len(executor.calls) == 4
    assert registry(output)["committedCostYen"] == 6.0
