# Ommatidia Runtime and Research Harness Architecture

**Document Version:** 1.0.0  
**Language:** British English  
**Ownership:** Implementation Sub-agent (`src/`, `scripts/`, `tests/`, `pyproject.toml`, `research/runtime-design.md`, `research/hand_over_runtime.md`)

---

## 1. Architectural Boundaries and Principles

The Ommatidia runtime is designed as a minimal, reproducible, and verifiable Python empirical research harness grounded in the existing conceptual design (`docs/DESIGN.md`), protocol (`research/PROTOCOL.md`), and evaluation specification (`research/EVALUATION_SPEC.md`).

To preserve research integrity, the architecture is guided by six core principles:
1. **Zero Fabrication:** The harness never invents benchmark results, execution metrics, citations, or model capabilities. Where metrics are unavailable (e.g. monetary cost or token counts from certain host providers), fields are explicitly recorded as `None` (`null` in JSON) rather than being fabricated as `0`.
2. **Strict Evaluation Separation:** Gold standards, critical evidence hashes, and evaluation answer keys remain strictly segregated from agent-visible task packets and runtime states.
3. **No Unsanctioned CLI Subprocesses:** The runtime does not launch ordinary external provider CLIs (such as raw `claude` or `gemini` executable calls). Instead, it defines structured payload generation and response ingestion compatible with T3 Code host-native child task delegation.
4. **Zero Third-Party Runtime Dependencies:** The entire core runtime (`ommatidia.*`) relies strictly on the Python 3.10+ standard library (`dataclasses`, `json`, `hashlib`, `typing`, `enum`, `math`, `pathlib`). Testing uses standard `unittest` and `pytest`.
5. **Atomic Resumption and Concurrency Protection:** All experimental runs acquire process-level filesystem locks and log to append-only JSONL ledgers to prevent split-brain runs or corrupted checkpoints.
6. **Immutable Protocol Sealing:** SHA-256 cryptographic digests of the protocol specification and datasets are computed and verified before execution commences. Any seal mismatch halts execution immediately.

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
|                                        |  ommatidia.ingestion       |                            |        |
|                                        +-------------+--------------+                            |        |
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

The central state representation (`ommatidia.types.UnderstandingState`) tracks evidence-grounded reasoning without treating model hallucinations or search empty results as definitive proofs.

### 3.1 Data Structures
- **TaskPacket:** Encapsulates the immutable challenge brief: `taskId`, `goal`, `mode` (`explain` | `execute`), `successCriteria`, `capabilities`, initial `evidence`, and `budget`.
- **Evidence:** Immutable observation records containing `id`, `kind` (`document` | `code` | `test` | `user_statement`), `locator`, `sourceGroup`, `retrievedAt`, `version`, `scope`, `passage`, `contentHash` (SHA-256), `validity` (`current` | `withdrawn` | `superseded`), and `passageUnavailable`.
- **Claim:** Factual propositions with `id`, `role` (`observation` | `assumption` | `hypothesis` | `answer_claim`), `text`, `scope`, and `status` (`unverified` | `supported` | `contradicted` | `disputed`).
- **Lens:** Analytical viewpoints (`id`, `label`, `rationale`, `origin`, `status`).
- **Gap:** Explicit evidentiary uncertainties (`id`, `kind`, `lensId`, `question`, `triggerRefs`, `whyItMatters`, `importance`, `claimIds`, `probeIds`, `status`, `resolution`).
- **Probe:** Discriminating empirical investigations (`id`, `gapIds`, `method`, `question`, `requiredCapability`, `sourceGroups`, `successCondition`, `refutationCondition`, `inconclusiveCondition`, `status`).
- **Observation:** Verified empirical findings emitted by probe executions (`executionId`, `probeId`, `outcome`, `evidence`, `toolCalls`, `elapsedMs`, `costYen`, `totalTokens`).
- **Usage:** Physical tracking structure: `rounds`, `modelCalls`, `toolCalls`, `elapsedMs`, `totalTokens` (nullable), `costYen` (nullable).

### 3.2 State Transitions and Stopping Rules
The state machine evaluates stopping conditions deterministically:
1. **Budget Exhaustion:** If `usage.exceeds(budget)` evaluates to true, transition to `stopReason = "budget_exhausted"`, `decision = BLOCKED`.
2. **Required Gap Resolution:** If all gaps where `importance == REQUIRED` achieve `status == RESOLVED`, transition to `stopReason = "required_gaps_resolved"`, `decision = READY_FOR_REQUESTED_STEP`.
3. **Probe Exhaustion:** If all probes are complete or unavailable, and unresolved required gaps remain, transition to `stopReason = "probes_exhausted_unresolved_gaps"`, `decision = BLOCKED`. Otherwise `stopReason = "probes_exhausted"`, `decision = READY_FOR_REQUESTED_STEP`.

---

## 4. Evidence Invalidation Cascades and Falsification Rules

A critical requirement of empirical research is the ability to withdraw refuted or superseded findings without corrupting historical accounting:
1. **Deduplication:** When incoming evidence shares a SHA-256 `contentHash` with existing evidence, it is rejected as redundant. Citing the same source multiple times cannot artificially inflate evidentiary weight.
2. **Cascading Invalidation (`invalidate_evidence`):**
   - When evidence is marked `WITHDRAWN` or `SUPERSEDED`, all assessments citing the target evidence are invalidated.
   - Associated claims are re-evaluated: if supporting evidence is lost, the claim reverts to `UNVERIFIED` (or `DISPUTED` if conflicting assessments remain).
   - Any gaps whose resolution depended on the invalidated evidence are automatically reopened (`status = OPEN`, `resolution = None`).
   - Prior applied execution records and consumed physical resource usage are preserved in full to maintain honest budget accounting.
3. **Falsification Guardrails:** A tool timeout, permission denial, or empty search result is recorded as `unavailable` or `no_result`. The runtime strictly forbids converting execution failures or empty results into a refutation verdict or a gap resolution.

---

## 5. Experimental Condition Contracts (A through E)

All conditions operate within the exact same budget constraints (maximum 8 model calls, 12 tool calls, 180,000 ms elapsed time, 48,000 input characters):

| Condition | Class | Execution Contract | Role Allocation |
| :--- | :--- | :--- | :--- |
| **A (Baseline)** | `ConditionARunner` | Single-pass unguided investigation. Obtains sources and reaches conclusion without structured lens decomposition. | Single unconstrained investigator. |
| **B (Generic Recheck)** | `ConditionBRunner` | Two-pass investigation. Pass 1 conducts initial inquiry; Pass 2 re-checks for generic counterexamples and scope violations without role specialisation. | Single self-reflective investigator. |
| **C (Fixed Lenses)** | `ConditionCRunner` | Queries a fixed, pre-registered catalogue of lenses (Boundary limits, Counterexample search, Chronological divergence). | Fixed checklist investigator. |
| **D (Single Adaptive)** | `ConditionDRunner` | Maintains explicit `UnderstandingState`, dynamically generates gaps and probes, but executes all investigations sequentially. | Single adaptive investigator. |
| **E (Ommatidia Compound)** | `ConditionERunner` | Dynamically constructs perspective lenses and focused probe roles from `UnderstandingState`, dispatching bounded probe batches and cross-collating evidence. | Multi-role compound (Coordinator, Bounded Investigators, Collation). |

---

## 6. External Host Ingestion Interface (T3 Code Integration)

To support execution inside T3 Code without launching arbitrary CLI tools:
1. **Payload Preparation (`prepare_child_task_payload`):** Prepares clean, unpolluted JSON packets containing only public evidence, goal statements, and stage instructions. Private gold answers and held-out files are strictly excluded.
2. **Strict Response Validation (`ingest_proposal`, `ingest_observations`):**
   - Strips optional Markdown code fences (` ```json `).
   - Parses JSON strictly.
   - Enforces field presence, identifier formats, and enum memberships.
   - Returns typed domain objects or raises explicit `IngestionValidationError`.
3. **Usage Attribution:** Ingests reported model calls, tool calls, and elapsed times. Null token counts and costs remain `None`.

---

## 7. Run Ledger and Crash Consistency

The `RunLedger` provides an append-only, crash-consistent event ledger:
- **Stages Tracked:** `planning`, `investigator`, `communication`, `retry`, `synthesis`.
- **JSONL Ledger Format:** Each entry contains `timestamp`, `stage`, `executionId`, `taskId`, `condition`, `inputPayloadHash`, `outputPayloadHash`, `model`, `usage`, `status`, and `notes`.
- **Lock Management:** An atomic lock file (`<ledger>.lock`) prevents concurrent execution on the same target run.
- **Stage Aggregation:** `aggregate_usage_by_stage()` and `total_usage()` compute resource consumption partitioned by investigative lifecycle stage.

---

## 8. Objective Evaluation and Paired Comparison Framework

Scoring is implemented in `ommatidia.evaluator` and strictly decoupled from execution:
1. **Objective Metrics:**
   - **Final Decision Success ($FDA$):** Binary score indicating whether the final decision matches the pre-registered gold target.
   - **Required Gap Recall ($Recall_{\text{crit}}$):** Exact fraction of required questions identified, using an exact denominator ($|\mathcal{M}_i|$).
   - **Unnecessary Check Rate ($FAR$):** Proportion of probes targeting non-required issues.
   - **Valid Evidence Count ($DSC$):** Count of unique, non-withdrawn source content hashes cited.
   - **Contradiction Detection Rate:** Accuracy on negative control cases where initial claims must be refuted.
2. **Paired Statistics:**
   - For every matched case pair $i$, computes $\Delta_i = Score_{E, i} - Score_{\text{Baseline}, i}$.
   - Evaluates mean paired difference, standard error, and small-sample $t$-adjusted 95% confidence intervals.
   - Explicitly records caveat notes on small sample sizes ($N \le 24$ per cohort) to prevent premature claims of general superiority.
