# Alternative: repair the execution boundary, then run a small development pilot

Estimate only; no pilot or paid call is executed by this PR. These are engineering estimates, not measured timings, quotes or authorisation to spend.

## Required work

1. Reconcile the active graph, response schemas, stopping/synthesis rules, per-task provenance and paired analysis endpoints; preserve the H4 significance block until its binding is resolved. Audit the canonical runtime rather than rely on the superseded runtime-design.md.
2. Verify source isolation, bounded dispatch, cancellation, retries and host-attested resource usage. Provide an enforceable per-call JPY ceiling and trustworthy settlement within the existing JPY500 campaign envelope. A pricing calibration or unknown usage cannot clear this gate.
3. Keep the old evaluation package historical. Construct a separately versioned blind replacement without reading old gold; independently verify public/evaluator separation and freeze the reviewed implementation, prompts, schemas and data. A hash-only refresh cannot restore blinding or validate an implementation.
4. Before any paid run, obtain a clean committed current tree, release verification and independent acceptance of the controller and package. Confirm exact historical model availability; separately approve a prospective substitution if unavailable.
5. Use two approved development cases across A-E as the first ten slots of the planned 120 development trials, not an additional campaign. Do not inspect held-out outcomes or treat ten trials as confirmatory evidence. If a separate pilot or new cases are wanted, revise its scope and budget before running it.

## Scale and time

- Two development cases x five configurations = ten trials, at most 80 model calls and 120 tool calls under the existing eight/twelve per-trial ceilings. All retries and synthesis count within those maxima.
- At 180 seconds per trial, the sum of ten trial wall-clock ceilings is 30 minutes. Queueing, launch latency, audits and human review are additional; this is not a completion-time promise.
- Indicative engineering work: contract/endpoint reconciliation 0.5-1 day; controller/isolation/accounting repairs and tests 1-3 days; package preparation and independent verification 1-2 days; final freeze and pilot inspection 0.5-1 day. Serial envelope: roughly 3-7 working days, assuming the required host/provider controls actually exist. If they do not, no finite completion estimate is justified until that dependency changes.
- No defensible JPY estimate is available from unknown host settlement. Require a measured/enforced per-call reservation first; all pilot expenditure must share the JPY500 study ceiling, leaving room for later development and evaluation. This PR neither increases that cap nor launches a calibration call.

## Comparison with publishing the plan first

The design/protocol route needs no model execution and makes the outstanding requirements public, with no efficacy claim. The pilot-first route could expose integration defects and establish resource measurements on development tasks, but it adds blocked infrastructure work and cannot by itself establish comparative effectiveness. The recommended minimal submission is the plan-first candidate; the author decides publication and any later experimental authorisation.
