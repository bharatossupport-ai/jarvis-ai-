"""SQLite storage: one file, thread-safe connection per call."""
import sqlite3
import threading
from contextlib import contextmanager
from .paths import data_dir

DB_PATH = data_dir() / "jarvis.db"
_lock = threading.RLock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations(
  id INTEGER PRIMARY KEY, title TEXT, companion TEXT, project_id INTEGER,
  created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS messages(
  id INTEGER PRIMARY KEY, conversation_id INTEGER, role TEXT, companion TEXT,
  model TEXT, content TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS memories(
  id INTEGER PRIMARY KEY, category TEXT, scope TEXT, content TEXT,
  approved INTEGER DEFAULT 0, created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS projects(
  id INTEGER PRIMARY KEY, name TEXT UNIQUE, notes TEXT,
  created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS documents(
  id INTEGER PRIMARY KEY, path TEXT, title TEXT, content TEXT,
  created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS tasks(
  id INTEGER PRIMARY KEY, title TEXT, status TEXT, companion TEXT, result TEXT,
  created TEXT DEFAULT CURRENT_TIMESTAMP, updated TEXT);
CREATE TABLE IF NOT EXISTS approvals(
  id INTEGER PRIMARY KEY, tool TEXT, args TEXT, risk TEXT, decision TEXT,
  created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS audit(
  id INTEGER PRIMARY KEY, kind TEXT, detail TEXT,
  created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS workflows(
  id INTEGER PRIMARY KEY, name TEXT, prompt TEXT, trigger TEXT, spec TEXT,
  companion TEXT, enabled INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS workflow_runs(
  id INTEGER PRIMARY KEY, workflow_id INTEGER, status TEXT, output TEXT,
  created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(kind, ref, text);
"""


def _connect():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@contextmanager
def db():
    with _lock:
        conn = _connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def init():
    with db() as c:
        try:
            c.executescript(SCHEMA)
        except sqlite3.OperationalError:
            # SQLite without FTS5: fall back to a plain table + LIKE search
            c.executescript(SCHEMA.replace(
                "CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(kind, ref, text);",
                "CREATE TABLE IF NOT EXISTS search_index(kind TEXT, ref TEXT, text TEXT);"))


def audit(kind: str, detail: str):
    with db() as c:
        c.execute("INSERT INTO audit(kind, detail) VALUES(?,?)", (kind, detail))
