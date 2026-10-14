# Ommatidia Research Design Hand-Over Protocol

**Document Version:** 1.1.0  
**Status:** Design and Review Phase Completed; Ready for Code Worker Implementation.  
**Language:** British English.  
**Author / Role:** Design & Review Sub-Agents (`Antigravity`, model: `gemini-3.8-flash-high`).  
**Target Recipient:** Concurrent Code Worker & Manuscript Author.  

---

## 1. Executive Summary & Deliverables

As authorised by the task specification, the design and review sub-agents have established and verified the formal pre-registration research foundation for **Ommatidia** under workspace `D:\develop\works\ommatidia`. 

### Delivered Artifacts (Strict Ownership: Named Files Only)
1. [`research/PROTOCOL.md`](file:///D:/develop/works/ommatidia/research/PROTOCOL.md):  
   Empirical research protocol defining the core research question, operational hypotheses (H1 to H4), balanced experimental conditions (A to E), 48-case benchmark architecture (24 dev / 24 held-out with 4 control classes), resource envelopes, corrected held-out denominator ($N_{\text{heldout}} = 24$), phased execution matrix (120 pilot + 120 held-out evaluation runs), and boundary distinctions.
2. [`research/EVALUATION_SPEC.md`](file:///D:/develop/works/ommatidia/research/EVALUATION_SPEC.md):  
   Automated objective scoring specification providing mathematical formulations for all primary ($\text{FDA}$, $\text{Recall}_{\text{crit}}$) and secondary metrics ($\text{FAR}$, $\text{Prec}_{\text{cand}}$, $\text{DDR}$, $\text{WAR}$, $\text{UAR}$, $\text{DSC}$), efficiency ratios, input/output JSON schemas, prompt specifications across conditions A to E, case-level paired exact McNemar tests, Wilson score confidence intervals, Holm-Bonferroni correction, single-blind / masked assessor protocols, and leakage-free automated scoring.
3. [`research/review-protocol.md`](file:///D:/develop/works/ommatidia/research/review-protocol.md):  
   Formal independent review report recording vendor disclosures (cross-vendor review `NOT_RUN`), statistical and methodological audit findings, live TOMBO session audit verdicts, and concrete path/line primary-source correction requests for Adaptive-RAG, Reflexion, and STORM.
4. [`research/hand_over_protocol.md`](file:///D:/develop/works/ommatidia/research/hand_over_protocol.md) *(this document)*:  
   Formal hand-over contract, recording live ledger evidence, verification boundaries, execution budgets, vendor gate disclosures, and implementation directives for the code worker.
5. [`research/tombo-audit/*`](file:///D:/develop/works/ommatidia/research/tombo-audit/):  
   Complete live TOMBO conversation-mode session artifacts (`task.json`, `context.json`, `proposal.json`, `inspection.json`, `observations.json`, `context-next.json`, `proposal-next.json`, `next.json`, `events.jsonl`, `report.md`).
6. [`paper/hand_over_manuscript.md`](file:///D:/develop/works/ommatidia/paper/hand_over_manuscript.md):  
   Manuscript handover contract authored concurrently by runtime writer.

*(Note: In accordance with strict ownership boundaries, no code, paper, or reference files were modified by this review agent).*

---

## 2. Benchmark-Ledger Classification & Model Evidence Record

The model selection and task classification were performed strictly read-only against the local benchmark ledger and live capabilities catalogue:

### 2.1 Task Classification
- **Execution Command:**
  ```powershell
  python "<HOME>\.agents\skills\bench-ledger-router\scripts\classify_task.py" "Empirical research design protocol and evaluation specification for Ommatidia"
  ```
- **Raw Output:**
  ```json
  {"kind": "research", "domain": "coding-implement", "requirements": []}
  ```

### 2.2 Candidate Ranking and Selected Model Evidence
- **Execution Command:**
  ```powershell
  python "<HOME>\.agents\skills\bench-ledger-router\scripts\bench_candidates.py" "<saved_capabilities.json>"
  ```
- **Selected Model Record:**
  - **Provider Instance:** `Antigravity`
  - **Vendor:** `google`
  - **Model ID:** `gemini-3.8-flash-high`
  - **Rank:** `13`
  - **Ledger Best Score:** `100.0`
  - **Ledger Best Source:** `measured`
  - **Cost Profile:** `{"input": null, "output": null}` (unmetered by local harness)
  - **Effort Option:** Model-encoded (reported as `['default']` in catalogue because high-reasoning effort is encoded in the model ID).
- **Epistemic Caveat (Mandatory Boundary):**  
  > **Crucial Warning:** The ledger score of 100.0 reflects binary acceptance on prior coding, prompt-contract, and static review benchmarks. **These coding ledger scores are NOT proof of empirical research quality, scientific truth discovery, or multi-perspective reasoning efficacy.** Empirical efficacy must be established independently through the experimental matrix defined in `PROTOCOL.md`. Global ledger remains read-only.

---

## 3. Critical Verification Boundaries & Tombo-View Architecture

Following an exhaustive read-only inspection of `tombo-view` (`SKILL.md`, `references/host-session.md`, `references/runtime.json`, `D:\develop\works\tombo-view\src\types.ts`, and `D:\develop\works\tombo-view\src\fixture.ts`), the following architectural boundaries are strictly established:

### 3.1 The 2-Case Fixture is a Unit Mock, Not Empirical Condition E
1. **Inspection Finding:**  
   `D:\develop\works\tombo-view\src\fixture.ts` contains exactly two hardcoded replay fixtures:
   - `demo-account-close` (`synthetic-account-v1`)
   - `demo-event-resend` (`synthetic-event-v1`)  
   Any input deviating from these two tasks throws a fatal `unsupported_fixture` exception (`TomboError`).
2. **Mandatory Distinction:**  
   - **Mechanism / Unit Fixture Validation:** Using `fixture.ts` and `session.mjs` to confirm that the JSON schema serialization, hash computation, and event ledger transitions function correctly.
   - **Empirical Model Efficacy Evaluation:** Running Condition E across the 48 research cases driven dynamically by `gemini-3.8-flash-high`.
3. **Prohibition Against Conflation:**  
   Condition E must **never** be silently conflated with or substituted by the deterministic 2-case `fixture.ts` replay. Claims of superior performance cannot be derived from a hardcoded mock.

### 3.2 Live TOMBO Audit Verdict
The protocol and paper audit was executed through `scripts/session.mjs` without fixture adapters or extra LLM calls:
- **Verdict:** `判定: 必須の確認が残り、停止している` (`stopReason: capability_limit`).
- **Preserved Essentials:** Unresolved empirical results, full costs, and open-web generalisation remain strictly pending and are not prematurely marked resolved.

---

## 4. Execution Plan, Resource Accounts, and Unknowns

### 4.1 Corrected Run Matrix and Call Counts
- **Held-Out Isolation:** The benchmark comprises 48 total cases, partitioned into 24 Dev and 24 Held-Out cases. Held-out reporting uses $N_{\text{heldout}} = 24$.
- **Phase 1: Dev Pilot (Calibration & Smoke Test):**  
  24 Dev cases $\times$ 5 conditions $\times$ 1 replication = **120 total runs**.  
  - Model Calls: Max $120 \times 8 = 960$ calls.  
  - Tool Invocations: Max $120 \times 12 = 1,440$ calls.
- **Phase 2: Pre-Registered Held-Out Evaluation:**  
  24 Held-Out cases $\times$ 5 conditions $\times$ 1 replication = **120 total runs**.  
  - Model Calls: Max $120 \times 8 = 960$ calls.  
  - Tool Invocations: Max $120 \times 12 = 1,440$ calls.
- **Total Minimum Recommended Execution:** **240 runs** across two isolated phases.
- **Optional Extended Replications:**  
  24 Held-Out cases $\times$ 5 conditions $\times$ 3 replications = **360 runs** (requires separate authorization).
- **Rejected Plan:** The previously drafted 720-run expansion pooling 48 cases $\times$ 5 $\times$ 3 without held-out isolation is rejected.

### 4.2 Measurable Host Metrics vs Unknown Accounting
1. **Host-Measurable Variables:**  
   - Wall-clock elapsed time (ms).
   - Number of model call turns per run.
   - Number of tool call invocations per run.
   - Input character counts.
   - Subprocess return codes, JSON parsing errors, and retry attempts.
2. **Unmetered / Unknown Accounting:**  
   - Exact input/output token counts (if API metadata returns null).
   - Monetary cost in USD or JPY (Antigravity harness does not emit billing data).
3. **Reporting Discipline:**  
   The experiment must refrain from publishing fabricated monetary costs; efficiency must be reported strictly in verifiable physical quantities.

---

## 5. Explicit Directives for the Code Worker

The code worker concurrently developing implementation files should follow these concrete steps:

1. **Benchmark Fixture Construction:**  
   Construct the 48 synthetic benchmark cases according to the taxonomy in `PROTOCOL.md` Section 5:
   - 16 Software Engineering, 16 Workflow Automation, 16 Document Research.
   - 24 Dev and 24 Held-Out cases, with the 4 balanced control classes embedded.
   - Compute and commit the SHA-256 digest of the held-out cases to establish the pre-registration freeze boundary.
   - Strict rule: zero experiment execution or gold creation before freeze!
2. **Condition Runners:**  
   Implement runner scripts for Conditions A, B, C, D, and E matching the schemas and prompts in `EVALUATION_SPEC.md` Section 3 and Section 4.
   - Ensure the total budget envelope (max 8 model calls across all roles, 12 tool calls, 180s timeout) is enforced uniformly.
   - For Condition E, implement a live generation adapter interfacing with `gemini-3.8-flash-high` (do not route to static `fixture.ts`).
3. **Evaluation and Masking Harness:**  
   Implement the scoring engine computing $\text{FDA}$, $\text{Recall}_{\text{crit}}$, $\text{FAR}$, $\text{Prec}_{\text{cand}}$, $\text{DDR}$, $\text{WAR}$, $\text{UAR}$, and $\text{DSC}$ as specified in `EVALUATION_SPEC.md` Section 2.
   - Integrate single-blind / masked assessor evaluation (shuffled UUIDs without condition labels).
   - Implement the statistical tests: case-level paired exact McNemar's test on the 24 held-out cases, Wilson score confidence intervals, and Holm-Bonferroni correction.
   - Ensure automated objective JSON scoring without hidden-answer prompt leakage.
4. **Dev-Only Iteration:**  
   Perform smoke testing and prompt refinement solely on the 24 Dev cases. Do not inspect or execute against the 24 held-out cases until the dev freeze is certified.

---

## 6. Task Gate Compliance & Vendor Disclosures

- **G1 (Hand-over Artifacts):** Complete. Hand-over protocol recorded herein; `paper/hand_over_manuscript.md` verified present.
- **G2 & G3 (Independent Cross-Vendor Verification):**  
  - Independent vendor read failed before process creation (`helper_unknown_error: setup refresh had errors; no findings` on OpenAI/gpt-6-luna/high; Claude rate limited; Cursor startup failed; Grok auto-review rejected; other providers prohibited).
  - Cross-vendor review status explicitly recorded as **NOT_RUN**.
  - A separate-context SAME-vendor review was conducted (`gemini-3.8-flash-high` on agy) and recorded in [`research/review-protocol.md`](file:///D:/develop/works/ommatidia/research/review-protocol.md).
  - Task gate remains **conditionally incomplete / gated** for cross-vendor independence. No cross-vendor success is fabricated.
- **G4 (Budget Adherence):** Total local review cost = $0.00 (read-only local analysis, zero paid API calls invoked).
