"""SQLite 스키마 생성 및 upsert 헬퍼."""
import sqlite3
import sys
from pathlib import Path

# Windows 콘솔(cp949)에서 이모지/특수기호 출력 시 UnicodeEncodeError 방지
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "shipping.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS indicators (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    unit TEXT,
    source TEXT NOT NULL,
    region TEXT,
    source_url TEXT
);

CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY,
    indicator_id INTEGER NOT NULL REFERENCES indicators(id),
    date TEXT NOT NULL,
    value REAL NOT NULL,
    UNIQUE(indicator_id, date)
);
"""


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn=None):
    own = conn is None
    conn = conn or get_connection()
    conn.executescript(SCHEMA)
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(indicators)")}
    if "source_url" not in existing_cols:
        conn.execute("ALTER TABLE indicators ADD COLUMN source_url TEXT")
    conn.commit()
    if own:
        conn.close()


def upsert_indicator(conn, code, name, category, unit, source, region=None, source_url=None):
    conn.execute(
        """
        INSERT INTO indicators (code, name, category, unit, source, region, source_url)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(code) DO UPDATE SET
            name=excluded.name, category=excluded.category,
            unit=excluded.unit, source=excluded.source, region=excluded.region,
            source_url=excluded.source_url
        """,
        (code, name, category, unit, source, region, source_url),
    )
    conn.commit()
    row = conn.execute("SELECT id FROM indicators WHERE code = ?", (code,)).fetchone()
    return row[0]


def upsert_observations(conn, indicator_id, date_value_pairs):
    """date_value_pairs: iterable of (iso_date_str, float_value)"""
    conn.executemany(
        """
        INSERT INTO observations (indicator_id, date, value)
        VALUES (?, ?, ?)
        ON CONFLICT(indicator_id, date) DO UPDATE SET value=excluded.value
        """,
        [(indicator_id, d, v) for d, v in date_value_pairs],
    )
    conn.commit()


if __name__ == "__main__":
    init_db()
    print(f"DB initialized at {DB_PATH}")
