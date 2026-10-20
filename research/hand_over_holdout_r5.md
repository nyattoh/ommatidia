# Ommatidia R5 Candidate Evaluation Package Handover

**Document Version:** 1.0.0  
**Status:** Candidate Package (Unfrozen / Pre-registration Candidate)  
**Role:** Research Sub-agent (Data Author)  
**Language:** British English  
**Base Commit:** 56ef2f1  

---

## 1. Executive Summary

This document records the creation of the independent **R5 Candidate Evaluation Package** for the Ommatidia empirical study, created strictly under the pre-registered protocol (`research/PROTOCOL.md`) and evaluation specification (`research/EVALUATION_SPEC.md`).

R4 was completely isolated, not accessed, and not reused following its independent audit failure. All 24 cases in R5 Candidate have been generated independently from public primary specifications and newly synthesized fictional operational records. Case identifiers are entirely opaque, with no label, domain, or control tokens. Gold evaluation rubrics were generated deterministically into evaluator-only storage without any answer text or per-case label exposure in chat, manifests, logs, or this handover.

---

## 2. Package Architecture and File Layout

The R5 candidate evaluation package is located at `research/datasets/heldout_r5_candidate/` and contains the following file tree:

```
research/datasets/heldout_r5_candidate/
├── cases/                     # 24 complete case packages (task + gold standard)
├── evidence/                  # 24 evidence files across 3 domains
│   ├── document_research/
│   ├── software_engineering/
│   └── workflow_automation/
├── gold/                      # 24 evaluator-only GoldStandard rubrics
├── public_packets/            # 24 agent-visible TaskPacket JSON files
└── manifest.json              # Complete SHA-256 dataset manifest
```

The top-level candidate manifest is located at `research/holdout_manifest_r5_candidate.json`.

---

## 3. Aggregate Metrics and Stratification

### 3.1 Case and Document Counts
- **Total Public Packets:** 24
- **Total Gold Rubrics:** 24
- **Total Case Definitions:** 24
- **Total Evidence Documents:** 24 (spanning 3 domain subdirectories)

### 3.2 Domain Stratification
- **Software Engineering (SE):** 8 cases
- **Workflow Automation (WA):** 8 cases
- **Document & Policy Research (DR):** 8 cases
- **Total Held-Out Evaluated Denominator ($N_{\text{heldout}}$):** 24 cases

### 3.3 Negative Control Allocation (Protocol §5.3 Compliance)
Across the full 48-case benchmark, the frozen protocol specifies exactly 12 negative controls (4 per domain: 2 in Dev, 2 in Held-Out). The Held-Out R5 candidate satisfies this split with exactly 6 negative controls:
- **Control Type 1 (Sufficient Initial State / No-Op):** 2 cases (SE and DR)
- **Control Type 2 (Capability Limit / Unresolvable Abstention):** 2 cases (SE and DR)
- **Control Type 3 (Superficially Plausible Distractor):** 1 case (WA)
- **Control Type 4 (Genuine Irresolvable Conflict):** 1 case (WA)
*(Dev retains the complementary 6 negative controls, guaranteeing exact 12-control benchmark balance without per-heldout distortion).*

### 3.4 H4 Counterexample Membership
- **Frozen H4 Counterexample Cases:** Exactly 12 cases (50% of the held-out partition, meeting EVALUATION_SPEC.md §5.2 requirements for exact McNemar paired testing power).

---

## 4. Primary Source Corrections and Verification Status

All primary references cite exact official versions and sections, resolving all historical R4 citation defects:

| Reference Topic | Official Source Citation | Section / Version | Verification Status |
| :--- | :--- | :--- | :--- |
| **HTTP Retry-After** | IETF RFC 9110 | Section 10.2.3 (not §10.2.7) | Verified primary RFC text (delay-seconds vs HTTP-date) |
| **C11 Memory Consistency** | ISO/IEC 9899:201x WG14 N1570 | Section 7.17.3 | Verified primary committee draft (N1570, not ISO final) |
| **Password Verifier Rules** | NIST SP 800-63B-4 (Final, 2025-07-31) | Section 3.1.1.2 | Verified final official standard (supersedes SP 800-63-3) |
| **POSIX Mutex Semantics** | IEEE Std 1003.1-2017 / Issue 7 | System Interfaces (pthread_mutex_lock) | Verified primary Open Group Base Specifications text |
| **Account Disabling Controls** | NIST SP 800-53 Rev 5 | Control AC-2(3) | Verified open primary standard replacing paywalled ISO 27001 |
| **Securities Fraud vs Reg FD** | 17 CFR § 240.10b-5 & SEC Release 33-7881 | Rule 10b-5 vs Reg FD | Verified official eCFR regulation and SEC release distinction |
| **Right to Erasure** | Regulation (EU) 2016/679 (GDPR) | Article 17(1) & 17(3)(b) | Verified official EUR-Lex regulation text and statutory exception |
| **Payment API Idempotency** | Stripe API Reference (v1 vs v2) | Idempotent Requests (v1) / Events v2 | Verified official Stripe documentation with explicit API versioning |

### 4.1 Fictional Operational Records Integrity
All synthetic operational logs, code snippets, and internal company memos are explicitly labelled:
- Header level: `[FICTIONAL TEST DATASET - NOT REAL ENTITY OR OPERATIONAL RECORD]`
- Inline level: Explicit synthetic context markers preventing conflation with real entities.

---

## 5. Requirement Verification Checklist

- [x] Exactly 24 public packets created under `public_packets/`
- [x] Required `domain` field present in all 24 public packets
- [x] Required `availableSources` present in all 24 public packets
- [x] Every `entryLocator` in `availableSources` exists on disk and resolves strictly within repository
- [x] Task IDs are strictly opaque (`case_r5_01` to `case_r5_24`) without label, domain, or control tokens
- [x] No gold keys, answer keys, target decisions, or rubrics present in `public_packets/`
- [x] R4 candidate and old gold files were not read, accessed, or reused
- [x] Strict compliance with frozen protocol negative control distribution across Dev and Held-Out
- [x] Public packets verified by runtime loader (`ommatidia.harness.load_public_packets`, exit code 0)
- [x] Dataset manifest validates all 96 files by size and SHA-256 hash (exit code 0)
- [x] Top-level candidate manifest binds frozen hashes without updating seal manifest (exit code 0)
- [x] Handover and logs contain zero case-by-case expected labels or answer text

---

## 6. Cryptographic Provenance and Manifest Hashes

### 6.1 Package Manifests
- **Dataset Manifest (`research/datasets/heldout_r5_candidate/manifest.json`):**  
  `6c81e7e40625f420218f9c9323b02dcd303d209471db95653c80afbe394dce7c`
- **Top Candidate Manifest (`research/holdout_manifest_r5_candidate.json`):**  
  `1d3f0c9a176a9b6107909a88956c3b1c347dd9c4ea4c11e829299a0d120e7a0f`

### 6.2 Bound Frozen Component Hashes
- **Protocol (`research/PROTOCOL.md`):**  
  `a8e928a19d2a390ef017da638bad87682c8e81f01f0081ec3f1c488915d7fefe`
- **Evaluation Spec (`research/EVALUATION_SPEC.md`):**  
  `61734daec67d4b3a66f40ddf490bdc338498f6c37de99732a26fb9394e314865`
- **Condition Implementation (`src/ommatidia/conditions.py`):**  
  `cf0310e4f55197b0858f543acfe6cbf354b1f77de7369f22cd79fb8f2c45e703`
- **Core Types (`src/ommatidia/types.py`):**  
  `1052b5e6e415e5c1d2d6bb0ab6bde8378e6e2bb3d18638381edebdaad0c22571`
- **Evaluator (`src/ommatidia/evaluator.py`):**  
  `d29efee0aa7897e8f7264beae13da60fe678cc05a9a289ab094bd449dd2fb3c8`

---

## 7. Known Limitations and Pre-Registration Boundary

1. **Candidate Status:** The package remains an unfrozen candidate. Final sealing (`seal_manifest.json` or `runtime_freeze_r3.json`) must be executed by the independent reviewer / parent agent following audit.
2. **Zero Model Execution:** No live study experiments, model calls, or prompt tuning against these held-out cases have been performed during this task.
3. **Execution Readiness:** Structural validation confirms that the candidate package conforms fully to `load_public_packets()` and is ready for independent candidate gate audit.
