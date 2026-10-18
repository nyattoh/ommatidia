"""Fail-closed manifest coverage using temporary synthetic gold only."""

import hashlib
import json

import pytest

from ommatidia.harness import load_gold_standards
from ommatidia.types import Decision, GoldStandard

UNVERIFIED_MANIFESTS = (
    "unlisted",
    "absent",
    "empty_manifest",
    "empty_files",
    "missing_hash",
    "empty_hash",
    "null_hash",
)


def write_gold(root, name="synthetic.json", keyword="sealed"):
    gold = GoldStandard(
        task_id="synthetic_manifest_01",
        domain="synthetic",
        required_gap_questions=[],
        critical_evidence_hashes=[],
        expected_answer_keywords=[keyword],
        ground_truth_verdicts={},
        target_decision=Decision.READY_FOR_REQUESTED_STEP,
    )
    path = root / "gold" / name
    path.parent.mkdir(exist_ok=True)
    content = json.dumps(gold.to_dict()).encode("utf-8")
    path.write_bytes(content)
    return gold, hashlib.sha256(content).hexdigest()


def write_manifest(root, files):
    (root / "manifest.json").write_text(
        json.dumps({"files": files}), encoding="utf-8"
    )


def write_unverified_manifest(root, mode):
    if mode == "absent":
        return
    if mode == "empty_manifest":
        (root / "manifest.json").write_text("{}", encoding="utf-8")
        return
    files = {
        "unlisted": {"gold/other.json": {"hash": "0" * 64}},
        "empty_files": {},
        "missing_hash": {"gold/synthetic.json": {}},
        "empty_hash": {"gold/synthetic.json": {"hash": ""}},
        "null_hash": {"gold/synthetic.json": {"hash": None}},
    }[mode]
    write_manifest(root, files)


@pytest.mark.parametrize("mode", UNVERIFIED_MANIFESTS)
def test_verified_loading_rejects_missing_manifest_hash(
    synthetic_private_io_root, mode
):
    root = synthetic_private_io_root
    write_gold(root)
    write_unverified_manifest(root, mode)

    with pytest.raises((ValueError, FileNotFoundError)):
        load_gold_standards(root, verify_hashes=True)


def test_unlisted_duplicate_cannot_overwrite_verified_gold(synthetic_private_io_root):
    root = synthetic_private_io_root
    sealed, digest = write_gold(root, "a_sealed.json")
    write_manifest(root, {"gold/a_sealed.json": {"hash": digest}})
    assert load_gold_standards(root, verify_hashes=True) == {sealed.task_id: sealed}
    duplicate, _ = write_gold(root, "z_unlisted.json", keyword="unverified")
    assert duplicate.task_id == sealed.task_id
    assert duplicate != sealed

    with pytest.raises(ValueError):
        load_gold_standards(root, verify_hashes=True)


def test_listed_correct_hash_loads_exact_gold(synthetic_private_io_root):
    root = synthetic_private_io_root
    gold, digest = write_gold(root)
    write_manifest(root, {"gold/synthetic.json": {"hash": digest}})

    assert load_gold_standards(root, verify_hashes=True) == {gold.task_id: gold}


def test_listed_mismatch_reports_hash_error(synthetic_private_io_root):
    root = synthetic_private_io_root
    _, digest = write_gold(root)
    wrong_digest = "0" * 64
    assert wrong_digest != digest
    write_manifest(root, {"gold/synthetic.json": {"hash": wrong_digest}})

    with pytest.raises(ValueError, match="Hash mismatch for gold synthetic.json"):
        load_gold_standards(root, verify_hashes=True)


@pytest.mark.parametrize("mode", (*UNVERIFIED_MANIFESTS, "mismatch"))
def test_explicit_unverified_loading_remains_compatible(
    synthetic_private_io_root, mode
):
    root = synthetic_private_io_root
    gold, _ = write_gold(root)
    if mode == "mismatch":
        write_manifest(root, {"gold/synthetic.json": {"hash": "0" * 64}})
    else:
        write_unverified_manifest(root, mode)

    assert load_gold_standards(root, verify_hashes=False) == {gold.task_id: gold}
