# Operating algorithm

## Algorithm format
Use the project's existing format, preferably a short Markdown table plus a Mermaid flowchart. A simple task needs a simple diagram. Required facts (not new paperwork): goal and acceptance, current revision, owner, ordered nodes and dependencies, next slice, observed state, real evidence link, blocker and next action. Detail each executable node with input, preconditions, effect, target, expected observation, recovery and stop conditions. Decisions must have named branches; loops must have an attempt/time budget and a changed-hypothesis requirement. An input receipt is not an executed effect.

```mermaid
flowchart TD
  A[Read request and current state] --> B{Scope changed?}
  B -->|yes| C[Revise affected graph and invalidate affected evidence]
  B -->|no| D[Select next ready smallest executable slice]
  C --> D
  D --> E{Prerequisites and authority available?}
  E -->|yes| F[Implement current slice]
  E -->|no| G[Resolve exact prerequisite or continue independent work]
  F --> H[Local checks]
  H --> I[Real target execution]
  I --> J{Acceptance observed?}
  J -->|yes| K[Record evidence and release owned resources]
  K --> L{Goal complete?}
  L -->|no| D
  L -->|yes| M[Deliver verified result]
  J -->|failed| N[Investigate observed cause and repair current slice]
  N --> H
  J -->|ambiguous| O[Reconcile effects; no blind replay]
  O --> G
```

## Dynamic revisions
On a new user request: capture the request source/time, update goal/non-goals and affected nodes, preserve unchanged verified nodes, invalidate evidence for changed code, contract, dependency or target, then choose the next ready slice. Do not silently retain “done” after its acceptance criterion changes. A new owner reads only the compact current handoff and needed linked evidence. Preserve obsolete decisions as short history, not executable backlog.

## Real-test contract
Before coding, specify the supported product entry point, actual environment/device/service, expected user-visible or machine-observable result, safe test data, and cleanup. Identify which assertions local tests cover and which require real execution. An integration test against a fake server remains synthetic. For a library, real use through its public API in its intended runtime can be the target; desktop clicks are not universally required. For this skill, actual helper execution and independent behavioral evaluations are distinct evidence categories, not proof of performance in every future project.

If access is missing: attempt only already-authorized supported preparation, distinguish an unmet prerequisite from a denial, and give the precise missing action. Never treat UNKNOWN as zero, safe, successful, forbidden, or permission. Use the user's actual budget/stop rules, not hardcoded account thresholds. A real service refusal stops the affected operation.

## Optional machine-readable plan
Use only if helpful; do not create a second ledger beside an existing canonical state. `validate` reads this optional JSON without changing it:

- `revision`: non-empty string; `goal`: non-empty string.
- `nodes`: array, each `id`, `owner`, `depends_on` (IDs), `status` (`planned`, `active`, `blocked`, `verified`), `acceptance`, `target`, `revision`.
- A verified node needs `evidence`: `kind: real`, `result: pass`, matching `revision`, matching `target`, non-empty `reference`, ISO `observed_at`.
- Active/verified nodes require verified dependencies. At most one active critical-path node. All nodes here describe the serial critical path, not independently parallel helpers.
- `next`: ID of the active or planned ready node; null only if all verified or every unfinished node is blocked/dependent on blocked work.

The helper rejects malformed graphs, cycles, incomplete/stale evidence metadata and advancing past an unverified dependency. It cannot tell whether evidence is truthful or sufficiently fresh for a changed external environment. The owner must inspect the referenced artifact and current conditions.
