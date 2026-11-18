"""Exercise the standalone plugin payload builder with in-memory inputs."""

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
import unittest
from zipfile import ZIP_STORED, ZipFile


BUILDER = Path(__file__).resolve().parents[1] / 'scripts' / 'build_plugin_payload_e6c19a72.py'
PIN_OPTION = '--recipe-sha256'


def manifest_for(files):
    return {
        'format': 'boosterai-plugin-runtime-v1',
        'source_commit': '1' * 40,
        'files': {
            path: sha256(content.encode('utf-8')).hexdigest()
            for path, content in files.items()
        },
    }


def canonical_manifest(manifest):
    return (json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode('utf-8')


def request_bytes(manifest, files):
    return json.dumps({'manifest': manifest, 'files': files}, ensure_ascii=False).encode('utf-8')


class BuildPluginPayloadTests(unittest.TestCase):
    def setUp(self):
        self.files = {'scripts/sample.py': 'print("sample")\n', 'README.md': 'Caf\u00e9\r\n'}
        self.manifest = manifest_for(self.files)
        self.manifest_bytes = canonical_manifest(self.manifest)
        self.pin = sha256(self.manifest_bytes).hexdigest()

    def run_builder(self, request, *arguments):
        return subprocess.run(
            [sys.executable, '-I', '-S', '-B', str(BUILDER), *arguments],
            input=request,
            capture_output=True,
            timeout=10,
        )

    def assert_rejected(self, request, *arguments):
        result = self.run_builder(request, *arguments)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b'')
        self.assertIn(result.stderr, (b'invalid runtime build input\n', b'invalid runtime build input\r\n'))

    def test_builds_deterministic_stored_zip(self):
        first = self.run_builder(request_bytes(self.manifest, self.files), PIN_OPTION, self.pin)
        reordered_files = dict(reversed(list(self.files.items())))
        reordered_manifest = {
            'files': manifest_for(reordered_files)['files'],
            'source_commit': self.manifest['source_commit'],
            'format': self.manifest['format'],
        }
        second = self.run_builder(request_bytes(reordered_manifest, reordered_files), PIN_OPTION, self.pin)
        for result in (first, second):
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, b'')
        self.assertEqual(first.stdout, second.stdout)

        with ZipFile(BytesIO(first.stdout)) as archive:
            expected_names = ['runtime/manifest.json', *(f'runtime/{path}' for path in self.files)]
            self.assertCountEqual(archive.namelist(), expected_names)
            self.assertTrue(all(entry.compress_type == ZIP_STORED for entry in archive.infolist()))
            self.assertEqual(archive.read('runtime/manifest.json'), self.manifest_bytes)
            for path, content in self.files.items():
                self.assertEqual(archive.read(f'runtime/{path}'), content.encode('utf-8'))

    def test_rejects_changed_content_under_original_manifest(self):
        files = {**self.files, 'README.md': 'changed content'}
        self.assert_rejected(request_bytes(self.manifest, files), PIN_OPTION, self.pin)

    def test_rejects_wrong_recipe_pin(self):
        self.assert_rejected(request_bytes(self.manifest, self.files), PIN_OPTION, 'e' * 64)

    def test_rejects_invalid_cli_arguments_with_fixed_diagnostic(self):
        request = request_bytes(self.manifest, self.files)
        selection = (PIN_OPTION, self.pin)
        cases = {
            'unknown option': (*selection, '--private-flag-marker=private-value-marker'),
            'abbreviated pin option': ('--recipe-sha', self.pin),
            'identical repeated pin': (*selection, *selection),
            'different repeated pin': (PIN_OPTION, 'e' * 64, *selection),
        }
        for case, arguments in cases.items():
            with self.subTest(case=case):
                self.assert_rejected(request, *arguments)

    def test_rejects_missing_and_extra_files(self):
        cases = {
            'missing': {'README.md': self.files['README.md']},
            'extra': {**self.files, 'extra.md': 'extra content'},
        }
        for case, files in cases.items():
            with self.subTest(case=case):
                self.assert_rejected(request_bytes(self.manifest, files), PIN_OPTION, self.pin)

    def test_rejects_duplicate_decoded_property(self):
        request = request_bytes(self.manifest, self.files)
        duplicate = b'{"f\\u0069les":"first value",' + request[1:]
        self.assert_rejected(duplicate, PIN_OPTION, self.pin)

    def test_rejects_invalid_paths_even_with_matching_pin(self):
        oversized_member = '/'.join(['a' * 255] * 255 + ['a' * 248])
        self.assertEqual(len('runtime/' + oversized_member), 65536)
        cases = {
            'parent traversal': ('../outside.md',),
            'absolute path': ('/absolute.md',),
            'backslash separator': ('nested\\separator.md',),
            'ZIP member exceeds 65535 bytes': (oversized_member,),
            'path component exceeds 255 bytes': ('nested/' + 'a' * 256,),
            'directory has case aliases': ('Shared/one.md', 'shared/two.md'),
            'file and directory collide': ('shared', 'Shared/one.md'),
        }
        for case, paths in cases.items():
            with self.subTest(case=case):
                files = {path: 'sample' for path in paths}
                manifest = manifest_for(files)
                pin = sha256(canonical_manifest(manifest)).hexdigest()
                self.assert_rejected(request_bytes(manifest, files), PIN_OPTION, pin)


if __name__ == '__main__':
    unittest.main()
