> R3 notice (2026-10-15): Readiness and implementation claims below are historical and superseded by [the R3 driver contract](runtime-driver-r3.md) and [the R3 remediation handover](hand_over_runtime_fix_r3.md). No empirical study has been completed; the evaluation package requires replacement after the disclosed boundary violation.

# Ommatidia Runtime and Research Harness Architecture

**Document Version:** 2.0.0\
**Language:** British English  
**Ownership:** Implementation Sub-agent (`src/`, `scripts/`, `tests/`, `pyproject.toml`, `research/runtime-design.md`, `research/hand_over_runtime.md`, `research/hand_over_runtime_fix_r2.md`, `research/task-gate-runtime-state.json`)

---

## 1. Architectural Boundaries and Principles

The Ommatidia runtime is designed as a minimal, reproducible, and verifiable Python empirical research harness grounded in the conceptual design (`docs/DESIGN.md`), protocol (`research/PROTOCOL.md`), and evaluation specification (`research/EVALUATION_SPEC.md`).

Following independent cross-vendor review ([research/review-runtime-round2.md](file:///D:/develop/works/ommatidia/research/review-runtime-round2.md)), the architecture is strictly governed by the following core invariants:
1. **Zero Fabrication & Strict Fail-Closed Semantics:** The harness never invents benchmark results, execution metrics, citations, or model capabilities. Where metrics are unavailable (e.g. monetary cost or token counts from certain host providers), fields are explicitly recorded as `None` (`null` in JSON) rather than being fabricated as `0`. If T3 child delegation is unavailable, execution fails closed immediately; silent fallback to synthetic fixtures has been completely eliminated.
2. **Strict Evaluation Separation:** Gold standards, critical evidence hashes, and evaluation answer keys remain strictly segregated from agent-visible task packets and runtime states.
3. **No Unsanctioned Subprocesses:** The runtime does not launch raw external provider CLIs (such as unmetered `claude` or `gemini` executable calls). Instead, it defines structured payload generation and response ingestion compatible with T3 Code host-native child task delegation.
4. **Zero Third-Party Runtime Dependencies:** The entire core runtime (`ommatidia.*`) relies strictly on the Python 3.10+ standard library (`dataclasses`, `json`, `hashlib`, `typing`, `enum`, `math`, `pathlib`, `uuid`, `random`, `time`). Testing uses standard `unittest` and `pytest`.
5. **Atomic Resumption and Cumulative Accounting:** All experimental runs acquire process-level filesystem locks and log to append-only JSONL ledgers. The resource registry is persisted atomically to disk (`resource_registry.json`) and reconciled with existing trial files upon restart so that aggregate usage across process restarts is strictly cumulative and never resets to 0.
6. **Immutable Protocol Sealing:** SHA-256 cryptographic digests of the protocol specification and dataset manifests are verified before execution commences. Any seal mismatch halts execution immediately.

---

## 2. Component Architecture

```
                                    +-----------------------------------+
                                    |     research/PROTOCOL.md          |
                                    |     research/EVALUATION_SPEC.md   |
                                    +-----------------+-----------------+
                                                      |
                                           (Cryptographic Seal)
                                                      v
                                        +----------------------------+
                                        |   ommatidia.seal           |
                                        +----------------------------+
                                                      |
+-----------------------------------------------------+-----------------------------------------------------+
|                                                     v                                                     |
|                                        +----------------------------+                                     |
|                                        |  ommatidia.harness         |                                     |
|                                        +-------------+--------------+                                     |
|                                                      |                                                    |
|            +-----------------------+-----------------+-----------------------+---------------------+      |
|            v                       v                                         v                     v      |
|  +--------------------+  +--------------------+                    +--------------------+  +------------+ |
|  | Condition A Runner |  | Condition B Runner |  ... [C, D, E] ... |  ommatidia.ledger  |  | Evaluator  | |
|  +---------+----------+  +---------+----------+                    +--------------------+  +-----+------+ |
|            |                       |                                                             |        |
|            +-----------------------+-----------------+                                           |        |
|                                                      |                                           |        |
|                                                      v                                           |        |
|                                        +----------------------------+                            |        |
|                                        |    T3 Host Child Call      |                            |        |
|                                        | (Structured Ingestion API) |                            |        |
|                                        +-------------+--------------+                            |        |
|                                                      |                                           |        |
|                                                      v                                           |        |
|                                        +----------------------------+                            |        |
|                                        |  ommatidia.state           |                            |        |
|                                        |  ommatidia.invalidation    |                            |        |
|                                        +-------------+--------------+                            |        |
|                                                      |                                           |        |
|                                                      +-------------------------------------------+        |
|                                                                                                           |
+-----------------------------------------------------------------------------------------------------------+
```

---

## 3. Strongly Typed Understanding State

The central state representation (`ommatidia.types.UnderstandingState`) tracks evidence-grounded reasoning without treating model hallucinations or empty search results as definitive proofs.

### 3.1 Data Structures
- **TaskPacket:** Encapsulates the immutable challenge brief: `taskId`, `goal`, `mode` (`explain` | `execute`), `successCriteria`, `capabilities`, initial `evidence`, `budget`, and `proposedAnswer`.
- **Evidence:** Immutable observation records containing `id`, `kind`, `locator`, `sourceGroup`, `retrievedAt`, `version`, `scope`, `passage`, `contentHash` (SHA-256), `validity` (`current` | `withdrawn` | `superseded`), and `passageUnavailable`.
- **Claim:** Factual propositions with `id`, `role` (`observation` | `assumption` | `hypothesis` | `answer_claim`), `text`, `scope`, and `status` (`unverified` | `supported` | `contradicted` | `disputed`).
- **Lens:** Analytical viewpoints (`id`, `label`, `rationale`, `origin`, `status`).
- **Gap:** Explicit evidentiary uncertainties (`id`, `kind`, `lensId`, `question`, `triggerRefs`, `whyItMatters`, `importance`, `claimIds`, `probeIds`, `status`, `resolution`).
- **Probe:** Discriminating empirical investigations (`id`, `gapIds`, `method`, `question`, `requiredCapability`, `sourceGroups`, `successCondition`, `refutationCondition`, `inconclusiveCondition`, `status`).
- **Observation:** Verified empirical findings emitted by probe executions (`executionId`, `probeId`, `outcome`, `evidence`, `toolCalls`, `elapsedMs`, `costYen`, `totalTokens`).
- **Usage:** Physical tracking structure: `rounds`, `modelCalls`, `toolCalls`, `elapsedMs`, `inputChars`, `totalTokens` (nullable), `costYen` (nullable).
- **FinalJudgement:** Standardised schema-conformant final resolution emitted by model conditions: `taskId`, `verdict`, `confidenceScore`, `justification`, `citedEvidence`, `unresolvedGaps`, `resourceUsage`.

### 3.2 State Transitions, Observation Ingestion, and Stopping Rules
The state machine evaluates stopping conditions deterministically:
1. **No Double-Counting of Tool Calls:** Tool calls and elapsed time are accumulated at the step level via `_accumulate_step_usage`. In `apply_observations`, default execution does not add observation tool calls again, preventing artificial metric inflation.
2. **Strict Unknown-to-Known Invariant:** Unknown costs (`cost_yen = None`) or token counts remain `None` when adding observation usage. Missing measurements cannot be promoted to known values.
3. **Budget Exhaustion:** If `usage.exceeds(budget)` evaluates to true, transition to `stopReason = "budget_exhausted"`, `decision = BLOCKED`.
4. **Required Gap Resolution:** If all gaps where `importance == REQUIRED` achieve `status == RESOLVED`, transition to `stopReason = "required_gaps_resolved"`, `decision = READY_FOR_REQUESTED_STEP`.
5. **Probe Exhaustion:** If all probes are complete or unavailable, and unresolved required gaps remain, transition to `stopReason = "probes_exhausted_unresolved_gaps"`, `decision = BLOCKED`. Otherwise `stopReason = "probes_exhausted"`, `decision = READY_FOR_REQUESTED_STEP`.

---

## 4. Evidence Invalidation Cascades and Falsification Rules

A critical requirement of empirical research is the ability to withdraw refuted or superseded findings without corrupting historical accounting:
1. **Deduplication:** When incoming evidence shares a SHA-256 `contentHash` with existing evidence, it is rejected as redundant. Citing the same source multiple times cannot artificially inflate evidentiary weight.
2. **Withdrawal Cascades:** When an evidence item is marked `withdrawn` or `superseded`:
   - All dependent claims citing that evidence lose verification.
   - Any gap resolved solely based on withdrawn evidence transitions from `RESOLVED` back to `OPEN`.
   - Associated probes are scheduled for re-investigation if budget permits.

---

## 5. Experimental Conditions (A to E) Contracts

Every experimental condition executes under the identical base model envelope (`gemini-3.8-flash-high`) and strict per-case budget ceilings:
- **Condition A (Baseline Monolith):** Single pass unguided exploration with `PROMPT_CONDITION_A`.
- **Condition B (Generic Re-examination):** Two-phase check: Phase 1 standard query, followed by Phase 2 generic critique (`PROMPT_CONDITION_B_PHASE2`) prompting for negative counterexamples and boundary omissions.
- **Condition C (Fixed Perspectives):** Evaluates across 5 mandatory static viewpoints (`Scope`, `Counterexample`, `Temporal`, `Dependency`, `Redundancy`). Observations without pre-registered probes are handled gracefully.
- **Condition D (Single Adaptive Investigator):** Maintains explicit understanding state, iteratively selecting one critical gap and executing one probe at a time through a sequential single-agent loop.
- **Condition E (Ommatidia Full Compound):** Multi-role coordinator dynamically generating candidate lenses, deriving prioritized probe roles, and collating structured evidence with automated invalidation, concluding with a dedicated synthesis step.

---

## 6. Crash Consistency, Ledger Sanitization, and Failed-Trial Accounting

- **Append-Only Ledger:** `RunLedger` writes stage entries (`planning`, `investigator`, `communication`, `retry`, `synthesis`) to `ledger.jsonl`.
- **Torn Line Sanitization:** `sanitize_ledger_file` automatically cleans trailing incomplete or torn JSON lines resulting from ungraceful process termination, preventing resume deadlocks.
- **Failed Trial Preservation:** When an executor fails or encounters an unhandled exception, a `TrialRecord` with `status="failed"`, `decision="failed"`, and the captured error message is persisted immediately. Failed trials are retained in the pre-registered $N=24$ evaluation denominator with $FDA = 0$ rather than aborting the entire cohort.
- **Filesystem Concurrency Lock:** Acquires a PID-annotated lockfile (`ommatidia_run.lock`) preventing simultaneous execution runs in the same workspace.

---

## 7. Objective Scoring and Paired Comparisons

1. **Objective Metrics:**
   - **Final Decision Accuracy ($FDA$):** Binary score indicating whether `FinalJudgement.verdict` matches ground truth $V_i^*$.
   - **Critical Item Recall ($Recall_{\text{crit}}$):** Exact fraction of required questions identified, using an exact denominator ($|\mathcal{M}_i|$). Evaluator strictly excludes evidence hashes already present in the task input packet, crediting only novel retrieval.
   - **Disjoint Source Coverage ($DSC$):** Count of unique, independent source groups verified in cited evidence.
   - **Unnecessary Check Rate ($FAR$):** Proportion of probes targeting non-required issues.
2. **Pre-Registered Paired Statistics:**
   - **Exact McNemar Test:** Computed via standard library `math.comb` on discordant pairs $(b, c)$ for paired binary FDA differences.
   - **Wilson Score 95% Confidence Intervals:** Computed with continuity correction for binomial proportions.
   - **Paired Wilcoxon Signed-Rank Test:** Applied to continuous difference distributions ($\Delta Recall_{\text{crit}}$, $\Delta DSC$).
   - **Holm-Bonferroni Step-Down Correction:** Controls family-wise error rates ($\alpha = 0.05$) across primary hypotheses H1–H4.
   - **Stored Data Analysis:** `--mode paired_compare` reads stored, completed trial records from disk; mechanism fixtures are never executed during comparative analysis.

---

## 8. Testable Dataset Loader and Zero-Leakage Architecture

The dataset ingestion subsystem (`ommatidia.harness.load_public_packets`) guarantees strict empirical isolation:
1. **Public Packet Ingestion:** Loads task packets from `public_packets/` exclusively. Each packet is cryptographically verified against the SHA-256 digests in `manifest.json`.
2. **File Count and Allowlist Enforcement:** Enforces exact expected packet counts ($N=24$), rejects unlisted or duplicate files, and asserts that no gold fields (`ground_truth_verdicts`, `critical_evidence_hashes`, `target_decision`, `unblinding_key`) exist in the packet.
3. **Gold Standard Segregation:** Rubrics located in `gold/` are never attached to `TaskPacket` or accessible to operational runners (Conditions A–E). Operational models only receive task goals, success criteria, and public evidence locators.

---

## 9. Global Resource Registry and Cumulative 1,920 Ceiling

To enforce pre-registered experimental boundaries and prevent budget runaway, the harness implements a unified `GlobalResourceRegistry`:
1. **Aggregate Ceilings:**
   - **Total Trials:** Hard cap of 240 trials (Phase 1: 120 dev + Phase 2: 120 held-out).
   - **Model Invocations:** Hard cap of 1,920 aggregate model turns ($240 \times 8$).
   - **Tool Invocations:** Hard cap of 2,880 aggregate tool invocations ($240 \times 12$).
2. **Per-Trial Envelopes:**
   - Maximum 8 model turns, 12 tool invocations, 180,000 ms elapsed wall-clock, 48,000 input characters.
   - If an individual trial exceeds any dimension, execution halts with `ResourceLimitExceeded`.
3. **Atomic Persistence and Pre-Call Reservation:**
   - Persists state atomically to `resource_registry.json`.
   - `reserve_model_call(1)` validates quota availability before any child call is dispatched.
   - Negative usage values are rejected with `ValueError`.
4. **Host Metering Integrity:**
   - Host `time.perf_counter()` and payload string length override child self-reporting to prevent under-reporting.
   - Where the host environment does not measure token counts or monetary cost, fields remain strictly `null` (`None`). Missing measurements cannot be coerced to zero or used to prove caps.

---

## 10. Robust Crash-Consistent Resume

Long-running cohorts across 24 cases $\times$ 5 conditions are protected against interruptions:
1. **Trial-Level Atomicity:** Each trial emits an immediate JSON record into `output_dir / <partition> / trials / <taskId>_<condition>.json` via atomic rename (`.tmp` + `os.replace`).
2. **Executor Provenance Verification:** Upon resume, existing trial records are verified to match the active executor (`synthetic` vs `t3`). Synthetic records cannot be re-used in a live execution.
3. **Counter Reconciliation:** Skipped trial records are loaded and added to the cumulative registry so that process restarts never reset usage counters to 0.

---

## 11. Single-Blind Masked Assessor Evaluation & UUID Masking

In accordance with `research/EVALUATION_SPEC.md` Section 1, human and LLM evaluators must not observe condition labels:
1. **Condition Masking:** Experimental conditions (A–E) are permuted to neutral identifiers (`MCOND_01` to `MCOND_05`) with unpredictable seeding.
2. **UUID Trial Keys:** Every trial is assigned a random RFC 4122 UUID4 identifier.
3. **Usage Fingerprint Stripping:** Call counts and resource usage fields (`modelCalls`, `toolCalls`, `elapsedMs`, `inputChars`) are strictly stripped from `masked_evaluation_set.json` to prevent condition de-anonymization based on call volume.
4. **Isolated Unblinding Key:** The mapping from masked trial UUID to true task, condition, and run identifier is stored in a separate restricted file (`unblinding_key.json`).

---

## 12. T3 Code Dispatch-Ready Trial Export and In-Session Controller Protocol

1. **Dispatch-Ready Plan Export (`--mode plan`):** Generates pre-formulated, sealed `DispatchReadyJob` records containing `clientRequestId`, prompt, target model (`agy:gemini-3.8-flash-high`), proposedAnswer, budget, and strict FinalJudgement JSON schema.
2. **Multi-Step Condition Sequence Fidelity:** Full condition sequences (Condition B 2 phases, Condition C 5 lenses, Condition D sequential loop, Condition E coordinator/investigator/synthesis) are represented in export plans.
3. **In-Session Controller (`T3CampaignController`):** Dispatches jobs via `mcp__t3_code__delegate_task`, polls with `task_status`, cancels timed-out tasks with `task_cancel`, and appends trial results incrementally.
4. **Fail-Closed Diagnostics:** If executed via CLI with `--executor t3` without an in-session dispatcher or ACP node, the harness raises a clean diagnostic error and terminates immediately with exit code 1.
