import os
import unittest
from unittest.mock import patch

from nexus.database import _HybridRow, _PostgresConnection, connect_database


class FakeCursor:
    def __init__(self, rows=()):
        self.rows = list(rows)

    def fetchone(self):
        return self.rows.pop(0) if self.rows else None

    def fetchall(self):
        rows, self.rows = self.rows, []
        return rows

    def __iter__(self):
        return iter(self.fetchall())


class FakeConnection:
    def __init__(self):
        self.calls = []
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def execute(self, sql, params=()):
        self.calls.append((sql, params))
        return FakeCursor()

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


class DatabaseAdapterTests(unittest.TestCase):
    def test_hybrid_row_supports_mapping_and_sqlite_positional_access(self):
        row = _HybridRow({"count": 7, "label": "records"})
        self.assertEqual(row["count"], 7)
        self.assertEqual(row[0], 7)
        self.assertEqual(row[1], "records")
        self.assertEqual(dict(row), {"count": 7, "label": "records"})

    def test_postgres_adapter_translates_placeholders(self):
        connection = FakeConnection()
        adapter = _PostgresConnection(connection)
        adapter.execute("SELECT * FROM tasks WHERE task_id=? AND state=?", ("t-1", "INTAKE"))
        self.assertEqual(connection.calls[-1], (
            "SELECT * FROM tasks WHERE task_id=%s AND state=%s", ("t-1", "INTAKE")
        ))

    def test_postgres_adapter_ignores_sqlite_pragma(self):
        connection = FakeConnection()
        adapter = _PostgresConnection(connection)
        cursor = adapter.execute("PRAGMA foreign_keys=ON")
        self.assertIsNone(cursor.fetchone())
        self.assertEqual(connection.calls, [])

    def test_invalid_nonempty_database_url_fails_closed(self):
        with patch.dict(os.environ, {"DATABASE_URL": "not-a-resolved-render-reference"}):
            with self.assertRaisesRegex(RuntimeError, "not a PostgreSQL connection URL"):
                connect_database("/tmp/should-not-be-created.db")

    def test_context_manager_commits_on_success_and_rolls_back_on_error(self):
        committed = FakeConnection()
        with _PostgresConnection(committed):
            pass
        self.assertTrue(committed.committed)
        self.assertTrue(committed.closed)

        rolled_back = FakeConnection()
        with self.assertRaisesRegex(RuntimeError, "test failure"):
            with _PostgresConnection(rolled_back):
                raise RuntimeError("test failure")
        self.assertTrue(rolled_back.rolled_back)
        self.assertTrue(rolled_back.closed)


if __name__ == "__main__":
    unittest.main()
