"""SQLite connections and schema migrations."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from mortgage_advisor.core.config import MIGRATIONS_DIR


@contextmanager
def connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    """Open a connection with dict-like rows; commit on success, always close."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def apply_migrations(conn: sqlite3.Connection, migrations_dir: Path = MIGRATIONS_DIR) -> list[str]:
    """Run every `*.sql` file in filename order. Scripts must be idempotent
    (`CREATE ... IF NOT EXISTS`). Returns the names of the files applied."""
    files = sorted(migrations_dir.glob("*.sql"))
    if not files:
        raise FileNotFoundError(f"No migrations found in {migrations_dir}")
    for f in files:
        conn.executescript(f.read_text(encoding="utf-8"))
    return [f.name for f in files]
