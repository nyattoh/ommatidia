from ommatidia.types import Budget, Usage


def budget(max_cost_yen=500.0):
    return Budget(
        max_rounds=4,
        max_model_calls=8,
        max_tool_calls=12,
        max_elapsed_ms=180000,
        max_input_chars=48000,
        max_output_tokens_per_call=0,
        max_cost_yen=max_cost_yen,
    )


def test_unknown_cost_exceeds_a_configured_cost_budget():
    assert Usage(cost_yen=None).exceeds(budget()) is True


def test_cost_at_the_configured_limit_is_within_budget():
    assert Usage(cost_yen=500.0).exceeds(budget()) is False


def test_cost_above_the_configured_limit_exceeds_budget():
    assert Usage(cost_yen=500.01).exceeds(budget()) is True
