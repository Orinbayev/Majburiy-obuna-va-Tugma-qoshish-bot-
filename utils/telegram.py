# utils/telegram.py
from aiogram.exceptions import TelegramBadRequest

async def safe_edit(message, text: str, reply_markup=None, parse_mode="HTML"):
    """
    .edit_text() da 'message is not modified' xatosini yutib yuboradi.
    """
    try:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except TelegramBadRequest as e:
        # xuddi shu matn/markup bo‘lsa – jim
        if "message is not modified" in str(e).lower():
            return
        raise
