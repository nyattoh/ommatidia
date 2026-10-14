"""Strongly typed representations for the Ommatidia research harness.

Grounds the understanding-state model, experimental condition contracts,
run ledger, evidence provenance, and evaluation metrics.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import re
from typing import Any, Dict, List, Optional, Set


ID_PATTERN = re.compile(r"^[A-Za-z0-9_\-:.]{1,200}$")
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")


def validate_id(identifier: str, field_name: str = "id") -> str:
    """Validate that an identifier is non-empty, alphanumeric/safe, and not reserved."""
    if not isinstance(identifier, str) or not ID_PATTERN.match(identifier):
        raise ValueError(f"Invalid {field_name}: '{identifier}'")
    if identifier.startswith("task:"):
        raise ValueError(f"Reserved identifier prefix in {field_name}: '{identifier}'")
    return identifier


def validate_sha256(hash_str: str, field_name: str = "hash") -> str:
    """Validate that a string is a 64-character lowercase SHA-256 hexadecimal digest."""
    if not isinstance(hash_str, str) or not SHA256_PATTERN.match(hash_str):
        raise ValueError(f"Invalid SHA-256 digest in {field_name}: '{hash_str}'")
    return hash_str


class EvidenceKind(str, Enum):
    DOCUMENT = "document"
    CODE = "code"
    TEST = "test"
    USER_STATEMENT = "user_statement"


class EvidenceValidity(str, Enum):
    CURRENT = "current"
    WITHDRAWN = "withdrawn"
    SUPERSEDED = "superseded"


class ClaimRole(str, Enum):
    OBSERVATION = "observation"
    ASSUMPTION = "assumption"
    HYPOTHESIS = "hypothesis"
    ANSWER_CLAIM = "answer_claim"


class ClaimStatus(str, Enum):
    UNVERIFIED = "unverified"
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    DISPUTED = "disputed"


class AssessmentVerdict(str, Enum):
    SUPPORTS = "supports"
    REFUTES = "refutes"
    INCONCLUSIVE = "inconclusive"


class LensOrigin(str, Enum):
    INITIAL = "initial"
    PROPOSED = "proposed"


class LensStatus(str, Enum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    RETIRED = "retired"


class GapKind(str, Enum):
    MISSING_FACT = "missing_fact"
    AMBIGUOUS_INTENT = "ambiguous_intent"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    UNEXPLORED_VIEW = "unexplored_view"
    CAPABILITY_LIMIT = "capability_limit"


class GapImportance(str, Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"


class GapStatus(str, Enum):
    OPEN = "open"
    CHECKING = "checking"
    RESOLVED = "resolved"
    BLOCKED = "blocked"


class ResolutionReason(str, Enum):
    SUPPORTED = "supported"
    REFUTED = "refuted"
    NOT_APPLICABLE = "not_applicable"


class ProbeMethod(str, Enum):
    EXAMPLE = "example"
    COUNTEREXAMPLE = "counterexample"
    BOUNDARY = "boundary"
    DEPENDENCY = "dependency"
    CORROBORATION = "corroboration"
    RECONSTRUCTION = "reconstruction"


class ProbeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


class ObservationOutcome(str, Enum):
    COMPLETED = "completed"
    NO_RESULT = "no_result"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


class Decision(str, Enum):
    READY_FOR_REQUESTED_STEP = "ready_for_requested_step"
    NEEDS_CHECK = "needs_check"
    NEEDS_USER_INPUT = "needs_user_input"
    BLOCKED = "blocked"


class ConditionType(str, Enum):
    A = "A"  # Baseline standard exploration
    B = "B"  # Generic re-examination
    C = "C"  # Fixed perspectives
    D = "D"  # Single adaptive investigator
    E = "E"  # Ommatidia multi-perspective investigation


class LedgerStage(str, Enum):
    PLANNING = "planning"
    INVESTIGATOR = "investigator"
    COMMUNICATION = "communication"
    RETRY = "retry"
    SYNTHESIS = "synthesis"


@dataclass(frozen=True)
class Budget:
    max_rounds: int
    max_model_calls: int
    max_tool_calls: int
    max_elapsed_ms: int
    max_input_chars: int
    max_output_tokens_per_call: int
    max_cost_yen: Optional[float] = None

    def __post_init__(self) -> None:
        if self.max_rounds < 0 or self.max_model_calls < 0 or self.max_tool_calls < 0:
            raise ValueError("Budget limits cannot be negative")
        if self.max_elapsed_ms < 0 or self.max_input_chars < 0 or self.max_output_tokens_per_call < 0:
            raise ValueError("Budget limits cannot be negative")
        if self.max_cost_yen is not None and self.max_cost_yen < 0:
            raise ValueError("Budget cost cannot be negative")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "maxRounds": self.max_rounds,
            "maxModelCalls": self.max_model_calls,
            "maxToolCalls": self.max_tool_calls,
            "maxElapsedMs": self.max_elapsed_ms,
            "maxInputChars": self.max_input_chars,
            "maxOutputTokensPerCall": self.max_output_tokens_per_call,
            "maxCostYen": self.max_cost_yen,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Budget:
        return cls(
            max_rounds=int(data["maxRounds"]),
            max_model_calls=int(data["maxModelCalls"]),
            max_tool_calls=int(data["maxToolCalls"]),
            max_elapsed_ms=int(data["maxElapsedMs"]),
            max_input_chars=int(data["maxInputChars"]),
            max_output_tokens_per_call=int(data["maxOutputTokensPerCall"]),
            max_cost_yen=float(data["maxCostYen"]) if data.get("maxCostYen") is not None else None,
        )


@dataclass
class Usage:
    rounds: int = 0
    model_calls: int = 0
    tool_calls: int = 0
    elapsed_ms: float = 0.0
    total_tokens: Optional[int] = None  # None indicates unknown; unknown is not 0
    cost_yen: Optional[float] = None    # None indicates unknown; unknown is not 0

    def add(self, other: Usage) -> None:
        self.rounds += other.rounds
        self.model_calls += other.model_calls
        self.tool_calls += other.tool_calls
        self.elapsed_ms += other.elapsed_ms

        # If either is None, the sum remains unknown (None) unless both are numbers
        if self.total_tokens is not None and other.total_tokens is not None:
            self.total_tokens += other.total_tokens
        else:
            self.total_tokens = None

        if self.cost_yen is not None and other.cost_yen is not None:
            self.cost_yen += other.cost_yen
        else:
            self.cost_yen = None

    def exceeds(self, budget: Budget) -> bool:
        if self.rounds > budget.max_rounds:
            return True
        if self.model_calls > budget.max_model_calls:
            return True
        if self.tool_calls > budget.max_tool_calls:
            return True
        if self.elapsed_ms > budget.max_elapsed_ms:
            return True
        if budget.max_cost_yen is not None and self.cost_yen is not None:
            if self.cost_yen > budget.max_cost_yen:
                return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rounds": self.rounds,
            "modelCalls": self.model_calls,
            "toolCalls": self.tool_calls,
            "elapsedMs": self.elapsed_ms,
            "totalTokens": self.total_tokens,
            "costYen": self.cost_yen,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Usage:
        return cls(
            rounds=int(data.get("rounds", 0)),
            model_calls=int(data.get("modelCalls", 0)),
            tool_calls=int(data.get("toolCalls", 0)),
            elapsed_ms=float(data.get("elapsedMs", 0.0)),
            total_tokens=int(data["totalTokens"]) if data.get("totalTokens") is not None else None,
            cost_yen=float(data["costYen"]) if data.get("costYen") is not None else None,
        )


@dataclass(frozen=True)
class Evidence:
    id: str
    kind: EvidenceKind
    locator: str
    source_group: str
    retrieved_at: str
    version: Optional[str]
    scope: str
    passage: str
    content_hash: str
    validity: EvidenceValidity = EvidenceValidity.CURRENT
    passage_unavailable: bool = False

    def __post_init__(self) -> None:
        validate_id(self.id, "evidence.id")
        validate_sha256(self.content_hash, "evidence.content_hash")
        if self.passage_unavailable and self.passage != "":
            raise ValueError("Unavailable passage must be empty string")

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "id": self.id,
            "kind": self.kind.value,
            "locator": self.locator,
            "sourceGroup": self.source_group,
            "retrievedAt": self.retrieved_at,
            "version": self.version,
            "scope": self.scope,
            "passage": self.passage,
            "contentHash": self.content_hash,
            "validity": self.validity.value,
        }
        if self.passage_unavailable:
            result["passageUnavailable"] = True
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Evidence:
        return cls(
            id=validate_id(data["id"], "evidence.id"),
            kind=EvidenceKind(data["kind"]),
            locator=str(data["locator"]),
            source_group=str(data["sourceGroup"]),
            retrieved_at=str(data["retrievedAt"]),
            version=str(data["version"]) if data.get("version") is not None else None,
            scope=str(data["scope"]),
            passage=str(data.get("passage", "")),
            content_hash=validate_sha256(data["contentHash"], "evidence.content_hash"),
            validity=EvidenceValidity(data.get("validity", EvidenceValidity.CURRENT.value)),
            passage_unavailable=bool(data.get("passageUnavailable", False)),
        )


@dataclass(frozen=True)
class Assessment:
    claim_id: str
    evidence_ids: List[str]
    verdict: AssessmentVerdict
    scope_matched: bool
    reason: str

    def __post_init__(self) -> None:
        validate_id(self.claim_id, "assessment.claim_id")
        if not self.evidence_ids:
            raise ValueError("Assessment must cite at least one evidence item")
        for eid in self.evidence_ids:
            validate_id(eid, "assessment.evidence_ids")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("Duplicate evidence references in assessment")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claimId": self.claim_id,
            "evidenceIds": list(self.evidence_ids),
            "verdict": self.verdict.value,
            "scopeMatched": self.scope_matched,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Assessment:
        return cls(
            claim_id=validate_id(data["claimId"], "assessment.claimId"),
            evidence_ids=[validate_id(x, "assessment.evidenceIds") for x in data["evidenceIds"]],
            verdict=AssessmentVerdict(data["verdict"]),
            scope_matched=bool(data["scopeMatched"]),
            reason=str(data["reason"]),
        )


@dataclass
class Claim:
    id: str
    role: ClaimRole
    text: str
    scope: str
    status: ClaimStatus = ClaimStatus.UNVERIFIED
    assessments: List[Assessment] = field(default_factory=list)

    def __post_init__(self) -> None:
        validate_id(self.id, "claim.id")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role.value,
            "text": self.text,
            "scope": self.scope,
            "status": self.status.value,
            "assessments": [a.to_dict() for a in self.assessments],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Claim:
        return cls(
            id=validate_id(data["id"], "claim.id"),
            role=ClaimRole(data["role"]),
            text=str(data["text"]),
            scope=str(data["scope"]),
            status=ClaimStatus(data.get("status", ClaimStatus.UNVERIFIED.value)),
            assessments=[Assessment.from_dict(a) for a in data.get("assessments", [])],
        )


@dataclass(frozen=True)
class Lens:
    id: str
    label: str
    rationale: str
    origin: LensOrigin
    status: LensStatus = LensStatus.ACTIVE

    def __post_init__(self) -> None:
        validate_id(self.id, "lens.id")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "rationale": self.rationale,
            "origin": self.origin.value,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Lens:
        return cls(
            id=validate_id(data["id"], "lens.id"),
            label=str(data["label"]),
            rationale=str(data["rationale"]),
            origin=LensOrigin(data["origin"]),
            status=LensStatus(data.get("status", LensStatus.ACTIVE.value)),
        )


@dataclass(frozen=True)
class Resolution:
    reason: ResolutionReason
    evidence_ids: List[str]
    explanation: str

    def __post_init__(self) -> None:
        if not self.evidence_ids:
            raise ValueError("Resolution requires at least one evidence item")
        for eid in self.evidence_ids:
            validate_id(eid, "resolution.evidence_ids")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reason": self.reason.value,
            "evidenceIds": list(self.evidence_ids),
            "explanation": self.explanation,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Resolution:
        return cls(
            reason=ResolutionReason(data["reason"]),
            evidence_ids=[validate_id(x, "resolution.evidenceIds") for x in data["evidenceIds"]],
            explanation=str(data["explanation"]),
        )


@dataclass
class Gap:
    id: str
    kind: GapKind
    lens_id: str
    question: str
    trigger_refs: List[str]
    why_it_matters: str
    importance: GapImportance
    claim_ids: List[str]
    probe_ids: List[str] = field(default_factory=list)
    status: GapStatus = GapStatus.OPEN
    resolution: Optional[Resolution] = None

    def __post_init__(self) -> None:
        validate_id(self.id, "gap.id")
        validate_id(self.lens_id, "gap.lens_id")
        if not self.trigger_refs:
            raise ValueError("Gap requires at least one trigger reference")
        if (self.status == GapStatus.RESOLVED) != (self.resolution is not None):
            raise ValueError("Only resolved gaps require resolution")

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "id": self.id,
            "kind": self.kind.value,
            "lensId": self.lens_id,
            "question": self.question,
            "triggerRefs": list(self.trigger_refs),
            "whyItMatters": self.why_it_matters,
            "importance": self.importance.value,
            "claimIds": list(self.claim_ids),
            "probeIds": list(self.probe_ids),
            "status": self.status.value,
        }
        if self.resolution is not None:
            result["resolution"] = self.resolution.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Gap:
        res = Resolution.from_dict(data["resolution"]) if data.get("resolution") is not None else None
        return cls(
            id=validate_id(data["id"], "gap.id"),
            kind=GapKind(data["kind"]),
            lens_id=validate_id(data["lensId"], "gap.lensId"),
            question=str(data["question"]),
            trigger_refs=[str(x) for x in data["triggerRefs"]],
            why_it_matters=str(data["whyItMatters"]),
            importance=GapImportance(data["importance"]),
            claim_ids=[validate_id(x, "gap.claimIds") for x in data.get("claimIds", [])],
            probe_ids=[validate_id(x, "gap.probeIds") for x in data.get("probeIds", [])],
            status=GapStatus(data.get("status", GapStatus.OPEN.value)),
            resolution=res,
        )


@dataclass
class Probe:
    id: str
    gap_ids: List[str]
    method: ProbeMethod
    question: str
    required_capability: str
    source_groups: List[str]
    success_condition: str
    refutation_condition: str
    inconclusive_condition: str
    status: ProbeStatus = ProbeStatus.PENDING

    def __post_init__(self) -> None:
        validate_id(self.id, "probe.id")
        if not self.gap_ids:
            raise ValueError("Probe must address at least one gap")
        for gid in self.gap_ids:
            validate_id(gid, "probe.gap_ids")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "gapIds": list(self.gap_ids),
            "method": self.method.value,
            "question": self.question,
            "requiredCapability": self.required_capability,
            "sourceGroups": list(self.source_groups),
            "successCondition": self.success_condition,
            "refutationCondition": self.refutation_condition,
            "inconclusiveCondition": self.inconclusive_condition,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Probe:
        return cls(
            id=validate_id(data["id"], "probe.id"),
            gap_ids=[validate_id(x, "probe.gapIds") for x in data["gapIds"]],
            method=ProbeMethod(data["method"]),
            question=str(data["question"]),
            required_capability=str(data["requiredCapability"]),
            source_groups=[str(x) for x in data.get("sourceGroups", [])],
            success_condition=str(data["successCondition"]),
            refutation_condition=str(data["refutationCondition"]),
            inconclusive_condition=str(data["inconclusiveCondition"]),
            status=ProbeStatus(data.get("status", ProbeStatus.PENDING.value)),
        )


@dataclass(frozen=True)
class TaskPacket:
    schema_version: str
    task_id: str
    goal: str
    mode: str
    success_criteria: List[str]
    evidence: List[Evidence]
    capabilities: List[str]
    budget: Budget
    proposed_answer: Optional[str] = None
    proposed_actions: Optional[List[str]] = None

    def __post_init__(self) -> None:
        validate_id(self.task_id, "task_packet.task_id")
        if not self.success_criteria:
            raise ValueError("TaskPacket must specify at least one success criterion")

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "schemaVersion": self.schema_version,
            "taskId": self.task_id,
            "goal": self.goal,
            "mode": self.mode,
            "successCriteria": list(self.success_criteria),
            "evidence": [e.to_dict() for e in self.evidence],
            "capabilities": list(self.capabilities),
            "budget": self.budget.to_dict(),
        }
        if self.proposed_answer is not None:
            result["proposedAnswer"] = self.proposed_answer
        if self.proposed_actions is not None:
            result["proposedActions"] = list(self.proposed_actions)
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TaskPacket:
        return cls(
            schema_version=str(data.get("schemaVersion", "0.1")),
            task_id=validate_id(data["taskId"], "task_packet.taskId"),
            goal=str(data["goal"]),
            mode=str(data.get("mode", "explain")),
            success_criteria=[str(x) for x in data["successCriteria"]],
            evidence=[Evidence.from_dict(e) for e in data.get("evidence", [])],
            capabilities=[str(c) for c in data.get("capabilities", [])],
            budget=Budget.from_dict(data["budget"]),
            proposed_answer=data.get("proposedAnswer"),
            proposed_actions=data.get("proposedActions"),
        )


@dataclass(frozen=True)
class Observation:
    execution_id: str
    probe_id: str
    outcome: ObservationOutcome
    evidence: List[Evidence]
    tool_calls: int
    elapsed_ms: float
    cost_yen: Optional[float] = None
    total_tokens: Optional[int] = None
    raw_output: Optional[str] = None

    def __post_init__(self) -> None:
        validate_id(self.execution_id, "observation.execution_id")
        validate_id(self.probe_id, "observation.probe_id")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "executionId": self.execution_id,
            "probeId": self.probe_id,
            "outcome": self.outcome.value,
            "evidence": [e.to_dict() for e in self.evidence],
            "toolCalls": self.tool_calls,
            "elapsedMs": self.elapsed_ms,
            "costYen": self.cost_yen,
            "totalTokens": self.total_tokens,
            "rawOutput": self.raw_output,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Observation:
        return cls(
            execution_id=validate_id(data["executionId"], "observation.executionId"),
            probe_id=validate_id(data["probeId"], "observation.probeId"),
            outcome=ObservationOutcome(data["outcome"]),
            evidence=[Evidence.from_dict(e) for e in data.get("evidence", [])],
            tool_calls=int(data.get("toolCalls", 0)),
            elapsed_ms=float(data.get("elapsedMs", 0.0)),
            cost_yen=float(data["costYen"]) if data.get("costYen") is not None else None,
            total_tokens=int(data["totalTokens"]) if data.get("totalTokens") is not None else None,
            raw_output=data.get("rawOutput"),
        )


@dataclass(frozen=True)
class AppliedExecution:
    execution_id: str
    payload_hash: str
    probe_id: str
    outcome: ObservationOutcome

    def __post_init__(self) -> None:
        validate_id(self.execution_id, "applied_execution.execution_id")
        validate_sha256(self.payload_hash, "applied_execution.payload_hash")
        validate_id(self.probe_id, "applied_execution.probe_id")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "executionId": self.execution_id,
            "payloadHash": self.payload_hash,
            "probeId": self.probe_id,
            "outcome": self.outcome.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AppliedExecution:
        return cls(
            execution_id=validate_id(data["executionId"], "applied_execution.executionId"),
            payload_hash=validate_sha256(data["payloadHash"], "applied_execution.payloadHash"),
            probe_id=validate_id(data["probeId"], "applied_execution.probeId"),
            outcome=ObservationOutcome(data["outcome"]),
        )


@dataclass
class UnderstandingState:
    schema_version: str
    task_id: str
    revision: int
    started_at: str
    task: TaskPacket
    evidence: List[Evidence] = field(default_factory=list)
    claims: List[Claim] = field(default_factory=list)
    lenses: List[Lens] = field(default_factory=list)
    gaps: List[Gap] = field(default_factory=list)
    probes: List[Probe] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    decision: Decision = Decision.NEEDS_CHECK
    stop_reason: Optional[str] = None
    applied_executions: List[AppliedExecution] = field(default_factory=list)
    pending_assessment_execution_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "taskId": self.task_id,
            "revision": self.revision,
            "startedAt": self.started_at,
            "task": self.task.to_dict(),
            "evidence": [e.to_dict() for e in self.evidence],
            "claims": [c.to_dict() for c in self.claims],
            "lenses": [l.to_dict() for l in self.lenses],
            "gaps": [g.to_dict() for g in self.gaps],
            "probes": [p.to_dict() for p in self.probes],
            "usage": self.usage.to_dict(),
            "decision": self.decision.value,
            "stopReason": self.stop_reason,
            "appliedExecutions": [a.to_dict() for a in self.applied_executions],
            "pendingAssessmentExecutionIds": list(self.pending_assessment_execution_ids),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> UnderstandingState:
        return cls(
            schema_version=str(data.get("schemaVersion", "0.1")),
            task_id=validate_id(data["taskId"], "state.taskId"),
            revision=int(data.get("revision", 0)),
            started_at=str(data["startedAt"]),
            task=TaskPacket.from_dict(data["task"]),
            evidence=[Evidence.from_dict(e) for e in data.get("evidence", [])],
            claims=[Claim.from_dict(c) for c in data.get("claims", [])],
            lenses=[Lens.from_dict(l) for l in data.get("lenses", [])],
            gaps=[Gap.from_dict(g) for g in data.get("gaps", [])],
            probes=[Probe.from_dict(p) for p in data.get("probes", [])],
            usage=Usage.from_dict(data.get("usage", {})),
            decision=Decision(data.get("decision", Decision.NEEDS_CHECK.value)),
            stop_reason=data.get("stopReason"),
            applied_executions=[AppliedExecution.from_dict(a) for a in data.get("appliedExecutions", [])],
            pending_assessment_execution_ids=data.get("pendingAssessmentExecutionIds", []),
        )


@dataclass
class Proposal:
    claims: Optional[List[Claim]] = None
    lenses: Optional[List[Lens]] = None
    gaps: Optional[List[Gap]] = None
    probes: Optional[List[Probe]] = None
    assessments: Optional[List[Assessment]] = None
    resolutions: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        res: Dict[str, Any] = {}
        if self.claims is not None:
            res["claims"] = [c.to_dict() for c in self.claims]
        if self.lenses is not None:
            res["lenses"] = [l.to_dict() for l in self.lenses]
        if self.gaps is not None:
            res["gaps"] = [g.to_dict() for g in self.gaps]
        if self.probes is not None:
            res["probes"] = [p.to_dict() for p in self.probes]
        if self.assessments is not None:
            res["assessments"] = [a.to_dict() for a in self.assessments]
        if self.resolutions is not None:
            res["resolutions"] = self.resolutions
        return res


@dataclass
class LedgerEntry:
    timestamp: str
    stage: LedgerStage
    execution_id: str
    task_id: str
    condition: ConditionType
    input_payload_hash: str
    output_payload_hash: str
    model: Optional[str]
    usage: Usage
    status: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "stage": self.stage.value,
            "executionId": self.execution_id,
            "taskId": self.task_id,
            "condition": self.condition.value,
            "inputPayloadHash": self.input_payload_hash,
            "outputPayloadHash": self.output_payload_hash,
            "model": self.model,
            "usage": self.usage.to_dict(),
            "status": self.status,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LedgerEntry:
        return cls(
            timestamp=str(data["timestamp"]),
            stage=LedgerStage(data["stage"]),
            execution_id=validate_id(data["executionId"], "ledger.executionId"),
            task_id=validate_id(data["taskId"], "ledger.taskId"),
            condition=ConditionType(data["condition"]),
            input_payload_hash=validate_sha256(data["inputPayloadHash"], "ledger.inputPayloadHash"),
            output_payload_hash=validate_sha256(data["outputPayloadHash"], "ledger.outputPayloadHash"),
            model=data.get("model"),
            usage=Usage.from_dict(data.get("usage", {})),
            status=str(data["status"]),
            notes=data.get("notes"),
        )


@dataclass(frozen=True)
class GoldStandard:
    """Separate objective evaluation rubric not visible to agents during execution."""
    task_id: str
    domain: str
    required_gap_questions: List[str]
    critical_evidence_hashes: List[str]
    expected_answer_keywords: List[str]
    ground_truth_verdicts: Dict[str, str]  # claim_id -> 'supported' | 'contradicted'
    target_decision: Decision

    def to_dict(self) -> Dict[str, Any]:
        return {
            "taskId": self.task_id,
            "domain": self.domain,
            "requiredGapQuestions": list(self.required_gap_questions),
            "criticalEvidenceHashes": list(self.critical_evidence_hashes),
            "expectedAnswerKeywords": list(self.expected_answer_keywords),
            "groundTruthVerdicts": dict(self.ground_truth_verdicts),
            "targetDecision": self.target_decision.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> GoldStandard:
        return cls(
            task_id=validate_id(data["taskId"], "gold.taskId"),
            domain=str(data["domain"]),
            required_gap_questions=[str(x) for x in data["requiredGapQuestions"]],
            critical_evidence_hashes=[validate_sha256(x, "gold.criticalEvidenceHashes") for x in data["criticalEvidenceHashes"]],
            expected_answer_keywords=[str(x) for x in data["expectedAnswerKeywords"]],
            ground_truth_verdicts={str(k): str(v) for k, v in data.get("groundTruthVerdicts", {}).items()},
            target_decision=Decision(data["targetDecision"]),
        )


@dataclass
class EvaluationMetricRecord:
    task_id: str
    condition: ConditionType
    run_id: str
    final_decision_success: int  # 0 or 1
    required_gap_recall: float   # 0.0 to 1.0 (exact denominator)
    unnecessary_check_rate: float
    valid_evidence_count: int
    contradiction_detection_rate: float
    usage: Usage
    stage_breakdown: Dict[str, Usage] = field(default_factory=dict)
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "taskId": self.task_id,
            "condition": self.condition.value,
            "runId": self.run_id,
            "finalDecisionSuccess": self.final_decision_success,
            "requiredGapRecall": self.required_gap_recall,
            "unnecessaryCheckRate": self.unnecessary_check_rate,
            "validEvidenceCount": self.valid_evidence_count,
            "contradictionDetectionRate": self.contradiction_detection_rate,
            "usage": self.usage.to_dict(),
            "stageBreakdown": {k: v.to_dict() for k, v in self.stage_breakdown.items()},
            "notes": self.notes,
        }
