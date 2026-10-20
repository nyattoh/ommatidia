"""Synthetic Git evidence for a freeze-only commit and fail-closed guards.

The proposed additional accepted shape is a direct child of baseCommit whose
only tree delta is the supplied tracked freeze. Ancestry alone is insufficient.
No repository freeze, protocol, or evaluation data is read by these tests.
"""

import json
import subprocess

import pytest

from ommatidia import integrity
from ommatidia.seal import SealMismatchError, hash_file


def git(root, *args):
    return subprocess.check_output(
        ["git", "-c", "core.autocrlf=false", "-c", "core.hooksPath=/dev/null",
         "-c", "commit.gpgsign=false", "-c", "user.name=Synthetic Test",
         "-c", "user.email=synthetic@example.invalid", *args],
        cwd=root, text=True, stderr=subprocess.STDOUT,
    ).strip()


def synthetic_fingerprints(root):
    files = {"src/ommatidia/runtime.py": hash_file(root / "src/ommatidia/runtime.py")}
    prompts = {"syntheticPrompt": integrity.digest("synthetic prompt")}
    return {
        "files": files, "prompts": prompts,
        "codeHash": integrity.digest(files),
        "promptHash": integrity.digest(prompts),
        "specHash": integrity.digest("synthetic specification"),
    }


@pytest.fixture
def repository(synthetic_private_io_root, monkeypatch):
    root = synthetic_private_io_root / "repository"
    root.mkdir()
    git(root, "init", "--quiet")
    for name, content in {
        "src/ommatidia/runtime.py": "# Synthetic runtime only.\n",
        "archive/history.json": '{"synthetic": "history"}\n',
        "archive/core.py": "# Synthetic historical core.\n",
        "notes.txt": "Synthetic tracked content outside the fingerprint.\n",
    }.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "--quiet", "-m", "test: synthetic base")
    monkeypatch.setattr(integrity, "fingerprints", synthetic_fingerprints)
    return root


def write_freeze(root, path=None, **overrides):
    path = path or root / "research/runtime_freeze_r4.json"
    data = {
        **synthetic_fingerprints(root),
        "baseCommit": git(root, "rev-parse", "HEAD"),
        "evaluationPackageStatus": "rebuilt_and_approved",
        "history": {"archive/history.json": hash_file(root / "archive/history.json")},
        "historicalCore": {"archive/core.py": hash_file(root / "archive/core.py")},
    }
    data.update(overrides)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
    return path


def commit_freeze(root, **overrides):
    path = write_freeze(root, **overrides)
    git(root, "add", path.relative_to(root).as_posix())
    git(root, "commit", "--quiet", "-m", "test: synthetic freeze only")
    return path


def legacy_freeze(root):
    return write_freeze(root, path=root.parent / "external_synthetic_freeze.json")


@pytest.mark.parametrize("require_release", [False, True])
def test_committed_default_style_freeze_retains_base_provenance(repository, require_release):
    root = repository
    base = git(root, "rev-parse", "HEAD")
    path = commit_freeze(root)
    before = path.read_bytes()
    assert json.loads(before)["baseCommit"] == base
    assert git(root, "rev-parse", "HEAD") != base
    assert git(root, "rev-parse", "HEAD^") == base
    assert git(root, "diff", "--name-only", base, "HEAD") == path.relative_to(root).as_posix()
    assert git(root, "status", "--porcelain", "--untracked-files=all") == ""

    actual = integrity.verify_runtime_freeze(path, root=root, require_release=require_release)

    assert actual == synthetic_fingerprints(root)
    assert path.read_bytes() == before


def test_existing_head_equal_base_shape_remains_valid(repository):
    path = legacy_freeze(repository)
    assert integrity.verify_runtime_freeze(path, root=repository, require_release=True) == (
        synthetic_fingerprints(repository)
    )


@pytest.mark.parametrize("field", ["codeHash", "promptHash", "specHash", "files", "prompts"])
def test_fingerprint_tampering_is_rejected(repository, field):
    path = legacy_freeze(repository)
    data = json.loads(path.read_text(encoding="utf-8"))
    data[field] = {} if isinstance(data[field], dict) else "tampered"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(SealMismatchError, match=f"Runtime freeze mismatch: {field}"):
        integrity.verify_runtime_freeze(path, root=repository, require_release=True)


@pytest.mark.parametrize("name, message", [
    ("src/ommatidia/runtime.py", "Runtime freeze mismatch"),
    ("archive/history.json", "Historical freeze changed"),
    ("archive/core.py", "Historical experimental core changed"),
])
def test_runtime_history_and_core_changes_fail_before_git_gate(repository, name, message):
    path = legacy_freeze(repository)
    (repository / name).write_text("Synthetic mutation.\n", encoding="utf-8")
    with pytest.raises(SealMismatchError, match=message):
        integrity.verify_runtime_freeze(path, root=repository, require_release=True)


@pytest.mark.parametrize("kind", ["tracked", "staged", "untracked"])
def test_release_rejects_dirty_tree_with_unchanged_fingerprints(repository, kind):
    path = legacy_freeze(repository)
    name = "new.txt" if kind == "untracked" else "notes.txt"
    (repository / name).write_text("Synthetic dirty content.\n", encoding="utf-8")
    if kind == "staged":
        git(repository, "add", name)
    assert git(repository, "status", "--porcelain", "--untracked-files=all")
    with pytest.raises(SealMismatchError, match="committed, clean freeze"):
        integrity.verify_runtime_freeze(path, root=repository, require_release=True)


def test_release_rejects_unapproved_package(repository):
    path = write_freeze(repository, path=repository.parent / "external_synthetic_freeze.json",
                        evaluationPackageStatus="blocked_rebuild_required")
    with pytest.raises(SealMismatchError, match="Replacement evaluation package"):
        integrity.verify_runtime_freeze(path, root=repository, require_release=True)


@pytest.mark.parametrize("invalid_base", ["0" * 40, "refs/heads/missing-synthetic-base", "HEAD:notes.txt"])
def test_invalid_or_noncommit_base_is_rejected(repository, invalid_base):
    path = write_freeze(repository, path=repository.parent / "external_synthetic_freeze.json",
                        baseCommit=invalid_base)
    with pytest.raises((SealMismatchError, subprocess.CalledProcessError, ValueError)):
        integrity.verify_runtime_freeze(path, root=repository, require_release=True)


@pytest.mark.parametrize("mutation", ["notes.txt", "src/ommatidia/runtime.py"])
def test_freeze_commit_cannot_also_change_other_tracked_files(repository, mutation):
    base = git(repository, "rev-parse", "HEAD")
    (repository / mutation).write_text("Synthetic replacement.\n", encoding="utf-8")
    # Recompute fingerprints: tree provenance must still reject the extra delta.
    path = write_freeze(repository, baseCommit=base)
    git(repository, "add", ".")
    git(repository, "commit", "--quiet", "-m", "test: synthetic unsealed tree change")
    assert git(repository, "status", "--porcelain") == ""
    with pytest.raises(SealMismatchError):
        integrity.verify_runtime_freeze(path, root=repository, require_release=True)


@pytest.mark.parametrize("descendant", ["empty", "tracked_change", "freeze_tampering"])
def test_arbitrary_descendants_of_freeze_are_not_accepted(repository, descendant):
    path = commit_freeze(repository)
    if descendant == "tracked_change":
        (repository / "notes.txt").write_text("Synthetic descendant change.\n", encoding="utf-8")
    elif descendant == "freeze_tampering":
        data = json.loads(path.read_text(encoding="utf-8"))
        data["history"] = {}
        data["historicalCore"] = {}
        path.write_text(json.dumps(data), encoding="utf-8")
    git(repository, "add", ".")
    git(repository, "commit", "--quiet", "--allow-empty", "-m", "test: synthetic unsealed descendant")
    assert git(repository, "status", "--porcelain") == ""
    with pytest.raises(SealMismatchError):
        integrity.verify_runtime_freeze(path, root=repository, require_release=True)


def test_release_rejects_dirty_committed_freeze_even_with_rebased_metadata(repository):
    path = commit_freeze(repository)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["baseCommit"] = git(repository, "rev-parse", "HEAD")
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(SealMismatchError, match="committed, clean freeze"):
        integrity.verify_runtime_freeze(path, root=repository, require_release=True)


@pytest.mark.parametrize("require_release", [False, True])
def test_committed_freeze_bytes_cannot_be_substituted(repository, require_release):
    path = commit_freeze(repository)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["history"] = {}
    data["historicalCore"] = {}
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(SealMismatchError, match="differs from committed freeze"):
        integrity.verify_runtime_freeze(path, root=repository, require_release=require_release)


def test_rebased_metadata_cannot_bypass_committed_bytes_in_nonrelease_mode(repository):
    path = commit_freeze(repository)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["baseCommit"] = git(repository, "rev-parse", "HEAD")
    data["history"] = {}
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(SealMismatchError, match="differs from committed freeze"):
        integrity.verify_runtime_freeze(path, root=repository)


def test_external_copy_cannot_stand_in_for_committed_freeze(repository):
    path = commit_freeze(repository)
    external = repository.parent / "external_synthetic_freeze.json"
    external.write_bytes(path.read_bytes())
    with pytest.raises(SealMismatchError, match="inside the repository"):
        integrity.verify_runtime_freeze(external, root=repository)


def test_merge_with_base_as_first_parent_is_rejected(repository):
    base = git(repository, "rev-parse", "HEAD")
    git(repository, "checkout", "--quiet", "-b", "synthetic-freeze")
    path = commit_freeze(repository)
    git(repository, "checkout", "--quiet", "--detach", base)
    git(repository, "merge", "--quiet", "--no-ff", "synthetic-freeze",
        "-m", "test: synthetic freeze merge")
    assert git(repository, "diff", "--name-only", base, "HEAD") == path.relative_to(repository).as_posix()
    with pytest.raises(SealMismatchError, match="single parent"):
        integrity.verify_runtime_freeze(path, root=repository)


def test_freeze_only_update_to_existing_tracked_freeze_is_accepted(repository):
    commit_freeze(repository)
    path = commit_freeze(repository)
    assert integrity.verify_runtime_freeze(path, root=repository, require_release=True) == (
        synthetic_fingerprints(repository)
    )


@pytest.mark.parametrize("kind", ["tracked", "staged", "untracked"])
def test_committed_freeze_release_retains_dirty_tree_guards(repository, kind):
    path = commit_freeze(repository)
    name = "new.txt" if kind == "untracked" else "notes.txt"
    (repository / name).write_text("Synthetic dirty content.\n", encoding="utf-8")
    if kind == "staged":
        git(repository, "add", name)
    with pytest.raises(SealMismatchError, match="committed, clean freeze"):
        integrity.verify_runtime_freeze(path, root=repository, require_release=True)
