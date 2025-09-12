# bot.py
import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# .env ni yuklaymiz (lokal ishga tushirish uchun)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Routerlar
from handlers.start import start_router
from handlers.admin import admin_router

# DB init
from db import init_db, bootstrap_super_admin

def get_token_and_props():
    """
    BOT_TOKEN ni quyidagi tartibda olish:
    1) .env / OS environment: BOT_TOKEN
    2) config.py dagi BOT_TOKEN
    DefaultBotProperties ham config.py dan o‘qiladi, bo‘lmasa HTML qo‘yamiz.
    """
    token = os.getenv("BOT_TOKEN")

    default_props = DefaultBotProperties(parse_mode=ParseMode.HTML)

    # config.py bo‘lsa, undan ham o‘qib ko‘ramiz
    try:
        import config
        if not token:
            token = getattr(config, "BOT_TOKEN", None)
        cfg_props = getattr(config, "DEFAULT_BOT_PROPERTIES", None)
        if cfg_props:
            default_props = cfg_props
    except Exception:
        pass

    if not isinstance(token, str) or not token.strip():
        raise RuntimeError(
            "BOT_TOKEN topilmadi. .env faylingizga BOT_TOKEN=XXXX qo‘ying "
            "yoki config.py ichida BOT_TOKEN = 'XXXX' bo‘lishi kerak."
        )

    return token, default_props

async def main():
    # DB jadvallarini yaratamiz
    await init_db()

    # Token va default parse_mode
    token, default_props = get_token_and_props()

    bot = Bot(token=token, default=default_props)
    dp = Dispatcher()

    # Routerlar
    dp.include_router(start_router)
    dp.include_router(admin_router)

    # Agar SUPER_ADMIN_ID environmentda bo‘lsa — bazaga belgilab qo‘yamiz
    super_id = os.getenv("SUPER_ADMIN_ID")
    if super_id:
        # ismi ixtiyoriy, keyin ham o‘zgartirsa bo‘ladi
        await bootstrap_super_admin(super_id, name="SuperAdmin")

    print("Bot ishga tushdi.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
