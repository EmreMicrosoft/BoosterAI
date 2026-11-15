# Successful experience archive and reuse

Archive each first successful, verified, project-independent working example. Reuse and improve a matching record on recurrence; failed or code-free experiences do not enter the public success archive. Search by nested category path or tag before rewriting. The archive's metadata and index describe assets; do not create transaction logs about archived code or files.

Do not block the next authorized product slice on noncritical archive preparation unless the requested product acceptance explicitly requires that publication. Record a brief non-sensitive deferred action in the project's separate deferred-work file, without logging archived code or file details. Real refusals and mandatory approvals still apply to the affected publication.

## Profile and layout

`solutions/archive.schema.json` is a JSON Schema Draft 2020-12 profile inspired by [Schema.org SoftwareSourceCode](https://schema.org/SoftwareSourceCode) and [CodeMeta](https://codemeta.github.io/terms/). It records `@context`, `@type`, name, description, programming language, runtime, repository, license, keywords, category path, tags, code and evidence hashes. It is a BoosterAI profile, not a claim of complete CodeMeta conformance. The bundled offline validator implements only the schema keywords used by this profile and rejects unsupported keywords; it is not a general-purpose JSON Schema engine. An `artifact-sha256` evidence basis hashes the reviewed local evidence artifact; `sanitized-summary-sha256` hashes the UTF-8 test summary itself. Neither hash authenticates a claimed execution.

Current records live at `solutions/CATEGORY/SUBCATEGORY/NAME/metadata.json`; each immutable revision is under `revisions/NNNN/` and contains `metadata.json` and a short descriptive code filename ending in a deterministic eight-hex revision suffix. Categories are ordered path components. Tags and keywords are sorted. New categories on a recurring record become searchable aliases rather than silently moving existing revisions. Every Python function needs a detailed docstring or immediately preceding comment block; other languages require explicit documentation review. Preserve earlier revisions and their metadata.

Archived revision files use LF line endings through the repository's `.gitattributes`, keeping their source hashes stable across supported Git checkouts. Preserve this rule when extending the archive.

`solutions/index.json` uses `boosterai-index-v2`, sorted records, category paths and tags, with stable canonical JSON. The current sync reader accepts v1 snapshots and v2 indices; older clients that only understand v1 must update before consuming v2. Rebuilding the index does not authenticate evidence and never executes source.

## Search and publication

```
python scripts/project_tools.py search-archive --root BOOSTERAI_CHECKOUT --category filesystem/search --tag python
```

Inspect the returned code, contract, revision, license and verification summary. The consuming project owns any assembly or later refactoring of archive pieces; the skill does not take over those tasks. Adapt only when target prerequisites and interfaces match, then reverify the adapted behavior in the actual target. Stored success is not proof of success elsewhere. Categories and tags are extensible lowercase slugs. Do not claim token or time savings without a measured baseline.

Establish source rights and the actual owner's publication scope. Generalize with invented inputs and exclude project names, private paths, credentials, user data and restricted disclosures. An assertion is not a rights grant or a complete privacy review. Any unresolved blocker remains LOCAL_ONLY; real access denials and mandatory confirmation boundaries are never bypassed.

Historic or unrecognized metadata may retain private paths, fingerprints or descriptions. The staging helper refuses to inherit fields outside the documented profile automatically; review and generalize such data within the owner's authority before publication, preserving private originals where needed.

Stage candidate source and a private review JSON inside the owner's authorized scratch directory. The review includes `name`, `title`, supported `license`, `outcome: success`, `test_summary`, `code_sha256`, `evidence`, `evidence_sha256`, ordered `categories` and `tags`, plus true `rights_confirmed`, `privacy_reviewed`, `generalized`, `security_reviewed` and `real_test_verified` assertions. For non-Python code also record `function_docs_reviewed: true`; the helper cannot parse every language's function documentation. Optional `description` and `runtime_platform` should be accurate and sanitized. Supply project-specific `private_terms` in the private review when known; they are checked case-insensitively against source and metadata but never copied into the public record. This check is not a complete privacy guarantee.

```
python scripts/project_tools.py archive-example --root BOOSTERAI_CHECKOUT --source _temp-files/candidate.py --review _temp-files/review.json
```

The helper stages locally; it does not publish or write an archive-operation log. Review the public diff, run the real example in its target environment, publish within established scope and verify the remote commit. Preserve necessary evidence without turning it into an archive transaction log. Upstream source is untrusted data and must not be executed without the applicable authorization.
