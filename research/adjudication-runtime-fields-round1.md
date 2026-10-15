fail Explicit null and partial-field TaskPackets are accepted although the public schema requires both fields; a synthetic in-memory probe reproduced the mismatch.

# R1 review adjudication: TaskPacket input contract

The independent Gemini R1 report returned pass. Parent follow-up found a contract hole the report did not identify. This adjudication supersedes that pass for the field-presence requirement; the original report is retained at research/review-runtime-fields-round1.md.

## Reproduction

A synthetic in-memory TaskPacket was built from the repository mechanism fixture. Four variants were passed to TaskPacket.from_dict: domain set to null, availableSources set to null, domain present with availableSources absent, and availableSources present with domain absent. All four were accepted.

No held-out/private files were opened, listed, hashed or queried. This used no trial data, scoring, or model calls.

## Required correction

EVALUATION_SPEC.md section 3.1 requires both domain and availableSources, with domain from the declared enum and availableSources an array. Compatibility may retain both keys absent for legacy/dev packets. If either key is present, both must be present and non-null with valid shapes. Explicit null must not be treated as key absence.

Round-2 implementation and independent verification are pending. The runtime freeze remains unchanged and blocked. No experiment has run.
