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

        res1 = apply_observations(self.state, [obs], track_tool_calls=True)
        self.assertEqual(res1["appliedExecutionsCount"], 1)
        self.assertEqual(self.state.usage.tool_calls, 2)
        self.assertEqual(probe.status, ProbeStatus.COMPLETE)

        # Re-apply identical execution: should be skipped idempotently
        res2 = apply_observations(self.state, [obs], track_tool_calls=True)
        self.assertEqual(res2["appliedExecutionsCount"], 0)
        self.assertEqual(self.state.usage.tool_calls, 2)  # tool_calls not doubled

    def test_apply_observations_avoids_double_counting_by_default(self) -> None:
        probe = Probe(
            id="probe_dc_check",
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
            execution_id="exec_dc_001",
            probe_id=probe.id,
            outcome=ObservationOutcome.COMPLETED,
            evidence=[],
            tool_calls=2,
            elapsed_ms=500.0,
        )

        # Step-level usage is already recorded in state.usage by _accumulate_step_usage
        self.state.usage.tool_calls = 2
        # apply_observations should NOT double count it
        apply_observations(self.state, [obs])
        self.assertEqual(self.state.usage.tool_calls, 2)

    def test_apply_observations_rejects_negative_usage(self) -> None:
        obs_bad = Observation(
            execution_id="exec_neg",
            probe_id="probe_any",
            outcome=ObservationOutcome.COMPLETED,
            evidence=[],
            tool_calls=-1,
            elapsed_ms=0.0,
        )
        with self.assertRaises(ValueError):
            apply_observations(self.state, [obs_bad])

    def test_apply_observations_preserves_unknown_cost_and_tokens(self) -> None:
        self.state.usage.cost_yen = None
        self.state.usage.total_tokens = None

        obs = Observation(
            execution_id="exec_known_cost",
            probe_id="probe_obs_check",
            outcome=ObservationOutcome.COMPLETED,
            evidence=[],
            tool_calls=1,
            elapsed_ms=10.0,
            cost_yen=5.0,
            total_tokens=100,
        )
        apply_observations(self.state, [obs])
        # Must remain None, never promoted back to 5.0 or 100
        self.assertIsNone(self.state.usage.cost_yen)
        self.assertIsNone(self.state.usage.total_tokens)

    def test_apply_observations_preserves_known_host_cost_when_omitted_and_allows_continuation_under_cap(
        self,
    ) -> None:
        # Step host cost is already known before applying observation with cost omitted
        self.state.usage.cost_yen = 25.0

        obs_omitted = Observation(
            execution_id="exec_cost_omitted",
            probe_id="probe_cost_test",
            outcome=ObservationOutcome.COMPLETED,
            evidence=[],
            tool_calls=1,
            elapsed_ms=50.0,
            cost_yen=None,
        )
        apply_observations(self.state, [obs_omitted])
        # Preserves known host cost instead of resetting to None
        self.assertEqual(self.state.usage.cost_yen, 25.0)

        # Continuation under cap via closest existing focused stopping/budget path
        capped_budget = Budget(
            max_rounds=self.task.budget.max_rounds,
            max_model_calls=self.task.budget.max_model_calls,
            max_tool_calls=self.task.budget.max_tool_calls,
            max_elapsed_ms=self.task.budget.max_elapsed_ms,
            max_input_chars=self.task.budget.max_input_chars,
            max_output_tokens_per_call=self.task.budget.max_output_tokens_per_call,
            max_cost_yen=50.0,
        )
        should_stop, reason, dec = evaluate_stopping_conditions(self.state, capped_budget)
        self.assertFalse(should_stop)
        self.assertIsNone(reason)
        self.assertEqual(dec, Decision.NEEDS_CHECK)

        # Explicit observation cost adds once to existing known cost
        obs_explicit = Observation(
            execution_id="exec_cost_explicit",
            probe_id="probe_cost_test",
            outcome=ObservationOutcome.COMPLETED,
            evidence=[],
            tool_calls=1,
            elapsed_ms=50.0,
            cost_yen=10.0,
        )
        apply_observations(self.state, [obs_explicit])
        self.assertEqual(self.state.usage.cost_yen, 35.0)

        # Re-applying identical execution skips idempotently without adding cost again
        apply_observations(self.state, [obs_explicit])
        self.assertEqual(self.state.usage.cost_yen, 35.0)

        # Unknown remains None on observation with cost omitted or explicit cost
        self.state.usage.cost_yen = None
        obs_omitted_when_unk = Observation(
            execution_id="exec_cost_omitted_unk",
            probe_id="probe_cost_test",
            outcome=ObservationOutcome.COMPLETED,
            evidence=[],
            tool_calls=1,
            elapsed_ms=10.0,
            cost_yen=None,
        )
        apply_observations(self.state, [obs_omitted_when_unk])
        self.assertIsNone(self.state.usage.cost_yen)

        obs_explicit_when_unk = Observation(
            execution_id="exec_cost_explicit_unk",
            probe_id="probe_cost_test",
            outcome=ObservationOutcome.COMPLETED,
            evidence=[],
            tool_calls=1,
            elapsed_ms=10.0,
            cost_yen=5.0,
        )
        apply_observations(self.state, [obs_explicit_when_unk])
        self.assertIsNone(self.state.usage.cost_yen)

    def test_apply_observations_preserves_known_step_tokens_when_omitted(
        self,
    ) -> None:
        # Step host tokens already known before applying observation with total_tokens omitted
        self.state.usage.total_tokens = 300

        obs_omitted = Observation(
            execution_id="exec_tokens_omitted",
            probe_id="probe_tokens_test",
            outcome=ObservationOutcome.COMPLETED,
            evidence=[],
            tool_calls=1,
            elapsed_ms=50.0,
            total_tokens=None,
        )
        apply_observations(self.state, [obs_omitted])
        # Preserves known step tokens instead of resetting to None
        self.assertEqual(self.state.usage.total_tokens, 300)

        # Explicit observation tokens add once to existing known tokens
        obs_explicit = Observation(
            execution_id="exec_tokens_explicit",
            probe_id="probe_tokens_test",
            outcome=ObservationOutcome.COMPLETED,
            evidence=[],
            tool_calls=1,
            elapsed_ms=50.0,
            total_tokens=75,
        )
        apply_observations(self.state, [obs_explicit])
        self.assertEqual(self.state.usage.total_tokens, 375)

        # Re-applying identical execution skips idempotently without adding tokens again
        apply_observations(self.state, [obs_explicit])
        self.assertEqual(self.state.usage.total_tokens, 375)

        # Unknown remains None on observation with tokens omitted or explicit tokens
        self.state.usage.total_tokens = None
        obs_omitted_when_unk = Observation(
            execution_id="exec_tokens_omitted_unk",
            probe_id="probe_tokens_test",
            outcome=ObservationOutcome.COMPLETED,
            evidence=[],
            tool_calls=1,
            elapsed_ms=10.0,
            total_tokens=None,
        )
        apply_observations(self.state, [obs_omitted_when_unk])
        self.assertIsNone(self.state.usage.total_tokens)

        obs_explicit_when_unk = Observation(
            execution_id="exec_tokens_explicit_unk",
            probe_id="probe_tokens_test",
            outcome=ObservationOutcome.COMPLETED,
            evidence=[],
            tool_calls=1,
            elapsed_ms=10.0,
            total_tokens=50,
        )
        apply_observations(self.state, [obs_explicit_when_unk])
        self.assertIsNone(self.state.usage.total_tokens)

    def test_apply_observations_tolerant_to_unregistered_probe(self) -> None:
        obs = Observation(
            execution_id="exec_unregistered_probe",
            probe_id="probe_not_in_state",
            outcome=ObservationOutcome.COMPLETED,
            evidence=[],
            tool_calls=1,
            elapsed_ms=10.0,
        )
        # Should not raise ValueError
        res = apply_observations(self.state, [obs])
        self.assertEqual(res["appliedExecutionsCount"], 1)

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
