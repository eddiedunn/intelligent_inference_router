import sqlite3
from contextlib import contextmanager
from pathlib import Path
import threading

DB_PATH = Path(__file__).parent.parent / "persistent-data" / "api_keys.sqlite3"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    created_ip TEXT,
    description TEXT,
    priority INTEGER DEFAULT 0,
    active BOOLEAN DEFAULT 1,
    revoked_at TIMESTAMP,
    is_superadmin BOOLEAN DEFAULT 0
);
"""

_db_lock = threading.Lock()

def init_db():
    with _db_lock, sqlite3.connect(DB_PATH) as conn:
        conn.execute(CREATE_TABLE_SQL)
        conn.commit()

@contextmanager
def get_db():
    with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        try:
            yield conn
        finally:
            conn.close()

def add_api_key(key, created_ip, description=None, priority=0, is_superadmin=False):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO api_keys (key, created_ip, description, priority, is_superadmin) VALUES (?, ?, ?, ?, ?)",
            (key, created_ip, description, priority, int(is_superadmin))
        )
        conn.commit()

def get_api_key(key):
    with get_db() as conn:
        cur = conn.execute("SELECT * FROM api_keys WHERE key = ? AND active = 1", (key,))
        return cur.fetchone()

def revoke_api_key(key):
    with get_db() as conn:
        conn.execute("UPDATE api_keys SET active = 0, revoked_at = CURRENT_TIMESTAMP WHERE key = ?", (key,))
        conn.commit()

def list_api_keys():
    with get_db() as conn:
        cur = conn.execute("SELECT * FROM api_keys")
        return cur.fetchall()

# Call on startup
init_db()
