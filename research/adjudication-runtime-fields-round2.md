needs_review R2 report line references for TaskPacket do not match the current checkout; parent readback and the focused test confirm the round-2 contract behavior.

# R2 review adjudication: locator correction

The Gemini R2 review artifact is retained at research/review-runtime-fields-round2.md and returned pass for the focused code contract. Its stated TaskPacket line references (in the 300s–400s) are stale relative to the current checkout.

Current symbol locations in this checkout:
- TASK_DOMAINS and AvailableSource: src/ommatidia/types.py lines 707 and 711.
- TaskPacket and __post_init__: src/ommatidia/types.py lines 739 and 754.
- TaskPacket.from_dict: src/ommatidia/types.py line 799.
- step_payload: src/ommatidia/runtime.py line 114.
- Focused synthetic tests: tests/test_task_packet_fields.py.

Parent independently read the current parser, ran four in-memory null/partial variants after R1, inspected the R2 implementation, and reran the focused test file: 28 passed. The R2 implementation rejects both-null, either-null and partial pairs; both absent remains valid for legacy/dev packets. The reviewer’s pass is retained for behavior, with locator accuracy corrected here.

The full suite remains unresolved under the unchanged stale freeze. No trials ran and no release-ready status is asserted.
