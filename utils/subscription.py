# utils/subscription.py

from __future__ import annotations
from typing import List, Tuple, Optional
from aiogram import Bot
from aiogram.enums import ChatMemberStatus

from db import list_channels_full  # faqat shu kerak

# --- ichki yordamchi ---
async def _is_subscribed(bot: Bot, user_id: int, chat_id: int) -> bool:
    """
    Foydalanuvchi kanalga obuna bo‘lganmi-yo‘qmi.
    Bot kanalga admin/kirishga ega bo‘lishi shart, aks holda False qaytadi.
    """
    try:
        member = await bot.get_chat_member(chat_id, user_id)
    except Exception:
        return False

    status = getattr(member, "status", None)
    return status in (
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.CREATOR,
    )

async def check_subscriptions(user_id: int, bot: Bot) -> bool:
    """
    Barcha saqlangan majburiy kanallar bo‘yicha tekshiradi.
    Hech bo‘lmaganda bitta kanalga obuna bo‘lmagan bo‘lsa — False.
    Kanallar bo‘lmasa True (tekshiradigan narsa yo‘q).
    """
    rows = await list_channels_full()
    if not rows:
        return True

    for chat_id, title, username, invite_link, url in rows:
        try:
            cid = int(chat_id)
        except Exception:
            # Noto'g'ri ID bo'lsa: tekshirib bo'lmaydi -> obuna emas deb qaraymiz
            return False

        ok = await _is_subscribed(bot, user_id, cid)
        if not ok:
            return False

    return True


async def get_unsubscribed(user_id: int, bot: Bot) -> List[Tuple[str, Optional[str], Optional[str], Optional[str], Optional[str]]]:
    """
    Obuna bo‘lmagan kanallar ro‘yxatini qaytaradi:
    (chat_id, title, username, invite_link, url)
    """
    rows = await list_channels_full()
    need: List[Tuple[str, Optional[str], Optional[str], Optional[str], Optional[str]]] = []

    for chat_id, title, username, invite_link, url in rows:
        try:
            cid = int(chat_id)
        except Exception:
            # ID noto‘g‘ri bo‘lsa ham, foydalanuvchiga ko‘rsatish uchun qo‘shamiz
            need.append((str(chat_id), title, username, invite_link, url))
            continue

        if not await _is_subscribed(bot, user_id, cid):
            need.append((str(chat_id), title, username, invite_link, url))

    return need
