"""
beataniversebot_compat.py
==========================
Compatibility shim — BeatVerse modules import from 'BeatVerseProbot' package.
This file re-exports everything they need from the flat bot.py globals + database_dual.

All modules that had:  from BeatVerseProbot import X
now get:               from beataniversebot_compat import X
"""

import os
import logging
import time

# ── Bot identity (populated after bot starts) ─────────────────────────────────
BOT_ID: int = 0
BOT_NAME: str = os.getenv("BOT_NAME", "BeatAniVerse Bot")
BOT_USERNAME: str = ""

# ── Owner / privilege levels ──────────────────────────────────────────────────
OWNER_ID: int = int(os.getenv("OWNER_ID", "0") or "0")
ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0") or os.getenv("OWNER_ID", "0"))

_dragons_raw = os.getenv("DRAGONS", "")
_dev_raw     = os.getenv("DEV_USERS", "")
_demons_raw  = os.getenv("DEMONS", "")
_tigers_raw  = os.getenv("TIGERS", "")
_wolves_raw  = os.getenv("WOLVES", "")

def _ids(s): return [int(x.strip()) for x in s.split() if x.strip().lstrip('-').isdigit()]

DRAGONS:   list = _ids(_dragons_raw) + [OWNER_ID, ADMIN_ID]
DEV_USERS: list = _ids(_dev_raw)     + [OWNER_ID, ADMIN_ID]
DEMONS:    list = _ids(_demons_raw)
TIGERS:    list = _ids(_tigers_raw)
WOLVES:    list = _ids(_wolves_raw)

# ── Database URIs ─────────────────────────────────────────────────────────────
DB_URI:       str = os.getenv("DATABASE_URL", "")
MONGO_DB_URI: str = os.getenv("MONGO_DB_URI", "")

# ── Bot settings ──────────────────────────────────────────────────────────────
ALLOW_CHATS: bool = bool(os.getenv("ALLOW_CHATS", "True"))
ALLOW_EXCL:  bool = bool(os.getenv("ALLOW_EXCL",  "True"))
DEL_CMDS:    bool = bool(os.getenv("DEL_CMDS",    "True"))
STRICT_GBAN: bool = bool(os.getenv("STRICT_GBAN", "True"))
EVENT_LOGS:  int  = int(os.getenv("EVENT_LOGS", "0") or "0") or None
SUPPORT_CHAT: str = os.getenv("SUPPORT_CHAT", "Beat_Anime_Discussion")
INFOPIC:     bool = True
START_IMG:   str  = os.getenv("START_IMG", "https://telegra.ph/file/40eb1ed850cdea274693e.jpg")
TEMP_DOWNLOAD_DIRECTORY: str = os.getenv("TEMP_DOWNLOAD_DIRECTORY", "./")
WORKERS:     int  = int(os.getenv("WORKERS", "8"))
LOAD:        list = []
NO_LOAD:     list = os.getenv("NO_LOAD", "").split()

# ── Timing ────────────────────────────────────────────────────────────────────
StartTime: float = time.time()

# ── Logger ────────────────────────────────────────────────────────────────────
LOGGER = logging.getLogger("BeatAniVerse")

# ── Pyrogram / Telethon clients (stubs - real clients are in bot.py) ─────────
# Modules that use pbot (Pyrogram) for things like /couple will get the real
# client injected after bot.py starts.
class _StubClient:
    """Stub so modules don't crash at import time if pbot isn't set yet."""
    async def send_message(self, *a, **kw): pass
    async def get_users(self, *a, **kw):
        class _U:
            mention = "Unknown"
        return _U()
    async def get_chat_members(self, *a, **kw):
        return []
    def on_message(self, *a, **kw):
        def decorator(func): return func
        return decorator
    def on_callback_query(self, *a, **kw):
        def decorator(func): return func
        return decorator
    def add_event_handler(self, *a, **kw): pass   # Fix: purge module
    def add_handler(self, *a, **kw): pass          # Fix: various modules
    async def iter_chat_members(self, *a, **kw): return iter([])

pbot = _StubClient()
telethn = _StubClient()

# ── Missing API keys expected by some modules ──────────────────────────────────
CASH_API_KEY: str = os.getenv("CASH_API_KEY", "")
TIME_API_KEY: str = os.getenv("TIME_API_KEY", "")

# ── CustomCommandHandler (used by cleaner module) ─────────────────────────────
try:
    from telegram.ext import CommandHandler as _BaseCommandHandler
    class CustomCommandHandler(_BaseCommandHandler):
        """PTB v13 CustomCommandHandler compat stub."""
        def __init__(self, *args, **kwargs):
            kwargs.pop('run_async', None)
            super().__init__(*args, **kwargs)
except Exception:
    CustomCommandHandler = None

# ── Telegram dispatcher (set by bot.py after startup) ─────────────────────────
dispatcher = None

def _set_dispatcher(dp):
    global dispatcher
    dispatcher = dp

def _set_pbot(client):
    global pbot
    pbot = client

def _set_telethn(client):
    global telethn
    telethn = client

def _set_bot_info(bot_id, bot_name, bot_username):
    global BOT_ID, BOT_NAME, BOT_USERNAME
    BOT_ID = bot_id
    BOT_NAME = bot_name
    BOT_USERNAME = bot_username
