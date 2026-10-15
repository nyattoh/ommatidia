"""Campaign cost-cap edge cases from the cost-ledger review; synthetic data only."""

import json

import pytest

from ommatidia.campaign import (
    GlobalResourceRegistry,
    ResourceLimitExceeded,
    atomic_json,
)
from ommatidia.harness import ResearchHarness
from ommatidia.integrity import fingerprints
from ommatidia.seal import create_seal_manifest
from ommatidia.types import Budget, ConditionType, Usage
from scripts.run_harness import dummy_synthetic_executor
from tests.fixtures.synthetic_dev_cases import get_mechanism_check_fixtures


def budget(max_cost_yen=500.0):
    return Budget(
        max_rounds=4,
        max_model_calls=8,
        max_tool_calls=12,
        max_elapsed_ms=180000,
        max_input_chars=48000,
        max_output_tokens_per_call=0,
        max_cost_yen=max_cost_yen,
    )


def registry(tmp_path, **kwargs):
    reg = GlobalResourceRegistry(storage_path=tmp_path / "registry.json", **kwargs)
    reg.begin_trial("t1", ConditionType.A, {"case": "t1"})
    return reg


def reserve(reg, step_id, cost, task_budget=None):
    reg.reserve_step(
        "t1", step_id, 0, 10, task_budget or budget(), reserved_cost_yen=cost
    )


def settle(reg, step_id, cost):
    reg.settle_step(
        step_id, Usage(model_calls=1, input_chars=10, cost_yen=cost), True, "completed"
    )


def saved(tmp_path):
    return json.loads((tmp_path / "registry.json").read_text(encoding="utf-8"))


def test_manual_cost_above_ceiling_is_kept_and_blocks_new_reservations(tmp_path):
    reg = registry(tmp_path)
    with pytest.raises(ResourceLimitExceeded, match="cost"):
        reg.record_step("legacy", Usage(model_calls=1, cost_yen=900.0))
    with pytest.raises(ResourceLimitExceeded, match="cost"):
        reserve(reg, "s1", 400.0)
    assert reg.calls == {}
    assert saved(tmp_path)["committedCostYen"] == 900.0


def test_manual_known_cost_shares_the_campaign_ceiling(tmp_path):
    reg = registry(tmp_path)
    reg.record_step("legacy", Usage(model_calls=1, cost_yen=450.0))
    with pytest.raises(ResourceLimitExceeded, match="cost"):
        reserve(reg, "s1", 50.01)
    reserve(reg, "s2", 50.0)
    assert saved(tmp_path)["committedCostYen"] == 500.0


def test_constructor_cost_is_preserved_as_manual_usage(tmp_path):
    reg = registry(tmp_path, total_model_calls=5, cost_yen=450.0)
    with pytest.raises(ResourceLimitExceeded, match="cost"):
        reserve(reg, "s1", 100.0)
    reserve(reg, "s2", 50.0)
    data = saved(tmp_path)
    assert (data["manualUsage"]["costYen"], data["committedCostYen"]) == (450.0, 500.0)


@pytest.mark.parametrize("seed", ["constructor", "record_step"])
def test_unknown_manual_cost_fails_closed_for_new_reservations(tmp_path, seed):
    if seed == "constructor":
        reg = registry(tmp_path, total_model_calls=5)
    else:
        reg = registry(tmp_path)
        reg.record_step("legacy", Usage(model_calls=1))
    with pytest.raises(ResourceLimitExceeded, match="unknown"):
        reserve(reg, "s1", 0.0)
    assert reg.calls == {}
    assert saved(tmp_path)["committedCostYen"] is None


def test_second_settlement_is_rejected_and_keeps_the_first_amount(tmp_path):
    reg = registry(tmp_path)
    reserve(reg, "s1", 50.0)
    settle(reg, "s1", 10.0)
    with pytest.raises(ResourceLimitExceeded, match="already settled"):
        settle(reg, "s1", 1.0)
    call = saved(tmp_path)["calls"]["s1"]
    assert (call["status"], call["settledCostYen"]) == ("completed", 10.0)
    assert saved(tmp_path)["committedCostYen"] == 10.0


def test_reload_with_in_flight_reservation_requires_audit(tmp_path):
    reg = registry(tmp_path)
    reserve(reg, "s1", 50.0)
    del reg  # Simulated crash between dispatch and settlement.

    reloaded = GlobalResourceRegistry()
    reloaded.load_from_path(tmp_path / "registry.json")
    assert reloaded.trials["t1"]["auditRequired"] is True
    assert reloaded.calls["s1"]["auditRequired"] is True
    assert reloaded.committed_cost_yen() == 50.0
    with pytest.raises(ResourceLimitExceeded, match="audit"):
        reserve(reloaded, "s2", 0.0)


def test_float_rounding_cannot_admit_a_reservation_above_the_ceiling(tmp_path):
    reg = registry(tmp_path)
    reserve(reg, "a", 499.99999999999994)
    with pytest.raises(ResourceLimitExceeded, match="cost"):
        reserve(reg, "b", 2**-44 + 2**-46)  # Float sum rounds to exactly 500.0.
    assert list(reg.calls) == ["a"]


def test_float_rounding_cannot_admit_a_reservation_above_the_task_budget(tmp_path):
    reg = registry(tmp_path)
    reserve(reg, "a", 9.999999999999998, budget(10.0))
    with pytest.raises(ResourceLimitExceeded, match="Trial cost"):
        reserve(reg, "b", 2**-49 + 2**-51, budget(10.0))
    assert list(reg.calls) == ["a"]


def test_previous_schema_is_rejected_with_an_audited_migration_error(tmp_path):
    reg = registry(tmp_path)
    reserve(reg, "s1", 5.0)
    settle(reg, "s1", 5.0)
    data = saved(tmp_path)
    data["schemaVersion"] = 3
    (tmp_path / "registry.json").write_text(json.dumps(data), encoding="utf-8")

    reloaded = GlobalResourceRegistry()
    with pytest.raises(ValueError, match="schemaVersion 3.*audited migration"):
        reloaded.load_from_path(tmp_path / "registry.json")
    assert reloaded.calls == {}


@pytest.fixture
def harness_setup(tmp_path):
    protocol = tmp_path / "protocol.md"
    protocol.write_text("Synthetic protocol", encoding="utf-8")
    manifest = tmp_path / "seal.json"
    create_seal_manifest(protocol, [], manifest)
    freeze = tmp_path / "freeze.json"
    atomic_json(freeze, {**fingerprints(), "baseCommit": "HEAD"})
    return tmp_path / "output", manifest, freeze, get_mechanism_check_fixtures()[0][0]


def test_harness_refuses_any_trial_after_a_crash_left_a_call_reserved(harness_setup):
    output, manifest, freeze, task = harness_setup
    crashed = GlobalResourceRegistry(storage_path=output / "resource_registry.json")
    crashed.begin_trial(f"dev/{task.task_id}/A/1", ConditionType.A, {"case": "crashed"})
    crashed.reserve_step(
        f"dev/{task.task_id}/A/1", "lost", 0, 10, task.budget, reserved_cost_yen=50.0
    )
    calls = []

    def executor(step, payload):
        calls.append(step)
        return dummy_synthetic_executor(step, payload)

    executor.enforced_cost_cap_yen = 50.0
    harness = ResearchHarness(
        output, seal_manifest_path=manifest, runtime_freeze_path=freeze
    )
    with pytest.raises(ValueError, match="audit"):
        harness.run_cohort([task], [ConditionType.B], "after_crash", executor, executor_name="paid_probe")
    assert calls == []
    assert list(
        json.loads((output / "resource_registry.json").read_text(encoding="utf-8"))[
            "calls"
        ]
    ) == ["lost"]
