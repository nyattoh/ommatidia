# Pre-run amendment: campaign spending ceiling

Status: adopted before any study trial. No study-condition model call has been made.

## Change

The complete 240-trial campaign has an aggregate spending ceiling of JPY 500. The existing limits of 240 trials and 1,920 model calls remain in force. The optional replication plan remains outside this authorisation.

The ceiling applies to every model call charged to the study, including planning, investigation, communication between study roles, retries and synthesis. Development and evaluation trials draw from the same aggregate ceiling.

## Enforcement

The runner must reserve a provider-enforced maximum cost before dispatch. The sum of settled usage and outstanding reservations must not exceed JPY 500. The runner must use host-verified cost data to settle each reservation. It must stop before dispatch when the provider cannot enforce a maximum, when the host cannot verify usage, or when cost data is missing. Missing cost is unknown and cannot be treated as zero.

If a response omits usage after dispatch, preserve the reservation as spent for the ceiling and stop the campaign for audit. Do not retry an ambiguous dispatch.

## Unchanged study design

This amendment does not change the cases, conditions, prompts, outcomes, scoring rubrics, primary analyses or trial denominator in `PROTOCOL.md` and `EVALUATION_SPEC.md`. It adds an operational ceiling only.

## Release consequence

The current T3 task dispatcher exposes no provider-enforced cost reservation or host-verified cost field in the inspected task status. It cannot satisfy this amendment. Study execution remains blocked until a metered dispatcher is available and independently verified.
