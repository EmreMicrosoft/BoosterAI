"""Offline contribution-input preflight; never grants authority or creates a PR."""

import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys


TARGET = 'https://github.com/EmreMicrosoft/BoosterAI'
BRANCH = 'main'
REQUIRED = ('contributor', 'source_url', 'consent_reference', 'consent_scope',
            'license', 'rights_review', 'privacy_review', 'security_review',
            'test_evidence')
TEXT_FIELDS = ('consent_reference', 'consent_scope', 'license', 'rights_review',
               'privacy_review', 'security_review')


class PrivateArgumentParser(argparse.ArgumentParser):
    """Suppress supplied argument values if command-line parsing fails.

    Emit a fixed diagnostic rather than reflecting a private reference or path.
    Parsing failure never attempts to examine a contribution or create a PR.
    """

    def error(self, message):
        """Exit with a generic error while deliberately ignoring parser details.

        This prevents unrecognized argument values from leaking to stderr; the
        standard help option remains available without touching contribution data.
        """
        self.exit(2, 'invalid arguments; no contribution was evaluated\n')


def project_root(requested):
    """Return this checkout's verified root without accepting another project.

    Compare the lexical path with the script's own checkout first, then reject
    link/reparse ancestors before resolution. A mismatched root is never read.
    """
    script = Path(__file__).absolute()
    expected = script.parent.parent
    proposed = Path(requested).absolute()
    if os.path.normcase(str(proposed)) != os.path.normcase(str(expected)):
        raise ValueError('unsupported_project_root')
    for ancestor in (proposed, *proposed.parents):
        info = ancestor.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('project_root_link_forbidden')
    if not proposed.is_dir():
        raise ValueError('project_root_unavailable')
    return proposed.resolve()


def ordinary_file(root, relative):
    """Resolve a project-relative existing file without following links or hardlinks.

    Reject traversal, drives, streams and reparse points at every component. Return
    None for an absent file; reject directories and malformed paths with ValueError.
    """
    if not isinstance(relative, str) or not relative or '\x00' in relative or ':' in relative:
        raise ValueError('invalid_path')
    raw = Path(relative)
    if raw.is_absolute() or raw.drive or '..' in raw.parts or not raw.parts:
        raise ValueError('invalid_path')
    path = root
    for part in raw.parts:
        path = path / part
        try:
            info = path.lstat()
        except FileNotFoundError:
            return None
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('link_forbidden')
        if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
            raise ValueError('hardlink_forbidden')
    if not stat.S_ISREG(info.st_mode) or not path.resolve().is_relative_to(root):
        raise ValueError('invalid_path')
    return path


def specific_source_url(value):
    """Check only the syntax and repository scope of a specific GitHub link.

    Issue, pull-request, immutable commit and immutable blob links are supported.
    This does not contact GitHub or establish existence, ownership or permission.
    """
    if not isinstance(value, str):
        return False
    pattern = (r'https://github\.com/EmreMicrosoft/BoosterAI/'
               r'(?:issues/[1-9][0-9]*|pull/[1-9][0-9]*|commit/[0-9a-f]{40}'
               r'|blob/[0-9a-f]{40}/[A-Za-z0-9._/-]+)')
    if re.fullmatch(pattern, value, flags=re.IGNORECASE) is None:
        return False
    parts = value.split('/')[7:] if '/blob/' in value.lower() else []
    return not parts or all(part not in ('', '.', '..') for part in parts)


def nonempty_text(value):
    """Accept a bounded metadata reference without judging whether it is true.

    The value remains private input and is never echoed in the preflight result.
    Identity, authority, rights and the substance of a review require host checks.
    """
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 1000


def evaluate(root, review):
    """List missing or invalid inputs while withholding all private input values.

    A complete set is only ready for manual authorization and substantive review.
    The helper never authenticates identities or evidence, contacts a service,
    creates an artifact, executes source code, or opens a pull request.
    """
    root = project_root(root)
    if not isinstance(review, dict):
        raise ValueError('review_must_be_object')
    missing = [key for key in REQUIRED if key not in review or review[key] is None or review[key] == '']
    invalid = []
    access_denied = []
    if 'contributor' not in missing:
        value = review['contributor']
        if (not isinstance(value, str) or len(value) > 39
                or re.fullmatch(r'[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*', value) is None
                or value.casefold() == 'emremicrosoft'):
            invalid.append('contributor')
    if 'source_url' not in missing and not specific_source_url(review['source_url']):
        invalid.append('source_url')
    for key in TEXT_FIELDS:
        if key not in missing and not nonempty_text(review[key]):
            invalid.append(key)
    if review.get('target_repository', TARGET) != TARGET:
        invalid.append('target_repository')
    if review.get('target_branch', BRANCH) != BRANCH:
        invalid.append('target_branch')
    if 'test_evidence' not in missing:
        try:
            if ordinary_file(root, review['test_evidence']) is None:
                missing.append('test_evidence')
        except PermissionError:
            access_denied.append('test_evidence')
        except (OSError, ValueError, TypeError):
            invalid.append('test_evidence')
    status = 'NOT_READY' if missing or invalid or access_denied else 'MANUAL_AUTHORIZATION_AND_REVIEW_REQUIRED'
    return {'status': status, 'missing': missing, 'invalid': invalid, 'access_denied': access_denied,
            'target_repository': TARGET, 'target_branch': BRANCH,
            'identity_verified': False, 'consent_verified': False, 'rights_verified': False,
            'privacy_verified': False, 'security_verified': False, 'test_evidence_authenticated': False,
            'network_accessed': False, 'source_executed': False, 'pr_status': 'NOT_RUN', 'pr_created': False}


def main(argv=None):
    """Read optional local review metadata and emit only non-sensitive gate names.

    Inputless use is supported and reports missing prerequisites. Malformed input
    or unsafe paths fail closed; JSON diagnostics never include supplied content.
    """
    parser = PrivateArgumentParser(description=__doc__)
    parser.add_argument('--root', default=str(Path(__file__).absolute().parent.parent))
    parser.add_argument('--review', help='project-relative JSON file containing private input references')
    args = parser.parse_args(argv)
    try:
        root = project_root(args.root)
        review = {}
        if args.review is not None:
            path = ordinary_file(root, args.review)
            if path is None or path.stat().st_size > 65536:
                raise ValueError('review_unavailable_or_too_large')
            review = json.loads(path.read_text(encoding='utf-8-sig'))
        result = evaluate(root, review)
        print(json.dumps(result, indent=2))
        return 1 if result['invalid'] or result['access_denied'] else 0
    except PermissionError:
        print(json.dumps({'status': 'NOT_READY', 'error': 'access_denied',
                          'pr_status': 'NOT_RUN', 'pr_created': False}))
        return 1
    except (OSError, ValueError, TypeError, UnicodeError, json.JSONDecodeError):
        print(json.dumps({'status': 'NOT_READY', 'error': 'invalid_or_unavailable_input',
                          'pr_status': 'NOT_RUN', 'pr_created': False}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
