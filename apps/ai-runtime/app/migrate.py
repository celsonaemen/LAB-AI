"""Apply immutable, checksummed SQL migrations under an advisory transaction lock."""
import hashlib
import os
from pathlib import Path

from app.rag.store import _connect


def migrate(directory: Path | None = None) -> list[str]:
    directory = directory or Path(os.getenv("MIGRATIONS_DIR", "infrastructure/database/migrations"))
    scripts = sorted(directory.glob("V*__*.sql"))
    if not scripts:
        raise RuntimeError("No versioned database migrations found")
    applied = []
    with _connect() as connection:
        connection.execute("SELECT pg_advisory_xact_lock(72627491)")
        connection.execute("CREATE SCHEMA IF NOT EXISTS knowledge")
        connection.execute("CREATE TABLE IF NOT EXISTS knowledge.schema_migrations "
                           "(version text PRIMARY KEY, checksum char(64) NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())")
        for script in scripts:
            sql = script.read_text(encoding="utf-8")
            checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()
            row = connection.execute("SELECT checksum FROM knowledge.schema_migrations WHERE version=%s", (script.name,)).fetchone()
            if row:
                if row["checksum"] != checksum:
                    raise RuntimeError(f"Applied migration checksum changed: {script.name}")
                continue
            connection.execute(sql)
            connection.execute("INSERT INTO knowledge.schema_migrations (version,checksum) VALUES (%s,%s)", (script.name, checksum))
            applied.append(script.name)
    return applied


if __name__ == "__main__":
    print({"applied_migrations": migrate()})
