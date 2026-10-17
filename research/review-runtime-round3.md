fail model-authored verdict is still ignored (blank and contradicted child output both give supported/1.0); failed trials cannot be serialised so the cohort aborts; the registry double-counts on every resume; the frozen conditions are unchanged, so the live path cannot run B/D/E correctly.

# Code Review: Ommatidia Runtime, Remediation Round 2 (final independent review, Round 3)

**Review date:** 2026-10-15 (JST)
**Reviewer:** `claude-sonnet-5-5`, effort `high`, vendor Anthropic (differs from the Google implementer, so cross-vendor holds)
**Target:** working tree on `main`, HEAD `56ef2f1` (equals `baseCommit`), with uncommitted changes to `src/ommatidia/{harness,state,t3_adapter}.py`, `scripts/run_harness.py`, `tests/test_{harness,state}.py`, `research/seal_manifest.json` and docs
**Implementer hand-over:** `research/hand_over_runtime_fix_r2.md` (claims B1–B8 fixed, 57 tests)
**Prior review:** `research/review-runtime-round2.md`
**Owned artefacts:** this file and `research/task-gate-runtime-state.json`
**Decision source:** `framework_only_local`; Jev was not consulted.
**Scope statement:** code-level verification only. Nothing here is evidence about the efficacy of Ommatidia. No model experiment has been run. The synthetic cohort is a mechanism check only.

## 1. Verdict

**FAIL.** This is the last allowed remediation round, so per the instruction no further implement/verify pair should be dispatched; escalate to the parent/user (section 6).

Some Round-2 items are genuinely fixed (section 4). The central B1–B4 claims are not, and the hand-over's "57 passed" does not cover them because the tests never serialise a failed trial, never restart a registry, and never check a verdict.

## 2. Blocking findings (each reproduced; probes in section 5)

### F1. The model's verdict still never reaches `FinalJudgement` (hand-over B2)
- `src/ommatidia/harness.py:765-791` looks for `final_state.final_judgement` first. Every runner ends with `state.synthesize_final_judgement()`, so it is always set (`src/ommatidia/types.py:814-882`, derived from claim status). `hasattr(final_state, "raw_response")` is never true (no such attribute exists anywhere in `src/`); `ingest_final_judgement` is therefore dead code on the run path. `src/ommatidia/conditions.py` is **unchanged** since the freeze (hash `cf0310e4…` still matches `holdout_manifest.json`).
- Probe P1 (A and B, in-memory fixture, test-owned executor):

  | executor output | recorded verdict | confidence | model calls |
  | :--- | :--- | :--- | :--- |
  | `{}` (blank) | `supported` | 1.0 | 0 |
  | `finalJudgement.verdict = contradicted` | `supported` | 1.0 | 1 (A), 2 (B) |
  | flat JSON with `verdict = contradicted` | `supported` | 1.0 | 1 (A), 2 (B) |

- Impact: A and B always report `supported`; C, D and E depend on harness-side claim status, not on what the model said. FDA, H1, H4 are artefacts of the harness. The hand-over line "blank/invalid responses recorded as inconclusive" is false. The `inconclusive` branch at `harness.py:775-791` is unreachable.
- Minimal fix: in each runner (or a wrapper), take the last step output, call `ingest_final_judgement`, and set `state.final_judgement` from it; on parse failure record `inconclusive`/0.0 and count it as an invalid response. Because `conditions.py` is inside `conditionImplementationFreeze`, this needs a deliberate re-freeze of `holdout_manifest.json` before any held-out run (no held-out run has happened, so this is allowed but must be recorded).

### F2. A failed trial cannot be saved; the first executor failure aborts the cohort (hand-over B4)
- `harness.py:854-867` builds `FinalJudgement(resource_usage={...dict...})`. `FinalJudgement.to_dict` calls `self.resource_usage.to_dict()` (`types.py:253`), so `TrialRecord.to_dict()` raises `AttributeError: 'dict' object has no attribute 'to_dict'`.
- Probe P2b: `evaluate_task` returns the failed record in memory, then `run_cohort` raises at `harness.py:957`. Result: zero trial files, no `summary.json`, `registry.total_trials == 1` for a trial with no record.
- The new test `test_failed_trial_recorded_and_stays_in_denominator` (`tests/test_harness.py:218-240`) only checks the in-memory object and never calls `to_dict()`.
- Impact: a T3 outage or timeout still halts the campaign, and the registry counts a trial that has no file. "Failed trials remain in N = 24" is not achieved.
- Minimal fix: build `FinalJudgementResourceUsage(...)` objects (as `synthesize_final_judgement` does), add a round-trip test (`run_cohort` with a raising executor, then reload every file), and assert the file exists.

### F3. The persisted registry double-counts on every restart and is not reconciled (hand-over B3)
- `harness.py:915` loads the file totals (`load_from_path`, max-merge, `:288-304`), then each resumed trial calls `record_trial_completion(..., from_resume=True)` (`:935-937`) which adds the same trial and its usage again (`:250-258`). `reconciled_trial_keys` is not persisted.
- Probe P4 (2 tasks × A,B, synthetic executor, new harness object per run, same output dir): trials/model calls = 4/6 → 8/12 → 12/18; the on-disk file also reads 12. Each restart inflates the aggregate, so a campaign with a few restarts exhausts the 240-trial ceiling early and refuses valid work. It is fail-closed in direction but is not reconciliation.
- No reconciliation with trial files exists. In the repository now, `research/output/dev/resource_registry.json` says `totalTrials: 2, trialsByCondition {E: 2}` (produced by `mechanism_check`), while `research/output/dev/trials/` holds 120 stale synthetic files. A live `run_dev` would start from 2 and silently ignore the rest.
- The registry file is per partition (`run_harness.py:191`, `harness.py:913`). Probe P5: `dev` and `heldout` each get their own counters, so the 1,920-call / 240-trial ceilings are enforced per partition, not for the study.
- `load_from_path` swallows every exception (`harness.py:303-304`). Probe P6: a truncated registry file loads as 0 trials / 0 calls with no error, resetting the budget.
- Reservation is not durable and is not per call: `reserve_model_call(1)` (`:145-150`, called once at `:709`) neither mutates nor persists anything. Usage is written only after a step returns (`:740-741`).
- Failed or timed-out calls are unmetered: probe P3, an executor that raises after the child ran leaves `rec.usage.model_calls == 0` and registry calls 0. A child that omits `usage` is counted as 0 model calls (P1 blank case). The host never applies a floor of one call per dispatched step. This contradicts "failed calls retained in the denominator" for the cost side and Protocol 6.2 (host counts model turns).
- Minimal fix: one campaign-wide registry path (not per partition) written with a durable `reserved` count before each dispatch (write-then-call, settle after); on start, recompute totals from trial files plus an append-only step ledger instead of adding to the stored totals; fail closed on an unreadable registry; count at least one model call for any dispatched step, including failures and timeouts.

### F4. The live T3 path still cannot run conditions B–E as pre-registered (hand-over B2/B5)
- The executor that `--executor t3` actually uses is `delegate_step` (`t3_adapter.py:375-476`) fed by the runners' own payloads (`conditions.py:154-163, 214-222, 336-344, 393-400, 479-486`). Those payloads contain no `proposedAnswer`, no `budget`, and no response schema. `delegate_step`'s prompt (`t3_adapter.py:390-395`) says "matching the FinalJudgement schema or step output schema" without supplying either. The changes Gemini made to include these fields are in `create_condition_dispatch_jobs`, which nothing in the run path calls.
- The exported plan does not match the runners. Probe P4 step names:

  | Cond | runner steps (executed) | plan steps (exported) |
  | :--- | :--- | :--- |
  | B | `pass1_investigation`, `generic_recheck` | `pass1_investigation`, `pass2_reflection` |
  | D | `adaptive_plan_step`, `single_investigator_exec` | + `adaptive_synthesis` |
  | E | `ommatidia_inspect`, `ommatidia_investigate_batch` | `ommatidia_coordinator`, `…_investigate_batch`, `ommatidia_synthesis` |

  No runner has a synthesis step, so `PROMPT_CONDITION_E_SYNTHESIS` and the D synthesis job are never used on a live run. Plan jobs are static and cannot carry the prior step output (B pass 2, D/E investigate depend on earlier results); every job demands the FinalJudgement schema, including planning steps.
- No code imports a returned job result by unique trial/step (`grep` for import/ingest of dispatch results in `src/` and `scripts/`: none). The hand-over's "return import by unique trial/step" is not implemented.
- `delegate_task` is called without `isolation` or path restriction (`t3_adapter.py:403-408, 494-499`), so a child with file tools can read `research/datasets/**/gold` and `cases/`. This was Round-2 item 6 and is unchanged. `check_heldout_leakage` (`seal.py:114`) is still never called.
- Nothing records which provider/model/child task actually answered (`TrialRecord` has no such field); model, tool and model-call counts are child self-report only. A CLI-created adapter has no `in_session_dispatcher`, so only the `T3_ACP_MCP_NODE` route is reachable from the script.
- Minimal fix: make one code path define each step (runner step name, payload, schema, expected output) and use it for both live execution and the plan; add the synthesis steps to D/E runners; pass `proposedAnswer`, `budget` and the per-step schema in every payload; record `taskId`/provider/model per step; run children in an isolated worktree that contains only public packets, and call the leakage check on every dispatched prompt.

### F5. Freeze and hash checks are still decorative (hand-over B6)
- `harness.py:714-715`: `code_hash = sha256("ommatidia_code_<cond>")`, `prompt_hash = sha256("<cond>")`. Probe P12 confirms these are hashes of constant labels, not of code or prompts.
- Resume trusts any saved file whose `executor` matches (`harness.py:926-942`). Probe P11: a record with `codeHash`/`promptHash` set to `deadbeef` is reused with 0 executor calls.
- `research/seal_manifest.json` seals four files (protocol, EVALUATION_SPEC, the two dataset manifests). No code, prompts or `holdout_manifest.json`. `run_heldout` only tests that `holdout_manifest.json` exists (`run_harness.py:275-282`); `baseCommit`, `conditionImplementationFreeze`, `coreTypesFreeze`, `evaluatorFreeze` are never read (`grep`: no references in `src/` or `scripts/`). The tree is dirty relative to `baseCommit` and `harness.py`, `t3_adapter.py`, `run_harness.py` sit outside every freeze.
- Current state is intact: SHA-256 of `conditions.py`, `evaluator.py`, `types.py`, `PROTOCOL.md`, `EVALUATION_SPEC.md` and `datasets/heldout/manifest.json` equal the recorded freezes, and `scripts/verify_seals.py verify` passes. This is a point-in-time fact; nothing in the runner enforces it.
- Minimal fix: compute the real hash of the implementation files and prompt constants at run time, compare against `holdout_manifest.json`, require a clean tree at `baseCommit`, stamp those hashes in each `TrialRecord`, and make resume reject any mismatch.

### F6. Assessor masking still leaks condition identity through usage (hand-over B8)
- `export_masked_assessor_dataset` drops top-level usage, but keeps `finalJudgement.to_dict()` (`harness.py:617`), which includes `resourceUsage` with `modelCalls`/`toolCalls`/`elapsedMs`/`inputCharsEstimated`. Probe P4 (all five conditions, synthetic): the masked file has `MCOND_05 → (5, 0)`, `MCOND_03 → (2, 1)`, `MCOND_02 → (1, 0)`, so each label is trivially identifiable (C always makes five calls). The unit test checks only top-level keys.
- The unblinding key is written next to the masked set (`harness.py:636`) and embeds `fda`/`recallCrit`. The random seed default is fine (seed `None` gives an unpredictable mapping).
- Minimal fix: strip `resourceUsage` from the masked `finalJudgement`, write the key outside the assessor directory.

### F7. Scoring and analysis remain incomplete and partly fabricated (hand-over B7)
- `--mode evaluate` (`run_harness.py:380-395`) writes `far=0.0`, `unnecessary_check_rate=0.0`, `required_gap_recall=recall_crit`, `warranted_abstention=None`, `unwarranted_abstention=None`, `efficiency_*=0.0`, and `dsc` counted from cited evidence including input sources. `TrialRecord` stores no state, so `score_run_objectively` cannot be applied afterwards. H2 (DSC) and H3 (FAR) cannot be tested from these records, and `required_gap_recall` is mislabelled. These values are then written back over the trial files (`:416-418`).
- `compute_holm_bonferroni` is defined and imported but never called (`grep`); no mode applies Holm across H1–H4. No H4 12-case subset, DDR, Prec_cand or BCa.
- Denominators are not enforced: `evaluate` iterates only the trial files that exist, a missing gold file silently scores that task as FDA = 0 (`:351-413`), and `paired_compare` takes the intersection of task ids without asserting N = 24 (`:471-474`). The comment in the code says "failed/missing" but missing trials are never added.
- Correct: Recall excludes input-packet evidence (`run_harness.py:364-367`); exact McNemar (`harness.py:81-93`) and Holm (`:96-110`) are mathematically right; Wilson interval follows the spec's continuity-corrected form; `paired_compare` now reads stored trials and no longer reruns fixtures.
- Not run: I did not execute `evaluate` or `paired_compare`; they need gold or stored live trials, and gold is out of bounds. These points are from code reading only.
- Minimal fix: persist the final `UnderstandingState` (or the metrics computed by `score_run_objectively` at run time against an in-memory gold supplied only to the scorer) in each trial; require exactly 24 trial records per (partition, condition) and 24 gold files with hashes; call Holm over H1–H4 in one analysis mode.

### F8. CLI exit semantics hide failures (new)
- `main()` ends with `return 0` and "Execution completed successfully" regardless of how many trials failed (`run_harness.py:523-524`). If F2 were fixed, a systemic T3 outage would save 120 failed records and exit 0; resume then reuses them as done (`harness.py:926-939`), so a transient outage is frozen into the denominator with no retry policy. Needs an explicit rule (retry up to the approved budget, then record failure) and a non-zero exit when any trial failed.

## 3. Hard caps (checked, partially met)
- Per-trial model/tool/time/char caps and negative-value rejection are enforced after the step returns (`harness.py:167-231`). Probe P8: a step reporting 99 model calls executes in full, then raises; the registry correctly holds 99. The caps are therefore bounded damage, not prevention. `state.py` no longer double-counts tool calls and keeps `None` costs unknown (tests plus code read). Negative step usage is added to the per-trial tracker before `record_step` rejects it (`:740-741`), so the failed record carries `modelCalls = -100` (probe P6b), which F3's resume path would then add into the registry once F2 is fixed.
- Host timing and input characters are measured (`perf_counter`, `len(json.dumps(payload))`) and the 48,000-char check runs before dispatch. Output text size has no cap.

## 4. Hand-over claims verified as true
- `--executor t3` with `T3_ACP_MCP_NODE` unset exits 1 before any run and writes nothing (probe, temp output dir). Default `--executor` is still `synthetic`, and nothing stops `--mode run_heldout` with the default executor from writing synthetic held-out records into the live partition directory.
- `create_t3_executor` has no silent fallback; a delegation timeout calls `task_cancel` first.
- `TrialRecord` carries `executor`; resume re-executes on an executor mismatch.
- Torn trailing ledger line is recovered (probe P7: 2 → 4 lines after resume). Caveat: `sanitize_ledger_file` also drops any corrupt line mid-file silently (P7b).
- Exact-24 packet count, unlisted-file and hash checks in `load_public_packets` are present in code; I did not probe them this round.
- Seed `None` gives an unpredictable condition mapping and UUID4 trial ids.

## 5. Verification performed
- Read: `AGENTS.md`, `hand_over_runtime_fix_r2.md`, `review-runtime-round2.md`, `PROTOCOL.md` (§5.4, §6), `EVALUATION_SPEC.md` (§5), `src/ommatidia/{harness,t3_adapter,conditions,state,ingestion,evaluator,seal}.py`, parts of `types.py`, `scripts/run_harness.py`, `scripts/verify_seals.py`, `tests/test_harness.py` (failed-trial test), `tests/fixtures/synthetic_dev_cases.py` (head).
- Tests: `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider` run **once** → `57 passed in 0.38s` (matches the hand-over; none of the failures above are covered).
- Seal: `python scripts/verify_seals.py verify` run **once** → passed for protocol, EVALUATION_SPEC, dev manifest, held-out manifest. (`evaluate_task` re-verifies internally on every call; that is code behaviour, not a separate review step.)
- Freeze hashes: computed SHA-256 for `conditions.py`, `evaluator.py`, `types.py`, `PROTOCOL.md`, `EVALUATION_SPEC.md`, `heldout/manifest.json`: all equal `holdout_manifest.json`. `HEAD` equals `baseCommit` (`56ef2f1`), tree dirty.
- Probes (temp directories only, scripts under the user temp directory, no repo writes; `git status --short` identical before and after): P1 verdict ingestion; P2b failed-trial serialisation and cohort abort; P3 raising executor leaves usage 0; P4 resume double-counting (run twice more with a fresh harness); P4b masking fingerprint and runner-vs-plan step names; P5 per-partition registries; P6 corrupt registry loads as zero; P6b negative step usage; P7/P7b torn and mid-file ledger; P8 per-trial overshoot; P10 executor-mismatch resume with a failing executor (aborted by F2); P11 stale code/prompt hash reused; P12 hash provenance; CLI `--mode mechanism_check --executor t3` with `T3_ACP_MCP_NODE` removed from the environment → exit 1.
- Tool availability: no model, rate-limit or helper failure occurred in this review, so no fallback was needed; I did not re-run candidate ranking.

## 6. Escalation (no further dispatch)
Per instruction, no further implement/verify pair should be dispatched after this final round. Decisions that belong to the parent/user:
1. Authorise editing the frozen `conditions.py` (needed for F1, F4) and re-freezing `holdout_manifest.json` before any held-out run, or accept a driver that wraps the frozen runners.
2. Decide the failed-trial retry policy inside the 8-calls/trial and 1,920-call ceiling (F3, F8).
3. Decide how live children are isolated from `gold/` and `cases/` (F4).
4. Treat all historical calls (earlier study, probes, reviewers) as consuming the 1,920 ceiling; the registry cannot reconstruct them (unmetered, cost/token unknown).
5. Move or clearly label the 120 stale synthetic files in `research/output/dev/trials/` and reset the `mechanism_check`-written registry before a live run.
The runtime is not ready for a live campaign. Do not report results from this code.

## 7. Boundaries and disclosures
- **Not opened:** anything under `research/datasets/**/gold/**` or `research/datasets/**/cases/**`, `unblinding_key.json` (existing or any new one), any answer key. No held-out or dev gold was loaded by any program I ran (the probes use only the synthetic in-memory fixtures from `tests/fixtures`). No evaluation was run on held-out or dev data.
- **Metadata only:** I listed the top-level names of `research/datasets/heldout` (`cases/ evidence/ gold/ manifest.json public_packets/`), counted the 24 files in `public_packets/`, and printed `holdout_manifest.json` keys and truncated top-level freeze values (these included the stratification category counts and the H4 case id tags, which are manifest metadata). I printed the first two file keys of the dev `manifest.json` (case file names and hashes).
- **Not run:** `run_dev`, `run_heldout`, `evaluate`, `paired_compare`, `mask_assessor` and `plan` CLI modes; any live T3 delegation or paid external call; packet-tamper probes; any `record.py` or global-ledger write; any nested agent. No source file was edited. The Round-2 boundary event (a reviewer's accidental evaluation that loaded held-out gold in-process) and the Gemini builder's out-of-repo scratch directory are as documented by the parent; I did not inspect or touch either.
- Synthetic outputs and the 120 stale `research/output/dev/trials/` files are mechanism-check material and support no efficacy claim.
- Model-selection note (historical context only, not review accuracy): `coding-verify` fell back to `coding-implement` in the parent's catalogue, rank 2, measured best score 80, `cost.output` $10/1M, vendor Anthropic, effort high. System readiness is not implied by catalogue availability.
