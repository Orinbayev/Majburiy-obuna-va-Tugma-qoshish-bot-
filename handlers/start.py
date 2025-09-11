from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from db import upsert_user, list_buttons, list_button_contents, get_menu_cols
from utils.subscription import check_subscriptions, get_unsubscribed
from keyboards import subscribe_kb, main_menu_kb
from utils.telegram import safe_edit

start_router = Router()

WELCOME = (
    "Assalomu alaykum!\n"
    "Quyidagi majburiy kanallarga obuna bo‘ling. So‘ng «✅ Tekshirish» bosing."
)

async def _show_menu(chat, user_id: int):
    btns = await list_buttons()
    if not btns:
        await chat.answer("Menyu hali bo‘sh.")
        return
    cols = await get_menu_cols()
    kb = main_menu_kb(btns, cols)          # <-- BU YERDA AWAIT YO‘Q!
    await chat.answer("Menyu:", reply_markup=kb)

@start_router.message(CommandStart())
async def cmd_start(m: Message, bot: Bot):
    # foydalanuvchini ro‘yxatga olish
    await upsert_user(m.from_user)

    # majburiy obuna tekshiruvi
    if not await check_subscriptions(m.from_user.id, bot):
        need = await get_unsubscribed(m.from_user.id, bot)
        await m.answer(WELCOME, reply_markup=subscribe_kb(need))
        return

    await _show_menu(m, m.from_user.id)

@start_router.callback_query(F.data == "back_menu")
async def cb_back_menu(cb: CallbackQuery, bot: Bot):
    if not await check_subscriptions(cb.from_user.id, bot):
        need = await get_unsubscribed(cb.from_user.id, bot)
        await safe_edit(cb.message, WELCOME, reply_markup=subscribe_kb(need))
        return await cb.answer("Avval obuna bo‘ling.")
    kb = main_menu_kb(await list_buttons(), await get_menu_cols())
    await safe_edit(cb.message, "Menyu:", reply_markup=kb)
    await cb.answer("Menyu")

@start_router.callback_query(F.data == "check_sub")
async def cb_check_sub(cb: CallbackQuery, bot: Bot):
    if not await check_subscriptions(cb.from_user.id, bot):
        need = await get_unsubscribed(cb.from_user.id, bot)
        await safe_edit(cb.message, WELCOME, reply_markup=subscribe_kb(need))
        return await cb.answer("Hali hammasi emas.")
    kb = main_menu_kb(await list_buttons(), await get_menu_cols())
    await safe_edit(cb.message, "Menyu:", reply_markup=kb)
    await cb.answer("✅ Tekshirildi.")


from aiogram import Bot
from aiogram.types import CallbackQuery

MAX_TEXT = 4096        # text limit
MAX_CAPTION = 1024     # caption limit

def _chunks(s: str, n: int):
    for i in range(0, len(s), n):
        yield s[i:i+n]

@start_router.callback_query(F.data.startswith("open_btn:"))
async def open_button(cb: CallbackQuery, bot: Bot):
    btn_id = int(cb.data.split(":", 1)[1])
    contents = await list_button_contents(btn_id)
    if not contents:
        await cb.answer("Bu tugmada hozircha kontent yo‘q.", show_alert=False)
        return

    # Matn uchun (preview o‘chiriladi)
    text_kwargs = dict(parse_mode=None, disable_web_page_preview=True)
    # Media uchun (preview parametri yo‘q!)
    media_kwargs = dict(parse_mode=None)

    for _id, mtype, file_id, caption in contents:
        text = (caption or "").strip()

        if mtype == "text":
            for part in _chunks(text or " ", MAX_TEXT):
                await cb.message.answer(part, **text_kwargs)

        elif mtype == "photo":
            if text and len(text) > MAX_CAPTION:
                await bot.send_photo(cb.from_user.id, file_id, **media_kwargs)
                for part in _chunks(text, MAX_TEXT):
                    await cb.message.answer(part, **text_kwargs)
            else:
                await bot.send_photo(cb.from_user.id, file_id, caption=(text or None), **media_kwargs)

        elif mtype == "video":
            if text and len(text) > MAX_CAPTION:
                await bot.send_video(cb.from_user.id, file_id, **media_kwargs)
                for part in _chunks(text, MAX_TEXT):
                    await cb.message.answer(part, **text_kwargs)
            else:
                await bot.send_video(cb.from_user.id, file_id, caption=(text or None), **media_kwargs)

        elif mtype == "document":
            if text and len(text) > MAX_CAPTION:
                await bot.send_document(cb.from_user.id, file_id, **media_kwargs)
                for part in _chunks(text, MAX_TEXT):
                    await cb.message.answer(part, **text_kwargs)
            else:
                await bot.send_document(cb.from_user.id, file_id, caption=(text or None), **media_kwargs)

        elif mtype == "audio":
            if text and len(text) > MAX_CAPTION:
                await bot.send_audio(cb.from_user.id, file_id, **media_kwargs)
                for part in _chunks(text, MAX_TEXT):
                    await cb.message.answer(part, **text_kwargs)
            else:
                await bot.send_audio(cb.from_user.id, file_id, caption=(text or None), **media_kwargs)

        elif mtype == "animation":
            if text and len(text) > MAX_CAPTION:
                await bot.send_animation(cb.from_user.id, file_id, **media_kwargs)
                for part in _chunks(text, MAX_TEXT):
                    await cb.message.answer(part, **text_kwargs)
            else:
                await bot.send_animation(cb.from_user.id, file_id, caption=(text or None), **media_kwargs)

        else:
            # noma’lum tur — matn sifatida yuboramiz
            for part in _chunks(text or "Qo‘llanmagan tur.", MAX_TEXT):
                await cb.message.answer(part, **text_kwargs)

    await cb.answer()