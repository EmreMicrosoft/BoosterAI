"""Run the portable, explicitly bounded unittest selection in an owned workspace."""

import argparse
import importlib
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_MODULES = {"test_find_dirs_partial.py", "test_continuity_hook.py"}
EXCLUDED_CASE = "test_self_check_reports_missing_and_broken_registration"


def test_workspace():
    """Return the existing or newly created safe repository-local temporary root.

    Reject symbolic links, Windows reparse points and paths resolving outside the
    checkout. The directory is only a parent for owned, unique operations; this
    function never deletes existing children or alters any global configuration.
    """
    base = ROOT / "_temp-files"
    base.mkdir(exist_ok=True)
    info = base.lstat()
    if (stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400
            or base.resolve().parent != ROOT):
        raise ValueError("temporary root must be an ordinary checkout directory")
    return base


def find_interpreter(requested):
    """Find one requested Python minor version without downloading a runtime.

    Prefer the current executable when it matches. Otherwise inspect GitHub's
    read-only preinstalled tool cache for a stable x64 release of that minor
    version and select the highest patch. Missing or malformed versions raise
    ValueError; the selected interpreter verifies its own version before tests.
    """
    if re.fullmatch(r"3\.(?:10|11|12|13|14)", requested) is None:
        raise ValueError("unsupported CI Python version")
    major, minor = (int(part) for part in requested.split("."))
    if sys.version_info[:2] == (major, minor):
        return Path(sys.executable)
    cache = os.environ.get("RUNNER_TOOL_CACHE")
    if not cache:
        raise ValueError("requested Python is not current and no runner tool cache is available")
    versions = Path(cache) / "Python"
    candidates = []
    if versions.is_dir():
        for directory in versions.iterdir():
            match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", directory.name)
            if not match or tuple(map(int, match.groups()[:2])) != (major, minor):
                continue
            executable = directory / "x64" / ("python.exe" if os.name == "nt" else "bin/python3")
            if executable.is_file():
                candidates.append((int(match.group(3)), executable))
    if not candidates:
        raise ValueError("requested Python is absent from the preinstalled runner tool cache")
    return max(candidates, key=lambda item: item[0])[1]


def leaves(suite):
    """Yield individual unittest cases from a loader-produced nested suite.

    This only traverses the in-memory suite; no tests run and no files change.
    """
    for case in suite:
        if isinstance(case, unittest.TestSuite):
            yield from leaves(case)
        else:
            yield case


def run_selected():
    """Run permitted discovered tests while preserving excluded and unknown work.

    Exclude the two locally rejected candidate modules, link-creation cases and
    the package-copy case that could copy those candidates. Test fixtures and
    child process temporary files stay inside a unique checkout-local operation.
    Return zero only when the selected suite succeeds; do not call this full
    discovery or infer acceptance of any excluded case.
    """
    base = test_workspace()
    with tempfile.TemporaryDirectory(prefix="ci-suite-", dir=base) as operation:
        for name in ("TEMP", "TMP", "TMPDIR"):
            os.environ[name] = operation
        tempfile.tempdir = operation
        check = subprocess.run([sys.executable, "-I", "-S", "-B",
                                str(ROOT / "scripts/booster.py"), "self-check",
                                "--root", str(ROOT)], cwd=ROOT, check=False)
        if check.returncode != 0:
            return check.returncode
        tests = ROOT / "tests"
        sys.path.insert(0, str(tests))
        loader = unittest.TestLoader()
        selected = unittest.TestSuite()
        excluded_cases = 0
        for path in sorted(tests.glob("test_*.py")):
            if path.name in EXCLUDED_MODULES:
                continue
            module = importlib.import_module(path.stem)
            for case in leaves(loader.loadTestsFromModule(module)):
                name = case.id().lower()
                if "symlink" in name or "junction" in name or name.endswith(EXCLUDED_CASE):
                    excluded_cases += 1
                else:
                    selected.addTest(case)
        print("Selected %d tests; excluded %d individual cases and two candidate modules."
              % (selected.countTestCases(), excluded_cases), flush=True)
        result = unittest.TextTestRunner(verbosity=1).run(selected)
        return 0 if result.wasSuccessful() else 1


def main():
    """Validate and run a requested preinstalled interpreter without host changes.

    ``--python`` names a supported Python minor version. A child process checks
    that its actual interpreter matches before executing the selected tests.
    Missing runtimes fail explicitly rather than installing or silently skipping.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        interpreter = find_interpreter(args.python)
        if args.execute:
            actual = "%d.%d" % sys.version_info[:2]
            if actual != args.python:
                raise ValueError("resolved interpreter does not match requested version")
            print("Running selected tests on Python %s (%s)." % (sys.version.split()[0], sys.platform), flush=True)
            return run_selected()
        with tempfile.TemporaryDirectory(prefix="ci-launch-", dir=test_workspace()) as operation:
            environment = dict(os.environ)
            environment.update({name: operation for name in ("TEMP", "TMP", "TMPDIR")})
            command = [str(interpreter), "-I", "-S", "-B", str(Path(__file__)),
                       "--python", args.python, "--execute"]
            return subprocess.run(command, cwd=ROOT, env=environment, check=False).returncode
    except (OSError, ValueError) as error:
        print("CI runner error: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
