# Host integration and evidence

Load this workflow when routing work through the current host, selecting an
adapter interface, or verifying a hook or recipient. Start with the authorized
project, the selected host, the current owner and plan, and the exact request
identity. For an executable slice, also identify the allowed effects, current
revision, permitted target and acceptance test.

## Observe the selected interface

Inspect the interfaces available to the selected session. On the observed local
Codex Desktop surface, `send_message_to_thread` sends an authorized message to
an existing task. `read_thread` exposes recent turns, incoming items, visible tool
results and a completed response. `wait_threads` provides a bounded progress
snapshot. Use exact host and thread identities. The inspected task tools expose
manual thread and turn information. Native hook trust controls and the natural
hook lifecycle stream were unavailable through these tools. Record those
unobserved native stages as NOT_RUN.

| Observation | Evidence to record |
| --- | --- |
| The send call returns the task identity | Transport returned an acknowledgement. Check receipt next. |
| The recipient turn contains the matching incoming item | The intended task received this specific instruction. |
| A new turn begins and reports its assigned scope | The task started and interpreted the request. |
| A real target action and completed result appear | Check the effect and current revision against the assigned acceptance. |
| Native events are absent or outside the current interface | Record which interface was inspected. Mark the unobserved hook or delivery stage NOT_RUN. |

For a manual handoff, read back the exact recipient item, then verify the
recorded action and its meaningful result. With Codex Desktop `read_thread`,
select the authorized thread, use a bounded `turnLimit`, and follow the returned
page cursor if the needed turn is older. `includeOutputs: true` can expose the
incoming text. Match the returned turn and item identities, and bound output to
the evidence needed. Record only the necessary identities, revision and evidence
references in the existing project records. Follow
[in-flight messages](in-flight-messages.md) for STOP, duplicate delivery,
related reviews and independent work.

If a supported send or independent slot is unavailable, checkpoint the
affected request in the existing record. Use the current user channel for the
specific blocker and continue an authorized nonconflicting slice in the current
session where possible. An uncertain send needs effect reconciliation before
another attempt. A new host or transport never renews a refusal. When an OS
permission blocks work, assess the exact operation, the least privilege needed,
the expected benefit and the risks. Obtain any mandatory action-time approval
through the supported path.

## Keep execution with its owner

The host owns user authorization, exact target selection, agent/file ownership
and permission to start a test or effect. The
[single-executor harness](optional-harness.md) owns the selected serial run,
attempt and elapsed budgets, evidence freshness, STOP and reconciliation in its
existing state record. The owner checks dependencies and live claims before
dispatch. Collaborating agents may work on independent targets under disjoint
ownership.

Use the existing preflight before a separately authorized new run. Preflight
can acquire cooperative guards. A READY result establishes structural
readiness only. Start once through the supported entry, record the returned
run ID, and verify the named acceptance test on that same eligible run. The
status operation may update stale or interrupted run records. For an inventory
that must be read-only, inspect the persisted state and label it as a stored
observation.

## Accept a native adapter only on observed effects

On a selected host exposing a supported native interface, bind the actual
source hook session, turn and applicable tool-use identity to the reviewed
finding, selected plan, task, run and source revision. Verify the exact
recipient session and turn, user opt-in, effective hook trust, run eligibility
and budget. Preserve inherited hook declarations and obtain approval as
required for the exact definition. Keep STOP, denial and ambiguous effects in
the existing owner and state path.

A read-only matcher can establish agreement between supplied metadata and a
bounded plan/run observation. A command projection produces the reviewed
arguments for the supported caller. For cooperating emitters using receipt
deduplication, assign one owner to an explicitly authorized project-local store,
preserve existing records, and reconcile an uncertain claim or send before
attempting delivery again. A committed receipt establishes its store effect.

Record effective registration/trust, natural hook start and completion,
actual delivery, one-time recipient processing, real same-run acceptance,
needed continuation and ordinary final stop as distinct observations. Use the
host's event readback only for the events and identities it actually exposes.
When the proof is incomplete, checkpoint the exact gap and label the unobserved
stage NOT_RUN. Configuration, command text, a manual handoff and a receipt each
retain their measured scope.

Send an actual failed or unverified independent result to the responsible
developer with the exact unmet criteria, reproduction steps or missing
prerequisite, and evidence at the reviewed revision. For native review, send
once and observe recipient processing while the same run is still ACTIVE,
before final verification or STOP. Keep the original finding and revision
bound to the actual source and recipient. The owner corrects the demonstrated
cause or resolves the missing prerequisite, and a fresh reviewer repeats the
real acceptance before a successful final verification. Later readback uses
the single observed delivery. Keep each result scoped to its actual entry
and effects.
