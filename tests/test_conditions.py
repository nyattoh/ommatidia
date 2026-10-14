"""Tests for condition contracts (A-E), execution drivers, and budget adherence."""

from typing import Any, Dict
import unittest

from ommatidia.conditions import (
    ConditionARunner,
    ConditionBRunner,
    ConditionCRunner,
    ConditionDRunner,
    ConditionERunner,
)
from ommatidia.types import (
    Budget,
    ConditionType,
    Decision,
    ObservationOutcome,
    ProbeMethod,
    ProbeStatus,
)
from tests.fixtures.synthetic_dev_cases import get_mechanism_check_fixtures


class TestConditionRunners(unittest.TestCase):
    def setUp(self) -> None:
        fixtures = get_mechanism_check_fixtures()
        self.task, _ = fixtures[0]

    def test_condition_a_runner(self) -> None:
        runner = ConditionARunner()

        def mock_executor(step_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
            self.assertEqual(step_name, "single_pass_investigation")
            return {
                "answer": "Evaluated single-pass conclusion",
                "usage": {"rounds": 1, "modelCalls": 1, "toolCalls": 0, "elapsedMs": 200.0},
            }

        state = runner.run(self.task, mock_executor)
        self.assertEqual(state.decision, Decision.READY_FOR_REQUESTED_STEP)
        self.assertEqual(len(state.claims), 1)
        self.assertEqual(state.claims[0].text, "Evaluated single-pass conclusion")
        self.assertEqual(state.usage.model_calls, 1)

    def test_condition_b_runner(self) -> None:
        runner = ConditionBRunner()

        def mock_executor(step_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
            if step_name == "pass1_investigation":
                return {"answer": "Pass 1 answer", "usage": {"rounds": 1, "modelCalls": 1, "toolCalls": 0, "elapsedMs": 100.0}}
            elif step_name == "generic_recheck":
                return {"finalAnswer": "Pass 2 re-evaluated", "usage": {"rounds": 1, "modelCalls": 1, "toolCalls": 1, "elapsedMs": 150.0}}
            raise ValueError(f"Unknown step: {step_name}")

        state = runner.run(self.task, mock_executor)
        self.assertEqual(state.decision, Decision.READY_FOR_REQUESTED_STEP)
        self.assertEqual(state.claims[0].text, "Pass 2 re-evaluated")
        self.assertEqual(state.usage.rounds, 2)
        self.assertEqual(state.usage.tool_calls, 1)

    def test_condition_c_runner(self) -> None:
        runner = ConditionCRunner()

        def mock_executor(step_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
            self.assertEqual(step_name, "fixed_lens_query")
            return {"observations": [], "usage": {"rounds": 1, "modelCalls": 1, "toolCalls": 0, "elapsedMs": 50.0}}

        state = runner.run(self.task, mock_executor)
        self.assertEqual(len(state.lenses), 3)
        self.assertEqual(state.decision, Decision.READY_FOR_REQUESTED_STEP)
        self.assertEqual(state.usage.model_calls, 3)

    def test_condition_d_runner(self) -> None:
        runner = ConditionDRunner()

        step_counter = 0

        def mock_executor(step_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
            nonlocal step_counter
            step_counter += 1
            if step_name == "adaptive_plan_step":
                return {
                    "proposal": {
                        "probes": [{
                            "id": "probe_seq_01",
                            "gapIds": ["gap_dummy"],
                            "method": "example",
                            "question": "Seq check",
                            "requiredCapability": "doc",
                            "sourceGroups": ["docs"],
                            "successCondition": "ok",
                            "refutationCondition": "fail",
                            "inconclusiveCondition": "inc",
                        }]
                    },
                    "usage": {"rounds": 1, "modelCalls": 1, "toolCalls": 0, "elapsedMs": 50.0},
                }
            elif step_name == "single_investigator_exec":
                return {
                    "observations": [{
                        "executionId": "exec_d_01",
                        "probeId": "probe_seq_01",
                        "outcome": "completed",
                        "evidence": [],
                        "toolCalls": 1,
                        "elapsedMs": 100.0,
                    }],
                    "usage": {"rounds": 0, "modelCalls": 0, "toolCalls": 1, "elapsedMs": 100.0},
                }
            raise ValueError(f"Unknown step: {step_name}")

        state = runner.run(self.task, mock_executor)
        self.assertIn(state.stop_reason, ("probes_exhausted", "no_pending_probes"))
        self.assertEqual(len(state.probes), 1)
        self.assertEqual(state.probes[0].status, ProbeStatus.COMPLETE)

    def test_condition_e_runner(self) -> None:
        runner = ConditionERunner(max_concurrent_roles=2)

        def mock_executor(step_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
            if step_name == "ommatidia_inspect":
                return {
                    "proposal": {
                        "lenses": [{
                            "id": "lens_e_01",
                            "label": "Concurrency lens",
                            "rationale": "Inspect locks",
                            "origin": "proposed",
                        }],
                        "probes": [{
                            "id": "probe_e_01",
                            "gapIds": ["gap_e"],
                            "method": "boundary",
                            "question": "Boundary check",
                            "requiredCapability": "doc",
                            "sourceGroups": ["docs"],
                            "successCondition": "ok",
                            "refutationCondition": "fail",
                            "inconclusiveCondition": "inc",
                        }],
                    },
                    "usage": {"rounds": 1, "modelCalls": 1, "toolCalls": 0, "elapsedMs": 80.0},
                }
            elif step_name == "ommatidia_investigate_batch":
                return {
                    "observations": [{
                        "executionId": "exec_e_01",
                        "probeId": "probe_e_01",
                        "outcome": "completed",
                        "evidence": [],
                        "toolCalls": 2,
                        "elapsedMs": 120.0,
                    }],
                    "usage": {"rounds": 0, "modelCalls": 0, "toolCalls": 2, "elapsedMs": 120.0},
                }
            raise ValueError(f"Unknown step: {step_name}")

        state = runner.run(self.task, mock_executor)
        self.assertIn(state.stop_reason, ("probes_exhausted", "probes_completed"))
        self.assertEqual(len(state.lenses), 1)
        self.assertEqual(len(state.probes), 1)
        self.assertEqual(state.probes[0].status, ProbeStatus.COMPLETE)


if __name__ == "__main__":
    unittest.main()
