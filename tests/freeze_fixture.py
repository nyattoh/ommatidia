"""Test-only runtime freeze built from the current code.

The committed research freeze is a pre-registration record and must not be
rewritten by tests. Unit tests that exercise harness logic use this temporary
copy instead, so they run against the code under test. The freeze checks
themselves are still covered by the tests that name a freeze file explicitly.
"""

import json
import subprocess
from pathlib import Path

from ommatidia.integrity import ROOT, fingerprints

FREEZE_KEYS = ("codeHash", "promptHash", "specHash", "files", "prompts")


def write_current_freeze(directory: Path) -> Path:
    current = fingerprints()
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    path = directory / "runtime_freeze_test.json"
    data = {key: current[key] for key in FREEZE_KEYS}
    data["baseCommit"] = head
    path.write_text(json.dumps(data), encoding="utf-8")
    return path
