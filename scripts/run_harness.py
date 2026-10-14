#!/usr/bin/env python3
"""CLI utility to execute the Ommatidia reproducible research harness."""

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict

# Ensure src is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ommatidia.harness import ResearchHarness
from ommatidia.types import ConditionType
from tests.fixtures.synthetic_dev_cases import get_mechanism_check_fixtures


def dummy_synthetic_executor(step_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Synthetic executor for mechanism verification runs."""
    if "plan" in step_name or "inspect" in step_name:
        return {
            "proposal": {
                "claims": [{
                    "id": "claim_synth_01",
                    "role": "answer_claim",
                    "text": "Evaluated hypothesis",
                    "scope": "domain",
                }],
                "lenses": [{
                    "id": "lens_synth_01",
                    "label": "Boundary Lens",
                    "rationale": "Mechanism verification",
                    "origin": "proposed",
                }],
                "gaps": [{
                    "id": "gap_synth_01",
                    "kind": "missing_fact",
                    "lensId": "lens_synth_01",
                    "question": "Does asynchronous broadcast guarantee secondary copy invalidation?",
                    "triggerRefs": ["spec"],
                    "whyItMatters": "Consistency check",
                    "importance": "required",
                    "claimIds": ["claim_synth_01"],
                    "probeIds": ["probe_synth_01"],
                }],
                "probes": [{
                    "id": "probe_synth_01",
                    "gapIds": ["gap_synth_01"],
                    "method": "boundary",
                    "question": "Check async broadcast receipt",
                    "requiredCapability": "code_search",
                    "sourceGroups": ["source"],
                    "successCondition": "ok",
                    "refutationCondition": "fail",
                    "inconclusiveCondition": "inc",
                }],
            },
            "usage": {"rounds": 1, "modelCalls": 1, "toolCalls": 0, "elapsedMs": 50.0},
        }
    elif "exec" in step_name or "investigate" in step_name or "query" in step_name:
        return {
            "observations": [{
                "executionId": "exec_synth_01",
                "probeId": "probe_synth_01",
                "outcome": "completed",
                "evidence": [],
                "toolCalls": 1,
                "elapsedMs": 80.0,
                "costYen": None,
                "totalTokens": None,
            }],
            "usage": {"rounds": 0, "modelCalls": 0, "toolCalls": 1, "elapsedMs": 80.0},
        }
    elif "single_pass" in step_name or "pass1" in step_name:
        return {
            "answer": "Baseline single pass conclusion",
            "usage": {"rounds": 1, "modelCalls": 1, "toolCalls": 0, "elapsedMs": 40.0},
        }
    elif "recheck" in step_name:
        return {
            "finalAnswer": "Rechecked conclusion",
            "usage": {"rounds": 1, "modelCalls": 1, "toolCalls": 1, "elapsedMs": 60.0},
        }
    return {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Ommatidia research harness.")
    parser.add_argument("--mode", choices=["mechanism_check", "paired_compare"], default="mechanism_check",
                        help="Execution mode (mechanism_check on dev fixtures)")
    parser.add_argument("--condition-primary", choices=["A", "B", "C", "D", "E"], default="E",
                        help="Primary condition to evaluate")
    parser.add_argument("--condition-baseline", choices=["A", "B", "C", "D"], default="D",
                        help="Baseline condition for comparison")
    parser.add_argument("--output-dir", type=Path, default=Path("research/output"),
                        help="Output directory for ledgers and reports")
    parser.add_argument("--run-id", type=str, default="run_mech_001",
                        help="Unique run identifier")

    args = parser.parse_args()

    fixtures = get_mechanism_check_fixtures()
    harness = ResearchHarness(output_dir=args.output_dir)

    print(f"=== Running Ommatidia Research Harness [{args.mode}] ===")
    print(f"Output directory: {args.output_dir}")
    print(f"Run ID: {args.run_id}")

    if args.mode == "mechanism_check":
        cond = ConditionType(args.condition_primary)
        print(f"Evaluating {len(fixtures)} dev mechanism fixture(s) under Condition {cond.value}...")
        for task, gold in fixtures:
            rec = harness.evaluate_task(task, gold, cond, args.run_id, dummy_synthetic_executor)
            print(f"  Task {rec.task_id}: success={rec.final_decision_success}, "
                  f"gap_recall={rec.required_gap_recall:.2f}, tool_calls={rec.usage.tool_calls}")

    elif args.mode == "paired_compare":
        cond_p = ConditionType(args.condition_primary)
        cond_b = ConditionType(args.condition_baseline)
        print(f"Running paired comparison: Condition {cond_p.value} vs Condition {cond_b.value}...")
        result = harness.run_paired_comparison(
            fixtures, cond_p, cond_b, args.run_id, dummy_synthetic_executor
        )
        print("Paired statistics:")
        print(json.dumps(result["pairedStats"], indent=2))

    print("Execution completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
