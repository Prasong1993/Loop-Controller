import tempfile
import unittest
from pathlib import Path
from nexus.idempotency import IdempotencyStore, IdempotencyConflict, IdempotencyInProgress

class IdempotencyStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store=IdempotencyStore(str(Path(self.tmp.name)/"idempotency.db"))

    def test_completed_operation_returns_persisted_response_without_reexecution(self):
        key="execute-once"
        self.assertEqual(self.store.claim(key,scope="task:t1",fingerprint="f1")["status"],"IN_PROGRESS")
        self.store.complete(key,{"state":"EXECUTE","task_id":"t1"})
        replay=self.store.claim(key,scope="task:t1",fingerprint="f1")
        self.assertEqual(replay,{"status":"COMPLETED","response":{"state":"EXECUTE","task_id":"t1"}})

    def test_same_key_with_different_request_is_rejected(self):
        self.store.claim("key",scope="task:t1",fingerprint="first")
        with self.assertRaises(IdempotencyConflict):
            self.store.claim("key",scope="task:t1",fingerprint="different")

    def test_crash_or_timeout_leaves_uncertain_key_that_cannot_replay(self):
        self.store.claim("crashed",scope="task:t1",fingerprint="f1")
        reopened=IdempotencyStore(self.store.database)
        with self.assertRaises(IdempotencyInProgress):
            reopened.claim("crashed",scope="task:t1",fingerprint="f1")
        reopened.mark_uncertain("crashed","TimeoutError")
        with self.assertRaises(IdempotencyInProgress):
            reopened.claim("crashed",scope="task:t1",fingerprint="f1")

    def test_concurrent_duplicate_cannot_claim_existing_operation(self):
        self.store.claim("single",scope="task:t1",fingerprint="f1")
        with self.assertRaises(IdempotencyInProgress):
            self.store.claim("single",scope="task:t1",fingerprint="f1")

if __name__=="__main__":
    unittest.main()
