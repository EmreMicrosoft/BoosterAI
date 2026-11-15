import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

from repo_temp import workspace


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('archive_profile_test', ROOT / 'scripts/archive_profile.py')
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)
tools_spec = importlib.util.spec_from_file_location('project_tools_profile_test', ROOT / 'scripts/project_tools.py')
tools = importlib.util.module_from_spec(tools_spec)
tools_spec.loader.exec_module(tools)


class ArchiveProfileTests(unittest.TestCase):
    def setUp(self):
        self.root = workspace(self)
        self.index = json.loads((ROOT / 'solutions/index.json').read_text(encoding='utf-8'))

    def test_real_archive_profile_paths_hashes_and_function_docs(self):
        self.assertEqual(profile.validate_index(self.index), self.index)
        filenames = []
        metadata = list((ROOT / 'solutions/filesystem').rglob('metadata.json'))
        self.assertEqual(len(metadata), 5)  # Two current records and three preserved revisions.
        for record in metadata:
            entry = json.loads(record.read_text(encoding='utf-8'))
            profile.validate_entry(entry)
            code = ROOT / entry['code']
            self.assertEqual(hashlib.sha256(code.read_bytes()).hexdigest(), entry['code_sha256'])
            self.assertTrue(tools.python_docs_complete(code.read_text(encoding='utf-8')))
            self.assertFalse(any(key.startswith('legacy_') for key in entry))
            self.assertEqual(entry['evidence_basis'], 'sanitized-summary-sha256')
            self.assertEqual(entry['evidence_sha256'], hashlib.sha256(entry['test_summary'].encode('utf-8')).hexdigest())
            if 'revisions' in record.parts:
                filenames.append(code.name)
                self.assertRegex(code.name, r'^[a-z0-9-]+-[0-9a-f]{8}\.py$')
        self.assertEqual(len(filenames), 3)
        self.assertEqual(len(filenames), len(set(filenames)))
        previous = list((ROOT / 'solutions/filesystem').rglob('previous.json'))
        self.assertEqual(len(previous), 1)
        for record in previous:
            entry = json.loads(record.read_text(encoding='utf-8'))
            profile.validate_entry(entry)
            self.assertFalse(any(key.startswith('legacy_') for key in entry))
            self.assertEqual(entry['evidence_basis'], 'sanitized-summary-sha256')
            self.assertEqual(entry['evidence_sha256'], hashlib.sha256(entry['test_summary'].encode('utf-8')).hexdigest())

    def test_schema_and_semantics_reject_invalid_records(self):
        for field, value in [('code', 'solutions/../../outside.py'), ('revision', True),
                             ('keywords', []), ('code_sha256', 'bad'), ('name', 'bad/name')]:
            changed = copy.deepcopy(self.index)
            changed['entries'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                profile.validate_index(changed)
        with self.assertRaisesRegex(ValueError, 'unsupported schema keyword'):
            profile.validate_schema({}, {'unknownConstraint': True})

    def test_sanitized_summary_hash_mismatch_is_rejected(self):
        for field, value in [('test_summary', 'A changed summary that does not match the recorded digest.'),
                             ('evidence_sha256', '0' * 64)]:
            changed = copy.deepcopy(self.index)
            changed['entries'][0][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'summary hash mismatch'):
                profile.validate_index(changed)

    def test_deterministic_index_and_nested_category(self):
        entries = list(reversed(self.index['entries']))
        rebuilt = profile.build_index(entries)
        self.assertEqual(rebuilt, self.index)
        self.assertIn(['filesystem', 'search'], rebuilt['categories'])
        self.assertEqual(json.dumps(rebuilt, sort_keys=True), json.dumps(profile.build_index(entries), sort_keys=True))


if __name__ == '__main__':
    unittest.main(verbosity=2)
