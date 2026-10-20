pass

# Ommatidia TaskPacket Runtime Schema & Payload Verification (Round 2)

**Reviewer Model:** gemini-3.8-flash-high (Antigravity harness, host_default)  
**Implementation Author:** Claude Sonnet 5.5  
**Review Type:** Independent Cross-Vendor Contract Verification (Round 2)  
**Scope:** Verification of repaired TaskPacket `domain` and `availableSources` contract (paired presence, explicit null rejection, partial pair rejection, direct construction validation, schema boundaries, payload forwarding).  
**Adjudication Reference:** [adjudication-runtime-fields-round1.md](file:///d:/develop/works/ommatidia/research/adjudication-runtime-fields-round1.md)  
**Hand-Over Reference:** [hand_over_runtime_fields_r2.md](file:///d:/develop/works/ommatidia/research/hand_over_runtime_fields_r2.md)  
**Evaluated Artifacts:**
- [`src/ommatidia/types.py`](file:///d:/develop/works/ommatidia/src/ommatidia/types.py)
- [`src/ommatidia/runtime.py`](file:///d:/develop/works/ommatidia/src/ommatidia/runtime.py)
- [`tests/test_task_packet_fields.py`](file:///d:/develop/works/ommatidia/tests/test_task_packet_fields.py)
- [`research/EVALUATION_SPEC.md`](file:///d:/develop/works/ommatidia/research/EVALUATION_SPEC.md) (§3.1 schema specification)
- [`research/runtime_freeze_r3.json`](file:///d:/develop/works/ommatidia/research/runtime_freeze_r3.json)

---

## 1. Executive Summary

The round-2 repair addressing the TaskPacket field contract defect identified in round-1 adjudication passes verification. 

Key verified contract behaviors:
1. **Paired Field Presence / Rejection of Partial Pairs:** Both fields must be absent together (legacy/dev packets) or present together. Specifying one field without the other is strictly rejected during parsing (`TaskPacket.from_dict`) and direct dataclass instantiation (`TaskPacket.__post_init__`).
2. **Rejection of Explicit Nulls:** Explicit `null` values for `domain`, `availableSources`, or both are strictly rejected and not conflated with field absence.
3. **Exact Schema Adherence:** `domain` is restricted to the 3-value enum defined in `EVALUATION_SPEC.md` §3.1 (`"software_engineering"`, `"workflow_automation"`, `"document_research"`). `availableSources` items require string fields (`sourceGroup`, `description`, `entryLocator`). Empty strings are accepted because the specification defines no `minLength` constraint. An empty array (`[]`) for `availableSources` is valid and preserves as an array.
4. **Step Payload Forwarding & Public Guard:** Payloads across all conditions (A through E) carry `domain` and `availableSources` when set on the packet. The recursive `check_public_payload` validator continues to inspect `availableSources` and reject evaluator keys or private path locators (`/gold/`, `/cases/`, `unblinding_key.json`).
5. **Focused Test Execution:** All 28 focused unit tests in `tests/test_task_packet_fields.py` pass cleanly (`28 passed in 0.08s`).

**Boundary and Gate Notice:** 
This verification passes the narrow TaskPacket parser/serializer/payload contract only. The unchanged `research/runtime_freeze_r3.json` remains active. The full repository test suite is non-green (implementer reported 46 failed, 73 passed due to frozen `codeHash` mismatch) and was not run to protect freeze integrity. Release-ready status is **not** set, and no live model trials or study executions are authorised.

---

## 2. Checkpoint Verification Details

### Check 1: Legacy / Dev State Field Absence Preservation
- **Location:** [`src/ommatidia/types.py#L396-L397`](file:///d:/develop/works/ommatidia/src/ommatidia/types.py#L396-L397), [`src/ommatidia/types.py#L429-L432`](file:///d:/develop/works/ommatidia/src/ommatidia/types.py#L429-L432), [`src/ommatidia/types.py#L445-L450`](file:///d:/develop/works/ommatidia/src/ommatidia/types.py#L445-L450); [`src/ommatidia/runtime.py#L111-L114`](file:///d:/develop/works/ommatidia/src/ommatidia/runtime.py#L111-L114).
- **Mechanism:**
  - `TaskPacket` defaults `domain` and `available_sources` to `None`.
  - When neither key is present in `data`, `has_domain == False` and `has_sources == False`. The absence condition is satisfied.
  - In `to_dict()`, lines 429–432 conditionally append `"domain"` and `"availableSources"` only when `not None`. Absent keys are never emitted, and no default placeholder values (e.g. `""` or `[]`) are invented.
  - In `step_payload()`, lines 111–114 omit `"domain"` and `"availableSources"` if `task.domain is None`.
- **Test:** [`tests/test_task_packet_fields.py#L32-L41`](file:///d:/develop/works/ommatidia/tests/test_task_packet_fields.py#L32-L41) (`test_legacy_packet_loads_without_inventing_fields`) verifies that omitted fields remain absent in `TaskPacket`, `to_dict()`, and `step_payload()`.

### Check 2: Explicit Null Rejection and Paired Presence
- **Location:** [`src/ommatidia/types.py#L445-L456`](file:///d:/develop/works/ommatidia/src/ommatidia/types.py#L445-L456).
- **Mechanism:**
  ```python
  has_domain, has_sources = "domain" in data, "availableSources" in data
  if has_domain != has_sources:
      raise ValueError(
          "TaskPacket domain and availableSources must both be present or both absent"
      )
  sources = data.get("availableSources")
  if has_sources:
      if data["domain"] is None or sources is None:
          raise ValueError(
              "TaskPacket domain and availableSources must not be null"
          )
      if not isinstance(sources, list):
          raise ValueError("TaskPacket.availableSources must be an array")
  ```
  - If one field is provided and the other omitted (`has_domain != has_sources`), `ValueError` is raised immediately.
  - If either field is present with an explicit `None`/`null` (`data["domain"] is None or sources is None`), `ValueError` is raised.
  - When both are present and valid, non-null fields round-trip cleanly via `to_dict()` and `from_dict()`.
- **Tests:** [`tests/test_task_packet_fields.py#L24-L29`](file:///d:/develop/works/ommatidia/tests/test_task_packet_fields.py#L24-L29) (`test_roundtrip_preserves_fields`) and [`tests/test_task_packet_fields.py#L51-L81`](file:///d:/develop/works/ommatidia/tests/test_task_packet_fields.py#L51-L81) (`test_invalid_shapes_rejected`) exhaustively test both `None`, single `None`, single present, and malformed inputs.

### Check 3: Direct Construction Pair Validation
- **Location:** [`src/ommatidia/types.py#L406-L409`](file:///d:/develop/works/ommatidia/src/ommatidia/types.py#L406-L409).
- **Mechanism:**
  ```python
  if (self.domain is None) != (self.available_sources is None):
      raise ValueError(
          "TaskPacket.domain and availableSources must be set together"
      )
  ```
  - Direct instantiation of `TaskPacket(..., domain="document_research", available_sources=None)` or `TaskPacket(..., domain=None, available_sources=[...])` fails with `ValueError`.
- **Test:** [`tests/test_task_packet_fields.py#L90-L95`](file:///d:/develop/works/ommatidia/tests/test_task_packet_fields.py#L90-L95) (`test_direct_construction_requires_both_fields`) verifies that calling `dataclasses.replace` with either half-set pair raises `ValueError`.

### Check 4: Schema Adherence & Boundary Requirements
- **Location:** [`src/ommatidia/types.py#L352`](file:///d:/develop/works/ommatidia/src/ommatidia/types.py#L352), [`src/ommatidia/types.py#L355-L380`](file:///d:/develop/works/ommatidia/src/ommatidia/types.py#L355-L380), [`src/ommatidia/types.py#L410-L416`](file:///d:/develop/works/ommatidia/src/ommatidia/types.py#L410-L416); [`research/EVALUATION_SPEC.md#L94-L123`](file:///d:/develop/works/ommatidia/research/EVALUATION_SPEC.md#L94-L123).
- **Mechanism:**
  - `TASK_DOMAINS` defines `("software_engineering", "workflow_automation", "document_research")`. Any other string, empty string, or non-string domain raises `ValueError`.
  - In `AvailableSource`, `source_group`, `description`, and `entry_locator` are strictly required to be `isinstance(..., str)`. Empty strings (`""`) are valid because §3.1 defines no `minLength` for these properties.
  - `availableSources` is an array; empty list `[]` is schema-valid (no `minItems` in §3.1) and round-trips as an empty list rather than absent or `None`.
- **Tests:** 
  - [`tests/test_task_packet_fields.py#L44-L48`](file:///d:/develop/works/ommatidia/tests/test_task_packet_fields.py#L44-L48) (`test_empty_sources_is_present_not_absent`)
  - [`tests/test_task_packet_fields.py#L84-L87`](file:///d:/develop/works/ommatidia/tests/test_task_packet_fields.py#L84-L87) (`test_empty_strings_in_source_items_are_schema_valid`)

### Check 5: Step Payload Attachment Across Conditions A–E and Public-Path Guard
- **Location:** [`src/ommatidia/runtime.py#L75-L92`](file:///d:/develop/works/ommatidia/src/ommatidia/runtime.py#L75-L92), [`src/ommatidia/runtime.py#L111-L122`](file:///d:/develop/works/ommatidia/src/ommatidia/runtime.py#L111-L122).
- **Mechanism:**
  - `step_payload` attaches `"domain"` and `"availableSources"` when present on `task`.
  - At line 122, `check_public_payload(payload)` recursively checks the entire dictionary, sub-dictionaries, and list elements.
  - Forbidden evaluator keys (`gold`, `groundtruthverdicts`, `criticalevidencehashes`, `targetdecision`, `answerkey`, `unblindingkey`, `requiredgapquestions`) and private path substrings (`/gold/`, `/cases/`, `unblinding_key.json`) are blocked with `ValueError`.
- **Tests:**
  - [`tests/test_task_packet_fields.py#L98-L108`](file:///d:/develop/works/ommatidia/tests/test_task_packet_fields.py#L98-L108) (`test_every_condition_payload_carries_fields`) verifies that every step across all 5 conditions (`A`, `B`, `C`, `D`, `E`) attaches the fields and passes `render_prompt`.
  - [`tests/test_task_packet_fields.py#L111-L125`](file:///d:/develop/works/ommatidia/tests/test_task_packet_fields.py#L111-L125) (`test_public_guard_still_rejects_private_locator_in_sources`) verifies that private locator strings embedded in `availableSources` trigger `ValueError`.

### Check 6: Focused Test Execution
- **Command:**
  ```bash
  python -B -m pytest tests/test_task_packet_fields.py -q -p no:cacheprovider
  ```
- **Output:**
  ```
  ............................                                             [100%]
  28 passed in 0.08s
  ```
- **Exit Code:** 0.

---

## 3. Scope Boundaries & Unresolved Release Gates

1. **Focused Test Isolation:** The 28 passing unit tests represent narrow synthetic unit tests only.
2. **Runtime Freeze Intact:** `research/runtime_freeze_r3.json` remains unaltered (`codeHash`: `67916037000453ca273fab0e684afc53f95a624ecbd735b1debcb7b3753cdc9f`). Modifying `src/ommatidia/types.py` leaves the full repository test suite non-green until an approved freeze update occurs.
3. **Zero Inspection & Boundary Compliance:** No held-out datasets, gold files, private manifests, or unblinding keys were inspected, listed, read, or modified.
4. **No Model Trials:** No live model trials, study executions, or study budget consumption occurred or were authorised.
5. **Separate Unresolved Gates:**
   - Formal re-freeze and full test suite verification.
   - Public-only source tool live connection and runtime sandbox boundary controller.
   - Host-enforced trial call/tool budgets and exact usage accounting.
