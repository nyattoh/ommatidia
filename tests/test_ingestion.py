"""Tests for external response ingestion and strict schema validation."""

import unittest

from ommatidia.ingestion import (
    IngestionValidationError,
    ingest_observations,
    ingest_proposal,
    prepare_child_task_payload,
)
from tests.fixtures.synthetic_dev_cases import get_mechanism_check_fixtures


class TestIngestion(unittest.TestCase):
    def setUp(self) -> None:
        fixtures = get_mechanism_check_fixtures()
        self.task, _ = fixtures[0]

    def test_prepare_child_task_payload_excludes_private_data(self) -> None:
        context = {"currentRound": 1}
        payload = prepare_child_task_payload("planning", self.task, context)

        self.assertEqual(payload["stage"], "planning")
        self.assertEqual(payload["taskId"], self.task.task_id)
        self.assertIn("evidence", payload)
        self.assertNotIn("gold", payload)
        self.assertNotIn("groundTruth", payload)

    def test_strict_json_parsing_and_markdown_stripping(self) -> None:
        raw_markdown_json = """```json
        {
            "proposal": {
                "lenses": [{
                    "id": "lens_01",
                    "label": "Boundary Lens",
                    "rationale": "Test rationale",
                    "origin": "proposed"
                }]
            },
            "usage": {
                "totalTokens": null,
                "costYen": null
            }
        }
        ```"""

        prop, usage = ingest_proposal(raw_markdown_json)
        self.assertIsNotNone(prop.lenses)
        self.assertEqual(len(prop.lenses), 1)
        self.assertEqual(prop.lenses[0].id, "lens_01")
        self.assertIsNone(usage.total_tokens)
        self.assertIsNone(usage.cost_yen)

    def test_malformed_proposal_rejection(self) -> None:
        # Invalid JSON
        with self.assertRaises(IngestionValidationError):
            ingest_proposal("Not valid JSON at all")

        # Invalid lens definition (missing required fields)
        bad_lens_payload = {
            "proposal": {
                "lenses": [{"id": "bad_lens"}]  # missing label, rationale, origin
            }
        }
        with self.assertRaises(IngestionValidationError):
            ingest_proposal(bad_lens_payload)

    def test_observation_ingestion_validation(self) -> None:
        valid_obs_payload = {
            "observations": [{
                "executionId": "exec_ingest_01",
                "probeId": "probe_ingest_01",
                "outcome": "completed",
                "evidence": [],
                "toolCalls": 3,
                "elapsedMs": 450.0,
                "costYen": None,
                "totalTokens": 200,
            }]
        }

        obs_list = ingest_observations(valid_obs_payload)
        self.assertEqual(len(obs_list), 1)
        self.assertEqual(obs_list[0].execution_id, "exec_ingest_01")
        self.assertEqual(obs_list[0].total_tokens, 200)
        self.assertIsNone(obs_list[0].cost_yen)


if __name__ == "__main__":
    unittest.main()
