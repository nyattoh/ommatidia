"""A fresh checkout must reproduce the sealed dev bytes whatever the line-ending config."""

import hashlib
import json
import shutil
import subprocess

import pytest

from ommatidia.integrity import ROOT

PUBLIC = ("public_packets/", "evidence/")


@pytest.mark.skipif(
    shutil.which("git") is None or not (ROOT / ".git").exists(),
    reason="Requires a git checkout of the repository",
)
def test_fresh_checkout_without_autocrlf_matches_sealed_dev_manifest(tmp_path):
    # r4296529338: the manifest hashes the CRLF bytes; an LF checkout used to fail every entry.
    clone = tmp_path / "clone"
    subprocess.run(
        ["git", "clone", "--quiet", "-c", "core.autocrlf=false", "-c", "core.eol=lf",
         str(ROOT), str(clone)],
        check=True,
    )
    dev = clone / "research" / "datasets" / "dev"
    files = json.loads((dev / "manifest.json").read_text(encoding="utf-8"))["files"]
    public = [name for name in files if name.startswith(PUBLIC)]
    assert sum(name.startswith("public_packets/") for name in public) == 24
    mismatched = [
        name
        for name in public
        if hashlib.sha256((dev / name).read_bytes()).hexdigest() != files[name]["hash"]
    ]
    assert mismatched == []
    # Private files are not opened here; they must carry the same checkout rule.
    private = [f"research/datasets/dev/{name}" for name in files if not name.startswith(PUBLIC)]
    attrs = subprocess.run(
        ["git", "check-attr", "eol", "--", *private],
        cwd=clone, check=True, capture_output=True, text=True,
    ).stdout.splitlines()
    assert len(attrs) == len(private) and all(line.endswith(": eol: crlf") for line in attrs)
