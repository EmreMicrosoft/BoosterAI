"""Injected denial regressions; no verifier, filesystem fixture or denial is run."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'denial_memory_fixture', ROOT / 'tests/test_harness_waiting_prerequisite.py')
fixture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixture)
h = fixture.h


class DenialPersistenceTests(unittest.TestCase):
    def setUp(self):
        """Reuse the in-memory state adapter without executing its test methods."""
        self.memory = fixture.WaitingPrerequisiteTests()
        self.memory.setUp()
        self.addCleanup(self.memory.doCleanups)
        self.memory.data['tasks']['A']['verified_files'] = self.memory.files['A'].copy()
        self.memory.data['tasks']['B']['timeout_seconds'] = 10
        stack = self.memory.stack
        stack.enter_context(patch.object(h._TOOLS, 'scratch_directory', return_value=ROOT / '_temp-files'))
        stack.enter_context(patch.object(h.tempfile, 'mkdtemp', return_value=str(ROOT / '_temp-files/unused-denial')))
        stack.enter_context(patch.object(Path, 'lstat', return_value=ROOT.stat()))
        self.denial = PermissionError('synthetic denial only')
        self.run = stack.enter_context(patch.object(h.subprocess, 'run', side_effect=self.denial))

    def test_direct_denial_is_durable_and_not_replayable(self):
        """A known denial survives status/reconciliation without retry eligibility."""
        with self.assertRaisesRegex(h.VerificationAccessDenied, 'denial recorded') as caught:
            self.memory.verify('B')
        self.assertIs(caught.exception.__cause__, self.denial)
        self.assertEqual(self.run.call_count, 1)
        self.assertEqual(h.status(ROOT, 'plan.json')['tasks']['B']['status'], 'DENIED')
        with self.assertRaisesRegex(ValueError, 'not recoverable'):
            h.reconcile(ROOT, 'plan.json', 'B', 'B')
        with self.assertRaisesRegex(ValueError, 'denied'):
            self.memory.verify('B')
        self.assertEqual(self.run.call_count, 1)

    def test_initial_state_write_denial_is_not_retried(self):
        """A failed initial write never launches a verifier or repeats persistence."""
        with patch.object(h._STATE, 'write', side_effect=self.denial) as write:
            with self.assertRaisesRegex(h.VerificationAccessDenied, 'not confirmed') as caught:
                self.memory.verify('B')
        self.assertIs(caught.exception.__cause__, self.denial)
        self.assertEqual(write.call_count, 1)
        self.run.assert_not_called()
        self.assertEqual(self.memory.data['tasks']['B']['status'], 'ACTIVE')

    def test_failed_denial_persistence_preserves_original_exception_and_uncertainty(self):
        """Recording failure does not misreport persistence or mask the first denial."""
        calls = []
        def write(root, raw, value):
            calls.append(value['tasks']['B']['status'])
            if len(calls) == 2:
                raise OSError('synthetic persistence failure')
            return self.memory.write(root, raw, value)
        with patch.object(h._STATE, 'write', side_effect=write):
            with self.assertRaisesRegex(h.VerificationAccessDenied, 'not confirmed') as caught:
                self.memory.verify('B')
        self.assertIs(caught.exception.__cause__, self.denial)
        self.assertEqual(calls, ['VERIFYING', 'DENIED'])
        self.assertEqual(self.memory.data['tasks']['B']['status'], 'VERIFYING')

    def test_stop_state_write_denial_is_not_retried(self):
        """A failed STOP write is never retried under a different status."""
        calls = []
        def write(root, raw, value):
            calls.append(value['tasks']['B']['status'])
            if len(calls) == 2:
                raise self.denial
            return self.memory.write(root, raw, value)
        def interruptible(command, root, env, timeout, stream, persist_stop):
            persist_stop()
        with patch.object(h._STATE, 'write', side_effect=write), patch.object(h, '_interruptible', side_effect=interruptible):
            with self.assertRaisesRegex(h.VerificationAccessDenied, 'not confirmed'):
                h.verify(ROOT, 'plan.json', 'B', 'B', 'test.py', 'Checks.test_ok', stop_stream=object())
        self.assertEqual(calls, ['VERIFYING', 'STOP_REQUESTED'])
        self.run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
