# Fixed-LF checksum follow-up

Target: PR3, devin/20261021-minimal-protocol-preprint, starting at 5bcff29f54082ab4752935b042be9567cca74cd7. Manuscript content, PDF bytes and research protocol are unchanged by this follow-up.

## Correction

The first deterministic-build fix produced identical CRLF checksum files on Windows, but Git committed LF bytes. Therefore the old checksum-file digest f2e971... did not identify the committed file. build.py now explicitly writes UTF-8/LF for SHA256SUMS.txt and generated Zenodo metadata; verify.py does the same for validation.json. The versioned check_reproducibility.py generates LF reproducibility.json directly from the actual build bytes, compares two runs for each timestamp mode and restores default artefacts. No manuscript is generated or modified by this helper.

Current default output digests, identical in both consecutive runs:

- manuscript.pdf: `5411ce4622fcfc28c8bda8ca1d5005bad56a2df21be93edc2b1ff4d113f4c220`
- SHA256SUMS.txt (LF): `5aa797750bde6c98d8936908408c8c0cc0b798289bb155be5b4cea4ba565e64b`

With SOURCE_DATE_EPOCH=1700000000, both runs also match:

- manuscript.pdf: `67be0ec03ab1fe3484539d912c3a98cee6aea63f7eca9161b8bd5ce73e212b46`
- SHA256SUMS.txt (LF): `f5e04d008f4395b23a7a4fa023eb52f882af556c7d1483d95bfb8d4931872fe9`

See reproducibility.json for full per-run records. Dependency/font changes remain outside the same-environment reproducibility guarantee.

## Local checks performed

- Focused RED: `python -X utf8 -B -m pytest tests/test_publication_build.py::test_generated_publication_text_uses_lf_bytes -q -p no:cacheprovider --tb=short --assert=plain` failed as expected (exit1), identifying CR bytes in SHA256SUMS.txt.
- GREEN: `python -X utf8 -B -m pytest tests/test_publication_build.py -q -p no:cacheprovider --tb=short --assert=plain`: 12 passed, exit0. Tests cover LF on generated text, both build modes, required manifest entries and receipt/content hash agreement.
- Existing public/synthetic regression: `python -X utf8 -B -m pytest tests/test_conditions.py tests/test_state.py tests/test_ingestion.py tests/test_invalidation.py tests/test_runtime_r3.py -q -p no:cacheprovider --tb=short`: 91 passed, exit0. No actual held-out/gold/case data or empirical trial is used.
- `python -X utf8 -B paper/minimal-protocol/check_reproducibility.py`: both PDF/manifest byte pairs equal; final default restored.
- `python -X utf8 -B paper/minimal-protocol/verify.py`: exit0, four pages, all59 source blocks present, valid required hashes, CC-BY-4.0 and unpublished article retained.
- Git for Windows sha256sum.exe, `-c SHA256SUMS.txt` in the publication directory: manuscript.md OK; manuscript.pdf OK; exit0.

Root subsequently checks staged/index bytes and a sparse clean checkout of the committed revision before pushing. That post-commit result is a separate acceptance condition; it is not inferred from working-tree checks. Full local command output is retained under ignored rendered/lf-fix. A runner initially used duplicate relative path segments; after correcting the workdir-relative paths all listed commands succeeded.

All delegated roles in this round use codex/gpt-6.1-sol as explicitly requested, so the independent task is a separate same-model review, not a cross-vendor review. Old Claude audit applicability is checked read-only and reported separately; it does not authorise manuscript or statistical changes. Costs/tokens remain unknown. No main push, force push, merge, archival publication or experiment is performed.
