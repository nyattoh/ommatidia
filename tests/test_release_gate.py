"""Research partitions require an approved, clean release before dispatch."""

import json

import pytest

from ommatidia.harness import ResearchHarness
from ommatidia.seal import SealMismatchError, create_seal_manifest
from ommatidia.types import ConditionType
from scripts.run_harness import dummy_synthetic_executor
from tests.fixtures.synthetic_dev_cases import get_mechanism_check_fixtures
from tests.freeze_fixture import set_git_status, write_current_freeze


@pytest.fixture
def setup(tmp_path):
    protocol = tmp_path / "protocol.md"
    protocol.write_text("Synthetic protocol", encoding="utf-8")
    manifest = tmp_path / "seal.json"
    create_seal_manifest(protocol, [], manifest)
    task = get_mechanism_check_fixtures()[0][0]
    return ResearchHarness(
        tmp_path / "output",
        seal_manifest_path=manifest,
        runtime_freeze_path=write_current_freeze(tmp_path, release_ready=True),
    ), task


def capped_executor(calls):
    def executor(step, payload):
        calls.append(step)
        return dummy_synthetic_executor(step, payload)

    executor.enforced_cost_cap_yen = 5.0
    return executor


@pytest.mark.parametrize("partition", ["dev", "heldout"])
def test_direct_research_execution_rejects_dirty_tree(setup, monkeypatch, partition):
    harness, task = setup
    set_git_status(monkeypatch, "?? untracked.txt\n")
    calls = []
    with pytest.raises(SealMismatchError, match="clean freeze"):
        harness.evaluate_task(
            task, condition=ConditionType.A, executor_func=capped_executor(calls),
            executor_name="paid_probe", partition=partition,
        )
    assert calls == []


def test_direct_research_execution_requires_approved_package(setup, monkeypatch):
    harness, task = setup
    data = json.loads(harness.runtime_freeze_path.read_text(encoding="utf-8"))
    del data["evaluationPackageStatus"]
    harness.runtime_freeze_path.write_text(json.dumps(data), encoding="utf-8")
    set_git_status(monkeypatch, "")
    calls = []
    with pytest.raises(SealMismatchError, match="Replacement evaluation package"):
        harness.evaluate_task(
            task, condition=ConditionType.A, executor_func=capped_executor(calls),
            executor_name="paid_probe", partition="dev",
        )
    assert calls == []


def test_cohort_rejects_before_lock_and_dispatch(setup, monkeypatch):
    harness, task = setup
    set_git_status(monkeypatch, "?? untracked.txt\n")
    calls = []
    def unexpected_lock(*_args):
        raise AssertionError("lock acquired before release check")
    monkeypatch.setattr(harness.campaign_lock, "acquire_lock", unexpected_lock)
    with pytest.raises(SealMismatchError, match="clean freeze"):
        harness.run_cohort(
            [task], [ConditionType.A], "dirty", capped_executor(calls),
            executor_name="paid_probe", partition="dev",
        )
    assert calls == []


def test_synthetic_mechanism_still_runs(setup):
    harness, task = setup
    records = harness.run_cohort(
        [task], [ConditionType.A], "mechanism", dummy_synthetic_executor,
        partition="mechanism", executor_name="synthetic",
    )
    assert len(records) == 1


def test_release_git_status_includes_untracked_despite_config(setup, monkeypatch):
    harness, _ = setup
    commands = []
    set_git_status(
        monkeypatch, "", status_for_untracked_all="?? hidden-by-default.txt\n",
        commands=commands,
    )
    with pytest.raises(SealMismatchError, match="clean freeze"):
        harness.verify_environment(require_release=True)
    assert commands and "--ignore-submodules=none" in commands[0]


@pytest.mark.parametrize("method", ["evaluate_task", "run_cohort"])
@pytest.mark.parametrize("partition", ["mechanism", "DEV", "dev ", "heldout_r5_candidate", "test_other_partition"])
def test_paid_executor_rejects_dirty_tree_for_any_partition(setup, monkeypatch, method, partition):
    harness, task = setup
    set_git_status(monkeypatch, "?? untracked.txt\n")
    calls = []
    executor = capped_executor(calls)
    with pytest.raises(SealMismatchError, match="clean freeze"):
        if method == "evaluate_task":
            harness.evaluate_task(task, condition=ConditionType.A, executor_func=executor,
                                  executor_name="paid_probe", partition=partition)
        else:
            harness.run_cohort([task], [ConditionType.A], "dirty", executor,
                               executor_name="paid_probe", partition=partition)
    assert calls == []


@pytest.mark.parametrize("method", ["evaluate_task", "run_cohort"])
def test_unmarked_callable_cannot_use_synthetic_name(setup, monkeypatch, method):
    harness, task = setup
    set_git_status(monkeypatch, "")
    calls = []

    def unmarked_paid_callable(step, payload):
        calls.append(step)
        return dummy_synthetic_executor(step, payload)

    with pytest.raises(ValueError, match="Synthetic path"):
        if method == "evaluate_task":
            harness.evaluate_task(task, condition=ConditionType.A,
                                  executor_func=unmarked_paid_callable,
                                  executor_name="synthetic", partition="dev")
        else:
            harness.run_cohort([task], [ConditionType.A], "unmarked",
                               unmarked_paid_callable, executor_name="synthetic",
                               partition="dev")
    assert calls == []


def test_heldout_requires_approved_package_even_with_clean_tree(setup, monkeypatch):
    harness, task = setup
    data = json.loads(harness.runtime_freeze_path.read_text(encoding="utf-8"))
    del data["evaluationPackageStatus"]
    harness.runtime_freeze_path.write_text(json.dumps(data), encoding="utf-8")
    set_git_status(monkeypatch, "")
    calls = []
    with pytest.raises(SealMismatchError, match="Replacement evaluation package"):
        harness.evaluate_task(task, condition=ConditionType.A,
                              executor_func=capped_executor(calls),
                              executor_name="paid_probe", partition="heldout")
    assert calls == []


def test_direct_rejection_does_not_acquire_lock_or_write_registry(setup, monkeypatch):
    harness, task = setup
    set_git_status(monkeypatch, "?? untracked.txt\n")
    calls = []
    lock_calls = []
    original_acquire = harness.campaign_lock.acquire_lock

    def track_acquire(run_id):
        lock_calls.append(run_id)
        return original_acquire(run_id)

    monkeypatch.setattr(harness.campaign_lock, "acquire_lock", track_acquire)
    with pytest.raises(SealMismatchError, match="clean freeze"):
        harness.evaluate_task(task, condition=ConditionType.A,
                              executor_func=capped_executor(calls),
                              executor_name="paid_probe", partition="dev")
    assert calls == []
    assert lock_calls == []
    assert not harness.campaign_lock.lock_path.exists()
    assert not harness.resource_registry.storage_path.exists()
