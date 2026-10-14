"""Unknown cost and token counts must stay unknown when steps are accumulated."""

import unittest

from ommatidia.conditions import _accumulate_step_usage
from ommatidia.types import Usage


class TestUsageAccumulation(unittest.TestCase):
    def test_known_costs_sum_from_zero_start(self) -> None:
        usage = Usage(cost_yen=0.0, total_tokens=0)
        _accumulate_step_usage(usage, {"usage": {"costYen": 1.5, "totalTokens": 100}})
        _accumulate_step_usage(usage, {"usage": {"costYen": 2.0, "totalTokens": 50}})
        self.assertEqual(usage.cost_yen, 3.5)
        self.assertEqual(usage.total_tokens, 150)

    def test_step_without_usage_makes_total_unknown_not_zero(self) -> None:
        usage = Usage(cost_yen=0.0, total_tokens=0)
        _accumulate_step_usage(usage, {"usage": {"costYen": 1.0, "totalTokens": 10}})
        _accumulate_step_usage(usage, {"output": "no usage report"})
        self.assertIsNone(usage.cost_yen)
        self.assertIsNone(usage.total_tokens)

    def test_unknown_stays_unknown_after_later_known_step(self) -> None:
        usage = Usage(cost_yen=0.0, total_tokens=0)
        _accumulate_step_usage(usage, {"usage": {"costYen": None, "totalTokens": None}})
        _accumulate_step_usage(usage, {"usage": {"costYen": 5.0, "totalTokens": 20}})
        self.assertIsNone(usage.cost_yen)
        self.assertIsNone(usage.total_tokens)


if __name__ == "__main__":
    unittest.main()
