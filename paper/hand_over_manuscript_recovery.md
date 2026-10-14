# Manuscript recovery handover

**Status**: Manuscript repair done and checked locally. Awaiting the parent's independent review. The paper is not complete and contains no experimental results.  
**Date**: 14 October 2026 (work window 09:15Z to about 11:18Z)  
**Language**: British English  
**Role**: Manuscript recovery sub-agent, `claudeAgent` / `claude-opus-5-5`  
**Workspace**: `D:/develop/works/ommatidia` (verified with `git rev-parse --show-toplevel`)

## 1. What a reader of the paper gets now

The Japanese draft `paper/manuscript-ja.md` now matches `research/PROTOCOL.md` and `research/EVALUATION_SPEC.md` on the run plan, the budget, the statistics and the masking. Its related-work section says only what the four official papers support, and it marks every absence claim as an inference. The reference list has the correct page ranges and authors. The draft states that no real comparison trial has run and that costs and token use are unknown.

The next owner inherits a primary-source ledger (`references/verification-ledger.json` 2.0.0) whose quoted excerpts can be re-checked by script. They also inherit a list of protocol-side inconsistencies that this run was not allowed to fix (section 7).

## 2. Scope and ownership

Files written by this run:

- `paper/manuscript-ja.md`
- `paper/hand_over_manuscript.md` (corrections in place, original text otherwise kept)
- `paper/hand_over_manuscript_recovery.md` (this file)
- `references/RELATED_WORK.md`
- `references/verification-ledger.json`

No other file in the repository changed. A SHA-256 snapshot of all 162 tracked and untracked files was taken before the first write. A final comparison against it showed no change outside the five files above. This run did not modify, run or test `src/`, `scripts/`, `tests/`, `pyproject.toml`, `research/hand_over_runtime.md` (owned by the Grok runtime task) or `research/PROTOCOL.md`. No commit, push, publication, metadata, licence or identifier change was made. No model experiment was run. No held-out answer was read. The held-out set does not exist yet.

## 3. Throughput checkpoint

- **Blocking first steps.** Read the poteto and router skills, verify the workspace, snapshot hashes, then read the protocol, the evaluation specification, the review and the work records before any write.
- **Independent workstreams.** n/a. All five files are one coupled argument (ledger, then register, then manuscript, then handovers), and the brief forbids nested agents.
- **Shared mutable state.** The Grok task writes `src/`, `scripts/`, `tests/` and `pyproject.toml` at the same time. The write sets are disjoint. The hash snapshot detects any overlap.
- **Smallest safe decomposition.** One worker, sequenced as ledger, register, manuscript, old handover, recovery handover. Each unit ended with a scripted check before the next began.

## 4. Changes

### 4.1 Manuscript (`paper/manuscript-ja.md`)

| Issue found | Correction |
| :--- | :--- |
| §4.2 input budget given as 48,000 tokens | 48,000 characters, as in PROTOCOL §4 and the `TaskPacket` schema (`maxInputChars`). |
| §4.4 required at least 3 runs per case | One run per case and condition ($R = 1$). The optional 3-run held-out extension (360 trials) needs separate authorisation and is stated as not executed. |
| Run scale absent | Table of 120 development trials, 120 held-out trials, 240 in total, at most 8 model calls per trial including all overheads, 1,920 model calls and 2,880 tool calls at most. |
| Held-out denominator unstated | $N_{\text{heldout}} = 24$. Development cases are not pooled. The H4 subset denominator is stated as fixed when the held-out cases are written. |
| Condition B described as a prompt applied to Condition A's output | Two phases inside one trial sharing one budget, as in PROTOCOL §3. Stated that B is not a reimplementation of Reflexion or Self-RAG. |
| Condition C used example viewpoints (specification, constraints, running cost) | The five fixed lenses from PROTOCOL §3. |
| Metrics did not match the evaluation specification | FDA and $\text{Recall}_{\text{crit}}$ as primary metrics. FAR, $\text{Prec}_{\text{cand}}$, DDR, WAR, UAR, DSC and efficiency as secondary metrics. |
| "Blind evaluation" without qualification | Single-blind with masked assessors. Agents know their condition. Stated as not double-blind. |
| No statistical plan | Case-level pairing. Exact McNemar only for the binary per-case endpoints (H1, H4). Wilcoxon for DSC and FAR (H2, H3) as in the specification. Wilson intervals for proportions. Holm across the four primary tests. Computed power note (see section 6). |
| Claim states Refuted and Conflicted | `unverified`, `supported`, `contradicted`, `disputed`, plus `inconclusive` as a verdict. |
| Broken formulae in §3.1 and §3.2 (`$` signs lost) | Restored $S$, $\langle G, C, H, E, U, I \rangle$, $u \in U$ and $r_u$. |
| Abstract and §1 claimed that no systematic framework exists | Removed. Novelty is explicitly not claimed because only four papers were checked. |
| §2 overstated limits of Adaptive-RAG, STORM and Reflexion | Rewritten from the ledger with claim IDs. See section 5. |
| Hash de-duplication presented as catching syndicated copies | Limited to identical passages. Paraphrased syndication added as limitation 5. |
| §5 silent on existing artefacts | States 0 real trials. Explains that the dev-case "100%" check, the n = 2 mock run and the TOMBO audit are not results. |
| New limitations | Power at N = 24, masking scope, the same model authoring the dev cases and being evaluated, and a single base model. |
| References 5 and 6 (Okapi at TREC-3, DPR) | Removed. Neither was cited in the body. |

### 4.2 Related work and ledger

`references/RELATED_WORK.md` now holds one table per paper with claim ID, type (supported or inference) and location. The unverified comparison rows (resource budget and stopping) are deleted. The corrupted phrase in the Adaptive-RAG section is fixed.

`references/verification-ledger.json` 2.0.0 holds 28 claims (22 supported with verbatim excerpts, 6 inferences without excerpts), official URLs, BibTeX URLs, page ranges, PDF hashes and access times. The previous agent's router record is kept unchanged under `history`.

### 4.3 Old handover

`paper/hand_over_manuscript.md` keeps its text. A recovery note at the top lists what was wrong. The 48k-token budget line, the "minimum 3 runs" line and the "double-blind grading" line are corrected in place. Gates G1 and G4 now read "Superseded" with the reason.

## 5. Primary-source verification

Method. `curl` fetched the official venue PDFs and BibTeX into `D:/inbox/ommatidia-recovery-20261014/sources` (outside the repository) between 2026-10-14T11:01:56Z and 11:03:04Z. `pdftotext` extracted the text. `grep` located each passage. No summarising model was used. OpenReview returned HTTP 403 for Self-RAG, so the ICLR proceedings copy was used.

| Paper | Official version used | Correction to the draft |
| :--- | :--- | :--- |
| Self-RAG | ICLR 2024 proceedings, pp. 9112–9141 | Year 2024 and page range added. The API-model limitation is labelled as an inference. |
| Adaptive-RAG | ACL Anthology 2024.naacl-long.389, pp. 7036–7050 | Pages were 7029–7043. The routing is per query and before solving, and the multi-step branch conditions each retrieval on earlier documents and answers (§3.1, p. 7039). "No dynamic adaptation" was removed. |
| STORM | ACL Anthology 2024.naacl-long.347, pp. 6252–6278 | Pages were 6064–6082. Multi-turn follow-up questions within each conversation and a rule-based untrustworthy-source filter (§3.2) are now stated. The missing provenance grouping is labelled as an inference. |
| Reflexion | NeurIPS 2023 proceedings, pp. 8634–8652 | The NeurIPS version lists five authors. Edward Berman appears only on the arXiv page, which is now noted. Feedback is linguistic and generated from evaluator signals that include exact match, heuristics, LLM classification and self-written unit tests. The claim that Reflexion needs an external scalar-reward environment was removed. |

## 6. Numbers in the draft and where they come from

- 240 trials, 1,920 model calls and 2,880 tool calls are the authorised upper bounds in PROTOCOL §6.1 (120 + 120 trials, 8 calls and 12 tool calls per trial). They are plans, not measurements.
- The McNemar thresholds come from `D:/inbox/ommatidia-recovery-20261014/checks/mcnemar_threshold.py`, an exact binomial calculation with two assertions. Its raw output follows. They are design properties, not results.

```
alpha=0.0500 min_discordant_all_one_direction=6 p=0.03125 p_at_n_minus_1=0.06250
alpha=0.0125 min_discordant_all_one_direction=8 p=0.00781 p_at_n_minus_1=0.01562
```

- "100%" in `research/hand_over_dev_cases.md` §9.3 comes from a script that sets `st.decision = gold.target_decision` and then asserts that the scorer returns success. It validates the gold-assigned forms and the scorer. It is not efficacy.
- `research/output/paired_E_vs_D_run_paired_001.json` has `n: 2`, mean difference 0.0 and `model: null`. It is a mechanism mock and not an empirical result.

## 7. Open items for other owners

This run could not fix the following items, because the files are outside its write set.

1. `research/PROTOCOL.md` §3 describes Condition B as "mimicking standard Reflexion / Self-RAG approaches". The verified mechanisms do not support that wording. The manuscript now says that B is not a reimplementation.
2. PROTOCOL §2 compares H3 with "Condition B/D" and H4 with "Condition A/B". EVALUATION_SPEC §5.2 uses E vs D for H3 and E vs B for H4. The manuscript follows the specification. The protocol owner should align the table.
3. EVALUATION_SPEC §5.2 does not say how the Wilcoxon tests handle zero differences and ties. Many zero differences are likely with DSC and FAR at N = 24. Fix this before held-out runs.
4. The H4 counterexample subset size is not fixed. It sets the H4 denominator.
5. `research/seal_manifest.json` records PROTOCOL hash `2b45fc0b…`. The current `research/PROTOCOL.md` hashes to `ff79a4b9e40ee833358a13f238ac0b74e315e2ede4459fd898e4df179924d2d9`. The seal is stale. Its `datasets` object is empty.
6. `research/hand_over_dev_cases.md` §4 and §9.4 still say "double-blind".
7. The development cases were authored by `gemini-3.8-flash-high`, which is also the protocol's base model. The held-out author is undecided. This is now limitation 8 in the manuscript.
8. The 24 held-out cases do not exist yet.

## 8. Dependency on the Grok runtime task

`research/task-gate-runtime-state.json` records the runtime verify verdict as `fail` and lists eight remaining requirements. Examples are budget enforcement in Conditions A and B, null-cost handling and the wiring of a real delegation executor in place of a synthetic one. The manuscript makes no claim about runtime readiness. This run did not read, run or test the runtime code. The 240 trials depend on that work and on the parent's later independent runtime review. If shared runtime files change, this handover makes no claim about them.

## 9. Router evidence (bench-ledger-router)

Commands ran with `python -I`. The global ledger was read only. Its SHA-256 (`676a0070…`) was the same before and after.

- `classify_task.py "Ommatidia manuscript repair: 日本語論文原稿と関連研究台帳の修正、一次資料照合、プロトコル整合"` returned `{"kind": "implement", "domain": "coding-implement", "requirements": ["coding-implement"]}`. The plain phrase `"manuscript repair"` returned the same.
- The full live catalogue was saved to `D:/inbox/ommatidia-recovery-20261014/capabilities-live.json` (8 providers, 35 models).
- `bench_candidates.py capabilities-live.json --requirements coding-implement --max-results 100` and the same command without `--requirements` both exited 0 with 35 candidates.
- For the user-chosen target `claudeAgent` / `claude-opus-5-5`, both runs gave rank 12 of 35. The `benchmark.best_score` was 85.0, `best_source` was `measured`, `cost.output` was 20.0 and `cost.input` was 4.0. The candidate's efforts were `low`, `medium`, `high`, `xhigh`, `max`, `ultracode` and `ultrathink`. Ranks 1 to 3 were `codex/gpt-6-luna`, `cursor/composer-2.5` and `antigravity/gemini-3.8-flash-medium`.
- Effort for this run: the brief carried the prompt-injected value `ultrathink`. This agent cannot observe the host's effective effort setting.
- The ranking informed this report only. The user chose the model. No score, failure or feedback was recorded with `record.py`, because no implement/verify pair has completed and been reviewed.

## 10. Checks run

All commands ran from Git Bash on Windows. Raw outcomes are below.

| Check | Command | Outcome |
| :--- | :--- | :--- |
| Ledger excerpts appear in the official texts | `python -I -X utf8 checks/check_ledger.py references/verification-ledger.json sources` | `claims {'supported': 22, 'inference': 6} failures 0`, exit 0 |
| Manuscript, register and handovers | `python -I -X utf8 checks/check_manuscript.py D:/develop/works/ommatidia pre_hashes.txt` | Final run recorded in section 11 |
| McNemar thresholds | `python -I checks/mcnemar_threshold.py` | Output in section 6, assertions pass |

`check_manuscript.py` fails on forbidden strings (`48,000トークン`, `最低3回`, old page numbers, the removed references) and on missing required strings (`240試行`, `1,920`, `48,000文字`, `$R = 1$`, $N_{\text{heldout}} = 24$, `単盲検`). It also fails on unbalanced `$`, claim IDs absent from the ledger, a register and ledger mismatch, reference pages, authors or arXiv IDs that disagree with the ledger, broken relative links, inconsistent table columns, em dashes and any change outside the owned files. The check scripts live in `D:/inbox/ommatidia-recovery-20261014/checks/` and are not part of the repository.

## 11. Final check output

```
files outside owned set changed since snapshot: none
claim ids in ledger: 28 cited in manuscript: 28
problems: 0
```

## 12. Principles applied

Only principle leaves read in full this session are cited.

- **principle-laziness-protocol.** I deleted the unverified comparison rows and the two uncited references instead of sourcing them. I also kept the old handover's text and corrected only the wrong lines.
- **principle-sequence-verifiable-units.** I wrote the ledger first and checked its excerpts against the PDFs. Only then did I write the register and the manuscript from it, and I re-ran the integrated check after each file.
- **principle-prove-it-works.** Every primary-source claim was checked against the downloaded official PDF text, not against abstracts or the previous agent's report. File preservation was proved by hash comparison, not by `git status`.

Substitutions. The show-me-your-work cross-model trail review was not run, because the brief forbids nested agents and extra LLM calls. The parent's later independent review takes that role. `deslop` and `no-comments` do not apply, because this run changed no code in the repository.

## 13. Decision trail

```
ts	phase	decision	why	evidence	result
2026-10-14T09:15:07Z	frame	hashed every repo file before any write	prove later that only the five owned files changed	D:/inbox/ommatidia-recovery-20261014/pre_hashes.txt	162 files
2026-10-14T11:00:33Z	start	resumed after a context break and re-hashed	another worker may have written in between	resume_hashes.txt vs pre_hashes.txt	no change
2026-10-14T11:01:56Z	sources	downloaded official PDFs and BibTeX with curl instead of a web summariser	brief bars extra LLM calls and asks for full official papers	sources/sha256.txt	4 papers, 3 bib pages, Self-RAG via ICLR after OpenReview 403
2026-10-14T11:02:20Z	sources	found wrong page ranges and Reflexion author list in the draft	official BibTeX disagrees with the reference list	adaptiverag_acl.bib, storm_acl.bib, reflexion_neurips.bib	4 reference fixes
2026-10-14T11:07:07Z	router	ran classify_task and bench_candidates filtered and unfiltered	required by brief, ledger read only	bench_filtered.json, bench_unfiltered.json, ledger_db_sha_before.txt	claude-opus-5-5 rank 12, score 85.0 measured, cost.output 20.0
2026-10-14T11:08:00Z	stats	computed exact McNemar thresholds for N=24 by script	state the power limit as a computed design property, not prose	checks/mcnemar_threshold.py	6 pairs at 0.05, 8 at 0.0125
2026-10-14T11:10:00Z	ledger	rewrote ledger with supported and inference claims and verbatim excerpts	brief asks support and inference separated	checks/check_ledger.py	first run 2 excerpt failures, fixed, then 0
2026-10-14T11:12:00Z	register	rewrote RELATED_WORK from ledger ids and deleted unsourced table rows	smaller than sourcing rows nobody cites	references/RELATED_WORK.md	ids match ledger
2026-10-14T11:13:00Z	manuscript	aligned conditions, budget, run scale, metrics, stats and masking with protocol and spec	brief known issues plus B and C mismatch	paper/manuscript-ja.md	check found 0 manuscript problems
2026-10-14T11:13:30Z	manuscript	kept EVALUATION_SPEC pairs for H3 and H4 where PROTOCOL differs	spec is the test plan and PROTOCOL is outside the write set	section 7 item 2	open for protocol owner
2026-10-14T11:14:00Z	handover	corrected old handover lines in place instead of rewriting it	keep the previous agent's record readable	paper/hand_over_manuscript.md	G1 and G4 superseded
2026-10-14T11:15:00Z	sources	deleting downloaded scratch files was denied	deletion needs approval, files are outside the repo	D:/inbox/ommatidia-recovery-20261014/sources	kept
2026-10-14T11:20:00Z	verify	ran integrated check after writing this handover	prove-it-works before reporting	section 11	problems 0
2026-10-14T11:17:04Z	audit	supersedes the 11:20:00Z verify row, the check actually ran at 11:17:04Z	log audit against command output	date output before check_ledger and check_manuscript	ledger failures 0, manuscript problems 0, outside changes none
2026-10-14T11:17:30Z	audit	supersedes the 11:15:00Z deletion row, the denial happened during source download at about 11:03Z	log audit against tool order	denied rm in the ICLR fetch command	files kept
```

## 14. Attention

reviewed by: none. A cross-model trail review was not run because nested agents were out of scope. The parent's independent review is pending.

- The decision-trail timestamps from 11:08 to 11:20 are approximate to the minute. They were written after the fact from tool output order. The rows at 09:15:07, 11:00:33, 11:01:56, 11:02:20 and 11:07:07 are exact command outputs.
- The previous agent's access timestamps (02:25 JST) remain in the old handover and in the ledger history. They were not re-verified.
- This handover does not claim that the task graph is complete. That needs the parent's independent review.
