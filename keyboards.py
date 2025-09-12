# keyboards.py
from typing import List, Tuple, Any, Optional
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)

# -------------------- Helpers --------------------
def _normalize_url(username: Optional[str], invite_link: Optional[str], raw_url: Optional[str] = None) -> Optional[str]:
    if username:
        return f"https://t.me/{username.lstrip('@')}"
    if invite_link:
        return invite_link
    if raw_url and isinstance(raw_url, str) and raw_url.startswith("http"):
        return raw_url
    return None

# ==================== ADMIN ROOT ====================
def admin_menu_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="📌 Majburiy kanallar", callback_data="ad_channels")],
        [InlineKeyboardButton(text="🎛 Tugmalar",          callback_data="ad_buttons")],
        [InlineKeyboardButton(text="👥 Foydalanuvchilar",  callback_data="ad_users")],
        [InlineKeyboardButton(text="👮 Adminlar",          callback_data="ad_admins")],
        [InlineKeyboardButton(text="📣 Reklama yuborish",  callback_data="ad_broadcast")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def back_only_kb(back_to: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Orqaga", callback_data=back_to)]])

# ==================== MAJBURIY KANALLAR (ADMIN) ====================
def channels_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="➕ Kanal qo‘shish", callback_data="ch_add_simple")],
        [InlineKeyboardButton(text="📋 Ro‘yxat",        callback_data="ch_list")],
        [InlineKeyboardButton(text="🗑 O‘chirish",      callback_data="ch_del")],
        [InlineKeyboardButton(text="⬅️ Orqaga",        callback_data="admin_back")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def ch_add_mode_kb(back_to: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="🌐 Oddiy kanal",            callback_data="ch_type:n")],
        [InlineKeyboardButton(text="🔒 Join-request (zayavka)", callback_data="ch_type:j")],
        [InlineKeyboardButton(text="⬅️ Orqaga",                 callback_data=back_to)],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ==================== TUGMALAR (ADMIN) ====================
def buttons_menu_kb(cols: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"⚙️ Joylashuv (ustunlar): {cols}", callback_data="btn_cols")],
        [InlineKeyboardButton(text="➕ Yangi tugma",              callback_data="btn_add")],
        [InlineKeyboardButton(text="✏️ Nomini o‘zgartirish",      callback_data="btn_rename")],
        [InlineKeyboardButton(text="↕️ Joyini almashtirish",      callback_data="btn_move")],
        [InlineKeyboardButton(text="📎 Tugmaga kontent qo‘shish", callback_data="btn_add_content")],
        [InlineKeyboardButton(text="📑 Kontentlarni boshqarish",  callback_data="btn_list_content")],
        [InlineKeyboardButton(text="🗑 Tugmani o‘chirish",         callback_data="btn_del")],
        [InlineKeyboardButton(text="ℹ️ Ma’lumot",                 callback_data="btn_info")],
        [InlineKeyboardButton(text="⬅️ Orqaga",                   callback_data="admin_back")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def cols_kb(current: int) -> InlineKeyboardMarkup:
    row, rows = [], []
    for i in (1, 2, 3, 4):
        label = f"{'✅ ' if i == current else ''}{i}"
        row.append(InlineKeyboardButton(text=label, callback_data=f"set_cols:{i}"))
    rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="ad_buttons")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def pick_button_kb(items: List[Tuple[int, str]], back_to: str, prefix: str) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for bid, title in items:
        rows.append([InlineKeyboardButton(text=f"#{bid} — {title}", callback_data=f"{prefix}:{bid}")])
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data=back_to)])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ==================== USERS & ADMINS (ADMIN) ====================
def users_menu_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="📊 Statistika",    callback_data="u_stats")],
        [InlineKeyboardButton(text="📤 Excel eksport", callback_data="u_export")],
        [InlineKeyboardButton(text="⬅️ Orqaga",        callback_data="admin_back")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def admins_menu_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="📋 Ro‘yxat",  callback_data="adm_list")],
        [InlineKeyboardButton(text="➕ Qo‘shish",  callback_data="adm_add")],
        [InlineKeyboardButton(text="🗑 O‘chirish", callback_data="adm_del")],
        [InlineKeyboardButton(text="⬅️ Orqaga",   callback_data="admin_back")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ==================== FOYDALANUVCHI TOMON ====================
def subscribe_kb(rows: List[Tuple[str, Optional[str], Optional[str], Optional[str], Optional[str]]]
                 ) -> InlineKeyboardMarkup:
    ikb: List[List[InlineKeyboardButton]] = []
    for chat_id, title, username, invite_link, url in rows:
        open_url = _normalize_url(username, invite_link, url) or "https://t.me/"
        text = f"{title or ('@'+username if username else chat_id)}"
        ikb.append([InlineKeyboardButton(text=text, url=open_url)])
    ikb.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=ikb)

# Reply (oddiy) menyu — foydalanuvchi taraf
def reply_menu_kb(btns: List[Tuple[int, str]], cols: int, with_back: bool = False) -> ReplyKeyboardMarkup:
    cols = max(1, min(4, int(cols or 1)))
    buttons = [KeyboardButton(text=title) for _, title in btns]
    # satrlarga bo‘lish
    rows: List[List[KeyboardButton]] = []
    row: List[KeyboardButton] = []
    for b in buttons:
        row.append(b)
        if len(row) == cols:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    if with_back:
        rows.append([KeyboardButton(text="⬅️ Orqaga")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=False)
