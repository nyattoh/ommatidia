"""Private evaluation paths are rejected before the file is opened or parsed.

Every path here is a nonexistent synthetic path under a temporary directory.
"""

import pytest

from ommatidia.harness import ResearchHarness
from ommatidia.seal import create_seal_manifest
from scripts import run_harness
from tests.freeze_fixture import write_current_freeze


@pytest.fixture
def valid(tmp_path):
    protocol = tmp_path / "protocol.md"
    protocol.write_text("Synthetic protocol", encoding="utf-8")
    manifest = tmp_path / "seal.json"
    create_seal_manifest(protocol, [], manifest)
    return tmp_path, manifest, write_current_freeze(tmp_path)


@pytest.mark.parametrize("part", ["gold", "cases"])
def test_freeze_under_private_directory_is_rejected_before_open(valid, part):
    tmp, manifest, _ = valid
    harness = ResearchHarness(
        tmp / "output",
        seal_manifest_path=manifest,
        runtime_freeze_path=tmp / part / "freeze.json",
    )
    with pytest.raises(ValueError, match="Private evaluation asset path"):
        harness.verify_environment()


@pytest.mark.parametrize("part", ["gold", "cases"])
def test_seal_manifest_under_private_directory_is_rejected_before_open(valid, part):
    tmp, _, freeze = valid
    harness = ResearchHarness(
        tmp / "output",
        seal_manifest_path=tmp / part / "seal.json",
        runtime_freeze_path=freeze,
    )
    with pytest.raises(ValueError, match="Private evaluation asset path"):
        harness.verify_environment()


def test_cli_rejects_private_runtime_freeze_before_the_harness_is_built(
    valid, monkeypatch, capsys
):
    tmp, manifest, _ = valid
    built = []
    real = run_harness.ResearchHarness
    monkeypatch.setattr(
        run_harness,
        "ResearchHarness",
        lambda *a, **kw: built.append(kw) or real(*a, **kw),
    )
    args = [
        "--output-dir",
        str(tmp / "output"),
        "--manifest",
        str(manifest),
        "--runtime-freeze",
        str(tmp / "gold" / "freeze.json"),
        "--mode",
        "mechanism_check",
        "--executor",
        "synthetic",
    ]
    assert run_harness.main(args) == 1
    assert "Private evaluation asset path" in capsys.readouterr().err
    assert built == []
