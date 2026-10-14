"""Dev-only synthetic unit fixtures labelled as mechanism checks.

IMPORTANT NOTICE:
These fixtures are solely for mechanism verification and software testing of the runtime.
They DO NOT represent empirical research results, benchmark evaluation data,
or comparative efficacy measurements.
"""

from __future__ import annotations

from typing import List, Tuple

from ommatidia.types import (
    Budget,
    Decision,
    Evidence,
    EvidenceKind,
    EvidenceValidity,
    GoldStandard,
    TaskPacket,
)


def get_mechanism_check_fixtures() -> List[Tuple[TaskPacket, GoldStandard]]:
    """Return synthetic dev-only task packets and separate gold standards for unit testing."""
    budget = Budget(
        max_rounds=5,
        max_model_calls=8,
        max_tool_calls=12,
        max_elapsed_ms=180000,
        max_input_chars=48000,
        max_output_tokens_per_call=16000,
        max_cost_yen=None,
    )

    # Fixture 1: Falsification check (cache validity contradiction)
    task1 = TaskPacket(
        schema_version="0.1",
        task_id="dev_mech_cache_01",
        goal="Determine if the distributed cache remains consistent across node eviction.",
        mode="explain",
        success_criteria=["Identify whether eviction invalidates secondary cache copies."],
        evidence=[
            Evidence(
                id="ev_doc_01",
                kind=EvidenceKind.DOCUMENT,
                locator="docs/cache_spec_v1.md",
                source_group="spec_docs",
                retrieved_at="2026-10-14T00:00:00Z",
                version="1.0",
                scope="distributed_cache",
                passage="Eviction events broadcast asynchronously without receipt confirmation.",
                content_hash="a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90",
                validity=EvidenceValidity.CURRENT,
            )
        ],
        capabilities=["code_search", "document_read"],
        budget=budget,
        proposed_answer="Cache is strictly consistent.",
    )

    gold1 = GoldStandard(
        task_id="dev_mech_cache_01",
        domain="systems_dev",
        required_gap_questions=[
            "Does asynchronous broadcast guarantee secondary copy invalidation?",
        ],
        critical_evidence_hashes=[
            "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90",
        ],
        expected_answer_keywords=["asynchronous", "inconsistent", "no receipt"],
        ground_truth_verdicts={
            "claim_dev_mech_cache_01_01": "contradicted",
        },
        target_decision=Decision.READY_FOR_REQUESTED_STEP,
    )

    # Fixture 2: Duplicate evidence suppression check
    task2 = TaskPacket(
        schema_version="0.1",
        task_id="dev_mech_duplicate_02",
        goal="Verify if the migration protocol requires database lock.",
        mode="explain",
        success_criteria=["Check concurrency lock requirement."],
        evidence=[],
        capabilities=["document_read"],
        budget=budget,
    )

    gold2 = GoldStandard(
        task_id="dev_mech_duplicate_02",
        domain="database_ops",
        required_gap_questions=["Is global table lock required during migration?"],
        critical_evidence_hashes=[],
        expected_answer_keywords=["online", "lock-free"],
        ground_truth_verdicts={},
        target_decision=Decision.READY_FOR_REQUESTED_STEP,
    )

    return [(task1, gold1), (task2, gold2)]
