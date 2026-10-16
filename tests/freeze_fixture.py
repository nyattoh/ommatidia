"""Test-only runtime freeze built from the current code.

The committed research freeze is a pre-registration record and must not be
rewritten by tests. Unit tests that exercise harness logic use this temporary
copy instead, so they run against the code under test. The freeze checks
themselves are still covered by the tests that name a freeze file explicitly.
"""

import json
import subprocess
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from ommatidia.integrity import ROOT, fingerprints

FREEZE_KEYS = ("codeHash", "promptHash", "specHash", "files", "prompts")


def write_current_freeze(directory: Path, release_ready=False) -> Path:
    current = fingerprints()
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    path = directory / "runtime_freeze_test.json"
    data = {key: current[key] for key in FREEZE_KEYS}
    data["baseCommit"] = head
    if release_ready:
        data["evaluationPackageStatus"] = "rebuilt_and_approved"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _git_status_stub(original, status, status_for_untracked_all=None, commands=None):
    def check_output(args, **kwargs):
        if args[:2] == ["git", "status"]:
            if commands is not None:
                commands.append(args)
            if status_for_untracked_all is not None and "--untracked-files=all" in args:
                return status_for_untracked_all
            return status
        return original(args, **kwargs)

    return check_output


@contextmanager
def clean_git_status(status="", *, status_for_untracked_all=None, commands=None):
    """Simulate git status while preserving other subprocess calls."""
    stub = _git_status_stub(
        subprocess.check_output, status, status_for_untracked_all, commands
    )
    with patch.object(subprocess, "check_output", side_effect=stub):
        yield


def set_git_status(monkeypatch, status="", *, status_for_untracked_all=None, commands=None):
    """Keep simulated release tests independent of the checkout's pending edits."""
    stub = _git_status_stub(
        subprocess.check_output, status, status_for_untracked_all, commands
    )
    monkeypatch.setattr(subprocess, "check_output", stub)


def report_clean_git_status(monkeypatch):
    set_git_status(monkeypatch)
