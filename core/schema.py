"""
Defines the SQLite schema and a connection helper.
This file is shared across ALL clients/adapters -- it only knows about
the common internal schema, never about WordPress/Blogspot/etc specifically.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "pipeline.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    post_id INTEGER PRIMARY KEY,
    url TEXT NOT NULL,
    title TEXT,
    subheadings TEXT,              -- h2-h6 text, joined into one field
    body TEXT,
    meta_description TEXT,
    category TEXT,
    gsc_position REAL,
    top_keywords TEXT,

    -- AI-rewritten versions, filled in during the 'rewrite' step
    new_title TEXT,
    new_subheadings TEXT,
    new_body TEXT,
    new_meta_description TEXT,

    -- pipeline tracking
    status TEXT DEFAULT 'fetched', -- fetched -> rewritten -> reviewed -> published -> failed
    fetched_at TEXT,
    updated_at TEXT
);
"""


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets you access columns by name, e.g. row["title"]
    return conn


def init_db():
    conn = get_connection()
    conn.execute(SCHEMA)
    conn.commit()
    conn.close()
    print(f"Database ready at {DB_PATH}")


if __name__ == "__main__":
    # Run this file directly (`python core/schema.py`) to just create the DB
    # without fetching anything -- useful for a quick sanity check.
    init_db()
