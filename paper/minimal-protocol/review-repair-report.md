# PR3 review repair — 21 October 2026

Historical first-round record: its SHA256SUMS.txt file digests below describe Windows CRLF output and are superseded by the fixed-LF receipts in reproducibility.json and the LF follow-up report. The PDF digests remain unchanged. The follow-up fixes the mismatch between those old receipts and Git's committed LF manifest; do not use the historical checksum-file digests as current artefact digests.

Base: 00cc1b91ade4194b5a45aa4d82cb1dae801a1b03, branch devin/20261021-minimal-protocol-preprint. Scope is publication tools and approved publication licence, not experimental results or runtime repairs.

## Changes

- ReportLab invariant mode and explicit document invariant flag. A process-provided SOURCE_DATE_EPOCH takes precedence; otherwise document-metadata.json fixes creation/modification time to 2026-10-21 00:00:00 UTC. Only the build process environment is set; no persistent environment or system settings are changed. Reproducibility assumes unchanged input/dependencies/fonts.
- SHA256SUMS.txt is mandatory and must contain exactly one well-formed entry each for manuscript.md and manuscript.pdf. Missing/empty/partial/duplicate/unexpected entries and wrong digests fail with nonzero exit. These mandatory checks use explicit exceptions, not optimisation-removable assertions.
- CC-BY-4.0 on manuscript/PDF, generated ignored Zenodo metadata and Japanese Zenn text. LICENSE names only those publication texts and excludes software, tests and third-party material. Code licensing is unchanged. Real author name and ORCID remain public as approved. Zenn remains unpublished.
- Regenerated PDF, checksums and extraction validation. Paragraph spacing reduced by one point to keep the added licence statement and references within four pages; no research claims changed.

## Executed checks

1. `python -X utf8 -B -m pytest tests/test_publication_build.py -q -p no:cacheprovider --tb=short --assert=plain`: before implementation **6 failed, 4 passed**, exit 1; after implementation **10 passed**, exit 0. Earlier initial test run was 5 failed/5 passed before correcting the empty-file fixture from one blank line to actual zero bytes. The final RED run tests the real zero-byte case.
2. `python -X utf8 -B -m pytest tests/test_conditions.py tests/test_state.py tests/test_ingestion.py tests/test_invalidation.py tests/test_runtime_r3.py -q -p no:cacheprovider --tb=short`: **91 passed**, exit 0. These are public/synthetic fixtures; no real study, private cases/gold or assessor keys were read. This is a focused regression selection, not the entire repository suite.
3. Local consecutive-build script runs build.py twice at each of default and explicit SOURCE_DATE_EPOCH=1700000000, separated by more than a second. Both PDF and checksum-file **bytes** match within each pair. Final default artefacts restored. See reproducibility.json for all four exact hash/date receipts.
4. `python -X utf8 -B paper/minimal-protocol/verify.py`: exit 0, four pages, all 59 source blocks present, no out-of-page text or replacement glyphs, both required hashes match, CC-BY-4.0 metadata and unpublished Zenn confirmed. All four rendered pages visually inspected locally.

Default pair, both runs:

- PDF SHA-256: `5411ce4622fcfc28c8bda8ca1d5005bad56a2df21be93edc2b1ff4d113f4c220`
- SHA256SUMS.txt SHA-256: `f2e9716b43f3f23ec2180e5ea71a0ff4bcfa66edbb40c6a4af52b6bc8025e643`

Explicit epoch pair, both runs:

- PDF SHA-256: `67be0ec03ab1fe3484539d912c3a98cee6aea63f7eca9161b8bd5ce73e212b46`
- SHA256SUMS.txt SHA-256: `1277c78b3b8fa8ccd076126be1860c73f637f981b21715c886e93b8abb460180`

Full raw regression failure output and two resolved routing-setup errors are retained locally under ignored rendered/review-fix/all-error-output.txt, together with individual logs. They are not published as they contain machine-specific debug paths. No residual build/verification/test error was observed after the repairs.

Fresh independent bounded code review by Google/Antigravity gemini-3.8-flash-medium returned PASS with no P1/P2 blockers. It independently reran the 10 publication tests and 91 public regressions and checked that empty/tampered checksums fail even with Python optimisation. This accepts the bounded publication-tool/licence repair only, not scientific effectiveness or empirical-study completion. Its actual dispatch is ommatidia-pr3-build-license-review-google-20261021-r1; the complete host receipt is retained locally in rendered/review-fix/independent-review.md. Root cross-checked the actual invariant and checksum exception code rather than accepting reported line offsets as exact.

No comparative experiment, Zenodo submission, GitHub release, main push, force push or merge is performed by these checks. Costs and model token totals are unknown. The original root checkout's dirty recovery work and PR2 README changes are preserved.
