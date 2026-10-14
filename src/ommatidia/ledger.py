"""Run ledger for stage-aware execution tracking, atomic resume, and unknown cost accounting."""

from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Union

from ommatidia.types import (
    ConditionType,
    LedgerEntry,
    LedgerStage,
    Usage,
)


class ConcurrencyLockError(RuntimeError):
    """Raised when an active run lock prevents duplicate execution."""

    pass


def _pid_alive(pid: int) -> bool:
    """Best-effort check that a process with this PID exists. PIDs can be reused."""
    if os.name == "nt":
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return (
                ctypes.get_last_error() == 5
            )  # ERROR_ACCESS_DENIED: the process exists
        # A handle can outlive the process (e.g. held by Popen), so check the exit code too.
        code = ctypes.c_ulong()
        kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        kernel32.CloseHandle(handle)
        return code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class RunLedger:
    """Manages an append-only, crash-consistent event ledger for experimental runs.

    Guarantees:
    - Stage tracking: planning, investigator, communication, retry, synthesis.
    - Explicit unknown cost/token handling: preserves None (unknown is not 0).
    - Concurrency lock: prevents duplicate active runs on the same output path.
    - Atomic writes: appends JSONL lines with flush.
    """

    def __init__(self, ledger_path: Union[str, Path]) -> None:
        self.ledger_path = Path(ledger_path)
        self.lock_path = self.ledger_path.with_suffix(".lock")
        self._lock_acquired = False

    def acquire_lock(self, run_id: str) -> None:
        """Acquire an atomic run lock file to prevent duplicate runs.

        A lock whose owning process no longer exists (for example after a crash) is
        stale and is replaced. A lock that cannot be parsed, or has no PID, is not
        assumed stale and blocks the run.
        """
        if self.lock_path.exists():
            try:
                lock_data = json.loads(
                    self.lock_path.read_text(encoding="utf-8").strip()
                )
            except json.JSONDecodeError:
                raise ConcurrencyLockError(
                    f"Active run lock file exists at {self.lock_path}"
                )
            pid = lock_data.get("pid")
            if not isinstance(pid, int) or _pid_alive(pid):
                raise ConcurrencyLockError(
                    f"Active run lock already held by run '{lock_data.get('runId')}' "
                    f"since {lock_data.get('timestamp')}"
                )
            self.lock_path.unlink()

        lock_data = {
            "runId": run_id,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "pid": os.getpid(),
        }
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        # Write lock atomically
        temp_lock = self.lock_path.with_suffix(".tmp")
        temp_lock.write_text(json.dumps(lock_data), encoding="utf-8")
        temp_lock.replace(self.lock_path)
        self._lock_acquired = True

    def release_lock(self) -> None:
        """Release the run lock."""
        if self._lock_acquired and self.lock_path.exists():
            try:
                self.lock_path.unlink()
            except OSError:
                pass
            self._lock_acquired = False

    def __enter__(self) -> RunLedger:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.release_lock()

    def record_stage(
        self,
        stage: LedgerStage,
        execution_id: str,
        task_id: str,
        condition: ConditionType,
        input_payload_hash: str,
        output_payload_hash: str,
        usage: Usage,
        status: str,
        model: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> LedgerEntry:
        """Record an execution step to the ledger.

        Unknown tokens or costs (None) are strictly preserved as null in JSON
        and never coerced to 0.
        """
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        entry = LedgerEntry(
            timestamp=now_iso,
            stage=stage,
            execution_id=execution_id,
            task_id=task_id,
            condition=condition,
            input_payload_hash=input_payload_hash,
            output_payload_hash=output_payload_hash,
            model=model,
            usage=usage,
            status=status,
            notes=notes,
        )

        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")
            f.flush()

        return entry

    def read_entries(self) -> List[LedgerEntry]:
        """Read all ledger entries from the ledger file."""
        if not self.ledger_path.exists():
            return []

        entries: List[LedgerEntry] = []
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                clean = line.strip()
                if not clean:
                    continue
                try:
                    data = json.loads(clean)
                    entries.append(LedgerEntry.from_dict(data))
                except Exception as exc:
                    raise ValueError(
                        f"Corrupted ledger entry at line {line_no}: {exc}"
                    ) from exc
        return entries

    def aggregate_usage_by_stage(self) -> Dict[str, Usage]:
        """Aggregate recorded usage grouped by stage."""
        breakdown: Dict[str, Usage] = {}
        for entry in self.read_entries():
            st_key = entry.stage.value
            if st_key not in breakdown:
                breakdown[st_key] = Usage()
            breakdown[st_key].add(entry.usage)
        return breakdown

    def total_usage(self) -> Usage:
        """Aggregate total usage across all stages."""
        total = Usage()
        for entry in self.read_entries():
            total.add(entry.usage)
        return total
