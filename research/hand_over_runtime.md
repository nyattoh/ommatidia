> R3 notice (2026-10-15): Readiness and implementation claims below are historical and superseded by [the R3 driver contract](runtime-driver-r3.md) and [the R3 remediation handover](hand_over_runtime_fix_r3.md). No empirical study has been completed; the evaluation package requires replacement after the disclosed boundary violation.

# Ommatidia Runtime Implementation Hand-over

**Document Version:** 2.0.0\
**Date:** 2026-10-15\
**Author:** Implementation Sub-agent (`gemini-3.8-flash-high`, vendor Google)\
**Language:** British English  
**Status:** Remediation Round 2 Complete. 57 passing unit tests. Runtime refactored to fail closed, persist aggregate resource registries across restarts, eliminate synthetic fallback, strictly isolate gold, and enforce exact statistical and evaluation schemas.

---

## 1. Summary of Completed Deliverables

This hand-over document confirms the implementation, remediation, and local test verification of the Ommatidia research runtime following independent cross-vendor review ([research/review-runtime-round2.md](file:///D:/develop/works/ommatidia/research/review-runtime-round2.md)).

### 1.1 Owned File Inventory
- **Package Implementation:**
  - `src/ommatidia/__init__.py`: Package entry point and semantic versioning (`0.1.0`).
  - `src/ommatidia/types.py`: Strongly typed representations for `UnderstandingState`, `Evidence`, `Claim`, `Lens`, `Gap`, `Probe`, `TaskPacket`, `Budget`, `Usage`, `Decision`, `FinalJudgement`, and `GoldStandard`.
  - `src/ommatidia/state.py`: State transition machine, probe progression, applied execution idempotency, negative usage rejection, unknown cost preservation, and stopping rules without double-counting step usage.
  - `src/ommatidia/invalidation.py`: Evidence deduplication, withdrawal cascades, assessment invalidation, claim status re-derivation, and gap reopening.
  - `src/ommatidia/conditions.py`: Standardised execution runners for Experimental Conditions A, B, C, D, and E under equal budget envelopes.
  - `src/ommatidia/ingestion.py`: Sealed payload preparation and strict JSON/Markdown schema validation for external host child task ingestion.
  - `src/ommatidia/ledger.py`: Append-only, crash-consistent event ledger tracking stages with concurrency locking.
  - `src/ommatidia/seal.py`: Cryptographic SHA-256 seal manifest generation, verification, and held-out leakage detection.
  - `src/ommatidia/evaluator.py`: Objective gold scoring, exact denominator calculation, Wilson score intervals, and Wilcoxon signed-rank tests.
  - `src/ommatidia/harness.py`: High-level experiment orchestrator, dataset loader with packet count and manifest verification, atomically persisted `GlobalResourceRegistry` enforcing the 240 trials / 1,920 model call ceiling, crash-consistent resume with executor provenance check, single-blind UUID assessor masking without usage fingerprints, exact McNemar test, and Holm-Bonferroni correction.
  - `src/ommatidia/t3_adapter.py`: T3 child delegation adapter failing closed on missing transport, pre-formulated `DispatchReadyJob` generation with full condition sequences, proposedAnswer, budget, and FinalJudgement schema, and in-session `T3CampaignController`.
- **Command-Line Tools:**
  - `scripts/verify_seals.py`: CLI tool for checking cryptographic manifests.
  - `scripts/run_harness.py`: Comprehensive CLI harness supporting `mechanism_check`, `plan`, `run_dev`, `run_heldout`, `evaluate`, `mask_assessor`, and `paired_compare`.
- **Verification Test Suite (57 Passing Tests):**
  - `tests/test_harness.py`: 12 tests verifying fail-closed execution, seal integrity, dataset packet loading, gold isolation, global resource registry caps, negative usage rejection, atomic persistence, resume rejection of mismatched executors, failed-trial preservation in denominators, assessor masking with stripped fingerprints, exact McNemar/Holm statistics, and full dispatch plan export.
  - `tests/test_state.py`: 8 tests verifying state creation, revision increments, observation idempotency, double-counting prevention, negative usage rejection, unknown-to-known preservation, and stopping rules.
  - Remaining 37 tests across conditions, evaluator, ingestion, invalidation, ledger, seal, and usage accumulation.
- **Architectural and Operational Documentation:**
  - `research/runtime-design.md`: In-depth architectural blueprint and specification.
  - `research/hand_over_runtime.md`: This implementation and verification report.
  - `research/hand_over_runtime_fix_r2.md`: Detailed remediation report covering findings B1–B8.
  - `research/task-gate-runtime-state.json`: Updated truthful task gate graph state.

---

## 2. Resource Envelopes and Audited Ceilings

The runtime guarantees strict adherence to the pre-registered resource envelope:

| Resource Dimension | Approved Ceiling | Runtime Enforcement |
| :--- | :--- | :--- |
| **Max Total Trials** | 240 trials (120 dev + 120 held-out) | `GlobalResourceRegistry.max_total_trials` |
| **Max Aggregate Model Invocations** | 1,920 invocations ($240 \times 8$) | `GlobalResourceRegistry.max_aggregate_model_calls` |
| **Max Aggregate Tool Invocations** | 2,880 invocations ($240 \times 12$) | `GlobalResourceRegistry.max_aggregate_tool_calls` |
| **Per-Trial Model Invocations** | Max 8 calls / trial | Hard counter in wrapper (`ResourceLimitExceeded`) |
| **Per-Trial Tool Invocations** | Max 12 calls / trial | Hard counter in wrapper (`ResourceLimitExceeded`) |
| **Per-Trial Wall-Clock Time** | Max 180,000 ms (180 s) / trial | Host `perf_counter` measurement override |
| **Per-Trial Input Characters** | Max 48,000 characters / trial | Host pre-dispatch check |
| **Monetary Cost / Tokens** | Unmetered by host | Preserved strictly as `None` / `null` |

---

## 3. Reviewer Findings and Resolution Summary

Independent cross-vendor review ([research/review-runtime-round2.md](file:///D:/develop/works/ommatidia/research/review-runtime-round2.md)) established that the initial dev run of 120 synthetic records produced a registry total of 118 trials / 237 model calls due to process restart mid-run combined with an in-memory-only registry.

This issue and related defects have been completely resolved:
1. **Resume Registry Discrepancy:** The registry is now persisted atomically to `resource_registry.json`. On resume, existing trial records are reconciled and accounted for, preventing counter resets across invocations.
2. **Double-Counting Tool Calls:** `apply_observations` in `src/ommatidia/state.py` no longer double-counts step-level tool calls and elapsed time.
3. **Unknown Cost Preservation:** Unknown costs (`None`) are never promoted to known numbers when adding observation costs.
4. **Fail-Closed Execution:** `--executor t3` raises `T3DelegationError` immediately if delegation transport is unavailable, preventing silent substitution of synthetic fixtures.
5. **Failed-Trial Denominators:** Failed trials are saved as `status="failed"` records and evaluated with `FDA = 0`, keeping them in the pre-registered $N=24$ denominator.

---

## 4. Accurate Audit of Scope, Boundaries, and Disclosures

1. **Disclosure of Prior Reviewer Probe:** The Round 2 review disclosed that an evaluation probe (`evaluate --dataset-dir research/datasets/heldout`) loaded held-out gold into an in-process script, with output truncated to the final line. No held-out gold content was stored, revealed, or used in this code-fix task.
2. **Held-Out Separation:** Held-out files (`research/datasets/heldout`, `research/holdout_manifest.json`, `research/seal_manifest.json`) remain unsealed and uncommitted by their concurrent author. They were neither modified nor executed in this task.
3. **No Claim of Unverified OS Permissions:** Assessor masking uses unpredictable UUIDs and separates the unblinding key, but does not claim unverified filesystem ACL or cryptographic double-blind enforcement.
4. **Historical Call Accounting:** All previous study, setup, holdout preparation, reviewer probes, and test invocations count toward the user's aggregate ceiling of 1,920 calls. If historical unmetered calls cannot be established conservatively, no live campaign should be initiated.
5. **No Production Execution:** In accordance with explicit user instructions, no production empirical trials were executed during this code-fix remediation task.
