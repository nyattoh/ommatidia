#!/usr/bin/env python3
"""Public runner CLI. Study execution and synthetic checks have separate destinations."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ommatidia.campaign import atomic_json, is_bounded_cost
from ommatidia.harness import (
    ResearchHarness,
    TrialRecord,
    export_masked_assessor_dataset,
    load_public_packets,
)
from ommatidia.integrity import ROOT
from ommatidia.scoring import analyse_saved_trials, score_saved_trial, validate_matrix
from ommatidia.seal import ensure_non_private_asset_path, hash_file
from ommatidia.t3_adapter import (
    T3DelegationAdapter,
    create_t3_executor,
    export_campaign_dispatch_plan,
)
from ommatidia.types import ConditionType
from tests.fixtures.synthetic_dev_cases import get_mechanism_check_fixtures


def dummy_synthetic_executor(step_name, payload):
    """Synthetic mechanism data, with no claim of task correctness."""
    kind = payload["responseSchema"]["required"][0]
    # No paid call is made, so the spend is known to be zero.
    usage = {
        "modelCalls": 1,
        "toolCalls": 0,
        "elapsedMs": 1,
        "costYen": 0.0,
        "totalTokens": 0,
    }
    if kind == "proposal":
        return {
            "proposal": {"claims": [], "lenses": [], "gaps": [], "probes": []},
            "usage": usage,
        }
    if kind == "observations":
        return {"observations": [], "usage": usage}
    return {
        "taskId": payload["taskId"],
        "verdict": "inconclusive",
        "confidenceScore": 0.0,
        "justification": "Synthetic mechanism output; no empirical judgement.",
        "citedEvidence": [],
        "unresolvedGaps": [],
        "resourceUsage": {
            "modelCalls": 1,
            "toolCalls": 0,
            "elapsedMs": 1,
            "inputCharsEstimated": 0,
        },
        "usage": usage,
    }


dummy_synthetic_executor.synthetic_only = True


def parse_conditions(value):
    result = [ConditionType(item.strip().upper()) for item in value.split(",")]
    if len(result) != len(set(result)):
        raise ValueError("Duplicate condition")
    return result


def read_records(path):
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        return [TrialRecord.from_dict(item) for item in data]
    return [
        TrialRecord.from_dict(json.loads(file.read_text(encoding="utf-8")))
        for file in sorted(path.glob("*.json"))
    ]


def reject_private_path(path):
    return ensure_non_private_asset_path(path)


def require_sealed_file(path, manifest_path):
    path = reject_private_path(path)
    manifest_path = reject_private_path(manifest_path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = data.get("datasets", {})
    matched = [
        meta
        for name, meta in expected.items()
        if Path(name).resolve() == path.resolve()
    ]
    if len(matched) != 1 or matched[0].get("hash") != hash_file(path):
        raise ValueError(
            "Scoring rubric/design must be explicitly sealed before analysis"
        )


def main(argv=None, dispatcher=None, public_boundary=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=[
            "mechanism_check",
            "plan",
            "run_dev",
            "run_heldout",
            "evaluate",
            "mask_assessor",
            "paired_compare",
        ],
        default="mechanism_check",
    )
    parser.add_argument(
        "--dataset-dir", type=Path, default=Path("research/datasets/dev")
    )
    parser.add_argument("--partition", choices=["dev", "heldout"], default="dev")
    parser.add_argument("--conditions", default="A,B,C,D,E")
    parser.add_argument("--condition-primary", choices=list("ABCDE"), default="E")
    parser.add_argument("--condition-baseline", choices=list("ABCD"), default="D")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", default="run_001")
    parser.add_argument(
        "--manifest", type=Path, default=Path("research/seal_manifest.json")
    )
    parser.add_argument(
        "--runtime-freeze", type=Path, default=Path("research/runtime_freeze_r4.json")
    )
    parser.add_argument("--executor", choices=["synthetic", "t3"], default="synthetic")
    parser.add_argument("--host-cost-cap-yen", type=float)
    parser.add_argument("--synthetic-check", action="store_true")
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--no-resume", action="store_false", dest="resume")
    parser.add_argument("--export-plan", type=Path)
    parser.add_argument("--records-file", type=Path)
    parser.add_argument("--rubric-file", type=Path)
    parser.add_argument(
        "--metrics",
        default="fda,recallCrit,dsc,warrantedAbstention,unwarrantedAbstention",
    )
    parser.add_argument("--analysis-design", type=Path)
    parser.add_argument("--seed", type=int)
    args = parser.parse_args(argv)
    try:
        if (
            args.mode == "run_heldout"
            or args.partition == "heldout"
            or "heldout" in [part.lower() for part in args.dataset_dir.parts]
        ):
            # No existing held-out package is usable after the disclosed programmatic access.
            raise ValueError(
                "Held-out actions are disabled pending a new approved evaluation package; no dataset was read"
            )
        args.dataset_dir = reject_private_path(args.dataset_dir)
        for attr in (
            "rubric_file",
            "analysis_design",
            "records_file",
            "manifest",
            "runtime_freeze",
        ):
            path = getattr(args, attr)
            if path is not None:
                setattr(args, attr, reject_private_path(path))
        if args.executor == "synthetic" and args.output_dir.resolve().is_relative_to(
            (ROOT / "research/output").resolve()
        ):
            raise ValueError(
                "Synthetic checks require a separate temporary output directory"
            )
        if (
            args.mode == "run_dev"
            and args.executor != "t3"
            and not args.synthetic_check
        ):
            raise ValueError(
                "Study run requires a verified T3 dispatcher; synthetic cohort needs --synthetic-check"
            )
        harness = ResearchHarness(
            args.output_dir,
            seal_manifest_path=args.manifest,
            runtime_freeze_path=args.runtime_freeze,
        )
        harness.verify_environment()
        execution_modes = ("mechanism_check", "run_dev")
        executor = dummy_synthetic_executor
        if args.mode in execution_modes and args.executor == "t3":
            if not is_bounded_cost(args.host_cost_cap_yen):
                raise ValueError(
                    "T3 execution requires a finite, non-negative host cost cap (yen)"
                )
            adapter = T3DelegationAdapter(
                in_session_dispatcher=dispatcher,
                public_boundary=public_boundary,
                host_cost_cap_yen=args.host_cost_cap_yen,
            )
            adapter.require_public_boundary()
            executor = create_t3_executor(adapter)
        if args.mode == "mechanism_check":
            tasks = [task for task, _ in get_mechanism_check_fixtures()]
            records = harness.run_cohort(
                tasks,
                [ConditionType(args.condition_primary)],
                args.run_id,
                executor,
                partition="mechanism",
                executor_name=args.executor,
            )
            failures = sum(record.status != "completed" for record in records)
            print(
                f"Saved {len(records)} synthetic mechanism records; failed/invalid={failures}"
            )
            return 1 if failures else 0
        if args.mode in ("plan", "run_dev"):
            packets = load_public_packets(
                args.dataset_dir, verify_hashes=True, expected_count=24
            )
            conditions = parse_conditions(args.conditions)
            if args.mode == "plan":
                jobs = export_campaign_dispatch_plan(
                    packets,
                    conditions,
                    args.run_id,
                    args.export_plan or args.output_dir / "dispatch_graph_dev.json",
                )
                print(f"Saved {len(jobs)} graph templates; no calls dispatched")
                return 0
            if not args.synthetic_check:
                harness.verify_environment(require_release=True)
            records = harness.run_cohort(
                packets,
                conditions,
                args.run_id,
                executor,
                partition="dev",
                resume=args.resume,
                executor_name=args.executor,
            )
            failures = sum(record.status != "completed" for record in records)
            print(f"Saved {len(records)} trials; failed/invalid={failures}")
            return 1 if failures else 0
        records = read_records(
            args.records_file or args.output_dir / args.partition / "trials"
        )
        if not records:
            raise ValueError("No saved trial records")
        if args.mode == "mask_assessor":
            dataset, mapping = export_masked_assessor_dataset(
                records, args.output_dir, args.seed
            )
            print(f"Masked export: {dataset}; separate mapping: {mapping}")
            return 0
        if args.mode == "evaluate":
            if args.rubric_file is None:
                raise ValueError(
                    "An explicit sealed rubric file is required; no gold directory is read"
                )
            require_sealed_file(args.rubric_file, args.manifest)
            rubrics = json.loads(args.rubric_file.read_text(encoding="utf-8"))
            conditions = [
                condition.value for condition in parse_conditions(args.conditions)
            ]
            matrix = validate_matrix(records, conditions, list(rubrics), args.run_id)
            scored = []
            for trials in matrix.values():
                for task_id, record in trials.items():
                    record.metrics = score_saved_trial(
                        record, rubrics[task_id], args.metrics.split(",")
                    )
                    scored.append(record.to_dict())
            atomic_json(args.output_dir / args.partition / "scored_trials.json", scored)
            print(f"Scored {len(scored)} saved trials; original records preserved")
            return 1 if any(record["status"] != "completed" for record in scored) else 0
        if args.mode == "paired_compare":
            if args.analysis_design is None:
                raise ValueError(
                    "A sealed analysis design with 24 case IDs and 12 H4 tags is required"
                )
            require_sealed_file(args.analysis_design, args.manifest)
            design = json.loads(args.analysis_design.read_text(encoding="utf-8"))
            report = analyse_saved_trials(
                records, design["taskIds"], design["counterexampleIds"]
            )
            atomic_json(args.output_dir / args.partition / "paired_h1_h4.json", report)
            print("Saved preregistered paired H1-H4 analysis with Holm correction")
            return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
