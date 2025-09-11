# db.py
# Asinxron SQLite helper + bot uchun barcha kerakli CRUD funksiyalar

from __future__ import annotations
import os
from typing import Any, Iterable, Optional, Tuple, List
from datetime import datetime, timezone
import aiosqlite

# Render yoki lokal: DB fayl yo'li ENV dan olinadi, bo'lmasa ./data/data.db
DB_PATH = os.getenv("DB_PATH", "data/data.db")
os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)

# ===================== Ulanish helperlari =====================
async def _connect() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DB_PATH)
    await db.execute("PRAGMA journal_mode=WAL;")
    await db.execute("PRAGMA synchronous=NORMAL;")
    await db.execute("PRAGMA foreign_keys=ON;")
    return db

async def _exec(sql: str, params: Iterable[Any] | None = None) -> None:
    db = await _connect()
    try:
        await db.execute(sql, tuple(params or ()))
        await db.commit()
    finally:
        await db.close()

async def _query(sql: str, params: Iterable[Any] | None = None) -> List[Tuple]:
    db = await _connect()
    try:
        cur = await db.execute(sql, tuple(params or ()))
        rows = await cur.fetchall()
        await cur.close()
        return rows
    finally:
        await db.close()

async def _query_one(sql: str, params: Iterable[Any] | None = None) -> Optional[Tuple]:
    db = await _connect()
    try:
        cur = await db.execute(sql, tuple(params or ()))
        row = await cur.fetchone()
        await cur.close()
        return row
    finally:
        await db.close()

async def _fetchall(sql: str, params: Iterable[Any] = ()) -> List[Tuple]:
    db = await _connect()
    try:
        cur = await db.execute(sql, tuple(params))
        rows = await cur.fetchall()
        await cur.close()
        return rows
    finally:
        await db.close()

async def _fetchone(sql: str, params: Iterable[Any] = ()) -> Optional[Tuple]:
    db = await _connect()
    try:
        cur = await db.execute(sql, tuple(params))
        row = await cur.fetchone()
        await cur.close()
        return row
    finally:
        await db.close()

async def _fetchval(sql: str, params: Iterable[Any] = ()) -> Any:
    row = await _fetchone(sql, params)
    return row[0] if row else None

# ===================== Dastlabki yaratish =====================
async def init_db():
    # users
    await _exec("""
    CREATE TABLE IF NOT EXISTS users (
        user_id     INTEGER PRIMARY KEY,
        first_name  TEXT,
        last_name   TEXT,
        username    TEXT,
        joined_at   TEXT
    )
    """)

    # channels
    await _exec("""
    CREATE TABLE IF NOT EXISTS channels (
        chat_id     TEXT PRIMARY KEY,
        title       TEXT,
        username    TEXT,
        invite_link TEXT,
        url         TEXT
    )
    """)

    # buttons
    await _exec("""
    CREATE TABLE IF NOT EXISTS buttons (
        id    INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        pos   INTEGER NOT NULL
    )
    """)

    # button_contents
    await _exec("""
    CREATE TABLE IF NOT EXISTS button_contents (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        button_id  INTEGER NOT NULL,
        media_type TEXT NOT NULL,       -- text/photo/video/document/audio/animation
        file_id    TEXT,                -- text bo'lsa NULL
        caption    TEXT,
        FOREIGN KEY(button_id) REFERENCES buttons(id)
    )
    """)

    # settings
    await _exec("""
    CREATE TABLE IF NOT EXISTS settings (
        key   TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    # admins
    await _exec("""
    CREATE TABLE IF NOT EXISTS admins (
        user_id  INTEGER PRIMARY KEY,
        name     TEXT,
        is_super INTEGER DEFAULT 0
    )
    """)

    # default: menu_cols
    if await _fetchval("SELECT value FROM settings WHERE key='menu_cols'") is None:
        await _exec("INSERT INTO settings(key, value) VALUES('menu_cols', '2')")

# ===================== Users =====================
async def upsert_user(u) -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    await _exec("""
    INSERT INTO users(user_id, first_name, last_name, username, joined_at)
    VALUES(?, ?, ?, ?, ?)
    ON CONFLICT(user_id) DO UPDATE SET
        first_name=excluded.first_name,
        last_name =excluded.last_name,
        username  =excluded.username
    """, (
        int(u.id), getattr(u, "first_name", None), getattr(u, "last_name", None),
        getattr(u, "username", None), now_iso
    ))

async def count_users_range(since_iso: Optional[str]) -> int:
    if not since_iso:
        v = await _fetchval("SELECT COUNT(*) FROM users")
    else:
        v = await _fetchval("SELECT COUNT(*) FROM users WHERE joined_at >= ?", (since_iso,))
    return int(v or 0)

async def fetch_all_users() -> List[Tuple]]:
    return await _fetchall("""
        SELECT user_id, first_name, last_name, username, joined_at
        FROM users
        ORDER BY joined_at DESC
    """)

# ===================== Channels =====================
async def save_channel(chat_id: str,
                       title: Optional[str],
                       username: Optional[str],
                       invite_link: Optional[str],
                       url: Optional[str]) -> None:
    await _exec("""
    INSERT INTO channels(chat_id, title, username, invite_link, url)
    VALUES(?, ?, ?, ?, ?)
    ON CONFLICT(chat_id) DO UPDATE SET
        title       = excluded.title,
        username    = excluded.username,
        invite_link = excluded.invite_link,
        url         = excluded.url
    """, (str(chat_id), title, username, invite_link, url))

async def remove_channel(chat_id: str) -> int:
    db = await _connect()
    try:
        cur = await db.execute("DELETE FROM channels WHERE chat_id=?", (str(chat_id),))
        await db.commit()
        return cur.rowcount or 0
    finally:
        await db.close()

async def list_channels_full() -> List[Tuple[str, Optional[str], Optional[str], Optional[str], Optional[str]]]:
    return await _fetchall("""
        SELECT chat_id, title, username, invite_link, url
        FROM channels
        ORDER BY ROWID ASC
    """)

async def list_channels() -> List[str]:
    rows = await _fetchall("SELECT chat_id FROM channels ORDER BY ROWID ASC")
    return [str(r[0]) for r in rows]

# ===================== Buttons =====================
async def _next_pos() -> int:
    v = await _fetchval("SELECT MAX(pos) FROM buttons")
    return (int(v) + 1) if v is not None else 1

async def create_button(title: str) -> int:
    pos = await _next_pos()
    db = await _connect()
    try:
        cur = await db.execute("INSERT INTO buttons(title, pos) VALUES(?, ?)", (title, pos))
        await db.commit()
        return cur.lastrowid
    finally:
        await db.close()

async def list_buttons() -> List[Tuple[int, str]]:
    rows = await _fetchall("SELECT id, title FROM buttons ORDER BY pos ASC")
    return [(int(r[0]), str(r[1])) for r in rows]

async def get_menu_cols() -> int:
    v = await _fetchval("SELECT value FROM settings WHERE key='menu_cols'")
    try:
        return max(1, min(4, int(v)))
    except Exception:
        return 2

async def set_menu_cols(n: int) -> None:
    n = max(1, min(4, int(n)))
    await _exec("""
        INSERT INTO settings(key, value) VALUES('menu_cols', ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
    """, (str(n),))

async def rename_button(button_id: int, new_title: str) -> None:
    await _exec("UPDATE buttons SET title=? WHERE id=?", (new_title, int(button_id)))

async def _resequence_positions() -> None:
    rows = await _fetchall("SELECT id FROM buttons ORDER BY pos ASC")
    pos = 1
    db = await _connect()
    try:
        for r in rows:
            bid = int(r[0])
            await db.execute("UPDATE buttons SET pos=? WHERE id=?", (pos, bid))
            pos += 1
        await db.commit()
    finally:
        await db.close()

async def delete_button(button_id: int) -> None:
    await _exec("DELETE FROM button_contents WHERE button_id=?", (int(button_id),))
    await _exec("DELETE FROM buttons WHERE id=?", (int(button_id),))
    await _resequence_positions()

async def swap_with_neighbor(button_id: int, up: bool = True) -> None:
    cur = await _fetchone("SELECT id, pos FROM buttons WHERE id=?", (int(button_id),))
    if not cur:
        return
    bid, pos = int(cur[0]), int(cur[1])

    if up:
        neighbor = await _fetchone(
            "SELECT id, pos FROM buttons WHERE pos < ? ORDER BY pos DESC LIMIT 1", (pos,))
    else:
        neighbor = await _fetchone(
            "SELECT id, pos FROM buttons WHERE pos > ? ORDER BY pos ASC LIMIT 1", (pos,))

    if not neighbor:
        return

    nbid, npos = int(neighbor[0]), int(neighbor[1])

    db = await _connect()
    try:
        await db.execute("UPDATE buttons SET pos=? WHERE id=?", (npos, bid))
        await db.execute("UPDATE buttons SET pos=? WHERE id=?", (pos, nbid))
        await db.commit()
    finally:
        await db.close()

# ===================== Button Contents =====================
async def add_button_content(button_id: int,
                             media_type: str,
                             file_id: Optional[str],
                             caption: Optional[str]) -> int:
    db = await _connect()
    try:
        cur = await db.execute(
            "INSERT INTO button_contents(button_id, media_type, file_id, caption) VALUES(?, ?, ?, ?)",
            (int(button_id), media_type, file_id, caption)
        )
        await db.commit()
        return cur.lastrowid
    finally:
        await db.close()

async def list_button_contents(button_id: int) -> List[Tuple[int, str, Optional[str], Optional[str]]]:
    rows = await _fetchall("""
        SELECT id, media_type, file_id, caption
        FROM button_contents
        WHERE button_id=?
        ORDER BY id ASC
    """, (int(button_id),))
    return [(int(r[0]), str(r[1]), r[2], r[3]) for r in rows]

async def delete_button_content(content_id: int) -> None:
    await _exec("DELETE FROM button_contents WHERE id=?", (int(content_id),))

# ===================== Adminlar =====================
async def add_admin(user_id: int, name: Optional[str] = None, is_super: bool = False) -> None:
    await _exec("""
    INSERT INTO admins(user_id, name, is_super)
    VALUES(?, ?, ?)
    ON CONFLICT(user_id) DO UPDATE SET
        name=excluded.name,
        is_super=excluded.is_super
    """, (int(user_id), name, 1 if is_super else 0))

async def remove_admin(user_id: int) -> None:
    await _exec("DELETE FROM admins WHERE user_id=?", (int(user_id),))

async def list_admins() -> List[Tuple[int, Optional[str]]]:
    rows = await _fetchall("SELECT user_id, name FROM admins ORDER BY is_super DESC, user_id ASC")
    return [(int(r[0]), r[1]) for r in rows]

async def is_admin(user_id: int) -> bool:
    v = await _fetchval("SELECT 1 FROM admins WHERE user_id=? LIMIT 1", (int(user_id),))
    return v is not None

async def is_super_admin(user_id: int) -> bool:
    v = await _fetchval("SELECT 1 FROM admins WHERE user_id=? AND is_super=1 LIMIT 1", (int(user_id),))
    return v is not None

async def bootstrap_super_admin(user_id: int | str | None = None, name: str | None = None) -> None:
    if user_id is None:
        for key in ("SUPER_ADMIN_ID", "BOT_OWNER_ID", "OWNER_ID"):
            val = os.getenv(key)
            if val:
                user_id = val
                break
    if user_id is None:
        return
    try:
        uid = int(user_id)
    except Exception:
        return

    row = await _fetchone("SELECT is_super FROM admins WHERE user_id=?", (uid,))
    if row and int(row[0]) == 1:
        return

    await add_admin(uid, name, is_super=True)
