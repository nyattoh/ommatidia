"""Versioned runtime fingerprints without inspecting evaluation answers."""

from pathlib import Path
import hashlib
import json
import subprocess

from ommatidia import conditions
from ommatidia.seal import (
    SealMismatchError,
    ensure_non_private_asset_path,
    hash_file,
)

ROOT = Path(__file__).resolve().parents[2]
CORE = ["conditions.py", "types.py", "evaluator.py"]
DRIVER = ["campaign.py", "contracts.py", "runtime.py", "scoring.py", "integrity.py", "harness.py",
          "t3_adapter.py", "ingestion.py", "state.py", "invalidation.py", "ledger.py", "seal.py"]
SPEC = ["research/PROTOCOL.md", "research/EVALUATION_SPEC.md"]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _hash_runtime_file(path):
    return hash_file(ensure_non_private_asset_path(path))


def fingerprints(root=ROOT):
    files = ["src/ommatidia/" + name for name in CORE + DRIVER]
    files += SPEC + ["scripts/run_harness.py", "scripts/verify_seals.py", "pyproject.toml"]
    hashes = {name: _hash_runtime_file(root / name) for name in files}
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


def _verify_committed_freeze_bytes(root, head, name, freeze_bytes, allow_untracked=False):
    entry = subprocess.check_output(
        ["git", "ls-tree", "-z", head, "--", f":(literal){name}"], cwd=root,
    )
    if not entry and allow_untracked:
        return
    metadata, separator, entry_name = entry.partition(b"\t")
    fields = metadata.split()
    if (not separator or entry_name != name.encode("utf-8") + b"\0"
            or len(fields) != 3 or fields[0] not in (b"100644", b"100755")
            or fields[1] != b"blob"):
        raise SealMismatchError("Committed freeze must be a tracked regular file")
    committed = subprocess.check_output(
        ["git", "cat-file", "blob", fields[2].decode("ascii")], cwd=root,
    )
    if committed != freeze_bytes:
        raise SealMismatchError("Supplied freeze differs from committed freeze")


def _verify_freeze_commit(root, head, base, freeze_path, freeze_bytes):
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=root)

    parents = git("rev-list", "--parents", "-n", "1", head).decode().split()
    if parents != [head, base]:
        raise SealMismatchError("baseCommit differs from HEAD or its single parent")
    repository = Path(git("rev-parse", "--show-toplevel").decode().strip()).resolve()
    if not freeze_path.is_relative_to(repository):
        raise SealMismatchError("Committed freeze must be inside the repository")
    name = freeze_path.relative_to(repository).as_posix()
    changed = git("diff", "--name-only", "--no-renames", "-z", base, head, "--")
    if changed != name.encode("utf-8") + b"\0":
        raise SealMismatchError("Freeze commit must change only the supplied freeze")
    _verify_committed_freeze_bytes(root, head, name, freeze_bytes)


def verify_runtime_freeze(path, root=ROOT, require_release=False):
    freeze_path = ensure_non_private_asset_path(path)
    freeze_bytes = freeze_path.read_bytes()
    data = json.loads(freeze_bytes.decode("utf-8"))
    current = fingerprints(root)
    for key in ("codeHash", "promptHash", "specHash", "files", "prompts"):
        if data.get(key) != current[key]:
            raise SealMismatchError(f"Runtime freeze mismatch: {key}")
    for name, expected in data.get("history", {}).items():
        if _hash_runtime_file(root / name) != expected:
            raise SealMismatchError(f"Historical freeze changed: {name}")
    for name, expected in data.get("historicalCore", {}).items():
        if _hash_runtime_file(root / name) != expected:
            raise SealMismatchError(f"Historical experimental core changed: {name}")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    if not isinstance(data.get("baseCommit"), str):
        raise SealMismatchError("baseCommit must identify a commit")
    base = subprocess.check_output(
        ["git", "rev-parse", "--verify", "--end-of-options", data["baseCommit"] + "^{commit}"],
        cwd=root, text=True,
    ).strip()
    if head != base:
        _verify_freeze_commit(root, head, base, freeze_path, freeze_bytes)
    if require_release:
        if data.get("evaluationPackageStatus") != "rebuilt_and_approved":
            raise SealMismatchError("Replacement evaluation package is required after boundary violation")
        if subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=all", "--ignore-submodules=none"],
            cwd=root, text=True,
        ).strip():
            raise SealMismatchError("Study execution requires a committed, clean freeze")
    if head == base:
        repository = Path(subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], cwd=root, text=True,
        ).strip()).resolve()
        if freeze_path.is_relative_to(repository):
            _verify_committed_freeze_bytes(
                root, head, freeze_path.relative_to(repository).as_posix(), freeze_bytes,
                allow_untracked=True,
            )
    return current
