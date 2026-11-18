"""Check the helper registry reader and workspace creation boundary."""

import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, call, patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "project_tools_helper_lookup", ROOT / "scripts/project_tools.py",
)
PROJECT_TOOLS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROJECT_TOOLS)


class HelperLookupReadOnlyTests(unittest.TestCase):
    def test_missing_records_stop_before_metadata_lookup(self):
        records = Mock(spec=Path)
        records.is_dir.return_value = False
        records.mkdir.side_effect = AssertionError("helper lookup tried to create records")

        with patch.object(PROJECT_TOOLS, "safe", return_value=records) as safe:
            with self.assertRaisesRegex(ValueError, "^project records directory missing$"):
                PROJECT_TOOLS.helper_check(ROOT, "example", "1.0.0")

        safe.assert_called_once_with(ROOT, "_boosterAI")
        records.mkdir.assert_not_called()

    def test_existing_helper_checks_integrity_without_creating_records(self):
        metadata = {
            "format": "boosterai-helper-v1",
            "name": "example",
            "version": "1.0.0",
            "code": "helpers/example/1.0.0/example_3b7e41a9.py",
            "evidence": "evidence/example.json",
            "code_sha256": "a" * 64,
            "evidence_sha256": "b" * 64,
            "tested_target": "Python CLI",
            "evidence_authenticated": False,
        }
        records = Mock(spec=Path)
        records.is_dir.return_value = True
        records.mkdir.side_effect = AssertionError("helper lookup tried to create records")
        metadata_path = Mock(spec=Path)
        metadata_path.read_text.return_value = json.dumps(metadata)
        code_path = Mock(spec=Path)
        code_path.is_file.return_value = True
        evidence_path = Mock(spec=Path)
        evidence_path.is_file.return_value = True

        with (
            patch.object(PROJECT_TOOLS, "safe", side_effect=[
                records, metadata_path, code_path, evidence_path,
            ]) as safe,
            patch.object(PROJECT_TOOLS, "sha", side_effect=[
                metadata["code_sha256"], metadata["evidence_sha256"],
            ]) as sha,
        ):
            result = PROJECT_TOOLS.helper_check(ROOT, "example", "1.0.0")

        records.mkdir.assert_not_called()
        metadata_path.read_text.assert_called_once_with(encoding="utf-8")
        self.assertEqual(safe.call_args_list, [
            call(ROOT, "_boosterAI"),
            call(records, "helpers/example/1.0.0/metadata.json"),
            call(records, metadata["code"]),
            call(records, metadata["evidence"]),
        ])
        self.assertEqual(sha.call_args_list, [call(code_path), call(evidence_path)])
        self.assertEqual(result, {
            "path": metadata["code"],
            "metadata": metadata,
            "actual_runtime_retest_required_when_target_changes": True,
        })

    def test_default_workspace_still_requests_creation(self):
        records = Mock(spec=Path)
        with patch.object(PROJECT_TOOLS, "safe", return_value=records) as safe:
            result = PROJECT_TOOLS.workspace(ROOT)

        self.assertIs(result, records)
        safe.assert_called_once_with(ROOT, "_boosterAI")
        records.mkdir.assert_called_once_with(exist_ok=True)


if __name__ == "__main__":
    unittest.main()
