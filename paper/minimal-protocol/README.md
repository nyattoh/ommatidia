# Minimal design/protocol preprint candidate

This is a separate publication candidate. It does not replace the historical manuscript or protocol, report experimental results, or certify the live runtime. The existing README PR #2 and all README files are untouched. No licence has been selected for this new manuscript; author confirmation is required before archival publication.

## Inputs reviewed and disposition

- Existing paper/manuscript-en.md: supplied author metadata and four-source bibliography; the earlier design/plan is expanded and simplified here into introduction, bounded related work, intended method, evaluation, analysis, limitations and availability. No results-dependent conclusions, superiority claims or placeholder results tables are carried over.
- research/EVALUATION_SPEC.md: source for the five conditions, sample/denominator, metrics and tests. Its broad protocol motivation conflicts with the concrete H1/H4 analysis definitions; the candidate discloses that discrepancy and makes a new frozen analysis binding a prerequisite, rather than silently rewriting history.
- research/runtime-design.md: explicitly marked historical/superseded at its start. It supplies design intent only. research/runtime-driver-r3.md supplies later context and missingness/isolation caveats; neither is treated as a fresh implementation audit.
- Existing Zenodo metadata worksheet: author/name/ORCID source, not proof of a new submission or licence choice. The generated worksheet uses this candidate's exact title and abstract, correct English language, and a deliberately blank licence field.
- research/runtime_freeze_r4.json: public status only, zero study trials and blocked_rebuild_required. No case packets, gold, manifests or assessor mappings are inspected.
- references/verification-ledger.json and references/RELATED_WORK.md: only four existing primary sources are used. Their historical verification is not relabelled as a new literature audit.

The missing element for an empirical article is measured trial output and validated execution provenance. We intentionally do not manufacture a Results section. External preregistration is not established; depositing a prospective plan would provide a public dated record, not a Registered Report acceptance.

## Files and build

- manuscript.md / manuscript.pdf: English publication candidate.
- SHA256SUMS.txt: manuscript source/PDF digests.
- build.py and requirements-build.txt: local reproducible build recipe; it runs no model, does not access datasets and generates an ignored zenodo-metadata.md field worksheet.
- pilot-estimate.md: comparison with repairing execution first; no pilot performed.
- ../../articles/ommatidia-design-plan.md: Japanese Zenn draft with published: false.

From the repository root, after installing the listed build dependencies in an appropriate local environment:

    python -B paper/minimal-protocol/build.py

For extraction/hash checks and page renders, run `python -B paper/minimal-protocol/verify.py`. This checks every source paragraph against PDF body extraction, excluding page-number footers. See validation.json; all four rendered pages were also visually inspected locally. These checks establish document correspondence, not scientific acceptance or live runtime correctness.

Review the PDF and checksum before uploading. Ignore generated zenodo-metadata.md in Git, following the user's instruction to keep metadata drafts untracked. No new ZIP is required. The old bilingual ZIP and old metadata worksheet are removed from Git tracking under the same earlier instruction; their local copies are retained and exact ignore rules added. No repository-root README or runtime files are changed.

## Author decisions and stop boundary

Kota confirms author metadata, manuscript licence, Zenodo record/version/DOI and publication date, supplementary files, publication itself and whether to publish the Zenn article. No Zenodo action or GitHub release is performed here. The PR requests bugbot run and @codex review once each, then stops; it does not automatically chase subsequent findings.
