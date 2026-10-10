import tempfile
import unittest
from pathlib import Path
from nexus.records import RecordStore

class RecordStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = RecordStore(str(Path(self.tmp.name) / "records.db"))

    def test_append_and_search_by_trace_and_error(self):
        rec = self.store.append(project_id="p1", record_type="error",
            payload={"category":"validation", "message_redacted":"missing field"},
            trace_id="trace-1", error_code="NXR-E100", severity="medium",
            status="BLOCKED", component="api", summary="validation failed")
        result = self.store.search(project_id="p1", trace_id="trace-1", error_code="NXR-E100")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["records"][0]["record_id"], rec["record_id"])
        self.assertEqual(result["records"][0]["payload"]["category"], "validation")

    def test_search_pagination_and_time_order(self):
        self.store.append(project_id="p1", record_type="usage", payload={"operation":"read"},
                          operation_id="op-1", summary="read task")
        self.store.append(project_id="p1", record_type="usage", payload={"operation":"write"},
                          operation_id="op-2", summary="write task")
        result = self.store.search(project_id="p1", limit=1)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["total"], 2)
        self.assertIsNotNone(result["next_offset"])

    def test_rejects_secret_fields(self):
        with self.assertRaises(ValueError):
            self.store.append(project_id="p1", record_type="usage",
                payload={"request":{"authorization":"Bearer secret"}})

    def test_rejects_invalid_type_and_unbounded_page(self):
        with self.assertRaises(ValueError):
            self.store.append(project_id="p1", record_type="arbitrary", payload={})
        with self.assertRaises(ValueError):
            self.store.search(project_id="p1", limit=1000)

    def test_project_scoped_search(self):
        self.store.append(project_id="p1", record_type="usage", payload={"operation":"a"})
        self.store.append(project_id="p2", record_type="usage", payload={"operation":"b"})
        self.assertEqual(self.store.search(project_id="p1")["total"], 1)

if __name__ == "__main__":
    unittest.main()
