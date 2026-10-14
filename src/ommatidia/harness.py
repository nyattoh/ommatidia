"""Main experiment orchestrator and comparative research harness."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from ommatidia.conditions import (
    ConditionARunner,
    ConditionBRunner,
    ConditionCRunner,
    ConditionDRunner,
    ConditionERunner,
)
from ommatidia.evaluator import compute_paired_differences, score_run_objectively
from ommatidia.ledger import RunLedger
from ommatidia.seal import verify_seal_manifest
from ommatidia.state import compute_payload_hash
from ommatidia.types import (
    ConditionType,
    EvaluationMetricRecord,
    GoldStandard,
    LedgerStage,
    TaskPacket,
    UnderstandingState,
    Usage,
)


def _sha256_of_str(val: str) -> str:
    return hashlib.sha256(val.encode("utf-8")).hexdigest()


class ResearchHarness:
    """Orchestrates reproducible evaluation across conditions A through E."""

    def __init__(
        self,
        output_dir: Path,
        ledger_path: Optional[Path] = None,
        seal_manifest_path: Optional[Path] = None,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.ledger = RunLedger(ledger_path or (self.output_dir / "ledger.jsonl"))
        self.seal_manifest_path = seal_manifest_path

        self.runners = {
            ConditionType.A: ConditionARunner(),
            ConditionType.B: ConditionBRunner(),
            ConditionType.C: ConditionCRunner(),
            ConditionType.D: ConditionDRunner(),
            ConditionType.E: ConditionERunner(),
        }

    def verify_environment(self) -> None:
        """Verify immutable protocol and dataset hashes if a seal manifest is supplied."""
        if self.seal_manifest_path and self.seal_manifest_path.exists():
            manifest_data = json.loads(self.seal_manifest_path.read_text(encoding="utf-8"))
            verify_seal_manifest(manifest_data)

    def evaluate_task(
        self,
        task: TaskPacket,
        gold: GoldStandard,
        condition: ConditionType,
        run_id: str,
        executor_func: Callable[[str, Dict[str, Any]], Dict[str, Any]],
    ) -> EvaluationMetricRecord:
        """Run a single task under a specified condition and compute objective metrics."""
        runner = self.runners[condition]
        task_hash = compute_payload_hash(task.to_dict())

        # Record planning stage entry
        self.ledger.record_stage(
            stage=LedgerStage.PLANNING,
            execution_id=f"plan_{task.task_id}_{condition.value}_{run_id}",
            task_id=task.task_id,
            condition=condition,
            input_payload_hash=task_hash,
            output_payload_hash=_sha256_of_str(f"init_{task.task_id}"),
            usage=Usage(),
            status="started",
            notes=f"Starting task {task.task_id} under condition {condition.value}",
        )

        # Run condition
        final_state: UnderstandingState = runner.run(task, executor_func)

        # Record synthesis stage entry
        stage_breakdown = self.ledger.aggregate_usage_by_stage()
        self.ledger.record_stage(
            stage=LedgerStage.SYNTHESIS,
            execution_id=f"synth_{task.task_id}_{condition.value}_{run_id}",
            task_id=task.task_id,
            condition=condition,
            input_payload_hash=task_hash,
            output_payload_hash=_sha256_of_str(final_state.stop_reason or "complete"),
            usage=final_state.usage,
            status=final_state.decision.value,
            notes=f"Completed task {task.task_id} with decision {final_state.decision.value}",
        )

        # Compute objective score against gold
        metric_record = score_run_objectively(
            state=final_state,
            gold=gold,
            run_id=run_id,
            condition=condition,
            stage_breakdown=stage_breakdown,
        )

        return metric_record

    def run_paired_comparison(
        self,
        tasks_with_gold: List[Tuple[TaskPacket, GoldStandard]],
        primary_condition: ConditionType,
        baseline_condition: ConditionType,
        run_id: str,
        executor_func: Callable[[str, Dict[str, Any]], Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Execute paired runs on a task cohort and compute comparative differences."""
        self.ledger.acquire_lock(run_id)
        try:
            primary_records: List[EvaluationMetricRecord] = []
            baseline_records: List[EvaluationMetricRecord] = []

            for task, gold in tasks_with_gold:
                rec_p = self.evaluate_task(task, gold, primary_condition, f"{run_id}_p", executor_func)
                rec_b = self.evaluate_task(task, gold, baseline_condition, f"{run_id}_b", executor_func)
                primary_records.append(rec_p)
                baseline_records.append(rec_b)

            paired_stats = compute_paired_differences(
                primary_records, baseline_records, metric_name="final_decision_success"
            )

            result = {
                "runId": run_id,
                "primaryCondition": primary_condition.value,
                "baselineCondition": baseline_condition.value,
                "taskCount": len(tasks_with_gold),
                "pairedStats": paired_stats,
                "primaryRecords": [r.to_dict() for r in primary_records],
                "baselineRecords": [r.to_dict() for r in baseline_records],
            }

            out_file = self.output_dir / f"paired_{primary_condition.value}_vs_{baseline_condition.value}_{run_id}.json"
            out_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
            return result
        finally:
            self.ledger.release_lock()
