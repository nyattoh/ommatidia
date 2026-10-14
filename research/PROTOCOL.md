# Ommatidia Empirical Research Protocol

**Document Version:** 1.0.0  
**Status:** Pre-registration Protocol (Pre-experimental freeze).  
**Language:** British English (as specified by repository standards).  
**Ownership:** Design Sub-agent. (Code implementation and manuscript concurrently owned by code worker).  

---

## 1. Overview and Research Questions

### 1.1 Context
In autonomous AI agent research and complex investigative tasks, agents routinely form premature conclusions because underlying premises, hidden assumptions, temporal validity, and unverified edge conditions remain unexamined. Existing paradigms address this either via monolithic self-reflection (e.g. general re-inspection), static evaluation checklists, or iterative single-agent retrieval. 

**Ommatidia** investigates a compound multi-perspective architecture. It externalises an explicit understanding state (comprising objectives, hypotheses, claims, evidence, unresolved gaps, and candidate lenses), derives focused investigative tasks (exploratory probe roles), executes these against targeted evidence sources, collates the gathered evidence while tracking provenance and scope, and systematically updates the understanding state.

### 1.2 Core Research Question (RQ)
> **Under an identical base model (`gemini-3.8-flash-high`), identical initial materials, identical available tool registries, and an identical total resource budget, does dynamically deriving exploratory roles from an explicit external understanding state significantly improve the discovery of critical evidence and the accuracy of final judgements compared to general re-inspection, fixed static lenses, and sequential single-agent adaptive exploration?**

---

## 2. Operational Hypotheses and Falsification Criteria

Each hypothesis is paired with precise observable metrics and explicit criteria for empirical falsification.

| Hypothesis | Description | Supporting Observation | Falsification / Boundary Criteria |
| :--- | :--- | :--- | :--- |
| **H1: Dynamic Viewpoint Selection** | Dynamically synthesising investigation lenses and gaps tailored to the evolving task state outperforms static, pre-configured checklists. | Identifies mandatory critical evidence items missed by fixed checklists (Condition E vs Condition C; $\Delta \text{Recall}_{\text{crit}} > 0$). | Equivalent detection yield with strictly higher latency and call overhead ($\Delta \text{Recall}_{\text{crit}} \le 0$, $\Delta \text{Cost} > 0$), or generation of irrelevant distractor lenses. |
| **H2: Exploratory Role Decomposition** | Decomposing investigation across modular, focused exploratory probe roles yields more valid evidence from disjoint sources than a monolithic adaptive explorer. | Statistically significant increase in unique, non-redundant evidence from independent source groups (Condition E vs Condition D; $\Delta \text{DSC} > 0$). | Redundant retrieval of identical documents across roles, coordination overhead exceeding yield, or equal disjoint evidence yield ($\Delta \text{DSC} \le 0$). |
| **H3: Structured Evidence Collation** | Systematic cross-referencing, content-hash deduplication, and scope-matching eliminate misjudgements caused by circular citations or entity/temporal conflation. | Significant reduction in false-positive confirmations and erroneous resolutions (Condition E vs Condition D; lower False Alarm Rate $\text{FAR}$). | Excessive rejection of valid evidence (over-filtering) leading to reduced recall ($\text{Recall}_{\text{crit}}$ drops), or failure to detect conflicting sources. |
| **H4: State-Driven Belief Revision** | Incrementally updating the understanding state allows agents to overturn incorrect initial draft answers when decisive counterevidence is observed. | Significantly higher Decision Correction Rate when presented with counterexamples or boundary violations (Condition E vs Condition B). | Decision Degradation: Spurious observations degrading initially correct draft answers into false alarms ($\text{DDR} > 0.05$), or failure to overturn wrong hypotheses. |

---

## 3. Experimental Conditions (A to E)

All conditions operate under the **identical base model** and strict resource ceilings.

```
       [Task Packet & Initial Draft]
                    │
   ┌────────────────┼────────────────┬────────────────┬────────────────┐
   │                │                │                │                │
┌──▼───┐        ┌───▼──┐         ┌───▼──┐         ┌───▼──┐         ┌───▼──┐
│Cond A│        │Cond B│         │Cond C│         │Cond D│         │Cond E│
│Base- │        │Gene- │         │Fixed │         │Single│         │Omma- │
│line  │        │ral Re│         │Lenses│         │Adap- │         │tidia │
│Mono- │        │-ins- │         │Check-│         │tive  │         │Com-  │
│lith  │        │pect  │         │list  │         │State │         │pound │
└──────┘        └──────┘         └──────┘         └──────┘         └──────┘
```

### Condition A: Baseline Exploration (Unguided Monolith)
- **Architecture:** Single-agent direct synthesis.
- **Workflow:** The model receives the task packet and initial draft, is granted access to the tool registry, and proceeds to explore unguided until it issues a final conclusion or exhausts its budget.
- **Role:** Control baseline measuring raw unguided model capability.

### Condition B: General Re-inspection (Self-Reflection Baseline)
- **Architecture:** Two-phase reflective prompting (mimicking standard Reflexion / Self-RAG approaches).
- **Workflow:** 
  1. *Phase 1:* Executes initial retrieval and drafts an assessment.
  2. *Phase 2:* Receives a generalised self-critique prompt instructing it to re-inspect for omissions, overlooked edge cases, counterexamples, and unstated assumptions.
- **Role:** Controls for the effect of simply adding a second inspection turn or extra tokens.

### Condition C: Fixed Viewpoints (Static Checklist Baseline)
- **Architecture:** Static multi-perspective decomposition.
- **Workflow:** The model is evaluated across five fixed, hardcoded investigative lenses:
  1. *Scope & Applicability Boundaries*
  2. *Counterexamples & Negative Scenarios*
  3. *Temporal Validity & Version Divergence*
  4. *Dependency Invariants*
  5. *Source Duplication & Circularity*
- **Role:** Controls for multi-perspective inspection without dynamic state-dependent generation (tests H1).

### Condition D: Single Adaptive Exploration (Sequential State Baseline)
- **Architecture:** Sequential adaptive explorer maintaining an explicit understanding state.
- **Workflow:** The agent maintains an explicit state (claims, gaps, probes), but executes strictly sequentially through a single worker persona. It selects one gap, issues one probe, evaluates the result, updates the state, and iterates until termination.
- **Role:** Controls for the effect of explicit state maintenance without multi-role decomposition or parallelisation (tests H2).

### Condition E: Ommatidia (Full Compound Multi-Lens Architecture)
- **Architecture:** Explicit Understanding State $\to$ Dynamic Lens & Gap Derivation $\to$ Specialised Probe Roles $\to$ Structured Evidence Collation $\to$ State Update & Synthesis.
- **Workflow:**
  1. *State Initialisation:* Extracts claims, assumptions, and initial gaps from the task packet.
  2. *Dynamic Derivation:* Derives candidate lenses and priority gaps based on trigger patterns in the evolving state.
  3. *Role Specialisation:* Constructs focused probe roles (with restricted sub-budgets, target sources, and concrete refutation criteria).
  4. *Targeted Execution:* Up to 3 probe roles execute concurrently.
  5. *Evidence Collation:* Ingests observations, computes SHA-256 hashes, deduplicates identical passages, verifies scope matches, and resolves conflicts.
  6. *State Transition:* Updates claim statuses (`unverified`, `supported`, `contradicted`, `disputed`), retires resolved gaps, and triggers follow-up probes if budget permits.
  7. *Final Resolution:* Generates calibrated judgement and comprehensive audit trail.

---

## 4. Strict Resource Envelope and Budget Ceilings

To eliminate resource confounds, every condition is strictly bound to the following resource envelope:

| Resource Dimension | Upper Ceiling per Case Run | Enforcement Mechanism |
| :--- | :--- | :--- |
| **Base Model** | `gemini-3.8-flash-high` | Fixed provider instance (`Antigravity`, vendor `google`). |
| **Model Invocations** | Max 8 calls | Hard counter terminated by execution wrapper. |
| **Tool Invocations** | Max 12 calls | Hard counter terminated by execution wrapper. |
| **Input Context** | Max 48,000 characters | Truncation / boundary check before dispatch. |
| **Output Tokens** | Max 16,000 tokens (4,000 / call) | Host generation limit parameter. |
| **Wall-Clock Latency** | Max 180 seconds | Async timer abort. |
| **Concurrent Roles** | Max 3 (Condition E only) | Concurrency semaphore (within total budget). |

> **Accounting Rule:** All overheads—planning prompts, investigator tool calls, state serialization, JSON repair retries, synthesis, and coordination messages—are charged against the single unified budget.

---

## 5. Benchmark Dataset: 48 Balanced Synthetic Cases

To prevent contamination and guarantee known ground truth, the evaluation uses **48 purpose-designed synthetic benchmark cases**.

### 5.1 Domain Stratification
- **Domain 1: Software Engineering (SE)** (16 cases)  
  *Scenarios:* API breaking changes, silent configuration deprecation, race conditions under concurrency, dependency version conflicts, semantic regressions in patches.
- **Domain 2: Workflow Automation (WA)** (16 cases)  
  *Scenarios:* Webhook retry idempotency failures, OAuth token expiry edge cases, asynchronous message re-ordering, pagination cursor off-by-one errors.
- **Domain 3: Document & Policy Research (DR)** (16 cases)  
  *Scenarios:* Superseded administrative regulations, contradictory policy clauses across versions, jurisdiction scope mismatches, circular citations between secondary briefs.

### 5.2 Development vs Held-Out Partition
The dataset is split into **24 Development (Dev)** cases and **24 Held-Out** cases (stratified 8 Dev / 8 Held-Out per domain).

```
Total: 48 Cases
 ├── Software Engineering (16) ─── 8 Dev / 8 Held-Out
 ├── Workflow Automation (16)  ─── 8 Dev / 8 Held-Out
 └── Document Research (16)    ─── 8 Dev / 8 Held-Out
```

### 5.3 Balanced Negative Controls
Each domain includes **4 balanced negative control cases** (2 Dev / 2 Held-Out per domain; 12 total across benchmark):
1. **Control Type 1: Sufficient Initial State (No-Op):** Initial draft is already complete and accurate; any additional probe finding "fatal flaws" is penalized as a false alarm.
2. **Control Type 2: Capability Limit / Unresolvable Abstention:** Decisive evidence is intentionally withheld or tools fail; the model must explicitly report `inconclusive` or `capability_limit`.
3. **Control Type 3: Superficially Plausible Distractor:** Contains highly convincing but out-of-scope or outdated distractor evidence contradicting the correct claim.
4. **Control Type 4: Genuine Irresolvable Conflict:** Two authoritative sources directly conflict without an overriding tie-break; requires calibrated verdict `disputed`.

### 5.4 Pre-Registration and Contamination Freeze
- **Freeze Boundary:** The ground-truth answers, mandatory evidence locators, and rubrics for the 24 held-out cases are generated, cryptographically hashed (`SHA-256`), and locked.
- **Zero-Inspection Rule:** Neither human experimenters nor code/design agents may view or evaluate against the held-out answers during system development, prompt refinement, or unit testing.
- **No Result Tuning:** Prompts, threshold parameters, and heuristic rules must be frozen using only the 24 Dev cases before running the final held-out evaluation.

---

## 6. Execution Plan and Host Measurement Boundaries

### 6.1 Call Counts, Held-Out Denominator, and Execution Matrix
To guarantee experimental integrity and avoid unapproved budget expansion, the evaluation enforces a strict held-out denominator ($N_{\text{heldout}} = 24$) and a phased execution matrix.

- **Held-Out Isolation Mandate:** The benchmark comprises 48 total cases, partitioned strictly into 24 Development (Dev) cases and 24 Held-Out cases ($N_{\text{dev}} = 24$, $N_{\text{heldout}} = 24$). Held-out metric reporting must use the held-out denominator $N_{\text{heldout}} = 24$. Development cases must not be pooled into the held-out evaluation denominator.
- **Recommended Minimum Execution Plan:**
  1. **Phase 1: Dev Pilot (Calibration & Smoke Test):** 24 Dev cases $\times$ 5 conditions (A–E) $\times$ 1 replication = **120 runs** (Max 960 model calls, 1,440 tool calls).
  2. **Phase 2: Pre-Registered Held-Out Evaluation:** 24 Held-Out cases $\times$ 5 conditions (A–E) $\times$ 1 replication = **120 runs** (Max 960 model calls, 1,440 tool calls).
- **Separately Authorised Optional Replications:**
  If multi-run stochastic variance characterisation is separately authorised, the 24 held-out cases may be evaluated across 3 replications ($24 \times 5 \times 3 = 360$ runs). The previously proposed unapproved expansion of 720 runs (which pooled all 48 cases across 3 replications without held-out isolation) is explicitly rejected and replaced by the isolated structure below.
- **Strict Pre-Freeze Prohibition:** Zero experiment execution and zero gold label creation may occur prior to the pre-registration freeze boundary.

| Phase | Evaluation Partition | Cases | Conditions | Replications | Total Runs | Max Model Calls | Max Tool Calls | Authorisation Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Phase 1: Dev Pilot** | Calibration (Dev) | 24 | 5 (A–E) | 1 | 120 | 960 | 1,440 | Minimum Recommended Plan |
| **Phase 2: Held-Out Evaluation** | Generalisation (Held-Out) | 24 | 5 (A–E) | 1 | 120 | 960 | 1,440 | Minimum Recommended Plan |
| *Optional: Extended Replications* | Generalisation (Held-Out) | 24 | 5 (A–E) | 3 | 360 | 2,880 | 4,320 | Requires Separate Authorisation |

### 6.2 Host Measurement Boundaries
The experiment environment must explicitly distinguish what the local host harness can measure from unmetered or unknown variables:

```
┌───────────────────────────────────────┬───────────────────────────────────────┐
│     Directly Measurable by Host       │         Unmetered / Unknown           │
├───────────────────────────────────────┼───────────────────────────────────────┤
│ • Wall-clock execution time (ms)      │ • Exact token count (if API returns   │
│ • Exact count of model call turns     │   null usage metadata)                │
│ • Exact count of tool executions      │ • Monetary expenditure (USD / JPY)    │
│ • Input prompt string character length│   (if provider subscription / local   │
│ • Tool error and JSON repair retries  │   harness does not report billing)    │
│ • Process exit codes and schema errors│ • Proprietary hidden model states     │
└───────────────────────────────────────┴───────────────────────────────────────┘
```

> **Reporting Mandate:** Because the live Antigravity harness reports `cost.output: null` for `gemini-3.8-flash-high`, no speculative monetary cost comparisons shall be asserted. All efficiency comparisons shall be reported strictly in verifiable physical units: **elapsed wall-clock milliseconds**, **total model turns**, **total tool invocations**, and **input characters**.

---

## 7. Crucial Distinction: Mechanism Unit Validation vs Empirical Model Efficacy

1. **Mechanism / Unit Fixture Validation:**  
   The `tombo-view` SDK includes a deterministic unit test fixture (`fixture.ts`) featuring two fixed demo cases (`demo-account-close` and `demo-event-resend`). This fixture validates the JSON schema serialization, hash calculation, event ledger recording, and state-machine transitions of `session.mjs`. It is a static, mock replay mechanism.
2. **Empirical Model Efficacy Evaluation:**  
   Condition E is **NOT** the static `fixture.ts` demo. Condition E represents the live, multi-turn execution of Ommatidia driven by `gemini-3.8-flash-high` across the 48 benchmark cases.
3. **Guard Against Conflation:**  
   Under no circumstances shall the deterministic replay success of the 2-case `fixture.ts` be presented as evidence of model reasoning superiority or empirical research validation. The experimental framework must verify the execution harness via unit tests, but measure research claims solely against live experimental runs.
