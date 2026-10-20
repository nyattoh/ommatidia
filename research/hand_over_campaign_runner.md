> R3 notice (2026-10-15): Readiness and implementation claims below are historical and superseded by [the R3 driver contract](runtime-driver-r3.md) and [the R3 remediation handover](hand_over_runtime_fix_r3.md). No empirical study has been completed; the evaluation package requires replacement after the disclosed boundary violation.

# Ommatidia Production Campaign Runner Hand-over

**Document Version:** 1.0.0  
**Date:** 2026-10-15  
**Author:** Implementation Sub-agent  
**Language:** British English  
**Status:** Verification Complete. Production runner ready for in-session T3 dispatch and cohort execution.

---

## 1. Executive Summary

This document specifies the operational interface and execution protocol for the Ommatidia campaign runner. The runner supports executing the full benchmark matrix of 240 trials (Phase 1: 120 dev trials; Phase 2: 120 held-out trials) while strictly enforcing:
1. **Gold Isolation:** Operational agents receive public task packets only; gold rubrics and held-out answers are segregated from operational contexts.
2. **Resource Ceilings:** Global cap of 240 trials, 1,920 aggregate model invocations, 2,880 aggregate tool invocations, and per-trial caps (8 model calls, 12 tool calls, 180s, 48,000 chars).
3. **Crash Consistency:** Trial-by-trial atomic JSON checkpointing with automatic resumption (`--resume`) to prevent duplicate executions and wasted token quotas.
4. **T3 Code Integration:** Standalone export of pre-formulated, sealed `DispatchReadyJob` records and in-session `T3CampaignController` for execution via native T3 child delegation (`delegate_task`).
5. **Assessor Masking:** Single-blind export with neutral condition identifiers (`MCOND_01..05`), RFC 4122 UUID4 trial keys, and a securely isolated unblinding key.

---

## 2. Experimental Execution Matrix

The pre-registered evaluation matrix partitions cases across conditions and phases without pooling development and held-out cases into the same denominator:

| Phase | Partition | Cases | Conditions | Replications | Total Trials | Model Call Ceiling | Tool Call Ceiling | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Phase 1** | Development (`dev`) | 24 | 5 (A–E) | 1 | 120 | 960 | 1,440 | Verified & Ready |
| **Phase 2** | Held-Out (`heldout`) | 24 | 5 (A–E) | 1 | 120 | 960 | 1,440 | Pre-registration Freeze (Awaiting Holdout Seal) |
| **Total** | Aggregate Benchmark | 48 | 5 | 1 | **240** | **1,920** | **2,880** | Pre-registered Upper Ceiling |

---

## 3. CLI Operation Modes (`scripts/run_harness.py`)

The unified CLI provides 7 dedicated operating modes:

### 3.1 Mechanism Verification (`--mode mechanism_check`)
Runs dev unit fixtures to verify internal state-machine transitions and invalidation cascades:
```powershell
python scripts/run_harness.py --mode mechanism_check --condition-primary E --output-dir research/output
```

### 3.2 Dispatch Plan Generation (`--mode plan`)
Generates dispatch-ready trial jobs for in-session T3 execution without executing live calls:
```powershell
python scripts/run_harness.py --mode plan --partition dev --output-dir research/output --run-id campaign_001
```
*Output Artifact:* `research/output/dispatch_plan_dev.json` (120 structured trial jobs).

### 3.3 Development Cohort Execution (`--mode run_dev`)
Executes the 24 development cases across conditions A–E with automatic resume and resource tracking:
```powershell
python scripts/run_harness.py --mode run_dev --executor synthetic --output-dir research/output --run-id campaign_dev_001
```
*Output Artifacts:*
- `research/output/dev/trials/<taskId>_<condition>.json` (120 trial records)
- `research/output/dev/summary.json` (aggregate cohort metrics and resource counters)
- `research/output/ledger.jsonl` (append-only crash-consistent event log)

### 3.4 Held-Out Cohort Execution (`--mode run_heldout`)
Enforces the pre-registration freeze boundary. If `research/datasets/heldout` or `research/holdout_manifest.json` are absent, execution halts cleanly:
```powershell
python scripts/run_harness.py --mode run_heldout --output-dir research/output --run-id campaign_heldout_001
```

### 3.5 Objective Evaluation (`--mode evaluate`)
Scores completed trials in an output partition against objective gold rubrics:
```powershell
python scripts/run_harness.py --mode evaluate --partition dev --output-dir research/output
```
*Output Artifact:* `research/output/dev/evaluation_report.json`.

### 3.6 Masked Assessor Export (`--mode mask_assessor`)
Generates single-blind masked evaluation datasets for unbiased human and LLM evaluation:
```powershell
python scripts/run_harness.py --mode mask_assessor --partition dev --output-dir research/output --seed 42
```
*Output Artifacts:*
- `research/output/assessor/masked_evaluation_set.json` (Anonymised condition labels and UUID4 keys)
- `research/output/assessor/unblinding_key.json` (Restricted decryption and mapping key)

### 3.7 Paired Condition Comparison (`--mode paired_compare`)
Computes paired statistics ($\Delta FDA$, Wilcoxon signed-rank tests, Wilson score intervals):
```powershell
python scripts/run_harness.py --mode paired_compare --condition-primary E --condition-baseline D --output-dir research/output
```

---

## 4. T3 Code Orchestration and In-Session Controller Protocol

### 4.1 Subprocess Boundary Limitation
In T3 Code environments where `T3_ACP_MCP_NODE` is unset, external standalone Python subprocesses cannot directly invoke T3's in-process MCP tools (`delegate_task`, `task_status`). The harness enforces strict operational integrity:
- It does **not** invent mock environment variables or bypass mechanisms.
- It provides two sanctioned execution workflows:
  1. **Batch Plan Dispatch Workflow:** Generate the plan via `--mode plan`, then iterate through jobs using an active in-session T3 agent driving `delegate_task`.
  2. **In-Session Controller Workflow:** An in-session agent passes its live tool callable into `T3DelegationAdapter(in_session_dispatcher=...)` or uses `T3CampaignController`.

### 4.2 In-Session Controller Example
```python
from ommatidia.t3_adapter import DispatchReadyJob, T3CampaignController

# Initialize controller with in-session tool caller
controller = T3CampaignController(dispatcher_func=session_tool_caller)

# Dispatch trial job
task_id = controller.dispatch_job(job)

# Poll for completion
status = controller.check_task(task_id)
if status.get("status") == "completed":
    result = status.get("result")
    # Ingest into understanding state and save TrialRecord
```

---

## 5. Pre-Registration Boundaries and Held-out Integrity

1. **Held-out Asset Ownership:** The concurrent holdout builder writes:
   - `research/datasets/heldout`
   - `research/holdout_manifest.json`
   - `research/hand_over_heldout.md`
   - `research/seal_manifest.json`
   These files were strictly untouched and preserved.
2. **Zero-Inspection Enforcement:** The production harness loads `public_packets/` exclusively. At no point during trial execution are gold answers or held-out rubrics accessible to the operational model.
3. **Execution Freeze:** Production held-out runs will commence only after the holdout builder commits and seals the held-out partition.
