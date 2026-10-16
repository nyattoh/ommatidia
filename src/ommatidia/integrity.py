"""Versioned runtime fingerprints without inspecting evaluation answers."""

from pathlib import Path
import hashlib
import json
import subprocess

from ommatidia import conditions
from ommatidia.seal import SealMismatchError, hash_file

ROOT = Path(__file__).resolve().parents[2]
CORE = ["conditions.py", "types.py", "evaluator.py"]
DRIVER = ["campaign.py", "contracts.py", "runtime.py", "scoring.py", "integrity.py", "harness.py",
          "t3_adapter.py", "ingestion.py", "state.py", "invalidation.py", "ledger.py", "seal.py"]
SPEC = ["research/PROTOCOL.md", "research/EVALUATION_SPEC.md"]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def fingerprints(root=ROOT):
    files = ["src/ommatidia/" + name for name in CORE + DRIVER]
    files += SPEC + ["scripts/run_harness.py", "scripts/verify_seals.py", "pyproject.toml"]
    hashes = {name: hash_file(root / name) for name in files}
    prompts = {name: hashlib.sha256(getattr(conditions, name).encode()).hexdigest()
               for name in dir(conditions) if name.startswith("PROMPT_")}
    from ommatidia.runtime import DISPATCH_INSTRUCTION, condition_graph
    from ommatidia.types import ConditionType
    prompts["dispatchInstruction"] = hashlib.sha256(DISPATCH_INSTRUCTION.encode()).hexdigest()
    prompts["executableGraph"] = digest({condition.value: [
        {"name": step.name, "prompt": step.prompt, "schema": step.schema, "lens": step.lens}
        for step in condition_graph(condition)] for condition in ConditionType})
    return {"codeHash": digest(hashes), "promptHash": digest(prompts),
            "specHash": digest({name: hashes[name] for name in SPEC}),
            "files": hashes, "prompts": prompts}


def verify_runtime_freeze(path, root=ROOT, require_release=False):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    current = fingerprints(root)
    for key in ("codeHash", "promptHash", "specHash", "files", "prompts"):
        if data.get(key) != current[key]:
            raise SealMismatchError(f"Runtime freeze mismatch: {key}")
    for name, expected in data.get("history", {}).items():
        if hash_file(root / name) != expected:
            raise SealMismatchError(f"Historical freeze changed: {name}")
    for name, expected in data.get("historicalCore", {}).items():
        if hash_file(root / name) != expected:
            raise SealMismatchError(f"Historical experimental core changed: {name}")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    base = subprocess.check_output(["git", "rev-parse", data["baseCommit"]], cwd=root, text=True).strip()
    if head != base:
        raise SealMismatchError("baseCommit differs from HEAD")
    if require_release:
        if data.get("evaluationPackageStatus") != "rebuilt_and_approved":
            raise SealMismatchError("Replacement evaluation package is required after boundary violation")
        if subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=all", "--ignore-submodules=none"],
            cwd=root, text=True,
        ).strip():
            raise SealMismatchError("Study execution requires a committed, clean freeze")
    return current
