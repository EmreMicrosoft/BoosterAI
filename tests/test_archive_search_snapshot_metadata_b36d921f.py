"""Fixture-free checks for snapshot metadata rejected by archive search."""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import call, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import archive_sync


class ArchiveSearchSnapshotMetadataTest(unittest.TestCase):
    def test_search_rejects_duplicate_snapshot_metadata_before_reading_index(self):
        commit = '0' * 40
        work = ROOT / '_boosterAI' / 'archive-sync'
        active_path = work / 'active.json'
        metadata_path = work / 'snapshots' / commit / 'snapshot.json'
        active = json.dumps({'commit': commit})
        metadata_header = json.dumps({
            'commit': commit,
            'repository': archive_sync.REPOSITORY,
            'index_sha256': '0' * 64,
        })[:-1]
        variants = {
            'root': '"note":1,"note":2',
            'nested': '"details":{"note":1,"note":2}',
            'escaped': r'"note":1,"\u006eote":2',
        }
        for name, fields in variants.items():
            with self.subTest(variant=name):
                texts = {
                    active_path: active,
                    metadata_path: metadata_header + ',' + fields + '}',
                }
                output = io.StringIO()
                with (
                    patch.object(Path, 'mkdir', side_effect=AssertionError('search created storage')) as mkdir,
                    patch.object(Path, 'open', side_effect=AssertionError('metadata reached index')) as open_file,
                    patch.object(Path, 'read_text', autospec=True,
                                 side_effect=lambda path, *, encoding: texts[path]) as read_text,
                    patch.object(sys, 'argv', ['archive_sync.py', 'search', '--root', str(ROOT)]),
                    redirect_stdout(output),
                ):
                    self.assertEqual(archive_sync.main(), 1)
                self.assertEqual(json.loads(output.getvalue()), {
                    'status': 'FAILED', 'reason': 'duplicate archive manifest field',
                })
                self.assertEqual(read_text.call_args_list, [
                    call(active_path, encoding='utf-8'),
                    call(metadata_path, encoding='utf-8'),
                ])
                open_file.assert_not_called()
                mkdir.assert_not_called()


if __name__ == '__main__':
    unittest.main()
