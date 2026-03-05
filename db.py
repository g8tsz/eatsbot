"""SQLite persistence for card and email pools."""
import os
import sqlite3
from pathlib import Path
from queue import SimpleQueue, Empty
from typing import Optional, Tuple

DB_PATH = Path(os.getenv("DB_PATH", str(Path(__file__).parent / "data" / "pool.db")))
DB_CONN = None
_POOL_SIZE = 3
_POOL: SimpleQueue = SimpleQueue()

VALID_EMAIL_POOLS = ["main", "pump_20off25", "pump_25off"]
DEFAULT_EMAIL_POOL = "main"


def init_db():
    """Create data dir and tables if missing."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        try:
            with DB_PATH.open("rb") as f:
                header = f.read(16)
            if not header.startswith(b"SQLite format 3\x00"):
                DB_PATH.unlink()
        except Exception:
            try:
                DB_PATH.unlink()
            except Exception:
                pass

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number TEXT NOT NULL,
            cvv TEXT NOT NULL
        )
    """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            pool_type TEXT NOT NULL DEFAULT 'main'
        )
    """
    )
    try:
        cur.execute("SELECT pool_type FROM emails LIMIT 1")
    except sqlite3.OperationalError:
        cur.execute("ALTER TABLE emails ADD COLUMN pool_type TEXT NOT NULL DEFAULT 'main'")
        cur.execute("UPDATE emails SET pool_type = 'main' WHERE pool_type IS NULL OR pool_type = ''")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS payment_settings (
            method TEXT PRIMARY KEY,
            enabled INTEGER NOT NULL DEFAULT 1
        )
    """
    )
    for method in ["zelle", "venmo", "paypal", "cashapp", "crypto"]:
        cur.execute("INSERT OR IGNORE INTO payment_settings (method, enabled) VALUES (?, 1)", (method,))
    conn.commit()
    conn.close()


def _init_pool(size: int = _POOL_SIZE):
    for _ in range(size):
        _POOL.put(sqlite3.connect(DB_PATH, check_same_thread=False))


def get_connection():
    return DB_CONN


def acquire_connection() -> sqlite3.Connection:
    try:
        return _POOL.get_nowait()
    except Empty:
        return DB_CONN


def release_connection(conn: sqlite3.Connection) -> None:
    if conn is DB_CONN:
        return
    _POOL.put(conn)


def close_connection():
    global DB_CONN
    if DB_CONN is not None:
        DB_CONN.close()
        DB_CONN = None
    while True:
        try:
            conn = _POOL.get_nowait()
        except Empty:
            break
        else:
            conn.close()


def get_and_remove_email(pool_type: str = DEFAULT_EMAIL_POOL, fallback_to_main: bool = False) -> Optional[str]:
    if pool_type not in VALID_EMAIL_POOLS:
        raise ValueError(f"Invalid pool type: {pool_type}. Valid: {VALID_EMAIL_POOLS}")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, email FROM emails WHERE pool_type = ? ORDER BY id LIMIT 1", (pool_type,))
    row = cur.fetchone()
    if not row and fallback_to_main and pool_type != "main":
        cur.execute("SELECT id, email FROM emails WHERE pool_type = ? ORDER BY id LIMIT 1", ("main",))
        row = cur.fetchone()
    if not row:
        return None
    email_id, email = row
    cur.execute("DELETE FROM emails WHERE id = ?", (email_id,))
    conn.commit()
    return email


def add_email_to_pool(email: str, pool_type: str = DEFAULT_EMAIL_POOL, top: bool = False) -> bool:
    if pool_type not in VALID_EMAIL_POOLS:
        raise ValueError(f"Invalid pool type: {pool_type}. Valid: {VALID_EMAIL_POOLS}")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM emails WHERE email = ? AND pool_type = ?", (email, pool_type))
    if cur.fetchone()[0] > 0:
        return False
    if top:
        cur.execute("SELECT MIN(id) FROM emails WHERE pool_type = ?", (pool_type,))
        row = cur.fetchone()
        min_id = row[0] if row and row[0] is not None else None
        if min_id is None:
            cur.execute("INSERT INTO emails (email, pool_type) VALUES (?, ?)", (email, pool_type))
        else:
            cur.execute(
                "INSERT INTO emails (id, email, pool_type) VALUES (?, ?, ?)",
                (min_id - 1, email, pool_type),
            )
    else:
        cur.execute("INSERT INTO emails (email, pool_type) VALUES (?, ?)", (email, pool_type))
    conn.commit()
    return True


def remove_email_from_pool(email: str, pool_type: str = DEFAULT_EMAIL_POOL) -> bool:
    if pool_type not in VALID_EMAIL_POOLS:
        raise ValueError(f"Invalid pool type: {pool_type}. Valid: {VALID_EMAIL_POOLS}")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM emails WHERE email = ? AND pool_type = ?", (email, pool_type))
    deleted = cur.rowcount
    conn.commit()
    return deleted > 0


def get_emails_in_pool(pool_type: str = DEFAULT_EMAIL_POOL) -> list:
    if pool_type not in VALID_EMAIL_POOLS:
        raise ValueError(f"Invalid pool type: {pool_type}. Valid: {VALID_EMAIL_POOLS}")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT email FROM emails WHERE pool_type = ? ORDER BY id", (pool_type,))
    return [row[0] for row in cur.fetchall()]


def get_all_emails_with_pools():
    """Return list of (email, pool_type) for all emails."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT email, pool_type FROM emails ORDER BY pool_type, id")
    return cur.fetchall()


def get_pool_counts() -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM cards")
    card_count = cur.fetchone()[0]
    email_counts = {}
    for pt in VALID_EMAIL_POOLS:
        cur.execute("SELECT COUNT(*) FROM emails WHERE pool_type = ?", (pt,))
        email_counts[pt] = cur.fetchone()[0]
    return {"cards": card_count, "emails": email_counts}


def get_and_remove_card() -> Optional[Tuple[str, str]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, number, cvv FROM cards ORDER BY id LIMIT 1")
    row = cur.fetchone()
    if not row:
        return None
    card_id, number, cvv = row
    cur.execute("DELETE FROM cards WHERE id = ?", (card_id,))
    conn.commit()
    return number, cvv


def get_payment_setting(method: str) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT enabled FROM payment_settings WHERE method = ?", (method.lower(),))
    row = cur.fetchone()
    return bool(row[0]) if row else True


def set_payment_setting(method: str, enabled: bool) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO payment_settings (method, enabled) VALUES (?, ?)",
        (method.lower(), 1 if enabled else 0),
    )
    conn.commit()


def get_all_payment_settings() -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT method, enabled FROM payment_settings")
    return {m: bool(e) for m, e in cur.fetchall()}


init_db()
DB_CONN = sqlite3.connect(DB_PATH, check_same_thread=False)
_init_pool()
