"""The synthetic path is zero-cost only for executors that cannot spend. Its name is not a permission."""

import pytest

from ommatidia.harness import ResearchHarness
from ommatidia.seal import create_seal_manifest
from ommatidia.t3_adapter import T3DelegationAdapter, create_t3_executor
from ommatidia.types import ConditionType
from scripts.run_harness import dummy_synthetic_executor
from tests.fixtures.synthetic_dev_cases import get_mechanism_check_fixtures
from tests.freeze_fixture import write_current_freeze


@pytest.fixture
def setup(tmp_path):
    protocol = tmp_path / "protocol.md"
    protocol.write_text("Synthetic protocol", encoding="utf-8")
    manifest = tmp_path / "seal.json"
    create_seal_manifest(protocol, [], manifest)
    task = get_mechanism_check_fixtures()[0][0]
    return tmp_path / "output", manifest, task, write_current_freeze(tmp_path)


def harness(setup):
    output, manifest, _, freeze = setup
    return ResearchHarness(
        output, seal_manifest_path=manifest, runtime_freeze_path=freeze
    )


def test_capped_executor_cannot_take_the_synthetic_path(setup):
    def paid(step, payload):
        return dummy_synthetic_executor(step, payload)

    paid.enforced_cost_cap_yen = 50.0
    with pytest.raises(
        ValueError, match="Synthetic path cannot run a metered or capped executor"
    ):
        harness(setup).run_cohort(
            [setup[2]], [ConditionType.A], "paid_as_synthetic", paid
        )


def test_metered_t3_executor_cannot_take_the_synthetic_path(setup):
    executor = create_t3_executor(
        T3DelegationAdapter(in_session_dispatcher=lambda *args: None)
    )
    with pytest.raises(
        ValueError, match="Synthetic path cannot run a metered or capped executor"
    ):
        harness(setup).run_cohort(
            [setup[2]], [ConditionType.A], "t3_as_synthetic", executor
        )


def test_reported_spend_on_the_synthetic_path_is_not_overwritten(setup):
    def spends(step, payload):
        result = dummy_synthetic_executor(step, payload)
        result["usage"] = {**result["usage"], "costYen": 3.0}
        return result

    with pytest.raises(ValueError, match="audit required"):
        harness(setup).run_cohort([setup[2]], [ConditionType.A], "spend", spends)
