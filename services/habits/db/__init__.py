
import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row             
    conn.execute("PRAGMA foreign_keys = ON")   
    return conn


def init_schema(conn):
    """Creates the tables unless they already exist."""
    has_tables = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'users'"
    ).fetchone()
    if not has_tables:
        conn.executescript(SCHEMA_PATH.read_text())
