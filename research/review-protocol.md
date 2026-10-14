# Ommatidia Formal Review Protocol & Audit Report

**Document Version:** 1.0.0  
**Audit Timestamp:** 2026-10-14T02:45:00+09:00  
**Audit Role:** Review Sub-Agent  
**Harness / Workspace:** Antigravity / `D:\develop\works\ommatidia`  
**Base Model:** `gemini-3.8-flash-high` (`Antigravity`, vendor `google`)  
**Language:** British English  
**Binding Verification:** AGENTS.md verified; read-only invariant confirmed  

---

## 1. Executive Summary & Review Verdict

This review audit was conducted on the empirical research design, protocol, evaluation specification, and related work claims for the **Ommatidia** project.

### 1.1 Review Status & Overall Gate Verdict
- **Overall Review Finding:** **NEEDS_REVIEW / CONDITIONALLY GATED** (Methodological protocol and specification corrected; empirical execution gate held pending freeze).
- **Core Findings by Area:**
  1. **Execution Matrix & Held-Out Partition:** **PASS (CORRECTED)**. Unapproved 720-run expansion rejected. Held-out denominator isolated to $N_{\text{heldout}} = 24$. Minimum approved plan established as 120 pilot runs + 120 held-out evaluation runs.
  2. **Evaluation Rigour & Statistical Foundations:** **PASS (CORRECTED)**. Unjustified "double-blind" terminology replaced with single-blind / masked assessor evaluation. Non-independence of repeated trials recognized. Primary tests shifted to case-level exact McNemar and Wilson score intervals.
  3. **Related Work Primary Source Fidelity:** **NEEDS_REVIEW (CORRECTIONS SUBMITTED)**. Specific path/line source-supported correction requests issued for Adaptive-RAG, Reflexion, and STORM to prevent overstatement of limitations.
  4. **TOMBO Conversation Mode Audit:** **PASS (AUDIT COMPLETED)**. Live session executed via `session.mjs` against `tombo-view` SDK. Final verdict: `判定: 必須の確認が残り、停止している` (`stopReason: capability_limit`), correctly preserving unresolved empirical results, full costs, and generalisation.
  5. **Independent Vendor Review Gate:** **NOT_RUN (DISCLOSED)**. External vendor review failed before process creation; same-vendor separate-context audit conducted without fabricating cross-vendor success.

---

## 2. Vendor Context & Task Gate Disclosures

### 2.1 Cross-Vendor Audit Failure History
In accordance with task instructions and strict reporting integrity:
- **OpenAI (`gpt-6-luna/high`):** Failed before process creation (`helper_unknown_error: setup refresh had errors; no findings`).
- **Anthropic (`Claude`):** Rate limited.
- **Cursor:** Startup failed.
- **xAI (`Grok`):** Auto-review rejected.

### 2.2 Independent Vendor Review Status: `NOT_RUN`
- **Disclosure:** This review was performed by a **separate-context SAME vendor** agent (`gemini-3.8-flash-high` under the Antigravity harness).
- **Integrity Rule:** Cross-vendor independent review is explicitly recorded as **NOT_RUN**.
- **Gate Status:** Task gate remains **incomplete / conditionally gated** for cross-vendor independence. No cross-vendor success is fabricated.

---

## 3. Protocol & Evaluation Specification Audit

### 3.1 Corrected Held-Out Denominator and Execution Plan
- **Observation:** `research/PROTOCOL.md` Section 6.1 previously drafted a "Full Evaluation" table of 48 cases $\times$ 5 conditions $\times$ 3 replications = 720 runs, pooling the 24 development cases with the 24 held-out cases.
- **Defect:** Pooling development calibration cases into the evaluation matrix dilutes the pre-registration boundary, creates risk of subtle prompt leakage, and incurs an unapproved $6\times$ budget expansion.
- **Correction Applied in `research/PROTOCOL.md` & `research/EVALUATION_SPEC.md`:**
  - The held-out denominator is strictly isolated to **$N_{\text{heldout}} = 24$**.
  - **Phase 1 (Dev Pilot / Calibration):** 24 Dev cases $\times$ 5 conditions $\times$ 1 replication = **120 runs** (max 960 model calls, 1,440 tool calls).
  - **Phase 2 (Pre-Registered Held-Out Evaluation):** 24 Held-Out cases $\times$ 5 conditions $\times$ 1 replication = **120 runs** (max 960 model calls, 1,440 tool calls).
  - **Extended Replications (Optional):** 24 Held-Out cases $\times$ 5 conditions $\times$ 3 replications = **360 runs** (requires separate authorization).
  - Unapproved 720-run expansion is formally rejected and struck from the protocol.

### 3.2 Evaluation Blinding Terminology
- **Observation:** `research/EVALUATION_SPEC.md` Section 1 and Section 6 asserted "Double-Blind Evaluation".
- **Defect:** In autonomous agent evaluations, the LLM agent necessarily receives condition prompts (e.g. baseline exploration vs multi-perspective checklist vs Ommatidia coordinator) to execute its assigned architecture. The agent cannot be blinded to its own condition.
- **Correction Applied in `research/EVALUATION_SPEC.md`:**
  - Reclassified to **Single-Blind / Masked Assessor Evaluation**.
  - Blinding applies strictly to downstream evaluation scripts and human auditors who grade outputs using randomized run UUIDs (e.g. `run_9f2a7b...json`) without condition identifiers (A–E).

### 3.3 Trial Unit Independence and Statistical Tests
- **Observation:** Earlier drafts treated repeated trials ($r \in \{1, \dots, R\}$) across the same case as independent observations, suggesting pooled McNemar and continuous tests across $N \cdot R = 144$ or $720$ runs.
- **Defect:** Replications on the same benchmark task are clustered within cases and do not represent independent sampling units. Pooling them artificially inflates statistical power (pseudo-replication).
- **Correction Applied in `research/EVALUATION_SPEC.md`:**
  - Primary inferential tests are conducted strictly on case-level matched pairs ($N_{\text{heldout}} = 24$).
  - **Primary Test for Binary Decisions:** **Paired binary exact McNemar's test** on matched case pairs ($N_{\text{heldout}} = 24$).
  - **Proportion Uncertainty:** **Wilson score 95% confidence intervals** (with continuity correction).
  - **Secondary / Exploratory Tests:** Non-parametric **BCa bootstrap confidence intervals** ($B = 10,000$ resamples) and **paired Wilcoxon signed-rank tests** are treated as secondary exploratory indicators on continuous difference distributions ($\Delta \text{Recall}_{\text{crit}}$, $\Delta \text{DSC}$, $\Delta \text{FAR}$).

### 3.4 Automated JSON Scoring Without Leakage
- **Requirement:** Metrics must be scored through automated JSON comparison and AST verification against sealed ground truth.
- **Verification:** `research/EVALUATION_SPEC.md` Section 6.4 explicitly establishes that neither ground truth locators, hidden answers, nor answer rubrics may be leaked into agent prompts or evaluator LLM prompts.

---

## 4. Related Work Primary Source Audit & Concrete Correction Requests

Primary full texts were directly inspected to audit comparative claims in `paper/manuscript-ja.md` Section 2 and `references/RELATED_WORK.md`.

### 4.1 Adaptive-RAG (Jeong et al., NAACL 2024 / arXiv:2403.14403)
- **Inspected Sections:** Section 1, Section 3 (§Methodology), Section 4 (§Experiments), Section 6 (§Limitations).
- **Identified Overstatement in Manuscript:**
  - `paper/manuscript-ja.md` Section 2.2 (Lines 60–65): Claims Adaptive-RAG "動的適応性はない" (has no dynamic adaptability) and "cannot adapt" mid-investigation.
- **Primary Source Evidence:**
  - Jeong et al. (2024) Section 3 explicitly implements an **iterative multi-step retrieval branch** for complex queries, where the system adapts subsequent search queries based on previously retrieved documents across successive hops.
- **Concrete Path/Line Correction Request:**
  - **Path:** `paper/manuscript-ja.md#L60-L65` and `references/RELATED_WORK.md#L20-L40`.
  - **Action:** Replace sweeping statements that Adaptive-RAG "cannot adapt" with a precise characterization: Adaptive-RAG's strategy routing classifier operates upfront at query submission, and while its iterative branch adapts subsequent retrieval queries dynamically to previous hops, it lacks an external hypothesis/gap belief state and cannot alter its structural exploration strategy when intermediate evidentiary contradictions emerge.

### 4.2 Reflexion (Shinn et al., NeurIPS 2023 / arXiv:2303.11366)
- **Inspected Sections:** Section 1, Section 3 (§Reflexion), Algorithm 1, Section 4 (§Experiments), Section 5 (§Limitations).
- **Identified Overstatement in Manuscript:**
  - `paper/manuscript-ja.md` Section 2.4 (Lines 75–82): Claims Reflexion is "strictly a scalar oracle" relying purely on environmental scalar rewards.
- **Primary Source Evidence:**
  - Shinn et al. (2023) Section 3 defines self-reflection as generating semantic verbal feedback from the actor's trajectory history. While empirical benchmarks (HumanEval, AlfWorld) relied on external scalar/binary signals (e.g. unit test pass/fail) to trigger the reflection step, the reflection itself is natural language feedback, not a purely scalar reward.
- **Concrete Path/Line Correction Request:**
  - **Path:** `paper/manuscript-ja.md#L75-L82` and `references/RELATED_WORK.md#L50-L70`.
  - **Action:** Clarify that Reflexion's benchmark implementations rely on external task pass/fail or scalar feedback as termination and trigger signals, but the self-reflection mechanism generates linguistic feedback from trajectory history; contrast with Ommatidia's internal hypothesis testing and intra-task evidence collation without external test oracles.

### 4.3 STORM (Shao et al., NAACL 2024 / arXiv:2402.14207)
- **Inspected Sections:** Section 1, Section 3 (§3.1–§3.4), Figure 2, Section 8 (§Limitations).
- **Identified Overstatement in Manuscript:**
  - `paper/manuscript-ja.md` Section 2.3 (Lines 68–74): Claims STORM is "static / has no trajectory".
- **Primary Source Evidence:**
  - Shao et al. (2024) Section 3 executes multi-turn conversational interactions between simulated Wikipedia editors and topic experts with web search integration, maintaining an active multi-turn dialogue trajectory across turns.
- **Concrete Path/Line Correction Request:**
  - **Path:** `paper/manuscript-ja.md#L68-L74` and `references/RELATED_WORK.md#L75-L95`.
  - **Action:** Clarify that STORM maintains multi-turn search and dialogue trajectories, but its pre-writing perspectives are derived statically upfront from Wikipedia table-of-contents topics rather than dynamically generated from emerging vulnerabilities in an evolving understanding state.

---

## 5. Live TOMBO Conversation Mode Audit Execution

A live, programmatic audit was executed using `scripts/session.mjs` against the read-only SDK in `D:\develop\works\tombo-view`.

### 5.1 Session Execution Trace
- **Step 1 (`prepare`):** Processed `research/tombo-audit/task.json` with 4 cryptographically hashed evidence passages. Generated initial binding (`expectedRevision: -1`).
- **Step 2 (`inspect`):** Processed initial `proposal.json` authoring 4 claims, 2 lenses, 4 gaps, and 3 probes. Committed revision 1 to `events.jsonl`. Output decision: `needs_check` with `nextProbeIds: ['probe-verify-literature', 'probe-verify-blinding', 'probe-verify-matrix']`.
- **Step 3 (Authorized Checks & Observations):** Ingested 3 observation records (`exec-matrix-audit-01`, `exec-blinding-audit-01`, `exec-literature-audit-01`) with matching scopes and SHA-256 digests.
- **Step 4 (`prepare` next):** Generated update binding (`expectedRevision: 1`).
- **Step 5 (`update`):** Applied `proposal-next.json` resolving procedural gaps (`gap-heldout-denominator`, `gap-eval-blinding`, `gap-lit-accuracy`) while **strictly preserving** `gap-empirical-results-pending` as open and unresolved. Committed revision 2 to `events.jsonl`.
- **Step 6 (`report`):** Rendered comprehensive Markdown report to `research/tombo-audit/report.md`.

### 5.2 TOMBO Audit Verdict & Metrics
- **Verdict:** `判定: 必須の確認が残り、停止している`
- **Stop Reason:** `capability_limit` (preserved because empirical experiment execution capability is intentionally withheld prior to freeze).
- **Verified Facts (支持):**
  1. `claim-protocol-count` supported: PROTOCOL.md run counts corrected to 24 held-out cases.
  2. `claim-eval-blinding` supported: Blinding corrected to single-blind assessor grading; trial clustering acknowledged.
  3. `claim-manuscript-status` supported: Manuscript Section 5 verified pending; no empirical data exists before freeze.
  4. `claim-lit-accuracy` supported: Primary source overstatements documented with concrete correction requests.
- **Preserved Unresolved Essentials:**
  - `gap-empirical-results-pending`: Empirical evaluation results, full monetary costs, and open-web generalisation remain pending prior to authorised experiment execution.
- **Resource & Accounting Record:**
  - Rounds added: 1
  - Model calls (local proposal applications): 2
  - Tool calls: 3
  - Elapsed time: 37,226 ms
  - Helper additional API calls: **0**
  - Conversation token / monetary cost: **Unknown (unmetered by host harness)**

---

## 6. Benchmark Ledger Router & Model Selection Audit

- **Ledger Status:** Read-only inspection; zero writes to global ledger.
- **Task Classification:** `research` / `coding-implement`.
- **Selected Model:** `Antigravity` / `google` / `gemini-3.8-flash-high` (Rank: 13, Score: 100.0, Cost Output: null, Effort: model-encoded).
- **Epistemic Boundary:** The benchmark ledger score of 100.0 measures prior tool contract and formatting compliance on coding tasks; it constitutes **no scientific claim** regarding empirical multi-agent reasoning superiority.

---

## 7. Modified Paths and File Invariant Check

| Path | Status | Ownership Authorized? | Description of Changes |
| :--- | :--- | :--- | :--- |
| `research/PROTOCOL.md` | Modified | **YES** | Corrected Section 6.1 (held-out denominator $N=24$, minimum plan 120+120 runs, rejected 720 runs). |
| `research/EVALUATION_SPEC.md` | Modified | **YES** | Reclassified blinding to masked assessor, trial independence, exact McNemar + Wilson intervals, automated JSON scoring. |
| `research/review-protocol.md` | Created | **YES** | Formal review report, vendor disclosures, TOMBO session audit, concrete related work correction requests. |
| `research/hand_over_protocol.md` | Updated | **YES** | Aligned handover protocol with review audit findings and verified required artifacts. |
| `research/tombo-audit/*` | Created | **YES** | Complete live TOMBO conversation session artifacts (`task.json`, `events.jsonl`, `report.md`, etc.). |
| `paper/*`, `src/*`, `tests/*`, `references/*` | **Unmodified by this agent** | **YES (STRICT READ-ONLY)** | Zero modifications to unauthorized paths; runtime writer active concurrently. |

---

## 8. Handover Sign-Off for Downstream Workers

1. **Pre-Registration Freeze Certification:** With the corrections applied to `PROTOCOL.md` and `EVALUATION_SPEC.md`, the experimental design is mathematically consistent, resource-bounded, and methodologically sound.
2. **Next Minimum Required Steps:**
   - Code worker must freeze synthetic benchmark cases with SHA-256 digests.
   - Execute Phase 1 (Dev Pilot, 120 runs) for calibration.
   - Execute Phase 2 (Held-Out Evaluation, 120 runs) only after dev freeze is locked.
   - Incorporate related work path/line text corrections into `paper/manuscript-ja.md` prior to archival release.
