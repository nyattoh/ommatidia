"""Per-task Budget.max_cost_yen enforced before dispatch through the harness; synthetic data only."""

import dataclasses
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


def run(setup, task_cost_yen, cost_yen, condition=ConditionType.E):
    output, manifest, freeze, task = setup
    task = dataclasses.replace(
        task, budget=dataclasses.replace(task.budget, max_cost_yen=task_cost_yen)
    )
    calls = []

    def executor(step, payload):
        calls.append(payload["clientRequestId"])
        result = dummy_synthetic_executor(step, payload)
        result["usage"] = {**result["usage"], "costYen": cost_yen}
        return result

    executor.enforced_cost_cap_yen = 50.0
    harness = ResearchHarness(
        output, seal_manifest_path=manifest, runtime_freeze_path=freeze
    )
    record = harness.run_cohort([task], [condition], "task_cost", executor)[0]
    saved = json.loads((output / "resource_registry.json").read_text(encoding="utf-8"))
    return record, calls, saved


def test_task_budget_below_per_call_cap_dispatches_nothing(setup):
    record, calls, saved = run(setup, task_cost_yen=10.0, cost_yen=40.0)
    assert calls == []
    assert (record.status, record.error_message) == (
        "failed",
        "Trial cost ceiling would be exceeded",
    )
    assert (saved["calls"], saved["committedCostYen"]) == ({}, 0.0)


def test_task_budget_admits_calls_only_while_a_full_cap_fits(setup):
    record, calls, saved = run(setup, task_cost_yen=90.0, cost_yen=50.0)
    assert len(calls) == 1
    assert (record.status, record.error_message) == (
        "failed",
        "Trial cost ceiling would be exceeded",
    )
    assert saved["committedCostYen"] == 50.0


def test_task_without_cost_budget_is_limited_only_by_the_campaign(setup):
    record, calls, saved = run(setup, task_cost_yen=None, cost_yen=50.0)
    assert record.status == "completed", record.error_message
    assert (len(calls), saved["committedCostYen"]) == (2, 100.0)


@pytest.mark.parametrize("limit", [float("nan"), float("inf")])
def test_configured_but_unbounded_task_cost_limit_fails_closed(tmp_path, limit):
    task = get_mechanism_check_fixtures()[0][0]
    reg = GlobalResourceRegistry(storage_path=tmp_path / "registry.json")
    reg.begin_trial("t1", ConditionType.A, {"case": "t1"})
    with pytest.raises(ResourceLimitExceeded, match="Trial cost limit"):
        reg.reserve_step(
            "t1",
            "s1",
            0,
            10,
            dataclasses.replace(task.budget, max_cost_yen=limit),
            reserved_cost_yen=0.0,
        )
    assert reg.calls == {}
