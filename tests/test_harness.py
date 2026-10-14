"""Tests for ResearchHarness orchestrator and T3 delegation adapter."""

import json
from pathlib import Path
import tempfile
import unittest

from ommatidia.harness import ResearchHarness
from ommatidia.seal import SealMismatchError, create_seal_manifest
from ommatidia.t3_adapter import T3DelegationAdapter, create_t3_executor
from ommatidia.types import ConditionType
from tests.fixtures.synthetic_dev_cases import get_mechanism_check_fixtures


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

        fixtures = get_mechanism_check_fixtures()
        self.task, self.gold = fixtures[0]

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_harness_environment_verification_passes_when_intact(self) -> None:
        harness = ResearchHarness(
            output_dir=self.output_dir,
            seal_manifest_path=self.manifest_file,
        )
        # verify_environment should pass without raising
        harness.verify_environment()

    def test_harness_aborts_execution_on_tampered_seal(self) -> None:
        harness = ResearchHarness(
            output_dir=self.output_dir,
            seal_manifest_path=self.manifest_file,
        )
        # Mutate protocol file
        self.protocol_file.write_text("# Tampered Protocol Content", encoding="utf-8")

        def mock_executor(step_name: str, payload: dict) -> dict:
            return {}

        with self.assertRaises(SealMismatchError):
            harness.evaluate_task(self.task, self.gold, ConditionType.A, "run_fail", mock_executor)

    def test_t3_executor_falls_back_when_adapter_unwired(self) -> None:
        fallback_called = False

        def mock_fallback(step_name: str, payload: dict) -> dict:
            nonlocal fallback_called
            fallback_called = True
            return {"answer": "fallback conclusion", "usage": {"rounds": 1}}

        executor = create_t3_executor(fallback_executor=mock_fallback)
        res = executor("single_pass", {})
        self.assertTrue(fallback_called)
        self.assertEqual(res["answer"], "fallback conclusion")


if __name__ == "__main__":
    unittest.main()
