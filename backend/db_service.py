import sqlite3, os, logging
from datetime import datetime

logger = logging.getLogger(__name__)
DB_PATH = os.environ.get("DB_PATH", "weather_outfit.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_name TEXT UNIQUE NOT NULL,
                key_value TEXT NOT NULL,
                updated TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS outfit_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT, temperature REAL, condition TEXT,
                outfit_name TEXT, occasion TEXT, gender TEXT,
                created_at TEXT NOT NULL
            );
        """)
        now = datetime.utcnow().isoformat()
        defaults = [
            ("OWM_API_KEY", "568d4f6a784fd23816ccfad2e96eb4a1"),
            ("FRIEND_API_URL", "https://c730261bf2bc4236bcd5fd5f1d1c84bc.vfs.cloud9.us-east-1.amazonaws.com"),
            ("FRIEND_API_KEY", "pollhub-secret-key-2024"),
        ]
        for k, v in defaults:
            conn.execute("INSERT OR IGNORE INTO api_keys (key_name, key_value, updated) VALUES (?,?,?)", (k,v,now))
        conn.commit()
        logger.info("DB initialised at %s", DB_PATH)
    finally:
        conn.close()

def get_api_key(key_name):
    conn = get_db()
    try:
        row = conn.execute("SELECT key_value FROM api_keys WHERE key_name=?", (key_name,)).fetchone()
        return row["key_value"] if row else None
    finally:
        conn.close()

def set_api_key(key_name, key_value):
    conn = get_db()
    try:
        conn.execute("INSERT INTO api_keys (key_name,key_value,updated) VALUES (?,?,?) ON CONFLICT(key_name) DO UPDATE SET key_value=excluded.key_value,updated=excluded.updated",
            (key_name, key_value, datetime.utcnow().isoformat()))
        conn.commit()
    finally:
        conn.close()

def get_all_keys():
    conn = get_db()
    try:
        rows = conn.execute("SELECT key_name, key_value FROM api_keys").fetchall()
        return {r["key_name"]: r["key_value"] for r in rows}
    finally:
        conn.close()

def save_outfit_history(city, temperature, condition, outfit_name, occasion, gender):
    conn = get_db()
    try:
        conn.execute("INSERT INTO outfit_history (city,temperature,condition,outfit_name,occasion,gender,created_at) VALUES (?,?,?,?,?,?,?)",
            (city, temperature, condition, outfit_name, occasion, gender, datetime.utcnow().isoformat()))
        conn.commit()
    finally:
        conn.close()

def get_outfit_history(limit=10):
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM outfit_history ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
