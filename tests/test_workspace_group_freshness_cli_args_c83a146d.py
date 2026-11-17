"""Check freshness CLI parsing without opening an index or source file."""

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'project_index_freshness_a62e9d47.py'
SPEC = importlib.util.spec_from_file_location('freshness_cli_args', SCRIPT)
FRESHNESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FRESHNESS)


class FreshnessCliArgumentTest(unittest.TestCase):
    def invoke_parser(self, argv):
        with (
            patch.object(FRESHNESS, 'check_freshness',
                         side_effect=AssertionError('unexpected freshness comparison')) as check,
            redirect_stdout(io.StringIO()) as stdout,
            redirect_stderr(io.StringIO()) as stderr,
            self.assertRaises(SystemExit) as exit_info,
        ):
            FRESHNESS.main(argv)
        check.assert_not_called()
        return exit_info.exception.code, stdout.getvalue(), stderr.getvalue()

    def test_unknown_arguments_are_not_echoed(self):
        unknown = '--fictional-option'
        value = 'synthetic-argument-value'
        code, stdout, stderr = self.invoke_parser([
            '--root', '.', '--path', '_partials/README.md', unknown, value,
        ])
        self.assertEqual(code, 2)
        self.assertEqual(stdout, '')
        self.assertTrue(stderr.rstrip().endswith('invalid arguments. Use --help for usage.'))
        self.assertFalse(unknown in stderr or value in stderr)

    def test_help_is_printed_to_stdout(self):
        code, stdout, stderr = self.invoke_parser(['--help'])
        self.assertEqual(code, 0)
        self.assertEqual(stderr, '')
        self.assertIn('--root', stdout)
        self.assertIn('--path', stdout)

    def test_repeated_root_is_rejected_before_comparison(self):
        base = ['--root', '.', '--path', '_partials/README.md',
                '--path', '_boosterAI/_partials/README.md']
        for extra in (['--root', '.'], ['--root', 'other-root'], ['--root=other-root']):
            with self.subTest(extra=extra):
                code, stdout, stderr = self.invoke_parser(base + extra)
                self.assertEqual(code, 2)
                self.assertEqual(stdout, '')
                self.assertTrue(stderr.rstrip().endswith('invalid arguments. Use --help for usage.'))
                self.assertNotIn('other-root', stderr)


    def test_empty_root_is_rejected_before_comparison(self):
        for root in (['--root='], ['--root', '']):
            with self.subTest(root=root):
                code, stdout, stderr = self.invoke_parser(root + ['--path', '_partials/README.md'])
                self.assertEqual(code, 2)
                self.assertEqual(stdout, '')
                self.assertTrue(stderr.rstrip().endswith('invalid arguments. Use --help for usage.'))


if __name__ == '__main__':
    unittest.main()
