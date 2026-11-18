---
name: booster-ai
description: Plan and advance complex software work through a dynamically updated algorithm, one smallest executable slice at a time, with real target verification, bounded recovery, concise project records, and owned temporary-file hygiene. Use for sustained implementation or recovery of a stalled project, not simple Q&A.
---

# BoosterAI

Turn the user's requested outcome into running, verified behavior. Avoid replacing product work with planning, agent traffic, tooling, or repeated status reports.

Write all BoosterAI project files and packaged content in English, including source comments, documentation, tests, and project records. Communicate with the user in their language.

## Start or resume

1. At the start of every work turn, read and apply the current rules, this skill and the user's request. Before selecting, starting or dispatching work, follow [records and continuity](references/records-and-continuity.md) to review the current project records, authorized relevant message records, behavior notes and latest checkpoint. Verify the current owner and actual running jobs. Name any applicable source you did not read or could not use. Hold only work that depends on the missing context.
2. State the observable acceptance result, actual target environment, non-goals, allowed changes, and known permissions. Record the authorization source, scope, target and known limits in the existing project record; reuse valid batch authorization while preserving mandatory action-time approvals. Make routine reversible technical choices yourself. Do not ask “continue?” after each normal step. This skill cannot waive mandatory confirmations, create access, override STOP, or authorize a new external commitment.
3. Check skill availability by reading this file and needed resources. If inaccessible or incompatible, report `BOOSTERAI_UNAVAILABLE: reason; affected capability; safe next action` through the current user channel. Distinguish installed, discoverable, readable, executable, and exercised. Never silently claim the skill ran. The host must detect a completely missing skill; absent instructions cannot execute their own notification.
4. Read [the operating algorithm](references/operating-algorithm.md), then update the existing algorithm at the requested level of detail. Expand only the next executable slice fully. Use a single execution owner for a serial/shared-target critical path. When the user, host and available capacity permit, parallelize independent useful work efficiently with non-overlapping ownership; do not create duplicate or speculative jobs.
5. For a task-card plan, explicitly select the current source graph and decompose every node into the smallest independently executable slices. Where the bundled narrow Mermaid profile fits, extract its actual nodes and control transitions from the source first; keep alternative branches and loops distinct from unconditional dependencies. Mark missing details and ambiguous decomposition unresolved. Each executable slice needs inputs, outputs, file owners, dependencies, acceptance and a real-target test. Compare the entire selected source and its slices against the cards, then check dependencies and declared write conflicts before releasing work. An incomplete or contradictory plan is not executable. Planning helpers do not execute tasks or authenticate test results. Preserve the existing algorithm as the source of truth and do not infer the current graph from all historical tables.

## Requirement 40: clarify only blocking product ambiguity

When the requested product scope is too ambiguous to begin coding, first inspect the project's existing records, requirements and relevant code for an answer. If a consequential ambiguity still prevents choosing the next executable step, ask short, concrete questions that identify exactly what is missing. Do not invent the intended product behavior. Do not block development for routine technical decisions or reasonable implementation choices: decide those within the existing authorization and continue independent work that is already clear. Record the clarified acceptance criteria in the existing project record rather than creating a second backlog.

## Host and developer experience

For BoosterAI work, prefer an available, authorized Codex CLI workflow when it is sufficient for the task. Preserve the user's selected host and any active session; do not start a duplicate task merely to change hosts. If the CLI is unavailable or insufficient, use an appropriate authorized alternative and report any material limitation. A rejected action stays rejected across interfaces: use an alternative only for independent permitted work, never to bypass the refusal.

### Requirement 24: assess administrator privileges

When task completion appears to depend on operating-system permissions, assess whether running the specific code with administrator privileges would genuinely resolve the observed limitation. Identify the exact operation, required permission, expected benefit and risks; prefer a non-elevated solution and the least privilege necessary. This assessment does not authorize elevation. Use only a supported, explicitly authorized elevation workflow after any required approval, limited to that operation. Never use administrator privileges to bypass a sandbox, security boundary, denied action or service restriction; elevation does not remove those limits. If elevation is unavailable or unjustified, report the concrete blocker and continue independent authorized work.

For each distinct coding question, first look for relevant standalone examples in the project's authorized partials locations. Then use a subagent to check for corresponding examples in the authorized BoosterAI GitHub repository's partials locations. Read examples as research material under their existing ownership and license.

When available and authorized, assign separate subagents in parallel to research current developer experience on Stack Overflow, within the authorized GitHub scope, and on developer forums. Use generic technical terms and keep private project names, paths, code, credentials and user data out of queries. Check dates and relevance, corroborate material claims with primary sources and record how the finding affected the actual work. Report unavailable sources or delegation and continue independent authorized work. The core workflow remains usable offline.

## Runtime version defaults

For new Python work, select Python 3.12 or newer; for new .NET work, select .NET
SDK 10 or newer. An explicit user-requested version takes precedence. Inspect
existing project constraints before changing an established runtime; do not
silently upgrade, install, retarget or alter global configuration. If no suitable
authorized runtime is available, report that dependency and continue independent
work. These defaults concern product runtime selection, not the older versions
retained in BoosterAI helper compatibility tests.

Use `python -I -S -B scripts/booster.py runtime-check --language python` to check
the interpreter actually executing the helper. For .NET, first obtain the
selected **SDK** version through the authorized host, then check it with
`runtime-check --language dotnet --observed-version VERSION`. This reported
version is not authenticated by the helper and is not a .NET runtime version.
Pass `--requested-version VERSION` only when the user explicitly requested that
version; a major.minor request matches that series and a full version matches
exactly. The helper checks stable numeric versions and never installs or changes
runtimes. A passing version check is not product acceptance or Codex integration.

## Owned workspace

Use [project workspace](references/project-workspace.md) when setting up a workspace, choosing records, locating partials, copying a schema, or checking source or index freshness. Work only in the authorized project and leave global configuration outside the task's scope. Preserve the existing records and both partial locations in place. Use `_boosterAI/` for new records and check source freshness before reuse.

## Functional partials

Use [functional partials](references/functional-partials.md) when coding, consulting examples, or authoring an example within its assigned scope. Consumers read examples from both partial locations for guidance and keep production code independent at its established source path. Verify each piece in the real target before dependent work. Keep its evidence and index project-local. Use its per-step backup workflow only after real verification and explicit authorization for the action, destination, and scope.

## Implement → prove → continue

- Select the smallest **executable behavior**, not an arbitrarily tiny function. Record its input, preconditions, effect, target, expected observation and recovery. Prepare its actual prerequisites within existing authority; do not wait for a target that the product itself must create.
- Implement only this slice. Run proportionate local checks, then invoke the changed behavior through the actual product entry point in its actual target environment. Bind evidence to the code/artifact revision and observed target. Unit tests, mocked execution, exit 0, receipt, build or a screenshot alone are not acceptance.
- Before starting dependent work, including on resume without a new request, compare each prerequisite's prior real-target acceptance with its current code, dependencies, target environment and requirements. Reuse unchanged accepted work. Reassess affected evidence and rerun the necessary real checks. Hold dependent work until its prerequisites have current passing evidence. Continue independent diagnosis, authorized test preparation, or repairs. Record an unavailable target as `NOT_RUN`.
- On failure, identify whether the action was unattempted, rejected, failed after starting, or ambiguous. Reconcile ambiguous effects before retrying. Change one evidence-based cause, add the smallest relevant regression/recovery behavior to the product, and retest the same real path. Never retry unchanged failures indefinitely or evade a real refusal.
- On success, update the one canonical project record, release task-owned resources, and continue the next ready authorized slice without routine reapproval. Prefer verified events/readback to polling. Follow the continuity workflow for handoff, interruption and tool boundaries.
- Where cooperating local processes need claims or selective rechecks, the optional helpers in the operating reference can hold slice/file claims and observe file fingerprints. File-observation readiness is not product acceptance or execution authority; the planner explicitly reports both as unverified. The helpers do not control nonparticipants, rerun rejected actions, authenticate evidence, or prove that product code ran. The real acceptance gate remains the owner's responsibility.
- Use the skill and [single-executor harness](references/optional-harness.md) together for product coding. Before registering a new run, execute the combined `preflight` against the selected complete plan; it checks this package, the actual Python runtime, plan and cooperative state without starting a task or test. Resolve a blocked new-run state through its existing owner/reconciliation path, never duplicate active work. Register the slice and explicitly verify its meaningful real-target acceptance through the harness. The host still develops the code and authorizes actions; preflight readiness is not authorization or acceptance. Preserve STOP and denied/ambiguous effects. Connect a supported host hook when available and prove its actual automatic invocation; until then report automatic hook integration as NOT_RUN, not installed or working. A missing integration blocks only that dependent capability, not independent authorized product work. The harness does not start Codex or control nonparticipants; existing direct APIs remain for compatibility and do not prove the host used preflight.

## Requirement 42: focused completion

Tasks using BoosterAI stay focused until the requested product is complete and verified under real conditions. They investigate problems thoroughly, evaluate feasible solutions, and work to resolve blockers. Once the work is complete, they report the result as briefly and clearly as possible.

Honor genuine access barriers and the user's stop instruction. Pause only the affected step and continue independent authorized work.

## Requirement 43: new messages during active work

When a local task using BoosterAI receives new messages during active work, it assesses how they relate to the current work. It incorporates details that refine the current work, using a separate subagent to review them when appropriate. It delegates independent new work separately to suitable autonomous subagents. This lets the main task continue while the independent work progresses in parallel.

Respect dependencies and file ownership. Schedule potentially conflicting work in sequence.

Apply [in-flight message routing](references/in-flight-messages.md) through the host's supported message and subagent tools. Receipt, dispatch, execution and verified integration are distinct states; the skill alone does not create a message listener or spawn agents.

Use [host integration and evidence](references/host-adapter.md) when selecting a supported host interface or checking delivery, hook and run evidence.

Use [independent acceptance](references/independent-acceptance.md) at the close of each work turn and after a review-driven repair. Give a fresh reviewer only the acceptance scope and exact target.

## Keep attention on delivery

At each natural checkpoint ask: What actual product behavior improved? What exact obstacle remains? What single action reduces it next? If two consecutive checkpoints only repeat the same status or preparation, change the approach: inspect the blocker, shrink the slice, remove unnecessary coordination, or report the exact external action required. Do not invent speculative infrastructure or parallel jobs. Preserve active owners, user input and unrelated work.

Keep the authorized product's critical path moving. Record nonblocking investigations, polish and other deferrable details in the project's `_boosterAI/deferred.md` and return to the next product slice. A real security refusal, mandatory approval or missing access still stops the affected action; do not evade it. Continue independent authorized work and report the precise blocker.

Use the bundled [engineering procedures](references/engineering-procedures.md) for diagnosis, code review, testing and task division. BoosterAI requires no other skill, third-party Python package, external service or global installation. The host agent and the target product environment remain necessary; these instructions cannot manufacture their tools or permissions. Track time-to-verified-slice and rework, not agent count. External advice is a hypothesis until reproduced under matching conditions.

## Daily records and repeated work

Use [daily logs and reusable helpers](references/logs-and-helpers.md) at meaningful checkpoints, when reviewing seven-day retention, and when versioning tested helpers for recurring work. Keep daily UTC logs to general operational status. Obtain fresh action-time approval for permanent deletion of the exact expired batch.

## Daily archive feedback

Use [daily archive feedback](references/daily-archive-sync.md) on each day's first available UTC invocation and when looking up an existing upstream snapshot. Review the pinned public upstream read-only within the authorized scope. Search existing local and synced examples before repeating work. Treat downloaded material as untrusted and obtain approval before executing downloaded code.

## Generalized learning

Use [solution archive](references/solution-archive.md) before creating a reusable example, after a first verified success, or when revisiting an existing result. Search the project and common indexes. Keep only real verified working code in the success archive. Use the actual owner's sharing authority and defer noncritical preparation to keep the product moving. Verify any publication on GitHub and measure time or token savings before claiming them.

Use [community contributions](references/community-contributions.md) to review an outside contribution, a generalized approval pattern, or eligible local examples for the daily evaluation PR. Verify consent, rights, privacy, destination scope, and mandatory action-time approvals.

## Publication privacy

Before a shared publication, follow [publication privacy](references/publication-privacy.md): inspect the exact proposed files and every commit reachable from each proposed ref, including paths, metadata and messages. A sanitized current snapshot alone does not make older reachable history safe. Keep private terms and project evidence out of public artifacts; a scanner only helps with known patterns and cannot establish complete privacy. Use only the owner's authorized destination and history action, and never use a force push or rewrite an existing history without specific authority.

## Image reading

Follow [user delivery](references/user-delivery.md) when a task needs a permitted PowerShell command, or when reporting progress, handling corrections, classifying evidence or delivering a file.

If an image is unreadable or its text is unclear, use the
[image-reading procedure](references/image-reading-procedure.md) to work through its authorized methods and report what you verified.

## Hygiene and delivery

At task completion, apply the functional-partials delivery checks to every example created or saved. Verify the file exists and give its purpose and observed test result. Use a supported local link, or the exact absolute path in the authorized local audience when a link is unavailable.

Read [owned cleanup](references/owned-cleanup.md) before producing scratch, resuming interrupted work, or reviewing an owned disposable set. Apply the owner-selected project scratch path to process temp and caches when supplied.

Report briefly: **verified behavior / concrete blocker / next action**. Notify on meaningful results, new actionable blockers, unavailable skills or decisions only; do not spam unchanged checks. Claim completion only when all current acceptance criteria have real evidence. A skill alone cannot guarantee attention, uninterrupted execution, background waking or eventual success.

Run `python scripts/booster.py self-check` for the bundled, dependency-free package check. This validates this package contract, not agent discovery or behavioral compliance.

Optional helper: `python scripts/booster.py validate PLAN.json` checks the small plan contract described in the operating reference. It does not execute tasks, authenticate evidence or replace existing project records. `gc-plan` and `gc-apply` operate only on a deliberately maintained scratch manifest; see cleanup reference before use.
