# Runtime remediation R3 handover

Status: implementation and synthetic behaviour checks completed; empirical study not started; live execution and the existing held-out package remain blocked.

Verification completed on 2026-10-15 at 14:20:52 +09:00. Implementation used the user-selected Codex `gpt-6.1-sol`, reasoning effort `xhigh`. The supplied filtered benchmark results contained no evidence for this selection; no measured superiority is implied. No further agent or provider was dispatched by this implementation task.

## Scope and files

New implementation files:

- `src/ommatidia/campaign.py`: durable campaign-wide reservations and conservative accounting.
- `src/ommatidia/contracts.py`: complete planning, observation and judgement schemas aligned with existing types.
- `src/ommatidia/runtime.py`: executable A–E graph, actual verdict ingestion, state transitions, bounded concurrent specialised roles and synthesis.
- `src/ommatidia/integrity.py`: actual code, prompt, graph/schema, specification and historical-freeze hashes.
- `src/ommatidia/scoring.py`: saved-trace scoring and preregistered paired H1–H4 analysis.

Updated implementation/test entry points:

- `src/ommatidia/harness.py`: connects the new graph, persists serialisable failed records, checkpoints step provenance and validates resume.
- `src/ommatidia/t3_adapter.py`: injected dispatcher and public-boundary contract, result ingestion, cancellation, ambiguity handling; no provider CLI.
- `src/ommatidia/ledger.py`: exclusive lock creation and durable ledger appends.
- `src/ommatidia/seal.py`: rejects reading protected answer paths while hashing.
- `scripts/run_harness.py`: guarded CLI, saved-record scoring/analysis, separate synthetic destinations, non-zero failure exits.
- `scripts/verify_seals.py`: verifies the R3 runtime package as well as the existing seal.
- `tests/test_runtime_r3.py`, `tests/conftest.py`, `tests/test_harness.py`: behaviour regressions, private-file I/O rejection and corrected legacy test expectations.

New records/docs: `research/runtime_freeze_r3.json`, `research/runtime-driver-r3.md`, and this handover. Existing `runtime-design.md`, `hand_over_runtime.md` and `hand_over_campaign_runner.md` retain their earlier contents with a supersession notice. Five whitespace findings in two documents were repaired while preserving Markdown line breaks.

The existing edits to `state.py`, `tests/test_state.py`, the original seal, task-gate state and dataset/output artefacts were preserved. R3 did not alter `conditions.py`, `types.py`, `evaluator.py`, `PROTOCOL.md`, `EVALUATION_SPEC.md` or `holdout_manifest.json`. The historical runners/scorer remain available but are not the active campaign path. No commit, push, PR or publication was performed.

## Findings and behaviour evidence

- **F1:** A/B flat and nested model verdicts survive actual `run_cohort` persistence and reload. Blank, malformed, wrong-task and invalid-type outputs become inconclusive with confidence zero. Tests: `test_actual_child_verdict_survives_roundtrip`, `test_blank_invalid_response_is_inconclusive`.
- **F2:** executor failures produce typed, serialisable judgements and saved trial files; ordinary failures do not abort later trials. Failed records resume without another dispatch and remain among all 24 scoring records, with failed FDA zero. Tests: `test_failed_trials_persist_and_cohort_continues`, `test_cli_evaluate_scores_complete_saved_matrix_without_changing_trials`.
- **F3:** one root registry covers every partition. Fresh-process resume stays at four trials/six calls across three invocations. Each attempt is durably reserved before dispatch; failed/timeout/missing-usage calls have a model-call floor and conservative tool charges. Corrupt/legacy registries, unregistered output and missing crash records fail closed. Transport retries are limited to one and share the same caps; whole-trial reruns are not automatic. Ambiguous dispatch/cancellation and reported envelope violations persist a failure and stop the campaign for audit. Tests include the resume, shared cap, pre-dispatch reservation, corruption, crash, timeout, negative-usage, ambiguity and envelope-breach regressions in `test_runtime_r3.py`.
- **F4:** plan and execution share one graph; B receives its real prior response; C/D/E have synthesis; D/E ingest proposals and observations; E's role calls demonstrably overlap in the synthetic barrier test. Payloads include proposed answer, budgets and complete per-step schema. Every returned child is matched to provider/model/task/request IDs. The injected transport tests call only local fake functions. Unattested transports never dispatch, and graph templates cannot bypass harness accounting. Tests: `test_execution_and_plan_use_same_graph_and_injected_transport`, `test_adaptive_graph_ingests_each_selected_probe_and_synthesises`, `test_e_roles_overlap_and_reservations_remain_consistent`, `test_unattested_t3_transport_never_dispatches`.
- **F5:** hashes are derived from real file bytes, prompt constants, dispatch instruction and executable schemas/graph. Resume rejects changed records/provenance; old core hashes and `baseCommit` are verified. R3 is a separately versioned external driver package; old manifests remain history. Tests: `test_resume_rejects_saved_hash_changes`, `test_real_hashes_and_freeze_detect_driver_change`. The final seal command also checked the actual package.
- **F6:** actual masked export strips nested usage and execution fingerprints. The new mapping file is outside `assessor/`; no old mapping is read, printed or modified, and tests do not read mapping contents. Test: `test_actual_mask_export_strips_nested_usage_and_separates_mapping`.
- **F7:** CLI evaluation reads saved final state and explicit sealed synthetic rubrics, writes a separate scored artefact and preserves originals. It does not alias gap recall to evidence recall or substitute missing FAR/efficiency with zeros. FAR requires independent candidate labels; zero/unknown efficiency denominators are errors. Paired analysis requires all 24 cases for B/C/D/E and twelve H4 tags, applies the specified McNemar/Wilcoxon tests and Holm across all four hypotheses, and refuses missing metrics/pairs. BCa is secondary and reports degenerate distributions as unavailable. Tests: the saved-scoring and CLI evaluation/paired tests in `test_runtime_r3.py`.
- **F8:** failed/invalid execution and failed scored trials return CLI exit 1. Valid synthetic inconclusive output is a completed mechanism response, not a successful research finding. Tests: `test_cli_failure_exit`, the failed 24-record scoring regression and quota/timeout tests.

## Exact final checks

From `D:/develop/works/ommatidia`:

```powershell
python -B -m pytest tests/test_runtime_r3.py -q -p no:cacheprovider
# 44 passed in 9.92s; exit 0

python -B -m pytest -q -p no:cacheprovider
# 101 passed in 9.74s; exit 0; full suite run once

python -B scripts/verify_seals.py verify --runtime-freeze research/runtime_freeze_r3.json
# Exit 0; standalone seal/hash verification run once
# Runtime codeHash: 67916037000453ca273fab0e684afc53f95a624ecbd735b1debcb7b3753cdc9f
# Protocol, EVALUATION_SPEC, dev manifest and held-out manifest: OK

git diff --check
# Initially exit 2: five document trailing-whitespace findings.
# Those five findings were subsequently repaired without code changes.
# Final recheck: exit 0.
```

Earlier focused runs exposed invalid synthetic fixture definitions and a genuine repeated-probe lifecycle defect; these were corrected. One focused run's final terminal result was not captured and was not counted as a pass; the completed 44-test command above is the authoritative focused result. The full suite and standalone seal command were not repeated. The suite's automatic filesystem guard rejects access to private dataset directories and the original unblinding filename. Tests use public dev packets and synthetic in-memory fixtures with temporary outputs only.

Only dataset-manifest bytes were hashed during seal verification; no referenced answer file was opened. A preliminary synthetic CLI guard probe selected the protected partition flag without supplying protected inputs and returned before dataset access. It performed no evaluation; that invocation was removed from the final suite. No `run_dev`, `run_heldout`, or protected-data evaluation/analysis/export/plan was executed against the real datasets. No live child study call, external browsing or provider CLI was used.

## Boundary incident, limits and risks

The R2 review records a prior programmatic access to held-out gold. The reviewer reported that values were not displayed, saved or transmitted. This still violated zero-inspection. R3 did not repeat the access, inspect any old answer, tune against it or erase history. No held-out outcomes have been published according to the supplied brief. The new freeze records `blocked_rebuild_required`; held-out CLI branches stop before reading a dataset. A future evaluation package must be separately versioned and built without reading existing answers, then frozen and approved before any study. R3 does not author replacement cases or rubrics.

The supplied brief reports 120 stale synthetic dev records and an inconsistent older registry count of two. Those records were not reopened, migrated, overwritten or deleted. The new runtime rejects reuse of that legacy output tree. It does not invent historical call totals or reset budgets. Historical planning, investigator, review, communication, retry and synthesis costs/calls need an audit before a future campaign. Cost/token caps remain unspecified and costs/tokens remain unknown where unmetered.

A native T3 worktree is insufficient to isolate answers present in its parent commit. The required public-only filesystem boundary and single-invocation/tool/output/deadline enforcement are contracts for a trusted injected controller, tested only with fake transports. Native T3 support and real provider behaviour remain unverified; the present runner fails closed without that controller. If an executor reports violating its reservation, the charge is preserved even above the promised envelope and the campaign stops for audit. Counters do not retroactively prevent an external executor from breaking its promise.

The 180-second wall-clock limit and the existing cumulative call-time guard are both retained; parallel roles can therefore stop earlier under the latter. Missing tool usage is conservatively charged and is not measured tool consumption. Requested metrics that lack complete trace/rubric/measurement information fail instead of producing a complete-looking report. A mapping in a separate directory is not an ACL; assessor distribution remains the caller's responsibility.

An automatic approval review rejected a proposed deletion of the existing per-trial elapsed-time check as an unauthorised weakening of the resource limit. That deletion was not applied. The implemented alternative retains the check and adds locked parallel reservations plus separate wall-clock measurement.

## hand_over_summary

Code remediation and synthetic verification are complete. The authoritative runtime contract is `runtime-driver-r3.md`; package hashes are in `runtime_freeze_r3.json`. Actual study trials remain zero; study calls during R3 are zero. No efficacy, novelty, production-readiness or experiment-completion claim is supported.

Before any future study: audit historical resource accounting, provide and validate a real public-only metered transport, prepare and independently freeze a replacement evaluation package without old-answer inspection, and satisfy the clean committed release gate in a separately authorised task. No further live action is authorised by this handover.
