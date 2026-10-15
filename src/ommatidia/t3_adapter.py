"""Injected T3 transport for the same executable graph as the harness.

Native T3 worktree isolation alone is insufficient: it inherits the parent commit.
A trusted controller must attest public-only files, one model invocation per step,
and host-enforced budgets before any child dispatch is permitted.
"""
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import time

from ommatidia.campaign import atomic_json
from ommatidia.ingestion import ingest_json_response
from ommatidia.runtime import FINAL_SCHEMA, condition_graph, render_prompt, step_payload

FINAL_JUDGEMENT_SCHEMA = FINAL_SCHEMA


class T3DelegationError(RuntimeError):
    pass


class CampaignAuditRequired(T3DelegationError):
    """Dispatch or cancellation was ambiguous; no further campaign work is safe."""


@dataclass
class DispatchReadyJob:
    job_id: str
    client_request_id: str
    task_id: str
    condition: str
    step_name: str
    target: dict
    prompt: str
    payload: dict
    budget: dict
    schema: dict = field(default_factory=lambda: dict(FINAL_SCHEMA))

    def to_dict(self):
        return {"jobId": self.job_id, "clientRequestId": self.client_request_id,
                "taskId": self.task_id, "condition": self.condition, "stepName": self.step_name,
                "target": self.target, "prompt": self.prompt, "payload": self.payload,
                "budget": self.budget, "schema": self.schema,
                "isTemplate": True, "execution": "ResearchHarness executable graph only"}

    @classmethod
    def from_dict(cls, data):
        return cls(data["jobId"], data["clientRequestId"], data["taskId"], data["condition"],
                   data["stepName"], data["target"], data["prompt"], data["payload"], data["budget"], data["schema"])


def create_condition_dispatch_jobs(task, condition, run_id, provider_instance_id="agy", model_id="gemini-3.8-flash-high"):
    jobs = []
    graph = condition_graph(condition)
    for index, step in enumerate(graph, 1):
        payload = step_payload(task, condition, step, index, run_id, {
            "dependsOn": graph[index-2].name if index > 1 else None,
            "materialisation": "previous responses and updated state are supplied at execution",
            "repeat": "bounded adaptive loop" if step.kind == "proposal" else "per selected probe" if step.name == "ommatidia_investigator" else "once"})
        jobs.append(DispatchReadyJob("job_" + payload["clientRequestId"], payload["clientRequestId"],
                    task.task_id, condition.value, step.name,
                    {"providerInstanceId": provider_instance_id, "model": model_id},
                    render_prompt(payload), payload, task.budget.to_dict(), step.schema))
    return jobs


def create_condition_dispatch_job(*args, **kwargs):
    return create_condition_dispatch_jobs(*args, **kwargs)[0]


def export_campaign_dispatch_plan(tasks, conditions, run_id, output_path,
                                  provider_instance_id="agy", model_id="gemini-3.8-flash-high"):
    jobs = [job.to_dict() for task in tasks for condition in conditions
            for job in create_condition_dispatch_jobs(task, condition, run_id, provider_instance_id, model_id)]
    atomic_json(output_path, jobs)
    return jobs


def _unwrap(response):
    if not isinstance(response, dict):
        raise T3DelegationError("Transport returned no object")
    return response.get("structuredContent", response)


class T3DelegationAdapter:
    def __init__(self, provider_instance_id="agy", model_id="gemini-3.8-flash-high",
                 timeout_seconds=180.0, poll_interval_seconds=2.0,
                 in_session_dispatcher=None, public_boundary=None):
        self.provider_instance_id, self.model_id = provider_instance_id, model_id
        self.timeout_seconds, self.poll_interval_seconds = timeout_seconds, poll_interval_seconds
        self.in_session_dispatcher, self.public_boundary = in_session_dispatcher, public_boundary
        self.dispatch_observer = None

    def is_acp_cli_available(self):
        return bool(os.environ.get("T3_ACP_MCP_NODE"))

    def require_public_boundary(self):
        if self.in_session_dispatcher is None or self.public_boundary is None:
            raise T3DelegationError("Verified public-only dispatcher with host-enforced single-call budgets is required; ACP presence alone is insufficient")

    def delegate_step(self, step_name, payload, client_request_id=None, dispatch_observer=None):
        self.require_public_boundary()
        prompt = render_prompt(payload)
        if len(prompt) > 48000:
            raise T3DelegationError("Input character ceiling exceeded")
        attestation = self.public_boundary(payload)
        if not isinstance(attestation, dict) or not all(attestation.get(key) is True for key in
            ("publicOnly", "singleModelInvocation", "enforcesStepBudget", "hostUsageVerified")):
            raise T3DelegationError("Public workspace and host budget attestation failed")
        args = {"task": prompt, "target": {"providerInstanceId": self.provider_instance_id, "model": self.model_id},
                "isolation": "worktree", "mode": "async",
                "clientRequestId": client_request_id or payload["clientRequestId"]}
        try:
            response = _unwrap(self.in_session_dispatcher("delegate_task", args))
        except Exception as exc:
            raise CampaignAuditRequired("Dispatch acknowledgement lost; preserve reservation and audit the stable clientRequestId") from exc
        task_id = response.get("taskId")
        if not isinstance(task_id, str) or not task_id.strip() or task_id in ("None", "null"):
            raise CampaignAuditRequired("Missing delegated taskId; dispatch state is unknown")
        metadata = {"taskId": task_id, "providerInstanceId": response.get("providerInstanceId"),
                    "model": response.get("model"), "clientRequestId": args["clientRequestId"]}
        observer = dispatch_observer or self.dispatch_observer
        limit = min(self.timeout_seconds, payload["stepBudget"]["maxElapsedMs"] / 1000)
        deadline = time.monotonic() + limit
        try:
            if observer:
                observer(metadata)
            if metadata["providerInstanceId"] != self.provider_instance_id or metadata["model"] != self.model_id:
                raise T3DelegationError("Returned provider/model differs from selected study target")
            while time.monotonic() < deadline:
                status = _unwrap(self.in_session_dispatcher("task_status", {"taskId": task_id}))
                if status.get("status") == "completed":
                    raw = status.get("result") or status.get("summary") or status.get("latestTerminalSummary")
                    output = ingest_json_response(raw) if isinstance(raw, str) else raw
                    if not isinstance(output, dict):
                        raise T3DelegationError("Completed child returned no structured result")
                    output = dict(output)
                    output["_dispatch"] = metadata
                    host_usage = status.get("hostUsage")
                    if isinstance(host_usage, dict):
                        output["_hostUsage"] = host_usage
                    return output
                if status.get("status") in ("failed", "cancelled", "interrupted"):
                    raise T3DelegationError(f"Delegated task {task_id}: {status.get('status')}")
                if self.poll_interval_seconds:
                    time.sleep(min(self.poll_interval_seconds, max(0, deadline-time.monotonic())))
            raise TimeoutError(f"Delegated task {task_id} exceeded its deadline")
        except Exception:
            # Cancellation failure is surfaced; do not retry a child that might still spend.
            try:
                cancellation = _unwrap(self.in_session_dispatcher("task_cancel", {"taskId": task_id}))
            except Exception as exc:
                raise CampaignAuditRequired("Child cancellation failed; campaign audit required") from exc
            if cancellation.get("status") not in ("cancelled", "failed", "completed", "interrupted"):
                raise CampaignAuditRequired("Child cancellation unconfirmed; campaign audit required")
            raise


def create_t3_executor(adapter=None, fallback_executor=None):
    active = adapter or T3DelegationAdapter()

    def executor(step_name, payload):
        try:
            return active.delegate_step(step_name, payload,
                                        dispatch_observer=executor.dispatch_observers.get(payload.get("clientRequestId")))
        except Exception:
            if fallback_executor is not None:
                return fallback_executor(step_name, payload)
            raise
    executor.provider_instance_id, executor.model_id = active.provider_instance_id, active.model_id
    executor.dispatch_observers = {}
    executor.host_metered = True
    executor.synthetic_fallback = fallback_executor is not None
    executor.require_public_boundary = active.require_public_boundary
    return executor


class T3CampaignController:
    def __init__(self, dispatcher_func=None, public_boundary=None):
        self.adapter = T3DelegationAdapter(in_session_dispatcher=dispatcher_func, public_boundary=public_boundary)

    def run_cohort(self, harness, **kwargs):
        return harness.run_cohort(executor_func=create_t3_executor(self.adapter), executor_name="t3", **kwargs)

    def dispatch_job(self, job):
        raise T3DelegationError("Plan jobs are templates; use run_cohort for reservation, dependencies and result ingestion")
