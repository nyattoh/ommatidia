"""External response ingestion and strict payload validation for host child calls.

Suitable for integration with T3 Code orchestration (delegated child tasks)
without spawning unauthorized provider CLIs.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple, Union

from ommatidia.types import (
    Assessment,
    Claim,
    Evidence,
    Gap,
    Lens,
    Observation,
    ObservationOutcome,
    Probe,
    Proposal,
    TaskPacket,
    Usage,
)


class IngestionValidationError(ValueError):
    """Raised when an ingested response fails strict validation."""
    pass


def prepare_child_task_payload(
    stage: str,
    task: TaskPacket,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Prepare a strict, sealed payload suitable for a host delegated child call.

    Guarantees:
    - Gold answers, held-out files, and evaluation rubrics are never included.
    - Contains only the task goal, criteria, public evidence, and stage-specific context.
    """
    payload = {
        "stage": stage,
        "taskId": task.task_id,
        "goal": task.goal,
        "mode": task.mode,
        "capabilities": list(task.capabilities),
        "successCriteria": list(task.success_criteria),
        "evidence": [e.to_dict() for e in task.evidence],
        "context": context,
    }
    return payload


def ingest_json_response(raw_text: str) -> Dict[str, Any]:
    """Parse JSON strictly from raw response text, handling markdown fences if present."""
    clean_text = raw_text.strip()
    lines = clean_text.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    clean_text = "\n".join(lines).strip()

    try:
        data = json.loads(clean_text)
    except json.JSONDecodeError as exc:
        raise IngestionValidationError(f"Response is not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise IngestionValidationError(f"Expected top-level JSON object, got {type(data).__name__}")
    return data


def ingest_proposal(raw_input: Union[str, Dict[str, Any]]) -> Tuple[Proposal, Usage]:
    """Strictly validate and ingest a Proposal payload from a reasoning child task.

    Returns:
        (Proposal, Usage)
    """
    data = ingest_json_response(raw_input) if isinstance(raw_input, str) else raw_input

    # Parse usage if present
    usage_data = data.get("usage", {})
    usage = Usage.from_dict(usage_data) if isinstance(usage_data, dict) else Usage()

    proposal_data = data.get("proposal", data)
    if not isinstance(proposal_data, dict):
        raise IngestionValidationError("Missing 'proposal' dictionary in generation output")

    claims: Optional[List[Claim]] = None
    if "claims" in proposal_data:
        if not isinstance(proposal_data["claims"], list):
            raise IngestionValidationError("'claims' must be an array")
        try:
            claims = [Claim.from_dict(c) for c in proposal_data["claims"]]
        except Exception as exc:
            raise IngestionValidationError(f"Invalid claim definition: {exc}") from exc

    lenses: Optional[List[Lens]] = None
    if "lenses" in proposal_data:
        if not isinstance(proposal_data["lenses"], list):
            raise IngestionValidationError("'lenses' must be an array")
        try:
            lenses = [Lens.from_dict(l) for l in proposal_data["lenses"]]
        except Exception as exc:
            raise IngestionValidationError(f"Invalid lens definition: {exc}") from exc

    gaps: Optional[List[Gap]] = None
    if "gaps" in proposal_data:
        if not isinstance(proposal_data["gaps"], list):
            raise IngestionValidationError("'gaps' must be an array")
        try:
            gaps = [Gap.from_dict(g) for g in proposal_data["gaps"]]
        except Exception as exc:
            raise IngestionValidationError(f"Invalid gap definition: {exc}") from exc

    probes: Optional[List[Probe]] = None
    if "probes" in proposal_data:
        if not isinstance(proposal_data["probes"], list):
            raise IngestionValidationError("'probes' must be an array")
        try:
            probes = [Probe.from_dict(p) for p in proposal_data["probes"]]
        except Exception as exc:
            raise IngestionValidationError(f"Invalid probe definition: {exc}") from exc

    assessments: Optional[List[Assessment]] = None
    if "assessments" in proposal_data:
        if not isinstance(proposal_data["assessments"], list):
            raise IngestionValidationError("'assessments' must be an array")
        try:
            assessments = [Assessment.from_dict(a) for a in proposal_data["assessments"]]
        except Exception as exc:
            raise IngestionValidationError(f"Invalid assessment: {exc}") from exc

    resolutions = proposal_data.get("resolutions")
    if resolutions is not None and not isinstance(resolutions, list):
        raise IngestionValidationError("'resolutions' must be an array")

    return Proposal(
        claims=claims,
        lenses=lenses,
        gaps=gaps,
        probes=probes,
        assessments=assessments,
        resolutions=resolutions,
    ), usage


def ingest_observations(raw_input: Union[str, Dict[str, Any], List[Any]]) -> List[Observation]:
    """Strictly validate and ingest Observation records from an investigator child task."""
    if isinstance(raw_input, str):
        data = ingest_json_response(raw_input)
    else:
        data = raw_input

    items = data.get("observations", data) if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise IngestionValidationError("Expected list of observation objects")

    observations: List[Observation] = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise IngestionValidationError(f"Observation item {idx} is not an object")
        try:
            obs = Observation.from_dict(item)
            observations.append(obs)
        except Exception as exc:
            raise IngestionValidationError(f"Invalid observation at index {idx}: {exc}") from exc

    return observations
