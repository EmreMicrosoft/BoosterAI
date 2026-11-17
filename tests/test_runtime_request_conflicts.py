"""Check runtime request selection without creating workspace files."""

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("booster_runtime_requests", ROOT / "scripts/booster.py")
BOOSTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BOOSTER)
RUNTIME_ARGV = ["booster.py", "runtime-check", "--language", "python"]


class RuntimeRequestConflictTests(unittest.TestCase):
    def test_distinct_versions_fail_before_runtime_verification(self):
        for first, second in (("3.11", "3.12.0"), ("3.12.0", "3.11")):
            argv = [*RUNTIME_ARGV, "--requested-version", first, f"--requested-version={second}"]
            with (
                self.subTest(first=first, second=second),
                patch.object(sys, "argv", argv),
                patch.object(BOOSTER, "runtime_check") as check,
                redirect_stdout(io.StringIO()) as stdout,
                redirect_stderr(io.StringIO()) as stderr,
                self.assertRaises(SystemExit) as error,
            ):
                BOOSTER.main()
            check.assert_not_called()
            self.assertEqual(error.exception.code, 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertTrue(stderr.getvalue().splitlines()[-1].endswith(
                "runtime-check: error: conflicting --requested-version values"))
            self.assertNotIn(first, stderr.getvalue())
            self.assertNotIn(second, stderr.getvalue())

    def test_default_single_and_identical_requests_keep_runtime_results(self):
        matching = ".".join(str(part) for part in sys.version_info[:3])
        mismatching = "999.999"
        cases = (
            (None, []),
            (matching, ["--requested-version", matching]),
            (mismatching, ["--requested-version", mismatching]),
            (matching, ["--requested-version", matching, f"--requested-version={matching}"]),
            (mismatching, ["--requested-version", mismatching, f"--requested-version={mismatching}"]),
        )
        for requested, options in cases:
            expected = BOOSTER.runtime_check("python", requested_version=requested)
            with (
                self.subTest(options=options),
                patch.object(sys, "argv", [*RUNTIME_ARGV, *options]),
                patch.object(BOOSTER, "runtime_check", wraps=BOOSTER.runtime_check) as check,
                redirect_stdout(io.StringIO()) as stdout,
                redirect_stderr(io.StringIO()) as stderr,
            ):
                status = BOOSTER.main()
            check.assert_called_once_with("python", None, requested)
            self.assertEqual(status, int(not expected["valid"]))
            self.assertEqual(json.loads(stdout.getvalue()), expected)
            self.assertEqual(stderr.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
