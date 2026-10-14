# Ommatidia Objective Evaluation Specification

**Document Version:** 1.0.0  
**Status:** Pre-registration Freeze.  
**Language:** British English.  
**Ownership:** Design Sub-agent.  

---

## 1. Overview and Core Philosophy

This specification defines the exact, automated, and objective scoring procedures for comparing experimental Conditions A to E across the 48 pre-registered benchmark cases. 

To ensure complete empirical integrity and reproducibility:
1. **Mathematical Objectivity:** All metrics are formulated without subjective human rating scales.
2. **Strict Masked Assessor Evaluation:** Evaluation scripts and human auditors evaluate outputs with condition labels anonymised (single-blind / masked assessor evaluation). Autonomous agents receive condition prompts as operational instructions and therefore cannot be blinded to their own condition.
3. **Paired Statistical Rigour:** All comparisons are executed on matched case pairs, accounting for stochastic variance and multi-hypothesis family-wise error rates.
4. **Distinction Between Abstention Types:** Warranted abstention on capability limits is rewarded; unwarranted abstention on solvable problems is penalised.

---

## 2. Mathematical Metric Definitions and Held-Out Isolation

Let $N_{\text{heldout}} = 24$ be the number of pre-registered held-out benchmark test cases. The $N_{\text{dev}} = 24$ development cases are strictly reserved for smoke testing, prompt calibration, and dev-freeze verification; they are excluded from the held-out evaluation denominator.

> **Trial Independence & Clustering Notice:** Multiple runs on the same case are clustered observations, **not independent statistical sampling units**. The primary pre-registered benchmark plan evaluates $R = 1$ run per case across all conditions ($N_{\text{heldout}} = 24$). When optional multi-run replications ($R > 1$) are authorised, case-level aggregation (mode consensus verdict or case-level mean) is performed prior to hypothesis testing to preserve case-level exchangeability.

For a given condition $C \in \{A, B, C, D, E\}$ and case $i \in \{1, \dots, N_{\text{heldout}}\}$, let $y_i^{(C)}$ denote the agent output on the primary evaluation run.

### 2.1 Primary Metric 1: Final Decision Accuracy ($\text{FDA}$)
Each case has a ground-truth verdict:
$$V_i^* \in \{\text{supported}, \text{contradicted}, \text{disputed}, \text{inconclusive}\}$$

The agent's synthesized decision is mapped to $V(y_i^{(C)})$. The accuracy indicator is defined as:
$$\mathbb{I}_{\text{FDA}}(i, C) = \begin{cases} 1 & \text{if } V(y_i^{(C)}) = V_i^* \\ 0 & \text{otherwise} \end{cases}$$

The overall Final Decision Accuracy on the held-out set is:
$$\text{FDA}(C) = \frac{1}{N_{\text{heldout}}} \sum_{i=1}^{N_{\text{heldout}}} \mathbb{I}_{\text{FDA}}(i, C)$$

### 2.2 Primary Metric 2: Critical Item Recall ($\text{Recall}_{\text{crit}}$)
Each case $i$ defines a non-empty set of mandatory critical evidence items $\mathcal{M}_i = \{m_{i, 1}, \dots, m_{i, k_i}\}$ (e.g. specific contractual clauses, bug-inducing commits, or conflicting specifications) required to justify the verdict. Let $\widehat{\mathcal{M}}_i^{(C)}$ be the set of verified evidence locators correctly retrieved and cited by condition $C$.

$$\text{Recall}_{\text{crit}}(i, C) = \frac{|\mathcal{M}_i \cap \widehat{\mathcal{M}}_i^{(C)}|}{|\mathcal{M}_i|}$$

The mean Critical Item Recall across the held-out set is:
$$\text{Recall}_{\text{crit}}(C) = \frac{1}{N_{\text{heldout}}} \sum_{i=1}^{N_{\text{heldout}}} \text{Recall}_{\text{crit}}(i, C)$$

---

### 2.3 Secondary Metric 1: False Alarm Rate ($\text{FAR}$)
Let $\mathcal{P}_{i, r}^{(C)}$ be the set of candidate investigation probes generated during the run. Let $\mathcal{P}_{\text{spurious}}$ be the subset of probes that target non-existent contradictions, hallucinations, or out-of-scope issues.

$$\text{FAR}(i, r, C) = \begin{cases} \frac{|\mathcal{P}_{\text{spurious}}|}{|\mathcal{P}_{i, r}^{(C)}|} & \text{if } |\mathcal{P}_{i, r}^{(C)}| > 0 \\ 0 & \text{otherwise} \end{cases}$$

### 2.4 Secondary Metric 2: Candidate Precision ($\text{Prec}_{\text{cand}}$)
Measures the proportion of generated candidate gaps that correspond to genuine, verified evidentiary gaps:

$$\text{Prec}_{\text{cand}}(C) = \frac{\sum_{i, r} |\text{Valid Gaps Identified}|}{\sum_{i, r} |\text{Total Candidate Gaps Generated}|}$$

### 2.5 Secondary Metric 3: Decision Degradation Rate ($\text{DDR}$)
Evaluated specifically on cases where the initial draft answer was already correct ($V_{\text{initial}} = V_i^*$):

$$\text{DDR}(C) = \frac{\sum_{i \in \text{InitialCorrect}} \sum_{r} \mathbb{I}\left(V(y_{i, r}^{(C)}) \ne V_i^*\right)}{R \cdot |\text{InitialCorrect}|}$$
A high $\text{DDR}$ indicates that the system's re-investigation introduced confusion or accepted spurious distractors.

### 2.6 Secondary Metric 4: Warranted vs Unwarranted Abstention Rate
Cases are partitioned into solvable cases ($\mathcal{S}$) and unresolvable/control cases ($\mathcal{U}$, where ground truth is `inconclusive` due to missing data or capability limits).

- **Warranted Abstention Rate ($\text{WAR}$):**
  $$\text{WAR}(C) = \frac{1}{R \cdot |\mathcal{U}|} \sum_{i \in \mathcal{U}} \sum_{r} \mathbb{I}\left(V(y_{i, r}^{(C)}) = \text{inconclusive}\right)$$
  *(Target: 1.0)*

- **Unwarranted Abstention Rate ($\text{UAR}$):**
  $$\text{UAR}(C) = \frac{1}{R \cdot |\mathcal{S}|} \sum_{i \in \mathcal{S}} \sum_{r} \mathbb{I}\left(V(y_{i, r}^{(C)}) = \text{inconclusive}\right)$$
  *(Target: 0.0)*

### 2.7 Secondary Metric 5: Disjoint Source Coverage ($\text{DSC}$)
Let $\mathcal{S}_{i, r}^{(C)}$ be the set of unique, disjoint source groups (e.g. separate repositories, distinct document folders, independent service logs) successfully accessed and verified:

$$\text{DSC}(i, r, C) = |\text{Unique Source Groups Sampled}|$$

### 2.8 Efficiency Ratios (Based on Observable Host Metrics)
Because monetary costs are unknown in the host environment, efficiency is quantified through physical execution observables:
1. **Critical Yield per Tool Call:** $\eta_{\text{tool}} = \frac{\sum |\mathcal{M}_i \cap \widehat{\mathcal{M}}_{i, r}^{(C)}|}{\text{Total Tool Calls}}$
2. **Critical Yield per Second:** $\eta_{\text{time}} = \frac{\sum |\mathcal{M}_i \cap \widehat{\mathcal{M}}_{i, r}^{(C)}|}{\text{Total Elapsed Time (seconds)}}$

---

## 3. Standardised Input and Output Schemas

Every condition consumes the identical `TaskPacket` input and emits a conformant `FinalJudgement` JSON structure.

### 3.1 Input Schema: `TaskPacket`
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "TaskPacket",
  "type": "object",
  "required": ["taskId", "domain", "goal", "proposedAnswer", "availableSources", "budget"],
  "properties": {
    "taskId": { "type": "string" },
    "domain": { "enum": ["software_engineering", "workflow_automation", "document_research"] },
    "goal": { "type": "string" },
    "proposedAnswer": { "type": "string" },
    "availableSources": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["sourceGroup", "description", "entryLocator"],
        "properties": {
          "sourceGroup": { "type": "string" },
          "description": { "type": "string" },
          "entryLocator": { "type": "string" }
        }
      }
    },
    "budget": {
      "type": "object",
      "required": ["maxModelCalls", "maxToolCalls", "maxElapsedMs", "maxInputChars"],
      "properties": {
        "maxModelCalls": { "type": "integer", "const": 8 },
        "maxToolCalls": { "type": "integer", "const": 12 },
        "maxElapsedMs": { "type": "integer", "const": 180000 },
        "maxInputChars": { "type": "integer", "const": 48000 }
      }
    }
  }
}
```

### 3.2 Output Schema: `FinalJudgement`
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "FinalJudgement",
  "type": "object",
  "required": ["taskId", "verdict", "confidenceScore", "justification", "citedEvidence", "unresolvedGaps", "resourceUsage"],
  "properties": {
    "taskId": { "type": "string" },
    "verdict": { "enum": ["supported", "contradicted", "disputed", "inconclusive"] },
    "confidenceScore": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
    "justification": { "type": "string" },
    "citedEvidence": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "sourceGroup", "locator", "contentHash", "passage", "verdictRelation"],
        "properties": {
          "id": { "type": "string" },
          "sourceGroup": { "type": "string" },
          "locator": { "type": "string" },
          "contentHash": { "type": "string", "pattern": "^[a-f0-9]{64}$" },
          "passage": { "type": "string" },
          "verdictRelation": { "enum": ["supports", "refutes", "context"] }
        }
      }
    },
    "unresolvedGaps": {
      "type": "array",
      "items": { "type": "string" }
    },
    "resourceUsage": {
      "type": "object",
      "required": ["modelCalls", "toolCalls", "elapsedMs", "inputCharsEstimated"],
      "properties": {
        "modelCalls": { "type": "integer" },
        "toolCalls": { "type": "integer" },
        "elapsedMs": { "type": "number" },
        "inputCharsEstimated": { "type": "integer" }
      }
    }
  }
}
```

---

## 4. Prompt Specifications Across Conditions A to E

To guarantee fair benchmarking, all conditions receive standardized system prompts.

### 4.1 Condition A Prompt (Baseline Direct Explorer)
```text
You are an autonomous research agent evaluating a proposed answer.
You have access to local file inspection tools.
Investigate the provided sources, verify the proposed answer, and output your final verdict.
You must return your output strictly in the FinalJudgement JSON schema.
Total budget: maximum 8 model calls and 12 tool calls.
```

### 4.2 Condition B Prompt (General Re-inspection / Self-Reflection)
- **Phase 1 (Initial Probe):** Standard exploration prompt identical to Condition A.
- **Phase 2 (Reflection & Re-inspection Prompt):**
```text
Review your initial investigation. Re-examine your assumptions critically:
1. Did you miss any fatal counterexamples or negative edge cases?
2. Are the retrieved sources current, or could newer versions supersede them?
3. Did you conflate similar entities or extrapolate beyond the stated scope?
Conduct any necessary follow-up tool calls, then provide the final updated FinalJudgement JSON.
```

### 4.3 Condition C Prompt (Fixed Viewpoints Checklist)
```text
You are an investigative agent using 5 mandatory analytical lenses:
1. [L-SCOPE] Scope and applicability boundaries.
2. [L-COUNTER] Negative scenarios and edge-case counterexamples.
3. [L-TEMPORAL] Temporal validity and version divergence.
4. [L-DEPEND] Underlying dependency invariants.
5. [L-REDUNDANT] Circular citations and source duplication.
Systematically probe each of these five lenses up to your available budget.
Synthesise your findings into the FinalJudgement JSON schema.
```

### 4.4 Condition D Prompt (Single Adaptive State Explorer)
```text
You maintain an explicit investigative understanding state.
At each step:
1. Examine open gaps and unverified claims.
2. Select the single most critical gap.
3. Formulate a targeted probe and execute the necessary tool call.
4. Record your observation and update the state.
Repeat until all critical gaps are resolved or your budget is exhausted.
Emit your FinalJudgement JSON schema.
```

### 4.5 Condition E Prompts (Ommatidia Multi-Role Compound)
1. **Coordinator / Gap Synthesiser Prompt:**
   Takes current task packet and active understanding state, identifies unverified claims, synthesises dynamic candidate lenses, and generates prioritised probe specifications (`ProbeDefinition`).
2. **Specialised Probe Role Prompt:**
   Dispatched to execute a specific probe with assigned sources and strict refutation criteria. Output restricted to verified observations and content hashes.
3. **Collation & State Transition Engine:**
   Ingests raw observations, performs SHA-256 deduplication and entity matching, checks scope boundaries, resolves contradictory findings, and updates claim statuses.
4. **Final Synthesiser Prompt:**
   Produces the final `FinalJudgement` JSON from the fully updated, collated understanding state.

---

## 5. Statistical Analysis and Uncertainty Framework

### 5.1 Case-Level Unit Independence and Aggregation
In repeated trials, multiple stochastic generations for the same case $i$ are clustered observations and do not represent independent statistical units. To prevent pseudo-replication:
- **Primary Pre-Registered Analysis:** Executed on the primary evaluation run per case across all $N_{\text{heldout}} = 24$ held-out cases ($R = 1$).
- **Secondary Replicated Analysis:** If optional replications ($R = 3$) are separately authorised, trials are aggregated at the case level (majority voting for binary decisions $V(y_i^{(C)})$ and arithmetic mean for continuous metrics) before computing paired inferential statistics across cases.

### 5.2 Hypothesis Testing Protocol (Case-Level Paired Analysis)
To test the pre-registered hypotheses H1–H4, statistical tests are conducted strictly on matched case pairs ($N_{\text{heldout}} = 24$). Because repeated trials within the same case are clustered, pooled test statistics are avoided.

- **Primary Statistical Test for Binary Outcomes:** **Paired binary exact McNemar's test** on matched case pairs ($N_{\text{heldout}} = 24$).
- **Primary Proportion Uncertainty:** **Wilson score 95% confidence intervals** (with continuity correction).
- **Secondary / Exploratory Tests:** Non-parametric **BCa bootstrap confidence intervals** ($B = 10,000$ resamples) and **paired Wilcoxon signed-rank tests** are treated strictly as secondary indicators on continuous difference distributions ($\Delta \text{Recall}_{\text{crit}}$, $\Delta \text{DSC}$, $\Delta \text{FAR}$).

| Target Hypothesis | Comparison Pair | Primary Statistical Test | Secondary / Exploratory Indicator |
| :--- | :--- | :--- | :--- |
| **H1 (Dynamic Lenses)** | Condition E vs Condition C | Exact McNemar's Test on $\text{FDA}$ ($N_{\text{heldout}}=24$) | Paired Wilcoxon Signed-Rank on $\text{Recall}_{\text{crit}}$ |
| **H2 (Role Decomposition)** | Condition E vs Condition D | Paired Wilcoxon on Case-Level $\text{DSC}$ ($N_{\text{heldout}}=24$) | BCa Bootstrap 95% CI on $\Delta \text{DSC}$ |
| **H3 (Evidence Collation)** | Condition E vs Condition D | Paired Wilcoxon on Case-Level $\text{FAR}$ ($N_{\text{heldout}}=24$) | Exact McNemar's Test on Spurious Acceptance |
| **H4 (Belief Revision)** | Condition E vs Condition B | Exact McNemar's Test on Counterexample cases | Paired comparison of Case-Level $\text{DDR}$ |

**Fixed before any held-out run (decided 2026-10-15; no held-out case exists yet):**

1. **Wilcoxon zero differences and ties.** Pairs whose difference is exactly zero are excluded. Tied absolute differences receive average ranks, and the normal approximation without continuity correction is used. If fewer than 6 non-zero pairs remain, the test is reported as not computable and the hypothesis as *inconclusive*.
2. **H4 denominator.** H4 uses exactly 12 held-out cases tagged as counterexample cases (half of the 24 held-out cases). The tag set is written when the held-out cases are authored and is frozen before any run. Rationale: with Holm-adjusted $\alpha = 0.0125$, the exact McNemar test needs at least 8 discordant pairs in one direction. A subset of 8 would force every case to be discordant; 12 leaves room for 4 concordant cases.

### 5.3 Uncertainty Quantification
1. **Binomial Proportions ($\text{FDA}$):** Wilson score 95% confidence intervals with continuity correction.
2. **Continuous Differences ($\Delta \text{Recall}$, $\Delta \text{FAR}$, $\Delta \text{Latency}$):** 95% Confidence Intervals computed via non-parametric BCa bootstrap with $B = 10,000$ resamples (pre-declared secondary analysis).
3. **Multiplicity Correction:** To control Family-Wise Error Rate ($\text{FWER}$) at $\alpha = 0.05$ across the 4 primary hypotheses, $p$-values are adjusted using the **Holm-Bonferroni step-down procedure**.

---

## 6. Pre-Registration Freeze and Evaluation Blinding

1. **Cryptographic Sealing:**  
   The held-out case answer key and evaluation harness are archived with their SHA-256 digests committed to the repository before experimental runs commence.
2. **Single-Blind / Masked Assessor Evaluation:**  
   Autonomous agents observe condition prompts as operational directives and cannot be blinded to condition. Blinding applies strictly to downstream evaluation scripts and human assessors, who receive output files with shuffled UUIDs (e.g. `run_9f2a7b...json`) without condition identifiers (A–E). The unscrambling key is held separately and merged only after metric computation is complete.
3. **Prohibition of Held-Out Optimization:**  
   Any test run executed against held-out cases with unsealed prompts immediately invalidates the pre-registration status.
4. **Objective Automated JSON Scoring Without Leakage:**  
   All evaluation metrics ($\text{FDA}$, $\text{Recall}_{\text{crit}}$, $\text{FAR}$) are scored programmatically by exact JSON property comparison and cryptographic hash matching against pre-registered ground truth. At no point are hidden answers, ground truth locators, or secret rubrics injected into model prompts or evaluator prompts.
