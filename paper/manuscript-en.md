# Ommatidia: Design and Evaluation Plan for Understanding-State-Based Compound-Eye Investigation

**Status**: Manuscript draft (proposal and protocol design stage). Experiments have not been conducted (Pending). Empirical results are awaited and have not yet been obtained.

- **Author**: Ryoko Sakakibara (Independent Researcher)
- **ORCID**: [0009-0009-9544-6315](https://orcid.org/0009-0009-9544-6315)
- **Manuscript licence**: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- **DOI**: Not yet assigned. A DOI will be assigned upon registration with Zenodo.
- **Source for checking author information**: [Zenodo record 22925518](https://zenodo.org/records/22925518)

---

## Abstract

What can remain unchecked behind a confident answer? Premature closure—reaching confident conclusions while leaving unverified premises and critical counterexamples unexamined—is one of the most serious pitfalls facing LLM-powered investigation agents. How can an autonomous agent systematically stress-test its own emerging explanations? Inspired by the multifaceted vision of insect compound eyes, this paper presents the design of **Ommatidia**. Rather than burying beliefs inside ephemeral context windows, Ommatidia anchors investigation around an explicit, external **Understanding State**—a structured ledger recording goals, claims, hypotheses, evidence, unverified gaps, and inspection history. From this state, the system dynamically constructs concrete, testable **Investigators** targeted at unresolved assumptions, rigorously reconciling evidence without mistaking duplicate text for independent confirmation, preserving real-world contradictions, and enforcing termination under a strict composite budget of calls, tools, tokens, characters, and time.

We analyze the architectural mechanisms distinguishing Ommatidia from four foundational paradigms (Self-RAG, Adaptive-RAG, STORM, and Reflexion) and establish a rigorous, preregistered experimental protocol. The benchmark spans five conditions across 24 development and 24 evaluation cases (240 total trials), capped at 8 calls per trial (1,920 maximum model calls). At present, empirical trials stand at zero, and costs and token consumption remain unmeasured; in accordance with protocol boundaries and a targeted four-paper review, no claim of novelty or empirical superiority is asserted. The design stands complete, its hypotheses preregistered, awaiting execution under controlled experimental audit.

---

## 1. Introduction

In information investigation systems that combine large language models (LLMs) with external search and tools, reliance on a single generation path makes it difficult to track the assumptions underlying an answer and the counterexamples or exclusion conditions that may have been overlooked. In human investigative work, a hypothesis is followed by deliberate identification of the boundary conditions under which it would fail—counterexamples, mismatches in the target, information freshness and the reliability of primary sources—and focused further investigation.

The working hypothesis of this study is that a mechanism which defines new investigation tasks in response to unverified items identified during an investigation and reconciles evidence from different sources will reduce errors in final judgements. This hypothesis has not been tested at the time of writing.

To address this hypothesis, this study proposes a design termed Compound-eye Investigation. The name derives from the compound eyes of insects, which consist of multiple ommatidia. The system maintains its own Understanding State as data, initiates investigators to resolve unverified items in the current explanation, and updates the state by reconciling evidence.

### 1.1 Operational Definitions

The main concepts used in this study are operationally defined as follows.

1. **Understanding State**:
   An External Structured Ledger that explicitly stores the investigation's Goal, current Claims, Hypotheses to be tested, acquired Evidence, Unverified Items and Inspection History. It does not denote the model's internal reasoning or subjective consciousness.
2. **Investigator**:
   A concrete, testable task specification defining a particular unverified item, a hypothesis to be tested, a target collection of materials, available tools, decision criteria (support/contradiction/unknown) and limits on input, output and computational resources. It is not an anthropomorphic persona with a personality or character.
3. **Unverified Item**:
   A prerequisite or potential counterexample that affects the validity of a current claim and has not yet been supported or contradicted by direct evidence.
4. **Evidence Reconciliation**:
   A procedure that checks the provenance, target entity, investigation time and applicability conditions of acquired evidence, removes duplicate text and retains unexplained conflicts as contradictions.
5. **Stopping Condition**:
   A rule that ends the investigation when all essential unverified items have been resolved, further investigation no longer changes the state (stagnation), the total budget limit has been reached, or the necessary investigative capabilities are unavailable, while explicitly recording why any items remain unverified.

### 1.2 Research Questions

Based on the [research protocol (PROTOCOL.md)](../research/PROTOCOL.md), this study will examine the following research questions (RQs) using the same base model (fixed in the protocol as `gemini-3.8-flash-high`), initial materials, tools and total budget. The primary comparisons for each RQ follow the mapping in §5.2 of the [evaluation specification (EVALUATION_SPEC.md)](../research/EVALUATION_SPEC.md).

- **Main question**: Under the same resource budget, does dynamically constructing investigators from the Understanding State improve the discovery rate of critical evidence and the accuracy of final judgements compared with general re-inspection, fixed viewpoints and single adaptive exploration?
- **RQ1 (Effect of dynamic viewpoint selection, H1)**: Does selecting viewpoints in response to evidence and the Understanding State during investigation (Condition E) increase the detection of essential items that determine the conclusion and the number of correct final judgements compared with viewpoints fixed in advance (Condition C)?
- **RQ2 (Effect of dividing work among investigators, H2)**: Does dividing work among multiple investigators (Condition E) increase valid evidence from non-duplicate source groups compared with single adaptive exploration (Condition D)?
- **RQ3 (Effect of evidence reconciliation, H3)**: Does checking provenance and applicability conditions (Condition E) reduce erroneous checks (false alarms) compared with Condition D, without excessively rejecting valid evidence?
- **RQ4 (Effect of state updates, H4)**: Does progressively incorporating investigation results into structured data (Condition E) enable correction of initially erroneous conclusions in cases containing counterexamples compared with general re-inspection (Condition B)?

---

## 2. Related Work

This section is based on an examination of the official versions of Self-RAG, Adaptive-RAG, STORM and Reflexion (ICLR proceedings, ACL Anthology and NeurIPS proceedings). The bracketed identifiers following individual statements are claim IDs in the [verification ledger](../references/verification-ledger.json), which records the relevant passages and excerpts from the originals. Statements marked as 'inference' reflect this paper's reading that a feature is not described in the sections examined; they are not exhaustive claims of absence. Details are recorded in the [related-work ledger](../references/RELATED_WORK.md).

### 2.1 Self-checking RAG: Self-RAG

Self-RAG (Asai et al., 2024) adds 4 types of reflection token (Retrieve, IsRel, IsSup and IsUse) to the generator's vocabulary and trains the generator on data containing tokens assigned offline by a critic model [selfrag-1, selfrag-2]. At inference time, it performs beam search with 1 sentence per segment and selects candidates using a weighted linear sum of reflection-token probabilities [selfrag-3, selfrag-4]. The authors note that outputs insufficiently supported by citations may remain [selfrag-5].

- **Difference from this proposal**: Self-RAG requires training the generator (Llama2 7B/13B), so it cannot be applied directly to hosted models whose weights cannot be trained (inference, selfrag-6). Reflection tokens provide segment-level judgements, and §§3.1–3.3 of the paper do not describe an external record of claims or unverified items for the task as a whole (inference, selfrag-7).

### 2.2 Adaptive Retrieval Routing: Adaptive-RAG

Adaptive-RAG (Jeong et al., 2024) uses a T5-Large classifier to assign a question to 1 of 3 complexity levels before answering begins, selecting no retrieval, single-step retrieval or multi-step retrieval [adaptiverag-1, adaptiverag-3]. In the multi-step strategy, retrieval at each step takes a context containing earlier documents and intermediate answers as input, so later retrieval changes in response to earlier results [adaptiverag-2]. Training labels for the classifier are generated automatically, and the authors acknowledge both the possibility of incorrect labels and a performance gap relative to an ideal classifier [adaptiverag-4].

- **Difference from this proposal**: Strategy selection occurs for each question before answering, while retrieval adapts within the multi-step strategy. Adaptive-RAG therefore cannot be described as lacking dynamic adaptation. However, it does not describe procedures for switching strategies in response to contradictions in acquired evidence or for grouping retrieved documents by their primary provenance (inference, adaptiverag-5, adaptiverag-6). Ommatidia differs in design by constructing the next investigator from unverified items recorded during the investigation.

### 2.3 Long-form Article Generation through Multi-perspective Conversations: STORM

STORM (Shao et al., 2024) generates a set of perspectives from the tables of contents of Wikipedia articles on related topics. For each perspective, a writer role and a retrieval-based expert role engage in a multi-turn conversation for up to $M$ rounds [storm-1, storm-2, storm-3]. The writer's follow-up questions change according to the conversation history [storm-3]. The expert role applies a rule-based filter aligned with Wikipedia guidelines to search results, excluding unreliable sources [storm-4]. The implementation uses zero-shot prompts and does not train the model [storm-7]. The authors identify bias towards dominant sources and the possible inclusion of promotional content among the limitations of the collected information [storm-5].

- **Difference from this proposal**: STORM aims to write explanatory articles rather than determine whether claims hold. Its set of perspectives is determined before the conversations, while follow-up questions adapt within each conversation. The rule-based filter addresses source reliability; no procedure is described for grouping republications of the same original article (inference, storm-6).

### 2.4 Verbal Reinforcement Learning and Reflective Memory: Reflexion

Reflexion (Shinn et al., 2023) consists of 3 models: Actor, Evaluator and Self-Reflection. The self-reflection model generates natural-language feedback from trajectories and binary or scalar signals produced by the evaluator, stores it in memory with a limit typically ranging from 1 to 3 entries, and passes it to the next trial [reflexion-1, reflexion-2, reflexion-5]. Model weights are not updated [reflexion-8]. Evaluation signals in the experiments comprise exact-match scoring, predefined heuristics, LLM classification and self-written unit tests [reflexion-4]. The framework itself can accommodate both scalar and free-form verbal feedback [reflexion-3]. The authors identify reliance on self-evaluation, the absence of formal guarantees of success and the possibility of local optima as limitations [reflexion-6].

- **Difference from this proposal**: Reflexion generates reflections between trials in response to evaluator signals. These signals are not limited to external ground truth; they also include self-written tests and LLM judgements. Ommatidia is designed to update a record of unverified items within a single trial. A structured record linking claims to evidence and provenance is not described in the paper (inference, reflexion-7).

### 2.5 Technical Comparison and the Design Boundaries of Ommatidia

The table below summarises §§2.1–2.4. 'Not described' refers to the statements marked as inferences. The Ommatidia column describes the design in [PROTOCOL.md](../research/PROTOCOL.md); its effectiveness has not been tested.

| Comparison item | Self-RAG | Adaptive-RAG | STORM | Reflexion | Ommatidia (design, untested) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Purpose** | Retrieval, generation and self-critique in 1 model | Selection of retrieval strategy according to question complexity | Preliminary research and writing for Wikipedia-style articles | Improvement of actions through repeated trials | Investigation to determine whether claims hold |
| **Location of state** | Generation context and reflection tokens | Retrieval context (documents and intermediate answers) | Conversation history and reference set for each perspective | Memory of reflections (typically 1 to 3 entries) | External Understanding State |
| **When viewpoints or roles are determined** | Single model | For each question, before answering | A set of perspectives is generated before conversations begin | Fixed configuration of 3 models | Generated from unverified items during investigation |
| **Adaptation during the process** | Segment-level decisions on whether retrieval is needed | Retrieval context updated within the multi-step strategy | Follow-up questions within conversations | Verbal reflection between trials | Selection of the next investigator after updating the Understanding State |
| **Treatment of provenance** | Assessment of support using IsSup | Not described | Rule-based reliability filter; grouping of republications is not described | Not described | Deduplication of identical text using text hashes, and scope checks |
| **Training requirements** | Generator and critic models are trained | Classifier (T5-Large) is trained | No training | No weight updates | No training |

This proposal does not claim that LLMs autonomously acquire new concepts. It is a system design centred on an externalised Understanding State: investigators are assigned to contradict or qualify current claims, evidence is reconciled after duplicate text is removed, and investigation stops within a composite budget. The differences in the table are design differences. This paper claims neither that this combination is absent from prior work nor that the design is effective.

---

## 3. Proposed Method: Ommatidia

Ommatidia comprises a component that manages the externalised Understanding State, a component that dynamically constructs investigators, a component that reconciles acquired evidence, and a component that updates the state and determines when to stop.

### 3.1 Understanding State Data Structure

The Understanding State $S$ is defined as an external, verifiable data structure independent of the model's internal representations.

$$S = \langle G, C, H, E, U, I \rangle$$

- $G$ (Goals): The purpose of the investigation and the central question to be resolved.
- $C$ (Claims): The set of claims currently derived. Each claim is linked to references to supporting evidence rather than a degree of confidence.
- $H$ (Hypotheses): Working hypotheses formulated to test, qualify or contradict claims.
- $E$ (Evidence Ledger): A ledger of acquired evidence. Each item includes a text excerpt, source location, retrieval date and time, target entity, applicability conditions, provenance type and SHA-256 hash of the text.
- $U$ (Unverified Items): The set of unverified items that affect the validity of claims. Each item records the specific trigger that gave rise to it and why it affects the goal.
- $I$ (Inspection History): A history of the checks and investigators executed (submitted prompts, tools used and resources consumed).

In accordance with the protocol terminology, claims have 4 states: unverified (`unverified`), supported (`supported`), contradicted (`contradicted`) and disputed (`disputed`). Final judgements use 4 values, with inconclusive (`inconclusive`) as the additional outcome: `supported`, `contradicted`, `disputed` or `inconclusive`. A lack of search results or an unavailable tool must not be reinterpreted as contradiction or resolution.

### 3.2 Dynamic Investigator Dispatch

Investigators are generated as explicit inspection specifications rather than anthropomorphic personas. Given the current Understanding State $S$ and an unverified item $u \in U$ within it, an investigator $r_u$ is defined with the following attributes.

1. **Target unverified item**: The specific question to be checked.
2. **Hypothesis to be tested**: Conditions under which the claim would not hold, or prerequisites for it to hold.
3. **Target materials and tools**: Search keywords, documents to consult and permitted tools (such as search and file reading).
4. **Decision criteria**: Specific criteria distinguishing support, contradiction and unknown status.
5. **Resource limits**: The maximum number of calls, maximum number of input characters and timeout allocated to the investigator.

Multiple investigators are not initiated when a single investigator is sufficient. At most 3 investigators may run concurrently, and execution must remain within the total budget.

### 3.3 Evidence Reconciliation and Resolution of Provenance Dependencies

When investigators report evidence, its validity is not judged solely by search ranking or superficial similarity of wording. The following reconciliation procedures are applied.

- **Deduplication of identical text**: Excerpts with matching SHA-256 text hashes count as 1 item of evidence even if retrieved by multiple investigators. Grouping republications of the same primary source into 1 item, including paraphrased versions, is a design objective, but the procedure specified by the protocol is limited to deduplicating identical text (limitation 5 in §7).
- **Consistency of conditions and timing**: The prerequisites under which the evidence holds, the version of the target under investigation and the publication date are checked to establish whether their scope matches the current claim.
- **Explicit retention of conflicts**: When reliable sources contradict one another, the conflict is retained in the Understanding State as disputed (`disputed`), rather than selecting one source and treating the matter as resolved.

### 3.4 State Updates and Stopping Rules

The Understanding State $S$ is updated from investigator outputs. Investigation stops when any of the following conditions is met.

1. **Resolution of essential items**: All unverified items essential to the investigation's goal have been checked and either supported or contradicted.
2. **Evidence and state stagnation**: Further investigation yields no new evidence and the Understanding State no longer changes.
3. **Budget exhaustion**: Any limit on model calls, tool calls, input characters, output tokens or elapsed time has been reached.
4. **Insufficient capabilities**: Further investigation is structurally impossible, for example because a required verification tool is unavailable.

At the end of the investigation, the final output must record all remaining unverified items and the reasons they remain unresolved, such as budget limits or the absence of sources.

---

## 4. Experimental Protocol

This plan follows [PROTOCOL.md](../research/PROTOCOL.md) and [EVALUATION_SPEC.md](../research/EVALUATION_SPEC.md). Settings and ground-truth rules will be fixed before viewing evaluation data to prevent adaptation to those data.

### 4.1 Comparison Conditions

The following 5 conditions will be compared using the same base model, tool environment and total resource budget limits.

- **Condition A (Baseline Exploration)**: A single agent receives the task materials and an initial draft answer, investigates with tools without additional guidance, and continues until it reaches a conclusion or exhausts the budget.
- **Condition B (General Re-inspection)**: A single trial comprises 2 stages. The first produces an initial assessment using the same exploration prompt as Condition A. The second provides a generic prompt asking the agent to re-examine overlooked counterexamples, source freshness, confusion between targets and extensions beyond the applicable scope. Both stages share the budget for the same trial. Condition B uses a generic re-inspection prompt; it is not a reimplementation of Reflexion or Self-RAG.
- **Condition C (Fixed Viewpoints)**: The same 5 fixed viewpoints are examined in every case: scope of applicability; counterexamples and negative cases; differences in time and version; dependency invariants; and duplicate provenance and circular citations.
- **Condition D (Single Adaptive Exploration)**: An explicit Understanding State is maintained, and a single investigator selects and checks unverified items one at a time, updating the state.
- **Condition E (Ommatidia)**: Viewpoints and priority unverified items are derived from the Understanding State; up to 3 investigators run concurrently, and the state is updated after reconciling the acquired evidence.

Following EVALUATION_SPEC.md §5.2, the primary comparisons are E versus C for H1, E versus D for H2 and H3, and E versus B for H4.

### 4.2 Budget Constraints

Identical per-trial budget limits apply to all conditions. Resources consumed by plan generation, investigator calls, communication, state recording, retries to repair JSON and final synthesis are all charged to the same budget.

- Model calls: at most 8
- External tool calls: at most 12
- Input context: at most 48,000 characters (checked by character count before submission)
- Output tokens: at most 16,000 tokens (4,000 tokens per call)
- Elapsed time: at most 180 seconds
- Concurrent investigators: at most 3 (Condition E only)

The execution environment can directly measure elapsed time (milliseconds), model calls, tool executions, input characters, retries and schema errors. Token counts cannot be measured when the API does not return usage information, and monetary cost cannot be measured. As the execution environment reports the base model's cost (`cost.output`) as `null`, costs will not be compared; efficiency will instead be reported using the physical quantities listed above.

### 4.3 Evaluation Cases and Execution Scale

The case collection will comprise 48 synthetic cases: 16 from each of 3 domains—software development, business process automation and documentary research. The 16 cases in each domain will be divided into 8 for development and tuning (Development Set) and 8 for evaluation, kept private until results are finalised (Held-out Evaluation Set). This gives 24 development cases and 24 evaluation cases. Cases will include hidden critical materials, differences in the dates of materials, distinct target entities, duplicate information arising from republication, counterexamples, cases requiring no further checks, cases yielding no results and cases in which tools are unavailable. Essential checks and the applicability of evidence will be defined in advance in the ground truth and will not be provided to the model.

The planned execution scale is shown below. Each case will be run once per condition ($R = 1$).

| Stage | Set | Cases | Conditions | Trials | Maximum model calls | Maximum tool calls |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Stage 1: Development pilot | Development | 24 | 5 | 120 | 960 | 1,440 |
| Stage 2: Preregistered evaluation | Evaluation | 24 | 5 | 120 | 960 | 1,440 |
| Total | | 48 | 5 | 240 | 1,920 | 2,880 |

The model-call limits are calculated by multiplying the number of trials by 8 calls per trial, including planning, investigators, communication, retries and synthesis. An extension to 3 trials for each of the 24 evaluation cases (360 trials) is optional under the protocol and requires separate approval. This extension has not been approved, is excluded from the present plan and has not been executed.

Evaluation metrics will use only the 24 evaluation cases as the denominator ($N_{\text{heldout}} = 24$); development cases will not be included in that denominator. Ground-truth answers, locations of essential evidence and scoring rules for the evaluation cases will be sealed using SHA-256 before execution. Prompts, thresholds and heuristics will be fixed using only the 24 development cases before evaluation begins.

The current status is as follows. According to the work record (`research/hand_over_dev_cases.md`), the 24 development cases have been created as 8 case types × 3 cases. The 24 evaluation cases have not been approved as the definitive version and will not be used for the runs described in this paper. The seal record (`research/seal_manifest.json`) contains entries for the development manifest (`research/datasets/dev/manifest.json`) and evaluation manifest (`research/datasets/heldout/manifest.json`). The evaluation manifest itself is maintained as an untracked working copy. Runtime freeze r4 (`research/runtime_freeze_r4.json`) exists, but the evaluation package is marked `blocked_rebuild_required`, and no study trials have been run (`studyTrialsExecuted = 0`). Accordingly, this paper contains no experimental results.

### 4.4 Metrics

Metric definitions follow EVALUATION_SPEC.md §2. Final judgements will be scored using 4 values: `supported`, `contradicted`, `disputed` and `inconclusive`.

Primary metrics:

1. **Final decision accuracy ($\text{FDA}$)**: The proportion of cases in which the final judgement matches the ground-truth judgement. The denominator is $N_{\text{heldout}} = 24$.
2. **Critical evidence recall ($\text{Recall}_{\text{crit}}$)**: The mean across cases of the proportion of essential ground-truth evidence correctly retrieved and cited in each case.

Secondary metrics:

3. **False alarm rate ($\text{FAR}$)**: The proportion of generated checks addressing non-existent contradictions or issues outside the applicable scope.
4. **Candidate check precision ($\text{Prec}_{\text{cand}}$)**: The proportion of generated unverified items corresponding to actual gaps in the evidence.
5. **Decision degradation rate ($\text{DDR}$)**: Among cases in which the initial draft answer was correct, the proportion in which the final judgement becomes incorrect.
6. **Warranted and unwarranted abstention rates ($\text{WAR}$, $\text{UAR}$)**: The proportion of unresolvable cases answered with `inconclusive`, and the proportion of resolvable cases answered with `inconclusive`, respectively.
7. **Number of independent sources ($\text{DSC}$)**: The number of non-duplicate source groups retrieved and verified.
8. **Efficiency**: Essential evidence items retrieved per tool call and per second of elapsed time.

### 4.5 Statistical Analysis and Evaluator Masking

The unit of analysis is the case. As $R = 1$, there is no clustering due to repeated trials within a case. Comparisons between conditions will use pairs from the same case.

- **Binary primary endpoints (H1 and H4)**: A two-sided exact McNemar test will be used, assuming that each condition yields 1 binary outcome per case (whether the final judgement is correct) and that outcomes are paired by case. The test depends only on discordant pairs. H4 will be compared within the subset of cases containing counterexamples, fixed at 12 of the 24 evaluation cases. This count and the selection of cases will be specified when the evaluation cases are created and sealed before execution. Significance at the Holm-adjusted level of 0.0125 requires at least 8 discordant pairs in one direction.
- **Continuous and count primary endpoints ($\text{DSC}$ for H2 and $\text{FAR}$ for H3)**: Following EVALUATION_SPEC.md, a paired Wilcoxon signed-rank test will be applied at case level. Pairs with zero differences will be excluded. Ties will receive average ranks, and a normal approximation without continuity correction will be used. If there are fewer than 6 non-zero pairs, the test will be treated as not applicable and the outcome as inconclusive.
- **Uncertainty in proportions**: Each condition's $\text{FDA}$ will be reported with a continuity-corrected Wilson score 95% confidence interval.
- **Multiplicity**: The Holm procedure will be applied to the tests of the 4 primary hypotheses to control the family-wise Type I error rate at 0.05.
- **Secondary analyses**: BCa bootstrap 95% confidence intervals for continuous differences (such as $\Delta \text{Recall}_{\text{crit}}$), with $B = 10{,}000$, will be treated as exploratory measures.

With $N_{\text{heldout}} = 24$, statistical power is limited. A two-sided exact McNemar test requires at least 6 discordant pairs to achieve $p \le 0.05$, even if all discordant pairs point in the same direction ($p = 0.03125$). At least 8 are needed to fall below the first Holm threshold of $0.0125$ ($p \approx 0.0078$). These values are design properties calculated from the binomial distribution, not experimental results. A non-significant difference does not constitute evidence of no difference.

Masking is restricted to evaluators. Agents receive condition-specific prompts as execution instructions and therefore know their own condition. Scoring scripts and human evaluators receive outputs with condition labels removed and random IDs assigned; the mapping is consulted only after metrics have been calculated. The plan is therefore single-blind (evaluator masking), not double-blind. Scoring is automated by comparing JSON fields against the sealed ground truth and checking hashes; ground-truth answers are not passed to the model or evaluation prompts.

---

## 5. Results

**Status: Experiments have not been conducted (Pending)**

This study is currently at the stage of fixing the design and experimental protocol. There have been 0 real-model comparison trials, and none of the planned 240 trials has been executed. Cost and token usage are unmeasured. No experimental results are present. No measurements, success rates or cost estimates will be included in the manuscript until actual execution results are available.

The repository contains the following artefacts, none of which constitutes experimental results addressing the RQs.

- **Development-case format checks**: The check described in the work record set the state directly to the ground-truth judgement and passed it to the scorer, confirming '100%' success across all 24 cases. This checks consistency between case format and the scorer; it does not demonstrate the effectiveness of any condition.
- **Simulated mechanism runs**: `research/output/paired_E_vs_D_run_paired_001.json` records a check of the execution infrastructure, running Conditions E and D on 2 simulated tasks (with the model specified as `null`); the mean difference is 0.0. This is a simulated run with n = 2, not an empirical study result.
- **Document audit**: `research/tombo-audit/` records checks of consistency between the protocol and documentation; it is not a comparative experiment.

---

## 6. Discussion

The following issues will be examined after the experiments have been conducted.

1. **Information gain and overhead of dynamic viewpoint selection**:
   Whether dynamically generating viewpoints leads to the detection of more essential evidence than fixed viewpoints or general re-inspection, or merely increases calls and latency.
2. **Coordination costs of dividing work among investigators**:
   The extent of duplicate retrieval of the same materials and fragmentation of context when investigators run concurrently, and whether the reconciliation component can consolidate their outputs.
3. **Risk of excessive rejection through evidence reconciliation**:
   Whether checking provenance and applicability conditions also removes necessary supplementary evidence, increasing inconclusive judgements.
4. **Limits to generalisation from synthetic settings to practice**:
   The extent to which patterns observed in the 24 synthetic evaluation cases apply to real web investigations where provenance is opaque.

---

## 7. Limitations

The proposal and evaluation plan have the following limitations.

1. **LLM dependence in generating unverified items**:
   The unverified items identified by the system depend on the base model's knowledge and prompt-driven inference. There is no guarantee that blind spots beyond the model's recognition can be discovered without external information.
2. **No guarantee of formal verification**:
   Evidence reconciliation and management of state transitions are heuristic procedures; they provide neither formal verification nor proof of factuality.
3. **Dependence on external tool quality**:
   The accuracy of investigators is directly constrained by the available external tools, including search coverage and retrieval accuracy.
4. **State management overhead**:
   Maintaining the Understanding State and checking provenance increase calls, input characters and latency compared with direct generation. These additional resources are charged to the same budget in every condition.
5. **Limitations of identical-text hashes**:
   The deduplication specified by the protocol detects only identical text with matching SHA-256 hashes. Paraphrased republications may be counted as independent evidence.
6. **Statistical power**:
   There are 24 evaluation cases. As described in §4.5, significance in the exact McNemar test requires at least 6 discordant pairs biased towards one direction (at least 8 at the first Holm threshold). Small differences are unlikely to be detected.
7. **Scope of blinding**:
   Only evaluators and scoring scripts can remain unaware of the conditions; agents know their own condition.
8. **Overlap between the case author and the model under evaluation**:
   According to the work record, the 24 development cases were created by `gemini-3.8-flash-high`, the same model as the base model. Case wording may be biased in favour of or against the model under evaluation (inference). The author of the evaluation cases has not been determined.
9. **Single base model**:
   Any results obtained will concern the single base model fixed in the protocol; generalisation to other models will not be tested.
10. **Empirical evidence pending experiments**:
    The design and hypotheses in this paper remain proposals until supported by actual measured data.

---

## 8. Conclusion

This paper has presented the design and experimental plan for Ommatidia, a system for AI-agent investigation that maintains its Understanding State as external data, constructs investigators from unverified items and reconciles evidence. The official versions of Self-RAG, Adaptive-RAG, STORM and Reflexion were examined to distinguish their mechanisms, separating descriptions in those papers from inferences made here. This comparison identifies design differences; it establishes neither novelty nor effectiveness.

Future work is to create and seal the 24 evaluation cases, fix settings through 120 development trials, and then execute 120 evaluation trials. The effectiveness and limitations of the proposed method will subsequently be reported following checks by an independent verifier.

---

## References

1. Akari Asai, Zeqiu Wu, Yizhong Wang, Avirup Sil, and Hannaneh Hajishirzi. 2024. Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection. In *International Conference on Learning Representations (ICLR 2024)*, pages 9112–9141. arXiv:2310.11511.
2. Soyeong Jeong, Jinheon Baek, Sukmin Cho, Sung Ju Hwang, and Jong C. Park. 2024. Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models through Question Complexity. In *Proceedings of the 2024 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies (Volume 1: Long Papers)*, pages 7036–7050. arXiv:2403.14403.
3. Yijia Shao, Yucheng Jiang, Theodore A. Kanell, Peter Xu, Omar Khattab, and Monica S. Lam. 2024. Assisting in Writing Wikipedia-like Articles From Scratch with Large Language Models. In *Proceedings of the 2024 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies (Volume 1: Long Papers)*, pages 6252–6278. arXiv:2402.14207.
4. Noah Shinn, Federico Cassano, Ashwin Gopinath, Karthik Narasimhan, and Shunyu Yao. 2023. Reflexion: Language Agents with Verbal Reinforcement Learning. In *Advances in Neural Information Processing Systems 36 (NeurIPS 2023)*, pages 8634–8652. arXiv:2303.11366. (The current arXiv version lists 6 authors, including Edward Berman.)
