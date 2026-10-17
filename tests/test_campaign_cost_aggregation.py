import json

import pytest

from ommatidia.campaign import GlobalResourceRegistry, ResourceLimitExceeded
from ommatidia.types import Budget, ConditionType, Usage


def budget():
    return Budget(
        max_rounds=4,
        max_model_calls=8,
        max_tool_calls=12,
        max_elapsed_ms=180000,
        max_input_chars=48000,
        max_output_tokens_per_call=0,
        max_cost_yen=500.0,
    )


def registry(tmp_path):
    reg = GlobalResourceRegistry(storage_path=tmp_path / "registry.json")
    reg.begin_trial("t1", ConditionType.A, {"case": "t1"})
    return reg


def settle(reg, step_id, cost, tokens):
    reg.reserve_step("t1", step_id, 0, 10, budget(), reserved_cost_yen=50.0)
    reg.settle_step(
        step_id,
        Usage(model_calls=1, input_chars=10, total_tokens=tokens, cost_yen=cost),
        True,
        "completed",
    )


def saved(tmp_path):
    return json.loads((tmp_path / "registry.json").read_text(encoding="utf-8"))


def test_known_settlements_aggregate_to_exact_registry_and_trial_totals(tmp_path):
    reg = registry(tmp_path)
    settle(reg, "s1", 12.5, 300)
    settle(reg, "s2", 7.25, 120)

    data = saved(tmp_path)
    assert (data["costYen"], data["totalTokens"], data["committedCostYen"]) == (
        19.75,
        420,
        19.75,
    )
    trial = reg.trial_usage("t1")
    assert (trial.cost_yen, trial.total_tokens) == (19.75, 420)

    reloaded = GlobalResourceRegistry()
    reloaded.load_from_path(tmp_path / "registry.json")
    assert (reloaded.cost_yen, reloaded.total_tokens) == (19.75, 420)


def test_one_unknown_settlement_keeps_aggregates_unknown_and_requires_audit(tmp_path):
    reg = registry(tmp_path)
    settle(reg, "s1", 12.5, 300)
    with pytest.raises(ResourceLimitExceeded, match="audit required"):
        settle(reg, "s2", None, 120)

    data = saved(tmp_path)
    assert (data["costYen"], data["committedCostYen"]) == (None, 62.5)
    assert data["trials"]["t1"]["auditRequired"] is True
    assert reg.trial_usage("t1").cost_yen is None
    with pytest.raises(ResourceLimitExceeded, match="audit required"):
        reg.reserve_step("t1", "s3", 0, 10, budget(), reserved_cost_yen=1.0)


def test_in_flight_reservation_keeps_cost_unknown_until_settled(tmp_path):
    reg = registry(tmp_path)
    settle(reg, "s1", 12.5, 300)
    reg.reserve_step("t1", "s2", 0, 10, budget(), reserved_cost_yen=50.0)

    assert (saved(tmp_path)["costYen"], saved(tmp_path)["committedCostYen"]) == (
        None,
        62.5,
    )
    assert reg.trial_usage("t1").cost_yen is None

    reg.settle_step(
        "s2",
        Usage(model_calls=1, input_chars=10, total_tokens=80, cost_yen=0.5),
        True,
        "completed",
    )
    assert (saved(tmp_path)["costYen"], reg.trial_usage("t1").cost_yen) == (13.0, 13.0)
