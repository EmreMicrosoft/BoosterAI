# Validation

This record describes checks on the current package. It does not include private project details, user data or earlier release history.

## Package checks

- On Windows with Python 3.14, the complete standard-library suite passed 140 tests using `python -I -S -B -m unittest discover -s tests`. No third-party Python packages were needed.
- The bundled self-check validates the repository-local registration, required files and canonical skill link. It does not prove agent discovery, agent behavior or the authenticity of a source.
- Generalized source examples were exercised in controlled, repository-owned Python fixtures, including a real child process and a command-line search. Stored sanitized-summary digests hash the summary text and do not authenticate an observation.
- Temporary test artifacts use an owner-selected project-local directory and are cleaned or explicitly retained when ownership or approval is unresolved.

## Publication and privacy

Before publishing, review the selected current files and every commit reachable from the intended refs. Run the offline publication scan with the owner's private terms and known prior commit identifiers kept out of public files. A no-match result is limited to the supplied inputs and supported patterns; it is not a complete privacy guarantee. Verify the actual remote refs and history after publication.

The package does not grant source rights, authorize a third-party contribution, override access or safety decisions, or promise uninterrupted execution. A missing real target remains unverified.
