"""Adapter bridging Ommatidia condition runners to T3 Code child delegation.

Constructs strict, sealed payloads with prepare_child_task_payload and executes
reasoning and investigation steps via T3 Code's delegate_task tool or ACP fallback.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from typing import Any, Callable, Dict, Optional

from ommatidia.ingestion import (
    ingest_json_response,
    prepare_child_task_payload,
)


class T3DelegationError(RuntimeError):
    """Raised when T3 child delegation fails or returns unparseable outputs."""
    pass


class T3DelegationAdapter:
    """Dispatches reasoning and investigation tasks to T3 Code child delegation."""

    def __init__(
        self,
        provider_instance_id: Optional[str] = None,
        model_id: Optional[str] = None,
        timeout_seconds: float = 300.0,
        poll_interval_seconds: float = 2.0,
    ) -> None:
        self.provider_instance_id = provider_instance_id
        self.model_id = model_id
        self.timeout_seconds = timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds

    def is_acp_cli_available(self) -> bool:
        """Check if T3 ACP Node entrypoint is present in the environment."""
        return bool(os.environ.get("T3_ACP_MCP_NODE"))

    def call_acp_mcp(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool via T3 ACP MCP Node CLI fallback."""
        node_bin = os.environ.get("T3_ACP_MCP_NODE")
        if not node_bin:
            raise T3DelegationError("T3_ACP_MCP_NODE environment variable not set")

        entrypoint = os.environ.get("T3_ACP_MCP_ENTRYPOINT")
        cmd = [node_bin]
        if entrypoint:
            cmd.append(entrypoint)
        cmd.extend(["acp-mcp-call", tool_name, json.dumps(arguments)])

        env = os.environ.copy()
        env["ELECTRON_RUN_AS_NODE"] = "1"

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=self.timeout_seconds,
                check=True,
            )
            return json.loads(proc.stdout)
        except Exception as exc:
            raise T3DelegationError(f"ACP MCP call '{tool_name}' failed: {exc}") from exc

    def delegate_step(
        self,
        step_name: str,
        payload: Dict[str, Any],
        client_request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Delegate a step to a child subagent and wait for structured response."""
        req_id = client_request_id or f"ommatidia_step_{int(time.time() * 1000)}"

        target: Dict[str, Any] = {}
        if self.provider_instance_id:
            target["providerInstanceId"] = self.provider_instance_id
        if self.model_id:
            target["model"] = self.model_id

        task_prompt = (
            f"Step: {step_name}\n"
            f"Instruction: Execute the following task step and return your response strictly as a JSON object matching the requested schema.\n"
            f"Payload:\n{json.dumps(payload, indent=2)}\n"
        )

        args = {
            "task": task_prompt,
            "target": target,
            "mode": "async",
            "clientRequestId": req_id,
        }

        if self.is_acp_cli_available():
            resp = self.call_acp_mcp("delegate_task", args)
            task_id = resp.get("taskId")
            if not task_id:
                raise T3DelegationError(f"No taskId returned in delegation response: {resp}")

            # Poll for completion
            deadline = time.time() + self.timeout_seconds
            while time.time() < deadline:
                status_resp = self.call_acp_mcp("task_status", {"taskId": task_id})
                status = status_resp.get("status")
                if status == "completed":
                    result_text = status_resp.get("result", "")
                    return ingest_json_response(result_text)
                elif status in ("failed", "cancelled"):
                    raise T3DelegationError(f"Delegated task {task_id} {status}: {status_resp.get('error')}")
                time.sleep(self.poll_interval_seconds)

            raise TimeoutError(f"Delegated task {task_id} timed out after {self.timeout_seconds}s")
        else:
            raise T3DelegationError(
                "Neither T3 in-process delegate tool nor T3_ACP_MCP_NODE CLI available."
            )


def create_t3_executor(
    adapter: Optional[T3DelegationAdapter] = None,
    fallback_executor: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None,
) -> Callable[[str, Dict[str, Any]], Dict[str, Any]]:
    """Create an executor function suitable for condition runners."""
    active_adapter = adapter or T3DelegationAdapter()

    def executor(step_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return active_adapter.delegate_step(step_name, payload)
        except Exception as exc:
            if fallback_executor is not None:
                return fallback_executor(step_name, payload)
            raise

    return executor
