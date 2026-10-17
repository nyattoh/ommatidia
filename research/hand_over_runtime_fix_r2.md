# Ommatidia Runtime Remediation Hand-over (Round 2)

**Document Version:** 2.0.0  
**Date:** 2026-10-15  
**Author:** Implementation Sub-agent (`gemini-3.8-flash-high`, vendor Google)  
**Language:** British English  
**Status:** Remediation Round 2 Complete. 57 passing unit tests. Fail-closed execution contracts, atomic campaign-wide resource accounting, exact metric schemas, and single-blind masking implemented.

---

## 1. Executive Summary & Review Remediation

This hand-over report documents the complete remediation of the eight blocking findings (B1–B8) identified in the independent cross-vendor code review ([research/review-runtime-round2.md](file:///D:/develop/works/ommatidia/research/review-runtime-round2.md), Anthropic `claude-sonnet-5-5`, high effort). 

The runtime code in `src/ommatidia/harness.py`, `src/ommatidia/t3_adapter.py`, `src/ommatidia/state.py`, and `scripts/run_harness.py` has been systematically refactored. The test suite has been expanded from 47 to 57 unit tests, verifying fail-closed execution, atomic resume reconciliation, negative usage rejection, unknown cost preservation, exact McNemar hypothesis testing, and single-blind masking.

In strict adherence to repository and user instructions:
- **No Production Runs:** No production campaign or held-out evaluation was initiated during this code-fix task.
- **Zero Gold Touch:** No held-out gold, answer keys, seal manifests, or unblinding keys were viewed, modified, or executed.
- **Fail Closed:** If T3 child delegation is unavailable, `--executor t3` halts immediately with exit code 1; silent fallback to synthetic fixtures has been completely eliminated.
- **Strict Whitelist:** Edits were strictly confined to allowed implementation files (`harness.py`, `t3_adapter.py`, `state.py`, `run_harness.py`, relevant tests, `runtime-design.md`, `hand_over_runtime.md`, `hand_over_runtime_fix_r2.md`, and `task-gate-runtime-state.json`).

---

## 2. Detailed Audit of Addressed Review Findings (B1–B8)

### 2.1 B1: Silent Fallback and Executor Provenance
- **Defect in Round 2:** `--executor t3` caught all exceptions in `create_t3_executor` and silently substituted synthetic dummy fixtures; `TrialRecord` lacked executor provenance.
- **Remediation Implemented:**
  - `create_t3_executor` in [src/ommatidia/t3_adapter.py](file:///D:/develop/works/ommatidia/src/ommatidia/t3_adapter.py) now defaults to `fallback_executor=None` and fails closed by raising `T3DelegationError`.
  - In [scripts/run_harness.py](file:///D:/develop/works/ommatidia/scripts/run_harness.py), `--executor t3` verifies that either the T3 ACP MCP Node CLI or an active in-session tool dispatcher is present; if neither is available, it terminates immediately with exit code 1.
  - `TrialRecord` in [src/ommatidia/harness.py](file:///D:/develop/works/ommatidia/src/ommatidia/harness.py) now explicitly records `executor` (`"synthetic"`, `"t3"`), `code_hash`, `prompt_hash`, and `error_message`.
  - Resumption logic in `ResearchHarness.run_cohort` compares the saved `rec.executor` against the active executor. Mismatched records (e.g. attempting to resume a live `t3` run using existing `synthetic` records) are rejected and re-executed.

### 2.2 B2: Child Verdict Ingestion and Condition Sequence Fidelity
- **Defect in Round 2:** Child responses were never ingested into `FinalJudgement`; A/B defaulted to `supported`, C had no probes and raised on live observations (defaulting to `inconclusive`), and D/E dropped assessments. Blank or contradictory outputs synthesized `supported` with confidence 1.0.
- **Remediation Implemented:**
  - `ResearchHarness.evaluate_task` ingests child outputs via `ingest_final_judgement`. If a child response is missing, blank, unparseable, or invalid, it records `verdict="inconclusive"`, `confidence_score=0.0`, and justification noting the failure. Contradictory child verdicts are faithfully preserved.
  - In [src/ommatidia/state.py](file:///D:/develop/works/ommatidia/src/ommatidia/state.py), `apply_observations` is now tolerant to observations without pre-declared probes (such as Condition C fixed-lens queries), preventing unhandled `ValueError` crashes.
  - `create_condition_dispatch_jobs` in [src/ommatidia/t3_adapter.py](file:///D:/develop/works/ommatidia/src/ommatidia/t3_adapter.py) now generates the full sequence of trial jobs across all conditions:
    - Condition A: `single_pass_investigation`
    - Condition B: `pass1_investigation` and `pass2_reflection` (`PROMPT_CONDITION_B_PHASE2`)
    - Condition C: 5 mandatory lenses (`lens_scope`, `lens_counter`, `lens_temporal`, `lens_depend`, `lens_redundant`)
    - Condition D: `adaptive_plan_step`, `single_investigator_exec`, and `adaptive_synthesis`
    - Condition E: `ommatidia_coordinator`, `ommatidia_investigate_batch`, and `ommatidia_synthesis` (`PROMPT_CONDITION_E_SYNTHESIS`)

### 2.3 B3: Campaign-Wide Resource Accounting and Resume Persistence
- **Defect in Round 2:** `GlobalResourceRegistry` was in-memory only and reset to 0 in each process; skipped trials on resume were omitted from counters; killed runs were lost; `state.py:138` double-counted tool calls; `state.py:141-149` promoted `None` (unknown) cost to known.
- **Remediation Implemented:**
  - `GlobalResourceRegistry` is now persisted atomically to disk (`resource_registry.json`) using temporary file renaming (`os.replace`).
  - On initialization or resume, `ResearchHarness.run_cohort` loads and reconciles existing trial records so that aggregate consumption across process restarts is strictly cumulative and never resets to 0.
  - In [src/ommatidia/state.py](file:///D:/develop/works/ommatidia/src/ommatidia/state.py), `apply_observations` defaults to `track_tool_calls=False`, eliminating double-counting of tool calls and elapsed time already accumulated at the step level via `_accumulate_step_usage`.
  - In [src/ommatidia/state.py](file:///D:/develop/works/ommatidia/src/ommatidia/state.py), cost and token additions enforce that `None` (unknown) + known remains strictly `None`. Unknown values are never promoted to known.
  - `GlobalResourceRegistry.record_step` rejects negative usage values (`model_calls < 0`, `tool_calls < 0`, `elapsed_ms < 0`, `input_chars < 0`, `cost_yen < 0`, `total_tokens < 0`), raising `ValueError`.

### 2.4 B4: Crash-Safe Failed-Trial Accounting and Denominator Integrity
- **Defect in Round 2:** Executor exceptions aborted the cohort with no record; evaluate mode silently omitted trials without a judgement, breaking the pre-registered $N=24$ case denominator.
- **Remediation Implemented:**
  - `ResearchHarness.evaluate_task` wraps runner execution in a structured exception handler. If an executor or network failure occurs, a `TrialRecord` with `status="failed"`, `decision="failed"`, `stop_reason=str(exc)`, and `error_message=str(exc)` is created, saved atomically, and counted in the registry.
  - In [scripts/run_harness.py](file:///D:/develop/works/ommatidia/scripts/run_harness.py) `--mode evaluate`, failed or missing trials are retained in the evaluation denominator with `fda=0` and `recall_crit=0.0`.
  - Ledger reading in [src/ommatidia/harness.py](file:///D:/develop/works/ommatidia/src/ommatidia/harness.py) is guarded by `sanitize_ledger_file`, which cleans any incomplete or torn trailing line resulting from an ungraceful process kill, preventing resume deadlocks.

### 2.5 B5: Live-Run Integrity, Host Measurement, and Schema Dispatch
- **Defect in Round 2:** Usage relied entirely on child self-reporting; no host wall-clock or character metering; children were dispatched without `proposedAnswer`, `budget`, or output schema; timeouts left orphaned child executions.
- **Remediation Implemented:**
  - Host execution in `ResearchHarness.evaluate_task` measures wall-clock elapsed time using `time.perf_counter()` and payload size using `len(json.dumps(payload))`, taking the maximum of self-reported and host-measured values.
  - Pre-dispatch character check: if the formatted prompt exceeds the pre-registered ceiling of 48,000 characters, execution halts before dispatch.
  - Pre-dispatch reservation: `self.resource_registry.reserve_model_call(1)` verifies quota availability before dispatching.
  - On delegation timeout in `T3DelegationAdapter.delegate_step`, `task_cancel` is invoked before raising `TimeoutError` to prevent runaway child execution.
  - Every dispatch job prompt and payload includes `proposedAnswer`, `budget`, and the strict `FinalJudgement` JSON schema.
  - In `T3CampaignController.dispatch_job`, the returned task identifier is validated against empty strings and `"None"` to prevent false dispatch confirmations.

### 2.6 B6: Pre-Registration Freeze and Manifest Verification
- **Defect in Round 2:** Dataset loading accepted unlisted files or deleted files without error; `holdout_manifest.json` lacked a `files` key and bypassed verification; `run_heldout` exited 0 when files were absent.
- **Remediation Implemented:**
  - `load_public_packets` in [src/ommatidia/harness.py](file:///D:/develop/works/ommatidia/src/ommatidia/harness.py) enforces exact expected file counts ($N=24$), verifies file presence against `manifest.json`, rejects unlisted or duplicate files, and checks SHA-256 hashes.
  - In [scripts/run_harness.py](file:///D:/develop/works/ommatidia/scripts/run_harness.py), `--mode run_heldout` checks for `research/datasets/heldout/manifest.json` (with its `files` dictionary), verifies schema, and exits with code 1 (fail closed) if any asset is missing or incomplete.

### 2.7 B7: Scorer Alignment and Pre-Declared Paired Statistics
- **Defect in Round 2:** `--mode evaluate` constructed an empty state resulting in degenerate metrics; `Recall_crit` credited evidence already in task inputs; exact McNemar, Holm, and Wilcoxon tests were absent; `paired_compare` re-ran synthetic fixtures.
- **Remediation Implemented:**
  - `--mode evaluate` scores saved `TrialRecord`s directly against gold standards.
  - `Recall_crit` excludes evidence hashes present in the input `TaskPacket.evidence`, crediting only novel evidence retrieved by the agent.
  - Implemented exact two-sided McNemar test (`compute_exact_mcnemar`) using standard library `math.comb` for paired binary FDA differences.
  - Implemented Holm-Bonferroni step-down multiplicity correction (`compute_holm_bonferroni`) to control family-wise error rates across primary hypotheses H1–H4.
  - `--mode paired_compare` reads stored, collected trial records from `output_dir / partition / trials` rather than executing synthetic fixtures, computing paired FDA differences, Wilson 95% score intervals, exact McNemar $p$-values, and Wilcoxon signed-rank statistics.

### 2.8 B8: Single-Blind Masking and Anonymization
- **Defect in Round 2:** Assessor masking used documented seed 42; call count usage fingerprints allowed trivial de-anonymization; unblinding key was co-located.
- **Remediation Implemented:**
  - `export_masked_assessor_dataset` defaults to cryptographic unpredictable seeding (`seed=None`, standard `uuid.uuid4()`).
  - Call counts and resource usage fields (`modelCalls`, `toolCalls`, `elapsedMs`, `inputChars`) are strictly stripped from `masked_evaluation_set.json` so assessors cannot distinguish conditions by call volume.
  - The unblinding key (`unblinding_key.json`) is exported as a separate restricted file with atomic writes.

---

## 3. Test Suite Verification

The full unit test suite was executed locally:
```powershell
python -m pytest -q -p no:cacheprovider
```
**Console Output:**
```
.........................................................                [100%]
57 passed in 0.23s
```
All 57 unit tests passed cleanly across all 11 test modules.

### New Test Coverage Summary
- `tests/test_harness.py`:
  - `test_t3_executor_fails_closed_when_unwired_and_no_fallback`: Verifies that unwired T3 adapters fail closed rather than falling back.
  - `test_global_resource_registry_rejects_negative_usage`: Asserts `ValueError` on negative usage counters.
  - `test_global_resource_registry_atomic_persistence`: Verifies atomic disk writes and counter preservation across restarts.
  - `test_resume_rejects_mismatched_executor`: Confirms that `t3` runs will not resume existing `synthetic` records.
  - `test_failed_trial_recorded_and_stays_in_denominator`: Verifies that execution errors generate `status="failed"` records and stay in evaluation denominators.
  - `test_export_masked_assessor_dataset_strips_usage_fingerprints`: Verifies that resource usage is absent from masked assessor datasets.
  - `test_exact_mcnemar_and_holm_bonferroni`: Confirms mathematical exactness of McNemar and Holm-Bonferroni statistical routines.
- `tests/test_state.py`:
  - `test_apply_observations_avoids_double_counting_by_default`: Confirms that default observation ingestion does not inflate tool call counters.
  - `test_apply_observations_rejects_negative_usage`: Asserts `ValueError` on negative observation usage.
  - `test_apply_observations_preserves_unknown_cost_and_tokens`: Confirms that unknown (`None`) costs are never promoted to known numbers.
  - `test_apply_observations_tolerant_to_unregistered_probe`: Confirms tolerance for Condition C fixed-lens observations.

---

## 4. Operational Boundaries and Invariants

1. **Approved Study Budget:**  
   The pre-registered budget remains exactly:
   - Maximum 240 trials aggregate (120 dev + 120 held-out).
   - Maximum 8 model calls and 12 tool calls per trial.
   - Maximum 1,920 cumulative model calls across the entire study and process restarts.
   - Costs and token counts remain strictly `None` (unmetered by host).
2. **Historical Call Accounting:**  
   All historical study, setup, holdout preparation, reviewer probes, and test invocations count toward the user's aggregate ceiling of 1,920 calls. If historical unmetered calls cannot be established conservatively, no live campaign should be initiated.
3. **Held-out Partition Status:**  
   The held-out partition (`research/datasets/heldout`) and its manifest remain unsealed and uncommitted. In accordance with zero-inspection and pre-registration freeze rules, no code or test touched held-out gold during this remediation task.
4. **Readiness Gate:**  
   The runtime is code-verified and unit-tested. A live model campaign requires an in-session T3 tool dispatcher providing verified `delegate_task` connectivity.
