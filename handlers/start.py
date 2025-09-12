# handlers/start.py
from __future__ import annotations
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from db import (
    upsert_user, get_menu_cols,
    list_buttons, find_button_by_title, has_children,
    list_button_contents, get_button_parent,
    is_admin, bootstrap_super_admin
)
from utils.subscription import check_subscriptions, get_unsubscribed
from keyboards import subscribe_kb, reply_menu_kb, admin_menu_kb

start_router = Router()

WELCOME = (
    "Assalomu alaykum!\n"
    "Quyidagi majburiy kanallarga obuna bo‘ling. So‘ng «✅ Tekshirish» bosing."
)

MAX_TEXT = 4096
MAX_CAPTION = 1024


def _chunks(s: str, n: int):
    for i in range(0, len(s), n):
        yield s[i:i+n]


class NavSG(StatesGroup):
    here = State()  # current parent_id (None = root)


async def _show_level(chat: Message, parent_id: int | None):
    cols = await get_menu_cols()
    btns = await list_buttons(parent_id)
    kb = reply_menu_kb(btns, cols, with_back=(parent_id is not None))
    await chat.answer("Menyu:", reply_markup=kb)


async def _guard_sub_msg(m: Message, bot: Bot) -> bool:
    """
    Har safar tugma bosilganda yoki /start chaqirilganda obunani tekshiradi.
    Obuna bo'lmasa – Subscribe oynasini ko'rsatadi va Reply-klaviaturani olib tashlaydi.
    """
    ok = await check_subscriptions(m.from_user.id, bot)
    if ok:
        return True
    need = await get_unsubscribed(m.from_user.id, bot)
    # Reply keyboardni olib tashlaymiz, subscribe inline klaviatura yuboramiz
    await m.answer(WELCOME, reply_markup=ReplyKeyboardRemove())
    await m.answer("👇 Majburiy kanallar:", reply_markup=subscribe_kb(need))
    return False


async def _guard_sub_cb(cb: CallbackQuery, bot: Bot) -> bool:
    """
    Callback (✅ Tekshirish) uchun guard.
    """
    ok = await check_subscriptions(cb.from_user.id, bot)
    if ok:
        return True
    need = await get_unsubscribed(cb.from_user.id, bot)
    # shu eski xabarni tahrirlab turamiz (inline markup uchun)
    try:
        await cb.message.edit_text(WELCOME, reply_markup=subscribe_kb(need))
    except Exception:
        # agar edit bo'lmasa, yangisini yuboramiz
        await cb.message.answer(WELCOME, reply_markup=subscribe_kb(need))
    await cb.answer("Hali hammasi emas.")
    return False


@start_router.message(CommandStart())
async def cmd_start(m: Message, bot: Bot, state: FSMContext):
    await upsert_user(m.from_user)
    if not await _guard_sub_msg(m, bot):
        return
    await state.set_state(NavSG.here)
    await state.update_data(parent_id=None)
    await _show_level(m, None)


@start_router.message(NavSG.here, F.text == "⬅️ Orqaga")
async def go_back(m: Message, state: FSMContext, bot: Bot):
    if not await _guard_sub_msg(m, bot):
        return
    d = await state.get_data()
    current = d.get("parent_id")
    up_id = await get_button_parent(current) if current is not None else None
    await state.update_data(parent_id=up_id)
    await _show_level(m, up_id)


@start_router.message(NavSG.here, F.text)
async def handle_press(m: Message, state: FSMContext, bot: Bot):
    # Har bosishda obuna tekshiruvi
    if not await _guard_sub_msg(m, bot):
        return

    d = await state.get_data()
    parent_id = d.get("parent_id")
    title = (m.text or "").strip()

    found = await find_button_by_title(parent_id, title)
    if not found:
        # nomi bo'yicha topilmasa, shu darajadagi menyuni qayta ko'rsatamiz
        return await _show_level(m, parent_id)

    bid, _ = found
    if await has_children(bid):
        await state.update_data(parent_id=bid)
        return await _show_level(m, bid)

    # leaf -> kontent yuborishdan oldin ham ehtiyot uchun tekshiramiz
    if not await _guard_sub_msg(m, bot):
        return

    items = await list_button_contents(bid)
    if not items:
        return await m.answer("Bu tugmada hozircha kontent yo‘q.")

    text_kwargs = dict(parse_mode=None, disable_web_page_preview=True)
    media_kwargs = dict(parse_mode=None)

    for _id, mtype, file_id, caption in items:
        text = (caption or "").strip()

        if mtype == "text":
            for part in _chunks(text or " ", MAX_TEXT):
                await m.answer(part, **text_kwargs)

        elif mtype == "photo":
            if text and len(text) > MAX_CAPTION:
                await bot.send_photo(m.chat.id, file_id, **media_kwargs)
                for part in _chunks(text, MAX_TEXT):
                    await m.answer(part, **text_kwargs)
            else:
                await bot.send_photo(m.chat.id, file_id, caption=(text or None), **media_kwargs)

        elif mtype == "video":
            if text and len(text) > MAX_CAPTION:
                await bot.send_video(m.chat.id, file_id, **media_kwargs)
                for part in _chunks(text, MAX_TEXT):
                    await m.answer(part, **text_kwargs)
            else:
                await bot.send_video(m.chat.id, file_id, caption=(text or None), **media_kwargs)

        elif mtype == "document":
            if text and len(text) > MAX_CAPTION:
                await bot.send_document(m.chat.id, file_id, **media_kwargs)
                for part in _chunks(text, MAX_TEXT):
                    await m.answer(part, **text_kwargs)
            else:
                await bot.send_document(m.chat.id, file_id, caption=(text or None), **media_kwargs)

        elif mtype == "audio":
            if text and len(text) > MAX_CAPTION:
                await bot.send_audio(m.chat.id, file_id, **media_kwargs)
                for part in _chunks(text, MAX_TEXT):
                    await m.answer(part, **text_kwargs)
            else:
                await bot.send_audio(m.chat.id, file_id, caption=(text or None), **media_kwargs)

        elif mtype == "animation":
            if text and len(text) > MAX_CAPTION:
                await bot.send_animation(m.chat.id, file_id, **media_kwargs)
                for part in _chunks(text, MAX_TEXT):
                    await m.answer(part, **text_kwargs)
            else:
                await bot.send_animation(m.chat.id, file_id, caption=(text or None), **media_kwargs)

        else:
            for part in _chunks(text or "Qo‘llanmagan tur.", MAX_TEXT):
                await m.answer(part, **text_kwargs)


# ✅ Tekshirish tugmasi (inline)
@start_router.callback_query(F.data == "check_sub")
async def cb_check_sub(cb: CallbackQuery, bot: Bot, state: FSMContext):
    if not await _guard_sub_cb(cb, bot):
        return
    # Obuna bo‘ldi -> Reply keyboard menyuga qaytaramiz
    # (inline xabarni o‘chirib, yangi "Menyu" yuboramiz)
    try:
        await cb.message.delete()
    except Exception:
        pass

    # joriy joyni tiklaymiz
    d = await state.get_data()
    parent_id = d.get("parent_id", None)
    await _show_level(cb.message, parent_id)
    await cb.answer("✅ Tekshirildi.")


# /admin har qanday holatda ham ishlashi uchun:
@start_router.message(NavSG.here, Command("admin"))
async def admin_from_state(m: Message, state: FSMContext):
    await bootstrap_super_admin(m.from_user.id, m.from_user.full_name)
    if not await is_admin(m.from_user.id):
        return await m.answer("Bu bo‘lim faqat adminlar uchun.")
    await state.clear()
    await m.answer("Admin panel:", reply_markup=admin_menu_kb())

@start_router.message(Command("admin"))
async def admin_any(m: Message, state: FSMContext):
    await bootstrap_super_admin(m.from_user.id, m.from_user.full_name)
    if not await is_admin(m.from_user.id):
        return await m.answer("Bu bo‘lim faqat adminlar uchun.")
    await state.clear()
    await m.answer("Admin panel:", reply_markup=admin_menu_kb())
