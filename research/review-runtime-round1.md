Verdict: fail

# Code Review: Ommatidia Research Runtime (Round 1)

**Review Date:** 2026-10-14  
**Reviewer:** Review Sub-agent (Antigravity / `gemini-3.8-flash-high`, separate-context SAME vendor)  
**Target Repository:** `D:\develop\works\ommatidia`  
**Target Commit/Head:** Working tree on `main`  
**Governing Documents:** [AGENTS.md](file:///D:/develop/works/ommatidia/AGENTS.md), [research/hand_over_runtime.md](file:///D:/develop/works/ommatidia/research/hand_over_runtime.md), [research/EVALUATION_SPEC.md](file:///D:/develop/works/ommatidia/research/EVALUATION_SPEC.md), [research/PROTOCOL.md](file:///D:/develop/works/ommatidia/research/PROTOCOL.md)  
**Owned Artifacts in Scope:** [research/review-runtime-round1.md](file:///D:/develop/works/ommatidia/research/review-runtime-round1.md), [research/task-gate-runtime-state.json](file:///D:/develop/works/ommatidia/research/task-gate-runtime-state.json)  

---

## 1. Executive Summary & Review Verdict

### Verdict: **FAIL** (Experimental Readiness Blocked)

While the implementation sub-agent successfully authored a cleanly structured Python package with 24 passing unit tests and clear type abstractions, the runtime **cannot be accepted as experimentally ready for the empirical research paper** in its current form. 

The verdict is **FAIL** due to critical blocking defects across execution contracts, statistical uncertainty reporting, schema alignment with [research/EVALUATION_SPEC.md](file:///D:/develop/works/ommatidia/research/EVALUATION_SPEC.md), crash recovery locks, and budget/usage invariants:
1. **Misleading Statistical Uncertainty:** On small sample runs ($N=2$) with identical differences, [evaluator.py](file:///D:/develop/works/ommatidia/src/ommatidia/evaluator.py#L125-L144) reports degenerate $95\%$ Confidence Intervals of `[0.0, 0.0]`, creating a mathematically invalid impression of zero population uncertainty.
2. **Schema and Metric Disconnect:** The runtime checks internal state enum `Decision` (`READY_FOR_REQUESTED_STEP`, etc.) rather than the standardised `FinalJudgement` JSON schema specified in [research/EVALUATION_SPEC.md](file:///D:/develop/works/ommatidia/research/EVALUATION_SPEC.md). Core pre-registered metrics ($\text{FDA}$, $\text{Recall}_{\text{crit}}$, $\text{FAR}$, $\text{Prec}_{\text{cand}}$, $\text{DDR}$, $\text{WAR}$, $\text{UAR}$, $\text{DSC}$) are not implemented in [evaluator.py](file:///D:/develop/works/ommatidia/src/ommatidia/evaluator.py).
3. **Usage & Budget Leakage:** In [conditions.py](file:///D:/develop/works/ommatidia/src/ommatidia/conditions.py#L45-L48), `_accumulate_step_usage` coerces `None` (unknown costs/tokens) to `0.0`, masking unmeasured consumption. Furthermore, Conditions A and B completely bypass budget checks.
4. **Invalidation Decision Inconsistency:** In [invalidation.py](file:///D:/develop/works/ommatidia/src/ommatidia/invalidation.py#L128-L137), withdrawing evidence reopens required gaps, but fails to revoke `state.decision = Decision.READY_FOR_REQUESTED_STEP`.
5. **Crash Lock Deadlocks:** [ledger.py](file:///D:/develop/works/ommatidia/src/ommatidia/ledger.py#L34-L47) locks runs via a static `.lock` file without checking process liveness; any unhandled crash or process abort permanently blocks resumes.
6. **No Runtime Environment/Seal Verification:** [harness.py](file:///D:/develop/works/ommatidia/src/ommatidia/harness.py) never calls `verify_environment()` in either `evaluate_task` or `run_paired_comparison`, and [research/seal_manifest.json](file:///D:/develop/works/ommatidia/research/seal_manifest.json) seals no datasets, prompts, or code.
7. **Synthetic Fixture Boundary:** The passing 24 tests and harness executions replay synthetic dummy fixtures (`tests/fixtures/synthetic_dev_cases.py`), with `executor_func` returning hardcoded dictionaries rather than dispatched child tasks. No empirical efficacy claims can be drawn.

---

## 2. Router Skill Classification & Candidate Ranking

In accordance with user instructions, the task was classified and candidate capabilities were evaluated:

### 2.1 Router Classification
Command:
```powershell
python "<HOME>\.agents\skills\bench-ledger-router\scripts\classify_task.py" "Read-only code review of Ommatidia research runtime"
```
**Raw Console Output:**
```json
{"kind": "verify", "domain": "coding-verify", "requirements": ["coding-verify", "coding-implement"]}
```

### 2.2 Live Candidate Ranking
Evaluated against `capabilities.json` from Tombo View (`D:\develop\works\tombo-view\results\fix-retry-journal\capabilities.json`):
```powershell
python "<HOME>\.agents\skills\bench-ledger-router\scripts\bench_candidates.py" "D:\develop\works\tombo-view\results\fix-retry-journal\capabilities.json"
```
**Selected Candidate Record (Rank 13):**
- **Provider Instance:** `agy`
- **Model ID:** `gemini-3.8-flash-high`
- **Rank:** 13
- **Best Score:** 100.0 (measured)
- **Cost Output:** `null` (cost unknown in host environment, preserved as null)
- **Effort Option:** model-encoded (`model-encoded-high`)
- **Vendor:** `google`

### 2.3 Cross-Vendor Review Constraint
- Cross-vendor verification was attempted prior:
  - **OpenAI:** failed with `helper_unknown_error setup refresh`.
  - **Claude / Anthropic:** rate limit encountered.
  - **Cursor:** unavailable.
  - **xAI / Grok:** auto-review rejected.
- **Strict Boundary:** The present reviewer is a separate-context **SAME vendor** (`google`). Per router rules, this verification must **never** be labelled or recorded as a cross-vendor pass.

---

## 3. Detailed Falsification & Defect Analysis

### Defect 1: Misleading Paired Small-Sample Confidence Intervals ($[0.0, 0.0]$ on Zero Variance)
- **File & Line:** [src/ommatidia/evaluator.py:125-144](file:///D:/develop/works/ommatidia/src/ommatidia/evaluator.py#L125-L144)
- **Concrete Scenario:** Running a paired comparison between Condition E and Condition D on $N=2$ cases (as executed in `scripts/run_harness.py --mode paired_compare`) yields identical scores (`differences = [0.0, 0.0]`). In `compute_paired_differences`:
  ```python
  variance = sum((d - mean_diff) ** 2 for d in differences) / (n - 1) if n > 1 else 0.0
  std_dev = math.sqrt(variance)
  std_err = std_dev / math.sqrt(n) if n > 0 else 0.0
  ci_lower = mean_diff - (t_crit * std_err)
  ci_upper = mean_diff + (t_crit * std_err)
  ```
  Because sample variance is $0.0$, `std_err = 0.0`, producing `ci95: [0.0, 0.0]`.
- **Impact:** Asserting a $95\%$ confidence interval of $[0.0, 0.0]$ on an $N=2$ sample communicates complete certainty to readers that the population mean difference is exactly $0.0$. This is a severe statistical fallacy: in small samples, zero observed sample difference reflects lack of power, not zero population uncertainty. Furthermore, for discrete binary decision differences ($\in \{-1, 0, 1\}$), a normal/t-distribution interval is fundamentally inapplicable.
- **Spec Conflict:** [research/EVALUATION_SPEC.md: Section 5.3](file:///D:/develop/works/ommatidia/research/EVALUATION_SPEC.md#L150-L165) specifies:
  - Wilson score $95\%$ CI with continuity correction for binomial decision accuracy.
  - Non-parametric BCa bootstrap with $B=10,000$ resamples for continuous differences.
- **Minimal Fix:** In `compute_paired_differences`, when sample variance is $0.0$ or $N < 10$, flag the confidence interval as undefined or emit a bounded conservative non-parametric interval. Do not report `(0.0, 0.0)`. Implement the BCa bootstrap and Wilson score intervals mandated by the specification.
- **Boundary:** Static formula flaw exposed during harness runtime.

---

### Defect 2: Schema & Metric Disconnect with Evaluation Specification
- **File & Line:** [src/ommatidia/evaluator.py:20-85](file:///D:/develop/works/ommatidia/src/ommatidia/evaluator.py#L20-L85), [src/ommatidia/types.py:100-110, 480-515](file:///D:/develop/works/ommatidia/src/ommatidia/types.py#L100-L110)
- **Concrete Scenario:** [research/EVALUATION_SPEC.md: Section 3.2](file:///D:/develop/works/ommatidia/research/EVALUATION_SPEC.md#L90-L135) specifies that all conditions must emit a `FinalJudgement` JSON object containing `verdict` $\in \{\text{"supported"}, \text{"contradicted"}, \text{"disputed"}, \text{"inconclusive"}\}$, `confidenceScore`, `citedEvidence`, `unresolvedGaps`, and `resourceUsage`.
  However, in `src/ommatidia`:
  1. There is no `FinalJudgement` data structure or schema validator.
  2. [score_run_objectively](file:///D:/develop/works/ommatidia/src/ommatidia/evaluator.py#L20) scores `final_decision_success` by comparing `state.decision == gold.target_decision`, where `Decision` is `{READY_FOR_REQUESTED_STEP, NEEDS_CHECK, NEEDS_USER_INPUT, BLOCKED}`.
  3. Pre-registered metrics from [EVALUATION_SPEC.md](file:///D:/develop/works/ommatidia/research/EVALUATION_SPEC.md) ($\text{FDA}$, $\text{Recall}_{\text{crit}}$, $\text{FAR}$, $\text{Prec}_{\text{cand}}$, $\text{DDR}$, $\text{WAR}$, $\text{UAR}$, $\text{DSC}$, $\eta_{\text{tool}}$, $\eta_{\text{time}}$) are completely omitted. Instead, [evaluator.py](file:///D:/develop/works/ommatidia/src/ommatidia/evaluator.py) computes an ad-hoc `required_gap_recall` using substring matching on probe question text.
- **Impact:** The runtime cannot score real experimental runs against the pre-registered protocol. If empirical trials were run today, their outputs could not be evaluated under the paper's pre-registered statistical hypotheses H1–H4.
- **Minimal Fix:** Add `FinalJudgement` model to `types.py` and `ingestion.py`. Refactor [evaluator.py](file:///D:/develop/works/ommatidia/src/ommatidia/evaluator.py) to compute $\text{FDA}$ from `FinalJudgement.verdict` against $V_i^*$, and implement the exact mathematical formulas for $\text{Recall}_{\text{crit}}$, $\text{FAR}$, $\text{WAR}$, $\text{UAR}$, and $\text{DSC}$ per Section 2 of [EVALUATION_SPEC.md](file:///D:/develop/works/ommatidia/research/EVALUATION_SPEC.md).
- **Boundary:** Static type / schema omission leading to runtime evaluation failure.

---

### Defect 3: Unknown Cost/Token Coercion to Zero & Budget Bypass in Conditions A & B
- **File & Line:** [src/ommatidia/conditions.py:45-48, 63-75, 90-112](file:///D:/develop/works/ommatidia/src/ommatidia/conditions.py#L45-L48)
- **Concrete Scenario 1 (Coercion to 0):** `types.py` line 166 guarantees that if either usage operand has `total_tokens = None` or `cost_yen = None`, the accumulated sum remains `None` (preserving unknown cost). However, `_accumulate_step_usage` in `conditions.py` bypasses `Usage.add()`:
  ```python
  if step_u.cost_yen is not None:
      usage.cost_yen = (usage.cost_yen or 0.0) + step_u.cost_yen
  if step_u.total_tokens is not None:
      usage.total_tokens = (usage.total_tokens or 0) + step_u.total_tokens
  ```
  If step 1 has `cost_yen = 10.0` and step 2 has `cost_yen = None` (unknown), `_accumulate_step_usage` skips the update, leaving `usage.cost_yen = 10.0`, treating unmeasured step 2 cost as $0.0$. Conversely, if step 1 is `None` and step 2 is `10.0`, `(usage.cost_yen or 0.0)` coerces `None` to `0.0`.
- **Concrete Scenario 2 (Budget Bypass):** In `ConditionARunner` and `ConditionBRunner`, `state.usage.exceeds(task.budget)` is **never** checked. If `executor_func` runs 100 tool calls and 100,000 ms, both runners still return `Decision.READY_FOR_REQUESTED_STEP` with `stop_reason = "single_pass_complete"`.
- **Concrete Scenario 3 (Budget Field Ignored):** `Usage.exceeds(budget)` in `types.py:180-205` checks `rounds`, `model_calls`, `tool_calls`, `elapsed_ms`, and `cost_yen`, but completely ignores `budget.max_input_chars` and `budget.max_output_tokens_per_call`.
- **Impact:** Violates repository accounting rules: "Include all planning, investigator, communication, retry, and synthesis costs in comparisons", and "unknown is not 0". Baselines A and B can run arbitrary out-of-budget operations without triggering budget termination.
- **Minimal Fix:** 
  1. In `_accumulate_step_usage`, delegate directly to `usage.add(step_u)`.
  2. In `ConditionARunner` and `ConditionBRunner`, call `if state.usage.exceeds(task.budget): state.decision = Decision.BLOCKED; state.stop_reason = "budget_exhausted"`.
  3. Update `Usage.exceeds()` to check character and token limits if tracked.
- **Boundary:** Static code logic flaw verified via targeted adversarial execution.

---

### Defect 4: Evidence Withdrawal Fails to Revoke Decision
- **File & Line:** [src/ommatidia/invalidation.py:128-140](file:///D:/develop/works/ommatidia/src/ommatidia/invalidation.py#L128-L140)
- **Concrete Scenario:** An understanding state has reached `Decision.READY_FOR_REQUESTED_STEP` because its required gaps were resolved. Subsequently, an evidence item is discovered to be invalid and withdrawn via `invalidate_evidence(state, [target_id], "superseded")`.
  `invalidate_evidence` reopens the resolved gap (`gap.status = GapStatus.OPEN`, `gap.resolution = None`) and updates claim statuses. However, it never updates `state.decision` or `state.stop_reason`.
  **Adversarial Reproduction Output:**
  ```text
  gap status: GapStatus.OPEN gap resolution: None state decision: Decision.READY_FOR_REQUESTED_STEP stop_reason: required_gaps_resolved
  ```
- **Impact:** The system remains in a "ready" state and claims all required gaps are resolved even when its supporting evidence has been completely retracted and open required gaps exist.
- **Minimal Fix:** In `invalidate_evidence`, if any required gaps are reopened or any supporting claims are invalidated, re-evaluate stopping conditions or reset `state.decision = Decision.NEEDS_CHECK` and clear `state.stop_reason`.
- **Boundary:** Verified dynamically in targeted reproduction test.

---

### Defect 5: Run Ledger Crash Deadlocks (Stale Process Locks)
- **File & Line:** [src/ommatidia/ledger.py:34-47](file:///D:/develop/works/ommatidia/src/ommatidia/ledger.py#L34-L47)
- **Concrete Scenario:** `RunLedger.acquire_lock` writes a lock file (`ledger.lock`) with `{"runId": ..., "pid": os.getpid()}`. If the Python process terminates abnormally (OOM killer, process crash, keyboard interrupt, exception before `__exit__`), the file remains on disk.
  Upon restarting the harness to resume execution, `self.lock_path.exists()` evaluates to `True` and unconditionally raises `ConcurrencyLockError`:
  ```text
  ConcurrencyLockError: Active run lock already held by run 'run1' since ...
  ```
- **Impact:** No crashed run can ever be resumed or restarted without manual filesystem intervention (deleting `.lock`). In an automated benchmark evaluation pipeline across 48 cases, a single crash halts the entire pipeline indefinitely.
- **Minimal Fix:** In `acquire_lock`, inspect `lock_data.get("pid")`. Check if the PID is actively running (e.g. via `psutil.pid_exists(pid)` or OS process query). If the PID is dead, log a warning, unlink the stale lock, and acquire the lock.
- **Boundary:** Run boundary crash consistency issue.

---

### Defect 6: Omission of Seal Verification during Harness Execution
- **File & Line:** [src/ommatidia/harness.py:48-52, 60-120](file:///D:/develop/works/ommatidia/src/ommatidia/harness.py#L48-L52), [scripts/run_harness.py:75-85](file:///D:/develop/works/ommatidia/scripts/run_harness.py#L75-L85)
- **Concrete Scenario:** While `scripts/verify_seals.py` exists as a standalone script, `ResearchHarness.evaluate_task()` and `ResearchHarness.run_paired_comparison()` **never call `self.verify_environment()`**. Furthermore, `scripts/run_harness.py` initializes `ResearchHarness` without passing `seal_manifest_path`.
  Additionally, [research/seal_manifest.json](file:///D:/develop/works/ommatidia/research/seal_manifest.json) contains:
  ```json
  {
    "datasets": {},
    "protocol": {
      "hash": "2b45fc0b16545d9dc54075bbeb4adac702cd8566b3d5ec518eca06a02bbb4e3a",
      "path": "research/PROTOCOL.md"
    },
    "schemaVersion": "0.1"
  }
  ```
  `datasets` is empty. Prompt files, source code files, and task benchmark definitions are not included in the manifest.
- **Impact:** The cryptographic seal is completely bypassed in real execution. Any file or prompt can be mutated without detection by the harness.
- **Minimal Fix:** In `ResearchHarness.__init__`, require `seal_manifest_path` by default and invoke `self.verify_environment()` before starting task execution. Expand the seal manifest to include prompt definitions, benchmark datasets, and package source digests.
- **Boundary:** Static configuration & runtime execution omission.

---

### Defect 7: Inadequate Held-out Leakage Detection
- **File & Line:** [src/ommatidia/seal.py:105-121](file:///D:/develop/works/ommatidia/src/ommatidia/seal.py#L105-L121)
- **Concrete Scenario:** `check_heldout_leakage` checks for leaks using:
  ```python
  for tid, answer in heldout_answers.items():
      if len(answer) >= 6 and answer.lower() in agent_visible_text.lower():
          violations.append(...)
  ```
- **Impact:** 
  1. Any answer shorter than 6 characters (e.g., "true", "false", "lock", "crash", "yes", "no") is completely bypassed.
  2. Only exact substring matching is checked. Semantic leakage, paraphrased answers, key rationale fragments, and critical locator leaks are completely unmonitored.
  3. A file hash seal manifest does not prevent an agent with file inspection tools from directly reading unsealed held-out files in the repository.
- **Minimal Fix:** Enforce file path compartmentalisation (store held-out keys in an encrypted archive or external directory inaccessible to the runtime execution environment). Expand leak scanning to check token n-grams and remove the arbitrary `>= 6` character threshold.
- **Boundary:** Static detection heuristic flaw.

---

### Defect 8: Brittle JSON Ingestion from Host Model Responses
- **File & Line:** [src/ommatidia/ingestion.py:46-55](file:///D:/develop/works/ommatidia/src/ommatidia/ingestion.py#L46-L55)
- **Concrete Scenario:** In `ingest_json_response`:
  ```python
  clean_text = raw_text.strip()
  lines = clean_text.splitlines()
  if lines and lines[0].strip().startswith("```"):
      lines = lines[1:]
  if lines and lines[-1].strip().startswith("```"):
      lines = lines[:-1]
  clean_text = "\n".join(lines).strip()
  data = json.loads(clean_text)
  ```
  If an LLM outputs any introductory or concluding text (e.g. `Here is the structured proposal:\n```json\n{...}\n````), `lines[0]` does not start with backticks, causing `json.loads` to crash with `JSONDecodeError`.
- **Impact:** External model calls that include conversational preamble or markdown annotations are discarded as errors, distorting failure rates.
- **Minimal Fix:** Use regex pattern matching to extract the inner JSON block between the first ```` ```(json)? ```` and the matching ```` ``` ````, or parse from the first `{` to the last `}`.
- **Boundary:** Runtime parser brittleness.

---

### Defect 9: Absence of Condition Prompts & Real Host Execution Wiring
- **File & Line:** [src/ommatidia/conditions.py:53-247](file:///D:/develop/works/ommatidia/src/ommatidia/conditions.py#L53-L247), [scripts/run_harness.py:18-62](file:///D:/develop/works/ommatidia/scripts/run_harness.py#L18-L62)
- **Concrete Scenario:** Conditions A through E are represented as control-flow loops, but none of them contain or supply the actual prompt templates specified in [research/EVALUATION_SPEC.md: Section 4](file:///D:/develop/works/ommatidia/research/EVALUATION_SPEC.md#L137-L195). Furthermore, `scripts/run_harness.py` uses `dummy_synthetic_executor`, which returns hardcoded mock outputs.
- **Impact:** There is no wiring to the host's child task delegation (`delegate_task`). The runtime is currently a mock-loop test harness, not an executable benchmark runner.
- **Minimal Fix:** Embed the standardised prompts from `EVALUATION_SPEC.md` directly into the condition runners and implement an adapter that bridges `executor_func` to T3 Code child delegation.
- **Boundary:** Static implementation gap.

---

## 4. Actual Commands Run & Unmodified Raw Output

All verification commands were executed directly on the host machine.

### 4.1 Pytest Test Suite
```powershell
python -m pytest -v
```
**Raw Output:**
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

============================= 24 passed in 0.09s ==============================
```

### 4.2 Seal Verification
```powershell
python scripts/verify_seals.py verify --manifest research/seal_manifest.json
```
**Raw Output:**
```
Seal verification passed successfully.
  protocol: OK
```

### 4.3 Harness Mechanism Check Execution
```powershell
python scripts/run_harness.py --mode mechanism_check --condition-primary E --output-dir research/output --run-id run_mech_001
```
**Raw Output:**
```
=== Running Ommatidia Research Harness [mechanism_check] ===
Output directory: research\output
Run ID: run_mech_001
Evaluating 2 dev mechanism fixture(s) under Condition E...
  Task dev_mech_cache_01: success=0, gap_recall=1.00, tool_calls=2
  Task dev_mech_duplicate_02: success=0, gap_recall=0.00, tool_calls=2
Execution completed successfully.
```

### 4.4 Harness Paired Comparison (Exposing $[0.0, 0.0]$ CI)
```powershell
python scripts/run_harness.py --mode paired_compare --condition-primary E --condition-baseline D --output-dir research/output --run-id run_paired_001
```
**Raw Output:**
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

### 4.5 Adversarial Decision Revocation Test (Defect 4 Reproduction)
```powershell
$env:PYTHONPATH='src'; python -c "from ommatidia.types import *; from ommatidia.state import *; from ommatidia.invalidation import *; b = Budget(5, 8, 12, 180000, 48000, 16000); t = TaskPacket('0.1', 't1', 'goal', 'explain', ['crit1'], [], [], b); s = create_initial_state(t); ev = Evidence('ev1', EvidenceKind.DOCUMENT, 'loc', 'grp', '2026-10-14', None, 'scope', 'pass', 'a'*64); s.evidence.append(ev); g = Gap('g1', GapKind.MISSING_FACT, 'l1', 'q1', ['ref'], 'matters', GapImportance.REQUIRED, ['c1'], status=GapStatus.RESOLVED, resolution=Resolution(ResolutionReason.SUPPORTED, ['ev1'], 'exp')); s.gaps.append(g); s.decision = Decision.READY_FOR_REQUESTED_STEP; s.stop_reason = 'required_gaps_resolved'; rep = invalidate_evidence(s, ['ev1'], 'debunked'); print('gap status:', s.gaps[0].status, 'gap resolution:', s.gaps[0].resolution, 'state decision:', s.decision, 'stop_reason:', s.stop_reason)"
```
**Raw Output:**
```
gap status: GapStatus.OPEN gap resolution: None state decision: Decision.READY_FOR_REQUESTED_STEP stop_reason: required_gaps_resolved
```

### 4.6 Adversarial Partial Unknown Usage Accumulation Test (Defect 3 Reproduction)
```powershell
$env:PYTHONPATH='src'; python -c "from ommatidia.types import Usage; from ommatidia.conditions import _accumulate_step_usage; u = Usage(cost_yen=10.0, total_tokens=50); _accumulate_step_usage(u, {'usage': {'costYen': None, 'totalTokens': None}}); print('cost_yen:', u.cost_yen, 'total_tokens:', u.total_tokens)"
```
**Raw Output:**
```
cost_yen: 10.0 total_tokens: 50
```

### 4.7 Task Gate Execution
```powershell
python "<HOME>\.agents\skills\bench-ledger-router\scripts\task_gate.py" "research/task-gate-runtime-state.json"
```
**Raw Output:**
```json
{"ok": false, "violations": ["G2: implement task task-runtime-implement not passing (verdicts: fail)", "G3: verify task task-runtime-verify (google) same vendor as implement task-runtime-implement"], "counts": {"implement": 1, "verify": 1}}
```
**Exit Code:** `1` (Rule violation detected: G2 non-passing verdict + G3 same-vendor verification).

---

## 5. Measurable Acceptance Counts & Ledger (`record.py`) Guidance

### 5.1 Acceptance Metrics
- **Mechanism Unit Tests Passed:** 24 / 24 ($100\%$).
- **Falsification Checkpoints Evaluated:** 11.
- **Blocking Defects Identified:** 9.
- **Empirical Benchmark Trials Executed:** 0 (synthetic fixture replay only).
- **Held-Out Case Efficacy Proven:** 0.0 (no empirical data or cases ingested).

### 5.2 Router Ledger (`record.py`) Requirements
In accordance with user instructions:
- **Do not record self scores:** No score has been written to the global bench ledger (`D:/develop/works/bench-ledger-engine/bench_ledger.db`).
- **Parent Reporting Guidance:** When the runtime defects are remediated and real empirical trials across the 48 cases are run via host child delegation, the parent orchestrator must record the measured run using:
  ```bash
  python "<HOME>\.agents\skills\bench-ledger-router\scripts\record.py" \
      --model "gemini-3.8-flash-high" \
      --bench "ommatidia-runtime-review-r1" \
      --score 0 \
      --failure \
      --domain "coding-verify" \
      --vendor "google" \
      --effort "model-encoded-high" \
      --notes "Round 1 review FAIL: 9 blocking defects identified (CI [0,0], EVALUATION_SPEC schema disconnect, budget bypass in A/B, invalidation decision retention, crash locks). Synthetic fixtures only."
  ```

---

## 6. Concrete Remediation Plan for Implementation Sub-Agent

Before requesting Round 2 review or initiating benchmark cohort execution:
1. **Align Schemas:** Introduce `FinalJudgement` into `types.py` matching [research/EVALUATION_SPEC.md: Section 3.2](file:///D:/develop/works/ommatidia/research/EVALUATION_SPEC.md#L90-L135). In [evaluator.py](file:///D:/develop/works/ommatidia/src/ommatidia/evaluator.py), score `FDA` directly on verdict strings (`supported`, `contradicted`, `disputed`, `inconclusive`).
2. **Fix Uncertainty Quantification:** Remove the degenerate Student's t calculation that emits $[0.0, 0.0]$ when $s=0$. Implement Wilson score continuity-corrected CIs for binomial accuracy and BCa bootstrap for continuous differences per Section 5.3.
3. **Fix Usage Accumulation:** Refactor `_accumulate_step_usage` in [conditions.py](file:///D:/develop/works/ommatidia/src/ommatidia/conditions.py) to call `Usage.add()` directly so that unknown costs (`None`) are never coerced to $0.0$. Add budget checks to `ConditionARunner` and `ConditionBRunner`.
4. **Fix Invalidation Cascade:** Update `invalidate_evidence` in [invalidation.py](file:///D:/develop/works/ommatidia/src/ommatidia/invalidation.py) to reset `state.decision = Decision.NEEDS_CHECK` and clear `state.stop_reason` whenever required gaps are reopened.
5. **Implement Stale Lock Detection:** Update `RunLedger.acquire_lock` in [ledger.py](file:///D:/develop/works/ommatidia/src/ommatidia/ledger.py) to check PID liveness before rejecting lock acquisition.
6. **Enforce Manifest Verification:** In [harness.py](file:///D:/develop/works/ommatidia/src/ommatidia/harness.py), call `self.verify_environment()` at the beginning of `evaluate_task` and `run_paired_comparison`. Expand `research/seal_manifest.json` to seal datasets and prompts once committed.
7. **Wire T3 Host Child Delegation:** Replace `dummy_synthetic_executor` with an actual adapter calling T3 Code's `delegate_task` with sealed payloads produced by `prepare_child_task_payload`.
