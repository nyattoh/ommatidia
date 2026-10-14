"""Tests for objective scoring, metric exact denominators, and paired comparisons."""

import unittest

from ommatidia.evaluator import (
    compute_paired_differences,
    compute_wilcoxon_signed_rank,
    score_run_objectively,
    wilson_score_interval_cc,
)
from ommatidia.state import create_initial_state
from ommatidia.types import (
    Claim,
    ClaimRole,
    ClaimStatus,
    ConditionType,
    Decision,
    EvaluationMetricRecord,
    FinalJudgement,
    FinalJudgementResourceUsage,
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
        self.assertEqual(record.fda, 1)
        self.assertEqual(record.required_gap_recall, 1.0)
        self.assertEqual(record.recall_crit, 1.0)
        self.assertEqual(record.contradiction_detection_rate, 1.0)
        self.assertEqual(record.valid_evidence_count, 1)
        self.assertIsNotNone(record.final_judgement)

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

    def test_paired_differences_zero_variance_does_not_emit_misleading_zero_ci(self) -> None:
        rec_e_1 = EvaluationMetricRecord("task_01", ConditionType.E, "r1", 1, 1.0, 0.0, 1, 1.0, Usage())
        rec_e_2 = EvaluationMetricRecord("task_02", ConditionType.E, "r2", 1, 1.0, 0.0, 1, 1.0, Usage())
        rec_d_1 = EvaluationMetricRecord("task_01", ConditionType.D, "r3", 1, 1.0, 0.0, 1, 1.0, Usage())
        rec_d_2 = EvaluationMetricRecord("task_02", ConditionType.D, "r4", 1, 1.0, 0.0, 1, 1.0, Usage())

        paired = compute_paired_differences([rec_e_1, rec_e_2], [rec_d_1, rec_d_2], metric_name="final_decision_success")
        self.assertEqual(paired["n"], 2)
        self.assertEqual(paired["differences"], [0.0, 0.0])
        self.assertIsNone(paired["ci95"])
        self.assertIn("Confidence interval undefined", paired["ciNote"])

    def test_wilson_score_interval_cc(self) -> None:
        # Zero successes
        lower_0, upper_0 = wilson_score_interval_cc(0, 20)
        self.assertEqual(lower_0, 0.0)
        self.assertGreater(upper_0, 0.0)

        # Full successes
        lower_full, upper_full = wilson_score_interval_cc(20, 20)
        self.assertLess(lower_full, 1.0)
        self.assertEqual(upper_full, 1.0)

        # 12 / 24
        lower_mid, upper_mid = wilson_score_interval_cc(12, 24)
        self.assertAlmostEqual(lower_mid + upper_mid, 1.0, places=5)
        self.assertGreater(lower_mid, 0.25)
        self.assertLess(upper_mid, 0.75)

    def test_wilcoxon_signed_rank_less_than_6_inconclusive(self) -> None:
        diffs = [1.0, -1.0, 0.0, 0.0, 2.0]  # only 3 non-zero diffs
        res = compute_wilcoxon_signed_rank(diffs)
        self.assertFalse(res["computable"])
        self.assertEqual(res["verdict"], "inconclusive")
        self.assertEqual(res["nR"], 3)

    def test_wilcoxon_signed_rank_exact_calculation(self) -> None:
        # 8 non-zero pairs, all positive -> large positive z-score
        diffs = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
        res = compute_wilcoxon_signed_rank(diffs)
        self.assertTrue(res["computable"])
        self.assertEqual(res["nR"], 8)
        self.assertEqual(res["wMinus"], 0.0)
        self.assertEqual(res["wPlus"], 36.0)
        self.assertGreater(res["zScore"], 2.0)
        self.assertEqual(res["verdict"], "significant")


if __name__ == "__main__":
    unittest.main()
