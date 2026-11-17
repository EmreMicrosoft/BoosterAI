"""Fixture-free coverage of the active archive pointer used by search."""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import archive_sync


class ArchiveSearchActivePointerTest(unittest.TestCase):
    def test_search_rejects_duplicate_decoded_metadata_without_opening_snapshot(self):
        cases = {
            'root': '"note":1,"note":2',
            'nested': '"details":{"note":1,"note":2}',
            'escaped': r'"note":1,"\u006eote":2',
        }
        for variant, metadata in cases.items():
            with self.subTest(variant=variant):
                payload = '{"commit":"' + '0' * 40 + '",' + metadata + '}'
                output = io.StringIO()
                with (
                    patch.object(Path, 'mkdir', side_effect=AssertionError('search created storage')) as mkdir,
                    patch.object(Path, 'read_text', autospec=True, return_value=payload) as read_text,
                    patch.object(archive_sync, 'verify_snapshot') as verify,
                    patch.object(sys, 'argv', ['archive_sync.py', 'search', '--root', str(ROOT)]),
                    redirect_stdout(output),
                ):
                    self.assertEqual(archive_sync.main(), 1)
                self.assertEqual(json.loads(output.getvalue()), {
                    'status': 'FAILED', 'reason': 'duplicate archive manifest field',
                })
                read_text.assert_called_once_with(
                    ROOT / '_boosterAI' / 'archive-sync' / 'active.json', encoding='utf-8',
                )
                verify.assert_not_called()
                mkdir.assert_not_called()

    def test_search_allows_same_metadata_name_in_separate_objects(self):
        commit = '0' * 40
        payload = json.dumps({
            'commit': commit, 'left': {'note': 1}, 'right': {'note': 2},
        })
        with (
            patch.object(Path, 'mkdir', side_effect=AssertionError('search created storage')) as mkdir,
            patch.object(Path, 'read_text', return_value=payload),
            patch.object(archive_sync, 'verify_snapshot', return_value={'entries': []}) as verify,
        ):
            actual = archive_sync.search(ROOT)
        verify.assert_called_once_with(ROOT / '_boosterAI' / 'archive-sync', commit)
        mkdir.assert_not_called()
        self.assertEqual(actual, {
            'commit': commit, 'results': [], 'related_files_by_record': {},
            'execution_authorized': False,
        })


if __name__ == '__main__':
    unittest.main()
