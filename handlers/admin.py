# handlers/admin.py  (aiogram v3)
from __future__ import annotations
import asyncio
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta, timezone
from openpyxl import Workbook
import io
from typing import Optional, List, Tuple

from keyboards import (
    admin_menu_kb, channels_kb, buttons_menu_kb, users_menu_kb, back_only_kb,
    ch_add_mode_kb, pick_button_kb, cols_kb
)
from utils.telegram import safe_edit
from db import (
    # channels
    save_channel, remove_channel, list_channels_full,
    # users
    count_users_range, fetch_all_users, fetch_all_user_ids,
    # buttons (nested)
    create_button, list_buttons, find_button_by_title, has_children,
    rename_button, delete_button, add_button_content, list_button_contents,
    delete_button_content, swap_with_neighbor, get_menu_cols, set_menu_cols,
    # admins
    is_admin, is_super_admin, add_admin, remove_admin, list_admins, bootstrap_super_admin,
)

admin_router = Router()

# ---------- /admin kirish faqat bu faylda emas START.py dagi handlerlar orqali ----------

@admin_router.callback_query(F.data == "admin_back")
async def back_to_root(cb: CallbackQuery):
    if not (await is_admin(cb.from_user.id)):
        return await cb.answer("Ruxsat yo‘q.")
    await safe_edit(cb.message, "Admin panel:", reply_markup=admin_menu_kb())
    await cb.answer()

# ==================== KANALLAR (ixcham) ====================
def _normalize_url(username: str | None, invite_link: str | None, raw_url: str | None = None):
    if username:  return f"https://t.me/{username.lstrip('@')}"
    if invite_link:return invite_link
    if raw_url and raw_url.startswith("http"): return raw_url
    return None

class ChAddSG(StatesGroup):
    ask_id = State()
    choose_mode = State()
    ask_link = State()

@admin_router.callback_query(F.data == "ad_channels")
async def ch_root(cb: CallbackQuery):
    if not (await is_admin(cb.from_user.id)):
        return await cb.answer("Ruxsat yo‘q.")
    await safe_edit(cb.message, "📌 Majburiy kanallar:", reply_markup=channels_kb())
    await cb.answer()

@admin_router.callback_query(F.data == "ch_add_simple")
async def ch_add_start(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(ChAddSG.ask_id)
    txt = ("Kanal ID (-100...) yoki @username yuboring.\n"
           "Invite-link ham bo‘ladi (t.me/...).")
    await safe_edit(cb.message, txt, reply_markup=back_only_kb("ad_channels"))
    await cb.answer()

@admin_router.message(ChAddSG.ask_id)
async def ch_add_collect_id_or_link(m: Message, state: FSMContext, bot: Bot):
    raw = (m.text or "").strip()
    if raw.startswith("http"):
        await state.update_data(invite_link=raw)
        return await m.answer("Link qabul qilindi. Endi kanalning ID yoki @username yubor.")

    chat = None; username = None; chat_id = None; title = None
    if raw.startswith("@"):
        username = raw
        try: chat = await bot.get_chat(username)
        except Exception: pass
    else:
        try: chat_id = int(raw)
        except Exception: return await m.answer("❌ ID yoki @username yuboring.")
        try: chat = await bot.get_chat(chat_id)
        except Exception: return await m.answer("❌ Bot kanalni ko‘ra olmadi. Admin qiling yoki username to‘g‘ri ekanini tekshiring.")

    if chat:
        chat_id = chat.id
        title = getattr(chat, "title", None)
        username = getattr(chat, "username", username)

    d = await state.get_data()
    await state.update_data(chat_id=chat_id, title=title, username=username, invite_link=d.get("invite_link"))
    await state.set_state(ChAddSG.choose_mode)
    await m.answer(f"Topildi: <b>{title or chat_id or username}</b>\nKanal turi?", reply_markup=ch_add_mode_kb(back_to="ad_channels"))

async def _make_permanent_join_request_link(bot: Bot, chat_id: int) -> str | None:
    try:
        link = await bot.create_chat_invite_link(chat_id=chat_id, creates_join_request=True, name="ForcedSub")
        return link.invite_link
    except Exception:
        return None

@admin_router.callback_query(ChAddSG.choose_mode, F.data.in_({"ch_type:n", "ch_type:j"}))
async def ch_add_choose_type(cb: CallbackQuery, state: FSMContext, bot: Bot):
    d = await state.get_data()
    chat_id = d.get("chat_id"); title = d.get("title")
    username = d.get("username"); invite_link = d.get("invite_link")
    is_join = cb.data.endswith(":j")

    if is_join and not username:
        fresh = await _make_permanent_join_request_link(bot, chat_id)
        if fresh:
            invite_link = fresh
        else:
            await state.set_state(ChAddSG.ask_link)
            await safe_edit(cb.message, "Join-request kanal. Link yuboring (t.me/+...)", reply_markup=back_only_kb("ad_channels"))
            return await cb.answer()

    url = _normalize_url(username, invite_link)
    await save_channel(str(chat_id), title, username, invite_link, url)
    await state.clear()
    await safe_edit(cb.message, f"✅ Kanal qo‘shildi:\n<b>{title or '—'}</b>\nID: <code>{chat_id}</code>\nURL: {url or '—'}\n/admin",
                    reply_markup=channels_kb())
    await cb.answer("Saqlandi.")

@admin_router.message(ChAddSG.ask_link)
async def ch_add_collect_link_and_save(m: Message, state: FSMContext):
    link = (m.text or "").strip()
    if not (link.startswith("http://") or link.startswith("https://")):
        return await m.answer("❌ To‘g‘ri link yuboring (t.me/...).")
    d = await state.get_data()
    chat_id = d["chat_id"]; title = d.get("title"); username = d.get("username")
    await state.clear()
    url = _normalize_url(username, link)
    await save_channel(str(chat_id), title, username, link, url)
    await m.answer(f"✅ Kanal qo‘shildi:\n<b>{title or '—'}</b>\nID: <code>{chat_id}</code>\nURL: {url}\n/admin")

@admin_router.callback_query(F.data == "ch_list")
async def ch_list(cb: CallbackQuery):
    rows = await list_channels_full()
    if not rows:
        await safe_edit(cb.message, "Ro‘yxat bo‘sh.", reply_markup=channels_kb())
        return await cb.answer()
    ikb = []
    for (chat_id, title, username, invite_link, url) in rows:
        open_url = _normalize_url(username, invite_link, url) or "https://t.me/"
        text = f"{title or '—'}  ({chat_id})"
        ikb.append([InlineKeyboardButton(text=text, url=open_url)])
    ikb.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="ad_channels")])
    await safe_edit(cb.message, "📋 Majburiy kanallar ro‘yxati:", reply_markup=InlineKeyboardMarkup(inline_keyboard=ikb))
    await cb.answer()

@admin_router.callback_query(F.data == "ch_del")
async def ch_del_pick(cb: CallbackQuery):
    rows = await list_channels_full()
    if not rows:
        await safe_edit(cb.message, "O‘chirish uchun kanal yo‘q.", reply_markup=channels_kb())
        return await cb.answer()
    ikb = []
    for (chat_id, title, *_rest) in rows:
        txt = f"🗑 {title or '—'}  ({chat_id})"
        ikb.append([InlineKeyboardButton(text=txt, callback_data=f"pickdel:{chat_id}")])
    ikb.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="ad_channels")])
    await safe_edit(cb.message, "Qaysi kanalni o‘chiramiz?", reply_markup=InlineKeyboardMarkup(inline_keyboard=ikb))
    await cb.answer()

@admin_router.callback_query(F.data.startswith("pickdel:"))
async def ch_del_confirm(cb: CallbackQuery):
    chat_id = cb.data.split(":", 1)[1]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha, o‘chir", callback_data=f"chdel:{chat_id}:yes")],
        [InlineKeyboardButton(text="⬅️ Bekor", callback_data="ch_del")],
    ])
    await safe_edit(cb.message, f"Rostdan o‘chirasizmi?\nID: <code>{chat_id}</code>", reply_markup=kb)
    await cb.answer()

@admin_router.callback_query(F.data.startswith("chdel:"))
async def ch_del_do(cb: CallbackQuery):
    try:
        _, chat_id, ans = cb.data.split(":")
    except ValueError:
        return await cb.answer()
    if ans == "yes":
        n = await remove_channel(chat_id)
        msg = "✅ O‘chirildi." if n else "⚠️ Topilmadi."
        await safe_edit(cb.message, msg, reply_markup=channels_kb())
        await cb.answer("Bajarildi.")
    else:
        await safe_edit(cb.message, "Bekor qilindi.", reply_markup=channels_kb())
        await cb.answer()

# ==================== TUGMALAR (nested, async) ====================
async def _flatten_buttons_for_pick(parent_id: int | None = None, prefix: str = "") -> List[Tuple[int, str]]:
    items: List[Tuple[int, str]] = []
    rows = await list_buttons(parent_id)
    for bid, title in rows:
        items.append((bid, f"{prefix}{title}"))
        if await has_children(bid):
            items += await _flatten_buttons_for_pick(bid, prefix + "› ")
    return items

class BtnCreateSG(StatesGroup):
    parent = State()
    title = State()

class BtnRenameSG(StatesGroup):
    btn_id = State()
    new_title = State()

class BtnMoveSG(StatesGroup):
    btn_id = State()

class BtnAddContentSG(StatesGroup):
    btn_id = State()
    waiting_media = State()

def _add_where_kb(flat_items):
    rows = [[InlineKeyboardButton(text="📁 Root’ga qo‘shish", callback_data="add_here:root")]]
    for bid, label in flat_items:
        rows.append([InlineKeyboardButton(text=f"📂 {label}", callback_data=f"add_here:{bid}")])
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="ad_buttons")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

@admin_router.callback_query(F.data == "ad_buttons")
async def btn_menu(cb: CallbackQuery):
    if not (await is_admin(cb.from_user.id)):
        return await cb.answer("Ruxsat yo‘q.")
    cols = await get_menu_cols()
    await safe_edit(cb.message, "Tugmalar menyusi:", reply_markup=buttons_menu_kb(cols))
    await cb.answer()

@admin_router.callback_query(F.data.in_({"btn_layout", "btn_cols"}))
async def btn_cols_open(cb: CallbackQuery):
    cols = await get_menu_cols()
    await safe_edit(cb.message, "Nechta ustunda ko‘rsatamiz?", reply_markup=cols_kb(cols))
    await cb.answer()

@admin_router.callback_query(F.data.startswith("set_cols:"))
async def btn_cols_set(cb: CallbackQuery):
    n = int(cb.data.split(":")[1])
    await set_menu_cols(n)
    await safe_edit(cb.message, "Tugmalar menyusi:", reply_markup=buttons_menu_kb(await get_menu_cols()))
    await cb.answer("Joylashuv yangilandi.")

# Yangi tugma (joy tanlash -> nom yuborish)
@admin_router.callback_query(F.data == "btn_add")
async def btn_add_where(cb: CallbackQuery, state: FSMContext):
    flat = await _flatten_buttons_for_pick(None)
    await state.set_state(BtnCreateSG.parent)
    await safe_edit(cb.message, "Yangi tugma qayerga qo‘shilsin?", reply_markup=_add_where_kb(flat))
    await cb.answer()

@admin_router.callback_query(BtnCreateSG.parent, F.data.startswith("add_here:"))
async def btn_add_set_parent(cb: CallbackQuery, state: FSMContext):
    token = cb.data.split(":")[1]
    parent_id = None if token == "root" else int(token)
    await state.update_data(parent_id=parent_id)
    await state.set_state(BtnCreateSG.title)
    await safe_edit(cb.message, "Yangi tugma nomini yuboring:", reply_markup=back_only_kb("ad_buttons"))
    await cb.answer()

@admin_router.message(BtnCreateSG.title)
async def btn_add_save(m: Message, state: FSMContext):
    d = await state.get_data()
    parent_id = d.get("parent_id")
    title = (m.text or "").strip()
    if not title:
        return await m.answer("Nom bo‘sh bo‘lmasin.")
    bid = await create_button(title, parent_id)
    await state.clear()
    await m.answer(f"✅ Tugma yaratildi (ID={bid}). /admin")

# Nomini o‘zgartirish
@admin_router.callback_query(F.data == "btn_rename")
async def btn_rename_pick(cb: CallbackQuery, state: FSMContext):
    flat = await _flatten_buttons_for_pick(None)
    if not flat:
        return await safe_edit(cb.message, "Tugmalar yo‘q.", reply_markup=buttons_menu_kb(await get_menu_cols()))
    await state.set_state(BtnRenameSG.btn_id)
    await safe_edit(cb.message, "Qaysi tugma?", reply_markup=pick_button_kb(flat, "ad_buttons", "pick_rnm"))
    await cb.answer()

@admin_router.callback_query(BtnRenameSG.btn_id, F.data.startswith("pick_rnm:"))
async def btn_rename_wait_name(cb: CallbackQuery, state: FSMContext):
    bid = int(cb.data.split(":")[1])
    await state.update_data(btn_id=bid)
    await state.set_state(BtnRenameSG.new_title)
    await safe_edit(cb.message, "Yangi nomni yuboring:", reply_markup=back_only_kb("ad_buttons"))
    await cb.answer()

@admin_router.message(BtnRenameSG.new_title)
async def btn_rename_do(m: Message, state: FSMContext):
    d = await state.get_data()
    await rename_button(d["btn_id"], (m.text or "").strip())
    await state.clear()
    await m.answer("✅ Nom o‘zgartirildi. /admin")

# Joyini almashtirish
def move_controls_kb(bid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬆️ Tepaga", callback_data=f"mv:{bid}:up")],
        [InlineKeyboardButton(text="⬇️ Pastga", callback_data=f"mv:{bid}:down")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="ad_buttons")],
    ])

@admin_router.callback_query(F.data == "btn_move")
async def btn_move_pick(cb: CallbackQuery, state: FSMContext):
    flat = await _flatten_buttons_for_pick(None)
    if not flat:
        return await safe_edit(cb.message, "Tugmalar yo‘q.", reply_markup=buttons_menu_kb(await get_menu_cols()))
    await state.set_state(BtnMoveSG.btn_id)
    await safe_edit(cb.message, "Qaysi tugma ko‘chirilsin?", reply_markup=pick_button_kb(flat, "ad_buttons", "pick_move"))
    await cb.answer()

@admin_router.callback_query(BtnMoveSG.btn_id, F.data.startswith("pick_move:"))
async def btn_move_controls(cb: CallbackQuery, state: FSMContext):
    bid = int(cb.data.split(":")[1])
    await state.update_data(btn_id=bid)
    await safe_edit(cb.message, "Qanday ko‘chiramiz?", reply_markup=move_controls_kb(bid))
    await cb.answer()

@admin_router.callback_query(F.data.startswith("mv:"))
async def btn_move_do(cb: CallbackQuery):
    _, sid, direction = cb.data.split(":")
    await swap_with_neighbor(int(sid), up=(direction == "up"))
    await safe_edit(cb.message, "Joylashtirish yangilandi.", reply_markup=buttons_menu_kb(await get_menu_cols()))
    await cb.answer("OK")

# O‘chirish
def del_confirm_kb(bid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Ha, o‘chir", callback_data=f"delbtn:{bid}:yes")],
        [InlineKeyboardButton(text="⬅️ Bekor", callback_data="ad_buttons")],
    ])

@admin_router.callback_query(F.data == "btn_del")
async def btn_del_pick(cb: CallbackQuery):
    flat = await _flatten_buttons_for_pick(None)
    if not flat:
        return await safe_edit(cb.message, "Tugmalar yo‘q.", reply_markup=buttons_menu_kb(await get_menu_cols()))
    await safe_edit(cb.message, "Qaysi tugma o‘chirilsin?", reply_markup=pick_button_kb(flat, "ad_buttons", "pick_del"))
    await cb.answer()

@admin_router.callback_query(F.data.startswith("pick_del:"))
async def btn_del_confirm(cb: CallbackQuery):
    bid = int(cb.data.split(":")[1])
    await safe_edit(cb.message, f"Tasdiqlaysizmi? (ID={bid})", reply_markup=del_confirm_kb(bid))
    await cb.answer()

@admin_router.callback_query(F.data.startswith("delbtn:"))
async def btn_del_do(cb: CallbackQuery):
    _, sid, ans = cb.data.split(":")
    if ans == "yes":
        await delete_button(int(sid))
        await safe_edit(cb.message, "✅ O‘chirildi. Raqamlar qayta sanaldi.", reply_markup=buttons_menu_kb(await get_menu_cols()))
        await cb.answer("O‘chirildi")
    else:
        await cb.answer("Bekor")

# Kontent qo‘shish / boshqarish — to‘liq async
def content_manage_kb(items):
    rows = [[InlineKeyboardButton(text=f"❌ Del #{_id} ({mtype})", callback_data=f"delbc:{_id}")]
            for (_id, mtype, _, _) in items]
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="ad_buttons")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

@admin_router.callback_query(F.data == "btn_add_content")
async def btn_add_content_ask(cb: CallbackQuery, state: FSMContext):
    flat = await _flatten_buttons_for_pick(None)
    if not flat:
        return await safe_edit(cb.message, "Tugmalar yo‘q.", reply_markup=buttons_menu_kb(await get_menu_cols()))
    await state.set_state(BtnAddContentSG.btn_id)
    await safe_edit(cb.message, "Qaysi tugmaga kontent qo‘shamiz?", reply_markup=pick_button_kb(flat, "ad_buttons", "pick_content"))
    await cb.answer()

@admin_router.callback_query(BtnAddContentSG.btn_id, F.data.startswith("pick_content:"))
async def btn_add_content_wait(cb: CallbackQuery, state: FSMContext):
    bid = int(cb.data.split(":")[1])
    await state.update_data(btn_id=bid)
    await state.set_state(BtnAddContentSG.waiting_media)
    await safe_edit(cb.message, "Kontent yuboring: matn / foto / video / document / audio / gif.\nTugatish: /admin.",
                    reply_markup=back_only_kb("ad_buttons"))
    await cb.answer()

@admin_router.message(BtnAddContentSG.waiting_media)
async def btn_add_content_save(m: Message, state: FSMContext):
    d = await state.get_data()
    bid = d["btn_id"]

    if m.photo:
        file_id, media_type, caption = m.photo[-1].file_id, "photo", m.caption
    elif m.video:
        file_id, media_type, caption = m.video.file_id, "video", m.caption
    elif m.document:
        file_id, media_type, caption = m.document.file_id, "document", m.caption
    elif m.audio:
        file_id, media_type, caption = m.audio.file_id, "audio", m.caption
    elif m.animation:
        file_id, media_type, caption = m.animation.file_id, "animation", m.caption
    elif m.text:
        file_id, media_type, caption = None, "text", m.text
    else:
        return await m.answer("Qo‘llanmagan tur.")

    await add_button_content(bid, media_type, file_id, caption)
    await m.answer("✅ Saqlandi. Yana yuborishingiz mumkin. /admin")

@admin_router.callback_query(F.data == "btn_list_content")
async def btn_list_content_pick(cb: CallbackQuery):
    flat = await _flatten_buttons_for_pick(None)
    if not flat:
        return await safe_edit(cb.message, "Tugmalar yo‘q.", reply_markup=buttons_menu_kb(await get_menu_cols()))
    await safe_edit(cb.message, "Qaysi tugmaniki?", reply_markup=pick_button_kb(flat, "ad_buttons", "pick_showc"))
    await cb.answer()

@admin_router.callback_query(F.data.startswith("pick_showc:"))
async def btn_list_content_show(cb: CallbackQuery):
    bid = int(cb.data.split(":")[1])
    items = await list_button_contents(bid)
    if not items:
        await safe_edit(cb.message, "Bu tugmada kontent yo‘q.", reply_markup=buttons_menu_kb(await get_menu_cols()))
        return await cb.answer()
    txt = "Kontentlar:\n" + "\n".join([
        f"{i}. id={r[0]} | {r[1]} | {('file' if r[2] else 'text')} | {(r[3][:40]+'...') if r[3] else '-'}"
        for i, r in enumerate(items, 1)
    ])
    await safe_edit(cb.message, txt, reply_markup=content_manage_kb(items))
    await cb.answer()

@admin_router.callback_query(F.data.startswith("delbc:"))
async def btn_del_content_do(cb: CallbackQuery):
    cid = int(cb.data.split(":")[1])
    await delete_button_content(cid)
    await safe_edit(cb.message, "O‘chirildi. /admin", reply_markup=buttons_menu_kb(await get_menu_cols()))
    await cb.answer("O‘chirildi")

# ==================== USERS ====================
@admin_router.callback_query(F.data == "ad_users")
async def users_menu(cb: CallbackQuery):
    await safe_edit(cb.message, "Foydalanuvchilar bo‘limi:", reply_markup=users_menu_kb())
    await cb.answer()

@admin_router.callback_query(F.data == "u_stats")
async def users_stats(cb: CallbackQuery):
    now = datetime.now(timezone.utc)
    total = await count_users_range(None)
    last24 = await count_users_range((now - timedelta(days=1)).isoformat())
    last7  = await count_users_range((now - timedelta(days=7)).isoformat())
    last30 = await count_users_range((now - timedelta(days=30)).isoformat())
    txt = (f"👥 Umumiy: <b>{total}</b>\n"
           f"🕐 24 soat: <b>{last24}</b>\n"
           f"📅 Oxirgi hafta: <b>{last7}</b>\n"
           f"🗓️ Oxirgi 30 kun: <b>{last30}</b>")
    await safe_edit(cb.message, txt, reply_markup=users_menu_kb())
    await cb.answer()

@admin_router.callback_query(F.data == "u_export")
async def users_export(cb: CallbackQuery, bot: Bot):
    rows = await fetch_all_users()
    wb = Workbook(); ws = wb.active; ws.title = "users"
    ws.append(["user_id","first_name","last_name","username","joined_at"])
    for r in rows: ws.append(list(r))
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    await bot.send_document(cb.from_user.id, document=BufferedInputFile(buf.getvalue(), filename="users.xlsx"))
    await cb.answer("Yuklandi.")

# ==================== ADMINLAR (oddiy) ====================
class AdmAddSG(StatesGroup):
    waiting = State()
class AdmDelSG(StatesGroup):
    waiting = State()

def _admins_menu_kb(super_mode: bool) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="📋 Ro‘yxat", callback_data="adm_list")]]
    if super_mode:
        rows.append([InlineKeyboardButton(text="➕ Qo‘shish", callback_data="adm_add")])
        rows.append([InlineKeyboardButton(text="🗑 O‘chirish", callback_data="adm_del")])
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

@admin_router.callback_query(F.data == "ad_admins")
async def admins_root(cb: CallbackQuery):
    if not (await is_admin(cb.from_user.id)):
        return await cb.answer("Yo‘q.")
    super_mode = await is_super_admin(cb.from_user.id)
    await safe_edit(cb.message, "Adminlar:", reply_markup=_admins_menu_kb(super_mode))
    await cb.answer()

@admin_router.callback_query(F.data == "adm_list")
async def admins_list_handler(cb: CallbackQuery):
    rows = await list_admins()
    lines = [f"• {uid} — admin{(' ('+name+')' if name else '')}" for uid, name in rows]
    txt = "👮 Adminlar:\n" + ("\n".join(lines) if lines else "— yo‘q —")
    super_mode = await is_super_admin(cb.from_user.id)
    await safe_edit(cb.message, txt, reply_markup=_admins_menu_kb(super_mode))
    await cb.answer()

@admin_router.callback_query(F.data == "adm_add")
async def admins_add_start(cb: CallbackQuery, state: FSMContext):
    if not (await is_super_admin(cb.from_user.id)):
        return await cb.answer("Faqat super admin qo‘shishi mumkin.", show_alert=True)
    await state.set_state(AdmAddSG.waiting)
    await safe_edit(cb.message, "Yangi admin ID yoki @username yuboring:", reply_markup=_admins_menu_kb(True))
    await cb.answer()

@admin_router.message(AdmAddSG.waiting)
async def admins_add_do(m: Message, state: FSMContext, bot: Bot):
    if not (await is_super_admin(m.from_user.id)):
        return await m.answer("Faqat super admin qo‘shishi mumkin.")
    raw = (m.text or "").strip()
    uid = None; name = None
    if raw.startswith("@"):
        try:
            u = await bot.get_chat(raw)
            uid, name = u.id, u.full_name
        except Exception:
            return await m.answer("Username topilmadi.")
    else:
        try: uid = int(raw)
        except Exception: return await m.answer("ID noto‘g‘ri.")
    await add_admin(uid, name, False)
    await state.clear()
    await m.answer("✅ Qo‘shildi. /admin")

@admin_router.callback_query(F.data == "adm_del")
async def admins_del_start(cb: CallbackQuery, state: FSMContext):
    if not (await is_super_admin(cb.from_user.id)):
        return await cb.answer("Faqat super admin o‘chira oladi.", show_alert=True)
    await state.set_state(AdmDelSG.waiting)
    await safe_edit(cb.message, "O‘chiriladigan admin ID yuboring:", reply_markup=_admins_menu_kb(True))
    await cb.answer()

@admin_router.message(AdmDelSG.waiting)
async def admins_del_do(m: Message, state: FSMContext):
    if not (await is_super_admin(m.from_user.id)):
        return await m.answer("Faqat super admin o‘chira oladi.")
    try:
        uid = int((m.text or "").strip())
    except Exception:
        return await m.answer("ID noto‘g‘ri.")
    await remove_admin(uid)
    await state.clear()
    await m.answer("✅ O‘chirildi. /admin")

# ==================== REKLAMA / BROADCAST ====================
class BroadcastSG(StatesGroup):
    waiting = State()

@admin_router.callback_query(F.data == "ad_broadcast")
async def broadcast_start(cb: CallbackQuery, state: FSMContext):
    if not (await is_admin(cb.from_user.id)):
        return await cb.answer("Ruxsat yo‘q.")
    await state.set_state(BroadcastSG.waiting)
    await safe_edit(cb.message,
        "Reklama xabarini yuboring (matn / rasm / video / hujjat / audio / gif / *forward ham bo‘ladi*).\n"
        "Tugatish: /admin", reply_markup=back_only_kb("admin_back"))
    await cb.answer()

@admin_router.message(BroadcastSG.waiting)
async def broadcast_do(m: Message, state: FSMContext, bot: Bot):
    if not (await is_admin(m.from_user.id)):
        return await m.answer("Ruxsat yo‘q.")
    users = await fetch_all_user_ids()
    ok = 0; fail = 0
    for uid in users:
        try:
            await bot.copy_message(chat_id=uid, from_chat_id=m.chat.id, message_id=m.message_id)
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.05)  # throttling
    await state.clear()
    await m.answer(f"✅ Yuborildi: {ok} ta\n⚠️ Yuborilmadi: {fail} ta\n/admin")
