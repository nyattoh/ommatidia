"""The CLI passes a valid host cap to its T3 adapter before execution."""

import pytest

from scripts import run_harness
from ommatidia.seal import create_seal_manifest
from tests.freeze_fixture import write_current_freeze


@pytest.fixture
def setup(tmp_path, monkeypatch):
    protocol = tmp_path / "protocol.md"
    protocol.write_text("Synthetic protocol", encoding="utf-8")
    manifest = tmp_path / "seal.json"
    create_seal_manifest(protocol, [], manifest)
    freeze = write_current_freeze(tmp_path)
    adapters = []
    real_adapter = run_harness.T3DelegationAdapter

    def make_adapter(*args, **kwargs):
        adapter = real_adapter(*args, **kwargs)
        adapters.append(adapter)
        return adapter

    monkeypatch.setattr(run_harness, "T3DelegationAdapter", make_adapter)
    monkeypatch.setattr(run_harness.ResearchHarness, "run_cohort", lambda *_a, **_kw: [])
    return ["--output-dir", str(tmp_path / "output"), "--manifest", str(manifest),
            "--runtime-freeze", str(freeze), "--executor", "t3"], adapters


@pytest.mark.parametrize("mode", ["mechanism_check", "run_dev"])
def test_t3_without_host_cap_fails_before_adapter(setup, capsys, mode):
    args, adapters = setup
    assert run_harness.main([*args, "--mode", mode], dispatcher=lambda *_a: None) == 1
    assert "host cost cap" in capsys.readouterr().err.lower()
    assert adapters == []


@pytest.mark.parametrize("cap", ["-1", "nan", "inf"])
def test_t3_invalid_host_cap_fails_before_adapter(setup, capsys, cap):
    args, adapters = setup
    assert run_harness.main([*args, "--host-cost-cap-yen", cap],
                            dispatcher=lambda *_a: None) == 1
    assert "host cost cap" in capsys.readouterr().err.lower()
    assert adapters == []


def test_t3_valid_host_cap_reaches_adapter(setup, monkeypatch):
    args, adapters = setup
    monkeypatch.setattr(run_harness, "create_t3_executor", lambda adapter: lambda *_a: None)
    assert run_harness.main(
        [*args, "--host-cost-cap-yen", "5.5"],
        dispatcher=lambda *_a: None,
        public_boundary=lambda _payload: {},
    ) == 0
    assert len(adapters) == 1
    assert adapters[0].host_cost_cap_yen == 5.5
