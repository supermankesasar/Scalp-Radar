"""P0 offline recovery points. Never changes the selected production database.

Run only after stopping ALL scanner/launcher processes. The legacy direct
launcher does not share the auto-launch lock; port/lock checks are additional
guards, not proof of quiescence. No recovery point is automatically an LKG.
"""
import argparse
import contextlib
import datetime as dt
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import uuid

from database_location import app_home, config_path, existing_database

ROOT = Path(__file__).resolve().parent
CRITICAL = ("events", "research_snapshots", "research_candidates",
            "research_outcomes", "market_observations", "r11_events",
            "r111_events", "r112_events")
FORMAT = 1
RESERVE = 64 * 1024 * 1024


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def ro(path):
    return sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro",
                           uri=True, timeout=10)


def metadata(db, integrity=False):
    if integrity:
        for pragma in ("quick_check", "integrity_check"):
            if db.execute("PRAGMA " + pragma).fetchall() != [("ok",)]:
                raise RuntimeError("SQLite " + pragma + " failed")
    schema = db.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name"
    ).fetchall()
    tables = {row[1] for row in schema if row[0] == "table"}
    if "events" not in tables or "market_observations" not in tables:
        raise RuntimeError("Not a recognized Scalp Radar archive (critical tables missing)")
    counts = {t: db.execute('SELECT COUNT(*) FROM "' + t + '"').fetchone()[0]
              for t in CRITICAL if t in tables}
    return {"userVersion": db.execute("PRAGMA user_version").fetchone()[0],
            "schemaSHA256": hashlib.sha256(json.dumps(schema, ensure_ascii=False,
                separators=(",", ":")).encode("utf-8")).hexdigest(),
            "criticalCounts": counts}


def fsync_file(path):
    with Path(path).open("rb+") as f:
        f.flush()
        os.fsync(f.fileno())


def ensure_space(source, parent):
    needed = source.stat().st_size
    wal = source.with_name(source.name + "-wal")
    if wal.is_file():
        needed += wal.stat().st_size
    if shutil.disk_usage(parent).free < needed + RESERVE:
        raise RuntimeError("Insufficient disk space for verified recovery copy")


def snapshot(source, target):
    """Use SQLite backup API, not a filesystem copy of a potentially WAL DB."""
    with contextlib.closing(ro(source)) as src:
        src.execute("BEGIN")
        expected = metadata(src)
        with contextlib.closing(sqlite3.connect(target, timeout=10)) as dst:
            src.backup(dst, pages=512, sleep=.1)
            if metadata(dst, integrity=True) != expected:
                raise RuntimeError("Backup schema/count mismatch")
            # Publish a self-contained database rather than a WAL bundle.
            if dst.execute("PRAGMA journal_mode=DELETE").fetchone()[0] != "delete":
                raise RuntimeError("Could not finalize standalone backup")
    with contextlib.closing(ro(target)) as check:
        if metadata(check, integrity=True) != expected:
            raise RuntimeError("Reopened backup mismatch")
    fsync_file(target)
    return expected


def git_identity():
    def git(*args):
        return subprocess.check_output(["git", "-C", str(ROOT), *args],
                                      text=True, timeout=15).strip()
    try:
        sha = git("rev-parse", "HEAD")
        dirty = bool(git("status", "--porcelain", "--untracked-files=no"))
    except (OSError, subprocess.SubprocessError):
        sha, dirty = None, None
    try:
        ws = importlib.metadata.version("websockets")
    except importlib.metadata.PackageNotFoundError:
        ws = None
    return {"checkoutSHA": sha, "trackedDirty": dirty,
            "python": sys.version, "websockets": ws,
            "requirementsSHA256": digest(ROOT / "requirements.txt")}


def outside_checkout(path):
    path = Path(path).resolve()
    if path == ROOT or ROOT in path.parents:
        raise RuntimeError("Recovery copies must be outside the application checkout")
    return path


def verify(point):
    point = Path(point).resolve()
    manifest = json.loads((point / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("format") != FORMAT or manifest.get("state") != "VERIFIED":
        raise RuntimeError("Unknown or incomplete recovery manifest")
    db = point / "database.sqlite3"
    if not db.is_file() or db.stat().st_size != manifest["bytes"]:
        raise RuntimeError("Recovery database missing or size mismatch")
    if any(db.with_name(db.name + suffix).exists() for suffix in ("-wal", "-shm", "-journal")):
        raise RuntimeError("Recovery database has unexpected sidecars")
    if digest(db) != manifest["sha256"]:
        raise RuntimeError("Recovery database checksum mismatch")
    with contextlib.closing(ro(db)) as conn:
        if metadata(conn, integrity=True) != manifest["databaseMetadata"]:
            raise RuntimeError("Recovery database metadata mismatch")
    return manifest


def backup(source, parent):
    source = Path(source).resolve()
    parent = outside_checkout(parent)
    if not source.is_file():
        raise RuntimeError("Source database missing")
    parent.mkdir(parents=True, exist_ok=True)
    ensure_space(source, parent)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = "recovery-" + stamp + "-" + uuid.uuid4().hex
    dest = parent / name
    staging = Path(tempfile.mkdtemp(prefix=".incomplete-", dir=parent))
    try:
        target = staging / "database.sqlite3"
        info = snapshot(source, target)
        manifest = {"format": FORMAT, "state": "VERIFIED",
                    "createdUTC": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "source": str(source), "bytes": target.stat().st_size,
                    "sha256": digest(target), "databaseMetadata": info,
                    "codeIdentity": git_identity(), "knownGood": False}
        cfg = config_path()
        if cfg.is_file():
            shutil.copy2(cfg, staging / "database-location.json")
        for name in ("r10-heartbeat.json", "r10-runtime.jsonl"):
            p = source.parent / name
            if p.is_file():
                shutil.copy2(p, staging / name)
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2),
                                               encoding="utf-8")
        fsync_file(staging / "manifest.json")
        verify(staging)
        if dest.exists():
            raise RuntimeError("Recovery point collision")
        staging.rename(dest)
        return dest
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def restore_copy(point, parent):
    """Restore ONLY to a fresh directory; never select or overwrite production."""
    manifest = verify(point)
    src = Path(point).resolve() / "database.sqlite3"
    parent = outside_checkout(parent)
    parent.mkdir(parents=True, exist_ok=True)
    ensure_space(src, parent)
    dest = parent / ("restored-" + uuid.uuid4().hex)
    dest.mkdir(exist_ok=False)
    try:
        target = dest / "signals.sqlite3"
        if snapshot(src, target) != manifest["databaseMetadata"]:
            raise RuntimeError("Restore metadata mismatch")
        return target
    except BaseException:
        shutil.rmtree(dest)
        raise


def port_active():
    with socket.socket() as sock:
        sock.settimeout(.5)
        return sock.connect_ex(("127.0.0.1", 8765)) == 0


@contextlib.contextmanager
def offline_guard():
    if os.name != "nt":
        raise RuntimeError("Interactive recovery CLI is for Windows; core functions are portable")
    import msvcrt
    home = app_home()
    home.mkdir(parents=True, exist_ok=True)
    with (home / "auto-launch.lock").open("a+b") as lock:
        lock.seek(0, 2)
        if not lock.tell():
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            raise RuntimeError("Stop START-AUTO completely first") from exc
        try:
            if port_active():
                raise RuntimeError("Stop scanner first")
            yield
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("backup")
    b.add_argument("--parent", type=Path)
    v = sub.add_parser("verify")
    v.add_argument("point", type=Path)
    r = sub.add_parser("restore-copy")
    r.add_argument("point", type=Path)
    r.add_argument("--parent", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "verify":
        print(json.dumps(verify(args.point), indent=2))
        return
    print("Stop ALL scanners and launchers; do not start them during recovery.")
    if input("Type STOPPED to confirm: ").strip() != "STOPPED":
        raise RuntimeError("Cancelled")
    with offline_guard():
        if args.command == "backup":
            source = existing_database(ROOT)
            print("Source:", source, flush=True)
            parent = args.parent or source.parent.parent / "recovery"
            print("Verified recovery point:", backup(source, parent), flush=True)
        else:
            print("Restored independent copy:", restore_copy(args.point, args.parent))
            print("Production DB and location unchanged. Do not launch until schema compatibility is verified.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, sqlite3.Error, ValueError, KeyError) as exc:
        print("Recovery stopped:", exc, file=sys.stderr)
        sys.exit(1)
