# Ommatidia Runtime Implementation Hand-over

**Document Version:** 1.0.0  
**Date:** 2026-10-14  
**Author:** Implementation Sub-agent  
**Language:** British English  
**Status:** Verification Complete. Ready for cohort execution upon case freeze.

---

## 1. Summary of Completed Deliverables

This hand-over document confirms the implementation, local verification, and empirical sealing of the Ommatidia minimal reproducible research harness. All development strictly respects repository ownership rules and preserves peer-agent modifications to research drafts.

### 1.1 Owned File Inventory
- **Package Implementation:**
  - `src/ommatidia/__init__.py`: Package entry point and semantic versioning (`0.1.0`).
  - `src/ommatidia/types.py`: Strongly typed representations for `UnderstandingState`, `Evidence`, `Claim`, `Lens`, `Gap`, `Probe`, `TaskPacket`, `Budget`, `Usage`, `Decision`, and `GoldStandard`.
  - `src/ommatidia/state.py`: State transition machine, probe progression, applied execution idempotency, and deterministic stopping rules.
  - `src/ommatidia/invalidation.py`: Evidence deduplication, withdrawal cascades, assessment invalidation, claim status re-derivation, and gap reopening.
  - `src/ommatidia/conditions.py`: Standardised execution runners for Experimental Conditions A, B, C, D, and E under equal budget envelopes.
  - `src/ommatidia/ingestion.py`: Sealed payload preparation and strict JSON/Markdown schema validation for external host child task ingestion.
  - `src/ommatidia/ledger.py`: Append-only, crash-consistent event ledger tracking stages (`planning`, `investigator`, `communication`, `retry`, `synthesis`) with concurrency locking.
  - `src/ommatidia/seal.py`: Cryptographic SHA-256 seal manifest generation, verification, and held-out leakage detection.
  - `src/ommatidia/evaluator.py`: Objective gold scoring, exact denominator calculation, and paired comparison statistics.
  - `src/ommatidia/harness.py`: High-level experiment orchestrator managing task execution, ledger logging, and paired comparative evaluation.
- **Packaging and Configuration:**
  - `pyproject.toml`: Modern Python build configuration configuring `setuptools` and `pytest` paths.
- **Command-Line Tools:**
  - `scripts/verify_seals.py`: CLI tool for generating and checking cryptographic manifests.
  - `scripts/run_harness.py`: CLI harness supporting mechanism verification and paired cohort evaluations.
- **Verification Test Suite:**
  - `tests/__init__.py`, `tests/fixtures/__init__.py`
  - `tests/fixtures/synthetic_dev_cases.py`: Dev-only synthetic mechanism verification fixtures (explicitly segregated from benchmark efficacy data).
  - `tests/test_state.py`: 4 tests for state creation, transitions, idempotency, and stopping conditions.
  - `tests/test_invalidation.py`: 2 tests for duplicate evidence suppression, withdrawal cascades, and claim re-derivation.
  - `tests/test_ledger.py`: 3 tests for stage accounting, strictly null unknown costs/tokens, and process locking.
  - `tests/test_seal.py`: 4 tests for manifest creation, protocol/dataset tampering detection, and held-out leakage alerts.
  - `tests/test_evaluator.py`: 2 tests for exact denominators, objective scoring, and small-sample paired uncertainty.
  - `tests/test_conditions.py`: 5 tests verifying execution contracts across Conditions A to E.
  - `tests/test_ingestion.py`: 4 tests for payload sealing, strict JSON extraction, and malformed input rejection.
- **Architectural Documentation:**
  - `research/runtime-design.md`: In-depth architectural blueprint and specification.
  - `research/hand_over_runtime.md`: This implementation and verification report.
  - `research/seal_manifest.json`: Initial generated SHA-256 seal for `research/PROTOCOL.md`.

---

## 2. Skill Classification and Ledger Verification

In accordance with user instructions, the local skills catalogue and benchmark routing scripts were inspected prior to implementation:

### 2.1 Task Classification (`bench-ledger-router/scripts/classify_task.py`)
```bash
python "<HOME>\.agents\skills\bench-ledger-router\scripts\classify_task.py" "Implement research harness and runtime for Ommatidia"
```
**Raw Output:**
```json
{"kind": "research", "domain": "coding-implement", "requirements": []}
```

### 2.2 Live Candidate Ranking (`bench_candidates.py`)
Evaluating against the saved live catalogue (`capabilities.json`):
```bash
python "<HOME>\.agents\skills\bench-ledger-router\scripts\bench_candidates.py" "D:\develop\works\tombo-view\results\fix-retry-journal\capabilities.json"
```
**Observed Candidate Record (Rank 13):**
- **Provider Instance:** `agy`
- **Model:** `gemini-3.8-flash-high`
- **Rank:** 13
- **Best Score:** 100.0 (measured)
- **Cost Output:** `null` (cost unknown in host environment; preserved as null)
- **Effort Option:** model-encoded
*Verification Boundary Note:* The user specified `gemini-3.8-flash-high` under the `agy` harness. Coding benchmark ledger scores demonstrate prior task execution capability, not empirical proof of domain research superiority.

---

## 3. Actual Commands and Raw Verification Results

All tests and execution paths were validated directly on the host machine. Below are the exact commands executed and their unmodified outputs.

### 3.1 Test Suite Execution (`pytest -v`)
```powershell
python -m pytest -v
```
**Raw Console Output:**
```
============================= test session starts =============================
platform win32 -- Python 3.14.2, pytest-9.0.1, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: D:\develop\works\ommatidia
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.13.0, mock-3.16.0
collecting ... collected 24 items

tests/test_conditions.py::TestConditionRunners::test_condition_a_runner PASSED [  4%]
tests/test_conditions.py::TestConditionRunners::test_condition_b_runner PASSED [  8%]
tests/test_conditions.py::TestConditionRunners::test_condition_c_runner PASSED [ 12%]
tests/test_conditions.py::TestConditionRunners::test_condition_d_runner PASSED [ 16%]
tests/test_conditions.py::TestConditionRunners::test_condition_e_runner PASSED [ 20%]
tests/test_evaluator.py::TestObjectiveEvaluator::test_objective_scoring_exact_denominators PASSED [ 25%]
tests/test_evaluator.py::TestObjectiveEvaluator::test_paired_differences_and_small_sample_uncertainty PASSED [ 29%]
tests/test_ingestion.py::TestIngestion::test_malformed_proposal_rejection PASSED [ 33%]
tests/test_ingestion.py::TestIngestion::test_observation_ingestion_validation PASSED [ 37%]
tests/test_ingestion.py::TestIngestion::test_prepare_child_task_payload_excludes_private_data PASSED [ 41%]
tests/test_ingestion.py::TestIngestion::test_strict_json_parsing_and_markdown_stripping PASSED [ 45%]
tests/test_invalidation.py::TestInvalidationAndDeduplication::test_duplicate_evidence_rejection PASSED [ 50%]
tests/test_invalidation.py::TestInvalidationAndDeduplication::test_evidence_withdrawal_cascades_to_claims_and_gaps PASSED [ 54%]
tests/test_ledger.py::TestRunLedger::test_concurrency_lock_prevents_duplicate_active_run PASSED [ 58%]
tests/test_ledger.py::TestRunLedger::test_stage_tracking_and_aggregation PASSED [ 62%]
tests/test_ledger.py::TestRunLedger::test_unknown_costs_and_tokens_are_strictly_null PASSED [ 66%]
tests/test_seal.py::TestSealVerification::test_create_and_verify_seal_manifest PASSED [ 70%]
tests/test_seal.py::TestSealVerification::test_heldout_leakage_detection PASSED [ 75%]
tests/test_seal.py::TestSealVerification::test_seal_mismatch_detected_on_dataset_tampering PASSED [ 79%]
tests/test_seal.py::TestSealVerification::test_seal_mismatch_detected_on_protocol_tampering PASSED [ 83%]
tests/test_state.py::TestUnderstandingState::test_apply_observation_idempotency PASSED [ 87%]
tests/test_state.py::TestUnderstandingState::test_apply_proposal_and_revision_increment PASSED [ 91%]
tests/test_state.py::TestUnderstandingState::test_initial_state_creation PASSED [ 95%]
tests/test_state.py::TestUnderstandingState::test_stopping_rules PASSED  [100%]

============================= 24 passed in 0.10s ==============================
```

### 3.2 Protocol Sealing Verification (`scripts/verify_seals.py`)
```powershell
python scripts/verify_seals.py create --protocol research/PROTOCOL.md --out research/seal_manifest.json
python scripts/verify_seals.py verify --manifest research/seal_manifest.json
```
**Raw Console Output:**
```
Seal manifest successfully generated at research\seal_manifest.json
Protocol hash: 2b45fc0b16545d9dc54075bbeb4adac702cd8566b3d5ec518eca06a02bbb4e3a
Seal verification passed successfully.
  protocol: OK
```

### 3.3 Harness Mechanism Verification Run (`scripts/run_harness.py`)
```powershell
python scripts/run_harness.py --mode mechanism_check --condition-primary E --output-dir research/output --run-id run_mech_001
```
**Raw Console Output:**
```
=== Running Ommatidia Research Harness [mechanism_check] ===
Output directory: research\output
Run ID: run_mech_001
Evaluating 2 dev mechanism fixture(s) under Condition E...
  Task dev_mech_cache_01: success=0, gap_recall=1.00, tool_calls=2
  Task dev_mech_duplicate_02: success=0, gap_recall=0.00, tool_calls=2
Execution completed successfully.
```

### 3.4 Harness Paired Comparison Run (`scripts/run_harness.py`)
```powershell
python scripts/run_harness.py --mode paired_compare --condition-primary E --condition-baseline D --output-dir research/output --run-id run_paired_001
```
**Raw Console Output:**
```
=== Running Ommatidia Research Harness [paired_compare] ===
Output directory: research\output
Run ID: run_paired_001
Running paired comparison: Condition E vs Condition D...
Paired statistics:
{
  "metric": "final_decision_success",
  "n": 2,
  "tasks": [
    "dev_mech_cache_01",
    "dev_mech_duplicate_02"
  ],
  "differences": [
    0.0,
    0.0
  ],
  "meanDifference": 0.0,
  "stdDev": 0.0,
  "stdErr": 0.0,
  "ci95": [
    0.0,
    0.0
  ],
  "smallSampleNote": "Caution: Small sample size (N <= 24). Results represent pilot observation and effect size estimate only, not a conclusive proof of general superiority."
}
Execution completed successfully.
```

---

## 4. Mechanism Check Fixtures vs Comparative Efficacy

The fixtures located in `tests/fixtures/synthetic_dev_cases.py` are strictly defined as development-only unit fixtures to test runtime mechanisms (e.g. invalidation cascades, duplicate rejection, and objective scoring). 
- They do **not** represent comparative benchmark results.
- They do **not** substitute for the planned 48 empirical cases (24 dev / 24 held-out).
- In accordance with research rules, no held-out cases or fabricated experimental measurements have been generated by this sub-agent.

---

## 5. Peer-Agent Integration Status and Boundaries

1. **Protocol Designer Alignment:**  
   The runtime design mirrors the structures established in `research/PROTOCOL.md` and `research/EVALUATION_SPEC.md`. When the protocol designer finalises the concrete JSON files for the 24 development cases and seals the 24 held-out cases, the runtime can ingest them without code modifications.
2. **Manuscript Alignment:**  
   `paper/manuscript-ja.md` and `paper/hand_over_manuscript.md` remain untouched and preserved. The manuscript accurately notes that the repository contains early research drafts without established benchmark superiority claims.
3. **Workspace Integrity:**  
   Git working tree changes authored by peer agents were preserved. No unsanctioned git resets or overwrites were performed.

---

## 6. Unresolved Integration Needs (Next Steps)

To transition from runtime readiness to live comparative evaluation, the following inputs are required from the orchestration and design agents:
1. **Concrete Benchmark Case Files:**  
   Deposit the 24 development case `TaskPacket` files and separate `GoldStandard` evaluation rubrics into a dedicated dataset directory (e.g. `research/data/dev/`).
2. **Held-out Seal Manifest:**  
   Generate and commit the cryptographic SHA-256 seal manifest for the 24 held-out evaluation cases before any experimental runs are performed.
3. **T3 Code Dispatcher Wiring:**  
   When ready to execute real model comparison trials across Conditions A–E, wire the T3 Code host child delegation tool (`mcp__t3_code__delegate_task`) into `harness.py` via `executor_func`, passing payloads generated by `ommatidia.ingestion.prepare_child_task_payload`. No paid API calls or unsanctioned subprocesses should be run before explicit user authorisation.
