import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).absolute().parents[1] / 'scripts'))
import project_tools


class ArchiveSearchDuplicateKeysTest(unittest.TestCase):
    def test_rejects_duplicate_decoded_keys_before_validation(self):
        cases = {
            'root': '{"format":"boosterai-index-v1","entries":[],"sample":"first","sample":"second"}',
            'nested': (
                '{"format":"boosterai-index-v3",'
                '"entries":[{"details":{"sample":"first","sample":"second"}}]}'
            ),
            'escaped': (
                r'{"format":"boosterai-index-v2","entries":[],'
                r'"sample":"first","s\u0061mple":"second"}'
            ),
        }
        for name, payload in cases.items():
            with self.subTest(name=name):
                index = Mock(spec_set=Path)
                index.exists.return_value = True
                index.read_text.return_value = payload
                with (
                    patch.object(project_tools, 'repository_root', return_value=Path('virtual-root')),
                    patch.object(project_tools, 'safe', return_value=index),
                    patch.object(project_tools.profile, 'validate_index') as validate_index,
                ):
                    with self.assertRaises(ValueError) as error:
                        project_tools.archive_search('virtual-root', query='unmatched')
                self.assertEqual(str(error.exception), 'duplicate archive index field')
                validate_index.assert_not_called()


if __name__ == '__main__':
    unittest.main()
