# Ommatidia

[日本語](README.ja.md)

Ommatidia is a research project on how AI agents can inspect their current understanding, identify a potentially unexplored perspective, and direct bounded investigation towards evidence that could change a conclusion.

**Status: research draft. A Python research harness and runtime are implemented and covered by automated tests, but no study trial has been run. No benchmark results or novelty claim have been established.**

The central question is whether evidence-dependent perspective selection improves investigation over ordinary reflection, fixed perspectives, and a single adaptive investigator under the same budget.

## Design direction

1. Represent claims, evidence, assumptions, and unresolved questions separately.
2. Propose a perspective only when its relevance and a discriminating check can be stated.
3. Assign an investigation with a bounded scope, source target, and stopping rule.
4. Track evidence provenance and overlapping sources rather than count agent votes.
5. Update the understanding state and preserve questions that remain unresolved.

TOMBO supplies the conceptual inspection boundary. Ommatidia investigates the additional value of constructing and coordinating investigations from that boundary. TOMBO is currently a design proposal, not an installed dependency.

## Current state

- `src/ommatidia/` contains the research harness and runtime: the understanding state, the executable graph for conditions A to E, evidence provenance and invalidation, a run ledger, campaign-wide trial and cost reservations, dataset and protocol seals, runtime freeze checks, scoring of saved traces, and an injected T3 transport.
- `scripts/run_harness.py` is the runner CLI and `scripts/verify_seals.py` creates and verifies seal manifests.
- `research/datasets/dev/` holds the 24 development cases. Held-out actions are disabled in the runner pending a new approved evaluation package.
- The runtime freeze `research/runtime_freeze_r4.json` records the evaluation package as `blocked_rebuild_required` and zero study trials executed. Cost and token usage remain unmeasured.

## Running the tests

Python 3.10 or later is required. The package has no runtime dependencies; the tests use pytest.

```
pip install -e ".[dev]"
python -m pytest
```

## Start here

- [Research protocol](research/PROTOCOL.md)
- [Evaluation specification](research/EVALUATION_SPEC.md)
- [Design boundaries](docs/DESIGN.md)
- [Runtime and harness architecture](research/runtime-design.md)
- [Japanese manuscript draft](paper/manuscript-ja.md)
- [English manuscript draft](paper/manuscript-en.md)
- [Related work register](references/RELATED_WORK.md)
- [GitHub and Zenodo publication plan](docs/PUBLICATION.md)

The first milestone is a verified related-work comparison and a frozen minimum experimental protocol. A paper reporting results will follow the experiment, including negative results where applicable.

## Publication

GitHub is the working record. A future tagged snapshot can be archived on Zenodo for a persistent DOI, following the [official GitHub guidance](https://docs.github.com/en/repositories/archiving-a-github-repository/referencing-and-citing-content). No Zenodo record or DOI has been created for this project.

A reuse licence and citation metadata will be recorded before the first archival release. Author names and affiliations must be confirmed rather than inferred from account metadata.
