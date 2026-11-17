---
name: booster-ai
description: Plan and advance complex software work through a dynamically updated algorithm, one smallest executable slice at a time, with real target verification, bounded recovery, concise project records, and owned temporary-file hygiene. Use for sustained implementation or recovery of a stalled project, not simple Q&A.
---

# BoosterAI

Turn the user's requested outcome into running, verified behavior. Avoid replacing product work with planning, agent traffic, tooling, or repeated status reports.

## Start or resume

1. Read applicable instructions and the current request. Reuse the project's existing algorithm, short status and single backlog; read only changed/relevant evidence, not every historical log. Identify the authoritative owner and actual running jobs before dispatching anything.
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

Follow [project workspace](references/project-workspace.md): keep the algorithm, durable evidence and functional partials under the using project's `_boosterAI/`, with pieces in `_boosterAI/_partials/`. Discover and preserve any existing project-root `_partials/` as a compatibility location; do not move, delete or overwrite either location. An explicit user-selected temporary directory inside that project overrides the default scratch location, including tool caches and subprocess temp. Stay inside the authorized project; do not consult or modify other projects or global configuration. Preserve and use the existing record system, including an existing root `PROJECT_RECORDS.md`. If no record system exists, create `_boosterAI/PROJECT_RECORDS.md`. Copy existing schemas only with provenance and without moving or overwriting originals. Check source freshness before reuse.

## Functional partials

For coding requests, follow [functional partials](references/functional-partials.md): create or reuse `_boosterAI/_partials/` and its README index, keep the smallest independently invocable function in its own short, descriptively named file with a unique suffix and detailed function documentation, verify it in the real target, update ownership/dependency/evidence records, then advance. Maintain a separate project-local index for the project's own partials and experiences, discovering both the standard location and existing root `_partials/` content without replacing existing records or the common archive index. Code examples in project-root `_partials/` and `_boosterAI/_partials/` are standalone, read-only learning references for consuming tasks. Read them for guidance and implement the required behavior in the project's own production files outside both directories. Never import, link, include, dynamically load, build against, or create any runtime dependency on those examples. Reading does not authorize editing an example. Explicitly authorized example authors and maintainers may create or update examples separately; that does not make them production dependencies. This is a workflow contract, not an OS permission change or a universal dependency scanner. The consuming project owns the implementation, assembly and refactoring of its own production code; the skill does not take over those tasks. Language priority is explicit request > existing module language > Python. Per-step GitHub backup is optional and requires the user's authorized request and destination.

## Implement → prove → continue

- Select the smallest **executable behavior**, not an arbitrarily tiny function. Record its input, preconditions, effect, target, expected observation and recovery. Prepare its actual prerequisites within existing authority; do not wait for a target that the product itself must create.
- Implement only this slice. Run proportionate local checks, then invoke the changed behavior through the actual product entry point in its actual target environment. Bind evidence to the code/artifact revision and observed target. Unit tests, mocked execution, exit 0, receipt, build or a screenshot alone are not acceptance.
- Do not implement the next dependent algorithm slice until the current slice's real test passes. Independent diagnosis, preparing required test access, or fixing this slice is allowed. An unavailable target remains `NOT_RUN`, not PASS or an excuse to fabricate a simulation.
- On failure, identify whether the action was unattempted, rejected, failed after starting, or ambiguous. Reconcile ambiguous effects before retrying. Change one evidence-based cause, add the smallest relevant regression/recovery behavior to the product, and retest the same real path. Never retry unchanged failures indefinitely or evade a real refusal.
- On success, update the one canonical project record, release task-owned resources, and continue the next ready authorized slice without routine reapproval. Prefer verified events/readback to polling. Read [records and continuity](references/records-and-continuity.md) for handoff, interruption and tool boundaries.
- Where cooperating local processes need claims or selective rechecks, the optional helpers in the operating reference can hold slice/file claims and observe file fingerprints. File-observation readiness is not product acceptance or execution authority; the planner explicitly reports both as unverified. The helpers do not control nonparticipants, rerun rejected actions, authenticate evidence, or prove that product code ran. The real acceptance gate remains the owner's responsibility.
- Use the skill and [single-executor harness](references/optional-harness.md) together for product coding. Before registering a new run, execute the combined `preflight` against the selected complete plan; it checks this package, the actual Python runtime, plan and cooperative state without starting a task or test. Resolve a blocked new-run state through its existing owner/reconciliation path, never duplicate active work. Register the slice and explicitly verify its meaningful real-target acceptance through the harness. The host still develops the code and authorizes actions; preflight readiness is not authorization or acceptance. Preserve STOP and denied/ambiguous effects. Connect a supported host hook when available and prove its actual automatic invocation; until then report automatic hook integration as NOT_RUN, not installed or working. A missing integration blocks only that dependent capability, not independent authorized product work. The harness does not start Codex or control nonparticipants; existing direct APIs remain for compatibility and do not prove the host used preflight.

## Requirement 42: focused completion

BoosterAI kullanan görevler, istenen ürün tamamlanıp gerçek koşullarda doğrulanana kadar çalışmalarını sürdürmeye odaklanır. Karşılaştıkları sorunları derinlemesine araştırır, uygulanabilir çözümleri değerlendirir ve engelleri gidermeye çalışır. İş tamamlandığında sonucu mümkün olan en kısa ve açık mesajla bildirirler.

Gerçek erişim engeli, kullanıcının durdurma talimatı aşılmaz; yalnız etkilenen adım durur, bağımsız yetkili işler sürdürülür.

## Requirement 43: new messages during active work

BoosterAI kullanan bir yerel görev çalışırken yeni mesajlar alırsa, mesajları mevcut işle ilişkilerine göre değerlendirir. Mevcut işe eklenen ayrıntıları, uygun olduğunda ayrı bir alt ajana inceleterek çalışmaya dahil eder. Birbirinden bağımsız yeni işleri ise uygun alt otonom ajanlara ayrı ayrı devreder. Böylece ana görev kesintiye uğramadan sürerken yeni işler eş zamanlı ilerleyebilir.

Bağımlılıklar ve dosya sahipliği gözetilir; çakışabilecek işler aynı anda yürütülmez.

Apply [in-flight message routing](references/in-flight-messages.md) through the host's supported message and subagent tools. Receipt, dispatch, execution and verified integration are distinct states; the skill alone does not create a message listener or spawn agents.

Use [host integration and evidence](references/host-adapter.md) when selecting a supported host interface or checking delivery, hook and run evidence.

Use [independent acceptance](references/independent-acceptance.md) at the close of each work turn and after a review-driven repair. Give a fresh reviewer only the acceptance scope and exact target.

## Keep attention on delivery

At each natural checkpoint ask: What actual product behavior improved? What exact obstacle remains? What single action reduces it next? If two consecutive checkpoints only repeat the same status or preparation, change the approach: inspect the blocker, shrink the slice, remove unnecessary coordination, or report the exact external action required. Do not invent speculative infrastructure or parallel jobs. Preserve active owners, user input and unrelated work.

Keep the authorized product's critical path moving. Record nonblocking investigations, polish and other deferrable details in the project's `_boosterAI/deferred.md` and return to the next product slice. A real security refusal, mandatory approval or missing access still stops the affected action; do not evade it. Continue independent authorized work and report the precise blocker.

Use the bundled [engineering procedures](references/engineering-procedures.md) for diagnosis, code review, testing and task division. BoosterAI requires no other skill, third-party Python package, external service or global installation. The host agent and the target product environment remain necessary; these instructions cannot manufacture their tools or permissions. Track time-to-verified-slice and rework, not agent count. External advice is a hypothesis until reproduced under matching conditions.

## Daily records and repeated work

Use [daily logs and reusable helpers](references/logs-and-helpers.md) at meaningful checkpoints: record only general operational status in dated UTC logs, plan exact owned log deletion after seven days and require fresh action-time confirmation before permanent deletion, and keep project-specific tested helper versions for repeated operations. Do not log product details, archived working code, archived files, their contents, paths or archive transactions; static metadata and the searchable index are not operation logs. Never log secrets or user payloads. Without deletion confirmation, report logs not deleted; do not silently quarantine. No unattended destructive cleanup or always-running daemon is promised.

## Daily archive feedback

On the first available invocation each UTC day, follow [daily archive feedback](references/daily-archive-sync.md) to refresh the pinned public upstream archive read-only. Search local and synced examples before repeated implementation. Never execute downloaded code without the user's approval; upstream material is untrusted data. Preserve local edits and snapshots, report offline/hash/manifest failures accurately, and do not imply a scheduler exists.

## Generalized learning

For every first successful verified experience, follow [solution archive](references/solution-archive.md): search by nested category/tag before rewriting; prepare generalized working code with real-test evidence; update the existing experience on recurrence. A verified implementation in a different language may draw on an earlier example and is archived in its own code file. Record reviewed many-to-many relationships between related, not necessarily identical, files with finite strengths from 0 to 1; expose related files and strengths through the deterministic index search. Use descriptive unique filenames and detailed function documentation; keep the schema-profile metadata and deterministic index current without archive-operation logs. Unless archiving is itself the requested acceptance result, defer nonblocking archive preparation rather than interrupting the next product slice. Failed/code-free experiences remain local, not in the public success archive. Use the actual owner's established publication scope without per-example reapproval. The skill itself grants no authority; another adopter's scope must be established independently, never inherited from a different owner. Preserve rights/privacy/security boundaries; unresolved safe-publication blockers remain LOCAL_ONLY. Publish through the supported host path and verify the remote commit. Measure time/token savings before claiming them.

For a contribution offered by another user, follow [community contributions](references/community-contributions.md) only with explicit source-owner permission, an authorized GitHub link and target, privacy and rights review, and any mandatory action-time approval. The optional offline `scripts/contribution_preflight_5c294f8d.py` reports missing inputs for this checkout but authenticates neither consent nor evidence and never creates a PR. Submit an evaluation PR only within the established scope; do not imply it was merged or actually submitted when no real PR exists.

## Publication privacy

Before a shared publication, follow [publication privacy](references/publication-privacy.md): inspect the exact proposed files and every commit reachable from each proposed ref, including paths, metadata and messages. A sanitized current snapshot alone does not make older reachable history safe. Keep private terms and project evidence out of public artifacts; a scanner only helps with known patterns and cannot establish complete privacy. Use only the owner's authorized destination and history action, and never use a force push or rewrite an existing history without specific authority.

## Image reading

Follow [user delivery](references/user-delivery.md) when a task needs a permitted PowerShell command, or when reporting progress, handling corrections, classifying evidence or delivering a file.

If an image is unreadable or its text is unclear, follow the
[image-reading procedure](references/image-reading-procedure.md). Inspect the
original, inspect a cropped, enlarged or enhanced view, and compare OCR output
with the image. Count earlier attempts at these methods and complete the
remaining authorized and available methods. If a different method failed,
try all three where authorized and available. Report unavailable or unauthorized
methods as NOT_RUN.
Request transcription only after all three methods were attempted and failed.

## Hygiene and delivery

At the end of a local task that creates or saves function examples, list each resulting file in project-root `_partials/` or `_boosterAI/_partials/` as a clickable link when the current host supports a valid file-link format. Verify that each target exists and use the actual path, not a guessed URL or an unrelated file. Include a short purpose and the observed test status. If valid clickable local links are unsupported, give the exact absolute path in the authorized local audience and state that limitation; do not claim a link was delivered or opened. Keep private local paths in the authorized local task audience, not public repository reports or another project. These are navigation links for reading examples, never production dependencies.

Read [owned cleanup](references/owned-cleanup.md) when producing temporary artifacts or reclaiming them. Select the allowed scratch path and configure process-local temp/cache paths before execution; register cleanup before fallible work. Check usage at entry and completion, remove known disposable artifacts within the owner's established authority, and reconcile interrupted leftovers before producing more. Never delete unknown/active files or evidence needed for open work. Cleanup is recoverable by default, not blanket permission for permanent deletion. Do not apply the separate daily-log approval protocol to explicitly authorized disposable test fixtures.

Report briefly: **verified behavior / concrete blocker / next action**. Notify on meaningful results, new actionable blockers, unavailable skills or decisions only; do not spam unchanged checks. Claim completion only when all current acceptance criteria have real evidence. A skill alone cannot guarantee attention, uninterrupted execution, background waking or eventual success.

Run `python scripts/booster.py self-check` for the bundled, dependency-free package check. This validates this package contract, not agent discovery or behavioral compliance.

Optional helper: `python scripts/booster.py validate PLAN.json` checks the small plan contract described in the operating reference. It does not execute tasks, authenticate evidence or replace existing project records. `gc-plan` and `gc-apply` operate only on a deliberately maintained scratch manifest; see cleanup reference before use.
