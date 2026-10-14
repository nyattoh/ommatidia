"""Tests for UnderstandingState lifecycle, idempotency, and stopping conditions."""

import unittest

from ommatidia.state import (
    apply_observations,
    apply_proposal,
    create_initial_state,
    evaluate_stopping_conditions,
)
from ommatidia.types import (
    Budget,
    Claim,
    ClaimRole,
    ClaimStatus,
    Decision,
    Evidence,
    EvidenceKind,
    Gap,
    GapImportance,
    GapKind,
    GapStatus,
    Lens,
    LensOrigin,
    Observation,
    ObservationOutcome,
    Probe,
    ProbeMethod,
    ProbeStatus,
    Proposal,
    TaskPacket,
    Usage,
)
from tests.fixtures.synthetic_dev_cases import get_mechanism_check_fixtures


class TestUnderstandingState(unittest.TestCase):
    def setUp(self) -> None:
        fixtures = get_mechanism_check_fixtures()
        self.task, self.gold = fixtures[0]
        self.state = create_initial_state(self.task)

    def test_initial_state_creation(self) -> None:
        self.assertEqual(self.state.task_id, "dev_mech_cache_01")
        self.assertEqual(self.state.revision, 0)
        self.assertEqual(self.state.decision, Decision.NEEDS_CHECK)
        self.assertEqual(len(self.state.evidence), 1)
        self.assertEqual(len(self.state.claims), 0)

    def test_apply_proposal_and_revision_increment(self) -> None:
        lens = Lens(
            id="lens_cache_bound",
            label="Cache boundary",
            rationale="Evaluate boundary conditions",
            origin=LensOrigin.PROPOSED,
        )
        gap = Gap(
            id="gap_eviction_broadcast",
            kind=GapKind.MISSING_FACT,
            lens_id=lens.id,
            question="Is broadcast asynchronous?",
            trigger_refs=["spec_docs"],
            why_it_matters="Determines consistency",
            importance=GapImportance.REQUIRED,
            claim_ids=[],
            probe_ids=["probe_verify_sync"],
        )
        probe = Probe(
            id="probe_verify_sync",
            gap_ids=[gap.id],
            method=ProbeMethod.BOUNDARY,
            question="Check broadcast confirmation receipt",
            required_capability="code_search",
            source_groups=["source_code"],
            success_condition="Receipt is confirmed",
            refutation_condition="No receipt confirmed",
            inconclusive_condition="Code unavailable",
        )
        prop = Proposal(lenses=[lens], gaps=[gap], probes=[probe])

        report = apply_proposal(self.state, prop)
        self.assertEqual(report["newRevision"], 1)
        self.assertEqual(len(self.state.lenses), 1)
        self.assertEqual(len(self.state.gaps), 1)
        self.assertEqual(len(self.state.probes), 1)

    def test_apply_observation_idempotency(self) -> None:
        # First register probe
        probe = Probe(
            id="probe_obs_check",
            gap_ids=["gap_test"],
            method=ProbeMethod.EXAMPLE,
            question="Examine logs",
            required_capability="doc_read",
            source_groups=["logs"],
            success_condition="success",
            refutation_condition="fail",
            inconclusive_condition="empty",
        )
        self.state.probes.append(probe)

        obs = Observation(
            execution_id="exec_001",
            probe_id=probe.id,
            outcome=ObservationOutcome.COMPLETED,
            evidence=[],
            tool_calls=2,
            elapsed_ms=500.0,
            cost_yen=10.0,
            total_tokens=150,
        )

        res1 = apply_observations(self.state, [obs])
        self.assertEqual(res1["appliedExecutionsCount"], 1)
        self.assertEqual(self.state.usage.tool_calls, 2)
        self.assertEqual(probe.status, ProbeStatus.COMPLETE)

        # Re-apply identical execution: should be skipped idempotently
        res2 = apply_observations(self.state, [obs])
        self.assertEqual(res2["appliedExecutionsCount"], 0)
        self.assertEqual(self.state.usage.tool_calls, 2)  # tool_calls not doubled

    def test_stopping_rules(self) -> None:
        # 1. Active state needs check
        should_stop, reason, dec = evaluate_stopping_conditions(self.state, self.task.budget)
        self.assertFalse(should_stop)
        self.assertEqual(dec, Decision.NEEDS_CHECK)

        # 2. Budget exhaustion
        exhausted_state = create_initial_state(self.task)
        exhausted_state.usage.tool_calls = 999
        should_stop, reason, dec = evaluate_stopping_conditions(exhausted_state, self.task.budget)
        self.assertTrue(should_stop)
        self.assertEqual(reason, "budget_exhausted")
        self.assertEqual(dec, Decision.BLOCKED)


if __name__ == "__main__":
    unittest.main()
