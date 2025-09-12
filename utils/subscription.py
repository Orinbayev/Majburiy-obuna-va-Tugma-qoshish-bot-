# utils/subscription.py
from __future__ import annotations
from typing import List, Tuple, Optional
from aiogram import Bot
from aiogram.enums import ChatMemberStatus

from db import list_channels_full

async def _is_subscribed(bot: Bot, user_id: int, chat_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
    except Exception:
        return False
    status = getattr(member, "status", None)
    return status in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR)

async def check_subscriptions(user_id: int, bot: Bot) -> bool:
    rows = await list_channels_full()
    if not rows:
        return True
    for chat_id, *_ in rows:
        try:
            cid = int(chat_id)
        except Exception:
            return False
        if not await _is_subscribed(bot, user_id, cid):
            return False
    return True

async def get_unsubscribed(user_id: int, bot: Bot) -> List[Tuple[str, Optional[str], Optional[str], Optional[str], Optional[str]]]:
    rows = await list_channels_full()
    need: List[Tuple[str, Optional[str], Optional[str], Optional[str], Optional[str]]] = []
    for chat_id, title, username, invite_link, url in rows:
        try:
            cid = int(chat_id)
        except Exception:
            need.append((str(chat_id), title, username, invite_link, url))
            continue
        if not await _is_subscribed(bot, user_id, cid):
            need.append((str(chat_id), title, username, invite_link, url))
    return need
