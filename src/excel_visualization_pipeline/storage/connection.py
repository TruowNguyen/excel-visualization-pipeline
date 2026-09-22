from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def connect_database(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(
        path,
        timeout=5.0,
        isolation_level=None,
        factory=ClosingConnection,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def backup_database(db_path: str | Path, backup_path: str | Path) -> Path:
    source_path = Path(db_path)
    target_path = Path(backup_path)
    if not source_path.is_file():
        raise FileNotFoundError(f"Không tìm thấy SQLite database: {source_path}")
    if source_path.resolve() == target_path.resolve():
        raise ValueError("Đường dẫn backup phải khác database nguồn.")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with connect_database(source_path) as source:
        with closing(sqlite3.connect(target_path)) as target:
            source.backup(target)
    with closing(sqlite3.connect(target_path)) as restored:
        result = restored.execute("PRAGMA integrity_check").fetchone()[0]
    if result != "ok":
        target_path.unlink(missing_ok=True)
        raise RuntimeError(f"Backup integrity check thất bại: {result}")
    return target_path


def verify_database(db_path: str | Path) -> dict[str, object]:
    if not Path(db_path).is_file():
        raise FileNotFoundError(f"Không tìm thấy SQLite database: {db_path}")
    with connect_database(db_path) as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = [dict(row) for row in connection.execute("PRAGMA foreign_key_check")]
        migration_count = connection.execute(
            "SELECT COUNT(*) FROM schema_migrations"
        ).fetchone()[0]
        latest_run_id = connection.execute(
            "SELECT MAX(run_id) FROM import_runs WHERE status = 'committed'"
        ).fetchone()[0]
    return {
        "integrity_check": integrity,
        "foreign_key_issues": foreign_keys,
        "migration_count": migration_count,
        "latest_committed_run_id": latest_run_id,
        "is_valid": integrity == "ok" and not foreign_keys,
    }
