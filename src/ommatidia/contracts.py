"""Agent-visible schemas for every executable graph step."""

from ommatidia.types import (AssessmentVerdict, EvidenceKind, GapKind, ObservationOutcome,
                             ProbeMethod, ResolutionReason)

STRING = {"type": "string"}
STRINGS = {"type": "array", "items": STRING}
COUNT = {"type": "integer", "minimum": 0}


def object_schema(properties, required=None):
    return {"type": "object", "required": list(properties) if required is None else required,
            "properties": properties}


def array_schema(item):
    return {"type": "array", "items": item}


EVIDENCE_SCHEMA = object_schema({
    "id": STRING, "kind": {"enum": [item.value for item in EvidenceKind]},
    "locator": STRING, "sourceGroup": STRING, "retrievedAt": STRING,
    "version": STRING, "scope": STRING, "passage": STRING,
    "contentHash": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
    "validity": {"enum": ["current", "withdrawn", "superseded"]}})
ASSESSMENT_SCHEMA = object_schema({"claimId": STRING,
    "verdict": {"enum": [item.value for item in AssessmentVerdict]}, "evidenceIds": STRINGS,
    "scopeMatched": {"type": "boolean"}, "reason": STRING})
CLAIM_SCHEMA = object_schema({"id": STRING,
    "role": {"enum": ["observation", "assumption", "hypothesis", "answer_claim"]},
    "text": STRING, "scope": STRING, "status": {"enum": ["unverified", "supported", "contradicted", "disputed"]}},
    ["id", "role", "text", "scope"])
LENS_SCHEMA = object_schema({"id": STRING, "label": STRING, "rationale": STRING,
    "origin": {"enum": ["initial", "proposed"]}})
GAP_SCHEMA = object_schema({"id": STRING,
    "kind": {"enum": [item.value for item in GapKind]},
    "lensId": STRING, "question": STRING, "triggerRefs": STRINGS, "whyItMatters": STRING,
    "importance": {"enum": ["required", "optional"]}, "claimIds": STRINGS, "probeIds": STRINGS},
    ["id", "kind", "lensId", "question", "triggerRefs", "whyItMatters", "importance"])
PROBE_SCHEMA = object_schema({"id": STRING, "gapIds": {"type": "array", "minItems": 1, "items": STRING},
    "method": {"enum": [item.value for item in ProbeMethod]},
    "question": STRING, "requiredCapability": STRING, "sourceGroups": STRINGS,
    "successCondition": STRING, "refutationCondition": STRING, "inconclusiveCondition": STRING})
RESOLUTION_SCHEMA = object_schema({"gapId": STRING,
    "reason": {"enum": [item.value for item in ResolutionReason]},
    "evidenceIds": STRINGS, "explanation": STRING})
PROPOSAL_SCHEMA = object_schema({"proposal": object_schema({
    "claims": array_schema(CLAIM_SCHEMA), "lenses": array_schema(LENS_SCHEMA),
    "gaps": array_schema(GAP_SCHEMA), "probes": array_schema(PROBE_SCHEMA),
    "assessments": array_schema(ASSESSMENT_SCHEMA), "resolutions": array_schema(RESOLUTION_SCHEMA)},
    ["claims", "lenses", "gaps", "probes"])})
OBSERVATION_SCHEMA = object_schema({"observations": array_schema(object_schema({
    "executionId": STRING, "probeId": STRING,
    "outcome": {"enum": [item.value for item in ObservationOutcome]},
    "evidence": array_schema(EVIDENCE_SCHEMA), "toolCalls": COUNT,
    "elapsedMs": {"type": "number", "minimum": 0}},
    ["executionId", "probeId", "outcome", "evidence"]))})
FINAL_SCHEMA = object_schema({"taskId": STRING,
    "verdict": {"enum": ["supported", "contradicted", "disputed", "inconclusive"]},
    "confidenceScore": {"type": "number", "minimum": 0, "maximum": 1},
    "justification": {"type": "string", "minLength": 1},
    "citedEvidence": array_schema(object_schema({"id": STRING, "sourceGroup": STRING, "locator": STRING,
        "contentHash": {"type": "string", "pattern": "^[a-f0-9]{64}$"}, "passage": STRING,
        "verdictRelation": {"enum": ["supports", "refutes", "context"]}})),
    "unresolvedGaps": STRINGS,
    "resourceUsage": object_schema({"modelCalls": COUNT, "toolCalls": COUNT,
        "elapsedMs": {"type": "number", "minimum": 0}, "inputCharsEstimated": COUNT})})
