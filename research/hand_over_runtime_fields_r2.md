# Runtime TaskPacket fields: implementation hand-over (round 2)

Status: repair of the R1 spec defect; independent cross-vendor verification required. R1's pass is superseded. Not release-ready; no live trials authorised.

## Change
- `src/ommatidia/types.py`: `domain` and `availableSources` are now both-or-neither.
  - Both keys absent -> both `None`, no defaults (legacy/dev packets).
  - Either key present -> both required; explicit null on either rejected; domain must be in the spec enum; availableSources must be an array of objects with string `sourceGroup`/`description`/`entryLocator`.
  - `TaskPacket.__post_init__` also rejects a half-set pair on direct construction.
  - Empty list is valid and round-trips; empty strings are accepted (EVALUATION_SPEC §3.1 sets no minLength).
- `src/ommatidia/runtime.py`: unchanged this round (payload forwarding for A-E and public-path guard already correct).
- `tests/test_task_packet_fields.py`: 28 tests (null pairs, partial pairs, invalid values/shapes, legacy absent-both, valid round-trip incl. empty list, direct construction, five-condition payloads, public guard).

## Validation
- `python -B -m pytest tests/test_task_packet_fields.py -q -p no:cacheprovider` -> exit 0, 28 passed.
- Full suite NOT run: runtime_freeze_r3 codeHash is stale (R1: 46 failed/73 passed). Freeze not modified or bypassed; full-suite gate remains UNRESOLVED and needs a reviewed freeze update after cross-vendor verification.
- No trials, study conditions, or private/held-out data used. No commit/push.
