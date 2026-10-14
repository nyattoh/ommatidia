"""State machine and lifecycle management for UnderstandingState."""

from __future__ import annotations

import datetime
import hashlib
import json
from typing import Any, Dict, List, Optional, Set, Tuple

from ommatidia.invalidation import deduplicate_evidence
from ommatidia.types import (
    AppliedExecution,
    Assessment,
    AssessmentVerdict,
    Budget,
    Claim,
    ClaimRole,
    ClaimStatus,
    Decision,
    Evidence,
    EvidenceValidity,
    Gap,
    GapImportance,
    GapStatus,
    Lens,
    LensOrigin,
    LensStatus,
    Observation,
    ObservationOutcome,
    Probe,
    ProbeStatus,
    Proposal,
    Resolution,
    ResolutionReason,
    TaskPacket,
    UnderstandingState,
    Usage,
)


def create_initial_state(task: TaskPacket) -> UnderstandingState:
    """Create a new UnderstandingState initialized from a TaskPacket."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return UnderstandingState(
        schema_version="0.1",
        task_id=task.task_id,
        revision=0,
        started_at=now_iso,
        task=task,
        evidence=list(task.evidence),
        claims=[],
        lenses=[],
        gaps=[],
        probes=[],
        usage=Usage(),
        decision=Decision.NEEDS_CHECK,
        stop_reason=None,
        applied_executions=[],
        pending_assessment_execution_ids=[],
    )


def compute_payload_hash(payload: Any) -> str:
    """Calculate the deterministic SHA-256 hash of a JSON-serializable payload."""
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def apply_observations(
    state: UnderstandingState,
    observations: List[Observation],
    raw_payload_hash: Optional[str] = None,
) -> Dict[str, Any]:
    """Ingest observation results from probe investigations into UnderstandingState.

    Enforces:
    - Execution idempotency (cannot apply same execution_id twice with differing payload).
    - Evidence deduplication and provenance registration.
    - Probe status transition:
        - completed -> ProbeStatus.COMPLETE
        - no_result -> ProbeStatus.COMPLETE (records no evidence, does NOT refute)
        - unavailable -> ProbeStatus.UNAVAILABLE
        - error -> ProbeStatus.ERROR
    - Usage accumulation (tool calls, elapsed time, tokens, cost).
    """
    existing_execution_ids: Set[str] = {a.execution_id for a in state.applied_executions}
    probe_map: Dict[str, Probe] = {p.id: p for p in state.probes}

    new_evidence: List[Evidence] = []
    rejected_evidence: List[Evidence] = []
    new_applied: List[AppliedExecution] = []

    for obs in observations:
        if obs.execution_id in existing_execution_ids:
            # Check existing record
            existing_rec = next(a for a in state.applied_executions if a.execution_id == obs.execution_id)
            p_hash = raw_payload_hash or compute_payload_hash(obs.to_dict())
            if existing_rec.payload_hash != p_hash:
                raise ValueError(
                    f"Execution '{obs.execution_id}' previously applied with differing payload hash"
                )
            # Idempotently skip duplicate execution
            continue

        p_hash = raw_payload_hash or compute_payload_hash(obs.to_dict())
        probe = probe_map.get(obs.probe_id)
        if probe is None:
            raise ValueError(f"Observation references unknown probe ID: '{obs.probe_id}'")

        # Update probe status
        if obs.outcome == ObservationOutcome.COMPLETED:
            probe.status = ProbeStatus.COMPLETE
        elif obs.outcome == ObservationOutcome.NO_RESULT:
            # Note: No result does not refute the claim or resolve the gap
            probe.status = ProbeStatus.COMPLETE
        elif obs.outcome == ObservationOutcome.UNAVAILABLE:
            probe.status = ProbeStatus.UNAVAILABLE
        elif obs.outcome == ObservationOutcome.ERROR:
            probe.status = ProbeStatus.ERROR

        # Deduplicate and register incoming evidence
        accepted, rejected = deduplicate_evidence(state.evidence + new_evidence, obs.evidence)
        new_evidence.extend(accepted)
        rejected_evidence.extend(rejected)

        # Update usage
        state.usage.tool_calls += obs.tool_calls
        state.usage.elapsed_ms += obs.elapsed_ms
        if obs.cost_yen is not None:
            if state.usage.cost_yen is None:
                state.usage.cost_yen = obs.cost_yen
            else:
                state.usage.cost_yen += obs.cost_yen
        if obs.total_tokens is not None:
            if state.usage.total_tokens is None:
                state.usage.total_tokens = obs.total_tokens
            else:
                state.usage.total_tokens += obs.total_tokens

        applied = AppliedExecution(
            execution_id=obs.execution_id,
            payload_hash=p_hash,
            probe_id=obs.probe_id,
            outcome=obs.outcome,
        )
        new_applied.append(applied)
        state.applied_executions.append(applied)
        existing_execution_ids.add(obs.execution_id)

    state.evidence.extend(new_evidence)
    state.revision += 1

    return {
        "appliedExecutionsCount": len(new_applied),
        "newEvidenceAccepted": len(new_evidence),
        "evidenceRejected": len(rejected_evidence),
        "newRevision": state.revision,
    }


def apply_proposal(
    state: UnderstandingState,
    proposal: Proposal,
) -> Dict[str, Any]:
    """Incorporate structured reasoning updates (claims, lenses, gaps, probes, assessments, resolutions)."""
    # 1. Incorporate Lenses
    if proposal.lenses:
        existing_lens_ids = {l.id for l in state.lenses}
        for lens in proposal.lenses:
            if lens.id in existing_lens_ids:
                # Update existing lens
                idx = next(i for i, l in enumerate(state.lenses) if l.id == lens.id)
                state.lenses[idx] = lens
            else:
                state.lenses.append(lens)

    # 2. Incorporate Claims
    if proposal.claims:
        existing_claim_ids = {c.id for c in state.claims}
        for claim in proposal.claims:
            if claim.id in existing_claim_ids:
                idx = next(i for i, c in enumerate(state.claims) if c.id == claim.id)
                state.claims[idx] = claim
            else:
                state.claims.append(claim)

    # 3. Incorporate Gaps
    if proposal.gaps:
        existing_gap_ids = {g.id for g in state.gaps}
        for gap in proposal.gaps:
            if gap.id in existing_gap_ids:
                idx = next(i for i, g in enumerate(state.gaps) if g.id == gap.id)
                state.gaps[idx] = gap
            else:
                state.gaps.append(gap)

    # 4. Incorporate Probes
    if proposal.probes:
        existing_probe_ids = {p.id for p in state.probes}
        for probe in proposal.probes:
            if probe.id in existing_probe_ids:
                idx = next(i for i, p in enumerate(state.probes) if p.id == probe.id)
                state.probes[idx] = probe
            else:
                state.probes.append(probe)

    # 5. Incorporate Assessments and update claim statuses
    if proposal.assessments:
        claim_map = {c.id: c for c in state.claims}
        valid_evidence_ids = {e.id for e in state.evidence if e.validity == EvidenceValidity.CURRENT}

        for asm in proposal.assessments:
            claim = claim_map.get(asm.claim_id)
            if claim is None:
                continue
            # Ensure cited evidence exists and is current
            if not all(eid in valid_evidence_ids for eid in asm.evidence_ids):
                continue

            # Append assessment
            claim.assessments.append(asm)

            # Recompute claim status
            supports = sum(1 for a in claim.assessments if a.verdict == AssessmentVerdict.SUPPORTS)
            refutes = sum(1 for a in claim.assessments if a.verdict == AssessmentVerdict.REFUTES)
            if supports > 0 and refutes > 0:
                claim.status = ClaimStatus.DISPUTED
            elif supports > 0:
                claim.status = ClaimStatus.SUPPORTED
            elif refutes > 0:
                claim.status = ClaimStatus.CONTRADICTED

    # 6. Incorporate Resolutions
    if proposal.resolutions:
        gap_map = {g.id: g for g in state.gaps}
        valid_evidence_ids = {e.id for e in state.evidence if e.validity == EvidenceValidity.CURRENT}
        for res_dict in proposal.resolutions:
            gid = res_dict.get("gapId")
            gap = gap_map.get(gid)
            if gap is None:
                continue
            eids = res_dict.get("evidenceIds", [])
            if not all(eid in valid_evidence_ids for eid in eids):
                continue
            resolution = Resolution(
                reason=ResolutionReason(res_dict["reason"]),
                evidence_ids=eids,
                explanation=str(res_dict.get("explanation", "")),
            )
            gap.resolution = resolution
            gap.status = GapStatus.RESOLVED

    state.revision += 1
    return {"newRevision": state.revision}


def evaluate_stopping_conditions(
    state: UnderstandingState,
    budget: Budget,
) -> Tuple[bool, Optional[str], Decision]:
    """Evaluate whether the investigation loop should terminate.

    Returns:
        (should_stop, stop_reason, decision)
    """
    # 1. Budget check
    if state.usage.exceeds(budget):
        return True, "budget_exhausted", Decision.BLOCKED

    # 2. Check if all required gaps are resolved
    required_gaps = [g for g in state.gaps if g.importance == GapImportance.REQUIRED]
    if required_gaps:
        all_resolved = all(g.status == GapStatus.RESOLVED for g in required_gaps)
        if all_resolved:
            return True, "required_gaps_resolved", Decision.READY_FOR_REQUESTED_STEP

    # 3. Check probe exhaustion: if all probes are non-pending and no gaps can proceed
    pending_probes = [p for p in state.probes if p.status == ProbeStatus.PENDING]
    if state.probes and not pending_probes:
        # Check if unresolved required gaps remain
        unresolved_required = [
            g for g in required_gaps if g.status != GapStatus.RESOLVED
        ]
        if unresolved_required:
            return True, "probes_exhausted_unresolved_gaps", Decision.BLOCKED
        else:
            return True, "probes_exhausted", Decision.READY_FOR_REQUESTED_STEP

    # Continue investigation
    return False, None, Decision.NEEDS_CHECK
