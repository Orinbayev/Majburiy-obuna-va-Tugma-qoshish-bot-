# keyboards.py
from typing import List, Tuple, Any, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# -------------------- Helpers --------------------
def _normalize_url(username: Optional[str],
                   invite_link: Optional[str],
                   raw_url: Optional[str] = None) -> Optional[str]:
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
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_only_kb(back_to: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=back_to)]
    ])


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


def _extract_btn(rec: Any) -> Optional[Tuple[int, str, Optional[int]]]:
    """
    Har xil ko‘rinishdagi yozuvlardan (id, title[, order]) ni sug‘urib oladi.
    Qaytadi: (id, title, order|None) yoki None
    """
    bid: Optional[int] = None
    title: Optional[str] = None
    order: Optional[int] = None

    if isinstance(rec, (list, tuple)):
        if len(rec) >= 1:
            try:
                bid = int(rec[0])
            except Exception:
                return None
        if len(rec) >= 2:
            title = str(rec[1])
        if len(rec) >= 3 and isinstance(rec[2], (int, float)):
            order = int(rec[2])

    elif isinstance(rec, dict):
        bid = rec.get("id") or rec.get("bid") or rec.get("button_id")
        title = rec.get("title") or rec.get("name") or rec.get("text")
        order = rec.get("order") or rec.get("pos") or rec.get("sort")
        if bid is not None:
            try:
                bid = int(bid)
            except Exception:
                return None
        if title is not None:
            title = str(title)
        if order is not None:
            try:
                order = int(order)
            except Exception:
                order = None

    if bid is None or title is None:
        return None
    return bid, title, order


def pick_button_kb(btns: Any, back_to: str, prefix: str) -> InlineKeyboardMarkup:
    """
    btns: [(id, title), (id, title, order, ...)] YOKI dict’lar ketma-ketligi.
    """
    items: List[Tuple[int, str, Optional[int]]] = []
    for rec in btns:
        parsed = _extract_btn(rec)
        if parsed:
            items.append(parsed)  # (id, title, order)

    # tartiblash (order bo'lsa, unga ko'ra)
    items.sort(key=lambda x: (x[2] is None, x[2]))

    rows: List[List[InlineKeyboardButton]] = []
    for bid, title, _ in items:
        rows.append([
            InlineKeyboardButton(text=f"#{bid} — {title}", callback_data=f"{prefix}:{bid}")
        ])
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
# 1) Majburiy obuna klaviaturasi
def subscribe_kb(rows: List[Tuple[str, Optional[str], Optional[str], Optional[str], Optional[str]]]
                 ) -> InlineKeyboardMarkup:
    """
    rows: (chat_id, title, username, invite_link, url)
    Har kanal uchun tashqi URL tugma + pastda '✅ Tekshirish'
    Callback: 'check_sub'
    """
    ikb: List[List[InlineKeyboardButton]] = []
    for chat_id, title, username, invite_link, url in rows:
        open_url = _normalize_url(username, invite_link, url) or "https://t.me/"
        text = f"{title or ('@'+username if username else chat_id)}"
        ikb.append([InlineKeyboardButton(text=text, url=open_url)])
    ikb.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=ikb)


# 2) Asosiy menyu — universal parser
def main_menu_kb(btns: Any, cols: int) -> InlineKeyboardMarkup:
    """
    btns: [(id, title), (id, title, order, ...)] yoki dict’lar.
    cols: 1..4
    """
    cols = max(1, min(4, int(cols or 1)))
    items: List[Tuple[Optional[int], int, str]] = []  # (order, id, title)

    for rec in btns:
        parsed = _extract_btn(rec)  # (id, title, order)
        if not parsed:
            continue
        bid, title, order = parsed
        items.append((order, bid, title))

    # order bo'lsa shu bo'yicha, bo'lmasa kelgan tartib
    items.sort(key=lambda x: (x[0] is None, x[0]))

    rows: List[List[InlineKeyboardButton]] = []
    row: List[InlineKeyboardButton] = []
    for _, bid, title in items:
        # start.py da handler: F.data.startswith("open_btn:")
        row.append(InlineKeyboardButton(text=title, callback_data=f"open_btn:{bid}"))
        if len(row) == cols:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


# 3) DB’dan avtomatik
async def main_menu_kb_from_db() -> InlineKeyboardMarkup:
    from db import list_buttons, get_menu_cols
    btns = await list_buttons()
    cols = await get_menu_cols()
    return main_menu_kb(btns, cols)
