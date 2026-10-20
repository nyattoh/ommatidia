"""Tests for ResearchHarness orchestrator and T3 delegation adapter."""

import json
from pathlib import Path
import tempfile
import unittest

from ommatidia.harness import (
    GlobalResourceRegistry,
    ResearchHarness,
    ResourceLimitExceeded,
    TrialRecord,
    compute_exact_mcnemar,
    compute_holm_bonferroni,
    export_masked_assessor_dataset,
    get_completed_trial_keys,
    load_public_packets,
)
from ommatidia.seal import SealMismatchError, create_seal_manifest
from ommatidia.t3_adapter import (
    T3DelegationAdapter,
    T3DelegationError,
    create_t3_executor,
    export_campaign_dispatch_plan,
)
from ommatidia.types import ConditionType, Usage
from tests.fixtures.synthetic_dev_cases import get_mechanism_check_fixtures
from tests.freeze_fixture import clean_git_status, write_current_freeze


class TestResearchHarness(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base = Path(self.temp_dir.name)
        self.output_dir = self.base / "output"
        self.protocol_file = self.base / "PROTOCOL.md"
        self.protocol_file.write_text("# Test Protocol", encoding="utf-8")
        self.dataset_file = self.base / "dataset.json"
        self.dataset_file.write_text("{}", encoding="utf-8")

        self.manifest_file = self.base / "seal_manifest.json"
        create_seal_manifest(
            protocol_path=self.protocol_file,
            dataset_paths=[self.dataset_file],
            manifest_output_path=self.manifest_file,
        )

        self.freeze_file = write_current_freeze(self.base)

        fixtures = get_mechanism_check_fixtures()
        self.task, self.gold = fixtures[0]

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_harness_environment_verification_passes_when_intact(self) -> None:
        harness = ResearchHarness(
            output_dir=self.output_dir,
            seal_manifest_path=self.manifest_file,
            runtime_freeze_path=self.freeze_file,
        )
        # verify_environment should pass without raising
        harness.verify_environment()

    def test_harness_aborts_execution_on_tampered_seal(self) -> None:
        harness = ResearchHarness(
            output_dir=self.output_dir,
            seal_manifest_path=self.manifest_file,
            runtime_freeze_path=self.freeze_file,
        )
        # Mutate protocol file
        self.protocol_file.write_text("# Tampered Protocol Content", encoding="utf-8")

        def mock_executor(step_name: str, payload: dict) -> dict:
            return {}

        with self.assertRaises(SealMismatchError):
            harness.evaluate_task(
                self.task, self.gold, ConditionType.A, "run_fail", mock_executor
            )

    def test_t3_executor_fails_closed_when_unwired_and_no_fallback(self) -> None:
        executor = create_t3_executor(fallback_executor=None)
        with self.assertRaises(T3DelegationError):
            executor("single_pass", {})

    def test_t3_executor_calls_fallback_only_when_explicitly_configured(self) -> None:
        fallback_called = False

        def mock_fallback(step_name: str, payload: dict) -> dict:
            nonlocal fallback_called
            fallback_called = True
            return {
                "answer": "fallback conclusion",
                "usage": {"rounds": 1, "modelCalls": 1, "toolCalls": 0, "costYen": 0.0},
            }

        executor = create_t3_executor(fallback_executor=mock_fallback)
        res = executor("single_pass", {})
        self.assertTrue(fallback_called)
        self.assertEqual(res["answer"], "fallback conclusion")

    def test_load_public_packets_from_dev_isolates_gold(self) -> None:
        dev_dir = Path("research/datasets/dev")
        if not dev_dir.exists():
            self.skipTest("Dev dataset directory not present")

        packets = load_public_packets(dev_dir, verify_hashes=True, expected_count=24)
        self.assertEqual(len(packets), 24)

        for p in packets:
            self.assertTrue(p.task_id.startswith("dev_"))
            # Confirm no gold evaluation fields exist in public packets
            self.assertFalse(hasattr(p, "required_gap_questions"))
            self.assertFalse(hasattr(p, "ground_truth_verdicts"))
            self.assertFalse(hasattr(p, "critical_evidence_hashes"))

    def test_global_resource_registry_enforces_aggregate_ceiling(self) -> None:
        reg = GlobalResourceRegistry(max_aggregate_model_calls=10)
        u = Usage(model_calls=6)
        reg.record_step("step1", u)
        self.assertEqual(reg.total_model_calls, 6)

        # Exceed ceiling on next step
        u2 = Usage(model_calls=5)
        with self.assertRaises(ResourceLimitExceeded):
            reg.record_step("step2", u2)

    def test_global_resource_registry_rejects_negative_usage(self) -> None:
        reg = GlobalResourceRegistry()
        u_bad = Usage(model_calls=-10)
        with self.assertRaises(ValueError):
            reg.record_step("bad_step", u_bad)

    def test_global_resource_registry_enforces_trial_cap(self) -> None:
        reg = GlobalResourceRegistry(max_trial_model_calls=8)
        trial_u = Usage(model_calls=9)
        with self.assertRaises(ResourceLimitExceeded):
            reg.record_step("step1", Usage(model_calls=1), trial_usage=trial_u)

    def test_global_resource_registry_atomic_persistence(self) -> None:
        reg_file = self.output_dir / "resource_registry.json"
        reg = GlobalResourceRegistry(storage_path=reg_file)
        reg.record_step("step1", Usage(model_calls=3, tool_calls=2))
        self.assertTrue(reg_file.exists())

        reg2 = GlobalResourceRegistry()
        reg2.load_from_path(reg_file)
        self.assertEqual(reg2.total_model_calls, 3)
        self.assertEqual(reg2.total_tool_calls, 2)

    def test_robust_resume_skips_completed_trials_with_matching_executor(self) -> None:
        harness = ResearchHarness(
            output_dir=self.output_dir,
            seal_manifest_path=self.manifest_file,
            runtime_freeze_path=self.freeze_file,
        )

        call_count = 0

        def mock_executor(step_name: str, payload: dict) -> dict:
            nonlocal call_count
            call_count += 1
            return {
                "answer": "done",
                "usage": {"rounds": 1, "modelCalls": 1, "toolCalls": 0, "costYen": 0.0},
            }

        mock_executor.synthetic_only = True

        # First run executes
        records1 = harness.run_cohort(
            tasks=[self.task],
            conditions=[ConditionType.A],
            run_id="run_resume_test",
            executor_func=mock_executor,
            partition="test_part",
            resume=True,
            executor_name="synthetic",
        )
        self.assertEqual(len(records1), 1)
        self.assertEqual(call_count, 1)

        # Second run with resume skips execution
        records2 = harness.run_cohort(
            tasks=[self.task],
            conditions=[ConditionType.A],
            run_id="run_resume_test",
            executor_func=mock_executor,
            partition="test_part",
            resume=True,
            executor_name="synthetic",
        )
        self.assertEqual(len(records2), 1)
        self.assertEqual(call_count, 1)  # Still 1, skipped!

    def test_resume_rejects_mismatched_executor(self) -> None:
        harness = ResearchHarness(
            output_dir=self.output_dir,
            seal_manifest_path=self.manifest_file,
            runtime_freeze_path=self.freeze_file,
        )

        call_count = 0

        def mock_executor(step_name: str, payload: dict) -> dict:
            nonlocal call_count
            call_count += 1
            return {
                "answer": "done",
                "usage": {"rounds": 1, "modelCalls": 1, "toolCalls": 0, "costYen": 0.0},
            }

        mock_executor.synthetic_only = True

        # First run as synthetic
        harness.run_cohort(
            tasks=[self.task],
            conditions=[ConditionType.A],
            run_id="run_mismatch_test",
            executor_func=mock_executor,
            partition="test_part",
            resume=True,
            executor_name="synthetic",
        )
        self.assertEqual(call_count, 1)

        # An incompatible record is preserved, rather than overwritten by a new executor.
        harness.runtime_freeze_path = write_current_freeze(self.base, release_ready=True)
        with clean_git_status():
            with self.assertRaisesRegex(ValueError, "provenance mismatch"):
                harness.run_cohort(
                    tasks=[self.task],
                    conditions=[ConditionType.A],
                    run_id="run_mismatch_test",
                    executor_func=mock_executor,
                    partition="test_part",
                    resume=True,
                    executor_name="t3",
                )
        self.assertEqual(call_count, 1)

    def test_failed_trial_recorded_and_stays_in_denominator(self) -> None:
        harness = ResearchHarness(
            output_dir=self.output_dir,
            seal_manifest_path=self.manifest_file,
            runtime_freeze_path=self.freeze_file,
        )

        def failing_executor(step_name: str, payload: dict) -> dict:
            raise RuntimeError("Synthetic delegation network failure")

        failing_executor.synthetic_only = True

        rec = harness.evaluate_task(
            task=self.task,
            gold=self.gold,
            condition=ConditionType.A,
            run_id="run_fail_test",
            executor_func=failing_executor,
            executor_name="synthetic",
        )
        self.assertEqual(rec.status, "failed")
        self.assertEqual(rec.decision, "failed")
        self.assertIn("Synthetic delegation network failure", rec.error_message or "")
        self.assertIsNotNone(rec.final_judgement)
        self.assertEqual(rec.final_judgement.verdict, "inconclusive")
        self.assertEqual(rec.final_judgement.confidence_score, 0.0)

    def test_export_masked_assessor_dataset_strips_usage_fingerprints(self) -> None:
        records = [
            TrialRecord(
                task_id="dev_01",
                condition=ConditionType.E,
                run_id="r1",
                status="completed",
                usage=Usage(model_calls=2, tool_calls=3, elapsed_ms=100.0),
            ),
            TrialRecord(
                task_id="dev_01",
                condition=ConditionType.D,
                run_id="r1",
                status="completed",
                usage=Usage(model_calls=1, tool_calls=2, elapsed_ms=80.0),
            ),
        ]

        set_path, key_path = export_masked_assessor_dataset(
            records, self.output_dir, seed=123
        )
        self.assertTrue(set_path.exists())
        self.assertTrue(key_path.exists())

        masked_data = json.loads(set_path.read_text(encoding="utf-8"))
        self.assertEqual(len(masked_data), 2)
        # Condition should be masked to MCOND_xx
        self.assertTrue(masked_data[0]["maskedConditionId"].startswith("MCOND_"))
        # Trial ID should be a UUID
        self.assertEqual(len(masked_data[0]["maskedTrialId"]), 36)
        # Usage must be strictly stripped from masked evaluation set
        self.assertNotIn("usage", masked_data[0])

        self.assertNotEqual(key_path.parent, set_path.parent)

    def test_exact_mcnemar_and_holm_bonferroni(self) -> None:
        # McNemar concordant: b=0, c=0 -> p=1.0
        self.assertEqual(compute_exact_mcnemar(0, 0), 1.0)
        # Discordant b=8, c=0 -> 2 * (0.5^8) = 2/256 = 0.0078125
        p = compute_exact_mcnemar(8, 0)
        self.assertAlmostEqual(p, 0.0078125)

        # Holm-Bonferroni correction
        raw_p = [0.01, 0.04, 0.03, 0.05]
        adj = compute_holm_bonferroni(raw_p)
        self.assertEqual(len(adj), 4)
        self.assertAlmostEqual(adj[0], 0.04)  # 0.01 * 4

    def test_export_campaign_dispatch_plan_generates_jobs(self) -> None:
        plan_file = self.output_dir / "test_plan.json"
        jobs = export_campaign_dispatch_plan(
            tasks=[self.task],
            conditions=[ConditionType.A, ConditionType.E],
            run_id="run_plan_test",
            output_path=plan_file,
        )
        # Condition A has 1 step; Condition E has 3 steps (coord, inv, synth) -> total 4 jobs
        self.assertEqual(len(jobs), 4)
        self.assertTrue(plan_file.exists())
        self.assertEqual(jobs[0]["target"]["model"], "gemini-3.8-flash-high")
        self.assertEqual(jobs[0]["target"]["providerInstanceId"], "agy")
        self.assertIn("ommatidia_", jobs[0]["clientRequestId"])
        self.assertIn("schema", jobs[0])


if __name__ == "__main__":
    unittest.main()
