# Runtime TaskPacket fields: implementation hand-over (round 1)

Status: partial implementation; independent review requested for the scoped code changes. This does not authorise live trials or mark the runtime release-ready.

## Scope

- src/ommatidia/types.py: added validated optional domain and availableSources fields, preserving absence for legacy/dev packets.
- src/ommatidia/runtime.py: forwards both fields as structured payload fields when present.
- tests/test_task_packet_fields.py: added synthetic in-memory schema, round-trip, legacy, five-condition payload, and public-path guard checks.

No candidate data, manifests, freeze, seal, protocol, specification, scoring, transport, or manuscript were changed by this implementation task. No held-out/private data or model trials were used.

## Validation

- python -B -m pytest tests/test_task_packet_fields.py -q -p no:cacheprovider — exit 0, 18 passed (also rerun by the parent).
- Full repository command reported by the implementer: python -B -m pytest -q -p no:cacheprovider — exit 1, 46 failed, 73 passed. Forty-five failures report the unchanged runtime-freeze codeHash mismatch; one additional output assertion failed in the same run.
- The freeze was not bypassed or edited. Full-suite status is unresolved pending a reviewed, correctly versioned freeze update.

## Remaining gates

The independent review must assess the changed parser/serializer and payload contract. A public-only source reader, host-enforced call/tool budgets, exact usage accounting, clean committed release, and the blocked runtime freeze remain separate gates. No experiment or scoring has run.
