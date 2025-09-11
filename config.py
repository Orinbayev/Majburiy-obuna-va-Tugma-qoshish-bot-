# config.py
import os
from dotenv import load_dotenv
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

load_dotenv()  # .env ni yuklaydi

def _parse_admins(val: str) -> set[int]:
    if not val:
        return set()
    parts = [p.strip() for p in val.replace(" ", "").split(",") if p.strip()]
    out = set()
    for p in parts:
        try:
            out.add(int(p))
        except ValueError:
            pass
    return out

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN .env da topilmadi!")

ADMINS = _parse_admins(os.getenv("ADMINS", ""))
SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", "0") or 0)

DB_PATH = os.getenv("DB_PATH", "db.sqlite3")

_parse_mode = os.getenv("PARSE_MODE", "HTML").upper()
if _parse_mode not in ("HTML", "MARKDOWN", "MARKDOWNV2"):
    _parse_mode = "HTML"

DEFAULT_BOT_PROPERTIES = DefaultBotProperties(
    parse_mode=getattr(ParseMode, _parse_mode)
)
