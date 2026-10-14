"""Tests for RunLedger stage tracking, unknown token/cost accounting, and concurrency lock."""

import json
from pathlib import Path
import tempfile
import unittest

from ommatidia.ledger import ConcurrencyLockError, RunLedger
from ommatidia.types import ConditionType, LedgerStage, Usage


class TestRunLedger(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ledger_file = Path(self.temp_dir.name) / "test_ledger.jsonl"
        self.ledger = RunLedger(self.ledger_file)

    def tearDown(self) -> None:
        self.ledger.release_lock()
        self.temp_dir.cleanup()

    def test_unknown_costs_and_tokens_are_strictly_null(self) -> None:
        # Unknown tokens and cost must remain None (JSON null), NOT 0
        usage = Usage(
            rounds=1,
            model_calls=2,
            tool_calls=3,
            elapsed_ms=1200.0,
            total_tokens=None,  # unknown
            cost_yen=None,      # unknown
        )

        entry = self.ledger.record_stage(
            stage=LedgerStage.PLANNING,
            execution_id="exec_test_01",
            task_id="task_01",
            condition=ConditionType.E,
            input_payload_hash="1111111111111111111111111111111111111111111111111111111111111111",
            output_payload_hash="2222222222222222222222222222222222222222222222222222222222222222",
            usage=usage,
            status="completed",
            model="gemini-3.8-flash-high",
        )

        # Inspect raw JSON line in file
        raw_lines = self.ledger_file.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(raw_lines), 1)
        data = json.loads(raw_lines[0])

        self.assertIsNone(data["usage"]["totalTokens"])
        self.assertIsNone(data["usage"]["costYen"])
        self.assertNotEqual(data["usage"]["totalTokens"], 0)
        self.assertNotEqual(data["usage"]["costYen"], 0.0)

        # Read back via API
        entries = self.ledger.read_entries()
        self.assertEqual(len(entries), 1)
        self.assertIsNone(entries[0].usage.total_tokens)
        self.assertIsNone(entries[0].usage.cost_yen)

    def test_stage_tracking_and_aggregation(self) -> None:
        # Record across stages
        stages = [
            LedgerStage.PLANNING,
            LedgerStage.INVESTIGATOR,
            LedgerStage.COMMUNICATION,
            LedgerStage.RETRY,
            LedgerStage.SYNTHESIS,
        ]

        dummy_hash = "3333333333333333333333333333333333333333333333333333333333333333"
        for idx, stage in enumerate(stages):
            u = Usage(rounds=1, model_calls=1, tool_calls=2, elapsed_ms=100.0)
            self.ledger.record_stage(
                stage=stage,
                execution_id=f"exec_stage_{idx}",
                task_id="task_02",
                condition=ConditionType.E,
                input_payload_hash=dummy_hash,
                output_payload_hash=dummy_hash,
                usage=u,
                status="ok",
            )

        breakdown = self.ledger.aggregate_usage_by_stage()
        self.assertEqual(len(breakdown), 5)
        for st in stages:
            self.assertIn(st.value, breakdown)
            self.assertEqual(breakdown[st.value].tool_calls, 2)

        total = self.ledger.total_usage()
        self.assertEqual(total.rounds, 5)
        self.assertEqual(total.tool_calls, 10)

    def test_concurrency_lock_prevents_duplicate_active_run(self) -> None:
        self.ledger.acquire_lock("run_alpha")
        self.assertTrue(self.ledger.lock_path.exists())

        # Second runner attempting lock on same file must raise ConcurrencyLockError
        ledger2 = RunLedger(self.ledger_file)
        with self.assertRaises(ConcurrencyLockError):
            ledger2.acquire_lock("run_beta")

        # After releasing lock, new runner can acquire
        self.ledger.release_lock()
        ledger2.acquire_lock("run_beta")
        self.assertTrue(ledger2.lock_path.exists())
        ledger2.release_lock()


if __name__ == "__main__":
    unittest.main()
