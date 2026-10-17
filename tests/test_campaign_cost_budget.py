import json
import math
import threading

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


def registry(tmp_path, trials=("t1",), **kwargs):
    reg = GlobalResourceRegistry(storage_path=tmp_path / "registry.json", **kwargs)
    for key in trials:
        reg.begin_trial(key, ConditionType.A, {"case": key})
    return reg


def reserve(reg, step_id, cost, key="t1"):
    reg.reserve_step(key, step_id, 0, 10, budget(), reserved_cost_yen=cost)


def saved(tmp_path):
    return json.loads((tmp_path / "registry.json").read_text(encoding="utf-8"))


def test_campaign_cost_ceiling_is_capped_at_the_authorised_500_yen():
    assert GlobalResourceRegistry(max_cost_yen=10_000.0).max_cost_yen == 500.0


def test_reservation_and_settlement_persist_cost_amounts(tmp_path):
    reg = registry(tmp_path)
    reserve(reg, "s1", 2.5)
    call = saved(tmp_path)["calls"]["s1"]
    assert (call["reservedCostYen"], call["settledCostYen"]) == (2.5, None)

    reg.settle_step(
        "s1", Usage(model_calls=1, input_chars=10, cost_yen=1.25), True, "completed"
    )
    call = saved(tmp_path)["calls"]["s1"]
    assert (call["reservedCostYen"], call["settledCostYen"]) == (2.5, 1.25)
    assert saved(tmp_path)["committedCostYen"] == 1.25


def test_admission_counts_settled_cost_plus_in_flight_reservations(tmp_path):
    reg = registry(tmp_path)
    reserve(reg, "a", 300.0)
    reserve(reg, "b", 150.0)
    reg.settle_step(
        "a", Usage(model_calls=1, input_chars=10, cost_yen=100.0), True, "completed"
    )
    reserve(reg, "c", 250.0)
    with pytest.raises(ResourceLimitExceeded, match="cost"):
        reserve(reg, "d", 0.01)
    assert "d" not in reg.calls
    assert saved(tmp_path)["committedCostYen"] == 500.0


def test_concurrent_reservations_never_overcommit_the_ceiling(tmp_path):
    reg = registry(tmp_path, trials=[f"t{i}" for i in range(8)])
    gate = threading.Barrier(8)
    admitted, refused = [], []

    def worker(i):
        gate.wait()
        try:
            reserve(reg, f"s{i}", 100.0, key=f"t{i}")
            admitted.append(i)
        except ResourceLimitExceeded:
            refused.append(i)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert (len(admitted), len(refused)) == (5, 3)
    assert saved(tmp_path)["committedCostYen"] == 500.0


@pytest.mark.parametrize("cost", [None, math.inf, math.nan, -1.0, True, "1"])
def test_unknown_or_unbounded_per_call_cost_fails_closed_before_reservation(
    tmp_path, cost
):
    reg = registry(tmp_path)
    with pytest.raises(ResourceLimitExceeded, match="cost"):
        reserve(reg, "s1", cost)
    assert reg.calls == {}
    assert saved(tmp_path)["calls"] == {}


@pytest.mark.parametrize("actual", [None, 3.01])
def test_unknown_or_excess_settlement_retains_reservation_and_stops_for_audit(
    tmp_path, actual
):
    reg = registry(tmp_path)
    reserve(reg, "s1", 3.0)
    with pytest.raises(ResourceLimitExceeded, match="audit"):
        reg.settle_step(
            "s1",
            Usage(model_calls=1, input_chars=10, cost_yen=actual),
            actual is not None,
            "completed",
        )

    data = saved(tmp_path)
    call = data["calls"]["s1"]
    assert (call["settledCostYen"], call["auditRequired"], call["status"]) == (
        3.0,
        True,
        "failed",
    )
    assert data["trials"]["t1"]["auditRequired"] is True
    assert data["committedCostYen"] == 3.0
    with pytest.raises(ResourceLimitExceeded, match="audit"):
        reserve(reg, "s2", 0.0)

    reloaded = GlobalResourceRegistry()
    reloaded.load_from_path(tmp_path / "registry.json")
    with pytest.raises(ResourceLimitExceeded, match="audit"):
        reserve(reloaded, "s2", 0.0)
