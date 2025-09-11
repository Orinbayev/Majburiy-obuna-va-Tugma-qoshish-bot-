from aiogram import Router
from aiogram.types import ChatJoinRequest
from utils.shared import user_join_requests

join_router = Router()

@join_router.chat_join_request()
async def handle_join_request(ev: ChatJoinRequest):
    uid = ev.from_user.id
    cid = str(ev.chat.id)
    user_join_requests.setdefault(uid, set()).add(cid)
    # xohlasang auto-approve: await ev.approve()
