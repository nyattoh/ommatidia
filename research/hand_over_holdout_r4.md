# Ommatidia Replacement Held-Out Evaluation Package Candidate (Hand-Over R4)

**Document Version:** 1.0.0-candidate  
**Date:** 2026-10-15  
**Author / Role:** Research Sub-agent (Data Author)  
**Language:** British English (conforming to repository guidelines)  
**Model & Provider:** `gemini-3.8-flash-high`, provider `antigravity` (agy), reasoning effort `host_default` (no effort option exposed by host catalogue; no coding-verify ledger claims)  
**Resource Expenditure:** Cost and token usage unknown (`null`), as host harness does not meter proprietary subscription billing  
**Status:** Complete. 24 Replacement Held-Out Candidate Cases Authored, Structurally Validated, and Sealed in Candidate Manifests. Package status: `candidate_rebuild` (not production-ready, not frozen into runtime freeze). Zero study trials or research output executed.  

---

## 1. Executive Summary & Context

Following the independent Round 4 code review (`research/review-runtime-round4.md`), which approved runtime remediation R3 with a `pass` verdict, empirical study execution remained gated on the construction of a clean replacement held-out evaluation package. The historical held-out package (`research/datasets/heldout/`) was compromised by an unblinded programmatic read during a prior Round 2 reviewer process (though values were reportedly not displayed or transmitted). 

In strict adherence to the pre-registration protocol and zero-inspection rules:
1. **Preservation of Historical Assets:** The old held-out dataset under `research/datasets/heldout/`, existing gold files, case files, and historical freeze manifests were preserved byte-for-byte and never opened, read, printed, or modified.
2. **Zero Old Answer Inspection:** The replacement package was authored completely de novo without inspecting, querying, or parsing old answer values or private keys.
3. **New Candidate Location:** All candidate artifacts are versioned exclusively under `research/datasets/heldout_r4_candidate/` and `research/holdout_manifest_r4_candidate.json`.
4. **Data Author Scope:** This task is strictly data authoring and structural validation. No trials were evaluated, no experiment models were invoked, no runtime code was altered, old manifests were left untouched, and no commit, push, or publication was performed.

---

## 2. Directory Layout and File Inventory

The candidate package resides entirely under `research/datasets/heldout_r4_candidate/`:

```
research/datasets/heldout_r4_candidate/
├── cases/                     # 24 Composite Case JSONs (TaskPacket + GoldStandard)
│   ├── heldout_r4_se_01.json ... heldout_r4_se_08.json   (Software Engineering: 8 cases)
│   ├── heldout_r4_wa_01.json ... heldout_r4_wa_08.json   (Workflow Automation: 8 cases)
│   └── heldout_r4_dr_01.json ... heldout_r4_dr_08.json   (Document Research: 8 cases)
├── public_packets/            # 24 Agent-Visible TaskPackets (Zero gold leakage)
│   ├── heldout_r4_se_01.json ... heldout_r4_se_08.json
│   ├── heldout_r4_wa_01.json ... heldout_r4_wa_08.json
│   └── heldout_r4_dr_01.json ... heldout_r4_dr_08.json
├── gold/                      # 24 Evaluator-Only GoldStandard Rubrics (Strictly isolated)
│   ├── heldout_r4_se_01.json ... heldout_r4_se_08.json
│   ├── heldout_r4_wa_01.json ... heldout_r4_wa_08.json
│   └── heldout_r4_dr_01.json ... heldout_r4_dr_08.json
├── evidence/                  # 30 Deterministic Synthetic Evidence Documents
│   ├── software_engineering/  # 10 documents (.md, .c, .py specifications and stubs)
│   ├── workflow_automation/   # 10 documents (.md, .yaml, .py, .json integration guides and logs)
│   └── document_research/     # 10 documents (.md statutory texts, license clauses, standards)
└── manifest.json              # Cryptographic SHA-256 seal manifest (102 hashed files)
```

In addition, the top-level candidate manifest is stored at:
`research/holdout_manifest_r4_candidate.json`

---

## 3. Stratification, Paired Design, and Balanced Controls

The candidate package establishes an exact $N_{\text{heldout}} = 24$ denominator adhering strictly to `PROTOCOL.md` §5 and `EVALUATION_SPEC.md` §2:

### 3.1 Domain Distribution
- **Software Engineering (`software_engineering`):** 8 cases (`heldout_r4_se_01` to `heldout_r4_se_08`)
- **Workflow Automation (`workflow_automation`):** 8 cases (`heldout_r4_wa_01` to `heldout_r4_wa_08`)
- **Document & Policy Research (`document_research`):** 8 cases (`heldout_r4_dr_01` to `heldout_r4_dr_08`)

### 3.2 Target Verdict Balance
Across the 24 cases, target verdicts are partitioned evenly:
- `supported`: 6 cases (2 SE, 2 WA, 2 DR)
- `contradicted`: 6 cases (2 SE, 2 WA, 2 DR)
- `disputed`: 6 cases (2 SE, 2 WA, 2 DR)
- `inconclusive`: 6 cases (2 SE, 2 WA, 2 DR)

### 3.3 Balanced Negative Controls
Each domain includes the 4 protocol-specified negative controls:
- **Control Type 1 (Sufficient Initial State / No-Op):** Cases `02` (`heldout_r4_se_02`, `heldout_r4_wa_02`, `heldout_r4_dr_02`). The initial draft is already complete and accurate; any additional probe finding spurious fatal flaws is penalized. Target: `supported`, Decision: `ready_for_requested_step`.
- **Control Type 2 (Capability Limit / Unresolvable Abstention):** Cases `07` (`heldout_r4_se_07`, `heldout_r4_wa_07`, `heldout_r4_dr_07`). Decisive evidence is withheld/unavailable (e.g. truncated buffer, 503 gateway outage, redacted arbitration record); requires explicit abstention. Target: `inconclusive`, Decision: `blocked`.
- **Control Type 3 (Superficially Plausible Distractor):** Cases `08` (`heldout_r4_se_08`, `heldout_r4_wa_08`, `heldout_r4_dr_08`). Contains superficial distractors while formal governing declarations are withheld; requires calibrated abstention. Target: `inconclusive`, Decision: `blocked`.
- **Control Type 4 (Genuine Irresolvable Conflict):** Cases `06` (`heldout_r4_se_06`, `heldout_r4_wa_06`, `heldout_r4_dr_06`). Two authoritative standards directly conflict without an overriding tie-break; requires calibrated resolution. Target: `disputed`, Decision: `needs_user_input`.

### 3.4 H4 Belief Revision Tag Set
In accordance with `EVALUATION_SPEC.md` §5.2, exactly 12 cases are tagged for the paired H4 hypothesis test (Condition E vs Condition B on counterexample cases). These correspond to cases `03`, `04`, `05`, `06` in each domain:
- Software Engineering: `heldout_r4_se_03`, `heldout_r4_se_04`, `heldout_r4_se_05`, `heldout_r4_se_06`
- Workflow Automation: `heldout_r4_wa_03`, `heldout_r4_wa_04`, `heldout_r4_wa_05`, `heldout_r4_wa_06`
- Document Research: `heldout_r4_dr_03`, `heldout_r4_dr_04`, `heldout_r4_dr_05`, `heldout_r4_dr_06`

---

## 4. Primary Technical Sources & Verification Status

In compliance with repository standards (`AGENTS.md`) and pre-registration rules, every technical scenario grounds on verified public specifications, standards, or RFCs. Evidence documents are purpose-designed synthetic representations bearing the required header:  
`[FICTIONAL TEST DATASET - NOT REAL ENTITY OR OPERATIONAL RECORD]`  
No personal identities, real corporate accounts, proprietary API tokens, or actual regulatory entities are included.

| Case ID | Domain | Technical Standard / Topic | Primary Source URL | Verification Status |
| :--- | :--- | :--- | :--- | :--- |
| `heldout_r4_se_01` | Software Engineering | Python asyncio.TaskGroup exception cancellation | `https://docs.python.org/3/library/asyncio-task.html#asyncio.TaskGroup` | Verified |
| `heldout_r4_se_02` | Software Engineering | RFC 9110 §10.2.7 Retry-After header syntax | `https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.7` | Verified |
| `heldout_r4_se_03` | Software Engineering | ISO/IEC 9899:2011 (C11) §7.17.3 Memory Barriers | `https://en.cppreference.com/w/c/atomic/memory_order` | Verified |
| `heldout_r4_se_04` | Software Engineering | POSIX.1-2017 fork() multi-threading specification | `https://pubs.opengroup.org/onlinepubs/9699919799/functions/fork.html` | Verified |
| `heldout_r4_se_05` | Software Engineering | SQLite Write-Ahead Logging (WAL) concurrency | `https://www.sqlite.org/wal.html` | Verified |
| `heldout_r4_se_06` | Software Engineering | Git Commit-Graph Generation Numbers (v1 vs v2) | `https://git-scm.com/docs/commit-graph` | Verified |
| `heldout_r4_se_07` | Software Engineering | Linux epoll(7) edge-triggered starvation | `https://man7.org/linux/man-pages/man7/epoll.7.html` | Verified |
| `heldout_r4_se_08` | Software Engineering | Python PEP 484 Type System variance (List[T]) | `https://peps.python.org/pep-0484/#covariance-and-contravariance` | Verified |
| `heldout_r4_wa_01` | Workflow Automation | RFC 6749 §10.4 OAuth 2.0 refresh token rotation | `https://www.rfc-editor.org/rfc/rfc6749#section-10.4` | Verified |
| `heldout_r4_wa_02` | Workflow Automation | RFC 7519 §4.1.4 JWT expiration claim (exp) | `https://www.rfc-editor.org/rfc/rfc7519#section-4.1.4` | Verified |
| `heldout_r4_wa_03` | Workflow Automation | MITRE CWE-208 / HMAC constant-time comparison | `https://cwe.mitre.org/data/definitions/208.html` | Verified |
| `heldout_r4_wa_04` | Workflow Automation | AWS SQS FIFO message deduplication 5-min window | `https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/FIFO-deduplication.html` | Verified |
| `heldout_r4_wa_05` | Workflow Automation | Apache Kafka partition rebalance auto-commit risks | `https://kafka.apache.org/documentation/#consumerconfigs_enable.auto.commit` | Verified |
| `heldout_r4_wa_06` | Workflow Automation | OpenAPI 3.0 vs 3.1 nullable schema syntax | `https://spec.openapis.org/oas/v3.1.0#data-types` | Verified |
| `heldout_r4_wa_07` | Workflow Automation | GitHub Webhook delivery headers & retry GUID | `https://docs.github.com/en/webhooks/webhook-events-and-payloads#delivery-headers` | Verified |
| `heldout_r4_wa_08` | Workflow Automation | Stripe API idempotency key concurrency handling | `https://docs.stripe.com/api/idempotent_requests` | Verified |
| `heldout_r4_dr_01` | Document Research | UK Data Protection Act 2018 / UK GDPR Article 17 | `https://www.legislation.gov.uk/ukpga/2018/12/contents` | Verified |
| `heldout_r4_dr_02` | Document Research | ISO/IEC 27001:2022 Control A.8.1 Endpoint Security | `https://www.iso.org/standard/27001` | Verified |
| `heldout_r4_dr_03` | Document Research | EU AI Act (Regulation (EU) 2024/1689) Article 5 | `https://eur-lex.europa.eu/eli/reg/2024/1689/oj` | Verified |
| `heldout_r4_dr_04` | Document Research | Apache License, Version 2.0 §4(d) NOTICE file | `https://www.apache.org/licenses/LICENSE-2.0` | Verified |
| `heldout_r4_dr_05` | Document Research | MIT License copyright notice retention | `https://opensource.org/license/mit` | Verified |
| `heldout_r4_dr_06` | Document Research | W3C WCAG 2.2 Success Criterion 2.5.8 vs 2.5.5 | `https://www.w3.org/TR/WCAG22/#target-size-minimum` | Verified |
| `heldout_r4_dr_07` | Document Research | NIST SP 800-63B §5.1.1.2 Memorized Secrets | `https://pages.nist.gov/800-63-3/sp800-63b.html#memsecret` | Verified |
| `heldout_r4_dr_08` | Document Research | SEC Rule 10b-5 Material Non-Public Information | `https://www.sec.gov/rules/final/33-7881.htm` | Verified |

*(In compliance with data-author confidentiality rules, individual gold answer keys and expected keyword texts are omitted from this report.)*

---

## 5. Cryptographic Manifest & Structural Cross-Checks

### 5.1 Dataset Seal Manifest Summary
- **Path:** `research/datasets/heldout_r4_candidate/manifest.json`
- **Total Files Bound:** 102 files (24 cases, 24 public packets, 24 gold standards, 30 evidence documents)
- **SHA-256 Digest:** `fa5b60526ec72d6af74f45e1197a3f61cb0e08a058524176e5283733f7718df9`
- **Size:** 16,802 bytes

### 5.2 Top-Level Candidate Manifest Summary
- **Path:** `research/holdout_manifest_r4_candidate.json`
- **Candidate Status:** `candidate_rebuild`
- **Base Commit:** `56ef2f1871286af0111884de5f3a094b88fa26a0`
- **Bound Component Freezes:**
  - `research/PROTOCOL.md`: `a8e928a19d2a390ef017da638bad87682c8e81f01f0081ec3f1c488915d7fefe`
  - `research/EVALUATION_SPEC.md`: `61734daec67d4b3a66f40ddf490bdc338498f6c37de99732a26fb9394e314865`
  - `src/ommatidia/conditions.py`: `cf0310e4f55197b0858f543acfe6cbf354b1f77de7369f22cd79fb8f2c45e703`
  - `src/ommatidia/types.py`: `1052b5e6e415e5c1d2d6bb0ab6bde8378e6e2bb3d18638381edebdaad0c22571`
  - `src/ommatidia/evaluator.py`: `d29efee0aa7897e8f7264beae13da60fe678cc05a9a289ab094bd449dd2fb3c8`

### 5.3 Programmatic Structural Verification Log
Automated verification suite confirmed:
1. **File Count & Hash Integrity:** All 102 files exist and match their SHA-256 digests and byte counts with zero mismatches.
2. **Zero Gold Leakage in Public Packets:** Verified that forbidden evaluation keys (`groundTruthVerdicts`, `criticalEvidenceHashes`, `targetDecision`, `targetVerdict`, `gold`, `unblinding_key`) and case category labels are strictly absent from all 24 public packets.
3. **Public Packet Ingestion:** `load_dataset_partition("research/datasets/heldout_r4_candidate", include_gold=False, verify_hashes=True)` loaded and validated all 24 packets without error.
4. **Gold Standard Schema Conformance:** All 24 gold standard files deserialize cleanly via `GoldStandard.from_dict()`.
5. **Leakage & ID Intersection Check:** `check_heldout_leakage()` confirmed 0 task ID collisions with the development set (`dev_se_01`..`dev_dr_08`).
6. **Pytest Regression Suite:** 101 unit tests passed in 13.95s, confirming zero regressions.
7. **Seal Verification Status:** Standalone seal verification against `research/runtime_freeze_r3.json` passed with exit code 0.

---

## 6. Limitations, Operational Disclosures & Next Steps

1. **Candidate Status (Not Production-Ready):**  
   This candidate package is marked `candidate_rebuild`. In accordance with pre-registration protocols, neither `runtime_freeze_r3.json` nor `seal_manifest.json` have been modified or sealed to include this candidate. Production status requires formal peer acceptance and a release commit.
2. **No Experimental Validation or Efficacy Claims:**  
   This task performed data authoring and structural checks only. No study trials were dispatched, no experiment models were evaluated, and no claims of reasoning superiority or system performance are asserted.
3. **Transient Script Cleanup:**  
   The transient authoring script (`build_candidate.py`) was executed to generate and verify all assets and was cleanly deleted. Working tree integrity is maintained.
4. **Approval Gate for Live Trials:**  
   Live execution remains disabled under `run_harness.py` until the candidate package is formally reviewed, approved, and sealed into a new release freeze (`evaluationPackageStatus = "rebuilt_and_approved"`).
