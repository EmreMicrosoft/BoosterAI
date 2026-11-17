"""Verify omitted and explicit-empty archive filters through both CLI handlers."""

from contextlib import nullcontext, redirect_stdout
from io import BytesIO, StringIO
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import archive_sync
import project_tools

PROJECT = Path('virtual-archive-filter-root')
COMMIT = '0' * 40


def entry(name, categories, tags):
    return {
        'name': name, 'title': name, 'code': f'solutions/{name}/revisions/0001/example.py',
        'code_sha256': '0' * 64, 'evidence_sha256': '1' * 64, 'outcome': 'success',
        'test_summary': 'Checked', 'categories': categories, 'tags': tags,
    }


class ArchiveEmptyFilterParityTest(unittest.TestCase):
    def setUp(self):
        manifest = {
            'format': 'boosterai-index-v1',
            'entries': [
                entry('empty-path', [], ['python']),
                entry('typed-path', ['filesystem', 'search'], ['python', 'unittest']),
            ],
        }
        self.raw = json.dumps(manifest).encode('utf-8')
        self.manifest = archive_sync.validate_manifest(self.raw)

    def run_handler(self, module, action, flags):
        output = StringIO()
        with (
            patch.object(sys, 'argv', [module.__name__, action, '--root', str(PROJECT), *flags]),
            redirect_stdout(output),
        ):
            self.assertEqual(module.main(), 0)
        return json.loads(output.getvalue())

    def root_result(self, flags):
        index = Mock(spec_set=Path)
        index.exists.return_value = True
        with BytesIO(self.raw) as stream:
            index.open.return_value = nullcontext(stream)
            with (
                patch.object(project_tools, 'repository_root', return_value=PROJECT),
                patch.object(project_tools, 'safe', return_value=index),
            ):
                return self.run_handler(project_tools, 'search-archive', flags)

    def snapshot_result(self, flags):
        with (
            patch.object(archive_sync, 'storage', return_value=PROJECT),
            patch.object(archive_sync, 'safe', side_effect=lambda root, name: root / name),
            patch.object(archive_sync, '_read_metadata_json', return_value={'commit': COMMIT}),
            patch.object(archive_sync, 'verify_snapshot', return_value=self.manifest),
        ):
            return self.run_handler(archive_sync, 'search', flags)

    def test_legacy_v1_filter_parity(self):
        cases = (
            ([], ['empty-path', 'typed-path']),
            (['--tag', 'unittest'], ['typed-path']),
            (['--category', 'filesystem/search'], ['typed-path']),
            (['--category', 'filesystem/search', '--tag', 'python'], ['typed-path']),
            (['--category=', '--tag', 'python'], ['empty-path']),
            (['--category=', '--tag', 'unittest'], []),
            (['--category', 'filesystem/search', '--tag='], []),
            (['--category=', '--tag='], []),
        )
        for flags, names in cases:
            for read in (self.root_result, self.snapshot_result):
                with self.subTest(reader=read.__name__, flags=flags):
                    result = read(flags)
                    self.assertEqual([item['name'] for item in result['results']], names)
                    self.assertEqual(result['related_files_by_record'], {name: [] for name in names})


if __name__ == '__main__':
    unittest.main()
