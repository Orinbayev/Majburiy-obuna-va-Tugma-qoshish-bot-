import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN, DEFAULT_BOT_PROPERTIES
from db import init_db, add_admin
from handlers.start import start_router
from handlers.admin import admin_router
from handlers.join_requests import join_router
from config import ADMINS

async def main():
    logging.basicConfig(level=logging.INFO)
    await init_db()
    for a in ADMINS:
        try:
            await add_admin(int(a))
        except:
            pass
    bot = Bot(token=BOT_TOKEN, default=DEFAULT_BOT_PROPERTIES)
    dp = Dispatcher()
    dp.include_router(join_router)
    dp.include_router(start_router)
    dp.include_router(admin_router)
    print("Bot ishga tushdi.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
