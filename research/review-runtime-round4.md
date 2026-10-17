pass

# Independent Code Review: Ommatidia Runtime Remediation R3 (Round 4)

**Verdict:** `pass`  
**Review date:** 2026-10-15 (JST)  
**Reviewer:** `gemini-3.8-flash-high`, vendor Google, reasoning effort `host_default` (host catalogue exposes no effort option; no benchmark evidence available from coding-verify ledger filter, so no score claim is made)  
**Target:** Ommatidia working tree on `main`, base commit `56ef2f1871286af0111884de5f3a094b88fa26a0` with R3 changes:
- New implementation files: `src/ommatidia/{campaign,contracts,runtime,integrity,scoring}.py`
- Updated files: `src/ommatidia/{harness,t3_adapter,ledger,seal,state}.py`, `scripts/{run_harness,verify_seals}.py`, `tests/{test_harness,test_state}.py`
- New tests: `tests/test_runtime_r3.py`, `tests/conftest.py`
- New freeze & documentation: `research/runtime_freeze_r3.json`, `research/runtime-driver-r3.md`, `research/hand_over_runtime_fix_r3.md`
**Implementer:** Codex `gpt-6.1-sol`, reasoning effort `xhigh`, vendor OpenAI (cross-vendor review independence satisfied: Google reviewer verifying OpenAI implementer)  
**Prior failure report:** `research/review-runtime-round3.md` (Round 3, reviewer `claude-sonnet-5-5`, vendor Anthropic, verdict `fail`)  
**Scope statement:** Code and synthetic test verification only. No live model experiment was executed. No study calls were dispatched. No gold or private answer key was read, loaded, or inspected.

---

## 1. Executive Summary & Verdict

**PASS.** The R3 remediation package authored by Codex `gpt-6.1-sol` comprehensively resolves all blocking findings (F1–F8) reported in Round 3.

The architecture cleanly decouples the historical frozen experimental core (`conditions.py`, `types.py`, `evaluator.py`, `PROTOCOL.md`, `EVALUATION_SPEC.md`, `holdout_manifest.json`—all preserved byte-for-byte at their historical hashes) from the executable driver (`runtime.py`, `campaign.py`, `contracts.py`, `integrity.py`, `scoring.py`). The new driver replaces decorative hashes with true byte-derived cryptographic digests, enforces atomic pre-dispatch reservations and conservative consumption floors on a campaign-wide registry, validates real child `FinalJudgement` outputs, ensures failed trials serialize cleanly into the N=24 denominator with FDA=0, aligns execution and plan graphs with required synthesis steps, eliminates usage fingerprints and isolates unblinding keys, implements preregistered paired statistical testing with family-wise Holm-Bonferroni correction, and enforces non-zero CLI exits on failure.

All release gates for study execution—specifically requiring an approved rebuilt evaluation package, a clean committed tree, an attested public boundary, and an audit of historical resource consumption—are strictly and safely enforced in code.

---

## 2. Closure of Prior Blocking Findings (F1–F8)

### F1. Model Verdict Ingestion & Inconclusive Handling (Closed)
- **Prior failure:** `conditions.py` runners ended with `synthesize_final_judgement()`, ignoring child outputs; blank and contradicted responses both produced `supported` with confidence 1.0. `ingest_final_judgement` was dead code.
- **R3 implementation:** `src/ommatidia/runtime.py` defines `execute_graph()` and `final_response()` (`runtime.py:102-140`). For all conditions, the child response is parsed against `FINAL_SCHEMA`.
  - Required fields (`taskId`, `verdict`, `confidenceScore`, `justification`, `citedEvidence`, `unresolvedGaps`, `resourceUsage`) are strictly type-checked.
  - `ingest_final_judgement()` converts the dictionary into a `FinalJudgement`.
  - Missing, blank, malformed, or mismatched output raises `ValueError`, which is trapped to set `state.final_judgement = inconclusive(...)` with `verdict="inconclusive"`, `confidence_score=0.0`, and `status="invalid_response"`.
  - Contradicted model verdicts (`verdict="contradicted"`) survive without being coerced to `supported`.
- **Verification evidence:**
  - `tests/test_runtime_r3.py:test_actual_child_verdict_survives_roundtrip`: Contradicted responses for Condition A and B persist and reload with `verdict == "contradicted"` and `confidence_score == 0.7`.
  - `tests/test_runtime_r3.py:test_blank_invalid_response_is_inconclusive`: Blank `{}` and invalid responses produce `status == "invalid_response"`, `verdict == "inconclusive"`, `confidence_score == 0`.

### F2. Failed Trial Persistence in Evaluation Denominator (Closed)
- **Prior failure:** `harness.py:854-867` passed a raw `dict` as `resource_usage` to `FinalJudgement`. `FinalJudgement.to_dict()` called `self.resource_usage.to_dict()`, throwing an uncaught `AttributeError: 'dict' object has no attribute 'to_dict'` on executor failure, crashing the cohort without saving trial files.
- **R3 implementation:** In `src/ommatidia/runtime.py:94-98`, `inconclusive()` constructs `FinalJudgementResourceUsage(usage.model_calls, usage.tool_calls, usage.elapsed_ms, usage.input_chars)`. In `harness.py:680-720`, executor exceptions are caught, an inconclusive `TrialRecord` with `status="failed"` is created, atomically written to disk (`atomic_json`), registered in the `resource_registry`, and the cohort loop proceeds to subsequent tasks. On resume and evaluation, failed trials remain in the N=24 denominator with FDA=0.
- **Verification evidence:**
  - `tests/test_runtime_r3.py:test_failed_trials_persist_and_cohort_continues`: Cohort of 2 trials with a throwing executor completes without aborting, writes 2 failed trial files, records `failedTrials == 2` in `summary.json`, and records 2 trials and 2 model calls in the registry.

### F3. Durable Campaign Budget, Pre-Dispatch Reservation & Recovery (Closed)
- **Prior failure:** Registries double-counted on resume (4/6 -> 8/12 -> 12/18); registries were scoped per-partition (`dev` vs `heldout`) rather than campaign-wide; corrupt registries silently reset to zero; reservations were ephemeral; failed/timed-out/zero-usage steps went uncounted.
- **R3 implementation:**
  - `src/ommatidia/campaign.py:GlobalResourceRegistry` provides a unified campaign registry stored at `output_dir / "resource_registry.json"`, covering all partitions (`dev`, `heldout`, `mechanism`). Legacy partition-level registries fail closed (`harness.py:510-515`).
  - Resume reconciles saved trial records without incrementing stored counters (`harness.py:738-765`).
  - `reserve_step()` (`campaign.py:99-130`) persists and `fsync`s reservations to disk *before* dispatching to the executor.
  - `settle_step()` (`campaign.py:136-155`) enforces a conservative floor: `usage.model_calls = max(1, usage.model_calls)`. If tool usage is unknown (e.g. timeout or exception), `usage.tool_calls = max(reserved.tool_calls, usage.tool_calls)`. Negative usage is rejected.
  - `load_from_path()` (`campaign.py:195-230`) strictly validates schema version 3, field types, and recomputed totals, raising `ValueError` on truncated or corrupt files rather than resetting to zero.
- **Verification evidence:**
  - `tests/test_runtime_r3.py:test_resume_is_idempotent_across_fresh_instances`: 3 successive cohort runs with fresh harness instances maintain exact `(4, 6)` totals.
  - `tests/test_runtime_r3.py:test_campaign_caps_span_partitions_and_stop_before_call`: Global model-call ceiling is enforced across distinct partition names.
  - `tests/test_runtime_r3.py:test_corrupt_registry_and_legacy_records_fail_closed`: Truncated registry and unregistered legacy records fail closed with `ValueError`.
  - `tests/test_runtime_r3.py:test_negative_usage_never_reduces_reserved_calls`: Negative usage reports are rejected and do not reduce counters.

### F4. Protocol Alignment, Payload Schemas & Transport Boundary (Closed)
- **Prior failure:** Live execution used hardcoded payloads missing `proposedAnswer`, `budget`, and response schemas; plan export step names differed from runner step names; synthesis steps were absent for D and E; child provenance was unrecorded; children had no filesystem isolation.
- **R3 implementation:**
  - `condition_graph()` in `src/ommatidia/runtime.py:34-49` is the single source of truth for both live execution (`execute_graph`) and dispatch plan generation (`create_condition_dispatch_jobs` in `t3_adapter.py`).
  - Synthesis steps are explicitly defined for C (`fixed_synthesis`), D (`adaptive_synthesis`), and E (`ommatidia_synthesis`).
  - Dispatched payloads (`runtime.py:71-87`) include `proposedAnswer`, `budget`, `stepBudget`, `responseSchema` (from `contracts.py`), `context`, and a stable `clientRequestId`.
  - `check_public_payload()` (`runtime.py:52-68`) verifies that neither prompts nor outputs contain evaluator fields (`criticalEvidenceHashes`, etc.) or private file paths (`/gold/`, `/cases/`, `unblinding_key.json`).
  - Detailed child provenance (`taskId`, `providerInstanceId`, `model`, `clientRequestId`, `stepId`, `attempt`, `inputHash`, `outputHash`, `usage`) is checkpointed into `TrialRecord.steps`.
  - `T3DelegationAdapter` requires a verified `public_boundary` attestation and fails closed if unwired.
- **Verification evidence:**
  - `tests/test_runtime_r3.py:test_execution_and_plan_use_same_graph_and_injected_transport`: Verified across all 5 conditions (A–E) that plan steps match executed steps, payloads contain schemas and budgets, and provenance is recorded.
  - `tests/test_runtime_r3.py:test_unattested_t3_transport_never_dispatches`: Unattested T3 adapter aborts before any call.

### F5. Real Cryptographic Hashes, Freeze Validation & Boundary Gate (Closed)
- **Prior failure:** Code and prompt hashes were constant label strings (e.g. `sha256("ommatidia_code_A")`); resume ignored hash mismatches; historical freeze manifests were never checked.
- **R3 implementation:**
  - `src/ommatidia/integrity.py:fingerprints()` computes SHA-256 digests from the actual file bytes of 15 Python modules, protocol, evaluation spec, CLI scripts, `pyproject.toml`, prompt constants, dispatch instruction, and the serialized executable graph.
  - `verify_runtime_freeze()` validates current hashes against `research/runtime_freeze_r3.json`, verifies historical core files against `holdout_manifest.json`, and verifies `baseCommit` (`56ef2f18...`).
  - Resume validates that saved trial records match current hashes, rejecting modified records.
  - Programmatic access in Round 2 is recorded with `"evaluationPackageStatus": "blocked_rebuild_required"`. `require_release=True` strictly blocks live execution until a rebuilt package is approved.
- **Verification evidence:**
  - `tests/test_runtime_r3.py:test_real_hashes_and_freeze_detect_driver_change`: Mutating `runtime.py` triggers `SealMismatchError`.
  - `tests/test_runtime_r3.py:test_resume_rejects_saved_hash_changes`: Tampered `codeHash` in a saved record causes resume rejection.
  - Standalone seal verification: `python -B scripts/verify_seals.py verify --runtime-freeze research/runtime_freeze_r3.json` passes with exit code 0.

### F6. Assessor Masking & Key Separation (Closed)
- **Prior failure:** `export_masked_assessor_dataset` retained `finalJudgement.resourceUsage`, creating identifiable per-condition call-count fingerprints; unblinding key was co-located in `assessor/` and embedded outcome metrics.
- **R3 implementation:**
  - `harness.py:440-475` strips top-level `usage` and strips `resourceUsage` from `finalJudgement`.
  - The unblinding key is written to `output_dir / "private_assessor" / "assessor_mapping.json"`, completely outside the `assessor/` directory.
  - Outcome metrics (`fda`, `recallCrit`) are omitted from the unblinding mapping.
- **Verification evidence:**
  - `tests/test_runtime_r3.py:test_actual_mask_export_strips_nested_usage_and_separates_mapping`: Verifies that `resourceUsage`, `modelCalls`, `elapsedMs`, `codeHash`, `steps`, and `executor` are absent from masked records, and that dataset and key reside in distinct directories.

### F7. Objective Saved-Record Scoring & Paired Statistics (Closed)
- **Prior failure:** CLI evaluate fabricated 0.0 or null for missing metrics; `required_gap_recall` was aliased to critical evidence recall; Holm-Bonferroni correction was never applied; N=24 denominator was unenforced.
- **R3 implementation:**
  - `src/ommatidia/scoring.py:score_saved_trial()` computes metrics from saved `UnderstandingState` traces against explicit sealed rubrics. Unavailable metrics raise `MetricUnavailable` rather than fabricating values (e.g. FAR requires complete traces and probe labels; efficiency requires non-zero tool/time denominators).
  - Gap recall explicitly measures resolved gaps against `requiredGapQuestions`, completely separate from critical evidence recall.
  - `validate_matrix()` enforces an exact 24-case denominator per condition and exact 12 counterexample IDs for H4.
  - `analyse_saved_trials()` executes exact McNemar tests (H1, H4) and paired Wilcoxon signed-rank tests (H2, H3), and applies step-down Holm-Bonferroni correction across all 4 hypothesis family members. Uncomputable p-values remain in the family.
- **Verification evidence:**
  - `tests/test_runtime_r3.py:test_saved_scoring_uses_observations_and_refuses_unavailable_metrics`: Verifies metric computations and asserts that unavailable metrics raise `MetricUnavailable`.
  - `tests/test_runtime_r3.py:test_cli_paired_tests_require_24_saved_pairs_and_apply_holm`: Verifies exact 24-case requirement, 12-case H4 subset, and Holm-Bonferroni adjusted p-values.

### F8. CLI Exit Semantics on Incomplete/Failed Runs (Closed)
- **Prior failure:** CLI `main()` ended with `return 0` regardless of trial failures or exceptions.
- **R3 implementation:** In `scripts/run_harness.py`, `main()` inspects execution outcomes:
  - `mechanism_check` and `run_dev`: returns `1 if failures else 0`.
  - `evaluate`: returns `1 if any(record["status"] != "completed" for record in scored) else 0`.
  - Unhandled exceptions are caught and return code 1.
- **Verification evidence:**
  - `tests/test_runtime_r3.py:test_cli_failure_exit`: Verifies CLI returns exit code 1 when trials fail.

---

## 3. Investigation of P1/P2 Behaviors & Edge Conditions

1. **Runtime Graph Correctness & Budget Interplay:**
   - Loop bounds in Condition D and E (`runtime.py:168`): `while usage_getter().model_calls + 2 < min(8, task.budget.max_model_calls):`.
   - The `+ 2` guard guarantees that at least one model call is reserved for the proposal and at least one for the subsequent probe, while the `- 1` in `slots` calculation reserves the final call slot for synthesis (`runtime.py:183`).
   - If a step retry occurs and exhausts available model calls, the loop exits safely and attempts synthesis; if budget is fully depleted, it fails safely, persists the failed trial, and remains in the denominator.
2. **State Mutation & Provenance:**
   - Probes and gaps are ingested through immutable dataclass operations or validated dictionary transforms.
   - `sequence` numbers increment monotonically, generating unique SHA-256-derived `clientRequestId` strings for each dispatch attempt.
3. **Lock & Atomic Registry Cross-Process Guarantees:**
   - `RunLedger.acquire_lock()` uses exclusive creation (`open(..., "x")`) with process PID inspection. On Windows, `_pid_alive()` checks handle status via `OpenProcess` and `GetExitCodeProcess`.
   - `atomic_json()` uses `.tmp` file creation, write, `flush()`, `fsync()`, and `os.replace()` (atomic on NTFS/Windows via `MoveFileExW`).
4. **Split Registry Across Output Dirs:**
   - Single campaign registry is anchored at `output_dir / "resource_registry.json"`. Synthetic runs are strictly prohibited from targeting `research/output`.
5. **Schema Accuracy vs Serialized Types:**
   - All schemas in `contracts.py` accurately reflect dataclass fields in `types.py`. `FinalJudgementResourceUsage` round-trips through `.to_dict()` and `.from_dict()` without error.
6. **Actual CLI Environment & Default Executor:**
   - CLI defaults to `--executor synthetic`. Standalone invocation with `--executor t3` fails closed immediately with `T3DelegationError` because in-session dispatchers and public boundary attestations cannot be injected via CLI arguments. This prevents inadvertent live study dispatches.
7. **Assessment Export & Key Path:**
   - Keys are isolated under `private_assessor/`. As documented in `runtime-driver-r3.md`, directory separation is not an operating system ACL; distribution control remains the caller's responsibility.
8. **Timeouts & Cancellation on Caps:**
   - `t3_adapter.py:delegate_step` issues `task_cancel` upon timeout or error. Unconfirmed cancellations raise `CampaignAuditRequired`, which persists the failure and halts the entire campaign to prevent unmetered spending.

---

## 4. Test Execution & Seal Verification Log

The following independent verification commands were executed in `d:\develop\works\ommatidia`:

1. **Targeted R3 Regressions:**
   ```powershell
   python -B -m pytest tests/test_runtime_r3.py -q -p no:cacheprovider
   ```
   *Result:* `44 passed in 10.62s` (exit code 0).

2. **Full Test Suite:**
   ```powershell
   python -B -m pytest -q -p no:cacheprovider
   ```
   *Result:* `101 passed in 10.47s` (exit code 0).

3. **Standalone Seal & Freeze Verification:**
   ```powershell
   python -B scripts/verify_seals.py verify --runtime-freeze research/runtime_freeze_r3.json
   ```
   *Result:*
   ```text
   Runtime core/driver/prompt/spec hashes verified: 67916037000453ca273fab0e684afc53f95a624ecbd735b1debcb7b3753cdc9f
   Seal verification passed successfully.
     protocol: OK
     research/EVALUATION_SPEC.md: OK
     research/datasets/dev/manifest.json: OK
     research/datasets/heldout/manifest.json: OK
   ```
   (exit code 0).

4. **Whitespace & Formatting Integrity:**
   ```powershell
   git diff --check
   ```
   *Result:* Clean (exit code 0).

---

## 5. Boundaries & Disclosures

- **Zero-Inspection Maintained:** No gold standards, answer keys, or cases under `research/datasets/**/gold/**`, `cases/**`, or `unblinding_key.json` were opened, read, printed, or modified.
- **Test-Level Filesystem Guard:** `tests/conftest.py:reject_private_dataset_io` monkeypatches `builtins.open`, `io.open`, and `os.open` during test runs, actively raising `AssertionError` if any test attempts to read private files.
- **Unrun Boundary:** No live T3 model dispatch was performed. No production experiment was initiated. No git commit, push, or publication was executed.
- **No Efficacy Claim:** Synthetic mechanism fixtures verify architectural correctness and error handling only; they support no claim of empirical efficacy or task performance.

---

## 6. Recommendations for Live Study Readiness

Although code remediation is complete and verified, live empirical study execution remains strictly gated:
1. **Rebuild Evaluation Package:** The historical held-out package is blocked due to the prior Round 2 programmatic access. A new evaluation package must be constructed without inspecting previous gold, sealed, and marked `"evaluationPackageStatus": "rebuilt_and_approved"`.
2. **Release Commit:** Live execution requires a clean, committed working tree matching `baseCommit` (`verify_runtime_freeze(require_release=True)`).
3. **Attested Transport Controller:** A live execution harness must supply an injected controller that verifies public-only filesystem isolation (beyond bare git worktrees) and enforces host-metered single model invocation per step.
4. **Historical Accounting Audit:** Audit all historical planning, review, and testing calls against the 1,920 study model-call ceiling before commencing live trials.
