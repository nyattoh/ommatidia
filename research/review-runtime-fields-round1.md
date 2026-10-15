pass

# Ommatidia TaskPacket Runtime Schema & Payload Verification (Round 1)

**Reviewer Model:** gemini-3.8-flash-high (Antigravity harness, host_default)  
**Implementation Author:** Claude Sonnet 5.5  
**Review Type:** Independent Cross-Vendor Contract Verification  
**Scope:** Narrow runtime schema and payload repair for `domain` and `availableSources` fields.  
**Evaluated Artifacts:**
- `src/ommatidia/types.py`
- `src/ommatidia/runtime.py`
- `tests/test_task_packet_fields.py`
- `research/hand_over_runtime_fields_r1.md`
- `research/EVALUATION_SPEC.md` (Section 3.1 schema specification)
- `research/runtime_freeze_r3.json` (frozen boundary reference)

---

## 1. Executive Summary

The narrow runtime schema repair addressing the dropped `TaskPacket.domain` and `TaskPacket.availableSources` fields passes verification. The parser and serializer in `src/ommatidia/types.py` strictly validate the three allowed domain enum values and the item field types of `availableSources`. Spec-conformant packets preserve both fields through `from_dict`/`to_dict`, and legacy packets preserve field absence without inventing default values. All condition step payloads in `src/ommatidia/runtime.py` attach both fields when present and enforce recursive public-path and evaluator-field checks. Focused synthetic tests pass cleanly (18/18).

**Crucial Gate Notice:** This verification is strictly limited to the narrow code contract. The unchanged `research/runtime_freeze_r3.json` remains active and unbypassed; the full test suite remains non-green (reported 46 failed, 73 passed due to frozen code hash mismatch). This review does not signal release readiness, does not authorise live trials or model calls, and leaves public source tool binding, budget enforcement, and accounting gates separate and unresolved.

---

## 2. Checkpoint Verification Details

### Check 1: Validation of Allowed Domains and `availableSources` Types
- **Domain Validation:**
  - `src/ommatidia/types.py#L417`: `TASK_DOMAINS = ("software_engineering", "workflow_automation", "document_research")` exactly matches `research/EVALUATION_SPEC.md` Section 3.1 enum definition.
  - `src/ommatidia/types.py#L452-L453`: `TaskPacket.__post_init__` checks `if self.domain is not None and self.domain not in TASK_DOMAINS: raise ValueError(...)`. Non-matching domain strings, integers, or empty strings are rejected.
- **Available Sources Structure and Type Validation:**
  - `src/ommatidia/types.py#L420-L438`: `AvailableSource` dataclass encapsulates source group entries.
  - `src/ommatidia/types.py#L425-L428`: `__post_init__` enforces that `source_group`, `description`, and `entry_locator` are strictly `isinstance(..., str)`.
  - `src/ommatidia/types.py#L433-L438`: `from_dict` validates that items are `dict` objects and require all three keys (`sourceGroup`, `description`, `entryLocator`).
  - `src/ommatidia/types.py#L454-L457`: `TaskPacket.__post_init__` validates that `available_sources` is a list of `AvailableSource` instances.
  - `src/ommatidia/types.py#L481-L483`: `TaskPacket.from_dict` rejects any non-list `availableSources` input with `ValueError("TaskPacket.availableSources must be an array")`.

### Check 2: Preservation of Absent Fields vs. Spec-Conformant Round-Trip
- **Absence Preservation (Legacy/Dev Packets):**
  - `src/ommatidia/types.py#L449-L450`: Default values for `domain` and `available_sources` are `None`.
  - `src/ommatidia/types.py#L474-L477`: `to_dict` conditionally includes fields:
    ```python
    if self.domain is not None:
        result["domain"] = self.domain
    if self.available_sources is not None:
        result["availableSources"] = self.sources_dict()
    ```
    When fields are `None`, neither key is emitted. No default values (such as `""` or `[]`) are invented.
  - `tests/test_task_packet_fields.py#L31-L39`: `test_legacy_packet_loads_without_inventing_fields` asserts that omitted fields remain absent in `TaskPacket`, `to_dict()`, and `step_payload()`.
- **Conformant Round-Trip:**
  - When present, `TaskPacket.from_dict(data).to_dict()` outputs exact identical values for `domain` and `availableSources` (`tests/test_task_packet_fields.py#L23-L28`).
  - `tests/test_task_packet_fields.py#L42-L46`: Explicit empty list `availableSources: []` preserves `[]` in `to_dict()` rather than being dropped or treated as `None`.

### Check 3: Condition Step Payloads and Public-Path Guard
- **Payload Attachment:**
  - `src/ommatidia/runtime.py#L107-L110`: `step_payload` dynamically attaches `domain` and `availableSources` to the step payload when present on the task packet.
  - `tests/test_task_packet_fields.py#L77-L87`: `test_every_condition_payload_carries_fields` iterates across all 5 conditions (`ConditionType.A` through `ConditionType.E`) and verifies every step in `condition_graph(condition)` includes both `domain` and `availableSources`.
- **Public-Path Guard Retention:**
  - `src/ommatidia/runtime.py#L68-L87`: `check_public_payload` recursively traverses all nested dictionaries, lists, and strings in the payload. It rejects forbidden evaluator keys (`gold`, `groundtruthverdicts`, `criticalevidencehashes`, `targetdecision`, `answerkey`, `unblindingkey`, `requiredgapquestions`) and private path fragments (`/gold/`, `/cases/`, `unblinding_key.json`).
  - `src/ommatidia/runtime.py#L122`: `check_public_payload(payload)` is called at the end of `step_payload`.
  - `tests/test_task_packet_fields.py#L90-L106`: `test_public_guard_still_rejects_private_locator_in_sources` verifies that a private locator in `availableSources` triggers `ValueError("Private locator in public payload")`.

### Check 4: Test Coverage and Gap Assessment
- **Tested Malformed Cases (`tests/test_task_packet_fields.py#L49-L74`):**
  - Invalid domain string (`"other"`) -> rejected.
  - Invalid domain type (`3`) -> rejected.
  - Empty domain string (`""`) -> rejected.
  - String instead of array for `availableSources` (`"x"`) -> rejected.
  - Dict instead of array (`{"sourceGroup": "g"}`) -> rejected.
  - Array of strings instead of objects (`["x"]`) -> rejected.
  - Missing required key in item (`entryLocator` omitted) -> rejected.
  - Null value for required item field (`entryLocator: None`) -> rejected.
  - Non-string field in item (`sourceGroup: 1`) -> rejected.
- **Compatibility & Gap Analysis:**
  - *Top-level explicit null:* `data.get("domain")` when `domain: None` results in `None`, which behaves identically to an absent key. While not explicitly parameterized in `test_invalid_shapes_rejected`, this is compatible with standard Python/JSON deserialization where explicit `null` maps to field absence (`None`).
  - *Partial field pairs:* In `test_invalid_shapes_rejected`, `bad = {"domain": "other"}` and `bad = {"availableSources": "x"}` implicitly exercise partial pairs (one field present while the other is popped). Both fields operate independently as optional dataclass attributes, providing backward compatibility for dev/legacy fixtures while enforcing full conformant shapes on new packets.

### Check 5: Focused Test Execution
- Executed command:
  ```bash
  python -B -m pytest tests/test_task_packet_fields.py -q -p no:cacheprovider
  ```
- Result: **18 passed in 0.07s** (exit code 0).
- As instructed, the full test suite was **not** run or bypassed, respecting the stale frozen `codeHash`.

### Check 6: Full Suite and Runtime Freeze Status
- `research/runtime_freeze_r3.json` records:
  - `src/ommatidia/types.py`: `1052b5e6e415e5c1d2d6bb0ab6bde8378e6e2bb3d18638381edebdaad0c22571`
  - `src/ommatidia/runtime.py`: `1c44dd5c483dedffa9bae79032bd7cb65e688f3b23e27aade776b5c94d0d7653`
  - Overall `codeHash`: `67916037000453ca273fab0e684afc53f95a624ecbd735b1debcb7b3753cdc9f`
- Modifying `types.py` and `runtime.py` causes the integrity checks across tests checking the frozen boundary to fail. The full suite was reported by the implementer as 46 failed, 73 passed (45 failures from unchanged runtime freeze codeHash mismatch, plus one cascading assertion).
- The runtime freeze was neither modified nor bypassed. A versioned freeze update remains a prerequisite for full-suite resolution.

---

## 3. Verification Limits and Boundary Integrity

1. **Zero-Inspection & Boundary Compliance:** No held-out candidates, gold files, private manifests, or unblinding keys were accessed, listed, or read.
2. **No Model Trials:** No live model trials or empirical study calls were executed or authorised.
3. **Separate Downstream Gates:**
   - Package re-freeze (`runtime_freeze_r4` or equivalent) and clean full test suite pass.
   - Live public-source tool integration and isolation.
   - Host-enforced trial call/tool budgets and exact usage accounting.
