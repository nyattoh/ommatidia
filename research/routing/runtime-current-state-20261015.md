# Runtime and release-gate grounding

This note records the observed call path and the limits that any replacement runner must address. It does not approve a study run.

## Call path

1. `scripts/run_harness.py:89-92` rejects held-out actions before reading a dataset. A development run requires the T3 executor unless it is explicitly a synthetic check (`scripts/run_harness.py:98-108`). A non-synthetic development run calls `verify_environment(require_release=True)` before `run_cohort` (`scripts/run_harness.py:124-127`).
2. `ResearchHarness.evaluate_task` checks the runtime freeze and reserves a trial before execution (`src/ommatidia/harness.py:526-545`). Before each executor call, it reserves one model call and the remaining tool ceiling in `GlobalResourceRegistry` (`src/ommatidia/harness.py:548-577`, `src/ommatidia/campaign.py:103-127`).
3. The step payload states one model call, a tool ceiling, a deadline, and an output-token limit (`src/ommatidia/harness.py:555-565`). The current reservation ledger does not reserve any cost amount.
4. `T3DelegationAdapter` accepts an injected `public_boundary` callback whose four Boolean fields attest public-only access, one model invocation, step budgets and verified host usage (`src/ommatidia/t3_adapter.py:99-114`). It then sends an asynchronous `delegate_task` request using a T3 worktree (`src/ommatidia/t3_adapter.py:112-123`). This callback contract does not itself create or inspect an isolated public-only workspace.
5. On completion, the adapter copies `status.hostUsage` only when it is present (`src/ommatidia/t3_adapter.py:132-144`). The parent T3 task-status result for the two completed documentation audits exposed no `usage` or `hostUsage` field; their task costs and token counts remain unknown (`research/routing/ommatidia-haiku-publication-audits-20261015.json`).
6. The harness treats missing usage as unverified for that step, but still charges at least one model call and the reserved tool ceiling (`src/ommatidia/harness.py:579-609`, `src/ommatidia/campaign.py:133-150`). The campaign registry records `cost_yen` as optional and has no aggregate cost ceiling or cost reservation (`src/ommatidia/campaign.py:37-56`, `src/ommatidia/campaign.py:107-127`).
7. `Usage.exceeds` now fails a configured per-task cost budget closed when the cost is missing. A focused test proves unknown cost exceeds a configured ¥500 task budget (`src/ommatidia/types.py:358-372`, `tests/test_budget_cost_gate.py`). This does not provide a campaign-wide reservation or a provider-enforced maximum.
8. `verify_runtime_freeze(require_release=True)` requires `evaluationPackageStatus=rebuilt_and_approved`, a clean working tree and a `baseCommit` equal to HEAD (`src/ommatidia/integrity.py:51-59`). R4 remains `blocked_rebuild_required` and zero study trials are recorded (`research/runtime_freeze_r4.json`).

## Constraints for the design

- The study ceiling is 240 trials and 1,920 model calls. The authorised total cost ceiling is ¥500.
- No study trial or study-condition model call has run.
- The T3 task API provides asynchronous child tasks. The inspected task-status result contains no host cost, token or invocation-usage fields.
- The present T3 task request has no cost reservation field, and child worktree isolation does not by itself prove a public-only file boundary.
- Any runner must refuse dispatch before the first model call unless it can prove both a hard cost reservation and the permitted public input boundary. Post-call detection cannot guarantee the ¥500 ceiling.

## Current verification state

- The baseline full suite before the latest change reported 129 passing tests.
- `tests/test_budget_cost_gate.py` first failed on unknown cost, then passed all three cases after `Usage.exceeds` was corrected.
- The R4 freeze now fails its code-hash check because `src/ommatidia/types.py` changed. A replacement freeze must be generated after implementation is stable.
