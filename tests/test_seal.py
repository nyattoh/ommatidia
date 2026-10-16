"""Tests for protocol/dataset immutable hashing, heldout seals, and leak prevention."""

from pathlib import Path
import builtins
import hashlib
import io
import json
import os
import tempfile
import unittest

import pytest

from ommatidia import integrity
from ommatidia.harness import load_gold_standards, load_public_packets
from ommatidia.seal import (
    SealMismatchError,
    check_heldout_leakage,
    create_seal_manifest,
    hash_file,
    verify_seal_manifest,
)


PRIVATE_LOCATORS = (
    "gold/synthetic.json",
    "cases/synthetic.json",
    "unblinding_key.json",
)


@pytest.mark.parametrize("directory", ("gold", "cases"))
def test_hash_file_accepts_synthetic_private_named_files(
    synthetic_private_io_root, directory
):
    path = synthetic_private_io_root / directory / "synthetic.bin"
    path.parent.mkdir()
    content = b"Synthetic hash utility fixture\x00\xff"
    path.write_bytes(content)

    assert hash_file(path) == hashlib.sha256(content).hexdigest()


@pytest.mark.parametrize(
    "matching_hash", (True, False), ids=("correct_hash", "mismatch")
)
def test_gold_loader_verifies_manifest_hash(synthetic_private_io_root, matching_hash):
    root = synthetic_private_io_root
    path = root / "gold" / "synthetic.json"
    path.parent.mkdir()
    rubric = {
        "taskId": "synthetic_01",
        "domain": "synthetic",
        "requiredGapQuestions": [],
        "criticalEvidenceHashes": [],
        "expectedAnswerKeywords": [],
        "groundTruthVerdicts": {},
        "targetDecision": "ready_for_requested_step",
    }
    content = json.dumps(rubric).encode("utf-8")
    path.write_bytes(content)
    expected = hashlib.sha256(content).hexdigest() if matching_hash else "0" * 64
    (root / "manifest.json").write_text(
        json.dumps({"files": {"gold/synthetic.json": {"hash": expected}}}),
        encoding="utf-8",
    )

    if matching_hash:
        loaded = load_gold_standards(root, verify_hashes=True)
        assert set(loaded) == {"synthetic_01"}
        assert loaded["synthetic_01"].to_dict() == rubric
    else:
        with pytest.raises(ValueError, match="Hash mismatch for gold synthetic.json"):
            load_gold_standards(root, verify_hashes=True)


@pytest.fixture
def watch_private_open(monkeypatch):
    """Observe attempted opens independently of the autouse safety guard."""

    def watch(target):
        opened = []
        target = target.resolve()
        original_exists = Path.exists

        def exists(path):
            return True if path.resolve() == target else original_exists(path)

        def spy(function):
            def checked(path, *args, **kwargs):
                if isinstance(path, (str, bytes, os.PathLike)):
                    if Path(os.fsdecode(path)).resolve() == target:
                        opened.append(target)
                        raise AssertionError(
                            "Runtime attempted to open a private target"
                        )
                return function(path, *args, **kwargs)

            return checked

        monkeypatch.setattr(Path, "exists", exists)
        for module in (builtins, io, os):
            monkeypatch.setattr(module, "open", spy(module.open))
        return opened

    return watch


@pytest.mark.parametrize("locator", PRIVATE_LOCATORS)
@pytest.mark.parametrize("slot", ("protocol", "dataset"))
def test_verify_seal_rejects_private_target_before_open(
    tmp_path, watch_private_open, locator, slot
):
    protocol = tmp_path / "protocol.md"
    protocol.write_bytes(b"public protocol")
    manifest = {
        "protocol": {
            "path": "protocol.md",
            "hash": hashlib.sha256(b"public protocol").hexdigest(),
        },
        "datasets": {},
    }
    if slot == "protocol":
        manifest["protocol"] = {"path": locator, "hash": "0" * 64}
    else:
        manifest["datasets"][locator] = {"hash": "0" * 64}
    opened = watch_private_open(tmp_path / locator)

    with pytest.raises(ValueError, match="[Pp]rivate|[Pp]ublic"):
        verify_seal_manifest(manifest, base_dir=tmp_path)
    assert opened == []


@pytest.mark.parametrize("locator", PRIVATE_LOCATORS)
@pytest.mark.parametrize("slot", ("protocol", "dataset"))
def test_create_seal_rejects_private_target_before_open(
    tmp_path, watch_private_open, locator, slot
):
    protocol = tmp_path / "protocol.md"
    protocol.write_bytes(b"public protocol")
    target = tmp_path / locator
    opened = watch_private_open(target)

    with pytest.raises(ValueError, match="[Pp]rivate|[Pp]ublic"):
        create_seal_manifest(
            target if slot == "protocol" else protocol,
            [target] if slot == "dataset" else [],
        )
    assert opened == []


@pytest.mark.parametrize("locator", PRIVATE_LOCATORS)
@pytest.mark.parametrize("slot", ("history", "historicalCore"))
def test_runtime_freeze_rejects_private_history_before_open(
    tmp_path, monkeypatch, watch_private_open, locator, slot
):
    current = {
        "codeHash": "synthetic",
        "promptHash": "synthetic",
        "specHash": "synthetic",
        "files": {},
        "prompts": {},
    }
    manifest = tmp_path / "freeze.json"
    manifest.write_text(
        json.dumps({**current, slot: {locator: "0" * 64}}), encoding="utf-8"
    )
    monkeypatch.setattr(integrity, "fingerprints", lambda root: current)
    opened = watch_private_open(tmp_path / locator)

    with pytest.raises(ValueError, match="[Pp]rivate|[Pp]ublic"):
        integrity.verify_runtime_freeze(manifest, root=tmp_path)
    assert opened == []


@pytest.mark.parametrize("locator", PRIVATE_LOCATORS)
def test_runtime_freeze_rejects_private_manifest_before_open(
    tmp_path, watch_private_open, locator
):
    target = tmp_path / locator
    opened = watch_private_open(target)

    with pytest.raises(ValueError, match="[Pp]rivate|[Pp]ublic"):
        integrity.verify_runtime_freeze(target, root=tmp_path)
    assert opened == []


@pytest.mark.parametrize("locator", PRIVATE_LOCATORS)
def test_runtime_fingerprints_reject_private_code_input_before_open(
    tmp_path, monkeypatch, watch_private_open, locator
):
    monkeypatch.setattr(integrity, "CORE", [])
    monkeypatch.setattr(integrity, "DRIVER", [])
    monkeypatch.setattr(integrity, "SPEC", [locator])
    opened = watch_private_open(tmp_path / locator)

    with pytest.raises(ValueError, match="[Pp]rivate|[Pp]ublic"):
        integrity.fingerprints(tmp_path)
    assert opened == []


@pytest.mark.parametrize("locator", PRIVATE_LOCATORS)
def test_public_loader_rejects_private_partition_before_open(
    tmp_path, watch_private_open, locator
):
    target = tmp_path / locator
    opened = watch_private_open(target)

    with pytest.raises(ValueError, match="[Pp]rivate|[Pp]ublic"):
        load_public_packets(target, expected_count=None)
    assert opened == []


@pytest.mark.parametrize("locator", PRIVATE_LOCATORS)
def test_command_runner_rejects_private_target_before_open(
    tmp_path, watch_private_open, locator
):
    from scripts.run_harness import reject_private_path

    target = tmp_path / locator
    opened = watch_private_open(target)

    with pytest.raises(ValueError, match="Private evaluation asset path"):
        reject_private_path(target)
    assert opened == []


def test_synthetic_private_opt_in_still_forbids_keys(synthetic_private_io_root):
    with pytest.raises(AssertionError, match="must not access private"):
        (synthetic_private_io_root / "unblinding_key.json").read_bytes()


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
        violations = check_heldout_leakage(
            dev_ids, heldout_ids, clean_text, heldout_answers
        )
        self.assertEqual(len(violations), 0)

        # 2. Overlapping task ID
        leaky_dev_ids = {"dev_01", "heldout_01"}
        violations_id = check_heldout_leakage(
            leaky_dev_ids, heldout_ids, clean_text, heldout_answers
        )
        self.assertTrue(any("Task ID overlap" in v for v in violations_id))

        # 3. Leaked heldout answer
        leaked_text = "Here is the hint: secret_solution_token_xyz"
        violations_ans = check_heldout_leakage(
            dev_ids, heldout_ids, leaked_text, heldout_answers
        )
        self.assertTrue(
            any("Ground-truth answer for heldout task" in v for v in violations_ans)
        )


if __name__ == "__main__":
    unittest.main()
