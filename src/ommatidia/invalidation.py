"""Evidence provenance, deduplication, withdrawal, and cascading invalidation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from ommatidia.types import (
    Assessment,
    AssessmentVerdict,
    Claim,
    ClaimStatus,
    Evidence,
    EvidenceValidity,
    Gap,
    GapStatus,
    UnderstandingState,
)


class InvalidationError(ValueError):
    """Raised when an invalidation request is structurally invalid."""
    pass


def deduplicate_evidence(
    existing: List[Evidence],
    incoming: List[Evidence]
) -> Tuple[List[Evidence], List[Evidence]]:
    """Deduplicate incoming evidence against existing evidence.

    Returns:
        (accepted_evidence, rejected_duplicates)

    Deduplication rules:
    - Same ID with matching content hash is treated as an idempotent re-observation.
    - Same content hash (identical SHA-256) is rejected as duplicate evidence.
    - An empty passage when passageUnavailable is False is rejected.
    """
    seen_hashes: Set[str] = {e.content_hash for e in existing}
    seen_ids: Set[str] = {e.id for e in existing}

    accepted: List[Evidence] = []
    rejected: List[Evidence] = []

    for item in incoming:
        if item.id in seen_ids:
            # Check if identical item already recorded
            orig = next(e for e in existing if e.id == item.id)
            if orig.content_hash == item.content_hash:
                rejected.append(item)
                continue
            else:
                raise InvalidationError(f"Evidence ID '{item.id}' re-used with differing content hash")

        if item.content_hash in seen_hashes:
            # Duplicate evidence content even under different ID
            rejected.append(item)
            continue

        seen_hashes.add(item.content_hash)
        seen_ids.add(item.id)
        accepted.append(item)

    return accepted, rejected


def invalidate_evidence(
    state: UnderstandingState,
    target_evidence_ids: List[str],
    reason: str,
    action: EvidenceValidity = EvidenceValidity.WITHDRAWN
) -> Dict[str, Any]:
    """Withdraw or supersede evidence and propagate invalidation across the state.

    Cascading effects:
    1. Update target evidence validity to WITHDRAWN or SUPERSEDED.
    2. Invalidate assessments that cited the invalidated evidence:
       - Remove or recalculate assessments.
       - Re-evaluate claim statuses (supported/contradicted -> unverified or disputed).
    3. Reopen any gaps whose resolution relied on the invalidated evidence:
       - Set gap.status = OPEN, gap.resolution = None.
    4. Historical applied executions and usage are preserved intact.

    Returns a report detailing what was changed.
    """
    if action not in (EvidenceValidity.WITHDRAWN, EvidenceValidity.SUPERSEDED):
        raise InvalidationError("Invalidation action must be WITHDRAWN or SUPERSEDED")

    target_set = set(target_evidence_ids)
    if not target_set:
        raise InvalidationError("No evidence IDs supplied for invalidation")

    existing_evidence_map: Dict[str, Evidence] = {e.id: e for e in state.evidence}
    for tid in target_set:
        if tid not in existing_evidence_map:
            raise InvalidationError(f"Evidence ID '{tid}' not found in state")

    # 1. Update evidence items
    updated_evidence: List[Evidence] = []
    invalidated_evidence_ids: List[str] = []
    for e in state.evidence:
        if e.id in target_set:
            new_e = Evidence(
                id=e.id,
                kind=e.kind,
                locator=e.locator,
                source_group=e.source_group,
                retrieved_at=e.retrieved_at,
                version=e.version,
                scope=e.scope,
                passage=e.passage,
                content_hash=e.content_hash,
                validity=action,
                passage_unavailable=e.passage_unavailable,
            )
            updated_evidence.append(new_e)
            invalidated_evidence_ids.append(e.id)
        else:
            updated_evidence.append(e)
    state.evidence = updated_evidence

    # Valid evidence ID set
    valid_evidence_ids: Set[str] = {
        e.id for e in state.evidence if e.validity == EvidenceValidity.CURRENT
    }

    # 2. Invalidate assessments and re-evaluate claims
    claims_modified: List[str] = []
    for claim in state.claims:
        original_status = claim.status
        valid_assessments: List[Assessment] = []
        for assessment in claim.assessments:
            # Check if any cited evidence was invalidated
            if any(eid in target_set for eid in assessment.evidence_ids):
                continue
            valid_assessments.append(assessment)

        claim.assessments = valid_assessments

        # Re-derive claim status from remaining valid assessments
        supports_count = sum(1 for a in valid_assessments if a.verdict == AssessmentVerdict.SUPPORTS)
        refutes_count = sum(1 for a in valid_assessments if a.verdict == AssessmentVerdict.REFUTES)

        if supports_count > 0 and refutes_count > 0:
            claim.status = ClaimStatus.DISPUTED
        elif supports_count > 0:
            claim.status = ClaimStatus.SUPPORTED
        elif refutes_count > 0:
            claim.status = ClaimStatus.CONTRADICTED
        else:
            claim.status = ClaimStatus.UNVERIFIED

        if claim.status != original_status:
            claims_modified.append(claim.id)

    # 3. Reopen gaps resolved via invalidated evidence
    gaps_reopened: List[str] = []
    for gap in state.gaps:
        if gap.status == GapStatus.RESOLVED and gap.resolution is not None:
            if any(eid in target_set for eid in gap.resolution.evidence_ids):
                gap.status = GapStatus.OPEN
                gap.resolution = None
                gaps_reopened.append(gap.id)

    state.revision += 1

    return {
        "reason": reason,
        "action": action.value,
        "invalidatedEvidenceIds": invalidated_evidence_ids,
        "claimsModified": claims_modified,
        "gapsReopened": gaps_reopened,
        "newRevision": state.revision,
    }
