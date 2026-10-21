# Ommatidia: An External Evidence-State Design and Prospective Evaluation Protocol

Ryoko Sakakibara — Independent Researcher

ORCID: https://orcid.org/0009-0009-9544-6315

Draft dated 21 October 2026. Research plan and system design; no comparative study results. Manuscript licence: Creative Commons Attribution 4.0 International (CC-BY-4.0), https://creativecommons.org/licenses/by/4.0/.

## Abstract

An investigation can end with a fluent answer while leaving a decisive premise or counterexample unchecked. Ommatidia is a proposed architecture for making these open questions explicit. An external evidence state records goals, claims, testable hypotheses, passages, unresolved items and inspection history. A coordinator derives bounded investigations from that state, reconciles returned evidence and records why work stops. We specify the intended mechanism and a prospective comparison with direct exploration, general re-inspection, fixed viewpoints and a single adaptive investigator. The planned study comprises 24 development and 24 held-out cases across five configurations, with at most 240 trials and 1,920 model calls. Public study records report zero comparative trials, unknown costs and tokens, and an evaluation package marked blocked_rebuild_required. This paper therefore reports a design and an analysis plan, not evidence of effectiveness. Independent validation, a replacement blind evaluation package, a current runtime freeze and verified resource enforcement are prerequisites for execution. Publication of this plan would create a dated public record; no completed external preregistration is claimed.

## 1. Introduction

For an agent using a language model and external tools, a useful next action may be to check a dependency, seek counterevidence or distinguish a version boundary. Ommatidia proposes to represent such unresolved questions explicitly rather than leave them implicit in generated prose. Its research question is whether an external evidence state and state-driven allocation of investigations improve final judgements within a bounded resource envelope. That hypothesis remains untested.

The contribution is a design contract and a prospective evaluation plan. The compound-eye analogy describes multiple bounded investigations; it implies neither consciousness nor access to a model's internal reasoning. Configuration comparisons below estimate differences between complete procedures, not isolated causal effects of individual mechanisms.

## 2. Related work

This deliberately bounded comparison uses only the four primary papers already registered in the repository's references/verification-ledger.json and references/RELATED_WORK.md. Their verification dates are historical; this paper does not claim a new exhaustive literature search or the absence of similar architectures elsewhere.

Self-RAG combines retrieval, generation and reflection tokens [1]. Adaptive-RAG selects retrieval strategies according to question complexity and adapts retrieval context within multi-step retrieval [2]. STORM uses perspectives and multi-turn conversations to support article preparation [3]. Reflexion stores verbal feedback for use in later trials [4]. These systems motivate questions about criticism, adaptation and multiple viewpoints; they are not implemented as faithful benchmark reproductions here. In particular, our general re-inspection baseline is not a replication of Self-RAG or Reflexion. Differences in intended task and state representation do not establish novelty or superiority.

## 3. Method and intended design

The conceptual state contains six components: goals, claims, hypotheses, an evidence ledger, unverified items and inspection history. A claim has a scope and an evidence-linked status: unverified, supported, contradicted or disputed. Final judgements use supported, contradicted, disputed or inconclusive. These are external records, not measurements of cognition.

An investigator contract specifies its question, falsifiable hypothesis, permitted sources and tools, support/refutation/unknown criteria and allocation. Each evidence item records the exact passage, locator, source group, retrieval time, applicable version and scope, validity, and a SHA-256 passage hash. Equal text hashes establish text identity, not truth or source independence. Unavailable passages and empty search results cannot by themselves support or refute a claim.

The intended adaptive procedure is:

1. Initialise the state from the public task without exposing evaluator answers.
2. Identify a goal-relevant unresolved item and define bounded probes.
3. Check capability and remaining trial/campaign resources, reserving final synthesis capacity.
4. Dispatch one investigator for the single-adaptive configuration, or up to three for Ommatidia, within enforced allocations.
5. Validate returned passages and identifiers; assess target, time, scope and provenance; deduplicate exact text; preserve unresolved conflicts.
6. Update claims and open items, propagate evidence withdrawals, and record resource use and failures.
7. Stop on resolution of required items, frozen stagnation criteria, missing capabilities or resource exhaustion. Retain unknowns and the stop reason in the final judgement.

These are design requirements. Active withdrawal propagation, stagnation/capability stopping, synthesis authority and host enforcement require validation or further implementation before a study. The existence of prototype code or passing synthetic fixtures does not establish those requirements end to end.

## 4. Prospective evaluation protocol

### 4.1 Configurations and materials

All five configurations would use the same frozen base model, initial public packet, permitted source set and upper resource limits. The historical protocol names gemini-3.8-flash-high; its availability must be checked before execution. A model substitution would require a documented prospective revision, not a silent fallback. Execution also requires a frozen run configuration identifying the model snapshot, decoding parameters including temperature and top-p, seed support and policy, tool registry and unavailable-tool policy. These settings remain execution prerequisites; unspecified values must not be supplied retrospectively.

- A: direct exploration and final judgement.
- B: initial exploration followed by generic re-inspection. The second phase receives the first returned output and the public task; reconstructed raw tool/conversation history is not promised.
- C: five fixed viewpoints—scope, counterexamples, time, dependencies and redundancy—followed by synthesis.
- D: adaptive state-based investigation with one selected investigator at a time.
- E: adaptive coordination of up to three investigators, reconciliation and synthesis. The prototype supplies state context to investigators; it does not establish probe-only context isolation.

The ordinary host graphs permit one call for A, two for B and six for C. D's ordinary graph leaves a call slot unused relative to the shared ceiling, whereas E can use the full ceiling. These are structural differences in available computation, not merely differences in realised use. Planning, investigation, retries and synthesis all count; any additional model invocation needed to consume returned tool results must also count. A's single-step graph differs from the historical exploration-until-budget workflow despite the shared ceiling stated in its prompt. That deviation and the prompt/graph alignment must be recorded prospectively. A/B comparisons remain blocked until the tool-execution and invocation-counting contract is fixed and independently validated. E–C and E–B contrasts therefore include unequal call opportunities. D and E share state-update mechanisms, so their contrast cannot isolate a reconciliation effect unique to E.

The prospective scale is 24 development cases and a separately frozen set of 24 held-out cases, across software engineering, workflow automation and document research. One run per case and configuration gives 120 development and 120 evaluation trials. Development material is used to finalise settings; it must not enter the held-out denominator. Before tuning, declare comparable development allowances for each configuration and maintain a revision log covering prompts and settings. An undeclared allowance prevents development execution. No optional replications or additional pilot campaign are included in this plan.

### 4.2 Blinding, provenance and resources

The public record research/runtime_freeze_r4.json reports earlier programmatic access to held-out gold in boundaryIncident and marks evaluationPackageStatus as blocked_rebuild_required. The incident field says values were reportedly not displayed or transmitted; this does not restore the zero-inspection boundary. Preserve that package as history and construct a separately versioned replacement without consulting its answers. This drafting work does not inspect case packets, gold or unblinding data.

Before any execution, freeze the replacement public packets and rubrics, model, prompts, graph, schemas, scoring code, analysis decisions and current code revision. Before package freeze, a public aggregate table must declare domain, control-type and counterexample counts, their overlaps, and solvability and initial-verdict eligibility counts for the planned endpoints, without exposing case contents or answers. A randomised or interleaved case-by-configuration run order and its seed must also be chosen, frozen and verified before execution; their implementation is not established here. Missing declarations block execution. Operational agents must have access only to approved public material. Downstream assessors receive condition-masked outputs; agents themselves see condition-specific instructions. Hashes bind versions, but do not create access controls or prove semantic correctness. Matched analyses must use the same task-packet version across configurations, with complete provenance and all 24 case IDs per selected condition.

Per-trial ceilings are 8 model calls, 12 tool calls, 180 seconds and 48,000 cumulative rendered input characters. The study-wide ceilings are 240 trials, 1,920 model calls and 2,880 tool calls. Planning, investigator work, communication, serialised state, retries and synthesis all count. Parallel-role time and wall-clock time must be reported distinctly, with enforcement aligned before freezing.

The existing monetary amendment sets an aggregate JPY 500 ceiling. Before development, reserve capacity and planned cost for the complete held-out phase within the shared ceilings. Before either phase starts, verify that the complete phase can be accommodated; an infeasible phase must not begin. A paid dispatch requires provider-enforced maximum-cost reservation and host-verified settlement; a price estimate alone is insufficient. Unknown usage is not zero. Ambiguous dispatch or missing settlement retains the reservation and stops the campaign. Budget exhaustion also stops execution; an incomplete comparative matrix permits no confirmatory comparison. The current live transport has not demonstrated this contract, so no study is authorised by this paper.

## 5. Analysis plan

The case is the analysis unit. Final-decision accuracy (FDA) is the fraction of the 24 held-out cases whose saved final verdict equals the frozen four-valued target. Failed or invalid trials remain in that denominator and score zero, including a fallback inconclusive response. Missing trials invalidate the comparative matrix rather than silently reduce its size.

Critical-evidence recall is the fraction of each case's nonempty mandatory evidence set that was newly retrieved, verified and correctly cited. Passage, hash, locator and source group must match; input evidence is excluded. Disjoint source coverage (DSC) counts verified retrieved source groups and requires independent validation of grouping. Report the available source-group ceiling and allocated and realised investigator calls alongside DSC descriptively. E permits more investigator calls than D, so their coverage contrast does not isolate a role-decomposition effect. False alarm rate (FAR) is the fraction of generated probes independently labelled spurious, requiring a complete candidate trace. It measures probe-level false alarms, not erroneous acceptance or reconciliation. The historical secondary “spurious acceptance” endpoint remains undefined and is excluded from analysis. A zero-probe case scores zero FAR only if trace completeness is known. A/B lack verified retrieval traces in the current driver: recall, DSC and evidence-yield efficiency are unavailable, never imputed as zero. Missing required metrics prevent a complete confirmatory analysis. Inapplicable abstention indicators are null; pooled candidate precision needs its own labelled numerator and denominator.

The proposed hierarchy follows the concrete analysis table in EVALUATION_SPEC.md, while explicitly retaining its conflict with historical motivation prose:

- H1: E versus C on FDA, exact paired McNemar test; higher E accuracy is the predicted direction. Recall is secondary.
- H2: E versus D on DSC, paired Wilcoxon signed-rank test; higher E coverage is predicted.
- H3: E versus D on FAR, paired Wilcoxon signed-rank test; lower E FAR is predicted.
- H4: proposed E versus B final-decision correctness on exactly 12 predeclared counterexample cases, exact McNemar test. This is not general decision-correction rate: correction additionally requires frozen initial-error eligibility. Resolve that historical endpoint discrepancy and bind the decision in a new freeze before any confirmatory use; retain the existing H4 significance block until then.

Use two-sided tests and Holm correction over the four-member primary family at 0.05. An uncomputable member remains non-significant and enters the adjustment with the largest possible p-value; it is not removed in response to outcomes. Retaining that member is conservative for the remaining tests. The separate H4 significance block remains in force even when its test is computable. Hypothesis support also requires the predicted direction. For Wilcoxon, discard exact zero differences, average tied absolute ranks and use the normal approximation with tied-rank variance correction and without continuity correction; fewer than six nonzero pairs yields inconclusive. This is a computational floor, not evidence of adequate power or a guarantee of significance after Holm adjustment. Report paired differences, continuity-corrected Wilson 95% intervals for accuracy and secondary paired BCa bootstrap intervals with 10,000 resamples. These are prospective procedures, not computed results. Record the complete analysis binding before execution; this manuscript does not resolve it by relabelling historical records as externally preregistered.

## 6. Present status and limitations

The public runtime_freeze_r4.json records studyTrialsExecuted = 0, costYen = null and totalTokens = null. There are no comparative results to analyse, no measured improvement, and no completed external preregistration or scientific acceptance claimed here. No results table, significance claim or performance chart is supplied.

runtime-design.md is a historical architecture document with an explicit supersession notice; runtime-driver-r3.md describes later contracts. Neither replaces verification of a current executable tree. A new freeze must bind the reviewed implementation and approved replacement package; changing hashes merely to silence a failing check is insufficient. Remaining gates include public-only isolation, host usage/cost attestation, cancellation, prompt/schema alignment, endpoint binding and validation of the intended state transitions and stopping rules. The current scorer's H4 safeguard must not be bypassed to obtain a result.

The planned 24-case evaluation offers limited precision and generalisability. Source-group independence, probe validity and evaluator masking need validation rather than inference from hashes or JSON labels. Configuration contrasts combine multiple mechanisms and do not identify individual component effects. The method could increase overhead, redundant retrieval or false alarms; these remain possible outcomes. A later empirical paper would need the actual trial records and an audit of all failures and resources.

## 7. Data and code availability

The public code, historical protocol, evaluation specification and verification ledger are in https://github.com/nyattoh/ommatidia. This draft uses the public main baseline b8cc565ef016f531fdef7325801e3468db82135f as its repository anchor; the accompanying PR adds only this publication candidate and drafting material. Relevant paths are research/PROTOCOL.md, research/EVALUATION_SPEC.md, research/PROTOCOL_AMENDMENT_COST_CAP_20261015.md, research/runtime-design.md, research/runtime-driver-r3.md, research/runtime_freeze_r4.json and references/verification-ledger.json. No held-out answer key, private evaluator data or empirical result dataset accompanies this manuscript. No DOI or GitHub release is assigned by this work. The manuscript is licensed under CC-BY-4.0; this does not change the code's licensing. Archival publication remains with the author.

## References

[1] Asai, A., Wu, Z., Wang, Y., Sil, A. and Hajishirzi, H. Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection. ICLR, 2024. https://proceedings.iclr.cc/paper_files/paper/2024/file/25f7be9694d7b32d5cc670927b8091e1-Paper-Conference.pdf

[2] Jeong, S., Baek, J., Cho, S., Hwang, S. J. and Park, J. C. Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models through Question Complexity. NAACL, 2024. https://aclanthology.org/2024.naacl-long.389/

[3] Shao, Y., Jiang, Y., Kanell, T. A., Xu, P., Khattab, O. and Lam, M. S. Assisting in Writing Wikipedia-like Articles From Scratch with Large Language Models. NAACL, 2024. https://aclanthology.org/2024.naacl-long.347/

[4] Shinn, N., Cassano, F., Gopinath, A., Narasimhan, K. and Yao, S. Reflexion: Language Agents with Verbal Reinforcement Learning. NeurIPS, 2023. https://proceedings.neurips.cc/paper_files/paper/2023/file/1b44b878bb782e6954cd888628510e90-Paper-Conference.pdf
