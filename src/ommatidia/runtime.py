"""Executable condition graph outside the historical frozen runners."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
import hashlib
import json
import math

from ommatidia import conditions as prompts
from ommatidia.ingestion import (
    ingest_final_judgement,
    ingest_observations,
    ingest_proposal,
)
from ommatidia.state import (
    apply_observations,
    apply_proposal,
    create_initial_state,
    evaluate_stopping_conditions,
)
from ommatidia.types import (
    ConditionType,
    Decision,
    FinalJudgement,
    FinalJudgementResourceUsage,
    ProbeStatus,
)


from ommatidia.contracts import FINAL_SCHEMA, OBSERVATION_SCHEMA, PROPOSAL_SCHEMA

DISPATCH_INSTRUCTION = (
    "Use only supplied public material and the isolated public source tools. "
    "Do not inspect evaluator files. Perform one model invocation; do not spawn children. "
    "Return the supplied responseSchema. All tool use must respect the step budget."
)


@dataclass(frozen=True)
class Step:
    name: str
    prompt: str
    kind: str
    lens: str = ""

    @property
    def schema(self):
        return {
            "final": FINAL_SCHEMA,
            "proposal": PROPOSAL_SCHEMA,
            "observations": OBSERVATION_SCHEMA,
        }[self.kind]


def condition_graph(condition):
    if condition == ConditionType.A:
        return [Step("single_pass_investigation", prompts.PROMPT_CONDITION_A, "final")]
    if condition == ConditionType.B:
        return [
            Step("pass1_investigation", prompts.PROMPT_CONDITION_B_PHASE1, "final"),
            Step("generic_recheck", prompts.PROMPT_CONDITION_B_PHASE2, "final"),
        ]
    if condition == ConditionType.C:
        return [
            Step("fixed_lens_query", prompts.PROMPT_CONDITION_C, "observations", label)
            for _, label, _ in prompts.ConditionCRunner.DEFAULT_FIXED_LENSES
        ] + [Step("fixed_synthesis", prompts.PROMPT_CONDITION_C, "final")]
    if condition == ConditionType.D:
        return [
            Step("adaptive_plan_step", prompts.PROMPT_CONDITION_D, "proposal"),
            Step(
                "single_investigator_exec", prompts.PROMPT_CONDITION_D, "observations"
            ),
            Step("adaptive_synthesis", prompts.PROMPT_CONDITION_D, "final"),
        ]
    return [
        Step("ommatidia_inspect", prompts.PROMPT_CONDITION_E_COORDINATOR, "proposal"),
        Step(
            "ommatidia_investigator",
            prompts.PROMPT_CONDITION_E_INVESTIGATOR,
            "observations",
        ),
        Step("ommatidia_synthesis", prompts.PROMPT_CONDITION_E_SYNTHESIS, "final"),
    ]


def check_public_payload(value):
    """Reject evaluator fields and private file locators without loading any answer key."""
    forbidden = {
        "gold",
        "groundtruthverdicts",
        "criticalevidencehashes",
        "targetdecision",
        "answerkey",
        "unblindingkey",
        "requiredgapquestions",
    }
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower().replace("_", "") in forbidden:
                raise ValueError(f"Evaluator field in public payload: {key}")
            check_public_payload(item)
    elif isinstance(value, list):
        for item in value:
            check_public_payload(item)
    elif isinstance(value, str):
        normal = value.lower().replace("\\", "/")
        if (
            any(part in {"gold", "cases"} for part in normal.split("/"))
            or "unblinding_key.json" in normal
        ):
            raise ValueError("Private locator in public payload")


def validate_proposal_shape(output):
    """Require the fields marked required by PROPOSAL_SCHEMA before ingestion."""
    if not isinstance(output, dict):
        raise ValueError("Invalid proposal response object")

    for field in PROPOSAL_SCHEMA.get("required", []):
        if field not in output:
            raise ValueError("Missing proposal")

    proposal = output.get("proposal")
    if not isinstance(proposal, dict):
        raise ValueError("Invalid proposal object")

    proposal_schema = PROPOSAL_SCHEMA["properties"]["proposal"]
    properties = proposal_schema.get("properties", {})
    for field in proposal_schema.get("required", []):
        field_schema = properties.get(field, {})
        if field not in proposal:
            raise ValueError(f"Missing required proposal field: {field}")
        if field_schema.get("type") == "array" and not isinstance(
            proposal[field], list
        ):
            raise ValueError(f"Required proposal field must be an array: {field}")


def step_payload(task, condition, step, sequence, run_id, context=None):
    payload = {
        "taskId": task.task_id,
        "condition": condition.value,
        "stepName": step.name,
        "stepSequence": sequence,
        "systemPrompt": step.prompt,
        "goal": task.goal,
        "mode": task.mode,
        "proposedAnswer": task.proposed_answer,
        "successCriteria": task.success_criteria,
        "evidence": [e.to_dict() for e in task.evidence],
        "capabilities": task.capabilities,
        "budget": task.budget.to_dict(),
        "responseSchema": step.schema,
        "context": context or {},
    }
    # Legacy packets without the fields keep their original payload shape.
    if task.domain is not None:
        payload["domain"] = task.domain
    if task.available_sources is not None:
        payload["availableSources"] = task.sources_dict()
    payload["clientRequestId"] = (
        "ommatidia_"
        + hashlib.sha256(
            f"{run_id}/{task.task_id}/{condition.value}/{sequence}".encode()
        ).hexdigest()
    )
    if step.lens:
        payload["lensLabel"] = step.lens
    check_public_payload(payload)
    return payload


def render_prompt(payload):
    check_public_payload(payload)
    return DISPATCH_INSTRUCTION + "\n" + json.dumps(payload, sort_keys=True)


def inconclusive(task_id, usage, reason):
    return FinalJudgement(
        task_id,
        "inconclusive",
        0.0,
        reason,
        [],
        [],
        FinalJudgementResourceUsage(
            usage.model_calls, usage.tool_calls, usage.elapsed_ms, usage.input_chars
        ),
    )


def final_response(output, task_id):
    data = output.get("finalJudgement", output)
    if not isinstance(data, dict) or not set(FINAL_SCHEMA["required"]).issubset(data):
        raise ValueError("Incomplete FinalJudgement")
    if not isinstance(data["justification"], str) or not data["justification"].strip():
        raise ValueError("Empty justification")
    if not isinstance(data["citedEvidence"], list) or not isinstance(
        data["unresolvedGaps"], list
    ):
        raise ValueError("Invalid FinalJudgement arrays")
    if isinstance(data["confidenceScore"], bool) or not isinstance(
        data["confidenceScore"], (int, float)
    ):
        raise ValueError("Invalid confidenceScore")
    if not isinstance(data["resourceUsage"], dict) or not {
        "modelCalls",
        "toolCalls",
        "elapsedMs",
        "inputCharsEstimated",
    }.issubset(data["resourceUsage"]):
        raise ValueError("Incomplete FinalJudgement resourceUsage")
    for key, value in data["resourceUsage"].items():
        if key in ("modelCalls", "toolCalls", "inputCharsEstimated"):
            if type(value) is not int or value < 0:
                raise ValueError("Invalid FinalJudgement resource count")
        elif key == "elapsedMs" and (
            type(value) not in (int, float) or not math.isfinite(value) or value < 0
        ):
            raise ValueError("Invalid FinalJudgement elapsed time")
    if any(not isinstance(gap, str) for gap in data["unresolvedGaps"]):
        raise ValueError("Invalid unresolved gap")
    for item in data["citedEvidence"]:
        if not isinstance(item, dict) or not {
            "id",
            "sourceGroup",
            "locator",
            "contentHash",
            "passage",
            "verdictRelation",
        }.issubset(item):
            raise ValueError("Incomplete citation")
        if any(
            not isinstance(item[key], str)
            for key in (
                "id",
                "sourceGroup",
                "locator",
                "contentHash",
                "passage",
                "verdictRelation",
            )
        ):
            raise ValueError("Invalid citation field type")
    fj = ingest_final_judgement(data)
    if fj.task_id != task_id:
        raise ValueError("FinalJudgement taskId mismatch")
    return fj


def execute_graph(task, condition, run_id, executor, usage_getter, state=None):
    state = state or create_initial_state(task)
    graph = condition_graph(condition)
    sequence = 0
    invalid = []

    def execute(step, context):
        nonlocal sequence
        sequence += 1
        payload = step_payload(task, condition, step, sequence, run_id, context)
        output = executor(step.name, payload)
        state.usage = usage_getter()
        return output

    def observations(output, allowed=None):
        items = ingest_observations(output)
        if allowed is not None and any(obs.probe_id not in allowed for obs in items):
            raise ValueError("Observation returned for an unassigned probe")
        for observation in items:
            for evidence in observation.evidence:
                if (
                    hashlib.sha256(evidence.passage.encode()).hexdigest()
                    != evidence.content_hash
                ):
                    raise ValueError(
                        "Observation passage does not match its content hash"
                    )
        apply_observations(state, items)

    if condition in (ConditionType.A, ConditionType.B):
        prior = None
        for step in graph:
            output = execute(step, {"priorOutput": prior} if prior is not None else {})
            if "proposal" in output:
                proposal, _ = ingest_proposal(output)
                apply_proposal(state, proposal)
            if "observations" in output:
                observations(output)
            try:
                state.final_judgement = final_response(output, task.task_id)
            except ValueError as exc:
                invalid.append(str(exc))
                state.final_judgement = inconclusive(
                    task.task_id, state.usage, str(exc)
                )
            prior = output
    elif condition == ConditionType.C:
        for step in graph[:-1]:
            observations(execute(step, {"state": state.to_dict()}))
        output = execute(graph[-1], {"state": state.to_dict()})
        try:
            state.final_judgement = final_response(output, task.task_id)
        except ValueError as exc:
            invalid.append(str(exc))
            state.final_judgement = inconclusive(task.task_id, state.usage, str(exc))
    else:
        while usage_getter().model_calls + 2 < min(8, task.budget.max_model_calls):
            output = execute(
                graph[0],
                {
                    "state": state.to_dict(),
                    "maxRoles": 1 if condition == ConditionType.D else 3,
                },
            )
            validate_proposal_shape(output)
            proposal, _ = ingest_proposal(output)
            known_probes = {probe.id: probe for probe in state.probes}
            if proposal.probes:
                for probe in proposal.probes:
                    if (
                        probe.id in known_probes
                        and probe.question != known_probes[probe.id].question
                    ):
                        raise ValueError(
                            "Existing probe ID cannot be reused for a different question"
                        )
                proposal = replace(
                    proposal,
                    probes=[
                        probe
                        for probe in proposal.probes
                        if probe.id not in known_probes
                    ],
                )
            apply_proposal(state, proposal)
            pending = [
                probe for probe in state.probes if probe.status == ProbeStatus.PENDING
            ]
            if not pending:
                break
            slots = min(
                1 if condition == ConditionType.D else 3,
                min(8, task.budget.max_model_calls) - usage_getter().model_calls - 1,
            )
            selected = pending[:slots]
            if condition == ConditionType.E and len(selected) > 1:
                allocation = max(
                    0, min(12, task.budget.max_tool_calls) - usage_getter().tool_calls
                ) // len(selected)
                payloads = []
                for probe in selected:
                    sequence += 1
                    payloads.append(
                        step_payload(
                            task,
                            condition,
                            graph[1],
                            sequence,
                            run_id,
                            {
                                "probe": probe.to_dict(),
                                "state": state.to_dict(),
                                "roleId": probe.id,
                                "maxRoles": len(selected),
                                "toolAllocation": allocation,
                            },
                        )
                    )
                with ThreadPoolExecutor(max_workers=min(3, len(selected))) as pool:
                    futures = [
                        pool.submit(executor, graph[1].name, payload)
                        for payload in payloads
                    ]
                    for probe, future in zip(selected, futures):
                        observations(future.result(), {probe.id})
                state.usage = usage_getter()
            else:
                for probe in selected:
                    output = execute(
                        graph[1],
                        {
                            "probe": probe.to_dict(),
                            "state": state.to_dict(),
                            "roleId": probe.id,
                            "maxRoles": slots,
                        },
                    )
                    observations(output, {probe.id})
            stop, reason, decision = evaluate_stopping_conditions(state, task.budget)
            if stop:
                state.stop_reason, state.decision = reason, decision
                break
        output = execute(graph[-1], {"state": state.to_dict()})
        try:
            state.final_judgement = final_response(output, task.task_id)
        except ValueError as exc:
            invalid.append(str(exc))
            state.final_judgement = inconclusive(task.task_id, state.usage, str(exc))
    state.usage = usage_getter()
    if invalid:
        state.final_judgement = inconclusive(
            task.task_id, state.usage, "; ".join(invalid)
        )
    state.final_judgement.resource_usage = FinalJudgementResourceUsage(
        state.usage.model_calls,
        state.usage.tool_calls,
        state.usage.elapsed_ms,
        state.usage.input_chars,
    )
    state.decision = Decision.BLOCKED if invalid else Decision.READY_FOR_REQUESTED_STEP
    state.stop_reason = (
        "invalid_response" if invalid else (state.stop_reason or "graph_complete")
    )
    return state, invalid
