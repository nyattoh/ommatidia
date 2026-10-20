# Runtime freeze R4 handover

Status: verification candidate only. The replacement evaluation package is still blocked; no study trial or study-condition model call was made.

## Purpose

R3's `historicalCore` records the source hashes that were current when R3 was created and its verifier requires those files to remain byte-identical. The TaskPacket repair changed `src/ommatidia/types.py`, so an R3-derived candidate cannot both verify the current runtime and retain that old hash as the current R4 core. R4 therefore records its own current core hashes in `historicalCore`, and retains the R3 values under `supersededHistoricalCore`. R3 itself is unchanged.

R4 also records the superseded R3 `history` under `supersededHistory`; its active `history` fingerprints the current sealed manifests. This records the transition without changing R3's historical claims.

## Current gate state

- R4 status: `blocked_rebuild_required`.
- Study trials recorded: 0.
- Model-call totals, token totals and cost: unknown; this work made no study-condition calls.
- R4's `baseCommit` is the current HEAD used for verification. The working tree is dirty, so this is not a release freeze and cannot satisfy the clean committed execution gate.
- The public-only R6 candidate passed a public-material audit, but that audit did not approve live execution or certify hidden-side properties.
- Live execution remains blocked until a trusted public-only source workspace and dispatcher enforce a single model invocation per step, per-step limits, cancellation and verifiable host usage. The current T3 adapter's attestation is an injected contract, not a production controller.

## Verification

From the repository root:

```powershell
python -B scripts/verify_seals.py verify --runtime-freeze research/runtime_freeze_r4.json
# Passed. Current code, prompts, graph and specification fingerprints matched;
# the seal verifier also reported protocol, evaluation specification and public dataset manifests OK.

python -B -m pytest -q -p no:cacheprovider
# 129 passed.
```

The experiment was not run. R4 is a candidate verification record only; it is not approval to run dev or held-out study trials and is not a claim of empirical findings.

## Next gate

Implement and independently verify an isolated public-only source/controller path with hard invocation and usage accounting. Then prepare a clean committed R4 release candidate and complete the separate replacement-package approval gate before using any of the authorised 240 trials / 1,920-call ceiling.
