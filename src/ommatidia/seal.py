"""Dataset and protocol sealing to guarantee evaluation integrity."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set

from ommatidia.types import validate_sha256


class SealMismatchError(ValueError):
    """Raised when a sealed dataset or protocol hash fails verification."""
    pass


def hash_file(file_path: Path) -> str:
    """Compute the SHA-256 hash of a file."""
    if not file_path.exists():
        raise FileNotFoundError(f"Cannot hash non-existent file: {file_path}")
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_string_hash(content: str) -> str:
    """Compute the SHA-256 hash of a string."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def create_seal_manifest(
    protocol_path: Path,
    dataset_paths: List[Path],
    manifest_output_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Compute hashes for protocol and datasets, creating a seal manifest."""
    manifest: Dict[str, Any] = {
        "schemaVersion": "0.1",
        "protocol": {
            "path": str(protocol_path.as_posix()),
            "hash": hash_file(protocol_path),
        },
        "datasets": {},
    }

    for path in dataset_paths:
        manifest["datasets"][str(path.as_posix())] = {
            "hash": hash_file(path),
            "sizeBytes": path.stat().st_size,
        }

    if manifest_output_path is not None:
        manifest_output_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_output_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
        )

    return manifest


def verify_seal_manifest(
    manifest_data: Dict[str, Any],
    base_dir: Optional[Path] = None,
) -> Dict[str, bool]:
    """Verify that current files on disk match the recorded seal manifest.

    Raises SealMismatchError if any hash does not match or a file is missing.
    """
    base = base_dir or Path.cwd()

    # 1. Verify protocol
    prot_info = manifest_data.get("protocol", {})
    prot_rel = Path(prot_info.get("path", ""))
    prot_path = prot_rel if prot_rel.is_absolute() else base / prot_rel
    expected_prot_hash = prot_info.get("hash", "")

    if not prot_path.exists():
        raise SealMismatchError(f"Sealed protocol file missing: {prot_path}")
    actual_prot_hash = hash_file(prot_path)
    if actual_prot_hash != expected_prot_hash:
        raise SealMismatchError(
            f"Protocol seal mismatch for {prot_path}:\n"
            f"  Expected: {expected_prot_hash}\n"
            f"  Actual:   {actual_prot_hash}"
        )

    # 2. Verify datasets
    datasets = manifest_data.get("datasets", {})
    results: Dict[str, bool] = {"protocol": True}

    for rel_path_str, meta in datasets.items():
        rel_path = Path(rel_path_str)
        file_path = rel_path if rel_path.is_absolute() else base / rel_path
        expected_hash = meta.get("hash", "")

        if not file_path.exists():
            raise SealMismatchError(f"Sealed dataset file missing: {file_path}")
        actual_hash = hash_file(file_path)
        if actual_hash != expected_hash:
            raise SealMismatchError(
                f"Dataset seal mismatch for {file_path}:\n"
                f"  Expected: {expected_hash}\n"
                f"  Actual:   {actual_hash}"
            )
        results[rel_path_str] = True

    return results


def check_heldout_leakage(
    dev_task_ids: Set[str],
    heldout_task_ids: Set[str],
    agent_visible_text: str,
    heldout_answers: Dict[str, str],
) -> List[str]:
    """Verify that no held-out task IDs or ground truth answers leak into agent-visible context.

    Returns a list of leak violations (empty if clean).
    """
    violations: List[str] = []

    # Check for ID intersection between dev and held-out
    intersection = dev_task_ids.intersection(heldout_task_ids)
    if intersection:
        violations.append(f"Task ID overlap between dev and heldout sets: {sorted(list(intersection))}")

    # Check if any heldout answers appear in the visible text
    vis_lower = agent_visible_text.lower()
    for tid, answer in heldout_answers.items():
        ans_clean = answer.strip().lower()
        if not ans_clean:
            continue
        if ans_clean in vis_lower:
            violations.append(f"Ground-truth answer for heldout task '{tid}' detected in visible text")
        else:
            # Check token n-grams for multi-word answers
            tokens = [t for t in re.split(r"\W+", ans_clean) if t]
            if len(tokens) >= 3:
                for k in range(len(tokens) - 2):
                    ngram = " ".join(tokens[k : k + 3])
                    if ngram in vis_lower:
                        violations.append(f"Ground-truth n-gram fragment '{ngram}' for heldout task '{tid}' detected in visible text")
                        break

    return violations
