"""The in-session controller forwards the host cost cap to its adapter."""

import pytest

from ommatidia.t3_adapter import T3CampaignController, create_t3_executor


@pytest.mark.parametrize("cap", [0, 50.0])
def test_controller_forwards_host_cost_cap(cap):
    controller = T3CampaignController(host_cost_cap_yen=cap)
    assert controller.adapter.host_cost_cap_yen == cap
    assert create_t3_executor(controller.adapter).enforced_cost_cap_yen == cap


def test_controller_without_cap_stays_unbounded():
    controller = T3CampaignController()
    assert controller.adapter.host_cost_cap_yen is None
    assert create_t3_executor(controller.adapter).enforced_cost_cap_yen is None
