"""Synthetic regression coverage for saved critical-evidence recall integrity."""

from dataclasses import replace
import hashlib

import pytest

from ommatidia.harness import TrialRecord
from ommatidia.scoring import score_saved_trial
from ommatidia.types import (
    Budget,
    CitedEvidenceItem,
    ConditionType,
    Evidence,
    EvidenceKind,
    EvidenceValidity,
    FinalJudgement,
    FinalJudgementResourceUsage,
    TaskPacket,
    UnderstandingState,
)


@pytest.fixture
def saved_trial():
    passage = "Synthetic observation: the indicator remained blue."
    evidence = Evidence(
        id="retrieved_indicator",
        kind=EvidenceKind.DOCUMENT,
        locator="synthetic/indicator.txt",
        source_group="synthetic_indicator",
        retrieved_at="2026-10-16T00:00:00Z",
        version=None,
        scope="Synthetic indicator observation",
        passage=passage,
        content_hash=hashlib.sha256(passage.encode("utf-8")).hexdigest(),
    )
    task = TaskPacket(
        schema_version="0.1",
        task_id="synthetic_passage_integrity",
        goal="Assess the synthetic indicator observation.",
        mode="explain",
        success_criteria=["Cite the retrieved observation accurately."],
        evidence=[],
        capabilities=[],
        budget=Budget(1, 1, 1, 1000, 1000, 1000),
    )
    state = UnderstandingState(
        schema_version="0.1",
        task_id=task.task_id,
        revision=1,
        started_at="2026-10-16T00:00:00Z",
        task=task,
        evidence=[evidence],
    )
    judgement = FinalJudgement(
        task_id=task.task_id,
        verdict="supported",
        confidence_score=1.0,
        justification="The synthetic observation supports the answer.",
        cited_evidence=[
            CitedEvidenceItem(
                id=evidence.id,
                source_group=evidence.source_group,
                locator=evidence.locator,
                content_hash=evidence.content_hash,
                passage=evidence.passage,
                verdict_relation="supports",
            )
        ],
        unresolved_gaps=[],
        resource_usage=FinalJudgementResourceUsage(0, 0, 0),
    )
    record = TrialRecord(
        task_id=task.task_id,
        condition=ConditionType.A,
        run_id="synthetic_passage_integrity",
        final_state=state.to_dict(),
        final_judgement=judgement,
    )
    rubric = {
        "taskId": task.task_id,
        "targetVerdict": "supported",
        "criticalEvidenceHashes": [evidence.content_hash],
    }
    return record, rubric


def test_recall_credits_matching_passage_with_correct_sha256(saved_trial):
    record, rubric = saved_trial
    assert score_saved_trial(record, rubric, metrics=["recallCrit"]) == {
        "recallCrit": 1.0
    }


def test_recall_rejects_changed_citation_passage_with_original_provenance(saved_trial):
    record, rubric = saved_trial
    original = record.final_judgement.cited_evidence[0]
    record.final_judgement.cited_evidence = [
        replace(original, passage="Synthetic observation: the indicator turned red.")
    ]
    assert score_saved_trial(record, rubric, metrics=["recallCrit"]) == {
        "recallCrit": 0.0
    }


def test_recall_rejects_matching_passages_with_incorrect_stored_sha256(saved_trial):
    record, rubric = saved_trial
    incorrect_hash = hashlib.sha256(b"A different synthetic observation.").hexdigest()
    record.final_state["evidence"][0]["contentHash"] = incorrect_hash
    original = record.final_judgement.cited_evidence[0]
    record.final_judgement.cited_evidence = [
        replace(original, content_hash=incorrect_hash)
    ]
    rubric["criticalEvidenceHashes"] = [incorrect_hash]
    assert score_saved_trial(record, rubric, metrics=["recallCrit"]) == {
        "recallCrit": 0.0
    }


def test_recall_excludes_task_input_evidence(saved_trial):
    record, rubric = saved_trial
    record.final_state["task"]["evidence"] = [dict(record.final_state["evidence"][0])]
    assert score_saved_trial(record, rubric, metrics=["recallCrit"]) == {
        "recallCrit": 0.0
    }


@pytest.mark.parametrize(
    "validity", [EvidenceValidity.WITHDRAWN, EvidenceValidity.SUPERSEDED]
)
def test_recall_excludes_non_current_evidence(saved_trial, validity):
    record, rubric = saved_trial
    record.final_state["evidence"][0]["validity"] = validity.value
    assert score_saved_trial(record, rubric, metrics=["recallCrit"]) == {
        "recallCrit": 0.0
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("locator", "synthetic/another.txt"),
        ("source_group", "another_synthetic_source"),
    ],
)
def test_recall_rejects_mismatched_citation_provenance(saved_trial, field, value):
    record, rubric = saved_trial
    original = record.final_judgement.cited_evidence[0]
    record.final_judgement.cited_evidence = [replace(original, **{field: value})]
    assert score_saved_trial(record, rubric, metrics=["recallCrit"]) == {
        "recallCrit": 0.0
    }
