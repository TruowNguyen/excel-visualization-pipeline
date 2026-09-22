from __future__ import annotations

from pathlib import Path

from .connection import connect_database, utc_now


MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def initialize_database(db_path: str | Path) -> None:
    with connect_database(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )
            """
        )
        applied = {
            row["version"] for row in connection.execute("SELECT version FROM schema_migrations")
        }
        for migration_path in sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql")):
            version = int(migration_path.name.split("_", 1)[0])
            if version in applied:
                continue
            sql = migration_path.read_text(encoding="utf-8")
            safe_name = migration_path.name.replace("'", "''")
            applied_at = utc_now().replace("'", "''")
            script = (
                "BEGIN IMMEDIATE;\n"
                f"{sql}\n"
                "INSERT INTO schema_migrations(version, name, applied_at) "
                f"VALUES ({version}, '{safe_name}', '{applied_at}');\n"
                "COMMIT;"
            )
            try:
                connection.executescript(script)
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

        foreign_key_issues = list(connection.execute("PRAGMA foreign_key_check"))
        if foreign_key_issues:
            raise RuntimeError(f"Foreign key check thất bại sau migration: {foreign_key_issues}")
