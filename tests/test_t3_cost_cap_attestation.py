"""The T3 per-call cost cap comes from host configuration and must be echoed by host attestation."""

import pytest

from ommatidia.harness import ResearchHarness
from ommatidia.seal import create_seal_manifest
from ommatidia.t3_adapter import T3DelegationAdapter, create_t3_executor
from ommatidia.types import ConditionType
from tests.fixtures.synthetic_dev_cases import get_mechanism_check_fixtures
from tests.freeze_fixture import report_clean_git_status, write_current_freeze

ATTESTED_FLAGS = (
    "publicOnly",
    "singleModelInvocation",
    "enforcesStepBudget",
    "hostUsageVerified",
)


def attesting(cap):
    def boundary(_payload):
        attestation = dict.fromkeys(ATTESTED_FLAGS, True)
        if cap is not None:
            attestation["enforcedCostCapYen"] = cap
        return attestation

    return boundary


@pytest.fixture
def setup(tmp_path, monkeypatch):
    report_clean_git_status(monkeypatch)
    protocol = tmp_path / "protocol.md"
    protocol.write_text("Synthetic protocol", encoding="utf-8")
    manifest = tmp_path / "seal.json"
    create_seal_manifest(protocol, [], manifest)
    task = get_mechanism_check_fixtures()[0][0]
    return tmp_path / "output", manifest, task, write_current_freeze(tmp_path, release_ready=True)


def harness(setup):
    output, manifest, _, freeze = setup
    return ResearchHarness(
        output, seal_manifest_path=manifest, runtime_freeze_path=freeze
    )


def test_executor_cap_is_the_host_configured_value_or_none():
    dispatcher = lambda *args: None
    configured = create_t3_executor(
        T3DelegationAdapter(
            in_session_dispatcher=dispatcher,
            public_boundary=attesting(5.0),
            host_cost_cap_yen=5.0,
        )
    )
    unconfigured = create_t3_executor(
        T3DelegationAdapter(
            in_session_dispatcher=dispatcher, public_boundary=attesting(None)
        )
    )
    assert configured.enforced_cost_cap_yen == 5.0
    assert unconfigured.enforced_cost_cap_yen is None


def test_unconfigured_cap_is_refused_before_any_dispatch(setup):
    calls = []
    executor = create_t3_executor(
        T3DelegationAdapter(
            in_session_dispatcher=lambda *args: calls.append(args),
            public_boundary=attesting(None),
        )
    )
    with pytest.raises(ValueError, match="enforced_cost_cap_yen"):
        harness(setup).run_cohort(
            [setup[2]], [ConditionType.A], "no_cap", executor, executor_name="t3_probe"
        )
    assert calls == []


def test_attestation_that_does_not_echo_the_cap_never_dispatches(setup):
    calls = []
    executor = create_t3_executor(
        T3DelegationAdapter(
            in_session_dispatcher=lambda *args: calls.append(args),
            public_boundary=attesting(4.0),
            host_cost_cap_yen=5.0,
        )
    )
    with pytest.raises(ValueError, match="audit required"):
        harness(setup).run_cohort(
            [setup[2]],
            [ConditionType.A],
            "mismatch",
            executor,
            executor_name="t3_probe",
        )
    assert calls == []
