"""Behaviour regressions on public harness/CLI paths; temporary synthetic data only."""

import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from ommatidia.campaign import (
    GlobalResourceRegistry,
    ResourceLimitExceeded,
    atomic_json,
)
from ommatidia.harness import (
    ResearchHarness,
    TrialRecord,
    export_masked_assessor_dataset,
    sanitize_ledger_file,
)
from ommatidia.integrity import ROOT, fingerprints, verify_runtime_freeze
from ommatidia.contracts import PROPOSAL_SCHEMA
from ommatidia.runtime import condition_graph, validate_proposal_shape
from ommatidia.scoring import MetricUnavailable, analyse_saved_trials, score_saved_trial
from ommatidia.seal import SealMismatchError, create_seal_manifest
from ommatidia.t3_adapter import (
    T3DelegationAdapter,
    create_condition_dispatch_jobs,
    create_t3_executor,
)
from ommatidia.types import ConditionType, Decision, GoldStandard, Usage
from scripts.run_harness import dummy_synthetic_executor, main
from tests.fixtures.synthetic_dev_cases import get_mechanism_check_fixtures
from tests.freeze_fixture import report_clean_git_status, write_current_freeze


@pytest.fixture
def setup(tmp_path, monkeypatch):
    report_clean_git_status(monkeypatch)
    protocol = tmp_path / "protocol.md"
    protocol.write_text("Synthetic protocol", encoding="utf-8")
    manifest = tmp_path / "seal.json"
    create_seal_manifest(protocol, [], manifest)
    task = get_mechanism_check_fixtures()[0][0]
    return tmp_path / "output", manifest, task


TEST_HOST_COST_CAP_YEN = 5.0


def host_boundary():
    """Test double for a host that attests its configured per-call cap. It tests transport handling only."""
    flags = dict.fromkeys(
        ["publicOnly", "singleModelInvocation", "enforcesStepBudget", "hostUsageVerified"], True
    )
    flags["enforcedCostCapYen"] = TEST_HOST_COST_CAP_YEN
    return lambda _payload: dict(flags)


def make_harness(setup, **kwargs):
    output, manifest, _ = setup
    kwargs.setdefault("runtime_freeze_path", write_current_freeze(output.parent, release_ready=True))
    return ResearchHarness(output, seal_manifest_path=manifest, **kwargs)


def judgement(task_id, verdict="contradicted"):
    return {
        "taskId": task_id,
        "verdict": verdict,
        "confidenceScore": 0.7,
        "justification": "Synthetic response deliberately differs from the proposed answer.",
        "citedEvidence": [],
        "unresolvedGaps": [],
        "resourceUsage": {
            "modelCalls": 1,
            "toolCalls": 0,
            "elapsedMs": 1,
            "inputCharsEstimated": 0,
        },
    }


@pytest.mark.parametrize("condition", [ConditionType.A, ConditionType.B])
@pytest.mark.parametrize("nested", [False, True])
def test_actual_child_verdict_survives_roundtrip(setup, condition, nested):
    output, _, task = setup

    def executor(step, payload):
        response = judgement(task.task_id)
        return {"finalJudgement": response} if nested else response

    executor.synthetic_only = True

    record = make_harness(setup).run_cohort([task], [condition], "verdict", executor)[0]
    saved = TrialRecord.from_dict(
        json.loads(next((output / "dev/trials").glob("*.json")).read_text())
    )
    assert saved.final_judgement.verdict == "contradicted"
    assert saved.final_judgement.confidence_score == 0.7
    assert saved.usage.model_calls == (1 if condition == ConditionType.A else 2)
    assert saved.final_judgement.resource_usage.model_calls == saved.usage.model_calls


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"finalJudgement": {"verdict": "supported"}},
        {"taskId": "wrong", "verdict": "contradicted"},
        judgement("wrong"),
        {**judgement("dev_mech_cache_01"), "confidenceScore": True},
    ],
)
@pytest.mark.parametrize("condition", [ConditionType.A, ConditionType.B])
def test_blank_invalid_response_is_inconclusive(setup, response, condition):
    _, _, task = setup
    def executor(*_):
        return response

    executor.synthetic_only = True
    record = make_harness(setup).run_cohort(
        [task], [condition], "invalid", executor
    )[0]
    assert record.status == "invalid_response"
    assert record.final_judgement.verdict == "inconclusive"
    assert record.final_judgement.confidence_score == 0
    assert record.usage.model_calls >= 1


def test_failed_trials_persist_and_cohort_continues(setup):
    output, _, task = setup

    def fail(*_):
        raise RuntimeError("Synthetic outage")

    fail.synthetic_only = True

    records = make_harness(setup).run_cohort(
        [task], [ConditionType.A, ConditionType.B], "outage", fail
    )
    assert len(records) == 2
    for file in (output / "dev/trials").glob("*.json"):
        record = TrialRecord.from_dict(json.loads(file.read_text()))
        assert record.status == "failed"
        assert record.usage.model_calls == 1
        assert record.final_judgement.to_dict()["verdict"] == "inconclusive"
    assert json.loads((output / "dev/summary.json").read_text())["failedTrials"] == 2
    registry = json.loads((output / "resource_registry.json").read_text())
    assert registry["totalTrials"] == 2 and registry["totalModelCalls"] == 2
    before = (output / "resource_registry.json").read_bytes()
    make_harness(setup).run_cohort(
        [task], [ConditionType.A, ConditionType.B], "outage", fail
    )
    assert (output / "resource_registry.json").read_bytes() == before


def test_retry_is_charged_and_reserved_before_each_dispatch(setup):
    output, _, task = setup
    calls = []

    def executor(step, payload):
        registry = json.loads((output / "resource_registry.json").read_text())
        calls.append(payload["clientRequestId"])
        assert registry["totalModelCalls"] == len(calls)
        assert registry["calls"][calls[-1]]["status"] == "reserved"
        if len(calls) == 1:
            raise ConnectionError("Transient synthetic transport error")
        return {
            **judgement(task.task_id),
            "usage": {"modelCalls": 1, "toolCalls": 0, "costYen": 0.0},
        }

    executor.synthetic_only = True

    record = make_harness(setup).run_cohort(
        [task], [ConditionType.A], "retry", executor
    )[0]
    assert record.status == "completed" and record.usage.model_calls == 2
    assert len(set(calls)) == 2
    assert [step["attempt"] for step in record.steps] == [1, 2]


def test_resume_is_idempotent_across_fresh_instances(setup):
    output, _, task = setup
    tasks = [task, replace(task, task_id="synthetic_second")]
    totals = []
    for _ in range(3):
        harness = make_harness(setup)
        harness.run_cohort(
            tasks,
            [ConditionType.A, ConditionType.B],
            "resume",
            dummy_synthetic_executor,
        )
        totals.append(
            (
                harness.resource_registry.total_trials,
                harness.resource_registry.total_model_calls,
            )
        )
    assert totals == [(4, 6)] * 3


def test_campaign_caps_span_partitions_and_stop_before_call(setup):
    _, _, task = setup
    calls = []

    def executor(step, payload):
        calls.append(step)
        return dummy_synthetic_executor(step, payload)

    executor.synthetic_only = True

    registry = GlobalResourceRegistry(max_aggregate_model_calls=1, max_total_trials=2)
    make_harness(setup, resource_registry=registry).run_cohort(
        [task], [ConditionType.A], "first", executor, partition="dev"
    )
    with pytest.raises(ResourceLimitExceeded):
        make_harness(setup).run_cohort(
            [task],
            [ConditionType.A],
            "second",
            executor,
            partition="test_other_partition",
        )
    assert len(calls) == 1


def test_corrupt_registry_and_legacy_records_fail_closed(setup):
    output, _, task = setup
    output.mkdir()
    path = output / "resource_registry.json"
    path.write_text('{"totalTrials":', encoding="utf-8")
    with pytest.raises(ValueError, match="registry"):
        make_harness(setup).run_cohort(
            [task], [ConditionType.A], "corrupt", dummy_synthetic_executor
        )
    path.unlink()
    stale = output / "dev/trials/stale.json"
    atomic_json(stale, TrialRecord(task.task_id, ConditionType.A, "old").to_dict())
    before = stale.read_bytes()
    with pytest.raises(ValueError, match="Unregistered"):
        make_harness(setup).run_cohort(
            [task], [ConditionType.A], "legacy", dummy_synthetic_executor
        )
    assert stale.read_bytes() == before


def test_crash_keeps_reservation_without_redispatch(setup):
    output, _, task = setup

    def crash(*_):
        raise KeyboardInterrupt()

    crash.synthetic_only = True

    with pytest.raises(KeyboardInterrupt):
        make_harness(setup).run_cohort([task], [ConditionType.A], "crash", crash)
    registry = json.loads((output / "resource_registry.json").read_text())
    assert registry["totalTrials"] == 1 and registry["totalModelCalls"] == 1
    with pytest.raises(ValueError, match="no resumable record"):
        make_harness(setup).run_cohort(
            [task], [ConditionType.A], "crash", dummy_synthetic_executor
        )


def test_negative_usage_never_reduces_reserved_calls(setup):
    _, _, task = setup
    def executor(*_):
        return {"usage": {"modelCalls": -100, "toolCalls": -100}}

    executor.synthetic_only = True
    record = make_harness(setup).run_cohort(
        [task],
        [ConditionType.A],
        "negative",
        executor,
    )[0]
    assert record.status == "failed" and record.usage.model_calls == 1
    assert record.usage.tool_calls >= 0


@pytest.mark.parametrize("condition", list(ConditionType))
def test_execution_and_plan_use_same_graph_and_injected_transport(setup, condition):
    _, _, task = setup
    dispatched = []
    active = {}

    def dispatcher(tool, args):
        if tool == "delegate_task":
            payload = json.loads(args["task"].split("\n", 1)[1])
            assert payload["proposedAnswer"] == task.proposed_answer
            assert payload["budget"]["maxModelCalls"] == 8
            assert payload["stepBudget"]["maxModelCalls"] == 1
            assert args["isolation"] == "worktree"
            assert "responseSchema" in payload
            assert "criticalEvidenceHashes" not in args["task"]
            assert "/gold/" not in args["task"] and "/cases/" not in args["task"]
            task_id = f"child_{len(dispatched)}"
            dispatched.append(payload)
            active[task_id] = dummy_synthetic_executor(payload["stepName"], payload)
            return {
                "taskId": task_id,
                "providerInstanceId": "test_provider",
                "model": "test_model",
            }
        return {
            "status": "completed",
            "summary": json.dumps(active[args["taskId"]]),
            "hostUsage": {"modelCalls": 1, "toolCalls": 0, "costYen": 0.0},
        }

    boundary = host_boundary()
    adapter = T3DelegationAdapter(
        "test_provider",
        "test_model",
        in_session_dispatcher=dispatcher,
        host_cost_cap_yen=TEST_HOST_COST_CAP_YEN,
        public_boundary=boundary,
        poll_interval_seconds=0,
    )
    record = make_harness(setup).run_cohort(
        [task],
        [condition],
        "graph",
        create_t3_executor(adapter),
        executor_name="t3_simulation",
    )[0]
    assert record.status == "completed"
    planned = create_condition_dispatch_jobs(task, condition, "graph")
    expected = [step.name for step in condition_graph(condition)]
    actual = [payload["stepName"] for payload in dispatched]
    assert all(name in expected for name in actual)
    assert [job.step_name for job in planned] == expected
    if condition in (ConditionType.C, ConditionType.D, ConditionType.E):
        assert "synthesis" in actual[-1]
    if condition == ConditionType.B:
        assert dispatched[-1]["context"]["priorOutput"]["verdict"] == "inconclusive"
    assert all(step["taskId"].startswith("child_") for step in record.steps)
    assert all(
        step["providerInstanceId"] == "test_provider" and step["model"] == "test_model"
        for step in record.steps
    )


def test_unattested_t3_transport_never_dispatches(setup):
    _, _, task = setup
    calls = []
    executor = create_t3_executor(
        T3DelegationAdapter(in_session_dispatcher=lambda *args: calls.append(args))
    )
    with pytest.raises(Exception, match="public-only"):
        make_harness(setup).run_cohort(
            [task], [ConditionType.A], "blocked", executor, executor_name="t3"
        )
    assert calls == []


def test_resume_rejects_saved_hash_changes(setup):
    output, _, task = setup
    make_harness(setup).run_cohort(
        [task], [ConditionType.A], "hash", dummy_synthetic_executor
    )
    file = next((output / "dev/trials").glob("*.json"))
    data = json.loads(file.read_text())
    data["codeHash"] = "deadbeef"
    atomic_json(file, data)
    with pytest.raises(ValueError, match="checkpoint"):
        make_harness(setup).run_cohort(
            [task], [ConditionType.A], "hash", dummy_synthetic_executor
        )


def test_real_hashes_and_freeze_detect_driver_change(tmp_path):
    frozen = json.loads((ROOT / "research/runtime_freeze_r3.json").read_text())
    current = fingerprints()
    assert current["codeHash"] != hashlib.sha256(b"ommatidia_code_A").hexdigest()
    for name in current["files"]:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    (tmp_path / "src/ommatidia/runtime.py").write_text(
        "changed driver", encoding="utf-8"
    )
    manifest = tmp_path / "freeze.json"
    atomic_json(manifest, frozen)
    with pytest.raises(SealMismatchError, match="freeze mismatch"):
        verify_runtime_freeze(manifest, root=tmp_path)


def test_actual_mask_export_strips_nested_usage_and_separates_mapping(setup):
    output, _, task = setup
    records = make_harness(setup).run_cohort(
        [task], [ConditionType.A, ConditionType.B], "mask", dummy_synthetic_executor
    )
    dataset, mapping = export_masked_assessor_dataset(records, output)
    masked = json.loads(dataset.read_text())
    for record in masked:
        text = json.dumps(record)
        assert (
            "resourceUsage" not in text
            and "modelCalls" not in text
            and "elapsedMs" not in text
        )
        assert "codeHash" not in text and "steps" not in text and "executor" not in text
    assert dataset.parent != mapping.parent
    assert mapping.exists()  # No key contents are read.


def test_cli_failure_exit(setup, monkeypatch):
    output, manifest, _ = setup
    def blank_executor(*_):
        return {}

    blank_executor.synthetic_only = True
    monkeypatch.setattr("scripts.run_harness.dummy_synthetic_executor", blank_executor)
    assert (
        main(
            [
                "--output-dir",
                str(output),
                "--manifest",
                str(manifest),
                "--runtime-freeze",
                str(write_current_freeze(output.parent)),
                "--condition-primary",
                "A",
            ]
        )
        == 1
    )
    assert len(list((output / "mechanism/trials").glob("*.json"))) == 2


def test_ledger_only_recovers_torn_trailing_line(tmp_path):
    file = tmp_path / "ledger.jsonl"
    file.write_text('{}\n{"torn":', encoding="utf-8")
    sanitize_ledger_file(file)
    assert file.read_text().splitlines() == ["{}"]
    file.write_text("{}\ninvalid\n{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="interior"):
        sanitize_ledger_file(file)


@pytest.mark.parametrize("condition", [ConditionType.D, ConditionType.E])
def test_adaptive_graph_ingests_each_selected_probe_and_synthesises(setup, condition):
    _, _, task = setup
    calls = []

    def executor(step, payload):
        calls.append((step, payload))
        kind = payload["responseSchema"]["required"][0]
        output = dummy_synthetic_executor(step, payload)
        if kind == "proposal":
            output["proposal"]["probes"] = [
                {
                    "id": f"probe_{i}",
                    "gapIds": ["synthetic_gap"],
                    "method": "boundary",
                    "question": f"Synthetic check {i}",
                    "requiredCapability": "document_read",
                    "sourceGroups": [f"public_source_{i}"],
                    "successCondition": "found",
                    "refutationCondition": "refuted",
                    "inconclusiveCondition": "unavailable",
                }
                for i in range(2)
            ]
        if kind == "observations":
            probe = payload["context"]["probe"]
            output["observations"] = [
                {
                    "executionId": payload["clientRequestId"],
                    "probeId": probe["id"],
                    "outcome": "completed",
                    "evidence": [],
                    "toolCalls": 0,
                    "elapsedMs": 0,
                }
            ]
        return output

    executor.synthetic_only = True
    record = make_harness(setup).run_cohort([task], [condition], "probes", executor)[0]
    assert record.status == "completed"
    assert "synthesis" in calls[-1][0]
    assert {probe["status"] for probe in record.final_state["probes"]} == {"complete"}
    investigated = [
        payload["context"]["probe"]["id"]
        for _, payload in calls
        if "probe" in payload["context"]
    ]
    assert sorted(investigated) == ["probe_0", "probe_1"]
    assert record.usage.model_calls <= 8


@pytest.mark.parametrize("condition", [ConditionType.D, ConditionType.E])
def test_adaptive_graph_rejects_incomplete_proposal_before_synthesis(setup, condition):
    _, _, task = setup
    calls = []

    def executor(step, payload):
        if payload["responseSchema"]["required"][0] == "proposal":
            calls.append(step)
            return {"proposal": {}}
        calls.append(step)
        return dummy_synthetic_executor(step, payload)

    executor.synthetic_only = True
    record = make_harness(setup).run_cohort(
        [task], [condition], "invalid-proposal", executor
    )[0]

    assert record.status == "failed"
    assert record.error_message
    assert calls == [condition_graph(condition)[0].name]
    assert record.final_state["probes"] == []


@pytest.mark.parametrize("field", ["claims", "lenses", "gaps", "probes"])
def test_proposal_shape_requires_each_schema_array(field):
    required = PROPOSAL_SCHEMA["properties"]["proposal"]["required"]
    proposal = {name: [] for name in required}
    proposal.pop(field)

    with pytest.raises(ValueError, match=f"Missing required proposal field: {field}"):
        validate_proposal_shape({"proposal": proposal})


@pytest.mark.parametrize("field", ["claims", "lenses", "gaps", "probes"])
def test_proposal_shape_requires_arrays_for_required_fields(field):
    required = PROPOSAL_SCHEMA["properties"]["proposal"]["required"]
    proposal = {name: [] for name in required}
    proposal[field] = None

    with pytest.raises(
        ValueError, match=f"Required proposal field must be an array: {field}"
    ):
        validate_proposal_shape({"proposal": proposal})


def test_proposal_shape_keeps_optional_arrays_optional():
    required = PROPOSAL_SCHEMA["properties"]["proposal"]["required"]

    validate_proposal_shape({"proposal": {name: [] for name in required}})


def saved_matrix(setup):
    _, _, task = setup
    source = make_harness(setup).run_cohort(
        [task], [ConditionType.A], "matrix", dummy_synthetic_executor
    )[0]
    records = []
    for i in range(24):
        for condition in (
            ConditionType.B,
            ConditionType.C,
            ConditionType.D,
            ConditionType.E,
        ):
            record = copy.deepcopy(source)
            record.task_id = f"public_synthetic_{i:02d}"
            record.condition = condition
            record.final_judgement.task_id = record.task_id
            record.final_state["taskId"] = record.task_id
            record.final_state["task"]["taskId"] = record.task_id
            record.final_state["finalJudgement"]["taskId"] = record.task_id
            record.metrics = {
                "fda": int(condition == ConditionType.E),
                "recallCrit": 0.8 if condition == ConditionType.E else 0.2,
                "dsc": (i % 3 + 1) if condition == ConditionType.E else 0,
                "far": 0.0 if condition == ConditionType.E else (i % 3 + 1) / 4,
            }
            records.append(record)
    return records


def test_saved_scoring_uses_observations_and_refuses_unavailable_metrics(setup):
    _, _, task = setup
    record = make_harness(setup).run_cohort(
        [task], [ConditionType.A], "score", dummy_synthetic_executor
    )[0]
    new_evidence = copy.deepcopy(record.final_state["evidence"][0])
    new_evidence.update(
        id="retrieved_evidence",
        contentHash=hashlib.sha256(b"New public passage").hexdigest(),
        passage="New public passage",
        locator="public/new.txt",
        sourceGroup="new_source",
    )
    record.final_state["evidence"].append(new_evidence)
    from ommatidia.types import CitedEvidenceItem

    record.final_judgement.cited_evidence = [
        CitedEvidenceItem(
            new_evidence["id"],
            new_evidence["sourceGroup"],
            new_evidence["locator"],
            new_evidence["contentHash"],
            new_evidence["passage"],
            "context",
        )
    ]
    rubric = {
        "taskId": task.task_id,
        "targetVerdict": "inconclusive",
        "criticalEvidenceHashes": [
            task.evidence[0].content_hash,
            new_evidence["contentHash"],
        ],
        "requiredGapQuestions": ["A separate required question"],
    }
    scored = score_saved_trial(
        record,
        rubric,
        ["fda", "recallCrit", "dsc", "requiredGapRecall", "warrantedAbstention"],
    )
    assert scored == {
        "fda": 1,
        "recallCrit": 0.5,
        "dsc": 1,
        "requiredGapRecall": 0.0,
        "warrantedAbstention": 1,
    }
    with pytest.raises(MetricUnavailable, match="zero"):
        score_saved_trial(record, rubric, ["efficiencyTool"])
    record.final_state["probes"] = [
        {
            "id": "candidate",
            "gapIds": ["synthetic_gap"],
            "method": "boundary",
            "question": "Possible issue",
            "requiredCapability": "document_read",
            "sourceGroups": [],
            "successCondition": "yes",
            "refutationCondition": "no",
            "inconclusiveCondition": "unknown",
            "status": "complete",
        }
    ]
    with pytest.raises(MetricUnavailable, match="independent labels"):
        score_saved_trial(record, rubric, ["far"])
    rubric["probeLabels"] = {"candidate": "spurious"}
    assert score_saved_trial(record, rubric, ["far"])["far"] == 1.0


@pytest.mark.parametrize("hypothesis", ["H1", "H2", "H3", "H4"])
@pytest.mark.parametrize("favourable", [True, False], ids=["favourable", "adverse"])
def test_saved_analysis_significance_requires_predicted_direction(setup, hypothesis, favourable):
    from ommatidia.evaluator import compute_wilcoxon_signed_rank
    from ommatidia.harness import compute_exact_mcnemar, compute_holm_bonferroni

    records = saved_matrix(setup)
    ids = sorted({record.task_id for record in records})
    if not favourable:
        for record in records:
            record.metrics["fda"] = 1 - record.metrics["fda"]
            record.metrics["recallCrit"] = 1 - record.metrics["recallCrit"]
            record.metrics["dsc"] = 3 - record.metrics["dsc"]
            record.metrics["far"] = 1 - record.metrics["far"]

    result = analyse_saved_trials(records, ids, ids[:12])
    expected_p = [
        compute_exact_mcnemar(24, 0),
        compute_wilcoxon_signed_rank([i % 3 + 1 for i in range(24)])["pValue"],
        compute_wilcoxon_signed_rank([-(i % 3 + 1) / 4 for i in range(24)])["pValue"],
        compute_exact_mcnemar(12, 0),
    ]
    assert [item["test"]["pValue"] for item in result["hypotheses"]] == expected_p
    assert [item["holmAdjustedP"] for item in result["hypotheses"]] == compute_holm_bonferroni(expected_p)
    direction = 1 if favourable else -1
    assert [item["meanDifference"] for item in result["hypotheses"]] == [
        direction, 2 * direction, -0.5 * direction, direction
    ]
    report = next(item for item in result["hypotheses"] if item["hypothesis"] == hypothesis)
    assert report["holmAdjustedP"] < 0.05
    assert report["significant"] is (favourable and hypothesis != "H4")
    assert report["directionalSignificanceAvailable"] is (hypothesis != "H4")


@pytest.mark.parametrize("hypothesis", ["H2", "H3"])
def test_saved_analysis_uses_signed_rank_direction_not_mean_for_wilcoxon(hypothesis, setup):
    records = saved_matrix(setup)
    by_pair = {
        (record.condition.value, record.task_id): record
        for record in records
    }
    ids = sorted({record.task_id for record in records})

    for index, task_id in enumerate(ids):
        if hypothesis == "H2":
            # Mean E-D is positive, but signed ranks strongly favour D.
            by_pair[("D", task_id)].metrics["dsc"] = 0 if index < 3 else 1
            by_pair[("E", task_id)].metrics["dsc"] = 100 if index < 3 else 0
        else:
            # Mean E-D FAR is negative, but signed ranks strongly favour D.
            by_pair[("D", task_id)].metrics["far"] = 1.0 if index < 3 else 0.5
            by_pair[("E", task_id)].metrics["far"] = 0.0 if index < 3 else 0.51

    result = analyse_saved_trials(records, ids, ids[:12])
    report = next(item for item in result["hypotheses"] if item["hypothesis"] == hypothesis)

    if hypothesis == "H2":
        assert report["meanDifference"] > 0
        assert report["test"]["wPlus"] < report["test"]["wMinus"]
    else:
        assert report["meanDifference"] < 0
        assert report["test"]["wPlus"] > report["test"]["wMinus"]
    assert report["holmAdjustedP"] < 0.05
    assert report["significant"] is False


def test_cli_paired_tests_require_24_saved_pairs_and_apply_holm(setup):
    output, manifest, _ = setup
    records = saved_matrix(setup)
    ids = sorted({record.task_id for record in records})
    design = output.parent / "analysis_design.json"
    atomic_json(design, {"taskIds": ids, "counterexampleIds": ids[:12]})
    data = json.loads(manifest.read_text())
    data["datasets"][str(design)] = {
        "hash": hashlib.sha256(design.read_bytes()).hexdigest()
    }
    atomic_json(manifest, data)
    saved = output.parent / "saved_trials.json"
    atomic_json(saved, [record.to_dict() for record in records])
    assert (
        main(
            [
                "--mode",
                "paired_compare",
                "--output-dir",
                str(output),
                "--manifest",
                str(manifest),
                "--runtime-freeze",
                str(write_current_freeze(output.parent)),
                "--records-file",
                str(saved),
                "--analysis-design",
                str(design),
            ]
        )
        == 0
    )
    report = json.loads((output / "dev/paired_h1_h4.json").read_text())
    assert report["sampleSize"] == 24 and report["familySize"] == 4
    assert [item["sampleSize"] for item in report["hypotheses"]] == [24, 24, 24, 12]
    from ommatidia.harness import compute_holm_bonferroni

    p_values = [item["test"]["pValue"] for item in report["hypotheses"]]
    assert [
        item["holmAdjustedP"] for item in report["hypotheses"]
    ] == compute_holm_bonferroni(p_values)
    with pytest.raises(ValueError, match="24 cases"):
        analyse_saved_trials(records[:-1], ids, ids[:12])
    records[-1].metrics.pop("far")
    with pytest.raises(MetricUnavailable, match="far"):
        analyse_saved_trials(records, ids, ids[:12])


def test_cli_evaluate_scores_complete_saved_matrix_without_changing_trials(setup):
    output, manifest, _ = setup
    records = [
        record for record in saved_matrix(setup) if record.condition == ConditionType.E
    ]
    records[0].status = "failed"
    rubrics = {
        record.task_id: {
            "taskId": record.task_id,
            "targetVerdict": "inconclusive",
            "criticalEvidenceHashes": ["1" * 64],
        }
        for record in records
    }
    rubric = output.parent / "synthetic_rubrics.json"
    atomic_json(rubric, rubrics)
    data = json.loads(manifest.read_text())
    data["datasets"][str(rubric)] = {
        "hash": hashlib.sha256(rubric.read_bytes()).hexdigest()
    }
    atomic_json(manifest, data)
    saved = output.parent / "synthetic_records.json"
    atomic_json(saved, [record.to_dict() for record in records])
    before = saved.read_bytes()
    assert (
        main(
            [
                "--mode",
                "evaluate",
                "--conditions",
                "E",
                "--run-id",
                "matrix",
                "--output-dir",
                str(output),
                "--manifest",
                str(manifest),
                "--runtime-freeze",
                str(write_current_freeze(output.parent)),
                "--records-file",
                str(saved),
                "--rubric-file",
                str(rubric),
            ]
        )
        == 1
    )
    scored = json.loads((output / "dev/scored_trials.json").read_text())
    assert len(scored) == 24 and sum(item["metrics"]["fda"] for item in scored) == 23
    assert all("far" not in item["metrics"] for item in scored)
    assert saved.read_bytes() == before


def test_per_trial_budget_stops_before_extra_dispatch(setup):
    _, _, task = setup
    task = replace(task, budget=replace(task.budget, max_model_calls=1))
    dispatched = []

    def executor(step, payload):
        dispatched.append(step)
        return dummy_synthetic_executor(step, payload)

    executor.synthetic_only = True

    record = make_harness(setup).run_cohort(
        [task], [ConditionType.B], "one_call", executor
    )[0]
    assert dispatched == ["pass1_investigation"]
    assert record.status == "failed" and record.usage.model_calls == 1


def test_timeout_cancels_each_attempt_and_keeps_task_ids_and_usage(setup):
    _, _, task = setup
    dispatched, cancelled = [], []

    def dispatcher(tool, args):
        if tool == "delegate_task":
            tid = f"timeout_child_{len(dispatched)}"
            dispatched.append(tid)
            return {"taskId": tid, "providerInstanceId": "test", "model": "test"}
        if tool == "task_cancel":
            cancelled.append(args["taskId"])
            return {"status": "cancelled"}
        return {"status": "running"}

    boundary = host_boundary()
    adapter = T3DelegationAdapter(
        "test",
        "test",
        timeout_seconds=0,
        in_session_dispatcher=dispatcher,
        host_cost_cap_yen=TEST_HOST_COST_CAP_YEN,
        public_boundary=boundary,
    )
    # Cancelled attempts leave cost unsettled, so the campaign stops for audit and keeps the trial record.
    with pytest.raises(ValueError, match="audit required"):
        make_harness(setup).run_cohort(
            [task],
            [ConditionType.A],
            "timeout",
            create_t3_executor(adapter),
            executor_name="t3_simulation",
        )
    record = TrialRecord.from_dict(json.loads(next((setup[0] / "dev/trials").glob("*.json")).read_text()))
    assert record.status == "failed" and record.usage.model_calls == len(dispatched) >= 1
    assert dispatched == cancelled
    assert [step["taskId"] for step in record.steps] == dispatched
    assert not record.usage_known and record.usage.tool_calls == 12


def test_campaign_trial_limit_is_shared_by_partitions(setup):
    _, _, task = setup
    registry = GlobalResourceRegistry(max_total_trials=1)
    make_harness(setup, resource_registry=registry).run_cohort(
        [task],
        [ConditionType.A],
        "trial_cap",
        dummy_synthetic_executor,
        partition="dev",
    )
    with pytest.raises(ResourceLimitExceeded, match="trial ceiling"):
        make_harness(setup).run_cohort(
            [task],
            [ConditionType.B],
            "trial_cap",
            dummy_synthetic_executor,
            partition="synthetic_other",
        )


def test_e_roles_overlap_and_reservations_remain_consistent(setup):
    import threading

    _, _, task = setup
    barrier = threading.Barrier(2, timeout=3)

    def executor(step, payload):
        output = dummy_synthetic_executor(step, payload)
        if payload["responseSchema"]["required"][0] == "proposal":
            output["proposal"]["probes"] = [
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
        elif payload["responseSchema"]["required"][0] == "observations":
            barrier.wait()
            assert payload["stepBudget"]["maxToolCalls"] == 6
            output["observations"] = [
                {
                    "executionId": payload["clientRequestId"],
                    "probeId": payload["context"]["probe"]["id"],
                    "outcome": "completed",
                    "evidence": [],
                }
            ]
        return output

    executor.synthetic_only = True
    harness = make_harness(setup)
    record = harness.run_cohort([task], [ConditionType.E], "parallel", executor)[0]
    assert record.status == "completed", record.error_message
    # plan, two concurrent investigators, the update planning pass, synthesis
    assert record.usage.model_calls == harness.resource_registry.total_model_calls == 5
    assert len({step["stepId"] for step in record.steps}) == 5
    assert record.wall_elapsed_ms > 0


def test_ambiguous_dispatch_stops_campaign_after_persisting_failure(setup):
    output, _, task = setup
    calls = []

    def dispatcher(tool, args):
        calls.append(tool)
        raise ConnectionError("Synthetic lost acknowledgement")

    boundary = host_boundary()
    executor = create_t3_executor(
        T3DelegationAdapter(in_session_dispatcher=dispatcher, public_boundary=boundary, host_cost_cap_yen=TEST_HOST_COST_CAP_YEN)
    )
    with pytest.raises(ValueError, match="audit required"):
        make_harness(setup).run_cohort(
            [task],
            [ConditionType.A, ConditionType.B],
            "ambiguous",
            executor,
            executor_name="t3_simulation",
        )
    saved = [
        TrialRecord.from_dict(json.loads(file.read_text()))
        for file in (output / "dev/trials").glob("*.json")
    ]
    assert (
        len(saved) == 1 and saved[0].audit_required and saved[0].usage.model_calls == 1
    )
    with pytest.raises(ValueError, match="audit"):
        make_harness(setup).run_cohort(
            [task],
            [ConditionType.B],
            "ambiguous",
            executor,
            executor_name="t3_simulation",
        )
    assert calls == ["delegate_task"]


def test_reported_envelope_breach_is_durable_and_requires_audit(setup):
    output, _, task = setup

    def executor(*_):
        return {"usage": {"modelCalls": 9, "toolCalls": 0}}

    executor.synthetic_only = True

    with pytest.raises(ValueError, match="audit required"):
        make_harness(setup).run_cohort(
            [task], [ConditionType.A, ConditionType.B], "breach", executor
        )
    registry = json.loads((output / "resource_registry.json").read_text())
    assert registry["totalModelCalls"] == 9
    assert len(list((output / "dev/trials").glob("*.json"))) == 1


def test_initial_accounting_cannot_be_reset_by_trial_reservation(setup):
    _, _, task = setup
    registry = GlobalResourceRegistry(total_model_calls=1920)
    with pytest.raises(ResourceLimitExceeded):
        make_harness(setup, resource_registry=registry).run_cohort(
            [task], [ConditionType.A], "exhausted", dummy_synthetic_executor
        )
    assert registry.total_model_calls == 1920
