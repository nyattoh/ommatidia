"""Contracts and execution drivers for experimental conditions A through E."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Tuple

from ommatidia.state import (
    apply_observations,
    apply_proposal,
    create_initial_state,
    evaluate_stopping_conditions,
)
from ommatidia.types import (
    Budget,
    Claim,
    ClaimRole,
    ClaimStatus,
    ConditionType,
    Decision,
    Gap,
    GapImportance,
    GapKind,
    GapStatus,
    Lens,
    LensOrigin,
    Observation,
    Probe,
    ProbeMethod,
    ProbeStatus,
    Proposal,
    TaskPacket,
    UnderstandingState,
    Usage,
)


def _accumulate_step_usage(usage: Usage, step_output: Dict[str, Any]) -> None:
    """Helper to accumulate step resource consumption without double-counting rounds."""
    if "usage" in step_output:
        raw_u = step_output["usage"]
        step_u = Usage.from_dict(raw_u) if isinstance(raw_u, dict) else Usage()
        usage.model_calls += step_u.model_calls
        usage.tool_calls += step_u.tool_calls
        usage.elapsed_ms += step_u.elapsed_ms
        if step_u.cost_yen is not None:
            usage.cost_yen = (usage.cost_yen or 0.0) + step_u.cost_yen
        if step_u.total_tokens is not None:
            usage.total_tokens = (usage.total_tokens or 0) + step_u.total_tokens


class BaseConditionRunner(ABC):
    """Abstract base class defining the contract for experimental conditions A-E."""

    def __init__(self, condition_type: ConditionType) -> None:
        self.condition_type = condition_type

    @abstractmethod
    def run(
        self,
        task: TaskPacket,
        executor_func: Callable[[str, Dict[str, Any]], Dict[str, Any]],
    ) -> UnderstandingState:
        """Execute the condition on the given task packet using the provided step executor."""
        pass


class ConditionARunner(BaseConditionRunner):
    """Condition A: Standard baseline single-pass investigation.

    Conducts an ordinary exploration without structured perspective lenses
    or multi-round gap inspection loops.
    """

    def __init__(self) -> None:
        super().__init__(ConditionType.A)

    def run(
        self,
        task: TaskPacket,
        executor_func: Callable[[str, Dict[str, Any]], Dict[str, Any]],
    ) -> UnderstandingState:
        state = create_initial_state(task)
        state.usage.rounds = 1

        step_output = executor_func("single_pass_investigation", {
            "taskId": task.task_id,
            "goal": task.goal,
            "evidence": [e.to_dict() for e in task.evidence],
            "capabilities": list(task.capabilities),
        })

        _accumulate_step_usage(state.usage, step_output)

        # Ingest claim or answer
        ans_text = step_output.get("answer", task.proposed_answer or "Baseline conclusion")
        claim = Claim(
            id=f"claim_{task.task_id}_01",
            role=ClaimRole.ANSWER_CLAIM,
            text=ans_text,
            scope="global",
            status=ClaimStatus.SUPPORTED if step_output.get("success", True) else ClaimStatus.UNVERIFIED,
        )
        state.claims.append(claim)
        state.decision = Decision.READY_FOR_REQUESTED_STEP
        state.stop_reason = "single_pass_complete"
        return state


class ConditionBRunner(BaseConditionRunner):
    """Condition B: Generic re-examination.

    Executes a standard first pass followed by a generic second-pass check
    (prompted to re-check for counterexamples, boundaries, and missing facts)
    without dedicated perspective role structuring.
    """

    def __init__(self) -> None:
        super().__init__(ConditionType.B)

    def run(
        self,
        task: TaskPacket,
        executor_func: Callable[[str, Dict[str, Any]], Dict[str, Any]],
    ) -> UnderstandingState:
        state = create_initial_state(task)

        # Pass 1: Standard query
        state.usage.rounds = 1
        p1_output = executor_func("pass1_investigation", {
            "taskId": task.task_id,
            "goal": task.goal,
            "evidence": [e.to_dict() for e in task.evidence],
        })
        _accumulate_step_usage(state.usage, p1_output)

        # Pass 2: Generic re-examination check
        state.usage.rounds = 2
        p2_output = executor_func("generic_recheck", {
            "taskId": task.task_id,
            "priorOutput": p1_output,
            "checkInstruction": "Re-check for counterexamples, missing constraints, or edge cases.",
        })
        _accumulate_step_usage(state.usage, p2_output)

        # Ingest re-examined conclusions
        ans = p2_output.get("finalAnswer", p1_output.get("answer", "Rechecked conclusion"))
        claim = Claim(
            id=f"claim_{task.task_id}_01",
            role=ClaimRole.ANSWER_CLAIM,
            text=ans,
            scope="global",
            status=ClaimStatus.SUPPORTED,
        )
        state.claims.append(claim)
        state.decision = Decision.READY_FOR_REQUESTED_STEP
        state.stop_reason = "reexamination_complete"
        return state


class ConditionCRunner(BaseConditionRunner):
    """Condition C: Fixed perspectives.

    Investigates across a fixed, pre-defined catalogue of perspective lenses
    (e.g., boundary conditions, counterexamples, chronological shift) regardless of task context.
    """

    DEFAULT_FIXED_LENSES = [
        ("lens_fixed_boundary", "Boundary conditions and limits", "Check extreme values and preconditions"),
        ("lens_fixed_counter", "Counterexample search", "Search for contradictory cases"),
        ("lens_fixed_temporal", "Chronological differences", "Examine version or timestamp shifts"),
    ]

    def __init__(self, fixed_lenses: Optional[List[Tuple[str, str, str]]] = None) -> None:
        super().__init__(ConditionType.C)
        self.fixed_lenses = fixed_lenses or self.DEFAULT_FIXED_LENSES

    def run(
        self,
        task: TaskPacket,
        executor_func: Callable[[str, Dict[str, Any]], Dict[str, Any]],
    ) -> UnderstandingState:
        state = create_initial_state(task)

        # Register fixed lenses
        for lid, label, rationale in self.fixed_lenses:
            state.lenses.append(Lens(
                id=lid,
                label=label,
                rationale=rationale,
                origin=LensOrigin.INITIAL,
            ))

        # Query each fixed lens
        for lens in state.lenses:
            if state.usage.exceeds(task.budget):
                state.stop_reason = "budget_exhausted"
                state.decision = Decision.BLOCKED
                return state

            state.usage.rounds += 1
            step_out = executor_func("fixed_lens_query", {
                "taskId": task.task_id,
                "lensId": lens.id,
                "lensLabel": lens.label,
            })
            _accumulate_step_usage(state.usage, step_out)

            if "observations" in step_out:
                for obs_dict in step_out["observations"]:
                    obs = Observation.from_dict(obs_dict)
                    apply_observations(state, [obs])

        state.decision = Decision.READY_FOR_REQUESTED_STEP
        state.stop_reason = "fixed_lenses_complete"
        return state


class ConditionDRunner(BaseConditionRunner):
    """Condition D: Single adaptive investigator.

    Uses typed understanding state, gap identification, and probe checks,
    but executes all investigations sequentially through a single adaptive investigator role.
    """

    def __init__(self) -> None:
        super().__init__(ConditionType.D)

    def run(
        self,
        task: TaskPacket,
        executor_func: Callable[[str, Dict[str, Any]], Dict[str, Any]],
    ) -> UnderstandingState:
        state = create_initial_state(task)

        while True:
            should_stop, reason, decision = evaluate_stopping_conditions(state, task.budget)
            if should_stop:
                state.stop_reason = reason
                state.decision = decision
                break

            state.usage.rounds += 1

            # Step 1: Sequential adaptive planning step
            plan_out = executor_func("adaptive_plan_step", {
                "state": state.to_dict(),
                "role": "single_investigator",
            })
            _accumulate_step_usage(state.usage, plan_out)

            if "proposal" in plan_out:
                proposal_data = plan_out["proposal"]
                prop = Proposal(
                    claims=[Claim.from_dict(c) for c in proposal_data.get("claims", [])],
                    lenses=[Lens.from_dict(l) for l in proposal_data.get("lenses", [])],
                    gaps=[Gap.from_dict(g) for g in proposal_data.get("gaps", [])],
                    probes=[Probe.from_dict(p) for p in proposal_data.get("probes", [])],
                    resolutions=proposal_data.get("resolutions"),
                )
                apply_proposal(state, prop)

            # Step 2: Sequential probe execution (one probe at a time)
            pending = [p for p in state.probes if p.status == ProbeStatus.PENDING]
            if not pending:
                state.stop_reason = "no_pending_probes"
                state.decision = Decision.READY_FOR_REQUESTED_STEP
                break

            target_probe = pending[0]
            exec_out = executor_func("single_investigator_exec", {
                "probe": target_probe.to_dict(),
                "role": "single_investigator",
            })
            _accumulate_step_usage(state.usage, exec_out)

            if "observations" in exec_out:
                obs_list = [Observation.from_dict(o) for o in exec_out["observations"]]
                apply_observations(state, obs_list)

        return state


class ConditionERunner(BaseConditionRunner):
    """Condition E: Ommatidia multi-perspective structured investigation.

    Dynamically constructs perspective lenses and focused probe roles
    grounded in the typed understanding state, coordinating cross-collation of evidence.
    """

    def __init__(self, max_concurrent_roles: int = 3) -> None:
        super().__init__(ConditionType.E)
        self.max_concurrent_roles = max_concurrent_roles

    def run(
        self,
        task: TaskPacket,
        executor_func: Callable[[str, Dict[str, Any]], Dict[str, Any]],
    ) -> UnderstandingState:
        state = create_initial_state(task)

        while True:
            should_stop, reason, decision = evaluate_stopping_conditions(state, task.budget)
            if should_stop:
                state.stop_reason = reason
                state.decision = decision
                break

            state.usage.rounds += 1

            # Step 1: Understanding-state inspection and perspective proposal
            inspect_out = executor_func("ommatidia_inspect", {
                "state": state.to_dict(),
                "maxRoles": self.max_concurrent_roles,
            })
            _accumulate_step_usage(state.usage, inspect_out)

            if "proposal" in inspect_out:
                proposal_data = inspect_out["proposal"]
                prop = Proposal(
                    claims=[Claim.from_dict(c) for c in proposal_data.get("claims", [])],
                    lenses=[Lens.from_dict(l) for l in proposal_data.get("lenses", [])],
                    gaps=[Gap.from_dict(g) for g in proposal_data.get("gaps", [])],
                    probes=[Probe.from_dict(p) for p in proposal_data.get("probes", [])],
                    resolutions=proposal_data.get("resolutions"),
                )
                apply_proposal(state, prop)

            # Step 2: Targeted investigation of pending probes
            pending = [p for p in state.probes if p.status == ProbeStatus.PENDING]
            if not pending:
                state.stop_reason = "probes_completed"
                state.decision = Decision.READY_FOR_REQUESTED_STEP
                break

            # Bounded batch of probes allocated to perspective roles
            batch = pending[:self.max_concurrent_roles]
            exec_out = executor_func("ommatidia_investigate_batch", {
                "probes": [p.to_dict() for p in batch],
                "activeLenses": [l.to_dict() for l in state.lenses if l.status.value == "active"],
            })
            _accumulate_step_usage(state.usage, exec_out)

            if "observations" in exec_out:
                obs_list = [Observation.from_dict(o) for o in exec_out["observations"]]
                apply_observations(state, obs_list)

        return state
