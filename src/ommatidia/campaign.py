"""Durable, campaign-wide trial and dispatch reservations."""

from dataclasses import dataclass, field
from fractions import Fraction
import json
import math
import os
import threading
from pathlib import Path
from typing import Optional

from ommatidia.types import Usage


SCHEMA_VERSION = 4


class ResourceLimitExceeded(RuntimeError):
    pass


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def validate_usage(usage):
    for name in ("rounds", "model_calls", "tool_calls", "elapsed_ms", "input_chars",
                 "total_tokens", "cost_yen"):
        value = getattr(usage, name)
        if value is not None and (isinstance(value, bool) or not math.isfinite(value) or value < 0):
            raise ValueError(f"Invalid usage: {name}")


def known_zero_usage():
    return Usage(total_tokens=0, cost_yen=0.0)


def is_bounded_cost(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


@dataclass
class GlobalResourceRegistry:
    max_aggregate_model_calls: int = 1920
    max_aggregate_tool_calls: int = 2880
    max_total_trials: int = 240
    max_trial_model_calls: int = 8
    max_trial_tool_calls: int = 12
    max_trial_elapsed_ms: float = 180000.0
    max_trial_input_chars: int = 48000
    max_cost_yen: float = 500.0
    total_model_calls: int = 0
    total_tool_calls: int = 0
    total_elapsed_ms: float = 0.0
    total_input_chars: int = 0
    total_trials: int = 0
    total_tokens: Optional[int] = None
    cost_yen: Optional[float] = None
    trials_by_condition: dict = field(default_factory=dict)
    storage_path: Optional[Path] = None
    trials: dict = field(default_factory=dict)
    calls: dict = field(default_factory=dict)
    manual_usage: Usage = field(default_factory=known_zero_usage)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False, compare=False)

    def __post_init__(self):
        if self.total_trials != len(self.trials):
            raise ValueError("Historical trial totals require explicit audited reservations")
        if (self.total_model_calls or self.total_tool_calls or self.total_elapsed_ms or self.total_input_chars
                or self.total_tokens is not None or self.cost_yen is not None):
            self.manual_usage = Usage(model_calls=self.total_model_calls, tool_calls=self.total_tool_calls,
                                      elapsed_ms=self.total_elapsed_ms, input_chars=self.total_input_chars,
                                      total_tokens=self.total_tokens, cost_yen=self.cost_yen)
        validate_usage(self.manual_usage)
        self.max_aggregate_model_calls = min(1920, self.max_aggregate_model_calls)
        self.max_aggregate_tool_calls = min(2880, self.max_aggregate_tool_calls)
        self.max_total_trials = min(240, self.max_total_trials)
        self.max_cost_yen = min(500.0, self.max_cost_yen)

    def _recompute(self):
        usage = Usage.from_dict(self.manual_usage.to_dict())
        for call in self.calls.values():
            usage.add(Usage.from_dict(call["usage"]))
        self.total_model_calls, self.total_tool_calls = usage.model_calls, usage.tool_calls
        self.total_elapsed_ms, self.total_input_chars = usage.elapsed_ms, usage.input_chars
        self.total_tokens, self.cost_yen = usage.total_tokens, usage.cost_yen
        self.total_trials = len(self.trials)
        self.trials_by_condition = {}
        for trial in self.trials.values():
            cond = trial["condition"]
            self.trials_by_condition[cond] = self.trials_by_condition.get(cond, 0) + 1

    def check_trial_preconditions(self):
        if self.total_trials >= min(240, self.max_total_trials):
            raise ResourceLimitExceeded("Campaign trial ceiling reached")
        if self.total_model_calls >= min(1920, self.max_aggregate_model_calls):
            raise ResourceLimitExceeded("Campaign model-call ceiling reached")

    def begin_trial(self, key, condition, identity):
        if key in self.trials:
            raise ResourceLimitExceeded("Trial already reserved; resume or audit its saved record")
        self.check_trial_preconditions()
        self.trials[key] = {"condition": condition.value, "identity": identity, "status": "running"}
        self._recompute()
        self.save_atomic()

    def trial_usage(self, key):
        result = known_zero_usage()
        for call in self.calls.values():
            if call["trialKey"] == key:
                result.add(Usage.from_dict(call["usage"]))
        return result

    def _exact_committed_cost(self, key=None):
        # Exact rational sums: float addition can round a total above a ceiling down onto it.
        manual = self.manual_usage.cost_yen if key is None else 0
        if manual is None:
            return None
        return Fraction(manual) + sum(
            (Fraction(call["reservedCostYen"] if call["settledCostYen"] is None else call["settledCostYen"])
             for call in self.calls.values() if key is None or call["trialKey"] == key), Fraction(0))

    def committed_cost_yen(self):
        exact = self._exact_committed_cost()
        return None if exact is None else float(exact)

    def _check_model_call_capacity(self, count=1):
        if count <= 0 or self.total_model_calls + count > min(1920, self.max_aggregate_model_calls):
            raise ResourceLimitExceeded("Campaign model-call ceiling would be exceeded")

    def reserve_step(self, key, step_id, tool_ceiling, input_chars, budget, reserved_cost_yen=None):
        with self._lock:
            self._reserve_step(key, step_id, tool_ceiling, input_chars, budget, reserved_cost_yen)

    def _reserve_step(self, key, step_id, tool_ceiling, input_chars, budget, reserved_cost_yen):
        if any(trial.get("auditRequired") for trial in self.trials.values()):
            raise ResourceLimitExceeded("Campaign stopped; audit required before any further call")
        if not is_bounded_cost(reserved_cost_yen):
            raise ResourceLimitExceeded("Per-call cost is unknown or unbounded; refusing dispatch")
        committed = self._exact_committed_cost()
        if committed is None:
            raise ResourceLimitExceeded("Committed campaign cost is unknown; refusing dispatch")
        if committed + Fraction(reserved_cost_yen) > Fraction(self.max_cost_yen):
            raise ResourceLimitExceeded("Campaign cost ceiling would be exceeded")
        if budget.max_cost_yen is not None:
            if not is_bounded_cost(budget.max_cost_yen):
                raise ResourceLimitExceeded("Trial cost limit is unknown or unbounded; refusing dispatch")
            if self._exact_committed_cost(key) + Fraction(reserved_cost_yen) > Fraction(budget.max_cost_yen):
                raise ResourceLimitExceeded("Trial cost ceiling would be exceeded")
        if step_id in self.calls:
            raise ResourceLimitExceeded("Duplicate dispatch reservation")
        trial = self.trial_usage(key)
        self._check_model_call_capacity()
        if trial.model_calls + 1 > min(8, self.max_trial_model_calls, budget.max_model_calls):
            raise ResourceLimitExceeded("Per-trial model-call ceiling reached")
        if trial.input_chars + input_chars > min(48000, self.max_trial_input_chars, budget.max_input_chars):
            raise ResourceLimitExceeded("Per-trial input character ceiling reached")
        if trial.elapsed_ms >= min(self.max_trial_elapsed_ms, budget.max_elapsed_ms):
            raise ResourceLimitExceeded("Per-trial elapsed time ceiling reached")
        if tool_ceiling < 0 or trial.tool_calls + tool_ceiling > min(12, self.max_trial_tool_calls, budget.max_tool_calls):
            raise ResourceLimitExceeded("Per-trial tool-call ceiling reached")
        if self.total_tool_calls + tool_ceiling > min(2880, self.max_aggregate_tool_calls):
            raise ResourceLimitExceeded("Campaign tool-call ceiling reached")
        self.calls[step_id] = {"trialKey": key, "status": "reserved",
                               "usageKnown": False, "dispatch": {},
                               "reservedCostYen": float(reserved_cost_yen), "settledCostYen": None,
                               "usage": Usage(model_calls=1, tool_calls=tool_ceiling,
                                              input_chars=input_chars).to_dict()}
        self._recompute()
        self.save_atomic()  # Write and fsync BEFORE calling the executor.

    def annotate_dispatch(self, step_id, metadata):
        self.calls[step_id]["dispatch"] = dict(metadata)
        self.save_atomic()

    def settle_step(self, step_id, usage, known, status):
        with self._lock:
            self._settle_step(step_id, usage, known, status)

    def _settle_step(self, step_id, usage, known, status):
        if self.calls[step_id]["status"] != "reserved":
            raise ResourceLimitExceeded("Call already settled; duplicate settlement rejected")
        validate_usage(usage)
        reserved = Usage.from_dict(self.calls[step_id]["usage"])
        reserved_cost = self.calls[step_id]["reservedCostYen"]
        cost_unsettled = not known or usage.cost_yen is None or usage.cost_yen > reserved_cost
        usage.model_calls = max(1, usage.model_calls)
        usage.input_chars = max(reserved.input_chars, usage.input_chars)
        if not known:
            usage.tool_calls = max(reserved.tool_calls, usage.tool_calls)
        self.calls[step_id].update(usage=usage.to_dict(), usageKnown=known, status=status,
                                   settledCostYen=reserved_cost if cost_unsettled else usage.cost_yen)
        self._recompute()
        violation = (self.total_model_calls > self.max_aggregate_model_calls or
                     self.total_tool_calls > self.max_aggregate_tool_calls or
                     usage.model_calls > 1 or usage.tool_calls > reserved.tool_calls or cost_unsettled)
        if violation:
            self.calls[step_id].update(status="failed", auditRequired=True)
            self.trials[self.calls[step_id]["trialKey"]]["auditRequired"] = True
        self.save_atomic()
        if violation:
            raise ResourceLimitExceeded("Executor exceeded its reserved envelope; campaign audit required")

    def finish_trial(self, key, status, record_hash):
        self.trials[key].update(status=status, recordHash=record_hash)
        self.save_atomic()

    def record_step(self, step_name, step_usage, trial_usage=None):
        """Compatibility for isolated accounting tests; runtime uses reservations."""
        validate_usage(step_usage)
        self.manual_usage.add(step_usage)
        self._recompute()
        self.save_atomic()
        if self.total_model_calls > self.max_aggregate_model_calls or self.total_tool_calls > self.max_aggregate_tool_calls:
            raise ResourceLimitExceeded("Aggregate ceiling exceeded")
        committed = self._exact_committed_cost()
        if committed is not None and committed > Fraction(self.max_cost_yen):
            raise ResourceLimitExceeded("Aggregate cost ceiling exceeded")
        if trial_usage and (trial_usage.model_calls > self.max_trial_model_calls or trial_usage.tool_calls > self.max_trial_tool_calls):
            raise ResourceLimitExceeded("Per-trial ceiling exceeded")

    def to_dict(self):
        return {"schemaVersion": SCHEMA_VERSION, "maxAggregateModelCalls": self.max_aggregate_model_calls,
                "maxAggregateToolCalls": self.max_aggregate_tool_calls, "maxTotalTrials": self.max_total_trials,
                "maxCostYen": self.max_cost_yen, "committedCostYen": self.committed_cost_yen(),
                "totalModelCalls": self.total_model_calls, "totalToolCalls": self.total_tool_calls,
                "totalElapsedMs": self.total_elapsed_ms, "totalInputChars": self.total_input_chars,
                "totalTrials": self.total_trials, "totalTokens": self.total_tokens, "costYen": self.cost_yen,
                "trialsByCondition": self.trials_by_condition, "trials": self.trials, "calls": self.calls,
                "manualUsage": self.manual_usage.to_dict()}

    def save_atomic(self, path=None):
        target = path or self.storage_path
        if target:
            atomic_json(target, self.to_dict())

    def load_from_path(self, path):
        path = Path(path)
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data["schemaVersion"] != SCHEMA_VERSION:
                raise ValueError(f"Registry schemaVersion {data['schemaVersion']} needs explicit audited migration "
                                 f"to {SCHEMA_VERSION}; v4 counts manual cost in committedCostYen")
            self.trials, self.calls = data["trials"], data["calls"]
            self.manual_usage = Usage.from_dict(data["manualUsage"])
            validate_usage(self.manual_usage)
            for trial in self.trials.values():
                if trial["condition"] not in "ABCDE" or not isinstance(trial["identity"], dict):
                    raise ValueError("Invalid trial reservation")
            for call in self.calls.values():
                if call["trialKey"] not in self.trials or call["status"] not in ("reserved", "completed", "failed"):
                    raise ValueError("Invalid call reservation")
                validate_usage(Usage.from_dict(call["usage"]))
                if call["usage"]["modelCalls"] < 1:
                    raise ValueError("Uncharged call")
                settled = call["settledCostYen"]
                if not is_bounded_cost(call["reservedCostYen"]) or (
                        settled is not None and not (is_bounded_cost(settled) and settled <= call["reservedCostYen"])):
                    raise ValueError("Invalid call cost reservation")
            self._recompute()
            current = self.to_dict()
            for name in ("totalModelCalls", "totalToolCalls", "totalElapsedMs", "totalInputChars", "totalTrials", "trialsByCondition", "totalTokens", "costYen", "committedCostYen"):
                if current[name] != data[name]:
                    raise ValueError(f"Registry total mismatch: {name}")
            for call in self.calls.values():
                if call["status"] == "reserved":
                    # Dispatched before a crash with no settlement: outcome and cost are unknown.
                    call["auditRequired"] = True
                    self.trials[call["trialKey"]]["auditRequired"] = True
            self.max_aggregate_model_calls = min(self.max_aggregate_model_calls, data["maxAggregateModelCalls"], 1920)
            self.max_aggregate_tool_calls = min(self.max_aggregate_tool_calls, data["maxAggregateToolCalls"], 2880)
            self.max_total_trials = min(self.max_total_trials, data["maxTotalTrials"], 240)
            self.max_cost_yen = min(self.max_cost_yen, data["maxCostYen"], 500.0)
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise ValueError(f"Corrupt or incompatible campaign registry: {path}: {exc}") from exc
