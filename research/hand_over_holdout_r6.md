# R6 replacement held-out package: content-free blind hand-over

Status: candidate. Not ready for release. It needs an independent public-only audit and the separate freeze and runtime release gates. No freeze file, task gate, protocol, specification, runtime code, manuscript, test or earlier-round file was edited. No earlier-round package, hand-over or key was opened while authoring.

## Package

| Item | Value |
| :--- | :--- |
| Package root | `research/datasets/heldout_r6_candidate/` |
| Public packets | 24 (`public_packets/*.json`), domain coverage 8 / 8 / 8 |
| Public source files | 144 (`public_sources/<taskId>/<group>/<doc>.txt`), 3 source groups per packet, 2 files per group |
| Public manifest | `research/holdout_manifest_r6_candidate.json` (168 entries: 24 packets + 144 source files) |
| Public manifest SHA-256 | `5e8f4407e0c6e6724f32c49605c0131f9f5b4bb137499cedc79399fd4dd5160f` |
| Public validator | `research/datasets/heldout_r6_candidate/validate_public.py` |
| Line-ending guard | `research/datasets/heldout_r6_candidate/.gitattributes` (`* -text`), so stored bytes match the manifest hashes |

The public manifest lists only public paths. It carries one opaque commitment hash for the separate private-side manifest. It names no private path, file or ID. Private answer files and a private-side manifest are kept apart from the public tree; their location, names and contents are deliberately not described here.

## Public packet format

Each packet carries every field required by `EVALUATION_SPEC.md` section 3.1 (`taskId`, `domain`, `goal`, `proposedAnswer`, `availableSources`, `budget`), with the budget constants 8 / 12 / 180000 / 48000. It also carries the fields the runtime `TaskPacket` loader requires (`schemaVersion`, `mode`, `successCriteria`, `evidence`, `capabilities`, and `maxRounds`, `maxOutputTokensPerCall`, `maxCostYen` in the budget).

- Task IDs are opaque and were assigned by a seeded shuffle, so ID order carries no information.
- The three `successCriteria` strings, the capability list, the mode and the budget are byte-identical in all 24 packets. They state the requested task, citation format and gap reporting only. They define no verdict and contain no decision rule.
- `evidence` is empty. The runtime step payload forwards `goal`, `evidence`, `capabilities` and the criteria but not `availableSources`, so the source list (group, description, document locator and title) is written into `goal`. `availableSources` is kept for specification conformance.
- Source groups are named `grp1` to `grp3`. Group and document order within a packet was shuffled. Document names are `doc1.txt` and `doc2.txt`.
- Passage rule (also recorded in the manifest): a passage is the complete UTF-8 text of one source file, LF line endings, no trailing newline. Its content hash is the SHA-256 of that text. The public source tool must return exactly this text and hash.
- Every source file uses one header (`Title`, `Recorded`, `Version`, `Scope`) followed by the body. A reference date, 2026-10-01, appears in every goal.

## Source-verification boundary

- All source documents are authored synthetic material, as `PROTOCOL.md` section 5 specifies ("purpose-designed synthetic benchmark cases"). Entities, products, instruments, jurisdictions and dates are invented.
- No external document, URL, standard identifier, citation, section number or quotation is used. No web retrieval was performed, so there is no URL or retrieval date to record.
- Consequently there is no "verified against a current official source" claim. If the study requires real primary-source extracts, that is a different package design and was not attempted.
- The package states no claim about real-world law, software or services.

## Validation (public-only)

Run from the repository root:

```
python research/datasets/heldout_r6_candidate/validate_public.py research/holdout_manifest_r6_candidate.json
```

Result: PASS.

- It loads the packets through `ommatidia.harness.load_public_packets` with hash verification and an expected count of 24.
- It checks unique task IDs, the spec-required fields, the domain enum, the budget constants, 3 groups with 2 documents each, and that every locator named in a goal exists.
- It checks that the manifest lists exactly the public files on disk with matching SHA-256 and size, and that the shared fields are uniform across packets.
- It checks that no evaluator-field names appear in packets and that no cue-token list term (evaluator, label and stratification vocabulary) appears in any public byte.
- It reads, lists and hashes nothing outside `public_packets/`, `public_sources/` and the manifest passed on the command line.
- A separate dry run built the step payloads for all 24 packets under all five conditions with the runtime's own functions. No model was called and no condition was executed. The largest rendered prompt was 5,374 characters, against the 48,000 ceiling, and every payload passed `check_public_payload`.

Private-side validation was run in place by the authorised authoring tooling and reported PASS with aggregate totals only (181 checks, 24 records). Its output printed no IDs, labels or values, and its scope is not described here. A public-only auditor cannot verify hidden stratification, or any answer-side property, from this package, and this document does not claim they can.

## Author and usage

- Author: Claude Sonnet 5.5 (`claude-sonnet-5-5`), Anthropic, run through the Claude Code / Agent SDK harness as a research sub-agent.
- Reasoning effort: no named level was exposed to the author, so none is reported.
- Package-authoring tool use: local file reads (the protocol, the evaluation specification, the packet types and the runtime and manifest loader code), local file writes, and local Python runs for building and validation. No web search or fetch, no external service call.
- Model-call and token totals and cost: not reported by the host to the author; none are asserted. This is the authoring account only.
- Study-run cap: unused. No trial was run and no study-condition model was called. The approved cap (240 trials, 1,920 study model calls) is untouched.

## Known blockers and residual risks for the auditor and the gates

1. Verdict labels (`supported`, `contradicted`, `disputed`, `inconclusive`) are not defined in any public text. This avoids encoding decision rules, but it leaves ordinary-language ambiguity. The auditor should judge whether that is acceptable.
2. The goal lists document titles, and titles are visible to every condition. They were written neutrally, but residual cue risk from titles and from body wording needs independent reading.
3. Scoring credits only evidence that enters the saved state through observation steps, and excludes input evidence. This was read in `scoring.py` but not tested. Conditions that return only a final judgement may therefore earn no critical-item credit. This is a runtime-gate question, not a package property.
4. `seal.hash_file` rejects any path with a private-directory component by design. The runtime's private-answer loader hash verification therefore cannot verify the private-side manifest, and must not be relied on for it. The private-side hashes need an authorised private verifier.
5. The source-tool contract (list a directory, read a text file, return the text with its SHA-256) is assumed. It has not been exercised against a live public-only workspace.
6. Package integrity depends on `.gitattributes` surviving checkout. Any end-of-line rewriting would break the manifest hashes.
7. The protocol-required frozen tag set for the H4 subset exists in the private tree. It still has to be frozen by the separate freeze step, which was not performed.
8. `runtime_freeze_r3.json`, `seal_manifest.json` and `evaluationPackageStatus` were not touched. Nothing here authorises study execution.
