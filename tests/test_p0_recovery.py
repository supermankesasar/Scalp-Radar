import contextlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import p0_recovery as recovery


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "live.sqlite3"
        self.writer = sqlite3.connect(self.source)
        self.addCleanup(self.writer.close)
        self.writer.execute("PRAGMA journal_mode=WAL")
        self.writer.execute("CREATE TABLE events(id INTEGER PRIMARY KEY)")
        self.writer.execute("CREATE TABLE market_observations(id INTEGER PRIMARY KEY)")
        self.writer.execute("INSERT INTO events VALUES (1)")
        self.writer.execute("INSERT INTO market_observations VALUES (1)")
        self.writer.commit()
        self.parent = self.root / "backups"
        self.patches = [
            patch.object(recovery, "git_identity", return_value={"checkoutSHA": "fixture"}),
            patch.object(recovery, "config_path", return_value=self.root / "missing.json"),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def test_wal_and_non_overwriting_restore(self):
        point = recovery.backup(self.source, self.parent)
        manifest = recovery.verify(point)
        self.assertEqual(manifest["databaseMetadata"]["criticalCounts"]["events"], 1)
        self.assertFalse(manifest["knownGood"])
        self.writer.execute("INSERT INTO events VALUES (2)")
        self.writer.commit()
        restored = recovery.restore_copy(point, self.root / "restores")
        with contextlib.closing(sqlite3.connect(restored)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM events").fetchone()[0], 1)
        self.assertEqual(self.writer.execute("SELECT COUNT(*) FROM events").fetchone()[0], 2)
        self.assertNotEqual(restored, self.source)
        self.assertNotEqual(restored, recovery.restore_copy(point, self.root / "restores"))

    def test_multiple_points_and_corrupt_copy(self):
        first = recovery.backup(self.source, self.parent)
        second = recovery.backup(self.source, self.parent)
        self.assertNotEqual(first, second)
        with (first / "database.sqlite3").open("r+b") as f:
            f.write(b"broken")
        with self.assertRaises(RuntimeError):
            recovery.verify(first)
        recovery.verify(second)

    def test_bad_manifest_and_low_space(self):
        point = recovery.backup(self.source, self.parent)
        manifest = point / "manifest.json"
        data = json.loads(manifest.read_text())
        data["state"] = "PENDING"
        manifest.write_text(json.dumps(data))
        with self.assertRaises(RuntimeError):
            recovery.verify(point)
        with patch.object(recovery.shutil, "disk_usage", return_value=type("Usage", (), {"free": 0})()):
            with self.assertRaises(RuntimeError):
                recovery.backup(self.source, self.parent)
        self.assertEqual(len(list(self.parent.iterdir())), 1)

    def test_failed_snapshot_not_published(self):
        with patch.object(recovery, "snapshot", side_effect=sqlite3.DatabaseError("fixture")):
            with self.assertRaises(sqlite3.DatabaseError):
                recovery.backup(self.source, self.parent)
        self.assertEqual(list(self.parent.iterdir()), [])

    def test_wrong_database_and_checkout_destination(self):
        wrong = self.root / "wrong.sqlite3"
        with contextlib.closing(sqlite3.connect(wrong)) as conn:
            conn.execute("CREATE TABLE unrelated(id)")
        with self.assertRaises(RuntimeError):
            recovery.backup(wrong, self.parent)
        with self.assertRaises(RuntimeError):
            recovery.backup(self.source, recovery.ROOT / "backup")


if __name__ == "__main__":
    unittest.main()
