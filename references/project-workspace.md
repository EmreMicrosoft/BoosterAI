# Project workspace and existing records

Create `<project-root>/_boosterAI/` for durable BoosterAI-owned work: the working algorithm, evidence and handoffs. Create or reuse the separate `<project-root>/_partials/` for functional pieces and their index. By default scratch, cleanup manifests, quarantine and helper locks live under `_boosterAI/`. An explicit user-selected temporary directory inside the authorized project overrides that default for temporary artifacts. Product integration remains the consuming project's responsibility; this workspace convention never authorizes moving existing product files or accessing another project.

Inspect the existing record system first. Preserve and use its established files and formats in place. If no project record system exists, create one minimal open `PROJECT_RECORDS.md` at project root with goal/acceptance, current state/next, backlog, decisions/evidence and a link to `_boosterAI/`. This root record and the root partials directory are explicit exceptions to the owned-work directory rule. Do not create parallel ledgers merely because a familiar filename is absent.

After inspection, use one:
```
python scripts/booster.py workspace-init --root PROJECT --records-existing docs/status.md
python scripts/booster.py workspace-init --root PROJECT --create-records
```
Without either record option the helper scaffolds owned work but reports records not selected. It does not pretend to detect every possible record format. Agent judgment must finish that selection.

The scaffold creates `_boosterAI/algorithm.md`, `_boosterAI/README.md` and the project-root `_partials/README.md` when absent, preserving existing files. Existing root-level `_partials/` is reused. If the earlier `_boosterAI/_partials/` exists, report and inspect it as a legacy location; leave its files and history in place, reference them from the project index when appropriate, and never silently move, overwrite or duplicate an implementation. Preserve an existing root index unchanged during initialization and add any cross-reference only through an authorized, deliberate update.

## Existing algorithms and freshness
To make an authorized working copy of a project-local schema, add `--schema path/to/existing.md` on initialization. The source is read only, copied byte-for-byte into `_boosterAI/algorithm.md`, and its relative path, SHA-256, modification time and copy time are recorded in `algorithm.provenance.json`. An existing algorithm or provenance prevents overwrite. Copying preserves provenance, not acceptance: inspect the source and current requirements before trusting any old done status.

`python scripts/booster.py schema-status --root PROJECT` compares source and working-copy hashes to the captured origin. A changed source means reconcile against current requirements and invalidate affected evidence; a changed working copy may be intentional, not an instruction to replace either file. Keep the origin metadata immutable as historical provenance. Record reconciliations and scope revisions in the algorithm and existing project records. The helper does not infer truth, freshness of an external target or file ownership from hashes.

A schema outside the authorized project must not be guessed or copied by this helper. Use the host's authorized read/copy path, retain explicit source/revision/hash provenance, and never relocate the original without authorization. On a partial failure, inspect created files; exclusive creation prevents blind replacement but is not a cross-file transaction.

## Scratch tools
Pass `--root PROJECT/_boosterAI` to cleanup helpers by default. When the owner selects `PROJECT/_temp-files`, pass that directory as the cleanup root instead; `.booster-tmp`, quarantine, lock and manifest must all stay beneath it. The collector still only handles registered files in its `.booster-tmp` child; it is not a general directory cleaner. Do not feed the project root or unrelated temporary directories to routine cleanup.

Configure process-local `TEMP`, `TMP`, `TMPDIR` and relevant cache/staging options before invoking tools that write temporary files. For `project_tools.py`, set the process-local `BOOSTERAI_SCRATCH` to the owner's stable selected scratch root on first use; individual operation temp directories may vary beneath it. Do not bind the shared project lock to a short-lived child directory. Disable unnecessary bytecode/cache writes. Use unique owned run directories and cleanup on success and failure; keep only necessary durable evidence in the established record location. Inspect leftover scratch before a new run and after completion. Quarantine is still disk usage, not cleanup completion. Scope, ownership, recoverability and real verification rules remain unchanged.
