"""Main experiment orchestrator and comparative research harness.

Provides testable dataset loading with SHA-256 manifest verification,
global resource cap registry enforcing the 240 trials / 1920 aggregate model call ceiling,
robust crash-consistent resume without duplicate executions,
single-blind UUID assessor masking, and paired condition evaluations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import random
import time
import threading
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import uuid

from ommatidia.conditions import (
    ConditionARunner,
    ConditionBRunner,
    ConditionCRunner,
    ConditionDRunner,
    ConditionERunner,
)
from ommatidia.evaluator import compute_paired_differences, score_run_objectively
from ommatidia.ingestion import ingest_final_judgement
from ommatidia.ledger import RunLedger
from ommatidia.seal import hash_file, verify_seal_manifest
from ommatidia.state import compute_payload_hash
from ommatidia.campaign import atomic_json, is_bounded_cost, validate_usage
from ommatidia.integrity import fingerprints, verify_runtime_freeze
from ommatidia.runtime import (
    check_public_payload,
    execute_graph,
    inconclusive,
    render_prompt,
)
from ommatidia.scoring import score_saved_trial
from ommatidia.types import (
    ConditionType,
    Decision,
    EvaluationMetricRecord,
    FinalJudgement,
    GoldStandard,
    LedgerStage,
    TaskPacket,
    UnderstandingState,
    Usage,
)


def _sha256_of_str(val: str) -> str:
    return hashlib.sha256(val.encode("utf-8")).hexdigest()


from ommatidia.campaign import GlobalResourceRegistry, ResourceLimitExceeded


def sanitize_ledger_file(ledger_path: Path) -> None:
    """If ledger file ends with an incomplete or torn line from a crash, truncate to last valid JSON line."""
    if not ledger_path.exists():
        return
    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    valid_lines = []
    for index, line in enumerate(lines):
        clean = line.strip()
        if not clean:
            continue
        try:
            json.loads(clean)
            valid_lines.append(clean)
        except json.JSONDecodeError:
            if index != len(lines) - 1:
                raise ValueError("Corrupt interior ledger line; audit required")
    sanitized = "\n".join(valid_lines) + ("\n" if valid_lines else "")
    tmp_path = ledger_path.with_suffix(".tmp")
    tmp_path.write_text(sanitized, encoding="utf-8")
    os.replace(tmp_path, ledger_path)


def compute_exact_mcnemar(b: int, c: int) -> float:
    """Exact two-sided McNemar test for paired binary outcomes.

    b: discordant pairs where Condition 1 succeeded and Condition 2 failed.
    c: discordant pairs where Condition 1 failed and Condition 2 succeeded.
    Under H0, b ~ Binomial(n_d, 0.5) where n_d = b + c.
    """
    n_d = b + c
    if n_d == 0:
        return 1.0
    k = min(b, c)
    prob_tail = sum(math.comb(n_d, i) for i in range(k + 1)) * (0.5**n_d)
    return min(1.0, 2.0 * prob_tail)


def compute_holm_bonferroni(p_values: List[float]) -> List[float]:
    """Holm-Bonferroni step-down multiplicity correction across m hypotheses."""
    m = len(p_values)
    if m == 0:
        return []
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    adjusted = [0.0] * m
    running_max = 0.0

    for rank, (orig_idx, p_val) in enumerate(indexed):
        adj = (m - rank) * p_val
        running_max = max(running_max, adj)
        adjusted[orig_idx] = min(1.0, running_max)

    return adjusted


@dataclass
class TrialRecord:
    """Structured record of a single trial execution."""

    task_id: str
    condition: ConditionType
    run_id: str
    replication: int = 1
    status: str = "completed"
    decision: str = "ready_for_requested_step"
    stop_reason: Optional[str] = None
    usage: Usage = field(default_factory=Usage)
    final_judgement: Optional[FinalJudgement] = None
    metric_record: Optional[EvaluationMetricRecord] = None
    output_payload_hash: Optional[str] = None
    timestamp: str = ""
    notes: Optional[str] = None
    executor: str = "synthetic"
    code_hash: Optional[str] = None
    prompt_hash: Optional[str] = None
    error_message: Optional[str] = None
    spec_hash: Optional[str] = None
    task_hash: Optional[str] = None
    final_state: Optional[Dict[str, Any]] = None
    steps: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    usage_known: bool = False
    wall_elapsed_ms: Optional[float] = None
    audit_required: bool = False

    @property
    def fda(self) -> int:
        return self.metrics.get(
            "fda", self.metric_record.fda if self.metric_record else None
        )

    @property
    def final_decision_success(self) -> int:
        return self.fda

    @property
    def recall_crit(self) -> float:
        return self.metrics.get(
            "recallCrit", self.metric_record.recall_crit if self.metric_record else None
        )

    @property
    def required_gap_recall(self) -> float:
        return self.metrics.get(
            "requiredGapRecall",
            self.metric_record.required_gap_recall if self.metric_record else None,
        )

    @property
    def far(self) -> float:
        return self.metrics.get(
            "far", self.metric_record.far if self.metric_record else None
        )

    @property
    def unnecessary_check_rate(self) -> float:
        return self.metrics.get(
            "unnecessaryCheckRate",
            self.metric_record.unnecessary_check_rate if self.metric_record else None,
        )

    @property
    def dsc(self) -> int:
        return self.metrics.get(
            "dsc", self.metric_record.dsc if self.metric_record else None
        )

    @property
    def warranted_abstention(self) -> Optional[int]:
        return self.metric_record.warranted_abstention if self.metric_record else None

    @property
    def unwarranted_abstention(self) -> Optional[int]:
        return self.metric_record.unwarranted_abstention if self.metric_record else None

    @property
    def efficiency_tool(self) -> float:
        return self.metrics.get(
            "efficiencyTool",
            self.metric_record.efficiency_tool if self.metric_record else None,
        )

    @property
    def efficiency_time(self) -> float:
        return self.metrics.get(
            "efficiencyTime",
            self.metric_record.efficiency_time if self.metric_record else None,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "taskId": self.task_id,
            "condition": self.condition.value,
            "runId": self.run_id,
            "replication": self.replication,
            "status": self.status,
            "decision": self.decision,
            "stopReason": self.stop_reason,
            "usage": self.usage.to_dict(),
            "finalJudgement": self.final_judgement.to_dict()
            if self.final_judgement
            else None,
            "metricRecord": self.metric_record.to_dict()
            if self.metric_record
            else None,
            "outputPayloadHash": self.output_payload_hash,
            "timestamp": self.timestamp,
            "notes": self.notes,
            "fda": self.fda,
            "recallCrit": self.recall_crit,
            "far": self.far,
            "dsc": self.dsc,
            "executor": self.executor,
            "codeHash": self.code_hash,
            "promptHash": self.prompt_hash,
            "errorMessage": self.error_message,
            "specHash": self.spec_hash,
            "taskHash": self.task_hash,
            "finalState": self.final_state,
            "steps": self.steps,
            "metrics": self.metrics,
            "usageKnown": self.usage_known,
            "wallElapsedMs": self.wall_elapsed_ms,
            "auditRequired": self.audit_required,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TrialRecord:
        fj = (
            FinalJudgement.from_dict(data["finalJudgement"])
            if data.get("finalJudgement")
            else None
        )
        mr = (
            EvaluationMetricRecord.from_dict(data["metricRecord"])
            if data.get("metricRecord")
            else None
        )
        return cls(
            task_id=str(data["taskId"]),
            condition=ConditionType(data["condition"]),
            run_id=str(data["runId"]),
            replication=int(data.get("replication", 1)),
            status=str(data.get("status", "completed")),
            decision=str(data.get("decision", "ready_for_requested_step")),
            stop_reason=data.get("stopReason"),
            usage=Usage.from_dict(data.get("usage", {})),
            final_judgement=fj,
            metric_record=mr,
            output_payload_hash=data.get("outputPayloadHash"),
            timestamp=str(data.get("timestamp", "")),
            notes=data.get("notes"),
            executor=str(data.get("executor", "synthetic")),
            code_hash=data.get("codeHash"),
            prompt_hash=data.get("promptHash"),
            error_message=data.get("errorMessage"),
            spec_hash=data.get("specHash"),
            task_hash=data.get("taskHash"),
            final_state=data.get("finalState"),
            steps=list(data.get("steps", [])),
            metrics=dict(data.get("metrics", {})),
            usage_known=bool(data.get("usageKnown", False)),
            wall_elapsed_ms=data.get("wallElapsedMs"),
            audit_required=bool(data.get("auditRequired", False)),
        )


def load_public_packets(
    partition_dir: Path,
    manifest_path: Optional[Path] = None,
    verify_hashes: bool = True,
    expected_count: Optional[int] = 24,
) -> List[TaskPacket]:
    """Load public TaskPackets from partition directory without leaking gold standards.

    Verifies cryptographic file hashes against manifest if present.
    Enforces exact expected packet counts and fail-closed integrity.
    """
    p_dir = Path(partition_dir)
    if p_dir.name == "unblinding_key.json" or any(
        part.lower() in ("gold", "cases") for part in p_dir.resolve().parts
    ):
        raise ValueError("Only public packet directories may be loaded")
    packets_dir = (
        p_dir / "public_packets" if (p_dir / "public_packets").exists() else p_dir
    )

    if not packets_dir.exists():
        raise FileNotFoundError(f"Packet directory '{packets_dir}' does not exist.")

    manifest_files: Dict[str, Any] = {}
    m_path = manifest_path or (p_dir / "manifest.json")
    if m_path.exists():
        manifest_data = json.loads(m_path.read_text(encoding="utf-8"))
        manifest_files = manifest_data.get("files", {})
    elif verify_hashes:
        raise FileNotFoundError(
            f"Required manifest file '{m_path}' not found for packet verification."
        )
    if verify_hashes and (not isinstance(manifest_files, dict) or not manifest_files):
        raise ValueError("Packet manifest must contain a non-empty files mapping")

    json_files = sorted(
        [f for f in packets_dir.glob("*.json") if f.name != "manifest.json"]
    )

    if expected_count is not None and len(json_files) != expected_count:
        raise ValueError(
            f"Expected {expected_count} packets in {packets_dir}, found {len(json_files)}"
        )

    packets: List[TaskPacket] = []
    seen_task_ids: Set[str] = set()

    for fpath in json_files:
        if (
            any(part.lower() in ("gold", "cases") for part in fpath.resolve().parts)
            or fpath.name == "unblinding_key.json"
        ):
            raise ValueError(
                "Private evaluation file cannot be loaded as a public packet"
            )
        if verify_hashes:
            rel_key = f"public_packets/{fpath.name}"
            if rel_key not in manifest_files:
                rel_key = fpath.name

            if rel_key not in manifest_files:
                raise ValueError(
                    f"Unlisted packet file '{fpath.name}' found in {packets_dir}"
                )

            expected_hash = manifest_files[rel_key].get("hash")
            if not isinstance(expected_hash, str) or len(expected_hash) != 64:
                raise ValueError(f"Missing or invalid packet hash: {fpath.name}")
            actual_hash = hash_file(fpath)
            if expected_hash and actual_hash != expected_hash:
                raise ValueError(
                    f"Hash mismatch for packet {fpath.name}: expected {expected_hash}, got {actual_hash}"
                )

        content = json.loads(fpath.read_text(encoding="utf-8"))

        # Explicit allowlist check: assert gold/answer keys are strictly absent
        forbidden_keys = {
            "ground_truth_verdicts",
            "groundTruthVerdicts",
            "critical_evidence_hashes",
            "criticalEvidenceHashes",
            "target_decision",
            "targetDecision",
            "gold",
            "answer_key",
            "unblinding_key",
        }
        leaked = forbidden_keys.intersection(content.keys())
        if leaked:
            raise ValueError(
                f"Gold leakage detected in public packet {fpath.name}: {leaked}"
            )

        packet = TaskPacket.from_dict(content)
        if packet.task_id in seen_task_ids:
            raise ValueError(f"Duplicate taskId '{packet.task_id}' in {fpath.name}")
        seen_task_ids.add(packet.task_id)
        packets.append(packet)

    return packets


def load_gold_standards(
    partition_dir: Path,
    manifest_path: Optional[Path] = None,
    verify_hashes: bool = True,
) -> Dict[str, GoldStandard]:
    """Load GoldStandard evaluation rubrics strictly for scoring routines.

    Operational agent runners must never access these files.
    """
    p_dir = Path(partition_dir)
    gold_dir = p_dir / "gold"
    if not gold_dir.exists():
        return {}

    manifest_files: Dict[str, Any] = {}
    m_path = manifest_path or (p_dir / "manifest.json")
    if m_path.exists():
        manifest_data = json.loads(m_path.read_text(encoding="utf-8"))
        manifest_files = manifest_data.get("files", {})

    gold_map: Dict[str, GoldStandard] = {}
    json_files = sorted(list(gold_dir.glob("*.json")))

    for fpath in json_files:
        if verify_hashes and manifest_files:
            rel_key = f"gold/{fpath.name}"
            if rel_key in manifest_files:
                expected_hash = manifest_files[rel_key].get("hash")
                actual_hash = hash_file(fpath)
                if expected_hash and actual_hash != expected_hash:
                    raise ValueError(
                        f"Hash mismatch for gold {fpath.name}: expected {expected_hash}, got {actual_hash}"
                    )

        content = json.loads(fpath.read_text(encoding="utf-8"))
        gold = GoldStandard.from_dict(content)
        gold_map[gold.task_id] = gold

    return gold_map


def load_dataset_partition(
    partition_dir: Path,
    include_gold: bool = False,
    verify_hashes: bool = True,
) -> Tuple[List[TaskPacket], Optional[Dict[str, GoldStandard]]]:
    """Load an entire dataset partition, isolating gold unless explicitly requested for evaluation."""
    packets = load_public_packets(partition_dir, verify_hashes=verify_hashes)
    gold = (
        load_gold_standards(partition_dir, verify_hashes=verify_hashes)
        if include_gold
        else None
    )
    return packets, gold


def get_completed_trial_keys(
    output_dir: Path, partition: str = "dev"
) -> Set[Tuple[str, str, int]]:
    """Scan existing output directory to determine already completed (task_id, condition, replication) keys."""
    trials_dir = Path(output_dir) / partition / "trials"
    if not trials_dir.exists():
        return set()

    completed: Set[Tuple[str, str, int]] = set()
    for fpath in trials_dir.glob("*.json"):
        try:
            data = json.loads(fpath.read_text(encoding="utf-8"))
            task_id = str(data.get("taskId"))
            cond = str(data.get("condition"))
            rep = int(data.get("replication", 1))
            if task_id and cond:
                completed.add((task_id, cond, rep))
        except Exception:
            continue
    return completed


def export_masked_assessor_dataset(
    records: List[TrialRecord],
    output_dir: Path,
    seed: Optional[int] = None,
) -> Tuple[Path, Path]:
    """Export single-blind masked assessor evaluation set with unpredictable UUID trial keys.

    Masks condition labels (A-E -> MCOND_01-05) and assigns random UUID4 identifiers.
    Usage and call-count fingerprints are strictly stripped to prevent de-anonymization.
    Stores the unblinding key separately.
    """
    assessor_dir = Path(output_dir) / "assessor"
    assessor_dir.mkdir(parents=True, exist_ok=True)

    rng = random.Random(seed) if seed is not None else random.Random()
    conditions = ["A", "B", "C", "D", "E"]
    shuffled_conditions = list(conditions)
    rng.shuffle(shuffled_conditions)
    cond_to_mask = {c: f"MCOND_{i + 1:02d}" for i, c in enumerate(shuffled_conditions)}
    mask_to_cond = {v: k for k, v in cond_to_mask.items()}

    masked_records: List[Dict[str, Any]] = []
    unblinding_trials: Dict[str, Any] = {}

    for rec in records:
        masked_trial_id = str(uuid.uuid4())
        mcond = cond_to_mask[rec.condition.value]

        # Strip call counts and resource usage to prevent fingerprinting
        masked_item = {
            "maskedTrialId": masked_trial_id,
            "taskId": rec.task_id,
            "maskedConditionId": mcond,
            "finalJudgement": {
                key: value
                for key, value in rec.final_judgement.to_dict().items()
                if key != "resourceUsage"
            }
            if rec.final_judgement
            else None,
        }
        masked_records.append(masked_item)

        unblinding_trials[masked_trial_id] = {
            "taskId": rec.task_id,
            "condition": rec.condition.value,
            "runId": rec.run_id,
            "replication": rec.replication,
            "maskedConditionId": mcond,
        }

    dataset_path = assessor_dir / "masked_evaluation_set.json"
    tmp_set = dataset_path.with_suffix(".tmp")
    tmp_set.write_text(json.dumps(masked_records, indent=2), encoding="utf-8")
    os.replace(tmp_set, dataset_path)

    private_dir = Path(output_dir) / "private_assessor"
    private_dir.mkdir(parents=True, exist_ok=True)
    unblinding_path = private_dir / "assessor_mapping.json"
    unblinding_doc = {
        "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "seed": seed,
        "conditionMapping": cond_to_mask,
        "reverseConditionMapping": mask_to_cond,
        "trials": unblinding_trials,
    }
    tmp_key = unblinding_path.with_suffix(".tmp")
    tmp_key.write_text(json.dumps(unblinding_doc, indent=2), encoding="utf-8")
    os.replace(tmp_key, unblinding_path)

    return dataset_path, unblinding_path


class ResearchHarness:
    """Run the R3 external graph with a single locked campaign registry."""

    def __init__(
        self,
        output_dir,
        ledger_path=None,
        seal_manifest_path=None,
        resource_registry=None,
        runtime_freeze_path=None,
        max_step_attempts=2,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.ledger = RunLedger(ledger_path or self.output_dir / "ledger.jsonl")
        self.campaign_lock = RunLedger(self.output_dir / "campaign.jsonl")
        self.seal_manifest_path = Path(
            seal_manifest_path or "research/seal_manifest.json"
        )
        self.runtime_freeze_path = Path(
            runtime_freeze_path or "research/runtime_freeze_r4.json"
        )
        self.resource_registry = resource_registry or GlobalResourceRegistry()
        self.resource_registry.storage_path = self.output_dir / "resource_registry.json"
        if max_step_attempts not in (1, 2):
            raise ValueError("Retry policy permits at most two attempts per step")
        self.max_step_attempts = max_step_attempts
        self._locked = False

    def verify_environment(self, require_release=False):
        if not self.seal_manifest_path.exists():
            raise FileNotFoundError(f"Seal manifest missing: {self.seal_manifest_path}")
        verify_seal_manifest(
            json.loads(self.seal_manifest_path.read_text(encoding="utf-8"))
        )
        return verify_runtime_freeze(
            self.runtime_freeze_path, require_release=require_release
        )

    def _load_registry(self):
        self.resource_registry.load_from_path(self.resource_registry.storage_path)
        if any(
            trial.get("auditRequired")
            for trial in self.resource_registry.trials.values()
        ):
            raise ValueError("Campaign is stopped pending an ambiguous-dispatch audit")
        # Existing pre-R3 outputs must be explicitly audited, never silently reused or moved.
        for partition in ("dev", "heldout"):
            legacy = self.output_dir / partition / "resource_registry.json"
            if legacy.exists():
                raise ValueError(
                    "Legacy partition registry requires audited migration; choose fresh output"
                )

    def evaluate_task(
        self,
        task,
        gold=None,
        condition=ConditionType.E,
        run_id="run_001",
        executor_func=None,
        replication=1,
        executor_name="synthetic",
        partition="mechanism",
    ):
        if not self._locked:
            self.campaign_lock.acquire_lock(run_id)
            self._locked = True
            try:
                self._load_registry()
                return self.evaluate_task(
                    task,
                    gold,
                    condition,
                    run_id,
                    executor_func,
                    replication,
                    executor_name,
                    partition,
                )
            finally:
                self._locked = False
                self.campaign_lock.release_lock()
        hashes = self.verify_environment()
        if executor_func is None:
            raise ValueError("executor_func is required")
        if executor_name.startswith("t3"):
            if getattr(executor_func, "synthetic_fallback", False):
                raise ValueError("Synthetic fallback cannot be used for a T3 campaign")
            if not hasattr(executor_func, "require_public_boundary"):
                raise ValueError("T3 executor requires a verified public boundary")
            executor_func.require_public_boundary()
        # The synthetic path makes no paid calls, so each step reserves 0 yen.
        # Paid executors must still declare an enforced per-call cap.
        if executor_name == "synthetic":
            cost_cap = 0.0
        else:
            cost_cap = getattr(executor_func, "enforced_cost_cap_yen", None)
            if not is_bounded_cost(cost_cap):
                raise ValueError(
                    "Executor must expose a finite, non-negative enforced_cost_cap_yen per call"
                )
        if executor_name == "t3":
            self.verify_environment(require_release=True)
        trial_key = f"{partition}/{task.task_id}/{condition.value}/{replication}"
        identity = {key: hashes[key] for key in ("codeHash", "promptHash", "specHash")}
        identity.update(
            taskHash=compute_payload_hash(task.to_dict()),
            executor=executor_name,
            runId=run_id,
            retryPolicy=self.max_step_attempts,
        )
        self.resource_registry.begin_trial(trial_key, condition, identity)
        from ommatidia.state import create_initial_state

        state = create_initial_state(task)
        steps = []
        started = time.perf_counter()
        step_lock = threading.RLock()

        def metered_executor(step_name, payload):
            last_error = None
            for attempt in range(1, self.max_step_attempts + 1):
                with step_lock:
                    usage = self.resource_registry.trial_usage(trial_key)
                    if (time.perf_counter() - started) * 1000 >= min(
                        180000, task.budget.max_elapsed_ms
                    ):
                        raise ResourceLimitExceeded("Trial wall-clock deadline reached")
                    step_payload = dict(payload)
                    step_payload["clientRequestId"] = (
                        "ommatidia_"
                        + _sha256_of_str(trial_key + "/" + payload["clientRequestId"])
                        + f"_attempt_{attempt}"
                    )
                    tools_left = min(12, task.budget.max_tool_calls) - usage.tool_calls
                    tools_left = min(
                        tools_left,
                        payload.get("context", {}).get("toolAllocation", tools_left),
                    )
                    step_payload["stepBudget"] = {
                        "maxModelCalls": 1,
                        "maxToolCalls": tools_left,
                        "maxElapsedMs": max(
                            0,
                            min(180000, task.budget.max_elapsed_ms)
                            - max(
                                usage.elapsed_ms, (time.perf_counter() - started) * 1000
                            ),
                        ),
                        "maxOutputTokens": min(
                            4000, task.budget.max_output_tokens_per_call
                        ),
                    }
                    prompt_chars = len(render_prompt(step_payload))
                    step_id = step_payload["clientRequestId"]
                    self.resource_registry.reserve_step(
                        trial_key,
                        step_id,
                        tools_left,
                        prompt_chars,
                        task.budget,
                        reserved_cost_yen=cost_cap,
                    )
                    entry = {
                        "stepId": step_id,
                        "stepName": step_name,
                        "attempt": attempt,
                        "inputHash": compute_payload_hash(step_payload),
                        "status": "reserved",
                        "providerInstanceId": getattr(
                            executor_func, "provider_instance_id", "synthetic"
                        ),
                        "model": getattr(executor_func, "model_id", "synthetic"),
                        "taskId": None,
                    }
                    steps.append(entry)

                    def observe(
                        metadata, observed_step_id=step_id, observed_entry=entry
                    ):
                        with step_lock:
                            observed_entry.update(metadata)
                            self.resource_registry.annotate_dispatch(
                                observed_step_id, metadata
                            )

                    if hasattr(executor_func, "dispatch_observers"):
                        executor_func.dispatch_observers[step_id] = observe
                step_started = time.perf_counter()
                known = False
                measured = Usage(model_calls=1, input_chars=prompt_chars)
                output = None
                error = None
                try:
                    output = executor_func(step_name, step_payload)
                    if not isinstance(output, dict):
                        raise ValueError("Executor must return an object")
                    check_public_payload(output)
                    if output.get("_dispatch"):
                        observe(output["_dispatch"])
                    raw = (
                        output.get("_hostUsage")
                        if getattr(executor_func, "host_metered", False)
                        else output.get("usage")
                    )
                    known = isinstance(raw, dict) and "toolCalls" in raw
                    if isinstance(raw, dict):
                        candidate = Usage.from_dict(raw)
                        validate_usage(candidate)
                        measured = candidate
                    measured.model_calls = max(1, measured.model_calls)
                    measured.input_chars = max(prompt_chars, measured.input_chars)
                except Exception as exc:
                    error = exc
                    known = False
                finally:
                    if executor_name == "synthetic":
                        # The synthetic path makes no paid call, so its spend is known to be zero.
                        known = True
                        measured.cost_yen = 0.0
                    with step_lock:
                        measured.elapsed_ms = max(
                            measured.elapsed_ms,
                            (time.perf_counter() - step_started) * 1000,
                        )
                        entry["status"] = (
                            "completed"
                            if output is not None and error is None
                            else "failed"
                        )
                        self.resource_registry.settle_step(
                            step_id, measured, known, entry["status"]
                        )
                        state.usage = self.resource_registry.trial_usage(trial_key)
                        entry["usage"] = self.resource_registry.calls[step_id]["usage"]
                        entry["usageKnown"] = known
                        entry["outputHash"] = (
                            compute_payload_hash(output) if output is not None else None
                        )
                        stage = (
                            LedgerStage.RETRY
                            if attempt > 1
                            else (
                                LedgerStage.SYNTHESIS
                                if "synth" in step_name
                                else LedgerStage.PLANNING
                                if "plan" in step_name or "inspect" in step_name
                                else LedgerStage.INVESTIGATOR
                            )
                        )
                        self.ledger.record_stage(
                            stage,
                            step_id,
                            task.task_id,
                            condition,
                            entry["inputHash"],
                            entry["outputHash"] or _sha256_of_str("failure"),
                            measured,
                            entry["status"],
                            model=entry["model"],
                        )
                if state.usage.exceeds(task.budget):
                    # maxRounds is a legacy iteration bound; the protocol call limit is authoritative.
                    if (
                        state.usage.model_calls > min(8, task.budget.max_model_calls)
                        or state.usage.tool_calls > min(12, task.budget.max_tool_calls)
                        or state.usage.elapsed_ms
                        > min(180000, task.budget.max_elapsed_ms)
                    ):
                        raise ResourceLimitExceeded("Trial resource envelope exceeded")
                if error is None:
                    return output
                last_error = error
                # Only a transport error is retried. Invalid JSON, blank answers and cap breaches are terminal.
                if not isinstance(error, (TimeoutError, ConnectionError)):
                    raise error
            raise last_error

        status, error_message, audit_required = "completed", None, False
        try:
            state, invalid = execute_graph(
                task,
                condition,
                run_id,
                metered_executor,
                lambda: self.resource_registry.trial_usage(trial_key),
                state=state,
            )
            if invalid:
                status = "invalid_response"
        except Exception as exc:
            from ommatidia.t3_adapter import CampaignAuditRequired

            audit_required = isinstance(exc, CampaignAuditRequired) or bool(
                self.resource_registry.trials[trial_key].get("auditRequired")
            )
            status, error_message = "failed", str(exc)
            state.usage = self.resource_registry.trial_usage(trial_key)
            state.final_judgement = inconclusive(
                task.task_id, state.usage, f"Execution failed: {exc}"
            )
            state.decision = Decision.BLOCKED
            state.stop_reason = str(exc)
        rec = TrialRecord(
            task.task_id,
            condition,
            run_id,
            replication=replication,
            status=status,
            decision="failed" if status == "failed" else state.decision.value,
            stop_reason=state.stop_reason,
            usage=state.usage,
            final_judgement=state.final_judgement,
            output_payload_hash=compute_payload_hash(state.to_dict()),
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            executor=executor_name,
            code_hash=hashes["codeHash"],
            prompt_hash=hashes["promptHash"],
            spec_hash=hashes["specHash"],
            task_hash=identity["taskHash"],
            final_state=state.to_dict(),
            steps=steps,
            usage_known=bool(steps) and all(step.get("usageKnown") for step in steps),
            error_message=error_message,
            wall_elapsed_ms=(time.perf_counter() - started) * 1000,
            audit_required=audit_required,
        )
        if gold is not None:
            try:
                rec.metrics = score_saved_trial(rec, gold)
            except ValueError as exc:
                rec.notes = f"Scoring unavailable: {exc}"
        trial_file = (
            self.output_dir
            / partition
            / "trials"
            / f"{task.task_id}_{condition.value}_{replication}.json"
        )
        atomic_json(trial_file, rec.to_dict())
        if audit_required:
            self.resource_registry.trials[trial_key]["auditRequired"] = True
        self.resource_registry.finish_trial(
            trial_key, status, compute_payload_hash(rec.to_dict())
        )
        return rec

    def run_cohort(
        self,
        tasks,
        conditions,
        run_id,
        executor_func,
        gold_standards=None,
        partition="dev",
        resume=True,
        replication=1,
        executor_name="synthetic",
    ):
        self.verify_environment()
        if len({task.task_id for task in tasks}) != len(tasks) or len(
            set(conditions)
        ) != len(conditions):
            raise ValueError("Duplicate task or condition")
        self.campaign_lock.acquire_lock(run_id)
        self._locked = True
        try:
            self._load_registry()
            sanitize_ledger_file(self.ledger.ledger_path)
            hashes = fingerprints()
            trials_dir = self.output_dir / partition / "trials"
            # Reconcile all records in the campaign, including the other partition, without adding totals.
            for file in self.output_dir.glob("*/trials/*.json"):
                rec = TrialRecord.from_dict(
                    json.loads(file.read_text(encoding="utf-8"))
                )
                key = f"{file.parent.parent.name}/{rec.task_id}/{rec.condition.value}/{rec.replication}"
                reserved = self.resource_registry.trials.get(key)
                if not reserved:
                    raise ValueError(
                        "Unregistered saved trial; legacy output needs audited migration"
                    )
                record_hash = compute_payload_hash(rec.to_dict())
                if (
                    rec.usage.to_dict()
                    != self.resource_registry.trial_usage(key).to_dict()
                ):
                    raise ValueError(
                        "Trial usage differs from durable dispatch reservations"
                    )
                if reserved.get("recordHash") and reserved["recordHash"] != record_hash:
                    raise ValueError("Saved trial differs from campaign checkpoint")
                if reserved["status"] == "running":
                    # Record was durable but process died before completion checkpoint.
                    self.resource_registry.finish_trial(key, rec.status, record_hash)
            records = []
            for task in tasks:
                for condition in conditions:
                    key = f"{partition}/{task.task_id}/{condition.value}/{replication}"
                    trial_file = (
                        trials_dir
                        / f"{task.task_id}_{condition.value}_{replication}.json"
                    )
                    if key in self.resource_registry.trials:
                        if not resume or not trial_file.exists():
                            raise ValueError(
                                "Reserved trial has no resumable record; audit required, no redispatch"
                            )
                        rec = TrialRecord.from_dict(
                            json.loads(trial_file.read_text(encoding="utf-8"))
                        )
                        identity = self.resource_registry.trials[key]["identity"]
                        expected = {
                            name: hashes[name]
                            for name in ("codeHash", "promptHash", "specHash")
                        }
                        expected.update(
                            taskHash=compute_payload_hash(task.to_dict()),
                            executor=executor_name,
                            runId=run_id,
                            retryPolicy=self.max_step_attempts,
                        )
                        if identity != expected or any(
                            getattr(rec, attr) != expected[name]
                            for attr, name in (
                                ("code_hash", "codeHash"),
                                ("prompt_hash", "promptHash"),
                                ("spec_hash", "specHash"),
                                ("task_hash", "taskHash"),
                                ("executor", "executor"),
                                ("run_id", "runId"),
                            )
                        ):
                            raise ValueError(
                                "Resume provenance mismatch; existing record preserved"
                            )
                    else:
                        rec = self.evaluate_task(
                            task,
                            gold_standards.get(task.task_id)
                            if gold_standards
                            else None,
                            condition,
                            run_id,
                            executor_func,
                            replication,
                            executor_name,
                            partition,
                        )
                    records.append(rec)
                    if rec.audit_required:
                        raise ValueError(
                            "Campaign stopped after persisting ambiguous-dispatch failure; audit required"
                        )
            atomic_json(
                self.output_dir / partition / "summary.json",
                {
                    "runId": run_id,
                    "partition": partition,
                    "executor": executor_name,
                    "trialCount": len(records),
                    "failedTrials": sum(r.status != "completed" for r in records),
                    "resourceUsage": self.resource_registry.to_dict(),
                },
            )
            return records
        finally:
            self._locked = False
            self.campaign_lock.release_lock()

    def run_paired_comparison(self, *args, **kwargs):
        raise ValueError(
            "Use analyse_saved_trials on a complete saved 24-case matrix; comparisons never dispatch"
        )
