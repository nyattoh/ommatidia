# R3 external runtime driver

This document supersedes the runtime execution and readiness claims in the R2 handover documents. It describes implementation behaviour, not experimental findings. The historical `conditions.py`, `types.py`, `evaluator.py`, protocol, evaluation specification and `holdout_manifest.json` remain unchanged by R3. The executable experimental package has a new version in `runtime_freeze_r3.json`.

`ResearchHarness` executes `runtime.condition_graph`; both the plan exporter and the injected T3 executor use that graph. The old standalone condition runners and scorer are historical implementations and are not the campaign execution or saved-record scoring path.

## Execution contract

- A: one direct final judgement. B: initial judgement followed by generic re-inspection with the actual prior response.
- C: five fixed lens observations followed by synthesis.
- D: repeated planning and one selected investigator, with state ingestion between steps and a reserved synthesis slot.
- E: repeated coordination and up to three distinct specialised investigators, dispatched concurrently with divided tool allocations, deterministic collation, then synthesis. A planning loop cannot consume the final synthesis slot.
- Every dispatched payload includes the proposed answer, overall budget, remaining step budget, complete response schema and public context. Planning, observations and final judgements have different schemas derived from the existing types.
- The final judgement is ingested from the returned JSON. Missing, blank, malformed or mismatched output yields an inconclusive judgement with confidence zero and an invalid/failed trial. There is no host-generated supported verdict. Existing probe IDs cannot be repurposed or reset by repeating a planning proposal.
- Each result is associated with its unique trial, step sequence and attempt. The selected and returned provider/model, child task ID, input/output hashes and resource observations are recorded. An acknowledgement is checkpointed before polling the child.

## Budget and recovery

One `output_dir/resource_registry.json` covers the complete campaign, including both partitions. Atomic replacement follows a file flush and `fsync`. The campaign lock uses exclusive file creation. Each trial and each individual dispatch is reserved before execution. Limits remain 240 trials, 1,920 model calls, eight model calls and twelve tool calls per trial, 48,000 cumulative input characters, and 180 seconds. The existing cumulative call-time guard is also retained; it can stop parallel work earlier than the wall-clock ceiling. `wallElapsedMs` records trial wall-clock time separately for efficiency analysis.

Each dispatched step consumes at least one model call. Missing tool usage or a timeout consumes its entire reserved tool allowance conservatively; cost and tokens remain unknown. This is a conservative charge, not a claim of measured consumption. Usage cannot be negative or reduce a reservation. A reported breach of the step envelope stops the campaign for audit, rather than authorising more calls.

A transport failure may be retried once, always inside the same per-trial and campaign ceilings. There are no schema-repair calls or whole-trial reruns. A known child must be cancelled before a timeout retry. An unknown dispatch acknowledgement or unconfirmed cancellation stops the campaign after preserving its reservation and failure record. The stable request ID is available for an external audit. No blind retry is allowed in that state.

Retries may exhaust a trial's remaining allowance before synthesis; such a trial fails rather than borrowing another call.

Failed and invalid trials are terminal on resume and remain in the denominator. Resume verifies run, executor, task, code, prompt, specification and retry-policy identity, record hashes and reservation usage without adding counters. A crash after writing a trial but before its completion checkpoint can be reconciled. A missing record for a reserved trial requires audit and cannot silently redispatch. Corruption, incompatible registries, interior ledger corruption and unregistered historical records fail closed. Only a torn trailing ledger line is recoverable automatically. The old synthetic output and partition registries are preserved and are not migrated or reset automatically.

## Transport boundary

`main(argv, dispatcher=..., public_boundary=...)`, `T3DelegationAdapter` and `T3CampaignController.run_cohort` accept an injected dispatcher. No provider CLI is used. Standalone T3 execution fails closed even if an ACP executable exists, because ACP presence does not establish source isolation or resource enforcement.

The trusted controller must enforce and attest public-only sources, one model invocation per step, step tool/output/deadline limits and verified host usage. `isolation="worktree"` is also requested, but **a native worktree alone does not meet this contract**: it can contain private files from its parent commit. The normal native T3 API has not been demonstrated to supply this boundary. The fake transport tests attest only their synthetic in-memory environment. No live isolation, metering, cancellation or provider compatibility has been validated.

Never pass gold, composite case files, answer keys or assessor mappings to children. A recursive public-payload check rejects evaluator fields and private locators. Tests additionally reject filesystem access to private dataset directories and the original mapping filename. Prompt heuristics are not a replacement for the controller's filesystem boundary.

## Freeze and the evaluation boundary incident

The new freeze hashes the actual core and driver files, CLI, configuration, prompt constants, complete executable graph and response schemas, dispatch instruction, protocol and specification. It binds the unchanged old manifests and checks their historical core hashes and `baseCommit`. Resume cannot reuse a record from a different package. Live study execution additionally requires a clean committed tree and a replacement evaluation package marked approved; neither condition is satisfied by this implementation task.

R2 disclosed that a reviewer process loaded existing held-out gold during a probe. The reviewer reported that values were not displayed, saved or transmitted. Programmatic access nevertheless violated zero-inspection. R3 does not read or use those answers, and no tuning against them is permissible. Old logs and manifests remain history. The R3 freeze records `evaluationPackageStatus="blocked_rebuild_required"`; all held-out CLI actions are disabled before reading a dataset. A future separately versioned evaluation package must be built without inspecting existing gold, with fresh frozen rubrics, public sources, counterexample tags and an independently audited public-only transport. No new cases or answers are authored by R3.

## Saved-record evaluation

The evaluator accepts explicit sealed rubric and analysis-design files. It never discovers or automatically loads a gold directory. Exactly 24 distinct records per selected condition, one replication and matching runtime provenance are required. Missing records, mixed runs, duplicates and unavailable requested metrics are errors. Original trial files are preserved; scored records are a separate artefact.

FDA and abstention indicators use the saved final verdict and an explicit unambiguous target. Failed/invalid FDA is zero. Critical recall requires a non-empty mandatory evidence set and credits only retrieved, verified and cited evidence absent from the input packet. DSC uses verified retrieved source groups, excluding input and merely planned sources. FAR requires a complete candidate trace and independent labels for every probe; it is unavailable for failed traces. Gap recall uses required questions and saved resolutions, not critical-evidence recall. Efficiency requires a known non-zero denominator; its time denominator is measured `wallElapsedMs`. Conditions A and B return only a final answer, so no observation records what they retrieved: their critical recall, DSC and efficiency are null and listed under `unavailableMetrics`, never zero. DDR and candidate precision require the additional explicit labels and initial-verdict information. Inapplicable WAR/UAR indicators are null; missing measurements are never filled with zero. No pooled rate is implied by a per-trial indicator.

`paired_compare` analyses saved records only. It requires B/C/D/E for the same 24 cases and exactly twelve frozen H4 counterexample IDs. It runs H1 exact McNemar on E/C FDA, H2 Wilcoxon on E/D DSC, H3 Wilcoxon on E/D FAR, and H4 exact McNemar on E/B counterexample FDA. Holm correction retains all four family members; an uncomputable Wilcoxon stays inconclusive. Wilson intervals and secondary recall Wilcoxon/10,000-resample paired BCa intervals are available. It refuses unavailable FAR instead of issuing an apparently complete analysis. `resourceComparisons` adds descriptive E-minus-baseline means (B, C, D; all 24 cases) of each trial's total `usage` in the protocol section 6.2 units: elapsed ms, model calls, tool calls and input characters. These include every planning, investigator, retry and synthesis step, carry no hypothesis test and do not join the Holm family; if any paired trial has `usageKnown` false, every unit of that comparison is marked unavailable rather than failing the analysis.

Masked export strips nested `resourceUsage` as well as execution, provider, hash and step metadata. Only `assessor/` is supplied to an assessor. The mapping is a newly named file under the separate `private_assessor/` directory and is not read by tests. Separate directories do not create operating-system access controls; the caller controls distribution and permissions.

## CLI and present limits

An explicit output directory is required. Synthetic runs cannot write into `research/output`; use a temporary destination. A synthetic development cohort additionally requires `--synthetic-check`. Any failed or invalid trial causes a non-zero CLI exit. Plans are dependency-aware graph templates, not independently dispatchable jobs: `T3CampaignController.dispatch_job` rejects bypassing the harness reservation and ingestion path.

Actual study trials remain zero. Monetary and token caps are unspecified and usage remains unknown where unmetered. Historical planning, review and synthesis model costs/calls have not been reconstructed; that audit remains necessary before any campaign. Passing synthetic tests does not establish performance, novelty, experimental readiness, dataset independence or empirical-paper completion.
