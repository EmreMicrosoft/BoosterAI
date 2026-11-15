# Optional single-executor harness

The Markdown skill works without this Python 3.10+ standard-library helper. A
tool-capable host owns development, authorization, STOP, and the meaning of
acceptance. The harness does not launch a Codex session, run plan prose as a
shell command, sandbox tests, or grant permissions. Project test code is trusted
and can have arbitrary side effects; inspect the exact test and authorize it in
the host before each execution. Never use this tool to repeat a denied action.

## Plan and run

Select one complete task-card JSON graph using the existing contract in the
operating reference. Store it as a project-relative `.json` file, or place
exactly one JSON code fence between `<!-- BOOSTERAI_HARNESS_SOURCE_BEGIN -->`
and `<!-- BOOSTERAI_HARNESS_SOURCE_END -->` in the existing algorithm Markdown.
The helper generates and validates all cards in that selection. It cannot find
omitted requirements or infer missing file dependencies. Declare every relevant
input and owned output in `read_files` and `file_owners`, including project code
used by the acceptance test; the explicitly named test file is included too.
Existing records are not replaced. One recognized `_boosterAI/harness-state.json`
tracks the selected source and its tasks; an unknown state or a different source
is preserved and rejected. Guard files implement cooperative claims separately.

For an authorized project with that plan and a reviewed real-target test:

```text
python -I -S -B scripts/harness_5b7e9c31.py --root . --source _boosterAI/algorithm.md start --task SLICE --test tests/test_real_acceptance.py --case Acceptance.test_real --max-attempts 3 --timeout 60 --max-elapsed 3600
python -I -S -B scripts/harness_5b7e9c31.py --root . --source _boosterAI/algorithm.md verify --task SLICE --run-id RUN_ID --test tests/test_real_acceptance.py --case Acceptance.test_real
python -I -S -B scripts/harness_5b7e9c31.py --root . --source _boosterAI/algorithm.md status
```

Use the actual `run_id` from `start`; the exact case is repeated explicitly in
`verify`. It must be `Class.test_method` in a project-relative `.py` file. Only
one selected unittest case is supported in version one; its assertions may
exercise multiple real product behaviors. The test's exit status alone is not
enough: the runner must report exactly one executed case, no failures, errors,
skips, expected failures or unexpected successes, and unchanged declared files
and bundled verifier code before and after execution. The host must determine
whether those assertions actually establish the requested product acceptance.
The runner's structured report is not an authenticated attestation and trusted
test code can falsify it. Hashes detect changes to declared bytes only; they do
not discover undeclared code, environmental changes, remote effects or dishonesty.
The recorded revision is a working-file and verifier fingerprint, not a Git
commit identifier. Unrelated card changes do not stale an unchanged card;
changed prerequisites stale their dependents. `status` checks freshness again.

The host must set process-local `TEMP`, `TMP` and `TMPDIR` to its authorized
project-contained scratch; `BOOSTERAI_SCRATCH` selects an existing safe scratch
directory when the project uses one. A previously established project-tools
scratch guard must continue to match. Each harness test gets its own operation
directory. Unknown contents, changed identities and ambiguous live effects are
preserved for inspection; the helper does not run a background cleaner.

## Interruption, limits, and STOP

`ACTIVE` records host-owned development; a verifier records `VERIFYING` before
starting its child. A failed or skipped case is `FAILED`; changed code is
`STALE`. A missing report, timeout or interrupted verifier is `AMBIGUOUS`, not
an automatic retry. After inspecting real effects, run `reconcile` once to
observe declared files, then only if the host has actually reviewed the effects
run `reconcile ... --effects-reviewed`; this is a host declaration, not proof of
external effects or permission. An additional, explicitly requested `verify`
is needed to run another test. A completed failure report can be reconciled as
`FAILED`; a late success report alone cannot establish exit status or freshness.
The helper cannot guarantee exactly-once effects or determine whether orphaned
descendants or external services are still active.

`stop --task SLICE --run-id RUN_ID` records a project-wide stopped barrier for
future harness operations. It cannot interrupt a test while that test holds the
cooperative lock, cannot control unrelated processes, and has no built-in resume
of the stopped record. The host must enforce a user's STOP immediately, including
any separately running work. File claims cover cooperating processes only and are
held during harness operations and acceptance, not while the host edits code
between commands. Nonparticipating writers can race these checks.

Attempts, a per-test timeout and a wall-clock elapsed gate are bounded at start;
the child timeout is limited by remaining wall time. A timeout can leave child
descendants or side effects, so it is ambiguous and requires review. Clock changes
and an unresponsive host mean these are not a hard system-wide execution limit.
The harness performs no model calls and cannot enforce or report model tokens or
monetary cost. It records cost as unavailable unless the host obtains trustworthy
per-run measurements separately. Compare like-for-like tasks before claiming
speed or cost improvements.
