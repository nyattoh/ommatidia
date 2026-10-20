# Zenodo 入力項目（v0.1.1 下書き・未投稿）

投稿画面へ転記するための案。Zenodo への登録・公開は未実施。日付は投稿時に入力する。

## Upload type

- Resource type: Publication → Preprint

## Title

- Main title (English): Ommatidia: Design and Evaluation Plan for Understanding-State-Based Compound-Eye Investigation
- Translated title (Japanese): Ommatidia：理解状態に基づく複眼型探索の設計と評価計画
- Language: Japanese (`jpn`)

## Creators

| Family name | Given name | Affiliation | ORCID |
| :--- | :--- | :--- | :--- |
| Sakakibara | Ryoko | Independent Researcher | 0009-0009-9544-6315 |

These values follow the author's supplied metadata and Zenodo record 22925518.

## Description

Use the Japanese abstract in `manuscript-ja.md` as the primary description. Add the following English abstract as an additional description, language English (`eng`).

> What can remain unchecked behind a confident answer? Premature closure—reaching confident conclusions while leaving unverified premises and critical counterexamples unexamined—is one of the most serious pitfalls facing LLM-powered investigation agents. How can an autonomous agent systematically stress-test its own emerging explanations? Inspired by the multifaceted vision of insect compound eyes, this paper presents the design of **Ommatidia**. Rather than burying beliefs inside ephemeral context windows, Ommatidia anchors investigation around an explicit, external **Understanding State**—a structured ledger recording goals, claims, hypotheses, evidence, unverified gaps, and inspection history. From this state, the system dynamically constructs concrete, testable **Investigators** targeted at unresolved assumptions, rigorously reconciling evidence without mistaking duplicate text for independent confirmation, preserving real-world contradictions, and enforcing termination under a strict composite budget of calls, tools, tokens, characters, and time.
>
> We analyze the architectural mechanisms distinguishing Ommatidia from four foundational paradigms (Self-RAG, Adaptive-RAG, STORM, and Reflexion) and establish a rigorous, preregistered experimental protocol. The benchmark spans five conditions across 24 development and 24 evaluation cases (240 total trials), capped at 8 calls per trial (1,920 maximum model calls). At present, empirical trials stand at zero, and costs and token consumption remain unmeasured; in accordance with protocol boundaries and a targeted four-paper review, no claim of novelty or empirical superiority is asserted. The design stands complete, its hypotheses preregistered, awaiting execution under controlled experimental audit.

## Keywords

- English: large language models; investigation agents; understanding state; evidence reconciliation; pre-registration; evaluation protocol
- Japanese: 大規模言語モデル、調査エージェント、理解状態、証拠照合、事前登録、評価計画

## License

- CC-BY-4.0 for the manuscripts and accompanying research documents (author-confirmed metadata).
- No source code or evaluation cases are included in this submission package.

## Version and publication date

- Version: `0.1.1-draft`
- Publication date: Enter the date of submission.
- DOI: Leave for Zenodo to assign upon publication; no DOI has been assigned.

## Related identifiers

- Related work: `https://github.com/nyattoh/ommatidia`
- Add the exact source commit after the final package has been committed and pushed.

## Funding

Leave blank unless funding information is confirmed.

## Notes for the record

This is a design and evaluation-plan manuscript, not an empirical-results paper. No real-model comparison trials have been run (0); cost and token usage are unmeasured. Runtime freeze r4 reports the evaluation package as `blocked_rebuild_required`; the evaluation cases have not been approved as the definitive set. No evaluation answers or case files are included here. No claim of empirical effectiveness, novelty or superiority is made.

## Files in the package

- `manuscript-ja.pdf` and `manuscript-en.pdf`: rendered manuscripts.
- `manuscript-ja.md` and `manuscript-en.md`: editable source manuscripts.
- `zenodo-metadata-v0.1.1-draft.md`: these proposed record fields.
- `SHA256SUMS.txt`: checksums for the manuscript source and PDF files.
