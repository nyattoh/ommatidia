"""Tests for protocol/dataset immutable hashing, heldout seals, and leak prevention."""

from pathlib import Path
import tempfile
import unittest

from ommatidia.seal import (
    SealMismatchError,
    check_heldout_leakage,
    create_seal_manifest,
    verify_seal_manifest,
)


class TestSealVerification(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base = Path(self.temp_dir.name)

        self.protocol_file = self.base / "PROTOCOL.md"
        self.protocol_file.write_text("# Experimental Protocol v1.0", encoding="utf-8")

        self.dataset_file = self.base / "dev_cases.json"
        self.dataset_file.write_text('{"cases": []}', encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_create_and_verify_seal_manifest(self) -> None:
        manifest = create_seal_manifest(
            protocol_path=self.protocol_file,
            dataset_paths=[self.dataset_file],
        )

        # Verification passes on unmodified files
        res = verify_seal_manifest(manifest, base_dir=self.base)
        self.assertTrue(res["protocol"])

    def test_seal_mismatch_detected_on_protocol_tampering(self) -> None:
        manifest = create_seal_manifest(
            protocol_path=self.protocol_file,
            dataset_paths=[self.dataset_file],
        )

        # Alter protocol file
        self.protocol_file.write_text("# Tampered Protocol", encoding="utf-8")

        with self.assertRaises(SealMismatchError) as ctx:
            verify_seal_manifest(manifest, base_dir=self.base)
        self.assertIn("Protocol seal mismatch", str(ctx.exception))

    def test_seal_mismatch_detected_on_dataset_tampering(self) -> None:
        manifest = create_seal_manifest(
            protocol_path=self.protocol_file,
            dataset_paths=[self.dataset_file],
        )

        # Alter dataset file
        self.dataset_file.write_text('{"cases": ["tampered"]}', encoding="utf-8")

        with self.assertRaises(SealMismatchError) as ctx:
            verify_seal_manifest(manifest, base_dir=self.base)
        self.assertIn("Dataset seal mismatch", str(ctx.exception))

    def test_heldout_leakage_detection(self) -> None:
        dev_ids = {"dev_01", "dev_02"}
        heldout_ids = {"heldout_01", "heldout_02"}
        heldout_answers = {
            "heldout_01": "secret_solution_token_xyz",
            "heldout_02": "another_private_key_value",
        }

        # 1. Clean visible text
        clean_text = "Standard task description for dev_01"
        violations = check_heldout_leakage(dev_ids, heldout_ids, clean_text, heldout_answers)
        self.assertEqual(len(violations), 0)

        # 2. Overlapping task ID
        leaky_dev_ids = {"dev_01", "heldout_01"}
        violations_id = check_heldout_leakage(leaky_dev_ids, heldout_ids, clean_text, heldout_answers)
        self.assertTrue(any("Task ID overlap" in v for v in violations_id))

        # 3. Leaked heldout answer
        leaked_text = "Here is the hint: secret_solution_token_xyz"
        violations_ans = check_heldout_leakage(dev_ids, heldout_ids, leaked_text, heldout_answers)
        self.assertTrue(any("Ground-truth answer for heldout task" in v for v in violations_ans))


if __name__ == "__main__":
    unittest.main()
