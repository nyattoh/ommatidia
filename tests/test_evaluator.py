"""Tests for objective scoring, metric exact denominators, and paired comparisons."""

import unittest

from ommatidia.evaluator import compute_paired_differences, score_run_objectively
from ommatidia.state import create_initial_state
from ommatidia.types import (
    Claim,
    ClaimRole,
    ClaimStatus,
    ConditionType,
    Decision,
    EvaluationMetricRecord,
    Gap,
    GapImportance,
    GapKind,
    GapStatus,
    Resolution,
    ResolutionReason,
    Usage,
)
from tests.fixtures.synthetic_dev_cases import get_mechanism_check_fixtures


class TestObjectiveEvaluator(unittest.TestCase):
    def setUp(self) -> None:
        fixtures = get_mechanism_check_fixtures()
        self.task, self.gold = fixtures[0]
        self.state = create_initial_state(self.task)

    def test_objective_scoring_exact_denominators(self) -> None:
        # Match target decision
        self.state.decision = Decision.READY_FOR_REQUESTED_STEP

        # Add gap matching gold required question with valid resolution:
        res = Resolution(
            reason=ResolutionReason.SUPPORTED,
            evidence_ids=[self.task.evidence[0].id],
            explanation="Broadcast without receipt verified",
        )
        gap = Gap(
            id="gap_async_01",
            kind=GapKind.MISSING_FACT,
            lens_id="lens_test",
            question="Does asynchronous broadcast guarantee secondary copy invalidation?",
            trigger_refs=["spec"],
            why_it_matters="Cache consistency",
            importance=GapImportance.REQUIRED,
            claim_ids=[],
            status=GapStatus.RESOLVED,
            resolution=res,
        )
        self.state.gaps.append(gap)

        # Add claim matching ground truth contradiction:
        # "claim_dev_mech_cache_01_01" -> "contradicted"
        claim = Claim(
            id="claim_dev_mech_cache_01_01",
            role=ClaimRole.ANSWER_CLAIM,
            text="Cache is consistent",
            scope="cache",
            status=ClaimStatus.CONTRADICTED,
        )
        self.state.claims.append(claim)

        record = score_run_objectively(
            state=self.state,
            gold=self.gold,
            run_id="run_eval_01",
            condition=ConditionType.E,
        )

        self.assertEqual(record.final_decision_success, 1)
        # Denominator = 1, identified = 1 -> recall = 1.0
        self.assertEqual(record.required_gap_recall, 1.0)
        self.assertEqual(record.contradiction_detection_rate, 1.0)
        self.assertEqual(record.valid_evidence_count, 1)

    def test_paired_differences_and_small_sample_uncertainty(self) -> None:
        rec_e_1 = EvaluationMetricRecord(
            task_id="task_01",
            condition=ConditionType.E,
            run_id="r1",
            final_decision_success=1,
            required_gap_recall=1.0,
            unnecessary_check_rate=0.0,
            valid_evidence_count=3,
            contradiction_detection_rate=1.0,
            usage=Usage(),
        )
        rec_d_1 = EvaluationMetricRecord(
            task_id="task_01",
            condition=ConditionType.D,
            run_id="r2",
            final_decision_success=0,
            required_gap_recall=0.5,
            unnecessary_check_rate=0.2,
            valid_evidence_count=2,
            contradiction_detection_rate=0.0,
            usage=Usage(),
        )

        paired = compute_paired_differences([rec_e_1], [rec_d_1], metric_name="final_decision_success")
        self.assertEqual(paired["n"], 1)
        self.assertEqual(paired["differences"], [1.0])
        self.assertEqual(paired["meanDifference"], 1.0)
        self.assertIn("Small sample size", paired["smallSampleNote"])


if __name__ == "__main__":
    unittest.main()
