"""Exercise file-observed BoosterAI continuity in owned repository fixtures."""

import copy
import hashlib
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

import repo_temp


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "continuity_plan", ROOT / "scripts" / "continuity_plan_64e9b1c2.py"
)
continuity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(continuity)


def digest(content):
    """Return the expected SHA-256 of fixture bytes without creating a file."""
    return hashlib.sha256(content).hexdigest()


def node(node_id, *, owner=None, inputs=(), output=None, dependencies=(), content=b"ok"):
    """Build one explicit, file-accepted test slice without touching the filesystem."""
    output = output or node_id + ".out"
    owner = owner or node_id + "-owner"
    return {
        "id": node_id,
        "owner": owner,
        "contract": "Produce the fixture output for " + node_id,
        "file_owners": {output: owner},
        "inputs": list(inputs),
        "outputs": [output],
        "depends_on": list(dependencies),
        "target": output,
        "acceptance": {"type": "sha256", "path": output, "sha256": digest(content)},
    }


class ContinuityPlanTests(unittest.TestCase):
    """Verify actual file reads, bounded reuse, graph safety and stop behavior."""

    def setUp(self):
        """Create one owned operation directory with registered success/failure cleanup."""
        self.project = repo_temp.workspace(self)

    def write(self, relative, content):
        """Write only one regular fixture file beneath this test's owned directory."""
        path = self.project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def graph(self):
        """Create a three-slice dependency chain plus one independent real target."""
        self.write("source.txt", b"first")
        self.write("other.txt", b"stable")
        for name in ("a", "b", "c", "d"):
            self.write(name + ".out", name.encode("ascii"))
        return {"nodes": [
            node("c", inputs=("b.out",), dependencies=("b",), content=b"c"),
            node("a", inputs=("source.txt",), content=b"a"),
            node("d", inputs=("other.txt",), content=b"d"),
            node("b", inputs=("a.out",), dependencies=("a",), content=b"b"),
        ]}

    def test_real_target_read_is_required_and_receipts_are_not_evidence(self):
        """A claimed pass cannot verify a missing or mismatched actual output file."""
        plan = {"nodes": [node("a", content=b"expected")]}
        original = copy.deepcopy(plan)
        absent = continuity.evaluate(self.project, plan, observed=("a",))
        self.assertEqual(absent["nodes"]["a"]["state"], "PLANNED")
        self.assertFalse(absent["nodes"]["a"]["target_file_read"])
        self.assertEqual(absent["ready"], ["a"])
        self.write("a.out", b"wrong")
        wrong = continuity.evaluate(self.project, plan, observed=("a",))
        self.assertEqual(wrong["nodes"]["a"]["state"], "PLANNED")
        self.assertTrue(wrong["nodes"]["a"]["target_file_read"])
        self.assertFalse(wrong["nodes"]["a"]["target_matches_expected"])
        with self.assertRaisesRegex(ValueError, "invalid previous evidence"):
            continuity.evaluate(self.project, plan, {"a": {"agent_says_pass": True}})
        self.write("a.out", b"expected")
        accepted = continuity.evaluate(self.project, plan, observed=("a",))
        self.assertEqual(accepted["nodes"]["a"]["state"], "TARGET_MATCHED")
        self.assertTrue(accepted["nodes"]["a"]["target_matches_expected"])
        self.assertFalse(accepted["continuation_permitted"])
        self.assertEqual(plan, original)
        self.assertTrue(any("do not prove code execution" in text for text in accepted["limitations"]))

    def test_reuse_and_input_change_invalidate_only_dependent_slices(self):
        """Unchanged results are reread and reused; a changed input stales its descendants."""
        plan = self.graph()
        first = continuity.evaluate(self.project, plan, observed=("a", "b", "c", "d"))
        self.assertTrue(all(row["state"] == "TARGET_MATCHED" for row in first["nodes"].values()))
        reorder = copy.deepcopy(plan)
        reorder["nodes"].reverse()
        repeated = continuity.evaluate(self.project, reorder, previous=first["evidence"])
        self.assertEqual(repeated["order"], ["a", "d", "b", "c"])
        self.assertTrue(all(row["state"] == "TARGET_REUSED" for row in repeated["nodes"].values()))
        self.write("source.txt", b"changed")
        changed = continuity.evaluate(self.project, plan, previous=first["evidence"])
        self.assertEqual({key: value["state"] for key, value in changed["nodes"].items()},
                         {"a": "STALE", "b": "STALE", "c": "STALE", "d": "TARGET_REUSED"})
        self.assertEqual(changed["ready"], ["a"])
        resumed = continuity.evaluate(self.project, plan, previous=changed["evidence"], observed=("a",))
        self.assertEqual(resumed["nodes"]["a"]["state"], "TARGET_MATCHED")
        self.assertEqual(resumed["nodes"]["b"]["state"], "STALE")
        self.assertEqual(resumed["ready"], ["b"])

    def test_contract_output_and_dependency_changes_stale_affected_nodes(self):
        """Changing contract, output bytes or dependency edges invalidates relevant evidence."""
        plan = self.graph()
        first = continuity.evaluate(self.project, plan, observed=("a", "b", "c", "d"))
        changed_contract = copy.deepcopy(plan)
        next(item for item in changed_contract["nodes"] if item["id"] == "a")["contract"] += " revised"
        check = continuity.evaluate(self.project, changed_contract, previous=first["evidence"])
        self.assertEqual([check["nodes"][item]["state"] for item in ("a", "b", "c", "d")],
                         ["STALE", "STALE", "STALE", "TARGET_REUSED"])
        changed_dependency = copy.deepcopy(plan)
        next(item for item in changed_dependency["nodes"] if item["id"] == "d")["depends_on"] = ["a"]
        check = continuity.evaluate(self.project, changed_dependency, previous=first["evidence"])
        self.assertEqual(check["nodes"]["d"]["state"], "STALE")
        self.assertEqual(check["nodes"]["a"]["state"], "TARGET_REUSED")
        self.write("a.out", b"different")
        check = continuity.evaluate(self.project, plan, previous=first["evidence"], observed=("a",))
        self.assertFalse(check["nodes"]["a"]["target_matches_expected"])
        self.assertEqual([check["nodes"][item]["state"] for item in ("a", "b", "c", "d")],
                         ["STALE", "STALE", "STALE", "TARGET_REUSED"])

    def test_missing_input_blocks_ready_and_missing_output_cannot_be_reused(self):
        """Absent inputs block execution, and a removed output invalidates prior acceptance."""
        plan = {"nodes": [node("a", inputs=("source.txt",), content=b"a")]}
        result = continuity.evaluate(self.project, plan, observed=("a",))
        self.assertEqual(result["ready"], [])
        self.assertEqual(result["nodes"]["a"]["missing_inputs"], ["source.txt"])
        self.write("source.txt", b"input")
        output = self.write("a.out", b"a")
        result = continuity.evaluate(self.project, plan, observed=("a",))
        output.unlink()
        result = continuity.evaluate(self.project, plan, previous=result["evidence"])
        self.assertEqual(result["nodes"]["a"]["state"], "STALE")
        self.assertEqual(result["nodes"]["a"]["missing_outputs"], ["a.out"])
        self.assertEqual(result["ready"], ["a"])

    def test_ready_and_parallel_ready_distinguish_shared_owners_and_files(self):
        """All ready slices are shown, but a parallel batch claims each owner/file once."""
        a, b = node("a", owner="alpha"), node("b", owner="bravo")
        a["file_owners"]["shared.txt"] = "custodian"
        b["file_owners"]["shared.txt"] = "custodian"
        c, d = node("c", owner="alpha"), node("d", owner="delta")
        plan = {"nodes": [d, b, c, a]}
        result = continuity.evaluate(self.project, plan)
        self.assertEqual(result["ready"], ["a", "b", "c", "d"])
        self.assertEqual(result["parallel_ready"], ["a", "d"])
        self.assertEqual(result["deferred_ready"], ["b", "c"])

    def test_denial_blocks_only_descendants_and_never_reads_their_files(self):
        """Simulated denials stop a node and descendants while independent work remains ready."""
        plan = {"nodes": [node("a"), node("b", dependencies=("a",)), node("c")]}
        original_read = continuity._read_hash

        def read_independent(root, path):
            """Fail if the evaluator tries reading the simulated denied subtree."""
            self.assertNotIn(path, {"a.out", "b.out"})
            return original_read(root, path)

        with patch.object(continuity, "_read_hash", side_effect=read_independent):
            result = continuity.evaluate(self.project, plan, denied=("a",), observed=("a",))
        self.assertTrue(result["continuation_permitted"])
        self.assertEqual(result["nodes"]["a"]["state"], "DENIED")
        self.assertEqual(result["nodes"]["b"]["state"], "BLOCKED")
        self.assertEqual(result["blocked_descendants"], ["b"])
        self.assertEqual(result["ready"], ["c"])

    def test_stop_returns_no_read_or_continuation(self):
        """Global STOP halts all slices even if the project root is unavailable."""
        result = continuity.evaluate(self.project / "not-created", {"nodes": [node("a")]}, stopped=True)
        self.assertFalse(result["continuation_permitted"])
        self.assertEqual(result["ready"], [])
        self.assertEqual(result["nodes"]["a"]["state"], "HALTED")

    def test_invalid_graph_conflicting_owners_and_non_file_receipts_are_rejected(self):
        """Reject missing nodes, cycles, file-owner conflicts and unsupported acceptances."""
        missing = node("a", dependencies=("missing",))
        cycle_a, cycle_b = node("a", dependencies=("b",)), node("b", dependencies=("a",))
        owner_a, owner_b = node("a"), node("b")
        owner_a["file_owners"]["shared"] = "first"
        owner_b["file_owners"]["shared"] = "second"
        receipt = node("a")
        receipt["acceptance"] = {"agent_says_pass": True}
        for nodes in ([missing], [cycle_a, cycle_b], [owner_a, owner_b], [receipt]):
            with self.subTest(nodes=nodes), self.assertRaises(ValueError):
                continuity.evaluate(self.project, {"nodes": nodes})

    def test_generated_input_must_have_an_ordered_producer(self):
        """Avoid scheduling a consumer alongside an unrelated producer of its input."""
        producer, consumer = node("a"), node("b", inputs=("a.out",))
        with self.assertRaisesRegex(ValueError, "not ordered by dependencies"):
            continuity.evaluate(self.project, {"nodes": [producer, consumer]})
        consumer["depends_on"] = ["a"]
        result = continuity.evaluate(self.project, {"nodes": [consumer, producer]})
        self.assertEqual(result["ready"], ["a"])
        consumer["depends_on"] = []
        producer["depends_on"] = ["b"]
        with self.assertRaisesRegex(ValueError, "not ordered by dependencies"):
            continuity.evaluate(self.project, {"nodes": [consumer, producer]})

    def test_traversal_absolute_stream_and_hardlinks_are_rejected(self):
        """Reject out-of-scope paths, Windows streams and linked fixture files."""
        for bad in ("../outside", "/absolute", "C:/outside", "name:stream", "folder/../file"):
            invalid = node("a")
            invalid["inputs"] = [bad]
            with self.subTest(path=bad), self.assertRaises(ValueError):
                continuity.evaluate(self.project, {"nodes": [invalid]})
        self.write("original.txt", b"owned")
        (self.project / "linked.txt").hardlink_to(self.project / "original.txt")
        with self.assertRaisesRegex(ValueError, "single-linked"):
            continuity.evaluate(self.project, {"nodes": [node("a", inputs=("linked.txt",))]})

if __name__ == "__main__":
    unittest.main(verbosity=2)
