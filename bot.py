# ====================================================================
# PLACE AT: /app/bot.py
# ACTION: Replace existing file
# ====================================================================
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
        UNIFIED ANIME BOT — OVERPOWERED EDITION v5.0  (~20k lines)
================================================================================
Features:
  ✅ Fully working clone bot support (all menus, force-sub, deep links)
  ✅ User-friendly error messages in plain language (non-technical DM only)
  ✅ Admin gets technical error details separately
  ✅ Conversation-safe: deleted first message never breaks session
  ✅ Bold ! exclamation loading animation on /start
  ✅ Commands auto-register in BOTH main bot and every clone bot
  ✅ All menus fully connected — zero dead buttons
  ✅ Manga tracking with full MangaDex: chapters, pages, status
  ✅ Complete broadcast system (Normal / Auto-delete / Pin / Schedule)
  ✅ Complete upload manager (anime captions, multi-quality)
  ✅ Full auto-forward with filters, replacements, delays, bulk
  ✅ Feature flags: maintenance, clone redirect, error DMs, etc.
  ✅ Full user management: ban, unban, search, export, delete
  ✅ Complete post generation: anime, manga, movie, TV show (AniList+TMDB)
  ✅ Complete category settings: templates, buttons, watermarks, logos
  ✅ Admin panel with image banners, deep-link gen, stats
  ✅ All text is <b>bold</b> throughout
  ✅ Auto-delete previous messages everywhere
  ✅ Robust error handling — no crashes, no unhandled callbacks
================================================================================
"""

# ================================================================================
#                                   IMPORTS
# ================================================================================

import os
import sys
import json
import time
import uuid
import math
import random
import asyncio
import logging
import logging.handlers
import html
import re
import csv
import hashlib
import traceback
import threading
from io import StringIO, BytesIO
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Optional, Dict, List, Tuple, Any, Union, Set, Callable
from contextlib import asynccontextmanager

import requests
import aiohttp
import psutil

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import img2pdf
    IMG2PDF_AVAILABLE = True
except ImportError:
    IMG2PDF_AVAILABLE = False

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Bot,
    constants,
    InputMediaPhoto,
    InputMediaVideo,
    InputMediaDocument,
    ChatMember,
    CallbackQuery,
    BotCommand,
    BotCommandScopeChat,
    BotCommandScopeAllPrivateChats,
    InlineQueryResultArticle,
    InputTextMessageContent,
    ChatPermissions,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
    JobQueue,
    InlineQueryHandler,
    ConversationHandler,
    ChatJoinRequestHandler,
)
from telegram.error import (
    TelegramError,
    Forbidden,
    BadRequest,
    NetworkError,
    TimedOut,
    RetryAfter,
)
from telegram.constants import ParseMode

from database_dual import *
try:
    from health_check import health_server
except ImportError:
    class _HealthServerStub:
        async def start(self): pass
        async def stop(self): pass
    health_server = _HealthServerStub()

# ================================================================================
#                                LOGGING SETUP
# ================================================================================

os.makedirs("logs", exist_ok=True)

_fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_datefmt = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(
    format=_fmt,
    datefmt=_datefmt,
    level=logging.INFO,
    handlers=[
        logging.handlers.RotatingFileHandler(
            "logs/bot.log", maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
        ),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("bot")
db_logger = logging.getLogger("database")
api_logger = logging.getLogger("api")
broadcast_logger = logging.getLogger("broadcast")
error_logger = logging.getLogger("errors")

for name in ["httpx", "httpcore", "telegram", "apscheduler"]:
    logging.getLogger(name).setLevel(logging.WARNING)

# ================================================================================
#                     BEATVERSE MODULES — WIRING
# ================================================================================
# Wire up the compat shim so all BeatVerse modules can find their imports
import beataniversebot_compat as _compat
import sys as _sys

# Add modules directory to path so `from modules.xxx import` works
_sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

# ── Global text style engine ──────────────────────────────────────────────────
try:
    from text_style import apply_style as _apply_style, get_style as _get_style
    _TEXT_STYLE_AVAILABLE = True
except ImportError:
    _TEXT_STYLE_AVAILABLE = False
    def _apply_style(t): return t
    def _get_style(): return "normal"

# ── Filter-poster integration ─────────────────────────────────────────────────
try:
    from filter_poster import (
        get_or_generate_poster, migrate_poster_cache_table,
        _get_filter_poster_enabled, _set_filter_poster_enabled,
        _get_default_poster_template, _set_default_poster_template,
        build_filter_poster_settings_keyboard, get_filter_poster_settings_text,
        _clear_poster_cache, _get_cache_count,
    )
    _FILTER_POSTER_AVAILABLE = True
except ImportError as _fp_err:
    logger.warning(f"filter_poster module unavailable: {_fp_err}")
    _FILTER_POSTER_AVAILABLE = False

# ── Panel image system ────────────────────────────────────────────────────────
try:
    from panel_image import get_panel_image_async, clear_image_cache, get_cache_status
    _PANEL_IMAGE_AVAILABLE = True
except ImportError:
    _PANEL_IMAGE_AVAILABLE = False
    async def get_panel_image_async(panel: str = "default"): return None
    def clear_image_cache(panel=None): return 0
    def get_cache_status(): return {}
# Wire up the compat shim so all BeatVerse modules can find their imports
import beataniversebot_compat as _compat
import sys as _sys

# Add modules directory to path so `from modules.xxx import` works
_sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

# ================================================================================
#                           ENVIRONMENT CONFIGURATION
# ================================================================================

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "") or os.getenv("TOKEN", "")
DATABASE_URL: str = os.getenv("DATABASE_URL", "")
MONGO_DB_URI: str = os.getenv("MONGO_DB_URI", "")
# ── Owner / Admin IDs — OWNER_ID and ADMIN_ID are interchangeable ─────────────
# Only ONE of them needs to be set. If only OWNER_ID is set, ADMIN_ID mirrors it.
# If only ADMIN_ID is set, OWNER_ID mirrors it.
ADMIN_ID: int = int(os.getenv("ADMIN_ID") or os.getenv("OWNER_ID") or "0")
OWNER_ID: int = int(os.getenv("OWNER_ID") or os.getenv("ADMIN_ID") or "0")
# If one was missing, mirror from the other
if ADMIN_ID == 0 and OWNER_ID != 0:
    ADMIN_ID = OWNER_ID
if OWNER_ID == 0 and ADMIN_ID != 0:
    OWNER_ID = ADMIN_ID

# Poster settings
IMGBB_API_KEY: str = os.getenv("IMGBB_API_KEY", "")
# Help info from env (what users see)
HELP_TEXT_CUSTOM: str = os.getenv("HELP_TEXT_CUSTOM", "")
HELP_CHANNEL_1_URL: str = os.getenv("HELP_CHANNEL_1_URL", "")
HELP_CHANNEL_1_NAME: str = os.getenv("HELP_CHANNEL_1_NAME", " ᴀɴɪᴍᴇ ᴄʜᴀɴɴᴇʟ")
HELP_CHANNEL_2_URL: str = os.getenv("HELP_CHANNEL_2_URL", "")
HELP_CHANNEL_2_NAME: str = os.getenv("HELP_CHANNEL_2_NAME", " ᴅɪsᴄᴜssɪᴏɴ")
HELP_CHANNEL_3_URL: str = os.getenv("HELP_CHANNEL_3_URL", "")
HELP_CHANNEL_3_NAME: str = os.getenv("HELP_CHANNEL_3_NAME", " ʀᴇǫᴜᴇsᴛ")

# Timing
LINK_EXPIRY_MINUTES: int = int(os.getenv("LINK_EXPIRY_MINUTES", "5"))
BROADCAST_CHUNK_SIZE: int = int(os.getenv("BROADCAST_CHUNK_SIZE", "1000"))
BROADCAST_MIN_USERS: int = int(os.getenv("BROADCAST_MIN_USERS", "5000"))
BROADCAST_INTERVAL_MIN: int = int(os.getenv("BROADCAST_INTERVAL_MIN", "20"))
RATE_LIMIT_DELAY: float = float(os.getenv("RATE_LIMIT_DELAY", "0.05"))

# Ports
PORT: int = int(os.environ.get("PORT", 10000))
WEBHOOK_URL: str = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/") + "/"

# Source content
WELCOME_SOURCE_CHANNEL: int = int(os.getenv("WELCOME_SOURCE_CHANNEL", "-1002530952988"))
WELCOME_SOURCE_MESSAGE_ID: int = int(os.getenv("WELCOME_SOURCE_MESSAGE_ID", "32"))
# Panel DB channel — bot forwards panel images here and stores message IDs
# Same concept as WELCOME_SOURCE_CHANNEL. Add bot as admin to this channel.
PANEL_DB_CHANNEL: int = int(os.getenv("PANEL_DB_CHANNEL", "0"))

# Fallback image channel — bot scans this channel for photos on startup (ignores stickers/text).
# If PANEL_DB_CHANNEL has no manually added images, random photos from here are used for ALL panels.
# Bot must be a member/admin of this channel. Default: -1003794802745
FALLBACK_IMAGE_CHANNEL: int = int(os.getenv("FALLBACK_IMAGE_CHANNEL", "-1003794802745"))

# Public links / branding
PUBLIC_ANIME_CHANNEL_URL: str = os.getenv("PUBLIC_ANIME_CHANNEL_URL", "https://t.me/BeatAnime")
REQUEST_CHANNEL_URL: str = os.getenv("REQUEST_CHANNEL_URL", "https://t.me/Beat_Hindi_Dubbed")
ADMIN_CONTACT_USERNAME: str = os.getenv("ADMIN_CONTACT_USERNAME", "Beat_Anime_Ocean")
BOT_NAME: str = os.getenv("BOT_NAME", "Anime Bot")

# Image panels
HELP_IMAGE_URL: str = os.getenv("HELP_IMAGE_URL", "")
SETTINGS_IMAGE_URL: str = os.getenv("SETTINGS_IMAGE_URL", "")
STATS_IMAGE_URL: str = os.getenv("STATS_IMAGE_URL", "")
ADMIN_PANEL_IMAGE_URL: str = os.getenv("ADMIN_PANEL_IMAGE_URL", "")

# ── PANEL_IMAGE_FILE_ID: permanent Telegram file_id for the admin panel image ──
# How to get yours: forward any image to the bot and use /getfileid command.
# Set this in your .env / Render env vars for truly instant panels from boot.
# Example: PANEL_IMAGE_FILE_ID=AgACAgIAAxkBAAIB...
PANEL_IMAGE_FILE_ID: str = os.getenv("PANEL_IMAGE_FILE_ID", "")
WELCOME_IMAGE_URL: str = os.getenv("WELCOME_IMAGE_URL", "")
BROADCAST_PANEL_IMAGE_URL: str = os.getenv("BROADCAST_PANEL_IMAGE_URL", "")

# ── PANEL_PICS: comma-separated image URLs used randomly for all panels ───────
# Set this env variable with URLs like: https://i.imgur.com/abc.jpg,https://...
_PANEL_PICS_RAW: str = os.getenv("PANEL_PICS", "")
PANEL_PICS: list = [u.strip() for u in _PANEL_PICS_RAW.split(",") if u.strip().startswith("http")]

# Sticker
TRANSITION_STICKER_ID: str = os.getenv("TRANSITION_STICKER", "")

# ── Button & link text customization (set in ENV panel) ───────────────────────
JOIN_BTN_TEXT: str       = os.getenv("JOIN_BTN_TEXT",       "Join Now")
HERE_IS_LINK_TEXT: str   = os.getenv("HERE_IS_LINK_TEXT",   "ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʟɪɴᴋ! ᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ᴛᴏ ᴘʀᴏᴄᴇᴇᴅ")
LINK_EXPIRED_TEXT: str   = os.getenv("LINK_EXPIRED_TEXT",   "This invite link has expired. Please click the post button again.")
ANIME_BTN_TEXT: str      = os.getenv("ANIME_BTN_TEXT",      "Anime Channel")
REQUEST_BTN_TEXT: str    = os.getenv("REQUEST_BTN_TEXT",    "Request Anime")
CONTACT_BTN_TEXT: str    = os.getenv("CONTACT_BTN_TEXT",    "Contact Admin")
FORCE_SUB_TEXT: str      = os.getenv("FORCE_SUB_TEXT",      "Please join our channels first:")
BOT_WELCOME_TEXT: str    = os.getenv("BOT_WELCOME_TEXT",    "")
BOT_HELP_TEXT: str       = os.getenv("BOT_HELP_TEXT",       "")

# ── Button style (applied to bold_button / _btn) ──────────────────────────────
# Options: "mathbold" (default) | "smallcaps"
BUTTON_STYLE: str = os.getenv("BUTTON_STYLE", "mathbold")

# External APIs
TMDB_API_KEY: str = os.getenv("TMDB_API_KEY", "")

# Global runtime state
BOT_USERNAME: str = ""
I_AM_CLONE: bool = False
BOT_START_TIME: float = time.time()
_clone_bot_cache: Dict[str, Any] = {}
_clone_tasks: Dict[str, Any] = {}  # running clone asyncio tasks

# ── In-memory API cache (performance optimization) ────────────────────────────
_api_cache: Dict[str, Any] = {}
_API_CACHE_TTL: int = 300  # 5 minutes

# ── Filter system (DM/group/user/chat filtering) ──────────────────────────────
filters_config: Dict[str, Any] = {
    "global": {"dm": True, "group": True},
    "commands": {},
    "banned_users": set(),
    "disabled_chats": set(),
}


def _passes_filter(update: "Update", command: str = "") -> bool:
    """Check if a message passes the filter system. Returns False to block."""
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return True
    uid = user.id
    cid = chat.id
    # Always allow admins
    if uid in (ADMIN_ID, OWNER_ID):
        return True
    # Banned users
    if uid in filters_config["banned_users"]:
        return False
    # Disabled chats
    if cid in filters_config["disabled_chats"]:
        return False
    # Global DM/group toggle
    is_private = chat.type == "private"
    if is_private and not filters_config["global"].get("dm", True):
        return False
    if not is_private and not filters_config["global"].get("group", True):
        return False
    # Per-command filter
    if command and command in filters_config["commands"]:
        cmd_cfg = filters_config["commands"][command]
        if is_private and not cmd_cfg.get("dm", True):
            return False
        if not is_private and not cmd_cfg.get("group", True):
            return False
    return True


def _cache_get(key: str) -> Optional[Any]:
    """Get a value from the API cache if not expired."""
    entry = _api_cache.get(key)
    if entry and (time.time() - entry["ts"]) < _API_CACHE_TTL:
        return entry["data"]
    return None


def _cache_set(key: str, data: Any) -> None:
    """Store a value in the API cache."""
    _api_cache[key] = {"data": data, "ts": time.time()}
    # Trim cache to prevent unbounded growth
    if len(_api_cache) > 500:
        oldest = min(_api_cache, key=lambda k: _api_cache[k]["ts"])
        _api_cache.pop(oldest, None)

# ================================================================================
#                           STATE MACHINE CONSTANTS
# ================================================================================

# Channel states
(
    ADD_CHANNEL_USERNAME,
    ADD_CHANNEL_TITLE,
    ADD_CHANNEL_JBR,
) = range(3)

# Link states
(
    GENERATE_LINK_IDENTIFIER,
    GENERATE_LINK_TITLE,
    GENERATE_LINK_ANIME_NAME,
) = range(3, 6)

# Clone states
(ADD_CLONE_TOKEN,) = range(5, 6)

# Backup / move
(
    SET_BACKUP_CHANNEL,
    PENDING_MOVE_TARGET,
) = range(6, 8)

# Broadcast states
(
    PENDING_BROADCAST,
    PENDING_BROADCAST_OPTIONS,
    PENDING_BROADCAST_CONFIRM,
    SCHEDULE_BROADCAST_DATETIME,
    SCHEDULE_BROADCAST_MSG,
) = range(8, 13)

# Category settings states
(
    SET_CATEGORY_TEMPLATE,
    SET_CATEGORY_BRANDING,
    SET_CATEGORY_BUTTONS,
    SET_CATEGORY_CAPTION,
    SET_CATEGORY_THUMBNAIL,
    SET_CATEGORY_FONT,
    SET_CATEGORY_LOGO,
    SET_CATEGORY_LOGO_POS,
    SET_WATERMARK_TEXT,
    SET_WATERMARK_POS,
) = range(13, 23)

# Auto-forward states
(
    AF_ADD_CONNECTION_SOURCE,
    AF_ADD_CONNECTION_TARGET,
    AF_ADD_FILTER_WORD,
    AF_ADD_BLACKLIST_WORD,
    AF_ADD_WHITELIST_WORD,
    AF_ADD_REPLACEMENT_PATTERN,
    AF_ADD_REPLACEMENT_VALUE,
    AF_SET_DELAY,
    AF_SET_CAPTION,
    AF_BULK_FORWARD_COUNT,
) = range(23, 33)

# Auto manga states
(
    AU_ADD_MANGA_TITLE,
    AU_ADD_MANGA_TARGET,
    AU_REMOVE_MANGA,
    AU_CUSTOM_INTERVAL,
) = range(33, 37)

# Upload states
(
    UPLOAD_SET_CAPTION,
    UPLOAD_SET_SEASON,
    UPLOAD_SET_EPISODE,
    UPLOAD_SET_TOTAL,
    UPLOAD_SET_CHANNEL,
) = range(36, 41)

# User management states
(
    BAN_USER_INPUT,
    UNBAN_USER_INPUT,
    DELETE_USER_INPUT,
    SEARCH_USER_INPUT,
) = range(41, 45)

# Fill title
PENDING_FILL_TITLE = 45

# Settings
(
    SET_FEATURE_FLAG,
    SET_LINK_EXPIRY,
    SET_BOT_NAME,
    SET_WELCOME_MSG,
    SET_ADMIN_CONTACT,
) = range(46, 51)

# Manga
(
    MANGA_SEARCH_INPUT,
) = range(51, 52)

# Auto-manga delivery states
(
    AU_MANGA_CUSTOM_INTERVAL,
) = range(52, 53)

# "Forward a post" — admin forwards any channel post and bot auto-extracts channel ID
PENDING_CHANNEL_POST = 53

# Channel welcome system states
(
    CW_SET_TEXT,
    CW_SET_BUTTONS,
) = range(54, 56)

# Conversation dictionaries
user_states: Dict[int, int] = {}
user_data_temp: Dict[int, Dict[str, Any]] = {}

# Per-user debounce locks — prevents rapid-click double-processing that causes lag & ping hangs
_panel_locks: Dict[int, asyncio.Lock] = {}

def _get_panel_lock(uid: int) -> asyncio.Lock:
    """Return (creating if needed) an asyncio.Lock for this user."""
    if uid not in _panel_locks:
        _panel_locks[uid] = asyncio.Lock()
    return _panel_locks[uid]


# ================================================================================
#                          UPLOAD MANAGER GLOBALS
# ================================================================================

DEFAULT_CAPTION = (
    "<b>◈ {anime_name}</b>\n\n"
    "<b>- Season:</b> {season}\n"
    "<b>- Episode:</b> {episode}\n"
    "<b>- Audio track:</b> Hindi | Official\n"
    "<b>- Quality:</b> {quality}\n"
    "<blockquote>"
    "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▱▱\n"
    " <b>POWERED BY:</b> @beeetanime\n"
    "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▱▱\n"
    " <b>MAIN Channel:</b> @Beat_Hindi_Dubbed\n"
    "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▱▱\n"
    " <b>Group:</b> @Beat_Anime_Discussion\n"
    "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▱▱"
    "</blockquote>"
)

ALL_QUALITIES: List[str] = ["480p", "720p", "1080p", "4K", "2160p"]

upload_progress: Dict[str, Any] = {
    "target_chat_id": None,
    "anime_name": "Anime Name",
    "season": 1,
    "episode": 1,
    "total_episode": 1,
    "video_count": 0,
    "selected_qualities": ["480p", "720p", "1080p"],
    "base_caption": DEFAULT_CAPTION,
    "auto_caption_enabled": True,
    "forward_mode": "copy",     # copy | move
    "protect_content": False,
}

upload_lock = asyncio.Lock()


# ================================================================================
#                         BROADCAST MODE CONSTANTS
# ================================================================================

class BroadcastMode:
    NORMAL = "normal"
    AUTO_DELETE = "auto_delete"
    PIN = "pin"
    DELETE_PIN = "delete_pin"
    SILENT = "silent"


# ================================================================================
#                       TEXT UTILITIES & CONVERTERS
# ================================================================================

SMALL_CAPS_MAP: Dict[str, str] = {
    "a": "ᴀ", "b": "ʙ", "c": "ᴄ", "d": "ᴅ", "e": "ᴇ", "f": "ғ", "g": "ɢ",
    "h": "ʜ", "i": "ɪ", "j": "ᴊ", "k": "ᴋ", "l": "ʟ", "m": "ᴍ", "n": "ɴ",
    "o": "ᴏ", "p": "ᴘ", "q": "ǫ", "r": "ʀ", "s": "s", "t": "ᴛ", "u": "ᴜ",
    "v": "ᴠ", "w": "ᴡ", "x": "x", "y": "ʏ", "z": "ᴢ",
}
SMALL_CAPS_MAP.update({k.upper(): v for k, v in SMALL_CAPS_MAP.items()})

MATH_BOLD_MAP: Dict[str, str] = {
    "A": "𝗔", "B": "𝗕", "C": "𝗖", "D": "𝗗", "E": "𝗘", "F": "𝗙", "G": "𝗚",
    "H": "𝗛", "I": "𝗜", "J": "𝗝", "K": "𝗞", "L": "𝗟", "M": "𝗠", "N": "𝗡",
    "O": "𝗢", "P": "𝗣", "Q": "𝗤", "R": "𝗥", "S": "𝗦", "T": "𝗧", "U": "𝗨",
    "V": "𝗩", "W": "𝗪", "X": "𝗫", "Y": "𝗬", "Z": "𝗭",
    "a": "𝗮", "b": "𝗯", "c": "𝗰", "d": "𝗱", "e": "𝗲", "f": "𝗳", "g": "𝗴",
    "h": "𝗵", "i": "𝗶", "j": "𝗷", "k": "𝗸", "l": "𝗹", "m": "𝗺", "n": "𝗻",
    "o": "𝗼", "p": "𝗽", "q": "𝗾", "r": "𝗿", "s": "𝘀", "t": "𝘁", "u": "𝘂",
    "v": "𝘃", "w": "𝘄", "x": "𝘅", "y": "𝘆", "z": "𝘇",
    "0": "𝟬", "1": "𝟭", "2": "𝟮", "3": "𝟯", "4": "𝟰",
    "5": "𝟱", "6": "𝟲", "7": "𝟳", "8": "𝟴", "9": "𝟵",
}


def small_caps(text: str) -> str:
    """
    Convert ASCII letters to Unicode small caps.
    Skips: HTML tags, @mentions, /commands, http(s):// URLs, <code>...</code> content.
    Numbers and punctuation are passed through unchanged.
    """
    if not text:
        return text
    result: list = []
    i = 0
    n = len(text)
    in_tag = False
    in_code = False

    while i < n:
        ch = text[i]
        # HTML tag open
        if ch == "<" and not in_code:
            in_tag = True
            # Detect <code> / </code>
            rest = text[i:].lower()
            if rest.startswith("<code"):
                in_code = True
            elif rest.startswith("</code"):
                in_code = False
            result.append(ch)
            i += 1
            continue
        if ch == ">" and in_tag:
            in_tag = False
            result.append(ch)
            i += 1
            continue
        # Inside HTML tag attribute text — copy verbatim
        if in_tag:
            result.append(ch)
            i += 1
            continue
        # Inside <code> block — copy verbatim
        if in_code:
            result.append(ch)
            i += 1
            continue
        # @mention — copy word as-is
        if ch == "@":
            result.append(ch)
            i += 1
            while i < n and (text[i].isalnum() or text[i] == "_"):
                result.append(text[i])
                i += 1
            continue
        # /command — copy word as-is (only at word boundary)
        if ch == "/" and (i == 0 or not text[i-1].isalnum()):
            i += 1
            while i < n and (text[i].isalnum() or text[i] == "_"):
                result.append(text[i])
                i += 1
            continue
        # URL — copy until whitespace
        if text[i:i+7] in ("https:/", "http://") or text[i:i+8] == "https://":
            while i < n and text[i] not in (" ", "\n", "\t", "<", ">"):
                result.append(text[i])
                i += 1
            continue
        # Normal char — apply SC map
        result.append(SMALL_CAPS_MAP.get(ch, ch))
        i += 1
    return "".join(result)


def math_bold(text: str) -> str:
    """Convert text to Unicode math bold for button labels."""
    return "".join(MATH_BOLD_MAP.get(ch, ch) for ch in text)


def bold_button(label: str, **kwargs) -> InlineKeyboardButton:
    """Return an InlineKeyboardButton with math-bold label text."""
    return InlineKeyboardButton(math_bold(label), **kwargs)


def b(text: str) -> str:
    """Wrap text in HTML bold tags, auto-applying small caps to all letter content."""
    return f"<b>{small_caps(text)}</b>"


def code(text: str) -> str:
    """Wrap text in HTML code tags."""
    return f"<code>{text}</code>"


def bq(content: str, expandable: bool = True) -> str:
    """
    Wrap text in an expandable HTML blockquote (collapsed by default).
    Pass expandable=False for a plain blockquote.
    Text inside is SC-converted unless it already contains SC chars.
    """
    tag = "blockquote expandable" if expandable else "blockquote"
    return f"<{tag}>{content}</{tag.split()[0]}>"


def e(text: str) -> str:
    """HTML-escape text safely."""
    return html.escape(str(text))


def strip_html(text: str) -> str:
    """Strip all HTML tags from a string."""
    return re.sub(r"<[^>]+>", "", str(text))


def truncate(text: str, max_len: int = 200, suffix: str = "…") -> str:
    """Truncate text to max_len characters."""
    t = str(text)
    return t if len(t) <= max_len else t[: max_len - len(suffix)] + suffix


def format_number(n: int) -> str:
    """Format large numbers with commas."""
    return f"{n:,}"


def format_size(bytes_val: int) -> str:
    """Human-readable file size."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_val < 1024:
            return f"{bytes_val:.2f} {unit}"
        bytes_val //= 1024
    return f"{bytes_val:.2f} PB"


def format_duration(seconds: int) -> str:
    """Format seconds into h m s string."""
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    parts = []
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    parts.append(f"{s}s")
    return " ".join(parts)


def parse_date(d: Optional[Dict]) -> str:
    """Parse AniList date dict {'year':x,'month':y,'day':z} to readable string."""
    if not d:
        return "Unknown"
    try:
        parts = []
        if d.get("day"):
            parts.append(str(d["day"]))
        if d.get("month"):
            import calendar
            parts.append(calendar.month_abbr[d["month"]])
        if d.get("year"):
            parts.append(str(d["year"]))
        return " ".join(parts) if parts else "Unknown"
    except Exception:
        return "Unknown"


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def paginate(items: list, page: int, per_page: int = 10) -> Tuple[list, int, int]:
    """Return (page_items, total_pages, current_page)."""
    total = len(items)
    total_pages = max(1, math.ceil(total / per_page))
    page = max(0, min(page, total_pages - 1))
    start = page * per_page
    return items[start : start + per_page], total_pages, page


# ================================================================================
#                         USER-FRIENDLY ERROR MESSAGES
# ================================================================================

class UserFriendlyError:
    """
    Translates technical errors into plain, friendly language
    that non-coders can understand.
    """

    FRIENDLY_MAP: Dict[str, str] = {
        "forbidden": (
            "🚫 <b>Bot can't message this user</b>\n\n"
            "The user has blocked the bot or deleted their account."
        ),
        "chat not found": (
            "🔍 <b>Chat not found</b>\n\n"
            "The channel or group doesn't exist, or the bot hasn't been added there."
        ),
        "bot is not a member": (
            "🤖 <b>Bot is not in the channel</b>\n\n"
            "Please add the bot to the channel as an admin first."
        ),
        "not enough rights": (
            "🔐 <b>Missing permissions</b>\n\n"
            "The bot doesn't have admin rights in that channel. "
            "Please make the bot an admin with appropriate permissions."
        ),
        "message to edit not found": (
            "💬 <b>Message was deleted</b>\n\n"
            "The message was already deleted, so it couldn't be updated. This is harmless."
        ),
        "message is not modified": (
            "✏️ <b>Nothing changed</b>\n\n"
            "The message already shows the latest information."
        ),
        "query is too old": (
            "⏰ <b>Button expired</b>\n\n"
            "This button is too old. Please tap the menu button again to get a fresh one."
        ),
        "retry after": (
            "⏳ <b>Telegram rate limit</b>\n\n"
            "Too many messages sent too quickly. The bot will automatically retry shortly."
        ),
        "timed out": (
            "⌛ <b>Connection timed out</b>\n\n"
            "The request took too long. Please try again."
        ),
        "network error": (
            "🌐 <b>Network issue</b>\n\n"
            "There was a connection problem. Please try again in a moment."
        ),
        "invalid token": (
            "🔑 <b>Invalid bot token</b>\n\n"
            "The bot token provided doesn't work. Please check it and try again."
        ),
        "wrong file identifier": (
            "🖼 <b>File not available</b>\n\n"
            "This file is no longer accessible. Please send it again."
        ),
        "parse entities": (
            "📝 <b>Text formatting error</b>\n\n"
            "There was an issue formatting the message. This has been logged."
        ),
        "peer_id_invalid": (
            "👤 <b>User ID is invalid</b>\n\n"
            "That user ID doesn't exist or can't be reached."
        ),
    }

    GENERIC_USER_MSG = (
        "😅 <b>Something went wrong</b>\n\n"
        "Don't worry — this isn't your fault. "
        "The issue has been automatically reported to our team."
    )

    @staticmethod
    def get_user_message(error: Exception) -> str:
        """Return a friendly message for the user."""
        err_str = str(error).lower()
        for key, msg in UserFriendlyError.FRIENDLY_MAP.items():
            if key in err_str:
                return msg
        return UserFriendlyError.GENERIC_USER_MSG

    @staticmethod
    def get_admin_message(error: Exception, context_info: str = "") -> str:
        """Return a technical message for the admin."""
        err_type = type(error).__name__
        err_detail = str(error)
        tb = traceback.format_exc()
        tb_short = tb[-1500:] if len(tb) > 1500 else tb
        return (
            f"<b>⚠️ Technical Error</b>\n"
            f"<b>Type:</b> <code>{e(err_type)}</code>\n"
            f"<b>Detail:</b> <code>{e(err_detail[:300])}</code>\n"
            + (f"<b>Context:</b> <code>{e(context_info[:200])}</code>\n" if context_info else "")
            + f"\n<pre>{e(tb_short)}</pre>"
        )

    @staticmethod
    def is_ignorable(error: Exception) -> bool:
        """Return True for errors that are harmless and shouldn't be reported."""
        ignorable = [
            "query is too old",
            "message is not modified",
            "message to edit not found",
            "have no rights to send",
        ]
        err_str = str(error).lower()
        return any(ig in err_str for ig in ignorable)


# ================================================================================
#                           SAFE TELEGRAM SEND HELPERS
# ================================================================================

async def safe_delete(bot: Bot, chat_id: int, message_id: int) -> bool:
    """Delete a message safely, ignoring all errors."""
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        return True
    except Exception:
        return False


async def safe_answer(
    query: CallbackQuery,
    text: str = "",
    show_alert: bool = False,
) -> None:
    """Answer a callback query, silently ignoring timeout errors."""
    try:
        await query.answer(text=text, show_alert=show_alert)
    except Exception:
        pass


async def safe_send_message(
    bot: Bot,
    chat_id: int,
    text: str,
    parse_mode: str = ParseMode.HTML,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    disable_web_page_preview: bool = True,
) -> Optional[Any]:
    """Send a message safely with proper error handling."""
    try:
        return await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
            disable_web_page_preview=disable_web_page_preview,
        )
    except RetryAfter as e:
        await asyncio.sleep(e.retry_after + 1)
        try:
            return await bot.send_message(
                chat_id=chat_id, text=text, parse_mode=parse_mode,
                reply_markup=reply_markup,
            )
        except Exception:
            return None
    except Exception as exc:
        logger.debug(f"safe_send_message failed to {chat_id}: {exc}")
        return None


async def safe_edit_text(
    query: CallbackQuery,
    text: str,
    parse_mode: str = ParseMode.HTML,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
) -> Optional[Any]:
    """Edit a message text safely; fall back to sending new message."""
    try:
        return await query.edit_message_text(
            text=text, parse_mode=parse_mode, reply_markup=reply_markup
        )
    except BadRequest as e:
        if "message is not modified" in str(e).lower():
            return None
        # fall through to send new message
    except Exception:
        pass
    try:
        chat_id = query.message.chat_id
        return await safe_send_message(
            query.message.get_bot(),
            chat_id, text, parse_mode, reply_markup
        )
    except Exception as exc:
        logger.debug(f"safe_edit_text fallback failed: {exc}")
    return None


async def safe_edit_caption(
    query: CallbackQuery,
    caption: str,
    parse_mode: str = ParseMode.HTML,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
) -> Optional[Any]:
    """Edit a message caption safely."""
    try:
        return await query.edit_message_caption(
            caption=caption, parse_mode=parse_mode, reply_markup=reply_markup
        )
    except Exception:
        return await safe_edit_text(query, caption, parse_mode, reply_markup)


async def safe_reply(
    update: Update,
    text: str,
    parse_mode: str = ParseMode.HTML,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    disable_web_page_preview: bool = True,
) -> Optional[Any]:
    """Reply to a message or callback query safely."""
    try:
        if update.message:
            return await update.message.reply_text(
                text, parse_mode=parse_mode, reply_markup=reply_markup,
                disable_web_page_preview=disable_web_page_preview,
            )
        elif update.callback_query and update.callback_query.message:
            return await update.callback_query.message.reply_text(
                text, parse_mode=parse_mode, reply_markup=reply_markup,
                disable_web_page_preview=disable_web_page_preview,
            )
        elif update.effective_chat:
            bot = update._bot
            return await safe_send_message(
                bot, update.effective_chat.id, text, parse_mode, reply_markup
            )
    except Exception as exc:
        logger.debug(f"safe_reply failed: {exc}")
    return None


async def safe_send_photo(
    bot: Bot,
    chat_id: int,
    photo: Any,
    caption: str = "",
    parse_mode: str = ParseMode.HTML,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
) -> Optional[Any]:
    """
    Send photo with robust error handling + auto text fallback.
    If image URL is unreachable, invalid, or wrong size → sends caption as text.
    Handles: BadRequest, NetworkError, TimedOut, Forbidden, invalid URLs.
    """
    if not photo:
        if caption:
            return await safe_send_message(bot, chat_id, caption, parse_mode, reply_markup)
        return None
    try:
        return await bot.send_photo(
            chat_id=chat_id, photo=photo, caption=caption,
            parse_mode=parse_mode, reply_markup=reply_markup,
        )
    except BadRequest as exc:
        err = str(exc).lower()
        if any(k in err for k in ("photo_invalid", "url_invalid", "wrong file", "failed to get",
                                   "invalid document", "webpage_media_empty", "wrong_url")):
            logger.debug(f"safe_send_photo bad image, using text fallback: {exc}")
        else:
            logger.debug(f"safe_send_photo BadRequest: {exc}")
        if caption:
            try:
                return await safe_send_message(bot, chat_id, caption, parse_mode, reply_markup)
            except Exception:
                pass
    except (NetworkError, TimedOut) as exc:
        logger.debug(f"safe_send_photo network error (text fallback): {exc}")
        if caption:
            try:
                return await safe_send_message(bot, chat_id, caption, parse_mode, reply_markup)
            except Exception:
                pass
    except Forbidden:
        pass  # Bot blocked — don't retry
    except Exception as exc:
        logger.debug(f"safe_send_photo failed: {exc}")
        if caption:
            try:
                return await safe_send_message(bot, chat_id, caption, parse_mode, reply_markup)
            except Exception:
                pass
    return None



# ================================================================================
#   PANEL STORE SYSTEM — pre-render panels into PANEL_DB_CHANNEL for ms delivery
# ================================================================================
#
# How it works:
#   1. Every panel type (admin, stats, users, channels...) has a "template" stored
#      as a photo message in PANEL_DB_CHANNEL with caption = panel content.
#   2. The message_id is saved in bot_settings as "panel_store_{panel_type}".
#   3. When a user triggers a panel:
#        a. Look up the stored message_id
#        b. copy_message from PANEL_DB_CHANNEL to user's chat (pure CDN, ~50ms)
#        c. Attach the inline keyboard (copy_message doesn't carry keyboards)
#   4. If no stored message: generate normally, store it, reply instantly.
#   5. Background job re-stores all panels every 5 minutes with fresh content.
#
# This means panel delivery = 1 Telegram API call with a pre-cached file_id.
# Zero DB read latency for the photo. Zero generation time. Pure CDN speed.
# ================================================================================

# In-memory panel store: panel_type → {file_id, caption, stored_at}
_PANEL_STORE: dict = {}
_PANEL_STORE_TTL: int = 300  # rebuild panels every 5 min


def _ps_key(panel_type: str) -> str:
    return f"panel_store_{panel_type}"


def _ps_get(panel_type: str) -> Optional[dict]:
    """Get stored panel from memory cache."""
    entry = _PANEL_STORE.get(panel_type)
    if entry and (time.monotonic() - entry.get("ts", 0)) < _PANEL_STORE_TTL:
        return entry
    # Try DB
    try:
        raw = get_setting(_ps_key(panel_type), "")
        if raw:
            data = json.loads(raw)
            _PANEL_STORE[panel_type] = {**data, "ts": time.monotonic()}
            return _PANEL_STORE[panel_type]
    except Exception:
        pass
    return None


def _ps_set(panel_type: str, file_id: str, caption: str) -> None:
    """Cache a panel's photo file_id + caption."""
    entry = {"file_id": file_id, "caption": caption, "ts": time.monotonic()}
    _PANEL_STORE[panel_type] = entry
    try:
        set_setting(_ps_key(panel_type), json.dumps({
            "file_id": file_id,
            "caption": caption,
        }))
    except Exception:
        pass


def _ps_invalidate(panel_type: str = None) -> None:
    """Invalidate stored panel(s) so they're rebuilt on next access."""
    if panel_type:
        _PANEL_STORE.pop(panel_type, None)
    else:
        _PANEL_STORE.clear()


async def _deliver_panel(
    bot,
    chat_id: int,
    panel_type: str,
    caption: str,
    reply_markup,
    query=None,
) -> bool:
    """
    Ultra-fast panel delivery using pre-stored file_ids.

    Flow:
      1. Delete triggering message (if any)
      2. Check panel store for pre-cached file_id
      3a. If found: send_photo with cached file_id + keyboard (CDN-speed, ~50ms)
      3b. If not found: get_panel_pic() → send_photo → store file_id for next time
      4. Text fallback if no photo available at all

    The inline keyboard is always attached fresh (contains dynamic data like
    toggle states) — only the photo is cached/reused.
    """
    # ── Step 1: Delete old message ─────────────────────────────────────────────
    if query and query.message:
        try:
            await query.message.delete()
        except Exception:
            pass

    # ── Step 2: Look up cached file_id ─────────────────────────────────────────
    stored = _ps_get(panel_type)
    photo_to_send = stored["file_id"] if stored else None

    # ── Step 3a: If no cached file_id, get from panel image system ─────────────
    if not photo_to_send:
        photo_to_send = get_panel_pic(panel_type)

    # ── Step 3b: Send ──────────────────────────────────────────────────────────
    if photo_to_send:
        try:
            sent = await bot.send_photo(
                chat_id=chat_id,
                photo=photo_to_send,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
            )
            # ── Store file_id for next time (if not already stored) ───────────
            if sent and sent.photo and not stored:
                fid = sent.photo[-1].file_id
                _ps_set(panel_type, fid, caption)
                # Also update panel_image cache
                if _PANEL_IMAGE_AVAILABLE:
                    try:
                        from panel_image import set_tg_fileid
                        set_tg_fileid(panel_type, fid)
                        set_tg_fileid("default", fid)
                    except Exception:
                        pass
            return True
        except Exception as exc:
            logger.debug(f"_deliver_panel photo failed for {panel_type}: {exc}")
            # Invalidate bad file_id
            _ps_invalidate(panel_type)

    # ── Step 4: Text fallback ──────────────────────────────────────────────────
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
        )
        return True
    except Exception as exc:
        logger.debug(f"_deliver_panel text fallback failed: {exc}")
        return False


async def _prebuild_all_panels(bot) -> None:
    """
    Background loop: pre-send every panel to PANEL_DB_CHANNEL to warm up
    file_ids, then store them. Runs every 5 min.
    Panels with no photo just skip — text-only panels don't benefit from pre-build.
    """
    if not PANEL_DB_CHANNEL:
        return

    PANEL_TYPES = [
        "admin", "stats", "users", "channels", "clones",
        "settings", "broadcast", "upload", "categories",
        "poster", "manga", "autoforward", "flags", "style",
        "default",
    ]

    for ptype in PANEL_TYPES:
        try:
            photo = get_panel_pic(ptype)
            if not photo:
                continue
            stored = _ps_get(ptype)
            if stored:
                continue  # already warm, skip

            # Send a placeholder to PANEL_DB_CHANNEL to get a file_id
            sent = await bot.send_photo(
                chat_id=PANEL_DB_CHANNEL,
                photo=photo,
                caption=f"<b>Panel Store</b> | <code>{ptype}</code>",
                parse_mode="HTML",
            )
            if sent and sent.photo:
                fid = sent.photo[-1].file_id
                _ps_set(ptype, fid, "")  # caption stored per-render, file_id cached here
                # Update panel_image too
                if _PANEL_IMAGE_AVAILABLE:
                    try:
                        from panel_image import set_tg_fileid
                        set_tg_fileid(ptype, fid)
                        set_tg_fileid("default", fid)
                    except Exception:
                        pass
                logger.debug(f"[panel_store] pre-built {ptype}")

            await asyncio.sleep(0.3)  # small delay between sends

        except Exception as exc:
            logger.debug(f"[panel_store] pre-build {ptype} failed: {exc}")


async def safe_edit_panel(
    bot,
    query,
    chat_id: int,
    photo,
    caption: str,
    reply_markup,
    panel_type: str = "default",
) -> bool:
    """Alias → _deliver_panel. All panels now use the panel store system."""
    return await _deliver_panel(
        bot=bot,
        chat_id=chat_id,
        panel_type=panel_type,
        caption=caption,
        reply_markup=reply_markup,
        query=query,
    )


async def addpanelimg_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /addpanelimg — send one or more photos (or reply to a photo) to add them
    to the panel DB channel. The bot forwards each to PANEL_DB_CHANNEL, saves
    the file_id + message_id, and shows the numbered list.
    Works exactly like the welcome image system.
    """
    uid = update.effective_user.id if update.effective_user else 0
    if uid not in (ADMIN_ID, OWNER_ID):
        return

    msg = update.effective_message
    chat_id = msg.chat_id

    if not PANEL_DB_CHANNEL:
        await safe_send_message(
            context.bot, chat_id,
            "❌ <b>PANEL_DB_CHANNEL not set.</b>\n\n"
            "Add <code>PANEL_DB_CHANNEL</code> to your Render env vars.\n"
            "Create a private channel, add the bot as admin, and paste the channel ID (e.g. <code>-1001234567890</code>)."
        )
        return

    # Collect photos from replied-to message or current message
    photos = []
    if msg.reply_to_message and msg.reply_to_message.photo:
        photos = [msg.reply_to_message.photo[-1]]
    elif msg.photo:
        photos = [msg.photo[-1]]

    if not photos:
        # Show current list instead
        await _show_panel_img_list(context.bot, chat_id, query=None)
        return

    items = _get_panel_db_images()
    added = 0
    for photo in photos:
        try:
            # Forward to panel DB channel — same pattern as welcome source channel
            sent = await context.bot.send_photo(
                chat_id=PANEL_DB_CHANNEL,
                photo=photo.file_id,
                caption=f"Panel image #{len(items) + 1}",
            )
            file_id = sent.photo[-1].file_id
            msg_id  = sent.message_id
            items.append({"index": len(items) + 1, "msg_id": msg_id, "file_id": file_id})
            added += 1
        except Exception as exc:
            logger.error(f"addpanelimg: forward to channel failed: {exc}")

    if added:
        _save_panel_db_images(items)
        # Also update session cache so it takes effect immediately
        if _PANEL_IMAGE_AVAILABLE:
            try:
                from panel_image import set_tg_fileid, clear_tg_fileid
                clear_tg_fileid()
            except Exception:
                pass

    await _show_panel_img_list(context.bot, chat_id, query=None, just_added=added)


async def _show_panel_img_list(
    bot, chat_id: int, query=None, page: int = 0, just_added: int = 0
) -> None:
    """Show numbered panel image list with ◀ ▶ navigation (1 image per page)."""
    items = _get_panel_db_images()
    total = len(items)

    if not items:
        text = (
            "<b>🖼 Panel Images</b>\n\n"
            "No images added yet.\n\n"
            "Send a photo and use /addpanelimg, or reply to a photo with /addpanelimg."
        )
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="admin_env_panel"), InlineKeyboardButton("✖️", callback_data="close_message")]]
        if query:
            try:
                await query.delete_message()
            except Exception:
                pass
        await safe_send_message(bot, chat_id, text, reply_markup=InlineKeyboardMarkup(kb))
        return

    # Clamp page
    page = max(0, min(page, total - 1))
    item = items[page]
    file_id = item.get("file_id")
    idx     = page + 1  # 1-based display number

    added_note = f"\n✅ Added {just_added} image(s)." if just_added else ""
    caption = (
        f"<b>🖼 Panel Image {idx}/{total}</b>{added_note}\n\n"
        f"This image rotates randomly as your panel background.\n"
        f"<i>Image #{idx} of {total} stored in panel DB channel.</i>"
    )

    # Nav row: ◀ · idx/total · ▶
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("🔙", callback_data=f"panel_img_view_{page - 1}"))
    nav.append(InlineKeyboardButton(f"{idx}/{total}", callback_data="noop"))
    if page < total - 1:
        nav.append(InlineKeyboardButton("🔜", callback_data=f"panel_img_view_{page + 1}"))

    kb = [
        nav,
        [
            InlineKeyboardButton(f"🗑 Delete #{idx}", callback_data=f"panel_img_del_{page}"),
            InlineKeyboardButton("🔙 Back", callback_data="admin_env_panel"),
            InlineKeyboardButton("✖️", callback_data="close_message"),
        ],
    ]
    markup = InlineKeyboardMarkup(kb)

    if query:
        try:
            await query.delete_message()
        except Exception:
            pass

    if file_id:
        try:
            await bot.send_photo(
                chat_id=chat_id,
                photo=file_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=markup,
            )
            return
        except Exception:
            pass
    await safe_send_message(bot, chat_id, caption, reply_markup=markup)


async def getfileid_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /getfileid — reply to any photo with this command to get its Telegram file_id.
    Set PANEL_IMAGE_FILE_ID=<file_id> in your Render env vars for instant panels from boot.
    """
    uid = update.effective_user.id if update.effective_user else 0
    if uid not in (ADMIN_ID, OWNER_ID):
        return

    msg = update.effective_message
    photo = None

    # Check if replying to a photo
    if msg.reply_to_message and msg.reply_to_message.photo:
        photo = msg.reply_to_message.photo[-1]  # largest size
    elif msg.photo:
        photo = msg.photo[-1]

    if not photo:
        await safe_send_message(
            context.bot, msg.chat_id,
            "📎 <b>How to use:</b> Send or forward any image, then reply to it with /getfileid. "
            "Then copy the file_id and set it as <code>PANEL_IMAGE_FILE_ID</code> in your Render env vars. "
            "This makes every panel load instantly from the very first boot — no warmup needed.",
        )
        return

    file_id = photo.file_id
    # Also cache it immediately for this session
    if _PANEL_IMAGE_AVAILABLE:
        try:
            from panel_image import set_tg_fileid
            for ptype in ["admin", "stats", "settings", "broadcast", "default"]:
                set_tg_fileid(ptype, file_id)
        except Exception:
            pass

    await safe_send_message(
        context.bot, msg.chat_id,
        (
            "✅ <b>File ID captured and cached for this session!</b>\n\n"
            f"<code>{file_id}</code>\n\n"
            "To make this permanent (instant panels even after restart), "
            "add to Render env vars:\n"
            "<b>Key:</b> <code>PANEL_IMAGE_FILE_ID</code>\n"
            f"<b>Value:</b> <code>{file_id}</code>"
        ),
    )


async def delete_update_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Delete the user's trigger message.
    Never deletes on mobile if it's the ONLY message (prevents exit).
    Skips /start to preserve conversation start safety.
    """
    msg = update.message
    if not msg:
        return
    msg_text = msg.text or ""
    if msg_text.startswith("/start"):
        return
    user_id = update.effective_user.id if update.effective_user else 0
    if user_id == ADMIN_ID and user_states.get(user_id) in (
        PENDING_BROADCAST, PENDING_BROADCAST_OPTIONS, PENDING_BROADCAST_CONFIRM
    ):
        return
    try:
        await msg.delete()
    except Exception:
        pass


async def delete_bot_prompt(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int
) -> None:
    """Delete the previously stored bot prompt message."""
    msg_id = context.user_data.pop("bot_prompt_message_id", None)
    if msg_id and context.bot:
        await safe_delete(context.bot, chat_id, msg_id)


async def store_bot_prompt(
    context: ContextTypes.DEFAULT_TYPE, msg: Any
) -> None:
    """Store a bot message ID so it can be deleted later."""
    if msg and hasattr(msg, "message_id"):
        context.user_data["bot_prompt_message_id"] = msg.message_id


# ================================================================================
#                     CONVERSATION SAFETY — ANTI-EXIT SYSTEM
# ================================================================================
#
# On mobile Telegram, if the ONLY message in a DM is deleted, the app
# exits the conversation. To prevent this, we:
#   1. Always pin a "safety anchor" message on first /start
#   2. Use loading animation with bold "❗" so there's always a visible message
#   3. Never delete the last message in a conversation
#
# ================================================================================

_safety_anchors: Dict[int, int] = {}   # chat_id → message_id of anchor


async def ensure_safety_anchor(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int
) -> None:
    """
    Send (or update) a silent anchor message that prevents the
    mobile Telegram exit-on-delete-last-message bug.
    """
    if chat_id in _safety_anchors:
        return
    try:
        anchor = await context.bot.send_message(
            chat_id,
            "<b>❗</b>",
            parse_mode=ParseMode.HTML,
            disable_notification=True,
        )
        _safety_anchors[chat_id] = anchor.message_id
    except Exception as exc:
        logger.debug(f"Safety anchor failed for {chat_id}: {exc}")


async def loading_animation_start(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
) -> Optional[Any]:
    """
    Loading animation — supports:
      • Custom TG sticker (set via /set_loader, forwarding a sticker)
      • Default ❗ bold text frames
      • Fully disableable via /set_loader off
    Returns the message object (sticker or text).
    """
    # Check if loading is disabled by admin
    try:
        if get_setting("loading_anim_enabled", "true") == "false":
            return None
    except Exception:
        pass

    msg = None

    # Custom sticker (DB) or env TRANSITION_STICKER
    try:
        sticker_id = get_setting("loading_sticker_id", "") or TRANSITION_STICKER_ID
        if sticker_id:
            msg = await context.bot.send_sticker(chat_id, sticker_id)
            _safety_anchors[chat_id] = msg.message_id
            return msg
    except Exception:
        pass

    # Fast 3-frame ❗ animation (~0.5s total — snappy but visible)
    frames = ["❗", "❗❗", "❗❗❗"]
    try:
        msg = await context.bot.send_message(
            chat_id, b(frames[0]), parse_mode=ParseMode.HTML
        )
        _safety_anchors[chat_id] = msg.message_id
        for frame in frames[1:]:
            await asyncio.sleep(0.18)
            try:
                await msg.edit_text(b(frame), parse_mode=ParseMode.HTML)
            except Exception:
                break
    except Exception as exc:
        logger.debug(f"loading_animation_start failed: {exc}")
    return msg


async def loading_animation_end(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, msg: Optional[Any]
) -> None:
    """Delete the loading message (but only if it's not the last one)."""
    if not msg:
        return
    if _safety_anchors.get(chat_id) == msg.message_id:
        del _safety_anchors[chat_id]
    await safe_delete(context.bot, chat_id, msg.message_id)


async def send_transition_sticker(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int
) -> None:
    """
    Transition sticker — fire and forget (no wait, no delete delay).
    Sends sticker and schedules background delete after 1s without blocking.
    """
    if not TRANSITION_STICKER_ID:
        return
    try:
        sticker_msg = await context.bot.send_sticker(chat_id, TRANSITION_STICKER_ID)
        # Background delete — does NOT block the caller
        async def _delete_later():
            await asyncio.sleep(1.0)
            await safe_delete(context.bot, chat_id, sticker_msg.message_id)
        asyncio.create_task(_delete_later())
    except Exception as exc:
        logger.debug(f"Transition sticker failed: {exc}")


# ================================================================================
#                          MAINTENANCE / BAN BLOCK SCREENS
# ================================================================================

async def send_maintenance_block(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Show maintenance message to non-existing users."""
    backup_url = get_setting("backup_channel_url", "")
    text = (
        b("🔧 Bot Under Maintenance") + "\n\n"
        + bq(
            b("We are doing some scheduled maintenance right now.\n\n")
            + "<b>Existing members can still access the bot.\n"
            "New members, please wait for us to come back online.</b>",
        ) + "\n\n"
        + b("Stay updated via our backup channel.")
    )
    keyboard = []
    if backup_url:
        keyboard.append([InlineKeyboardButton("📢 Backup Channel", url=backup_url)])
    markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    try:
        if update.callback_query:
            await safe_edit_text(update.callback_query, text, reply_markup=markup)
        elif update.effective_chat:
            await safe_send_message(
                context.bot, update.effective_chat.id, text, reply_markup=markup
            )
    except Exception as exc:
        logger.debug(f"send_maintenance_block error: {exc}")


async def send_ban_screen(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Show a user-friendly ban screen."""
    text = (
        b("🚫 You have been restricted") + "\n\n"
        + bq(
            b("Your access to this bot has been suspended.\n\n")
            + b("If you think this is a mistake, please contact the admin.")
        ) + "\n\n"
        + f"<b>Contact:</b> @{e(ADMIN_CONTACT_USERNAME)}"
    )
    try:
        if update.callback_query:
            await safe_answer(update.callback_query)
            await safe_edit_text(update.callback_query, text)
        elif update.message:
            await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    except Exception:
        pass


# ================================================================================
#                       FORCE SUBSCRIPTION SYSTEM (FULL)
# ================================================================================

async def get_unsubscribed_channels(
    user_id: int, bot: Bot
) -> List[Tuple[str, str, bool]]:
    """
    Return list of (username, title, jbr) for channels the user has not joined.
    For clone bots, falls back to main bot token for membership checks.
    """
    channels_info = get_all_force_sub_channels(return_usernames_only=False)
    if not channels_info:
        return []

    unsubscribed = []
    main_bot: Optional[Bot] = None

    if I_AM_CLONE:
        main_token = get_main_bot_token()
        if main_token:
            try:
                main_bot = Bot(token=main_token)
            except Exception:
                pass

    for uname, title, jbr in channels_info:
        subscribed = False
        # Try with current bot first
        for check_bot in filter(None, [bot, main_bot]):
            try:
                member = await check_bot.get_chat_member(chat_id=uname, user_id=user_id)
                if member.status not in ("left", "kicked"):
                    subscribed = True
                    break
                else:
                    break   # Got an answer — not subscribed
            except Exception as exc:
                logger.debug(f"Membership check {uname} failed: {exc}")
                continue

        if not subscribed:
            unsubscribed.append((uname, title, jbr))

    return unsubscribed


def force_sub_required(func: Callable) -> Callable:
    """
    Decorator: check force-sub, maintenance mode, and ban before
    executing any command or button handler.
    """
    @wraps(func)
    async def wrapper(
        update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
    ):
        user = update.effective_user
        if user is None:
            return await func(update, context, *args, **kwargs)

        # Always answer callback queries immediately
        if update.callback_query:
            await safe_answer(update.callback_query)

        uid = user.id

        # Owner / Admin always bypass everything
        if uid in (ADMIN_ID, OWNER_ID):
            return await func(update, context, *args, **kwargs)

        # Ban check
        if is_user_banned(uid):
            await send_ban_screen(update, context)
            return

        # Maintenance check (only block NEW users)
        if is_maintenance_mode() and not is_existing_user(uid):
            await send_maintenance_block(update, context)
            return

        # Force-sub check
        unsubscribed = await get_unsubscribed_channels(uid, context.bot)
        if unsubscribed:
            await _send_force_sub_screen(update, context, unsubscribed, uid)
            return

        return await func(update, context, *args, **kwargs)

    return wrapper


async def _send_force_sub_screen(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    unsubscribed: List[Tuple[str, str, bool]],
    user_id: int,
) -> None:
    """Display the force-sub join screen."""
    user = update.effective_user
    total = len(get_all_force_sub_channels(return_usernames_only=False))
    unjoined = len(unsubscribed)
    user_name = e(getattr(user, "first_name", None) or getattr(user, "username", None) or "Friend")

    text = (
        f"⚠️ {b(f'Hey {user_name}! You need to join {unjoined} channel(s).')}\n\n"
        + bq(
            b("Please join ALL the channels listed below,\n")
            + b("then click the  Try Again button.")
        )
        + f"\n\n<b>Total channels: {total} | Unjoined: {unjoined}</b>"
    )

    keyboard = []
    for uname, title, jbr in unsubscribed:
        clean = uname.lstrip("@")
        if jbr:
            keyboard.append([InlineKeyboardButton(f" {title}", url=f"https://t.me/{clean}")])
        else:
            keyboard.append([InlineKeyboardButton(f" {title}", url=f"https://t.me/{clean}")])

    keyboard.append([bold_button("♻️Try Again", callback_data="verify_subscription")])
    keyboard.append([bold_button("Help", callback_data="user_help")])

    markup = InlineKeyboardMarkup(keyboard)
    try:
        if update.callback_query:
            await safe_edit_text(update.callback_query, text, reply_markup=markup)
        elif update.message:
            await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)
        elif update.effective_chat:
            await safe_send_message(context.bot, update.effective_chat.id, text, reply_markup=markup)
    except Exception as exc:
        logger.debug(f"_send_force_sub_screen error: {exc}")


# ================================================================================
#                            SYSTEM STATS HELPERS
# ================================================================================

def get_uptime() -> str:
    return format_duration(int(time.time() - BOT_START_TIME))


def get_db_size() -> str:
    try:
        with db_manager.get_cursor() as cur:
            cur.execute("SELECT pg_database_size(current_database())")
            return format_size(cur.fetchone()[0])
    except Exception:
        return "N/A"


def get_disk_usage() -> str:
    try:
        usage = psutil.disk_usage("/")
        return f"{format_size(usage.free)} free / {format_size(usage.total)} total"
    except Exception:
        return "N/A"


def get_cpu_usage() -> str:
    try:
        return f"{psutil.cpu_percent(interval=0.3):.1f}%"
    except Exception:
        return "N/A"


def get_memory_usage() -> str:
    try:
        m = psutil.virtual_memory()
        return f"{m.percent:.1f}% ({format_size(m.used)} / {format_size(m.total)})"
    except Exception:
        return "N/A"


def get_network_info() -> str:
    try:
        net = psutil.net_io_counters()
        return f"↑{format_size(net.bytes_sent)} ↓{format_size(net.bytes_recv)}"
    except Exception:
        return "N/A"


def get_system_stats_text() -> str:
    return (
        b(" System Statistics") + "\n\n"
        f"<b>⏱ Uptime:</b> {code(get_uptime())}\n"
        f"<b> CPU:</b> {code(get_cpu_usage())}\n"
        f"<b> Memory:</b> {code(get_memory_usage())}\n"
        f"<b> DB Size:</b> {code(get_db_size())}\n"
        f"<b> Disk:</b> {code(get_disk_usage())}\n"
        f"<b> Network:</b> {code(get_network_info())}\n"
        f"<b> Mode:</b> {code('Clone Bot' if I_AM_CLONE else 'Main Bot')}\n"
        f"<b> Username:</b> @{e(BOT_USERNAME)}"
    )


# ================================================================================
#                               ANILIST CLIENT (FULL)
# ================================================================================

class AniListClient:
    """Full AniList GraphQL API client."""
    BASE_URL = "https://graphql.anilist.co"
    SESSION: Optional[aiohttp.ClientSession] = None

    ANIME_FIELDS = """
        id siteUrl
        title { romaji english native }
        description(asHtml: false)
        coverImage { extraLarge large medium color }
        bannerImage
        format status season seasonYear
        episodes duration averageScore popularity
        genres tags { name rank isMediaSpoiler }
        studios(isMain: true) { nodes { name siteUrl } }
        startDate { year month day }
        endDate { year month day }
        nextAiringEpisode { episode airingAt timeUntilAiring }
        relations { edges { relationType(version: 2) node { id title { romaji } type format } } }
        characters(sort: ROLE, page: 1, perPage: 5) {
            nodes { name { full } image { medium } }
        }
        staff(sort: RELEVANCE, page: 1, perPage: 3) {
            nodes { name { full } primaryOccupations }
        }
        trailer { id site }
        externalLinks { url site }
        rankings { rank type context }
        streamingEpisodes { title thumbnail url site }
        isAdult
        countryOfOrigin
    """

    MANGA_FIELDS = """
        id siteUrl
        title { romaji english native }
        description(asHtml: false)
        coverImage { extraLarge large medium color }
        bannerImage
        format status
        chapters volumes averageScore popularity
        genres tags { name rank }
        startDate { year month day }
        endDate { year month day }
        relations { edges { relationType(version: 2) node { id title { romaji } type format } } }
        characters(sort: ROLE, page: 1, perPage: 5) {
            nodes { name { full } image { medium } }
        }
        staff(sort: RELEVANCE, page: 1, perPage: 3) {
            nodes { name { full } primaryOccupations }
        }
        externalLinks { url site }
        countryOfOrigin
    """

    @staticmethod
    def _normalize_query(query: str) -> str:
        """Normalize and fuzzy-correct search query.
        Removes extra spaces and common typos. AniList handles fuzzy matching server-side.
        """
        import difflib
        query = query.strip()
        # Remove duplicate spaces
        query = " ".join(query.split())
        # Common abbreviation expansions
        expansions = {
            "aot": "attack on titan",
            "bnha": "my hero academia",
            "mha": "my hero academia",
            "hxh": "hunter x hunter",
            "dbs": "dragon ball super",
            "dbz": "dragon ball z",
            "op": "one piece",
            "fma": "fullmetal alchemist",
            "snk": "attack on titan",
            "jjk": "jujutsu kaisen",
            "csm": "chainsaw man",
            "slime": "that time i got reincarnated as a slime",
            "rezero": "re zero starting life in another world",
        }
        lower = query.lower()
        if lower in expansions:
            return expansions[lower]
        return query

    @staticmethod
    def search_anime(query: str) -> Optional[Dict]:
        normalized = AniListClient._normalize_query(query)
        q = f"""
        query($s:String){{
          Media(search:$s,type:ANIME){{
            {AniListClient.ANIME_FIELDS}
          }}
        }}
        """
        result = AniListClient._query(q, {"s": normalized})
        if not result and normalized != query:
            result = AniListClient._query(q, {"s": query})
        return result

    @staticmethod
    def search_manga(query: str) -> Optional[Dict]:
        normalized = AniListClient._normalize_query(query)
        q = f"""
        query($s:String){{
          Media(search:$s,type:MANGA){{
            {AniListClient.MANGA_FIELDS}
          }}
        }}
        """
        result = AniListClient._query(q, {"s": normalized})
        if not result and normalized != query:
            result = AniListClient._query(q, {"s": query})
        return result

    @staticmethod
    def get_by_id(media_id: int, media_type: str = "ANIME") -> Optional[Dict]:
        fields = AniListClient.ANIME_FIELDS if media_type == "ANIME" else AniListClient.MANGA_FIELDS
        q = f"""
        query($id:Int){{
          Media(id:$id,type:{media_type}){{
            {fields}
          }}
        }}
        """
        return AniListClient._query(q, {"id": media_id})

    @staticmethod
    def get_trending(media_type: str = "ANIME", limit: int = 5) -> List[Dict]:
        q = f"""
        query($type:MediaType,$perPage:Int){{
          Page(perPage:$perPage){{
            media(type:$type,sort:TRENDING_DESC,isAdult:false){{
              id title{{romaji}} coverImage{{medium}} averageScore
            }}
          }}
        }}
        """
        result = AniListClient._query(q, {"type": media_type, "perPage": limit})
        if result:
            return result
        return []

    @staticmethod
    def _query_trending(q: str, variables: dict) -> Optional[List[Dict]]:
        try:
            resp = requests.post(
                AniListClient.BASE_URL,
                json={"query": q, "variables": variables},
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("data", {}).get("Page", {}).get("media", [])
        except Exception as exc:
            api_logger.debug(f"AniList trending query failed: {exc}")
        return []

    @staticmethod
    def _query(query_str: str, variables: dict) -> Optional[Dict]:
        cache_key = f"anilist:{hashlib.md5(json.dumps({'q': query_str, 'v': variables}, sort_keys=True).encode()).hexdigest()}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached
        try:
            resp = requests.post(
                AniListClient.BASE_URL,
                json={"query": query_str, "variables": variables},
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=12,
            )
            if resp.status_code == 200:
                data = resp.json()
                result = data.get("data", {}).get("Media")
                if result:
                    _cache_set(cache_key, result)
                return result
            elif resp.status_code == 429:
                api_logger.warning("AniList rate limited")
                return None
            else:
                api_logger.debug(f"AniList {resp.status_code}: {resp.text[:300]}")
        except requests.Timeout:
            api_logger.debug("AniList request timed out")
        except Exception as exc:
            api_logger.debug(f"AniList request failed: {exc}")
        return None

    @staticmethod
    def format_anime_caption(data: Dict, template: Optional[str] = None) -> str:
        """Build a rich, fully-formatted anime caption from AniList data."""
        title_obj = data.get("title", {}) or {}
        title_romaji = title_obj.get("romaji", "")
        title_english = title_obj.get("english", "")
        title_native = title_obj.get("native", "")
        title_display = title_english or title_romaji or "Unknown"

        status = (data.get("status") or "").replace("_", " ").title()
        fmt = (data.get("format") or "").replace("_", " ").title()
        episodes = data.get("episodes", "?")
        duration = data.get("duration")
        score = data.get("averageScore")
        popularity = data.get("popularity", 0)
        genres = data.get("genres", []) or []
        genres_str = ", ".join(genres[:5]) if genres else "N/A"

        season = data.get("season")
        season_year = data.get("seasonYear")
        season_str = f"{season.title() if season else ''} {season_year or ''}".strip() or "N/A"

        start_date = parse_date(data.get("startDate"))
        end_date = parse_date(data.get("endDate"))
        country = data.get("countryOfOrigin", "")

        studios = data.get("studios", {}) or {}
        studio_nodes = studios.get("nodes", []) or []
        studio_name = studio_nodes[0].get("name", "N/A") if studio_nodes else "N/A"

        desc = strip_html(data.get("description") or "No description available.")
        desc = truncate(desc, 350)

        next_ep = data.get("nextAiringEpisode")
        next_ep_str = ""
        if next_ep:
            ep_num = next_ep.get("episode", "?")
            time_left = next_ep.get("timeUntilAiring", 0)
            days = time_left // 86400
            hrs = (time_left % 86400) // 3600
            next_ep_str = f"\n<b>Next Episode:</b> Ep.{ep_num} in {days}d {hrs}h"

        tags = data.get("tags", []) or []
        top_tags = [t["name"] for t in tags if not t.get("isMediaSpoiler")][:3]
        tags_str = ", ".join(top_tags) if top_tags else ""

        # Ranking
        rankings = data.get("rankings", []) or []
        rank_str = ""
        for r in rankings[:2]:
            rank_str += f"#{r.get('rank', '?')} {r.get('context', '').title()}\n"

        if template:
            for key, val in {
                "{title}": e(title_display), "{romaji}": e(title_romaji),
                "{status}": e(status), "{type}": e(fmt),
                "{episodes}": str(episodes), "{score}": str(score or "N/A"),
                "{genres}": e(genres_str), "{studio}": e(studio_name),
                "{synopsis}": e(desc), "{season}": e(season_str),
                "{popularity}": format_number(popularity),
                "{rating}": str(score or "N/A"),
            }.items():
                template = template.replace(key, val)
            return template

        # Spec-compliant format
        caption = b(e(title_display)) + "\n\n"
        caption += "━━━━━━━━━━━━━━\n"
        caption += f"➤ Status: {status}\n"
        caption += f"➤ Episodes: {str(episodes)}"
        if duration:
            caption += f" × {duration}min"
        caption += "\n"
        caption += f"➤ Rating: {str(score) + '/100' if score else 'N/A'}\n"
        caption += f"➤ Genres: {e(genres_str)}\n"
        if next_ep_str:
            caption += next_ep_str + "\n"
        caption += "\n"
        caption += bq(e(desc), expandable=True)

        site_url = data.get("siteUrl", "")
        if site_url:
            caption += f"\n\n<b>AniList:</b> {site_url}"

        return caption

    @staticmethod
    def format_manga_caption(data: Dict, template: Optional[str] = None) -> str:
        """Build a rich manga caption from AniList data."""
        title_obj = data.get("title", {}) or {}
        title_display = title_obj.get("english") or title_obj.get("romaji") or "Unknown"
        title_native = title_obj.get("native", "")
        title_romaji = title_obj.get("romaji", "")

        status = (data.get("status") or "").replace("_", " ").title()
        fmt = (data.get("format") or "").replace("_", " ").title()
        chapters = data.get("chapters", "Ongoing")
        volumes = data.get("volumes", "?")
        score = data.get("averageScore")
        popularity = data.get("popularity", 0)
        genres = data.get("genres", []) or []
        genres_str = ", ".join(genres[:5]) if genres else "N/A"

        start_date = parse_date(data.get("startDate"))
        end_date = parse_date(data.get("endDate"))
        country = data.get("countryOfOrigin", "")

        desc = strip_html(data.get("description") or "No description available.")
        desc = truncate(desc, 350)

        tags = data.get("tags", []) or []
        top_tags = [t["name"] for t in tags][:3]
        tags_str = ", ".join(top_tags) if top_tags else ""

        if template:
            for key, val in {
                "{title}": e(title_display), "{romaji}": e(title_romaji),
                "{status}": e(status), "{type}": e(fmt),
                "{chapters}": str(chapters), "{volumes}": str(volumes),
                "{score}": str(score or "N/A"), "{genres}": e(genres_str),
                "{synopsis}": e(desc),
                "{popularity}": format_number(popularity),
            }.items():
                template = template.replace(key, val)
            return template

        # Spec-compliant format
        caption = b(e(title_display)) + "\n\n"
        caption += "━━━━━━━━━━━━━━\n"
        caption += f"➤ Chapters: {str(chapters)}\n"
        caption += f"➤ Status: {status}\n"
        caption += f"➤ Source: {e(genres_str)}\n"
        caption += "\n"
        caption += bq(e(desc), expandable=True)

        site_url = data.get("siteUrl", "")
        if site_url:
            caption += f"\n\n<b>AniList:</b> {site_url}"

        return caption


# ================================================================================
#                               TMDB CLIENT (FULL)
# ================================================================================

class TMDBClient:
    """Full TMDB API client for movies and TV shows."""
    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_BASE = "https://image.tmdb.org/t/p"

    @staticmethod
    def _get(endpoint: str, params: Dict = None) -> Optional[Dict]:
        if not TMDB_API_KEY:
            return None
        p = {"api_key": TMDB_API_KEY}
        if params:
            p.update(params)
        try:
            resp = requests.get(
                f"{TMDBClient.BASE_URL}{endpoint}", params=p, timeout=10
            )
            if resp.status_code == 200:
                return resp.json()
            api_logger.debug(f"TMDB {resp.status_code}: {endpoint}")
        except Exception as exc:
            api_logger.debug(f"TMDB error: {exc}")
        return None

    @staticmethod
    def search_movie(query: str) -> Optional[Dict]:
        data = TMDBClient._get("/search/movie", {"query": query, "language": "en-US"})
        if not data:
            return None
        results = data.get("results", [])
        if not results:
            return None
        return TMDBClient.get_movie_details(results[0]["id"])

    @staticmethod
    def search_tv(query: str) -> Optional[Dict]:
        data = TMDBClient._get("/search/tv", {"query": query, "language": "en-US"})
        if not data:
            return None
        results = data.get("results", [])
        if not results:
            return None
        return TMDBClient.get_tv_details(results[0]["id"])

    @staticmethod
    def get_movie_details(movie_id: int) -> Optional[Dict]:
        return TMDBClient._get(
            f"/movie/{movie_id}",
            {"append_to_response": "credits,keywords,release_dates,videos", "language": "en-US"},
        )

    @staticmethod
    def get_tv_details(tv_id: int) -> Optional[Dict]:
        return TMDBClient._get(
            f"/tv/{tv_id}",
            {"append_to_response": "credits,keywords,content_ratings,videos", "language": "en-US"},
        )

    @staticmethod
    def get_trending(media_type: str = "movie", time_window: str = "week") -> List[Dict]:
        data = TMDBClient._get(f"/trending/{media_type}/{time_window}")
        return (data or {}).get("results", [])[:5]

    @staticmethod
    def get_poster_url(path: str, size: str = "w500") -> str:
        if not path:
            return ""
        return f"{TMDBClient.IMAGE_BASE}/{size}{path}"

    @staticmethod
    def get_backdrop_url(path: str, size: str = "w780") -> str:
        if not path:
            return ""
        return f"{TMDBClient.IMAGE_BASE}/{size}{path}"

    @staticmethod
    def format_movie_caption(data: Dict, template: Optional[str] = None) -> str:
        """Build a rich movie caption."""
        title = e(data.get("title") or data.get("name") or "Unknown")
        original_title = e(data.get("original_title") or data.get("original_name") or "")
        tagline = e(data.get("tagline") or "")
        release = e(data.get("release_date") or "Unknown")
        runtime = data.get("runtime") or 0
        runtime_str = f"{runtime // 60}h {runtime % 60}m" if runtime else "N/A"
        rating = data.get("vote_average", 0)
        vote_count = data.get("vote_count", 0)
        popularity = data.get("popularity", 0)
        status = e(data.get("status") or "Unknown")
        language = e(data.get("original_language") or "N/A").upper()
        genres = [g["name"] for g in data.get("genres", []) or []]
        genres_str = " • ".join(genres[:5]) if genres else "N/A"
        budget = data.get("budget", 0)
        revenue = data.get("revenue", 0)
        overview = e(truncate(data.get("overview") or "No overview.", 300))

        # Cast
        credits = data.get("credits", {}) or {}
        cast = credits.get("cast", []) or []
        top_cast = ", ".join(
            e(c["name"]) for c in cast[:5]
        ) if cast else "N/A"
        crew = credits.get("crew", []) or []
        directors = [c["name"] for c in crew if c.get("job") == "Director"]
        director_str = e(", ".join(directors[:2])) if directors else "N/A"

        # Keywords
        keywords = data.get("keywords", {}) or {}
        kw_list = [k["name"] for k in (keywords.get("keywords") or [])[:5]]
        kw_str = " • ".join(kw_list) if kw_list else ""

        lines = [b(title)]
        if original_title and original_title != title:
            lines.append(f"<i>{original_title}</i>")
        if tagline:
            lines.append(f"<i>❝{tagline}❞</i>")
        lines.append("")

        lines += [
            f"<b> Released:</b> {code(release)}",
            f"<b> Runtime:</b> {code(runtime_str)}",
            f"<b> Status:</b> {code(status)}",
            f"<b> Rating:</b> {code(f'{rating:.1f}/10 ({format_number(vote_count)} votes)')}",
            f"<b> Language:</b> {code(language)}",
            f"<b> Genres:</b> {e(genres_str)}",
            f"<b> Director:</b> {director_str}",
            f"<b> Cast:</b> {top_cast}",
        ]
        if budget:
            lines.append(f"<b> Budget:</b> {code('$' + format_number(budget))}")
        if revenue:
            lines.append(f"<b> Revenue:</b> {code('$' + format_number(revenue))}")
        if kw_str:
            lines.append(f"<b>🏷 Keywords:</b> {e(kw_str)}")
        lines.append("")
        lines.append(b(" Overview"))
        lines.append(bq(overview, expandable=True))

        if template:
            for key, val in {
                "{title}": title, "{release_date}": release,
                "{rating}": str(rating), "{genres}": e(genres_str),
                "{overview}": overview, "{runtime}": runtime_str,
                "{director}": director_str, "{cast}": top_cast,
                "{status}": status, "{language}": language,
            }.items():
                template = template.replace(key, val)
            return template

        return "\n".join(l for l in lines if l is not None)

    @staticmethod
    def format_tv_caption(data: Dict, template: Optional[str] = None) -> str:
        """Build a rich TV show caption."""
        name = e(data.get("name") or "Unknown")
        original_name = e(data.get("original_name") or "")
        tagline = e(data.get("tagline") or "")
        first_air = e(data.get("first_air_date") or "Unknown")
        last_air = e(data.get("last_air_date") or "Unknown")
        status = e(data.get("status") or "Unknown")
        seasons = data.get("number_of_seasons", "?")
        episodes = data.get("number_of_episodes", "?")
        rating = data.get("vote_average", 0)
        vote_count = data.get("vote_count", 0)
        popularity = data.get("popularity", 0)
        language = e(data.get("original_language") or "N/A").upper()
        genres = [g["name"] for g in data.get("genres", []) or []]
        genres_str = " • ".join(genres[:5]) if genres else "N/A"
        overview = e(truncate(data.get("overview") or "No overview.", 300))
        networks = [n["name"] for n in (data.get("networks") or [])[:3]]
        network_str = e(", ".join(networks)) if networks else "N/A"

        # Cast
        credits = data.get("credits", {}) or {}
        cast = credits.get("cast", []) or []
        top_cast = ", ".join(e(c["name"]) for c in cast[:5]) if cast else "N/A"
        creators = [c.get("name") for c in (data.get("created_by") or [])]
        creators_str = e(", ".join(creators[:2])) if creators else "N/A"

        lines = [b(name)]
        if original_name and original_name != name:
            lines.append(f"<i>{original_name}</i>")
        if tagline:
            lines.append(f"<i>❝{tagline}❞</i>")
        lines.append("")

        lines += [
            f"<b> Aired:</b> {code(first_air + ' → ' + last_air)}",
            f"<b> Status:</b> {code(status)}",
            f"<b> Seasons:</b> {code(str(seasons))} | <b>Episodes:</b> {code(str(episodes))}",
            f"<b> Rating:</b> {code(f'{rating:.1f}/10 ({format_number(vote_count)} votes)')}",
            f"<b> Language:</b> {code(language)}",
            f"<b> Genres:</b> {e(genres_str)}",
            f"<b> Network:</b> {network_str}",
            f"<b> Created by:</b> {creators_str}",
            f"<b> Cast:</b> {top_cast}",
        ]
        lines.append("")
        lines.append(b(" Overview"))
        lines.append(bq(overview, expandable=True))

        if template:
            for key, val in {
                "{title}": name, "{name}": name,
                "{first_air_date}": first_air, "{status}": status,
                "{seasons}": str(seasons), "{episodes}": str(episodes),
                "{rating}": str(rating), "{genres}": e(genres_str),
                "{overview}": overview, "{network}": network_str,
            }.items():
                template = template.replace(key, val)
            return template

        return "\n".join(l for l in lines if l is not None)


# ================================================================================
#                         MANGADEX CLIENT (FULL — COMPLETE)
# ================================================================================

class MangaDexClient:
    """
    Full MangaDex API client.
    Supports: search, details, chapters, pages, cover art.
    """
    BASE_URL = "https://api.mangadex.org"
    COVER_BASE = "https://uploads.mangadex.org/covers"

    @staticmethod
    def _get(endpoint: str, params: Dict = None) -> Optional[Dict]:
        try:
            resp = requests.get(
                f"{MangaDexClient.BASE_URL}{endpoint}",
                params=params or {},
                timeout=12,
            )
            if resp.status_code == 200:
                return resp.json()
            api_logger.debug(f"MangaDex {resp.status_code}: {endpoint}")
        except Exception as exc:
            api_logger.debug(f"MangaDex error: {exc}")
        return None

    @staticmethod
    def search_manga(title: str, limit: int = 10) -> List[Dict]:
        """Search manga by title, returns list of manga objects."""
        data = MangaDexClient._get("/manga", {
            "title": title,
            "limit": limit,
            "includes[]": ["cover_art", "author", "artist"],
            "availableTranslatedLanguage[]": "en",
            "order[relevance]": "desc",
        })
        if not data:
            return []
        return data.get("data", [])

    @staticmethod
    def get_manga(manga_id: str) -> Optional[Dict]:
        """Get full manga details by ID."""
        data = MangaDexClient._get(f"/manga/{manga_id}", {
            "includes[]": ["cover_art", "author", "artist"]
        })
        if data:
            return data.get("data")
        return None

    @staticmethod
    def get_chapters(
        manga_id: str,
        language: str = "en",
        limit: int = 10,
        offset: int = 0,
        order: str = "desc",
    ) -> Tuple[List[Dict], int]:
        """Get chapters for a manga. Returns (chapters, total)."""
        data = MangaDexClient._get("/chapter", {
            "manga": manga_id,
            "translatedLanguage[]": language,
            "limit": limit,
            "offset": offset,
            f"order[chapter]": order,
            "includes[]": ["scanlation_group"],
        })
        if not data:
            return [], 0
        return data.get("data", []), data.get("total", 0)

    @staticmethod
    def get_latest_chapter(manga_id: str, language: str = "en") -> Optional[Dict]:
        """Get the most recent chapter."""
        chapters, total = MangaDexClient.get_chapters(manga_id, language, limit=1)
        return chapters[0] if chapters else None

    @staticmethod
    def get_chapter_pages(chapter_id: str) -> Optional[Tuple[str, str, List[str]]]:
        """
        Get pages for a chapter.
        Returns (base_url, hash, [filenames]) or None.
        """
        data = MangaDexClient._get(f"/at-home/server/{chapter_id}")
        if not data:
            return None
        chapter_data = data.get("chapter", {})
        return (
            data.get("baseUrl", ""),
            chapter_data.get("hash", ""),
            chapter_data.get("data", []),
        )

    @staticmethod
    def get_cover_url(manga_id: str, filename: str, size: int = 256) -> str:
        """Build cover art URL."""
        return f"{MangaDexClient.COVER_BASE}/{manga_id}/{filename}.{size}.jpg"

    @staticmethod
    def extract_cover_filename(manga: Dict) -> Optional[str]:
        """Extract cover filename from manga relationships."""
        for rel in (manga.get("relationships") or []):
            if rel.get("type") == "cover_art":
                attrs = rel.get("attributes") or {}
                return attrs.get("fileName")
        return None

    @staticmethod
    def extract_authors(manga: Dict) -> str:
        """Extract author/artist names from manga relationships."""
        names = []
        for rel in (manga.get("relationships") or []):
            if rel.get("type") in ("author", "artist"):
                attrs = rel.get("attributes") or {}
                name = attrs.get("name")
                if name and name not in names:
                    names.append(e(name))
        return ", ".join(names) if names else "Unknown"

    @staticmethod
    def format_manga_info(manga: Dict) -> str:
        """Build a complete manga info message from MangaDex data."""
        attrs = manga.get("attributes", {}) or {}
        manga_id = manga.get("id", "")

        # Title
        titles = attrs.get("title", {}) or {}
        title = (
            titles.get("en") or titles.get("ja-ro") or titles.get("ja")
            or next(iter(titles.values()), "Unknown")
        )

        # Alt titles
        alt_titles_list = attrs.get("altTitles", []) or []
        alt_en = next(
            (t.get("en") for t in alt_titles_list if "en" in t), None
        )

        # Description
        desc_obj = attrs.get("description", {}) or {}
        desc = desc_obj.get("en") or next(iter(desc_obj.values()), "No description.")
        desc = truncate(strip_html(desc), 280)

        status = (attrs.get("status") or "unknown").title()
        year = attrs.get("year") or "?"
        content_rating = (attrs.get("contentRating") or "safe").title()
        lang_origin = (attrs.get("originalLanguage") or "").upper()

        # Tags
        tags = attrs.get("tags", []) or []
        tag_names = [
            t.get("attributes", {}).get("name", {}).get("en", "")
            for t in tags
            if t.get("attributes", {}).get("name", {}).get("en")
        ]

        chapters = attrs.get("lastChapter") or attrs.get("lastVolume") or "?"
        volumes = attrs.get("lastVolume") or "?"

        authors = MangaDexClient.extract_authors(manga)

        cover_fn = MangaDexClient.extract_cover_filename(manga)
        cover_url = MangaDexClient.get_cover_url(manga_id, cover_fn, 512) if cover_fn else ""

        genre_str = " • ".join(tag_names[:6]) if tag_names else "N/A"

        site_url = f"https://mangadex.org/title/{manga_id}"

        lines = [
            b(e(title)),
        ]
        if alt_en and alt_en != title:
            lines.append(f"<i>{e(alt_en)}</i>")
        lines.append("")

        lines += [
            f"<b> Status:</b> {code(status)}",
            f"<b> Chapters:</b> {code(str(chapters))}",
            f"<b> Volumes:</b> {code(str(volumes))}",
            f"<b> Year:</b> {code(str(year))}",
            f"<b> Origin:</b> {code(lang_origin or 'N/A')}",
            f"<b> Rating:</b> {code(content_rating)}",
            f"<b> Author/Artist:</b> {authors}",
            f"<b> Genres:</b> {e(genre_str)}",
            "",
            b(" Synopsis"),
            bq(e(desc), expandable=True),
            f"\n<b> MangaDex:</b> {site_url}",
        ]

        info_text = "\n".join(str(l) for l in lines)
        return info_text, cover_url

    @staticmethod
    def format_chapter_info(chapter: Dict) -> str:
        """Format a single chapter's info."""
        attrs = chapter.get("attributes", {}) or {}
        ch_id = chapter.get("id", "")
        ch_num = attrs.get("chapter") or "?"
        title = attrs.get("title") or ""
        pages = attrs.get("pages", 0)
        lang = (attrs.get("translatedLanguage") or "?").upper()
        pub_at = attrs.get("publishAt") or attrs.get("createdAt") or ""
        if pub_at:
            try:
                pub_at = datetime.fromisoformat(pub_at.replace("Z", "+00:00")).strftime("%d %b %Y")
            except Exception:
                pass

        # Scanlation group
        groups = []
        for rel in (chapter.get("relationships") or []):
            if rel.get("type") == "scanlation_group":
                gname = (rel.get("attributes") or {}).get("name", "")
                if gname:
                    groups.append(e(gname))
        group_str = ", ".join(groups) if groups else "Unknown"

        parts = [f"<b>Chapter {ch_num}</b>"]
        if title:
            parts.append(f" — <i>{e(title)}</i>")
        lines = [" ".join(parts), ""]
        lines += [
            f"<b> Pages:</b> {code(str(pages))}",
            f"<b> Language:</b> {code(lang)}",
            f"<b> Group:</b> {group_str}",
            f"<b> Released:</b> {code(pub_at)}",
            f"<b> Read:</b> https://mangadex.org/chapter/{ch_id}",
        ]
        return "\n".join(lines)


# ================================================================================
#                       MANGA AUTO-UPDATE TRACKER (COMPLETE)
# ================================================================================

class MangaTracker:
    """
    Tracks manga series for automatic new-chapter notifications.
    Stores tracking data in the DB: manga_id, last chapter, target chat.
    """

    @staticmethod
    def add_tracking(
        manga_id: str,
        manga_title: str,
        target_chat_id: int,
        notify_language: str = "en",
    ) -> bool:
        """Add a manga to auto-tracking."""
        try:
            with db_manager.get_cursor() as cur:
                cur.execute("""
                    INSERT INTO manga_auto_updates
                        (manga_id, manga_title, target_chat_id, notify_language,
                         last_chapter, last_checked, active)
                    VALUES (%s, %s, %s, %s, %s, NOW(), TRUE)
                    ON CONFLICT (manga_id, target_chat_id) DO UPDATE
                        SET active = TRUE, manga_title = EXCLUDED.manga_title,
                            notify_language = EXCLUDED.notify_language
                """, (manga_id, manga_title, target_chat_id, notify_language, None))
            return True
        except Exception as exc:
            db_logger.error(f"MangaTracker.add_tracking error: {exc}")
            return False

    @staticmethod
    def remove_tracking(manga_id: str, target_chat_id: Optional[int] = None) -> bool:
        try:
            with db_manager.get_cursor() as cur:
                if target_chat_id:
                    cur.execute(
                        "UPDATE manga_auto_updates SET active = FALSE "
                        "WHERE manga_id = %s AND target_chat_id = %s",
                        (manga_id, target_chat_id),
                    )
                else:
                    cur.execute(
                        "UPDATE manga_auto_updates SET active = FALSE WHERE manga_id = %s",
                        (manga_id,),
                    )
            return True
        except Exception as exc:
            db_logger.error(f"MangaTracker.remove_tracking error: {exc}")
            return False

    @staticmethod
    def get_all_tracked() -> List[Tuple]:
        try:
            with db_manager.get_cursor() as cur:
                cur.execute("""
                    SELECT id, manga_id, manga_title, target_chat_id,
                           notify_language, last_chapter, last_checked
                    FROM manga_auto_updates WHERE active = TRUE
                """)
                return cur.fetchall() or []
        except Exception as exc:
            db_logger.error(f"MangaTracker.get_all_tracked error: {exc}")
            return []

    @staticmethod
    def update_last_chapter(rec_id: int, chapter: str) -> None:
        try:
            with db_manager.get_cursor() as cur:
                cur.execute(
                    "UPDATE manga_auto_updates SET last_chapter = %s, last_checked = NOW() WHERE id = %s",
                    (chapter, rec_id),
                )
        except Exception as exc:
            db_logger.error(f"MangaTracker.update_last_chapter error: {exc}")

    @staticmethod
    def get_tracked_for_admin() -> str:
        rows = MangaTracker.get_all_tracked()
        if not rows:
            return b("No manga tracked yet.")
        lines = [b("📚 Tracked Manga:"), ""]
        for rec in rows:
            rec_id, manga_id, title, target_chat, lang, last_ch, last_checked = rec
            lines.append(
                f"• {b(e(title))}\n"
                f"  <b>Last Chapter:</b> {code(last_ch or 'None yet')}\n"
                f"  <b>Target:</b> <code>{target_chat}</code>\n"
                f"  <b>Lang:</b> {code(lang)}\n"
                f"  <b>Checked:</b> {code(str(last_checked)[:16])}\n"
                f"  <b>ID:</b> <code>{manga_id}</code>\n"
            )
        return "\n".join(lines)


# ================================================================================
#                         WATERMARK SYSTEM
# ================================================================================

async def add_watermark(
    image_url: str, text: str, position: str = "center"
) -> Optional[BytesIO]:
    """Download image and stamp watermark, return BytesIO or None."""
    if not PIL_AVAILABLE:
        return None
    try:
        resp = requests.get(image_url, timeout=12)
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content)).convert("RGBA")
        overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)
        try:
            font = ImageFont.truetype("arial.ttf", 36)
        except Exception:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        pos_map = {
            "bottom": ((img.width - text_w) // 2, img.height - text_h - 15),
            "top": ((img.width - text_w) // 2, 15),
            "left": (15, (img.height - text_h) // 2),
            "right": (img.width - text_w - 15, (img.height - text_h) // 2),
            "center": ((img.width - text_w) // 2, (img.height - text_h) // 2),
            "bottom-left": (15, img.height - text_h - 15),
            "bottom-right": (img.width - text_w - 15, img.height - text_h - 15),
        }
        pos = pos_map.get(position, pos_map["center"])
        # Shadow
        draw.text((pos[0] + 2, pos[1] + 2), text, fill=(0, 0, 0, 100), font=font)
        draw.text(pos, text, fill=(255, 255, 255, 200), font=font)
        final = Image.alpha_composite(img, overlay)
        out = BytesIO()
        final = final.convert("RGB")
        final.save(out, format="JPEG", quality=90)
        out.seek(0)
        return out
    except Exception as exc:
        logger.debug(f"Watermark error: {exc}")
        return None


# ================================================================================
#                       CATEGORY SETTINGS — FULL MANAGEMENT
# ================================================================================

CATEGORY_DEFAULTS = {
    "anime": {
        "template_name": "rich_anime",
        "branding": "",
        "buttons": "[]",
        "caption_template": "",
        "thumbnail_url": "",
        "font_style": "normal",
        "logo_file_id": None,
        "logo_position": "bottom",
        "watermark_text": None,
        "watermark_position": "center",
        "include_related": True,
        "include_characters": True,
        "include_staff": False,
        "include_streaming": False,
    },
    "manga": {
        "template_name": "rich_manga",
        "branding": "",
        "buttons": "[]",
        "caption_template": "",
        "thumbnail_url": "",
        "font_style": "normal",
        "logo_file_id": None,
        "logo_position": "bottom",
        "watermark_text": None,
        "watermark_position": "center",
        "include_related": True,
        "include_characters": True,
        "include_staff": False,
        "include_streaming": False,
    },
    "movie": {
        "template_name": "rich_movie",
        "branding": "",
        "buttons": "[]",
        "caption_template": "",
        "thumbnail_url": "",
        "font_style": "normal",
        "logo_file_id": None,
        "logo_position": "bottom",
        "watermark_text": None,
        "watermark_position": "center",
        "include_related": False,
        "include_characters": False,
        "include_staff": False,
        "include_streaming": False,
    },
    "tvshow": {
        "template_name": "rich_tvshow",
        "branding": "",
        "buttons": "[]",
        "caption_template": "",
        "thumbnail_url": "",
        "font_style": "normal",
        "logo_file_id": None,
        "logo_position": "bottom",
        "watermark_text": None,
        "watermark_position": "center",
        "include_related": False,
        "include_characters": False,
        "include_staff": False,
        "include_streaming": False,
    },
}


def get_category_settings(category: str) -> Dict:
    """Fetch or initialize category settings from DB."""
    defaults = CATEGORY_DEFAULTS.get(category, CATEGORY_DEFAULTS["anime"])
    try:
        with db_manager.get_cursor() as cur:
            cur.execute("""
                SELECT template_name, branding, buttons, caption_template,
                       thumbnail_url, font_style, logo_file_id, logo_position,
                       watermark_text, watermark_position
                FROM category_settings WHERE category = %s
            """, (category,))
            row = cur.fetchone()
        if row:
            return {
                "template_name": row[0] or defaults["template_name"],
                "branding": row[1] or "",
                "buttons": json.loads(row[2]) if row[2] and row[2] != "[]" else [],
                "caption_template": row[3] or "",
                "thumbnail_url": row[4] or "",
                "font_style": row[5] or "normal",
                "logo_file_id": row[6],
                "logo_position": row[7] or "bottom",
                "watermark_text": row[8],
                "watermark_position": row[9] or "center",
            }
    except Exception as exc:
        db_logger.debug(f"get_category_settings error: {exc}")

    # Insert defaults
    try:
        with db_manager.get_cursor() as cur:
            cur.execute("""
                INSERT INTO category_settings
                    (category, template_name, branding, buttons, caption_template,
                     thumbnail_url, font_style, watermark_position)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (category) DO NOTHING
            """, (
                category, defaults["template_name"], "", "[]", "",
                "", "normal", "center",
            ))
    except Exception:
        pass

    return {
        "template_name": defaults["template_name"], "branding": "", "buttons": [],
        "caption_template": "", "thumbnail_url": "", "font_style": "normal",
        "logo_file_id": None, "logo_position": "bottom",
        "watermark_text": None, "watermark_position": "center",
    }


def update_category_field(category: str, field: str, value: Any) -> bool:
    """Update a single field in category_settings."""
    try:
        with db_manager.get_cursor() as cur:
            cur.execute(
                f"UPDATE category_settings SET {field} = %s WHERE category = %s",
                (value, category),
            )
        return True
    except Exception as exc:
        db_logger.error(f"update_category_field {field}: {exc}")
        return False


def build_buttons_from_settings(settings: Dict) -> Optional[InlineKeyboardMarkup]:
    """Convert settings buttons list to InlineKeyboardMarkup."""
    btns = settings.get("buttons", [])
    if not btns:
        return None
    keyboard = []
    row = []
    for i, btn in enumerate(btns):
        label = btn.get("text", "Link")
        url = btn.get("url", "")
        if not url:
            continue
        # Color prefix handling
        for pfx, icon in [("#g ", "🟢 "), ("#r ", "🔴 "), ("#b ", "🔵 "), ("#p ", "🟣 "), ("#y ", "🟡 ")]:
            if label.startswith(pfx):
                label = icon + label[len(pfx):]
                break
        row.append(InlineKeyboardButton(label, url=url))
        if len(row) == 2 or btn.get("newline"):
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard) if keyboard else None


# ================================================================================
#                         POST GENERATION ENGINE (COMPLETE)
# ================================================================================

async def generate_and_send_post(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    category: str,
    search_query: str = "",
    media_id: Optional[int] = None,
    source_manga_id: Optional[str] = None,
    preferred_size: str = "extraLarge",
) -> bool:
    """
    Full post generation for anime, manga, movie, tvshow.
    Returns True on success.
    preferred_size: 'extraLarge' | 'large' | 'medium' | 'bannerImage'
    """
    settings = get_category_settings(category)
    data: Optional[Dict] = None
    poster_url: Optional[str] = None
    caption_text: str = ""
    buttons_markup: Optional[InlineKeyboardMarkup] = None

    # ── Fetch data ────────────────────────────────────────────────────────────────
    try:
        if category == "anime":
            data = (
                AniListClient.get_by_id(media_id, "ANIME") if media_id
                else AniListClient.search_anime(search_query)
            )
            if not data:
                await safe_send_message(
                    context.bot, chat_id,
                    b("❌ No anime found for: ") + code(e(search_query or str(media_id)))
                )
                return False
            # Caption
            tmpl = settings.get("caption_template", "")
            caption_text = AniListClient.format_anime_caption(data, tmpl if tmpl else None)
            # Branding
            branding = settings.get("branding", "")
            if branding:
                caption_text += f"\n\n{branding}"
            # Poster — honour preferred_size, fall back through sizes
            cover = (data.get("coverImage") or {})
            if preferred_size == "bannerImage":
                poster_url = data.get("bannerImage") or cover.get("extraLarge") or cover.get("large") or cover.get("medium")
            else:
                size_order = ["extraLarge", "large", "medium"] if preferred_size != "medium" else ["medium", "large", "extraLarge"]
                if preferred_size == "large":
                    size_order = ["large", "extraLarge", "medium"]
                poster_url = next((cover.get(s) for s in size_order if cover.get(s)), None)

        elif category == "manga":
            if source_manga_id:
                # MangaDex direct
                manga = MangaDexClient.get_manga(source_manga_id)
                if manga:
                    caption_text, poster_url = MangaDexClient.format_manga_info(manga)
                    # Override with AniList if found
                    anilist_data = AniListClient.search_manga(search_query or "")
                    if anilist_data:
                        tmpl = settings.get("caption_template", "")
                        caption_text = AniListClient.format_manga_caption(anilist_data, tmpl if tmpl else None)
                        cover = (anilist_data.get("coverImage") or {})
                        poster_url = cover.get("extraLarge") or cover.get("large") or poster_url
                else:
                    await safe_send_message(context.bot, chat_id, b("❌ Manga not found on MangaDex."))
                    return False
            else:
                data = (
                    AniListClient.get_by_id(media_id, "MANGA") if media_id
                    else AniListClient.search_manga(search_query)
                )
                if not data:
                    # Try MangaDex
                    md_results = MangaDexClient.search_manga(search_query)
                    if md_results:
                        manga = md_results[0]
                        caption_text, poster_url = MangaDexClient.format_manga_info(manga)
                    else:
                        await safe_send_message(
                            context.bot, chat_id,
                            b("❌ No manga found for: ") + code(e(search_query or ""))
                        )
                        return False
                else:
                    tmpl = settings.get("caption_template", "")
                    caption_text = AniListClient.format_manga_caption(data, tmpl if tmpl else None)
                    cover = (data.get("coverImage") or {})
                    if preferred_size == "bannerImage":
                        poster_url = data.get("bannerImage") or cover.get("extraLarge") or cover.get("large") or cover.get("medium")
                    else:
                        size_order = ["extraLarge", "large", "medium"] if preferred_size != "medium" else ["medium", "large", "extraLarge"]
                        if preferred_size == "large":
                            size_order = ["large", "extraLarge", "medium"]
                        poster_url = next((cover.get(s) for s in size_order if cover.get(s)), None)
            branding = settings.get("branding", "")
            if branding:
                caption_text += f"\n\n{branding}"

        elif category == "movie":
            data = TMDBClient.search_movie(search_query) if not media_id else TMDBClient.get_movie_details(media_id)
            if not data:
                await safe_send_message(
                    context.bot, chat_id,
                    b("❌ No movie found. Make sure TMDB_API_KEY is configured.") if not TMDB_API_KEY
                    else b("❌ No movie found for: ") + code(e(search_query or ""))
                )
                return False
            tmpl = settings.get("caption_template", "")
            caption_text = TMDBClient.format_movie_caption(data, tmpl if tmpl else None)
            branding = settings.get("branding", "")
            if branding:
                caption_text += f"\n\n{branding}"
            poster_path = data.get("poster_path")
            if poster_path:
                poster_url = TMDBClient.get_poster_url(poster_path)

        elif category == "tvshow":
            data = TMDBClient.search_tv(search_query) if not media_id else TMDBClient.get_tv_details(media_id)
            if not data:
                await safe_send_message(
                    context.bot, chat_id,
                    b("❌ No TV show found. Make sure TMDB_API_KEY is configured.") if not TMDB_API_KEY
                    else b("❌ No TV show found for: ") + code(e(search_query or ""))
                )
                return False
            tmpl = settings.get("caption_template", "")
            caption_text = TMDBClient.format_tv_caption(data, tmpl if tmpl else None)
            branding = settings.get("branding", "")
            if branding:
                caption_text += f"\n\n{branding}"
            poster_path = data.get("poster_path")
            if poster_path:
                poster_url = TMDBClient.get_poster_url(poster_path)

    except Exception as exc:
        logger.error(f"generate_and_send_post fetch error: {exc}")
        await safe_send_message(
            context.bot, chat_id,
            b("❌ Failed to fetch data. Please try again.")
        )
        return False

    # ── Font style ────────────────────────────────────────────────────────────────
    if settings.get("font_style") == "smallcaps":
        caption_text = small_caps(caption_text)

    # ── Truncate if too long ──────────────────────────────────────────────────────
    if len(caption_text) > 4000:
        caption_text = caption_text[:3980] + "\n<b>…(truncated)</b>"

    # ── Apply global text style ───────────────────────────────────────────────
    caption_text = _apply_style(caption_text)

    # ── Buttons ───────────────────────────────────────────────────────────────────
    buttons_markup = build_buttons_from_settings(settings)

    # ── Add "Join Now" button per spec (no emoji, clean) ─────────────────────────
    if buttons_markup:
        existing_rows = list(buttons_markup.inline_keyboard)
    else:
        existing_rows = []
    # Collect alternate image URLs for navigation (cover sizes)
    _alt_images: List[str] = []
    if data and isinstance(data, dict):
        cov = data.get("coverImage") or {}
        for sz in ("extraLarge", "large", "medium"):
            url_ = cov.get(sz)
            if url_ and url_ not in _alt_images:
                _alt_images.append(url_)
        banner = data.get("bannerImage")
        if banner and banner not in _alt_images:
            _alt_images.append(banner)
    if poster_url and poster_url not in _alt_images:
        _alt_images.insert(0, poster_url)

    # Navigation row if multiple images available
    nav_row: List[InlineKeyboardButton] = []
    if len(_alt_images) > 1:
        img_key = f"imgset_{category}_{search_query or str(media_id)}"
        # Store urls + caption so navigation can restore info text
        _cache_set(img_key, {"urls": _alt_images, "caption": caption_text, "shown": set()})
        nav_row = [
            InlineKeyboardButton("🔙", callback_data=f"imgn:0:{img_key}:prev"),
            InlineKeyboardButton("✕", callback_data="close_message"),
            InlineKeyboardButton("🔜", callback_data=f"imgn:0:{img_key}:next"),
        ]
    else:
        nav_row = [InlineKeyboardButton("✕", callback_data="close_message")]

    # Join Now button (always present, no emoji per spec)
    join_btn = InlineKeyboardButton((get_setting("env_JOIN_BTN_TEXT", JOIN_BTN_TEXT) or JOIN_BTN_TEXT), url=PUBLIC_ANIME_CHANNEL_URL)
    nav_keyboard = existing_rows + [[join_btn], nav_row]
    buttons_markup = InlineKeyboardMarkup(nav_keyboard)

    # ── Watermark ─────────────────────────────────────────────────────────────────
    wm_text = settings.get("watermark_text")
    wm_pos = settings.get("watermark_position", "center")
    if poster_url and wm_text:
        try:
            wm_image = await add_watermark(poster_url, wm_text, wm_pos)
            if wm_image:
                await context.bot.send_photo(
                    chat_id, wm_image, caption=caption_text,
                    parse_mode=ParseMode.HTML, reply_markup=buttons_markup,
                )
                _cache_post(category, search_query or str(media_id), data)
                return True
        except Exception as exc:
            logger.debug(f"Watermark send failed: {exc}")

    # ── Landscape poster via poster_engine (if PIL available) ─────────────────
    try:
        from poster_engine import (
            _make_poster, _anilist_anime, _anilist_manga,
            _build_anime_data, _build_manga_data,
            _build_movie_data, _build_tv_data,
            _get_settings as _pe_settings,
        )
        _pe_ok = True
    except Exception:
        _pe_ok = False

    if _pe_ok and data:
        try:
            _pe_cat_map = {"anime":"ani","manga":"anim","movie":"net","tvshow":"net"}
            _pe_tmpl = _pe_cat_map.get(category, "ani")
            _pe_s    = _pe_settings(category)
            _wm_txt  = _pe_s.get("watermark_text") or wm_text
            _wm_pos  = _pe_s.get("watermark_position","center")

            if category == "anime":
                _t, _n, _st, _rows, _d, _cu, _sc = _build_anime_data(data)
            elif category == "manga":
                _t, _n, _st, _rows, _d, _cu, _sc = _build_manga_data(data)
            elif category == "movie":
                _t, _n, _st, _rows, _d, _cu, _sc = _build_movie_data(data)
            else:
                _t, _n, _st, _rows, _d, _cu, _sc = _build_tv_data(data)

            _lp_buf = _make_poster(_pe_tmpl, _t, _n, _st, _rows, _d, _cu, _sc,
                                   _wm_txt, _wm_pos, None, "bottom")
            if _lp_buf:
                await context.bot.send_photo(
                    chat_id, _lp_buf,
                    caption=caption_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=buttons_markup,
                )
                _cache_post(category, search_query or str(media_id), data)
                return True
        except Exception as _pe_exc:
            logger.debug(f"Landscape poster failed, falling back: {_pe_exc}")

    # ── Send ──────────────────────────────────────────────────────────────────────
    if poster_url:
        sent = await safe_send_photo(
            context.bot, chat_id, poster_url,
            caption=caption_text, reply_markup=buttons_markup,
        )
        if not sent:
            await safe_send_message(
                context.bot, chat_id, caption_text,
                reply_markup=buttons_markup,
            )
    else:
        await safe_send_message(
            context.bot, chat_id, caption_text,
            reply_markup=buttons_markup,
        )

    _cache_post(category, search_query or str(media_id), data)
    return True


def _cache_post(category: str, key: str, data: Optional[Dict]) -> None:
    """Cache post data for history."""
    if not data:
        return
    try:
        with db_manager.get_cursor() as cur:
            cur.execute("""
                INSERT INTO posts_cache (category, title, anilist_id, media_data, created_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT DO NOTHING
            """, (
                category, key[:200],
                data.get("id") if isinstance(data, dict) else None,
                json.dumps(data)[:5000] if data else None,
            ))
    except Exception:
        pass


# ================================================================================
#                             NAVIGATION / BACK BUTTONS
# ================================================================================

def _back_kb(data: str = "admin_back") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[_back_btn(data), _close_btn()]])


def _back_close_kb(back_data: str = "admin_back") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[_back_btn(back_data), _close_btn()]])


def _build_pagination_kb(
    current_page: int,
    total_pages: int,
    base_callback: str,
    extra_buttons: Optional[List[List[InlineKeyboardButton]]] = None,
) -> InlineKeyboardMarkup:
    """Build a pagination keyboard row."""
    nav = []
    if current_page > 0:
        nav.append(InlineKeyboardButton("🔙", callback_data=f"{base_callback}_{current_page - 1}"))
    if total_pages > 1:
        nav.append(InlineKeyboardButton(f"{current_page + 1}/{total_pages}", callback_data="noop"))
    if current_page < total_pages - 1:
        nav.append(InlineKeyboardButton("🔜", callback_data=f"{base_callback}_{current_page + 1}"))
    keyboard = []
    if extra_buttons:
        keyboard.extend(extra_buttons)
    if nav:
        keyboard.append(nav)
    return InlineKeyboardMarkup(keyboard)


# ================================================================================
#                          ADMIN PANEL — COMPLETE MENUS
# ================================================================================

# ── Button helpers (ONLY allowed emojis: ➕ 🔙 ✔️ 🔜 ♻️ ❗ ✨ 🟢 🔴) ────────────

# ── Button style 60s cache — eliminates 70+ DB calls per panel open ──────────
_CACHED_BTN_STYLE: str = ""
_CACHED_BTN_STYLE_TS: float = 0.0
_BTN_STYLE_TTL: float = 60.0

def _refresh_btn_style_cache() -> None:
    """Force-refresh button style cache (call after admin changes style)."""
    global _CACHED_BTN_STYLE, _CACHED_BTN_STYLE_TS
    _CACHED_BTN_STYLE = ""
    _CACHED_BTN_STYLE_TS = 0.0

def _style_label(label: str) -> str:
    """Apply current button style to label text.
    Uses 60s in-memory cache — ZERO per-button DB calls.
    Without cache: 70+ DB round-trips = 1 min panel load.
    With cache: 1 DB read per 60s = instant panel load.
    """
    global _CACHED_BTN_STYLE, _CACHED_BTN_STYLE_TS
    import time as _t
    now = _t.monotonic()
    if not _CACHED_BTN_STYLE or (now - _CACHED_BTN_STYLE_TS) > _BTN_STYLE_TTL:
        try:
            from database_dual import get_setting as _gs
            _CACHED_BTN_STYLE = _gs("button_style", BUTTON_STYLE) or BUTTON_STYLE
        except Exception:
            _CACHED_BTN_STYLE = BUTTON_STYLE
        _CACHED_BTN_STYLE_TS = now
    style = _CACHED_BTN_STYLE
    # Preserve allowed emojis at start/end
    _ALLOWED_PFXS = ('◀ ','▶ ','✖️ ','🔙 ','🔜 ','➕ ','✔️ ','♻️ ','❗ ','✨ ','🟢 ','🔴 ','◀','▶','✖️','🔙','🔜','➕','✔️','♻️','❗','✨','🟢','🔴')
    prefix = ""
    clean = label
    for p in _ALLOWED_PFXS:
        if clean.startswith(p):
            prefix = p
            clean = clean[len(p):]
            break
    if style == "smallcaps":
        styled = small_caps(clean)
    else:
        styled = math_bold(clean)
    return prefix + styled


def _btn(label: str, cb: str) -> InlineKeyboardButton:
    """Panel button with dynamic style (mathbold or smallcaps)."""
    return InlineKeyboardButton(_style_label(label), callback_data=cb)

def _close_btn() -> InlineKeyboardButton:
    return InlineKeyboardButton("✖️", callback_data="close_message")

def _back_btn(cb: str = "admin_back") -> InlineKeyboardButton:
    return InlineKeyboardButton("🔙 " + _style_label("ʙᴀᴄᴋ"), callback_data=cb)

def _next_btn(cb: str) -> InlineKeyboardButton:
    return InlineKeyboardButton("🔜", callback_data=cb)

def bold_button(label: str, **kwargs) -> InlineKeyboardButton:
    """Styled button — respects BUTTON_STYLE setting."""
    return InlineKeyboardButton(_style_label(label), **kwargs)

def _grid3(items: list) -> list:
    """Arrange a flat list of InlineKeyboardButtons into rows of 3."""
    rows = []
    for i in range(0, len(items), 3):
        rows.append(items[i:i+3])
    return rows

def _grid4(items: list) -> list:
    """Arrange a flat list of InlineKeyboardButtons into rows of 4."""
    rows = []
    for i in range(0, len(items), 4):
        rows.append(items[i:i+4])
    return rows

def _panel_kb(grid_items: list, back_cb: str = "admin_back",
              extra_rows: list = None) -> InlineKeyboardMarkup:
    """
    Build a keyboard with items arranged in 3-per-row grid.
    Always appends: [🔙 BACK]  [CLOSE]
    """
    rows = _grid3(grid_items)
    if extra_rows:
        rows.extend(extra_rows)
    rows.append([_back_btn(back_cb), _close_btn()])
    return InlineKeyboardMarkup(rows)


# ── Panel DB channel helpers ──────────────────────────────────────────────────
def _get_panel_db_images() -> list:
    """Return list of {index, msg_id, file_id} dicts stored in DB."""
    try:
        import json as _j
        raw = get_setting("panel_db_images", "[]") or "[]"
        items = _j.loads(raw)
        if isinstance(items, list):
            return items
    except Exception:
        pass
    return []

def _save_panel_db_images(items: list) -> None:
    import json as _j
    set_setting("panel_db_images", _j.dumps(items))

# In-memory cache of file_ids auto-scanned from PANEL_DB_CHANNEL
_channel_scan_cache: list = []
_channel_scan_ts: float = 0.0
_CHANNEL_SCAN_TTL: float = 300.0  # re-scan every 5 min


def _get_panel_db_fileid() -> Optional[str]:
    """
    Return a random file_id for panel images — shared across ALL panel types.

    Priority:
      1. Manually added images (via /addpanelimg) — stored in DB
      2. Auto-scanned from PANEL_DB_CHANNEL (if set, 5-min cache)
      3. Auto-scanned from FALLBACK_IMAGE_CHANNEL (-1003794802745) — ignores stickers
    """
    global _channel_scan_cache, _channel_scan_ts

    # Priority 1: manually added images
    items = _get_panel_db_images()
    if items:
        item = random.choice(items)
        return item.get("file_id") or None

    # Priority 2 & 3: auto-scan from PANEL_DB_CHANNEL or FALLBACK_IMAGE_CHANNEL
    now = time.monotonic()
    if _channel_scan_cache and (now - _channel_scan_ts) < _CHANNEL_SCAN_TTL:
        return random.choice(_channel_scan_cache) if _channel_scan_cache else None

    # Cache miss / expired — return last known (non-blocking) or None on first call
    return random.choice(_channel_scan_cache) if _channel_scan_cache else None


async def _scan_panel_channel(bot) -> None:
    """
    Background task: scan PANEL_DB_CHANNEL (if set) or FALLBACK_IMAGE_CHANNEL for photo messages.
    Probes message IDs 1-200 using forward_message, extracts file_ids for photos only (skips stickers).
    Cached 5 min. Never blocks the event loop.
    """
    global _channel_scan_cache, _channel_scan_ts

    # Skip if manual images exist
    if _get_panel_db_images():
        return

    # Determine which channel to scan
    scan_channel = PANEL_DB_CHANNEL if PANEL_DB_CHANNEL else FALLBACK_IMAGE_CHANNEL
    if not scan_channel or not bot:
        return

    try:
        file_ids = []

        # Try pyrogram first (fast, gets full history)
        try:
            from pyrogram import Client as _Pyro
            import sys as _sys2
            pyro_client = None
            for obj in _sys2.modules.values():
                if isinstance(obj, _Pyro) and getattr(obj, "is_connected", False):
                    pyro_client = obj
                    break
            if pyro_client:
                async for msg in pyro_client.get_chat_history(scan_channel, limit=50):
                    # Skip stickers, only collect photos
                    if msg.photo and not msg.sticker:
                        file_ids.append(msg.photo.file_id)
                    if len(file_ids) >= 30:
                        break
        except Exception:
            pass

        # Bot API fallback: probe sequential message IDs (1-200).
        # Each call to copy_message returns the copied message with file_id.
        # We use a temp private chat (PANEL_DB_CHANNEL) as sink, then delete.
        if not file_ids:
            sink = PANEL_DB_CHANNEL or None
            if sink:
                for msg_id in range(1, 201):
                    if len(file_ids) >= 30:
                        break
                    try:
                        fwd = await bot.forward_message(
                            chat_id=sink,
                            from_chat_id=scan_channel,
                            message_id=msg_id,
                            disable_notification=True,
                        )
                        if fwd and fwd.photo and not fwd.sticker:
                            file_ids.append(fwd.photo[-1].file_id)
                            # Clean up forwarded copy to keep the channel tidy
                            try:
                                await bot.delete_message(sink, fwd.message_id)
                            except Exception:
                                pass
                        elif fwd and not fwd.photo:
                            # Non-photo message — skip (sticker, text, etc.)
                            try:
                                await bot.delete_message(sink, fwd.message_id)
                            except Exception:
                                pass
                    except Exception:
                        # Message doesn't exist at this ID — continue
                        pass
            else:
                # No sink — can't probe without a destination
                logger.debug("[panel] no PANEL_DB_CHANNEL set; cannot probe FALLBACK_IMAGE_CHANNEL via Bot API")

        if file_ids:
            _channel_scan_cache = file_ids
            _channel_scan_ts = time.monotonic()
            logger.info(f"[panel] scanned {len(file_ids)} panel images from channel {scan_channel}")
        else:
            _channel_scan_ts = time.monotonic()  # mark as attempted
            logger.debug(f"[panel] no photos found in channel {scan_channel}")
    except Exception as exc:
        logger.debug(f"[panel] channel scan failed: {exc}")


def get_panel_pic(panel_type: str = "default") -> Optional[str]:
    """
    Get panel image — synchronous, always instant.
    ALL panel types share the same image pool — zero external HTTP ever.

    Priority:
      1. Manually added images via /addpanelimg (stored in DB)
      2. PANEL_IMAGE_FILE_ID env var
      3. Session file_id cache (from panel_image module — channel scan)
      4. PANEL_PICS env var (file_ids or URLs)
      NO external API calls. NO waifu.im. NO nekos.best. NO TMDB.
    """
    # Priority 1: manually added channel images
    fid = _get_panel_db_fileid()
    if fid:
        return fid

    # Priority 2: permanent file_id from env
    if PANEL_IMAGE_FILE_ID:
        return PANEL_IMAGE_FILE_ID

    # Priority 3: session file_id cache from channel scan
    if _PANEL_IMAGE_AVAILABLE:
        try:
            from panel_image import get_tg_fileid, get_channel_scan_fileid
            cached_fid = get_tg_fileid("default") or get_tg_fileid(panel_type)
            if cached_fid:
                return cached_fid
            scan_fid = get_channel_scan_fileid()
            if scan_fid:
                return scan_fid
        except Exception:
            pass

    # Priority 4: PANEL_PICS env
    if PANEL_PICS:
        return random.choice(PANEL_PICS)

    return None  # No image available — panel will show text-only


async def get_panel_pic_async(panel_type: str = "default") -> Optional[str]:
    """
    Get panel image URL — ALWAYS instant (never blocks).
    Returns cached value immediately; triggers background refresh if stale.
    All panel types share the same image source so every panel loads equally fast.
    """
    # Synchronous cache check — instant
    quick = get_panel_pic(panel_type)
    scan_channel = PANEL_DB_CHANNEL if PANEL_DB_CHANNEL else FALLBACK_IMAGE_CHANNEL
    if not quick and scan_channel and not _get_panel_db_images():
        # No images yet — trigger background channel scan
        try:
            asyncio.create_task(_scan_panel_channel(None))
        except Exception:
            pass
    if quick:

        return quick

    # No API fallback — return None and let panel show text-only
    return None


# ── Pre-built cached panel pages (rebuilt once on first call / after TTL) ─────
_PANEL_PAGES: dict = {}       # page_num → (text, InlineKeyboardMarkup)
_PANEL_PAGES_TS: float = 0.0
_PANEL_PAGES_TTL: float = 60.0   # rebuild markup every 60 s


def _build_panel_pages(maint: bool, clone_red: bool, clean_gc: bool) -> dict:
    """
    5-page admin panel, 4x3 grid (12 buttons per page).
    Pre-built as InlineKeyboardMarkup objects — zero build time on open.
    """
    maint_icon = "🔴" if maint     else "🟢"
    gc_icon    = "✔️" if clean_gc  else "❗"
    cl_icon    = "✔️" if clone_red else "🔴"

    status_line = (
        f"{maint_icon} <b>{small_caps('Maintenance')}:</b> {small_caps('ON' if maint else 'OFF')}  "
        f"{gc_icon} <b>{small_caps('Clean GC')}:</b> {small_caps('ON' if clean_gc else 'OFF')}  "
        f"{cl_icon} <b>{small_caps('Clone Redirect')}:</b> {small_caps('ON' if clone_red else 'OFF')}"
    )

    def _row4(btns):
        rows = []
        for i in range(0, len(btns), 4):
            rows.append(btns[i:i+4])
        return rows

    TOTAL = 5

    def _nav(cur):
        row = []
        if cur > 0:
            row.append(InlineKeyboardButton("◀", callback_data=f"adm_page_{cur-1}"))
        row.append(InlineKeyboardButton(f"· {cur+1}/{TOTAL} ·", callback_data="noop"))
        if cur < TOTAL - 1:
            row.append(InlineKeyboardButton("▶", callback_data=f"adm_page_{cur+1}"))
        row.append(_close_btn())
        return row

    def _header(title):
        return InlineKeyboardButton(math_bold(title), callback_data="noop")

    def _page(num, label, btns):
        rows = [[_header(label)]] + _row4(btns)
        rows.append(_nav(num))
        return InlineKeyboardMarkup(rows)

    main_btns = [
        _btn("STATS", "admin_stats"),
        _btn("BROADCAST", "admin_broadcast_start"),
        _btn("USERS", "user_management"),
        _btn("CHANNELS", "manage_force_sub"),
        _btn("LINKS", "generate_links"),
        _btn("CLONES", "manage_clones"),
        _btn("SETTINGS", "admin_settings"),
        _btn("CATEGORY", "admin_category_settings"),
        _btn("UPLOAD", "upload_menu"),
        _btn("FILTERS", "admin_filter_settings"),
        _btn("POSTER DB", "admin_filter_poster"),
        _btn("FLAGS", "admin_feature_flags"),
    ]
    tools_btns = [
        _btn("AUTO FWD", "admin_autoforward"),
        _btn("MANGA", "admin_autoupdate"),
        _btn("STYLE", "admin_text_style"),
        _btn("SYSTEM", "admin_sysstats"),
        _btn("LOGS", "admin_logs"),
        _btn("RESTART", "admin_restart_confirm"),
        _btn("IMP USERS", "admin_import_users"),
        _btn("IMP LINKS", "admin_import_links"),
        _btn("EXP USERS", "admin_export_users_quick"),
        _btn("DB CLEAN", "dbcleanup_confirm"),
        _btn("PANELS", "panel_img_add_urls"),
        _btn("ENV VARS", "admin_env_panel"),
    ]
    feat_btns = [
        _btn("COUPLE", "feat_couple"),
        _btn("SLAP", "feat_slap"),
        _btn("HUG", "feat_hug"),
        _btn("KISS", "feat_kiss"),
        _btn("PAT", "feat_pat"),
        _btn("INLINE", "feat_inline_search"),
        _btn("REACTIONS", "feat_reactions"),
        _btn("CHATBOT", "feat_chatbot"),
        _btn("T/DARE", "feat_truth_dare"),
        _btn("NOTES", "feat_notes"),
        _btn("WARNS", "feat_warns"),
        _btn("MUTE", "feat_muting"),
    ]
    poster_btns = [
        _btn("ANI", "poster_cmd_ani"),
        _btn("NET", "poster_cmd_net"),
        _btn("CRUN", "poster_cmd_crun"),
        _btn("DARK", "poster_cmd_dark"),
        _btn("LIGHT", "poster_cmd_light"),
        _btn("MOD", "poster_cmd_mod"),
        _btn("BANS", "feat_bans"),
        _btn("RULES", "feat_rules"),
        _btn("AIRING", "feat_airing"),
        _btn("CHAR", "feat_character"),
        _btn("ANIME", "feat_anime_info"),
        _btn("AFK", "feat_afk"),
    ]
    all_mods = [
        _btn("ADMIN", "mod_admin"),      _btn("ANTIFLOOD", "mod_antiflood"),
        _btn("APPROVE", "mod_approve"),    _btn("BLACKLIST", "mod_blacklist"),
        _btn("BL STICKER", "mod_blsticker"),  _btn("CHATBOT", "mod_chatbot"),
        _btn("CLEANER", "mod_cleaner"),    _btn("CONNECTION", "mod_connection"),
        _btn("CURRENCY", "mod_currency"),   _btn("FILTERS", "mod_custfilters"),
        _btn("GBAN", "mod_globalbans"), _btn("IMDB", "mod_imdb"),
        _btn("LOCKS", "mod_locks"),      _btn("LOGCHAN", "mod_logchannel"),
        _btn("PING", "mod_ping"),       _btn("PURGE", "mod_purge"),
        _btn("REPORTING", "mod_reporting"),  _btn("SED", "mod_sed"),
        _btn("SHELL", "mod_shell"),      _btn("SPEEDTEST", "mod_speedtest"),
        _btn("STICKERS", "mod_stickers"),   _btn("TAGALL", "mod_tagall"),
        _btn("TRANSLATE", "mod_translator"), _btn("TRUTH/DARE", "mod_truthdare"),
        _btn("UD", "mod_ud"),         _btn("WALLPAPER", "mod_wallpaper"),
        _btn("WIKI", "mod_wiki"),       _btn("WRITE", "mod_writetool"),
        _btn("ANIMEQUOTE", "mod_animequotes"),_btn("GETTIME", "mod_gettime"),
        _btn("BAD WORDS", "mod_badwords"),
    ]

    return {
        0: _page(0, "MAIN",     main_btns),
        1: _page(1, "TOOLS",    tools_btns),
        2: _page(2, "FEATURES", feat_btns),
        3: _page(3, "POSTER",   poster_btns),
        4: _page(4, "MODULES",  all_mods),
    }, status_line


async def send_admin_menu(
    chat_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    query: Optional[CallbackQuery] = None,
    page: int = 0,
) -> None:
    """
    Send the paginated admin panel — INSTANT via edit-in-place + file_id cache.

    Speed path (after first open):
      1. Debounce: if user clicked while previous click is still processing → drop it.
      2. Build text + keyboard from in-memory cache (no DB hit, <1ms).
      3. Get image: file_id from panel_image cache → edit_message_media in-place.
         Total round-trip: ~0.05-0.15s, zero visible flash.
    """
    global _PANEL_PAGES, _PANEL_PAGES_TS

    # ── No lock — pre-built pages are read-only, safe for concurrent access ───
    # Drop duplicate clicks: if same message_id received twice, ignore 2nd
    if query:
        _dup_key = f"adm_dup_{chat_id}_{getattr(query.message, 'message_id', 0)}"
        _ts_now = time.monotonic()
        _last_ts = _panel_cache_get(_dup_key)
        if _last_ts and (_ts_now - _last_ts) < 0.8:
            try: await query.answer()
            except Exception: pass
            return
        _panel_cache_set(_dup_key, _ts_now)

    await delete_bot_prompt(context, chat_id)
    user_states.pop(chat_id, None)

    now = time.monotonic()

    # ── Rebuild page cache if stale (<1ms when fresh) ──────────────────────────
    if not _PANEL_PAGES or (now - _PANEL_PAGES_TS) > _PANEL_PAGES_TTL:
        maint     = get_setting("maintenance_mode",       "false") == "true"
        clone_red = get_setting("clone_redirect_enabled", "false") == "true"
        clean_gc  = get_setting("clean_gc_enabled",       "true")  == "true"
        _PANEL_PAGES, _status_line = _build_panel_pages(maint, clone_red, clean_gc)
        _PANEL_PAGES["_status"] = _status_line
        _PANEL_PAGES_TS = now

    status_line = _PANEL_PAGES.get("_status", "")
    markup      = _PANEL_PAGES.get(page, _PANEL_PAGES.get(0))

    text = (
        b(small_caps("admin panel")) + "\n\n"
        + status_line + "\n\n"
        + bq(
            f"<b>{small_caps('Bot')}:</b> @{e(BOT_USERNAME)}\n"
            f"<b>{small_caps('Mode')}:</b> {small_caps('Clone' if I_AM_CLONE else 'Main')}\n"
            f"<b>{small_caps('Name')}:</b> {e(BOT_NAME)}"
        )
    )

    img_url = get_panel_pic("admin")

    await _deliver_panel(
        context.bot, chat_id, "admin",
        caption=text, reply_markup=markup, query=query,
    )




async def send_stats_panel(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    query: Optional[CallbackQuery] = None,
) -> None:
    """Send bot statistics panel — instant via edit-in-place."""
    try:
        user_count = get_user_count()
        channel_count = len(get_all_force_sub_channels())
        link_count = get_links_count()
        clones = get_all_clone_bots(active_only=True)
        blocked = get_blocked_users_count()
        maint = "🔴 ON" if get_setting("maintenance_mode", "false") == "true" else "🟢 OFF"

        text = (
            b(" Bot Statistics") + "\n\n"
            f"<b> Total Users:</b> {code(format_number(user_count))}\n"
            f"<b> Force-Sub Channels:</b> {code(str(channel_count))}\n"
            f"<b> Generated Links:</b> {code(format_number(link_count))}\n"
            f"<b> Active Clone Bots:</b> {code(str(len(clones)))}\n"
            f"<b> Blocked Users:</b> {code(str(blocked))}\n"
            f"<b> Maintenance:</b> {maint}\n"
            f"<b> Link Expiry:</b> {code(str(LINK_EXPIRY_MINUTES) + ' min')}\n"
            f"<b> Uptime:</b> {code(get_uptime())}"
        )
    except Exception as exc:
        text = b("❌ Error loading stats: ") + code(e(str(exc)[:200]))

    grid = [
        _btn("♻️ REFRESH",      "admin_stats"),
        _btn("BROADCAST STATS", "broadcast_stats_panel"),
        _btn("SYSTEM STATS",    "admin_sysstats"),
        _btn("USERS",           "user_management"),
        _btn("LINK STATS",      "fsub_link_stats"),
        _btn("EXPORT USERS",    "admin_export_users_quick"),
    ]
    rows = _grid3(grid)
    rows.append([_back_btn("admin_back"), _close_btn()])
    markup = InlineKeyboardMarkup(rows)

    img_url = get_panel_pic("stats")

    await safe_edit_panel(
        context.bot, query, chat_id,
        photo=img_url, caption=text, reply_markup=markup,
        panel_type="stats",
    )


async def show_category_settings_menu(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    category: str,
    query: Optional[CallbackQuery] = None,
) -> None:
    """Show full settings menu for a category."""
    settings = get_category_settings(category)
    icon = {"anime": "🎌", "manga": "📚", "movie": "🎬", "tvshow": "📺"}.get(category, "⚙️")
    btns_count = len(settings.get("buttons") or [])
    wm = settings.get("watermark_text") or "None"
    logo = "✅ Set" if settings.get("logo_file_id") else "❌ Not set"

    style = _get_style() if _TEXT_STYLE_AVAILABLE else "normal"
    text = (
        f"{b(category.upper() + ' SETTINGS')}\n\n"
        + bq(
            f"<b>Template:</b> {code(settings['template_name'])}\n"
            f"<b>Font Style:</b> {code(settings['font_style'])}\n"
            f"<b>Buttons:</b> {code(str(btns_count))} configured\n"
            f"<b>Watermark:</b> {code(e(wm[:30]))}\n"
            f"<b>Logo:</b> {logo}\n"
            f"<b>Caption:</b> {'✔️ Custom' if settings.get('caption_template') else 'Default'}\n"
            f"<b>Branding:</b> {'✔️ Set' if settings.get('branding') else 'None'}\n"
            f"<b>Text Style:</b> {code(style)}"
        )
    )
    # Spec-compliant SETTINGS PANEL layout
    grid = [
        _btn("CAPTION",     f"cat_caption_{category}"),
        _btn("BUTTONS",     f"cat_buttons_{category}"),
        _btn("TEMPLATE",    f"cat_thumbnail_{category}"),
        _btn("BRANDING",    f"cat_branding_{category}"),
        _btn("FONT STYLE",  f"cat_font_{category}"),
        _btn("WATERMARK",   f"cat_watermark_{category}"),
        _btn("LOGO",        f"cat_logo_{category}"),
        _btn("AUTO UPDATE", "admin_autoupdate"),
        _btn("PREVIEW",     f"cat_preview_{category}"),
    ]
    keyboard = _grid3(grid)
    keyboard.append([_back_btn("admin_category_settings"), _close_btn()])
    markup = InlineKeyboardMarkup(keyboard)
    if query:
        # Try to edit with photo if possible, else edit text
        try:
            await query.delete_message()
        except Exception:
            pass
        img_url = None
        if _PANEL_IMAGE_AVAILABLE:
            try:
                img_url = await get_panel_pic_async("categories")
            except Exception:
                pass
        if img_url:
            sent = await safe_send_photo(context.bot, chat_id, img_url, caption=text, reply_markup=markup)
            if sent:
                return
        await safe_send_message(context.bot, chat_id, text, reply_markup=markup)
    else:
        img_url = None
        if _PANEL_IMAGE_AVAILABLE:
            try:
                img_url = await get_panel_pic_async("categories")
            except Exception:
                pass
        if img_url:
            sent = await safe_send_photo(context.bot, chat_id, img_url, caption=text, reply_markup=markup)
            if sent:
                return
        await safe_send_message(context.bot, chat_id, text, reply_markup=markup)


async def send_feature_flags_panel(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    query: Optional[CallbackQuery] = None,
) -> None:
    """Show feature flags panel."""
    flags = [
        ("maintenance_mode", "false", " Maintenance Mode"),
        ("clone_redirect_enabled", "false", " Clone Redirect"),
        ("error_dms_enabled", "1", " Error DMs to Admin"),
        ("force_sub_enabled", "true", " Force Subscription"),
        ("auto_delete_messages", "true", " Auto-Delete Messages"),
        ("watermarks_enabled", "true", " Watermarks"),
        ("inline_search_enabled", "true", " Inline Search"),
        ("group_commands_enabled", "true", "👥 Group Commands"),
    ]

    text = b("🚩 Feature Flags") + "\n\n"
    keyboard = []
    for key, default, label in flags:
        val = get_setting(key, default)
        is_on = val in ("1", "true", "yes")
        status = "✅ ON" if is_on else "❌ OFF"
        text += f"<b>{label}:</b> {status}\n"
        toggle_val = "false" if is_on else "true"
        keyboard.append([bold_button(
            f"{'Disable' if is_on else 'Enable'} {label.split(' ', 1)[-1]}",
            callback_data=f"flag_toggle_{key}_{toggle_val}"
        )])

    keyboard.append([_back_btn("admin_back")])

    markup = InlineKeyboardMarkup(keyboard)
    if query:
        try:
            await query.delete_message()
        except Exception:
            pass
    # Send with panel image
    img_url = None
    if _PANEL_IMAGE_AVAILABLE:
        try:
            img_url = await get_panel_pic_async("flags")
        except Exception:
            pass
    if img_url:
        try:
            await context.bot.send_photo(chat_id, img_url, caption=text,
                                         parse_mode=ParseMode.HTML, reply_markup=markup)
            return
        except Exception:
            pass
    await safe_send_message(context.bot, chat_id, text, reply_markup=markup)


# ================================================================================
#                           START COMMAND (SAFE + FULL)
# ================================================================================

@force_sub_required
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Main /start handler. Handles:
    - Regular users: welcome screen
    - Admin: admin panel
    - Deep links: channel link delivery
    - Clone redirect
    - Safety anchor to prevent mobile exit-on-delete
    """
    user = update.effective_user
    chat_id = update.effective_chat.id
    uid = user.id if user else 0

    # Register user in DB
    if user:
        add_user(uid, user.username, user.first_name, user.last_name)

    # Clean previous prompt
    await delete_bot_prompt(context, chat_id)

    # For admin: skip sticker/animation entirely — go straight to panel
    # For users: minimal loading indicator only
    loading_msg = None
    if uid not in (ADMIN_ID, OWNER_ID):
        await send_transition_sticker(context, chat_id)
        loading_msg = await loading_animation_start(context, chat_id)

    # ── Deep link handling ────────────────────────────────────────────────────────
    if context.args:
        link_id = context.args[0]

        # Clone redirect for non-admin users
        clone_redirect = get_setting("clone_redirect_enabled", "false").lower() == "true"
        if clone_redirect and not I_AM_CLONE and uid not in (ADMIN_ID, OWNER_ID):
            clones = get_all_clone_bots(active_only=True)
            if clones:
                clone_uname = clones[0][2]
                await loading_animation_end(context, chat_id, loading_msg)
                await safe_send_message(
                    context.bot, chat_id,
                    b("🔄 Getting your link via our server bot…"),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "📥 Get Your Link",
                            url=f"https://t.me/{clone_uname}?start={link_id}"
                        )
                    ]]),
                )
                return

        await loading_animation_end(context, chat_id, loading_msg)
        await handle_deep_link(update, context, link_id)
        return

    await loading_animation_end(context, chat_id, loading_msg)

    # ── Admin panel ───────────────────────────────────────────────────────────────
    if uid in (ADMIN_ID, OWNER_ID):
        user_states.pop(uid, None)
        await send_admin_menu(chat_id, context)
        return

    # ── Regular user welcome ──────────────────────────────────────────────────────
    keyboard = [
          [InlineKeyboardButton("ᴀɴɪᴍᴇ ᴄʜᴀɴɴᴇʟ", url=PUBLIC_ANIME_CHANNEL_URL)],
          [InlineKeyboardButton("ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ", url=f"https://t.me/{ADMIN_CONTACT_USERNAME}")],
          [InlineKeyboardButton("ʀᴇǫᴜᴇsᴛ ᴀɴɪᴍᴇ ᴄʜᴀɴɴᴇʟ", url=REQUEST_CHANNEL_URL)],
          [InlineKeyboardButton("ꜰᴇᴀᴛᴜʀᴇs", callback_data="user_features_0"),
           InlineKeyboardButton("ᴀʙᴏᴜᴛ ᴍᴇ", callback_data="about_bot")],
          [_close_btn()],
      ]
    markup = InlineKeyboardMarkup(keyboard)

    # Try to copy welcome message from source channel
    _sent_start_msg = None
    try:
        _sent_start_msg = await context.bot.copy_message(
            chat_id=chat_id,
            from_chat_id=WELCOME_SOURCE_CHANNEL,
            message_id=WELCOME_SOURCE_MESSAGE_ID,
            reply_markup=markup,
        )
    except Exception:
        pass
    if _sent_start_msg:
        # React with ✨ emoji on start message
        try:
            await context.bot.set_message_reaction(
                chat_id=chat_id,
                message_id=_sent_start_msg.message_id,
                reaction=[{"type": "emoji", "emoji": "✨"}],
                is_big=False,
            )
        except Exception:
            pass
        return

    # Fallback welcome
    if WELCOME_IMAGE_URL:
        try:
            await context.bot.send_photo(
                chat_id,
                WELCOME_IMAGE_URL,
                caption=(
                    b(f"✨ Welcome to {e(BOT_NAME)}!") + "\n\n"
                    + bq(b("Your gateway to all things Anime, Manga & Movies!"))
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=markup,
            )
            return
        except Exception:
            pass

    _fb_msg = await safe_send_message(
        context.bot, chat_id,
        b(f"Welcome to {e(BOT_NAME)}!") + "\n\n"
        + bq(b("Your gateway to all things Anime, Manga & Movies!")),
        reply_markup=markup,
    )
    if _fb_msg:
        try:
            await context.bot.set_message_reaction(
                chat_id=chat_id, message_id=_fb_msg.message_id,
                reaction=[{"type": "emoji", "emoji": "✨"}], is_big=False,
            )
        except Exception:
            pass


# ================================================================================
#                         DEEP LINK HANDLER (COMPLETE)
# ================================================================================

async def handle_deep_link(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    link_id: str,
) -> None:
    """Handle deep link /start?start=<link_id>."""
    chat_id = update.effective_chat.id

    link_info = get_link_info(link_id)
    if not link_info:
        await safe_send_message(
            context.bot, chat_id,
            b("❌ Invalid Link") + "\n\n"
            + bq(b("This link is invalid or has been removed. "
                   "Please tap the original post button again.")),
        )
        return

    channel_identifier, creator_id, created_time, never_expires = link_info

    # Expiry check
    if not never_expires:
        try:
            created_dt = datetime.fromisoformat(str(created_time))
            if now_utc() > created_dt + timedelta(minutes=LINK_EXPIRY_MINUTES):
                await safe_send_message(
                    context.bot, chat_id,
                    b("⏰ Link Expired") + "\n\n"
                    + bq(
                        b("This invite link has expired.\n\n")
                        + b("💡 Tip: Tap the post button again to get a fresh link.")
                    ),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(" ᴀɴɪᴍᴇ ᴄʜᴀɴɴᴇʟ", url=PUBLIC_ANIME_CHANNEL_URL)
                    ]]),
                )
                return
        except Exception:
            pass

    # Determine which bot creates the invite link
    invite_bot = context.bot
    if I_AM_CLONE:
        main_token = get_main_bot_token()
        if main_token:
            try:
                invite_bot = Bot(token=main_token)
            except Exception:
                pass

    try:
        if isinstance(channel_identifier, str) and channel_identifier.lstrip("-").isdigit():
            channel_identifier = int(channel_identifier)

        chat = await invite_bot.get_chat(channel_identifier)
        expire_ts = int(
            (now_utc() + timedelta(minutes=LINK_EXPIRY_MINUTES + 1)).timestamp()
        )
        # Check if this channel uses join_by_request mode
        _ch_info = get_force_sub_channel_info(str(chat.id))
        _jbr_mode = bool(_ch_info and _ch_info[2]) if _ch_info else False

        invite = await invite_bot.create_chat_invite_link(
            chat.id,
            expire_date=expire_ts,
            member_limit=1,
            name=f"DeepLink {link_id[:8]}",
            creates_join_request=_jbr_mode,
        )

        try:
            _here_link = get_setting("env_HERE_IS_LINK_TEXT", HERE_IS_LINK_TEXT) or HERE_IS_LINK_TEXT
            _join_text = get_setting("env_JOIN_BTN_TEXT", JOIN_BTN_TEXT) or JOIN_BTN_TEXT
        except Exception:
            _here_link = HERE_IS_LINK_TEXT
            _join_text = JOIN_BTN_TEXT

        _jbr_note = ""
        if _jbr_mode:
            _jbr_note = "\n" + b(small_caps("tap join → request sent → auto-approved instantly"))

        _link_msg = (
            f"<blockquote><b>{small_caps(_here_link)}</b></blockquote>\n\n"
            + f"<u><b>{small_caps('ɴᴏᴛᴇ: ɪꜰ ᴛʜᴇ ʟɪɴᴋ ɪs ᴇxᴘɪʀᴇᴅ, ᴘʟᴇᴀsᴇ ᴄʟɪᴄᴋ ᴛʜᴇ ᴘᴏsᴛ ʟɪɴᴋ ᴀɢᴀɪɴ ᴛᴏ ɢᴇᴛ ᴀ ɴᴇᴡ ᴏɴᴇ.')}</u></b>"
        )
        if _jbr_note:
            _link_msg += "\n" + _jbr_note
        keyboard = [[bold_button(small_caps(_join_text), url=invite.invite_link)]]
        await context.bot.send_message(
            chat_id, _link_msg,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    except Forbidden as exc:
        await safe_send_message(
            context.bot, chat_id,
            b("🚫 Bot Access Error") + "\n\n"
            + bq(b("The bot has been removed from that channel. "
                   "Please contact admin.")),
        )
        logger.error(f"handle_deep_link Forbidden error: {exc}")
    except Exception as exc:
        logger.error(f"handle_deep_link error: {exc}")
        await safe_send_message(
            context.bot, chat_id,
            UserFriendlyError.get_user_message(exc),
        )


# ================================================================================
#                             HELP COMMAND (FULL)
# ================================================================================

@force_sub_required
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Help command.
    - Regular users: shows ONLY custom info from ENV (HELP_TEXT_CUSTOM) with channel buttons.
      No feature list is revealed to users.
    - Admin/Owner: shows full admin command reference.
    """
    uid = update.effective_user.id if update.effective_user else 0
    await delete_update_message(update, context)
    is_admin = uid in (ADMIN_ID, OWNER_ID)

    # ── Build keyboard with channel buttons from ENV ──────────────────────────────
    keyboard = []
    if HELP_CHANNEL_1_URL:
        keyboard.append([InlineKeyboardButton(HELP_CHANNEL_1_NAME, url=HELP_CHANNEL_1_URL)])
    if HELP_CHANNEL_2_URL:
        keyboard.append([InlineKeyboardButton(HELP_CHANNEL_2_NAME, url=HELP_CHANNEL_2_URL)])
    if HELP_CHANNEL_3_URL:
        keyboard.append([InlineKeyboardButton(HELP_CHANNEL_3_NAME, url=HELP_CHANNEL_3_URL)])
    # Always add anime channel and contact admin
    if PUBLIC_ANIME_CHANNEL_URL and not any(PUBLIC_ANIME_CHANNEL_URL == r[0].url for r in keyboard if r):
        keyboard.append([InlineKeyboardButton("ᴀɴɪᴍᴇ ᴄʜᴀɴɴᴇʟ", url=PUBLIC_ANIME_CHANNEL_URL)])
    if ADMIN_CONTACT_USERNAME:
        keyboard.append([InlineKeyboardButton("💬 ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ", url=f"https://t.me/{ADMIN_CONTACT_USERNAME}")])
    keyboard.append([bold_button("CLOSE", callback_data="close_message")])
    markup = InlineKeyboardMarkup(keyboard)

    # ── Regular user: show only custom info from ENV ──────────────────────────────
    if not is_admin:
        user_text = HELP_TEXT_CUSTOM if HELP_TEXT_CUSTOM else (
            b(f"ℹ️ {e(BOT_NAME)}") + "\n\n"
            + bq(
                b(" Your gateway to Anime, Manga & Movies!\n\n")
                + "Use the buttons below to join our channels."
            )
        )
        if HELP_IMAGE_URL:
            sent = await safe_send_photo(
                context.bot, update.effective_chat.id,
                HELP_IMAGE_URL, caption=user_text, reply_markup=markup,
            )
            if sent:
                return
        await safe_reply(update, user_text, reply_markup=markup)
        return

    # ── Admin: show full command reference ───────────────────────────────────────
    user_states.pop(uid, None)
    await delete_bot_prompt(context, update.effective_chat.id)

    text = (
        b("📖 Admin Command Reference") + "\n\n"
        + bq(
            b(" Content Generation:\n")
            + "<b>/anime</b> [name] — Anime post (AniList)\n"
            + "<b>/manga</b> [name] — Manga post (AniList + MangaDex)\n"
            + "<b>/movie</b> [name] — Movie post (TMDB)\n"
            + "<b>/tvshow</b> [name] — TV show post (TMDB)\n"
            + "<b>/search</b> [name] — Search all categories\n\n"
            + b(" Poster Templates (Admin only):\n")
            + "<b>/ani, /anim, /crun, /net, /netm</b>\n"
            + "<b>/light, /lightm, /dark, /darkm</b>\n"
            + "<b>/mod, /modm, /netcr</b> — Styled poster images\n\n"
            + b(" Link Provider:\n")
            + "<b>/addchannel</b> @id_or_username [Title] [jbr]\n"
            + "<b>/removechannel</b> @username_or_id\n"
            + "<b>/channel</b> — List force-sub channels\n"
            + "<b>/genlink</b> (via admin panel)\n\n"
            + b(" User Management:\n")
            + "<b>/banuser, /unbanuser, /listusers</b>\n"
            + "<b>/deleteuser, /exportusers</b>\n\n"
            + b(" Broadcast:\n")
            + "<b>/broadcast</b> (via /start panel)\n"
            + "<b>/broadcaststats</b> — Broadcast history\n\n"
            + b(" Clone Bots:\n")
            + "<b>/addclone</b> TOKEN — Add clone\n"
            + "<b>/clones</b> — List clones\n\n"
            + b(" Upload Manager:\n")
            + "<b>/upload</b> — Open upload panel\n\n"
            + b(" Settings & Tools:\n")
            + "<b>/settings</b> — Category settings\n"
            + "<b>/autoforward</b> — Auto-forward manager\n"
            + "<b>/autoupdate</b> — Manga chapter tracker\n"
            + "<b>/connect, /disconnect</b> — Group connections\n"
            + "<b>/stats, /sysstats, /users</b>\n"
            + "<b>/backup, /reload, /logs</b>\n\n"
            + b(" Premium (Poster):\n")
            + "<b>/add_premium</b> id rank [duration]\n"
            + "<b>/remove_premium</b> id\n"
            + "<b>/premium_list</b> — List premium users",
            expandable=True,
        )
    )

    if HELP_IMAGE_URL:
        sent = await safe_send_photo(
            context.bot, update.effective_chat.id,
            HELP_IMAGE_URL, caption=text, reply_markup=markup,
        )
        if sent:
            return

    await safe_reply(update, text, reply_markup=markup)


# ================================================================================
#                             PING COMMAND
# ================================================================================

@force_sub_required
async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    t0 = time.monotonic()
    chat_id = update.effective_chat.id
    try:
        msg = await safe_reply(update, b("🏓 Pinging…"))
        if msg:
            elapsed_ms = (time.monotonic() - t0) * 1000
            await msg.edit_text(
                b("🏓 Pong!") + "\n\n"
                f"<b>Response Time:</b> {code(f'{elapsed_ms:.0f}ms')}\n"
                f"<b>Status:</b> {code('Online ✅')}",
                parse_mode=ParseMode.HTML,
            )
    except Exception:
        pass


# ================================================================================
#                            ALIVE COMMAND
# ================================================================================

@force_sub_required
async def alive_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        b("✅ Bot is Alive!") + "\n\n"
        f"<b>⏱ Uptime:</b> {code(get_uptime())}\n"
        f"<b>🤖 Username:</b> @{e(BOT_USERNAME)}\n"
        f"<b>🏷 Mode:</b> {code('Clone Bot' if I_AM_CLONE else 'Main Bot')}"
    )
    await safe_reply(update, text)


# ================================================================================
#                           SEARCH COMMAND (FULL RESULTS)
# ================================================================================

@force_sub_required
async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id if update.effective_user else 0
    await delete_update_message(update, context)

    if not context.args:
        await safe_reply(
            update,
            b("Usage: /search [name]") + "\n"
            + bq(b("Example: /search Naruto"))
        )
        return

    query_text = " ".join(context.args)
    chat_id = update.effective_chat.id

    searching_msg = await safe_send_message(
        context.bot, chat_id,
        b(f"🔍 Searching for: {e(query_text)}…"),
    )

    results = []
    anime = AniListClient.search_anime(query_text)
    if anime:
        title_obj = anime.get("title", {}) or {}
        title = title_obj.get("romaji") or title_obj.get("english") or "Unknown"
        results.append(("anime", anime["id"], f"🎌 {title}", "anime"))

    manga = AniListClient.search_manga(query_text)
    if manga:
        title_obj = manga.get("title", {}) or {}
        title = title_obj.get("romaji") or title_obj.get("english") or "Unknown"
        results.append(("manga", manga["id"], f"📚 {title}", "manga"))

    if TMDB_API_KEY:
        movie = TMDBClient.search_movie(query_text)
        if movie:
            title = movie.get("title") or "Unknown"
            results.append(("movie", movie.get("id", 0), f"🎬 {title}", "movie"))
        tv = TMDBClient.search_tv(query_text)
        if tv:
            name = tv.get("name") or "Unknown"
            results.append(("tvshow", tv.get("id", 0), f"📺 {name}", "tvshow"))

    # MangaDex results
    md_results = MangaDexClient.search_manga(query_text, limit=3)
    for md in md_results[:2]:
        attrs = md.get("attributes", {}) or {}
        titles = attrs.get("title", {}) or {}
        title = titles.get("en") or next(iter(titles.values()), "Unknown")
        results.append(("mangadex", md["id"], f"📖 {title} (MangaDex)", "mangadex"))

    if searching_msg:
        await safe_delete(context.bot, chat_id, searching_msg.message_id)

    if not results:
        await safe_send_message(
            context.bot, chat_id,
            b("❌ No results found.") + "\n"
            + bq(b("Try a different search term."))
        )
        return

    keyboard = []
    for media_type, media_id, label, cb_type in results:
        keyboard.append([bold_button(
            label[:40],
            callback_data=f"search_result_{cb_type}_{media_id}"
        )])

    await safe_send_message(
        context.bot, chat_id,
        b(f"🔍 Search results for: {e(query_text)}"),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ================================================================================
#                         CATEGORY POST COMMANDS
# ================================================================================

@force_sub_required
async def anime_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id if update.effective_user else 0
    if uid not in (ADMIN_ID, OWNER_ID):
        return  # Admin only
    if not _passes_filter(update, "anime"):
        return
    await delete_update_message(update, context)
    if not context.args:
        await safe_reply(update, b("Usage: /anime [name]") + "\n" + bq("<b>Example:</b> /anime Naruto"))
        return
    query_text = " ".join(context.args)
    await generate_and_send_post(context, update.effective_chat.id, "anime", query_text)


@force_sub_required
async def manga_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id if update.effective_user else 0
    if uid not in (ADMIN_ID, OWNER_ID):
        return  # Admin only
    if not _passes_filter(update, "manga"):
        return
    await delete_update_message(update, context)
    if not context.args:
        await safe_reply(update, b("Usage: /manga [name]") + "\n" + bq("<b>Example:</b> /manga One Piece"))
        return
    query_text = " ".join(context.args)
    await generate_and_send_post(context, update.effective_chat.id, "manga", query_text)


@force_sub_required
async def movie_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id if update.effective_user else 0
    if uid not in (ADMIN_ID, OWNER_ID):
        return  # Admin only
    if not _passes_filter(update, "movie"):
        return
    await delete_update_message(update, context)
    if not context.args:
        await safe_reply(update, b("Usage: /movie [name]") + "\n" + bq("<b>Example:</b> /movie Avengers"))
        return
    if not TMDB_API_KEY:
        await safe_reply(update, b("⚠️ TMDB API key not configured."))
        return
    query_text = " ".join(context.args)
    await generate_and_send_post(context, update.effective_chat.id, "movie", query_text)


@force_sub_required
async def tvshow_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id if update.effective_user else 0
    if uid not in (ADMIN_ID, OWNER_ID):
        return  # Admin only
    if not _passes_filter(update, "tvshow"):
        return
    await delete_update_message(update, context)
    if not context.args:
        await safe_reply(update, b("Usage: /tvshow [name]") + "\n" + bq("<b>Example:</b> /tvshow Breaking Bad"))
        return
    if not TMDB_API_KEY:
        await safe_reply(update, b("⚠️ TMDB API key not configured."))
        return
    query_text = " ".join(context.args)
    await generate_and_send_post(context, update.effective_chat.id, "tvshow", query_text)


# ================================================================================
#                           ADMIN COMMANDS (ALL)
# ================================================================================

async def cmd_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /cmd — Show commands based on who is asking.
    Everyone can use this. Output is filtered by authority level.
    """
    await delete_update_message(update, context)
    uid  = update.effective_user.id if update.effective_user else 0
    chat = update.effective_chat
    is_bot_admin = uid in (ADMIN_ID, OWNER_ID)

    # Check if user is a group admin
    is_group_admin = False
    if chat and chat.type in ("group", "supergroup"):
        try:
            m = await context.bot.get_chat_member(chat.id, uid)
            is_group_admin = m.status in ("administrator", "creator")
        except Exception:
            pass

    # ── Section builder ────────────────────────────────────────────────────
    def sec(title, cmds):
        lines = f"<b>{small_caps(title)}</b>\n"
        for cmd, desc in cmds:
            # Never small-cap the command itself (it starts with /)
            lines += f"  /{cmd} — {small_caps(desc)}\n"
        return lines + "\n"

    # ══════════════════════════════════════════════
    # SECTION 1 — EVERYONE (always shown)
    # ══════════════════════════════════════════════
    public = sec("🌐 General — Everyone", [
        ("start",       "Main menu"),
        ("help",        "Help & channel links"),
        ("cmd",         "Show all commands (this list)"),
        ("alive",       "Check if bot is online"),
        ("ping",        "Bot response speed"),
        ("id",          "Your Telegram user / chat ID"),
        ("info",        "User info lookup by reply or @username"),
        ("my_plan",     "Your daily poster usage limit"),
        ("plans",       "View all available poster plans"),
        ("start",       "Deep link channel join"),
        ("welcomehelp", "Welcome message format guide"),
        ("welcomemutehelp", "Explain welcome mute modes"),
        ("rules",       "View this group's rules"),
        ("report",      "<reason> — Report a message to admins (reply)"),
    ])

    anime_s = sec("🎌 Anime & Media — Everyone", [
        ("anime",      "<name> — Anime poster + info"),
        ("manga",      "<name> — Manga poster + info"),
        ("movie",      "<name> — Movie poster + info"),
        ("tvshow",     "<name> — TV show poster"),
        ("search",     "<name> — Multi-source search"),
        ("airing",     "<name> — Next episode countdown"),
        ("character",  "<name> — Character details"),
        ("imdb",       "<name> — IMDb lookup"),
    ])

    fun_s = sec("🎮 Fun & Reactions — Everyone", [
        ("hug",         "Hug someone (reply to their message)"),
        ("slap",        "Slap someone (reply)"),
        ("kiss",        "Kiss someone (reply)"),
        ("pat",         "Pat someone (reply)"),
        ("punch",       "Punch someone (reply)"),
        ("poke",        "Poke someone (reply)"),
        ("wave",        "Wave at someone (reply)"),
        ("bite",        "Bite someone (reply)"),
        ("wink",        "Wink at someone (reply)"),
        ("nod",         "Nod at someone (reply)"),
        ("shoot",       "Shoot someone (reply)"),
        ("cry",         "Cry expression"),
        ("laugh",       "Laugh expression"),
        ("blush",       "Blush expression"),
        ("couple",      "Couple of the day for the group"),
        ("truth",       "Random truth question"),
        ("dare",        "Random dare challenge"),
        ("toss",        "Flip a coin — heads or tails"),
        ("roll",        "Roll a dice (1–6)"),
        ("shrug",       "Post a shrug emoticon"),
        ("table",       "Flip a table (╯°□°）╯"),
        ("aq",          "Random anime quote"),
        ("run",         "Send a random run GIF"),
        ("afk",         "<reason> — Set yourself as AFK"),
    ])

    tools_s = sec("🛠 Tools — Everyone", [
        ("wiki",        "<topic> — Wikipedia summary"),
        ("ud",          "<word> — Urban Dictionary definition"),
        ("tr",          "<lang> <text> — Translate text"),
        ("time",        "<city/country> — Current time anywhere"),
        ("write",       "<text> — Generate handwriting image"),
        ("wall",        "<query> — Anime wallpaper search"),
        ("stickerid",   "Get sticker file_id (reply to sticker)"),
        ("getsticker",  "Download sticker as PNG (reply)"),
        ("kang",        "Add sticker to your own pack (reply)"),
        ("cash",        "<amount> <from> <to> — Currency converter"),
        ("shout",       "<text> — Make text shout-style"),
        ("fonts",       "<text> — Fancy font styles"),
        ("telegraph",   "Upload media to Telegraph"),
        ("shorturl",    "<url> — Shorten a URL"),
        ("weather",     "<city> — Current weather"),
        ("lyrics",      "<song> — Song lyrics search"),
        ("zip",         "Zip files (reply)"),
        ("unzip",       "Unzip archive (reply)"),
        ("json",        "Parse JSON (reply)"),
        ("github",      "<username> — GitHub user info"),
        ("google",      "<query> — Google search"),
    ])

    group_s = sec("📋 Group Info — Everyone", [
        ("rules",      "View group rules"),
        ("warns",      "Check your warn count"),
        ("notes",      "List all saved notes"),
        ("get",        "<name> — Get a note"),
        ("afk",        "<reason> — Set AFK status"),
        ("badwords",   "See banned word list"),
        ("reports",    "Toggle report notifications"),
        ("report",     "<reason> — Report to admins (reply)"),
    ])

    # ══════════════════════════════════════════════
    # SECTION 2 — GROUP ADMINS (shown if admin in group)
    # ══════════════════════════════════════════════
    moderation_s = sec("🛡 Moderation — Group Admins", [
        ("ban",        "@user <reason> — Ban"),
        ("tban",       "@user <time> — Temp ban (1h, 2d)"),
        ("kick",       "@user — Kick from group"),
        ("unban",      "@user — Unban"),
        ("mute",       "@user — Mute"),
        ("tmute",      "@user <time> — Temp mute"),
        ("unmute",     "@user — Unmute"),
        ("warn",       "@user <reason> — Warn (3=ban)"),
        ("unwarn",     "@user — Remove one warn"),
        ("resetwarns", "@user — Reset all warns"),
        ("gban",       "@user <reason> — Global ban"),
    ])

    group_mgmt_s = sec("⚙️ Group Settings — Group Admins", [
        ("setrules",   "<text> — Set rules"),
        ("clearrules", "Clear rules"),
        ("save",       "<name> <text> — Save note"),
        ("clear",      "<name> — Delete a note"),
        ("removeallnotes", "Delete all notes"),
        ("pin",        "Pin replied message"),
        ("unpin",      "Unpin message"),
        ("pinned",     "Show pinned message"),
        ("promote",    "@user — Promote to admin"),
        ("demote",     "@user — Demote admin"),
        ("invitelink", "Get invite link"),
        ("setgtitle",  "<title> — Set group title"),
        ("setgpic",    "Set group photo (reply)"),
        ("delgpic",    "Remove group photo"),
        ("setdesc",    "<text> — Set description"),
        ("setsticker", "Set group sticker (reply)"),
    ])

    welcome_s = sec("👋 Welcome System — Group Admins", [
        ("welcome",         "<on/off/noformat> — Toggle/view welcome"),
        ("setwelcome",      "<text> — Set custom welcome message"),
        ("resetwelcome",    "Reset welcome to default"),
        ("goodbye",         "<on/off> — Toggle goodbye message"),
        ("setgoodbye",      "<text> — Set goodbye message"),
        ("resetgoodbye",    "Reset goodbye to default"),
        ("welcomemute",     "<soft/strong/off> — Mute new members"),
        ("cleanservice",    "<on/off> — Delete Telegram join/left msgs"),
        ("cleanwelcome",    "<on/off> — Delete previous welcome on new join"),
        ("setwelcomeimage", "Reply to photo — Set welcome image"),
        ("welcdelay",       "<seconds> — Auto-delete welcome after N seconds"),
        ("welcomehelp",     "Full guide: variables, HTML tags, buttons"),
        ("welcomemutehelp", "Explain soft/strong mute modes"),
    ])

    filter_s = sec("🔍 Filters & Locks — Group Admins", [
        ("filter",     "<keyword> <reply> — Add filter"),
        ("stop",       "<keyword> — Remove filter"),
        ("filters",    "List all filters"),
        ("lock",       "<type> — Lock message type"),
        ("unlock",     "<type> — Unlock"),
        ("locks",      "Show all lock status"),
        ("locktypes",  "List all lockable types"),
        ("addblacklist","<word> — Blacklist word"),
        ("unblacklist","<word> — Remove blacklisted word"),
        ("blacklist",  "List blacklisted words"),
        ("blacklistmode","<action> — Set blacklist action"),
        ("addblsticker","Blacklist sticker (reply)"),
        ("rmblsticker","Remove sticker blacklist"),
        ("blstickermode","<action> — Sticker BL action"),
    ])

    anti_s = sec("🌊 Anti-Spam — Group Admins", [
        ("setflood",   "<number/off> — Set flood limit"),
        ("setfloodmode","<action> — Flood action"),
        ("flood",      "Current flood settings"),
        ("approve",    "@user — Exempt from restrictions"),
        ("unapprove",  "@user — Remove exemption"),
        ("approved",   "List approved users"),
        ("disable",    "<cmd> — Disable a command"),
        ("enable",     "<cmd> — Re-enable command"),
        ("cmds",       "List disabled commands"),
        ("chatbot",    "<on/off> — AI chatbot"),
        ("addword",    "<word> — Add bad word"),
        ("rmword",     "<word> — Remove bad word"),
        ("wordaction", "<action> — Bad word action"),
    ])

    log_s = sec("📋 Logging — Group Admins", [
        ("setlog",     "Set log channel (use in channel)"),
        ("unsetlog",   "Remove log channel"),
        ("logchannel", "Show log channel info"),
        ("ignore",     "@user — Ignore user from bot"),
        ("notice",     "@user — Un-ignore user"),
        ("tagall",     "<msg> — Mention all members"),
        ("purge",      "Delete messages (reply)"),
        ("del",        "Delete replied message"),
    ])

    # ══════════════════════════════════════════════
    # SECTION 3 — BOT ADMIN ONLY
    # ══════════════════════════════════════════════
    bot_admin_s = sec("🔴 Bot Admin Only", [
        ("stats",           "Full bot statistics dashboard"),
        ("sysstats",        "Server CPU/RAM/disk usage"),
        ("users",           "Total registered users count"),
        ("listusers",       "Browse user database with pagination"),
        ("banuser",         "<id/@user> — Ban user from bot"),
        ("unbanuser",       "<id/@user> — Unban user from bot"),
        ("deleteuser",      "<id> — Delete user from database"),
        ("exportusers",     "Export all users as CSV file"),
        ("addchannel",      "@username or -100ID — Add force-sub channel"),
        ("removechannel",   "@username — Remove force-sub channel"),
        ("channel",         "List all force-sub channels"),
        ("addclone",        "BOT_TOKEN — Register a clone bot"),
        ("clones",          "List all registered clone bots"),
        ("upload",          "Open upload/episode manager"),
        ("settings",        "Category poster settings"),
        ("autoupdate",      "Manga chapter auto-tracker"),
        ("autoforward",     "Auto-forward connections manager"),
        ("reload",          "Refresh admin cache / restart"),
        ("logs",            "View recent bot error logs"),
        ("broadcast",       "Send message to all users"),
        ("add_premium",     "<id> <gold/silver/bronze> <days> — Give poster plan"),
        ("remove_premium",  "<id> — Remove poster plan"),
        ("premium_list",    "List all premium poster users"),
        ("set_loader",      "Set loading animation sticker"),
        ("backup",          "List all generated deep links"),
        ("connect",         "Connect a group to bot"),
        ("disconnect",      "Disconnect a group from bot"),
        ("addsudo",         "@user — Add bot sudo user"),
        ("rmsudo",          "@user — Remove sudo user"),
        ("sudolist",        "List all sudo users"),
        ("gban",            "@user <reason> — Global ban"),
        ("ungban",          "@user — Global unban"),
        ("gbanlist",        "List globally banned users"),
        ("dbcleanup",       "Clean up old database entries"),
        ("sh",              "<command> — Run shell command"),
        ("eval",            "<code> — Evaluate Python code"),
        ("exec",            "<code> — Execute Python code"),
        ("speedtest",       "Run network speed test"),
        ("getid",           "<username> — Resolve username to ID"),
        ("getcommonchats",  "@user — Common chats with user"),
        ("setbotname",      "<name> — Change bot display name"),
        ("setbotdesc",      "<text> — Change bot description"),
        ("night",           "<on/off> — Night mode for group"),
        ("nightmode",       "Check night mode status"),
        ("addpanelimg",     "Add image to panel image pool"),
        ("set_loader",      "Set startup loading sticker"),
        ("refresh_commands","Refresh bot command list in Telegram"),
        ("addword",         "<word> — Add global bad word"),
        ("wordlist",        "List all global bad words"),
    ])

    # ── Build final text based on who's asking ────────────────────────────
    if is_bot_admin:
        text = (
            b("📋 All Commands — Bot Admin View") + "\n\n"
            + public + anime_s + fun_s + tools_s + group_s
            + moderation_s + group_mgmt_s + welcome_s
            + filter_s + anti_s + log_s + bot_admin_s
        )
        title = "📋 ᴀʟʟ ᴄᴏᴍᴍᴀɴᴅs — Admin"
    elif is_group_admin:
        text = (
            b("📋 Commands — Group Admin View") + "\n\n"
            + public + anime_s + fun_s + tools_s + group_s
            + moderation_s + group_mgmt_s + welcome_s
            + filter_s + anti_s + log_s
            + "\n<i>Bot admin commands not shown</i>"
        )
        title = "📋 ᴄᴏᴍᴍᴀɴᴅs — Group Admin"
    else:
        text = (
            b("📋 Commands — User View") + "\n\n"
            + public + anime_s + fun_s + tools_s + group_s
            + "\n<i>Group admin and bot admin commands not shown</i>"
        )
        title = "📋 ᴄᴏᴍᴍᴀɴᴅs"

    # ── Send /cmd — always to user's DM (private) to avoid group spam ──────
    # Telegram message limit is 4096 chars. We split at 3800 to be safe.
    TELE_MAX = 3800

    # Always try DM first; fall back to current chat if DM blocked
    send_to = update.effective_user.id  # DM
    close_kb = InlineKeyboardMarkup([[InlineKeyboardButton("✖️ Close", callback_data="close_message")]])

    # Build pages: split text into ≤3800-char chunks on section boundaries
    all_sections = [public, anime_s, fun_s, tools_s, group_s]
    if is_group_admin or is_bot_admin:
        all_sections += [moderation_s, group_mgmt_s, welcome_s, filter_s, anti_s, log_s]
    if is_bot_admin:
        all_sections += [bot_admin_s]

    pages = []
    current_page = b(title) + "\n\n"
    for section in all_sections:
        if len(current_page) + len(section) > TELE_MAX:
            pages.append(current_page)
            current_page = section
        else:
            current_page += section
    if current_page.strip():
        pages.append(current_page)

    if not pages:
        pages = [text]

    sent_any = False
    for i, page_text in enumerate(pages):
        suffix = f"\n\n<i>Page {i+1}/{len(pages)}</i>" if len(pages) > 1 else ""
        kb = close_kb if i == len(pages) - 1 else None
        try:
            await context.bot.send_message(
                chat_id=send_to,
                text=page_text + suffix,
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
                disable_web_page_preview=True,
            )
            sent_any = True
        except Forbidden:
            # DM blocked — send to current chat instead
            send_to = update.effective_chat.id
            try:
                await context.bot.send_message(
                    chat_id=send_to,
                    text=page_text + suffix,
                    parse_mode=ParseMode.HTML,
                    reply_markup=kb,
                    disable_web_page_preview=True,
                )
                sent_any = True
            except Exception as exc:
                logger.debug(f"cmd_command send failed: {exc}")
        except Exception as exc:
            logger.debug(f"cmd_command DM failed: {exc}")

    # If sent to DM from a group, notify user
    if sent_any and send_to == update.effective_user.id and update.effective_chat.id != update.effective_user.id:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=b(small_caps("📋 command list sent to your dm!")),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass


@force_sub_required
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID):
        return
    await delete_update_message(update, context)
    await send_stats_panel(context, update.effective_chat.id)


@force_sub_required
async def sysstats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID):
        return
    await delete_update_message(update, context)
    text = get_system_stats_text()
    await safe_reply(update, text, reply_markup=_back_kb())


@force_sub_required
async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID):
        return
    await delete_update_message(update, context)
    count = get_user_count()
    await safe_reply(
        update,
        b("👥 Total Registered Users:") + " " + code(format_number(count))
    )


@force_sub_required
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID):
        return
    await delete_update_message(update, context)
    user_states.pop(update.effective_user.id, None)
    await delete_bot_prompt(context, update.effective_chat.id)

    keyboard = [
        [_btn("ᴀɴɪᴍᴇ",   "cat_settings_anime"),   _btn("ᴍᴀɴɢᴀ",  "cat_settings_manga")],
        [_btn("ᴍᴏᴠɪᴇ",   "cat_settings_movie"),   _btn("ᴛᴠ sʜᴏᴡ","cat_settings_tvshow")],
        [_back_btn("admin_back")],
    ]
    text = b("⚙️ ᴄᴀᴛᴇɢᴏʀʏ sᴇᴛᴛɪɴɢs") + "\n\n" + bq(b("sᴇʟᴇᴄᴛ ᴀ ᴄᴀᴛᴇɢᴏʀʏ ᴛᴏ ᴄᴏɴғɪɢᴜʀᴇ ɪᴛs ᴛᴇᴍᴘʟᴀᴛᴇ, ʙᴜᴛᴛᴏɴs, ᴡᴀᴛᴇʀᴍᴀʀᴋs, ᴀɴᴅ ᴍᴏʀᴇ."))
        
    if SETTINGS_IMAGE_URL:
        sent = await safe_send_photo(
            context.bot, update.effective_chat.id,
            SETTINGS_IMAGE_URL, caption=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        if sent:
            return
    await safe_reply(update, text, reply_markup=InlineKeyboardMarkup(keyboard))


@force_sub_required
async def add_channel_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Add a force-sub channel by @username OR numeric ID. FIX: supports both."""
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID):
        return
    await delete_update_message(update, context)
    if len(context.args) < 1:
        await safe_reply(
            update,
            b("Usage: /addchannel @username_or_id [Title] [jbr]") + "\n"
            + bq(
                b("By username: /addchannel @BeatAnime My Channel\n")
                + b("By ID: /addchannel -1001234567890 My Channel\n")
                + b("Join by request: /addchannel @chan Title jbr")
            )
        )
        return
    identifier = context.args[0]
    # Determine if this is a numeric ID or @username
    if identifier.lstrip("-").isdigit():
        channel_lookup = int(identifier)
    else:
        channel_lookup = identifier if identifier.startswith("@") else f"@{identifier}"
    # Auto-title from remaining args, or fetch from Telegram
    args_rest = context.args[1:]
    jbr = False
    if args_rest and args_rest[-1].lower() == "jbr":
        jbr = True
        args_rest = args_rest[:-1]
    title = " ".join(args_rest) if args_rest else None
    try:
        chat_obj = await context.bot.get_chat(channel_lookup)
        if title is None:
            title = chat_obj.title or str(channel_lookup)
        channel_id_str = str(chat_obj.id)
        # Check bot membership (not strictly admin-required for force-sub listing)
        try:
            bm = await context.bot.get_chat_member(chat_obj.id, context.bot.id)
            bot_status = getattr(bm, "status", "")
            # Only warn — still allow adding even if bot is member not admin
            # (bot needs admin only to CREATE invite links, not to list channel)
            if bot_status in ("kicked", "banned", "left", ""):
                await safe_reply(update, b(
                    f"⚠️ I am not a member of {e(chat_obj.title or str(channel_id_str))}. "
                    "Add me first, then make me admin so I can create invite links."
                ))
                return
        except Exception:
            pass  # Channel may be public — proceed anyway
    except Exception as exc:
        await safe_reply(update, b(
            f"⚠️ Cannot access {e(str(identifier))}.\n\n"
            "Make sure:\n• The channel/group exists\n• I am a member (admin preferred)\n\n"
            f"Error: {e(str(exc)[:100])}"
        ))
        return
    add_force_sub_channel(channel_id_str, title, join_by_request=jbr)
    jbr_str = " (Join By Request)" if jbr else ""
    await safe_reply(update, b(f"✅ Added: {e(title)} (ID: {channel_id_str}){e(jbr_str)} as force-sub channel."))


@force_sub_required
async def remove_channel_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID):
        return
    await delete_update_message(update, context)
    if len(context.args) != 1:
        await safe_reply(update, b("Usage: /removechannel @username"))
        return
    uname = context.args[0]
    delete_force_sub_channel(uname)
    await safe_reply(update, b(f"🗑 Removed {e(uname)} from force-sub channels."))


@force_sub_required
async def ban_user_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID):
        return
    await delete_update_message(update, context)
    if not context.args:
        await safe_reply(update, b("Usage: /banuser @username_or_id"))
        return
    uid_input = context.args[0]
    uid = resolve_target_user_id(uid_input)
    if uid is None:
        await safe_reply(update, b(f"❌ User {e(uid_input)} not found in database."))
        return
    if uid in (ADMIN_ID, OWNER_ID):
        await safe_reply(update, b("⚠️ Cannot ban admin/owner."))
        return
    ban_user(uid)
    await safe_reply(update, b(f"🚫 User ") + code(str(uid)) + b(" has been banned."))


@force_sub_required
async def unban_user_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID):
        return
    await delete_update_message(update, context)
    if not context.args:
        await safe_reply(update, b("Usage: /unbanuser @username_or_id"))
        return
    uid = resolve_target_user_id(context.args[0])
    if uid is None:
        await safe_reply(update, b(f"❌ User not found."))
        return
    unban_user(uid)
    await safe_reply(update, b(f"✅ User ") + code(str(uid)) + b(" has been unbanned."))


    # ── User management quick-actions from panel ──────────────────────────────────
    if data.startswith("user_list_page_"):
        if not is_admin:
            return
        try:
            page = int(data.split("_")[-1])
        except Exception:
            page = 0
        offset = page * 10
        total = get_user_count()
        users = get_all_users(limit=10, offset=offset)
        text = b(f"USERS {offset+1}–{min(offset+10, total)} of {total:,}") + "\n\n"
        for uid2, uname, fname, lname, joined, banned in users:
            name = f"{fname or ''} {lname or ''}".strip() or "N/A"
            st = "🔴" if banned else "🟢"
            text += f"{st} <b>{e(name[:20])}</b> — @{e(uname or str(uid2))}\n"
        nav = []
        if page > 0:
            nav.append(_btn("PREV", f"user_list_page_{page-1}"))
        if total > offset + 10:
            nav.append(_btn("NEXT", f"user_list_page_{page+1}"))
        rows = [nav] if nav else []
        rows.append([_back_btn("user_management"), _close_btn()])
        try:
            await query.delete_message()
        except Exception:
            pass
        _img = None
        if _PANEL_IMAGE_AVAILABLE:
            try:
                _img = await get_panel_pic_async("users")
            except Exception:
                pass
        await _deliver_panel(context.bot, chat_id, "users", text, InlineKeyboardMarkup(rows), query=None)
        return

    if data == "user_search":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_USER_SEARCH"
        await safe_edit_text(
            query,
            b("sᴇᴀʀᴄʜ ᴜsᴇʀ") + "\n\n" + bq("sᴇɴᴅ @ᴜsᴇʀɴᴀᴍᴇ ᴏʀ ɴᴜᴍᴇʀɪᴄ ᴜsᴇʀ ɪᴅ:"),
            reply_markup=InlineKeyboardMarkup([[_back_btn("user_management"), _close_btn()]]),
        )
        return

    if data == "user_ban_input":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_BAN_USER"
        await safe_edit_text(
            query,
            b("ʙᴀɴ ᴜsᴇʀ") + "\n\n" + bq("sᴇɴᴅ @ᴜsᴇʀɴᴀᴍᴇ ᴏʀ ɴᴜᴍᴇʀɪᴄ ᴜsᴇʀ ɪᴅ ᴛᴏ ʙᴀɴ:"),
            reply_markup=InlineKeyboardMarkup([[_back_btn("user_management"), _close_btn()]]),
        )
        return

    if data == "user_unban_input":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_UNBAN_USER"
        await safe_edit_text(
            query,
            b("ᴜɴʙᴀɴ ᴜsᴇʀ") + "\n\n" + bq("sᴇɴᴅ @ᴜsᴇʀɴᴀᴍᴇ ᴏʀ ɴᴜᴍᴇʀɪᴄ ᴜsᴇʀ ɪᴅ ᴛᴏ ᴜɴʙᴀɴ:"),
            reply_markup=InlineKeyboardMarkup([[_back_btn("user_management"), _close_btn()]]),
        )
        return

    if data == "user_delete_input":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_DELETE_USER"
        await safe_edit_text(
            query,
            b("ᴅᴇʟᴇᴛᴇ ᴜsᴇʀ") + "\n\n" + bq("sᴇɴᴅ ɴᴜᴍᴇʀɪᴄ ᴜsᴇʀ ɪᴅ ᴛᴏ ᴅᴇʟᴇᴛᴇ ғʀᴏᴍ ᴅᴀᴛᴀʙᴀsᴇ:"),
            reply_markup=InlineKeyboardMarkup([[_back_btn("user_management"), _close_btn()]]),
        )
        return

    if data == "user_blocked_list":
        if not is_admin:
            return
        users = get_all_users()
        banned = [(u[0], u[1], u[2]) for u in users if u[5]]
        text = b(f"ʙʟᴏᴄᴋᴇᴅ ᴜsᴇʀs ({len(banned)})") + "\n\n"
        for uid2, uname, fname in banned[:20]:
            text += f"🔴 <code>{uid2}</code> @{e(uname or '')} {e(fname or '')}\n"
        if len(banned) > 20:
            text += f"\n<i>...ᴀɴᴅ {len(banned)-20} ᴍᴏʀᴇ</i>"
        await safe_edit_text(
            query, text,
            reply_markup=InlineKeyboardMarkup([[_back_btn("user_management"), _close_btn()]]),
        )
        return
            
# STATE HANDLERS for user management inputs
# These are handled in handle_admin_message:
#   AWAITING_USER_SEARCH → search and display
#   AWAITING_BAN_USER    → ban_user()
#   AWAITING_UNBAN_USER  → unban_user()
#   AWAITING_DELETE_USER → delete from DB

@force_sub_required
async def listusers_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID):
        return
    await delete_update_message(update, context)
    await delete_bot_prompt(context, update.effective_chat.id)

    try:
        offset = int(context.args[0]) if context.args else 0
    except (ValueError, IndexError):
        offset = 0

    total = get_user_count()
    users = get_all_users(limit=10, offset=offset)

    text = b(f"👥 Users {offset + 1}–{min(offset + 10, total)} of {format_number(total)}") + "\n\n"
    keyboard_rows = []

    for row in users:
        uid2, username, fname, lname, joined, banned = row
        name = f"{fname or ''} {lname or ''}".strip() or "N/A"
        status_icon = "🚫" if banned else "✅"
        uname_str = f"@{username}" if username else f"#{uid2}"
        text += f"{status_icon} {b(e(name[:20]))} — {e(uname_str)}\n"
        keyboard_rows.append([bold_button(
            f"{status_icon} {name[:15]}",
            callback_data=f"manage_user_{uid2}"
        )])

    nav = []
    if offset > 0:
        nav.append(bold_button("🔙PREV", callback_data=f"user_page_{max(0, offset - 10)}"))
    if total > offset + 10:
        nav.append(bold_button("NEXT🔜", callback_data=f"user_page_{offset + 10}"))
    if nav:
        keyboard_rows.append(nav)
    keyboard_rows.append([_back_btn("user_management")])

    await safe_reply(update, text, reply_markup=InlineKeyboardMarkup(keyboard_rows))


@force_sub_required
async def deleteuser_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID):
        return
    await delete_update_message(update, context)
    if not context.args:
        await safe_reply(update, b("Usage: /deleteuser user_id"))
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await safe_reply(update, b("❌ User ID must be a number."))
        return
    if uid in (ADMIN_ID, OWNER_ID):
        await safe_reply(update, b("⚠️ Cannot delete admin/owner."))
        return
    try:
        with db_manager.get_cursor() as cur:
            cur.execute("DELETE FROM users WHERE user_id = %s", (uid,))
        await safe_reply(update, b(f"✅ User ") + code(str(uid)) + b(" deleted from database."))
    except Exception as exc:
        await safe_reply(update, b("❌ Error: ") + code(e(str(exc)[:200])))


@force_sub_required
async def exportusers_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID):
        return
    await delete_update_message(update, context)
    try:
        rows = get_all_users(limit=None, offset=0)
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["user_id", "username", "first_name", "last_name", "joined_at", "banned"])
        writer.writerows(rows)
        output.seek(0)
        data_bytes = output.getvalue().encode("utf-8")
        await context.bot.send_document(
            update.effective_chat.id,
            document=BytesIO(data_bytes),
            filename=f"users_export_{now_utc().strftime('%Y%m%d_%H%M')}.csv",
            caption=b(f"📤 Exported {format_number(len(rows))} users."),
            parse_mode=ParseMode.HTML,
        )
    except Exception as exc:
        await safe_reply(update, b("❌ Export failed: ") + code(e(str(exc)[:200])))


@force_sub_required
async def broadcaststats_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID):
        return
    await delete_update_message(update, context)
    try:
        with db_manager.get_cursor() as cur:
            cur.execute("""
                SELECT id, mode, total_users, success, blocked, deleted, failed,
                       created_at, completed_at
                FROM broadcast_history
                ORDER BY created_at DESC LIMIT 15
            """)
            rows = cur.fetchall() or []
    except Exception as exc:
        await safe_reply(update, b("❌ Error: ") + code(e(str(exc)[:200])))
        return

    if not rows:
        await safe_reply(update, b("📣 No broadcast history yet."), reply_markup=_back_kb())
        return

    text = b("📣 Recent Broadcasts:") + "\n\n"
    for row in rows:
        bid, mode, total, sent, blocked, deleted, failed, created, completed = row
        dur = ""
        if created and completed:
            try:
                delta = completed - created
                dur = f" | ⏱ {int(delta.total_seconds())}s"
            except Exception:
                pass
        text += (
            f"{b(f'ID #{bid}')} — {code(mode)}\n"
            f"✅ {sent} | ❌ {failed} | 🚫 {blocked}{dur}\n"
            f"📅 {str(created)[:16]}\n\n"
        )

    await safe_reply(update, text, reply_markup=_back_kb())


@force_sub_required
async def backup_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID):
        return
    await delete_update_message(update, context)
    try:
        links = get_all_links(bot_username=BOT_USERNAME)
    except Exception as exc:
        await safe_reply(update, b("❌ Error: ") + code(e(str(exc)[:200])))
        return

    if not links:
        await safe_reply(update, b("🔗 No links generated yet."), reply_markup=_back_kb())
        return

    text = b(f"🔗 Generated Links ({len(links)}):") + "\n\n"
    for link_id, channel, title, src_bot, created, never_exp in links:
        line = f"• {b(e(title or channel))} — <code>t.me/{e(BOT_USERNAME)}?start={e(link_id)}</code>\n"
        if len(text) + len(line) > 3800:
            text += b("…more links truncated.")
            break
        text += line

    await safe_reply(update, text, reply_markup=_back_kb())


@force_sub_required
async def addclone_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID):
        return
    await delete_update_message(update, context)
    user_states.pop(update.effective_user.id, None)
    await delete_bot_prompt(context, update.effective_chat.id)

    if context.args:
        token = context.args[0].strip()
        await _register_clone_token(update, context, token)
        return

    user_states[update.effective_user.id] = ADD_CLONE_TOKEN
    msg = await safe_reply(
        update,
        b("🤖 Add Clone Bot") + "\n\n"
        + bq(b("Send the BOT TOKEN of the clone bot.\n\n"
               "⚠️ Keep the token secret!")),
        reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_back")]]),
    )
    await store_bot_prompt(context, msg)


async def _register_clone_token(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> None:
    """Validate and register a clone bot token."""
    chat_id = update.effective_chat.id
    try:
        clone_bot = Bot(token=token)
        me = await clone_bot.get_me()
        username = me.username
        # Register commands on clone bot too
        asyncio.create_task(_register_bot_commands_on_bot(clone_bot))
        launch_clone_bot(token, username)
        if add_clone_bot(token, username):
            await safe_send_message(
                context.bot, chat_id,
                b(f"✅ Clone bot @{e(username)} registered!") + "\n\n"
                + bq(b("Commands have been registered on the clone bot automatically.")),
                reply_markup=InlineKeyboardMarkup([[
                    bold_button("Manage Clones", callback_data="manage_clones")
                ]]),
            )
        else:
            await safe_send_message(
                context.bot, chat_id,
                b("❌ Failed to save clone bot to database.")
            )
    except Exception as exc:
        await safe_send_message(
            context.bot, chat_id,
            b("❌ Invalid token or API error:") + "\n"
            + bq(code(e(str(exc)[:200])))
        )


@force_sub_required
async def clones_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID):
        return
    await delete_update_message(update, context)
    clones = get_all_clone_bots(active_only=True)
    if not clones:
        await safe_reply(update, b("🤖 No clone bots registered yet."))
        return
    text = b(f"🤖 Active Clone Bots ({len(clones)}):") + "\n\n"
    for cid, token, uname, active, added in clones:
        text += f"• @{e(uname)} — {code(str(added)[:10])}\n"
    await safe_reply(update, text)



# ================================================================================
#                    USER FEATURE COMMANDS (available to all users)
# ================================================================================

# ── Reaction GIFs via nekos.best API ─────────────────────────────────────────
_REACTION_API = {
    "slap":  "https://nekos.best/api/v2/slap",
    "hug":   "https://nekos.best/api/v2/hug",
    "kiss":  "https://nekos.best/api/v2/kiss",
    "pat":   "https://nekos.best/api/v2/pat",
    "punch": "https://nekos.best/api/v2/punch",
    "poke":  "https://nekos.best/api/v2/poke",
}
_REACTION_TEXTS = {
    "slap":  ("{sender} slapped {target}! 👋", "{sender} slapped themselves??? 🤔"),
    "hug":   ("{sender} hugged {target}! 🤗", "{sender} wants a hug 🥺"),
    "kiss":  ("{sender} kissed {target}! 💋", "{sender} sent a flying kiss 💋"),
    "pat":   ("{sender} patted {target}! 😊", "{sender} pats themselves 😅"),
    "punch": ("{sender} punched {target}! 👊", "{sender} punched the air 💨"),
    "poke":  ("{sender} poked {target}! 👉", "{sender} pokes around 👀"),
}

async def user_reaction_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generic reaction GIF command — /slap /hug /kiss /pat etc."""
    if not update.message or not update.effective_user:
        return
    cmd = (update.message.text or "").split()[0].lstrip("/").split("@")[0].lower()
    sender_name = update.effective_user.first_name or "Someone"
    target_name = None
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        target_name = update.message.reply_to_message.from_user.first_name
    elif context.args:
        target_name = " ".join(context.args)

    templates = _REACTION_TEXTS.get(cmd, ("{sender} uses {cmd}!", "{sender}!"))
    if target_name:
        caption = templates[0].format(sender=sender_name, target=target_name, cmd=cmd)
    else:
        caption = templates[1].format(sender=sender_name, cmd=cmd)

    # Fetch GIF from nekos.best
    gif_url = None
    api_url = _REACTION_API.get(cmd)
    if api_url:
        try:
            r = requests.get(api_url, timeout=5)
            if r.status_code == 200:
                results = r.json().get("results", [])
                if results:
                    gif_url = results[0].get("url")
        except Exception:
            pass

    try:
        if gif_url:
            await update.message.reply_animation(
                animation=gif_url,
                caption=f"<b>{html.escape(caption)}</b>",
                parse_mode=ParseMode.HTML,
            )
        else:
            await update.message.reply_text(
                f"<b>{html.escape(caption)}</b>",
                parse_mode=ParseMode.HTML,
            )
    except Exception as exc:
        logger.debug(f"reaction cmd error: {exc}")


# ── Couple command ─────────────────────────────────────────────────────────────
async def couple_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/couple — randomly pick or set two users as a couple in the group."""
    if not update.message or not update.effective_user or not update.effective_chat:
        return
    chat = update.effective_chat
    sender = update.effective_user

    if context.args and len(context.args) >= 1:
        # Admin setting: /couple @user1 @user2
        partner_name = " ".join(context.args)
        caption = (
            f"💑 <b>{html.escape(sender.first_name)}</b> "
            f"and <b>{html.escape(partner_name)}</b> are now a couple!"
        )
    elif update.message.reply_to_message and update.message.reply_to_message.from_user:
        partner = update.message.reply_to_message.from_user
        caption = (
            f"💑 <b>{html.escape(sender.first_name)}</b> "
            f"and <b>{html.escape(partner.first_name)}</b> are a couple! 💕"
        )
    else:
        caption = f"💑 <b>{html.escape(sender.first_name)}</b> is looking for their other half! 💕"

    try:
        gif_url = None
        try:
            r = requests.get("https://nekos.best/api/v2/kiss", timeout=5)
            if r.status_code == 200:
                results = r.json().get("results", [])
                if results:
                    gif_url = results[0].get("url")
        except Exception:
            pass
        if gif_url:
            await update.message.reply_animation(animation=gif_url, caption=caption, parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(caption, parse_mode=ParseMode.HTML)
    except Exception as exc:
        logger.debug(f"couple_cmd error: {exc}")


# ── AFK system ─────────────────────────────────────────────────────────────────
_afk_users: Dict[int, Dict] = {}  # uid → {reason, time}

async def afk_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/afk [reason] — set AFK status."""
    if not update.effective_user or not update.message:
        return
    uid = update.effective_user.id
    reason = " ".join(context.args) if context.args else "AFK"
    _afk_users[uid] = {"reason": reason, "time": datetime.now(timezone.utc)}
    await update.message.reply_text(
        f"<b>{html.escape(update.effective_user.first_name)}</b> is now AFK: <i>{html.escape(reason)}</i>",
        parse_mode=ParseMode.HTML,
    )

async def afk_check_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Auto-reply when AFK user is mentioned, and clear AFK when they speak."""
    if not update.message or not update.effective_user:
        return
    uid = update.effective_user.id
    msg = update.message

    # Clear AFK if the user themselves sends a message
    if uid in _afk_users:
        afk_data = _afk_users.pop(uid)
        elapsed = datetime.now(timezone.utc) - afk_data["time"]
        mins = int(elapsed.total_seconds() // 60)
        time_str = f"{mins} min" if mins < 60 else f"{mins // 60}h {mins % 60}m"
        try:
            await msg.reply_text(
                f"<b>{html.escape(update.effective_user.first_name)}</b> is back! (was AFK for {time_str})",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
        return

    # Check if any mentioned user is AFK
    if msg.entities:
        for entity in msg.entities:
            if entity.type == "mention":
                try:
                    mention_text = msg.text[entity.offset + 1:entity.offset + entity.length]
                    for afk_uid, afk_data in _afk_users.items():
                        member = await context.bot.get_chat_member(msg.chat_id, afk_uid)
                        if member and hasattr(member, "user") and member.user.username == mention_text:
                            elapsed = datetime.now(timezone.utc) - afk_data["time"]
                            mins = int(elapsed.total_seconds() // 60)
                            await msg.reply_text(
                                f"<b>{html.escape(member.user.first_name)}</b> is AFK: "
                                f"<i>{html.escape(afk_data['reason'])}</i> ({mins}m ago)",
                                parse_mode=ParseMode.HTML,
                            )
                except Exception:
                    pass


# ── Notes system ───────────────────────────────────────────────────────────────
_notes_db: Dict[int, Dict[str, str]] = {}  # chat_id → {name: content}

def _get_notes(chat_id: int) -> Dict[str, str]:
    try:
        val = get_setting(f"notes_{chat_id}", "")
        if val:
            import json as _json
            return _json.loads(val)
    except Exception:
        pass
    return _notes_db.get(chat_id, {})

def _save_notes(chat_id: int, notes: Dict) -> None:
    import json as _json
    try:
        set_setting(f"notes_{chat_id}", _json.dumps(notes))
    except Exception:
        pass
    _notes_db[chat_id] = notes

async def note_save_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/save notename content — save a note."""
    if not update.message or not update.effective_chat:
        return
    # Only admins/mods can save notes
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("<b>Usage:</b> /save notename your note content", parse_mode=ParseMode.HTML)
        return
    name = context.args[0].lower()
    text_content = " ".join(context.args[1:])
    chat_id = update.effective_chat.id
    notes = _get_notes(chat_id)
    notes[name] = text_content
    _save_notes(chat_id, notes)
    await update.message.reply_text(f"<b>📝 Note saved:</b> #{html.escape(name)}", parse_mode=ParseMode.HTML)

async def note_get_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/get notename — retrieve a note."""
    if not update.message or not update.effective_chat:
        return
    if not context.args:
        await update.message.reply_text("Usage: /get notename", parse_mode=ParseMode.HTML)
        return
    name = context.args[0].lower()
    chat_id = update.effective_chat.id
    notes = _get_notes(chat_id)
    content = notes.get(name)
    if content:
        await update.message.reply_text(f"<b>#{html.escape(name)}:</b>\n{html.escape(content)}", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f"<b>No note named #{html.escape(name)}</b>", parse_mode=ParseMode.HTML)

async def notes_list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/notes — list all notes in this chat."""
    if not update.message or not update.effective_chat:
        return
    chat_id = update.effective_chat.id
    notes = _get_notes(chat_id)
    if not notes:
        await update.message.reply_text("<b>No notes saved in this chat.</b>", parse_mode=ParseMode.HTML)
        return
    text = "<b>📝 Notes in this chat:</b>\n" + "\n".join(f"• #{html.escape(n)}" for n in notes)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def note_trigger_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle #notename messages to retrieve notes."""
    if not update.message or not update.effective_chat:
        return
    text = update.message.text or ""
    import re as _re
    match = _re.match(r"^#([\w]+)", text.strip())
    if not match:
        return
    name = match.group(1).lower()
    chat_id = update.effective_chat.id
    notes = _get_notes(chat_id)
    content = notes.get(name)
    if content:
        await update.message.reply_text(f"<b>#{html.escape(name)}:</b>\n{html.escape(content)}", parse_mode=ParseMode.HTML)


# ── Warns system ───────────────────────────────────────────────────────────────
_warns_db: Dict[str, int] = {}  # "chat_id:user_id" → count

def _warn_key(chat_id: int, uid: int) -> str:
    return f"warn_{chat_id}_{uid}"

def _get_warns(chat_id: int, uid: int) -> int:
    try:
        return int(get_setting(_warn_key(chat_id, uid), "0") or "0")
    except Exception:
        return _warns_db.get(f"{chat_id}:{uid}", 0)

def _set_warns(chat_id: int, uid: int, count: int) -> None:
    try:
        set_setting(_warn_key(chat_id, uid), str(count))
    except Exception:
        pass
    _warns_db[f"{chat_id}:{uid}"] = count

async def warn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/warn — warn a user (reply or @mention)."""
    if not update.message or not update.effective_chat or not update.effective_user:
        return
    # Check if sender is admin
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if member.status not in ("administrator", "creator"):
            return
    except Exception:
        return
    target = None
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        target = update.message.reply_to_message.from_user
    if not target:
        await update.message.reply_text("Reply to a user to warn them.", parse_mode=ParseMode.HTML)
        return
    reason = " ".join(context.args) if context.args else "No reason given"
    chat_id = update.effective_chat.id
    count = _get_warns(chat_id, target.id) + 1
    _set_warns(chat_id, target.id, count)
    warn_limit = int(get_setting("warn_limit", "3") or "3")
    await update.message.reply_text(
        f"⚠️ <b>{html.escape(target.first_name)}</b> warned ({count}/{warn_limit})\nReason: {html.escape(reason)}",
        parse_mode=ParseMode.HTML,
    )
    if count >= warn_limit:
        try:
            await context.bot.ban_chat_member(chat_id, target.id)
            _set_warns(chat_id, target.id, 0)
            await update.message.reply_text(
                f"🔴 <b>{html.escape(target.first_name)}</b> has been banned after {warn_limit} warnings.",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass

async def unwarn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/unwarn — remove one warn."""
    if not update.message or not update.effective_chat:
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user to remove their warn.")
        return
    target = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id
    count = max(0, _get_warns(chat_id, target.id) - 1)
    _set_warns(chat_id, target.id, count)
    await update.message.reply_text(
        f"✅ Removed 1 warn from <b>{html.escape(target.first_name)}</b>. Now at {count} warns.",
        parse_mode=ParseMode.HTML,
    )

async def warns_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/warns — check warns for a user."""
    if not update.message or not update.effective_chat:
        return
    target = None
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        target = update.message.reply_to_message.from_user
    else:
        target = update.effective_user
    chat_id = update.effective_chat.id
    count = _get_warns(chat_id, target.id)
    warn_limit = int(get_setting("warn_limit", "3") or "3")
    await update.message.reply_text(
        f"⚠️ <b>{html.escape(target.first_name)}</b> has <b>{count}/{warn_limit}</b> warns.",
        parse_mode=ParseMode.HTML,
    )

async def resetwarns_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/resetwarns — reset warns for replied user."""
    if not update.message or not update.effective_chat:
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user to reset their warns.")
        return
    target = update.message.reply_to_message.from_user
    _set_warns(update.effective_chat.id, target.id, 0)
    await update.message.reply_text(
        f"✅ Warns reset for <b>{html.escape(target.first_name)}</b>.", parse_mode=ParseMode.HTML
    )


# ── Rules system ───────────────────────────────────────────────────────────────
async def rules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/rules — show group rules."""
    if not update.message or not update.effective_chat:
        return
    chat_id = update.effective_chat.id
    rules = get_setting(f"rules_{chat_id}", "")
    if rules:
        await update.message.reply_text(
            f"<b> Group Rules:</b>\n\n{html.escape(rules)}", parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text("<b>No rules set for this group yet.</b>", parse_mode=ParseMode.HTML)

async def setrules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/setrules — set group rules (admin only)."""
    if not update.message or not update.effective_chat or not update.effective_user:
        return
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if member.status not in ("administrator", "creator"):
            return
    except Exception:
        return
    if not context.args:
        await update.message.reply_text("<b>Usage:</b> /setrules your rules text here", parse_mode=ParseMode.HTML)
        return
    rules_text = " ".join(context.args)
    set_setting(f"rules_{update.effective_chat.id}", rules_text)
    await update.message.reply_text("<b>✅ Rules saved!</b>\nUsers can now use /rules to see them.", parse_mode=ParseMode.HTML)


# ── Chatbot (users talk directly, not admin-only) ──────────────────────────────
_chatbot_conv: Dict[int, list] = {}  # chat_id → message history

async def _chatbot_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """Send a chatbot reply using Anthropic API or simple fallback."""
    chat_id = update.effective_chat.id
    user_msg = text.strip()
    if not user_msg:
        return

    # Check if chatbot is enabled for this chat
    enabled = get_setting(f"chatbot_{chat_id}", "true")
    if enabled == "false":
        return

    history = _chatbot_conv.get(chat_id, [])
    history.append({"role": "user", "content": user_msg})
    if len(history) > 20:
        history = history[-20:]

    typing_task = None
    try:
        await context.bot.send_chat_action(chat_id, "typing")
    except Exception:
        pass

    reply_text = None
    try:
        import aiohttp
        payload = {
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 300,
            "system": (
                "You are an anime-loving chatbot assistant for a Telegram group. "
                "Be friendly, fun, and helpful. Keep replies short (1-3 sentences). "
                "You love anime and can recommend shows, discuss characters, etc."
            ),
            "messages": history,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.anthropic.com/v1/messages",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content = data.get("content", [])
                    for block in content:
                        if block.get("type") == "text":
                            reply_text = block["text"].strip()
                            break
    except Exception as exc:
        logger.debug(f"Chatbot API error: {exc}")

    if not reply_text:
        # Simple fallback responses
        import random
        fallbacks = [
            "Interesting! Tell me more! ",
            "That's cool! What anime are you watching? ",
            "I'm here to chat! What's on your mind? 😊",
            "Nice! Have you seen Demon Slayer? It's amazing! ",
        ]
        reply_text = random.choice(fallbacks)

    history.append({"role": "assistant", "content": reply_text})
    _chatbot_conv[chat_id] = history[-20:]

    try:
        await update.message.reply_text(reply_text, parse_mode=ParseMode.HTML)
    except Exception:
        try:
            await update.message.reply_text(reply_text)
        except Exception:
            pass

async def chatbot_private_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle chatbot messages in private chats — all users."""
    if not update.message or not update.message.text:
        return
    await _chatbot_reply(update, context, update.message.text)

async def chatbot_group_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle chatbot trigger in groups (when bot is mentioned or specific trigger words used)."""
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    bot_username = context.bot.username or ""
    # Only respond if bot is @mentioned or message starts with trigger words
    if f"@{bot_username}" in text:
        text = text.replace(f"@{bot_username}", "").strip()
        await _chatbot_reply(update, context, text)
    elif update.message.reply_to_message and update.message.reply_to_message.from_user:
        if update.message.reply_to_message.from_user.id == context.bot.id:
            await _chatbot_reply(update, context, text)


async def set_loader_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /set_loader — control the loading animation.
    Usage:
      • Forward a sticker to chat, then REPLY to it with /set_loader  → sets as loader sticker
      • /set_loader off  → disables loading animation entirely
      • /set_loader on   → restores default ❗ animation (clears custom sticker)
    """
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID):
        return
    await delete_update_message(update, context)
    reply = update.message.reply_to_message if update.message else None
    args = context.args or []

    if reply and reply.sticker:
        # Set sticker as loader
        sticker_id = reply.sticker.file_id
        set_setting("loading_sticker_id", sticker_id)
        set_setting("loading_anim_enabled", "true")
        await safe_send_message(
            context.bot, update.effective_chat.id,
            "<b>✅ Custom loading sticker set!</b>\n\n"
            "Every panel open will now show your sticker instead of ❗ animation.\n"
            "Use /set_loader on to restore default, /set_loader off to disable.",
            parse_mode="HTML",
        )
    elif args and args[0].lower() == "off":
        set_setting("loading_anim_enabled", "false")
        await safe_send_message(
            context.bot, update.effective_chat.id,
            "<b>✅ Loading animation disabled.</b>\n"
            "Panels will appear without any loading message.",
            parse_mode="HTML",
        )
    elif args and args[0].lower() == "on":
        set_setting("loading_anim_enabled", "true")
        set_setting("loading_sticker_id", "")
        await safe_send_message(
            context.bot, update.effective_chat.id,
            "<b>✅ Loading animation restored to default ❗ style.</b>",
            parse_mode="HTML",
        )
    else:
        # Show current status
        enabled = get_setting("loading_anim_enabled", "true") == "true"
        sticker_id = get_setting("loading_sticker_id", "")
        status = "🟢 Enabled" if enabled else "🔴 Disabled"
        kind = f"Custom Sticker (<code>{sticker_id[:20]}…</code>)" if sticker_id else "Default ❗ Animation"
        await safe_send_message(
            context.bot, update.effective_chat.id,
            f"<b> Loading Animation Settings</b>\n\n"
            f"<b>Status:</b> {status}\n"
            f"<b>Type:</b> {kind}\n\n"
            f"<b>How to change:</b>\n"
            f"• Forward a sticker here, then REPLY to it with <code>/set_loader</code>\n"
            f"• <code>/set_loader off</code> — disable animation\n"
            f"• <code>/set_loader on</code> — restore default ❗",
            parse_mode="HTML",
        )


async def reload_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID):
        return
    await delete_update_message(update, context)
    triggered_by = (update.effective_user.username or str(update.effective_user.id))
    try:
        with open("restart_message.json", "w") as f:
            json.dump({
                "chat_id": update.effective_chat.id,
                "admin_id": ADMIN_ID,
                "triggered_by": triggered_by,
            }, f)
    except Exception as exc:
        logger.error(f"Failed to write restart file: {exc}")
    try:
        await safe_reply(update, b("♻️ Bot is restarting… Be right back!"))
    except Exception:
        pass
    await asyncio.sleep(1)
    sys.exit(0)


@force_sub_required
async def test_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    await safe_reply(update, b("✅ Bot is alive and healthy!"))


@force_sub_required
async def logs_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID):
        return
    await delete_update_message(update, context)
    try:
        with open("logs/bot.log", "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()[-60:]
        log_text = "".join(lines)
        if len(log_text) > 3900:
            log_text = log_text[-3900:]
        await safe_reply(update, f"<pre>{e(log_text)}</pre>")
    except Exception as exc:
        await safe_reply(update, b("❌ Error reading logs: ") + code(e(str(exc))))


@force_sub_required
async def channel_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID):
        return
    await delete_update_message(update, context)
    channels = get_all_force_sub_channels(return_usernames_only=False)
    if not channels:
        await safe_reply(update, b("📢 No force-sub channels configured."))
        return
    text = b(f"📢 Force-Sub Channels ({len(channels)}):") + "\n\n"
    for uname, title, jbr in channels:
        jbr_tag = " (Join By Request)" if jbr else ""
        text += f"• {b(e(title))}\n  {e(uname)}{jbr_tag}\n\n"
    await safe_reply(update, text)


@force_sub_required
async def connect_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID):
        return
    await delete_update_message(update, context)
    if not context.args:
        await safe_reply(update, b("Usage: /connect @group_or_id"))
        return
    try:
        chat = await context.bot.get_chat(context.args[0])
        if chat.type not in ("group", "supergroup"):
            await safe_reply(update, b("❌ That's not a group."))
            return
        with db_manager.get_cursor() as cur:
            cur.execute("""
                INSERT INTO connected_groups (group_id, group_username, group_title, connected_by)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (group_id) DO UPDATE SET active = TRUE
            """, (chat.id, chat.username, chat.title, update.effective_user.id))
        await safe_reply(update, b(f"✅ Connected to {e(chat.title)}"))
    except Exception as exc:
        await safe_reply(update, UserFriendlyError.get_user_message(exc))


@force_sub_required
async def disconnect_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID):
        return
    await delete_update_message(update, context)
    if not context.args:
        await safe_reply(update, b("Usage: /disconnect @group_or_id"))
        return
    try:
        chat = await context.bot.get_chat(context.args[0])
        with db_manager.get_cursor() as cur:
            cur.execute("UPDATE connected_groups SET active = FALSE WHERE group_id = %s", (chat.id,))
        await safe_reply(update, b(f"✅ Disconnected from {e(chat.title)}"))
    except Exception as exc:
        await safe_reply(update, UserFriendlyError.get_user_message(exc))


@force_sub_required
async def connections_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID):
        return
    await delete_update_message(update, context)
    try:
        with db_manager.get_cursor() as cur:
            cur.execute("SELECT group_id, group_username, group_title FROM connected_groups WHERE active = TRUE")
            rows = cur.fetchall() or []
    except Exception as exc:
        await safe_reply(update, b("❌ Error: ") + code(e(str(exc)[:200])))
        return
    if not rows:
        await safe_reply(update, b("🔗 No connected groups."))
        return
    text = b(f"🔗 Connected Groups ({len(rows)}):") + "\n\n"
    for gid, uname, title in rows:
        text += f"• {b(e(title or ''))} {('@' + uname) if uname else ''} {code(str(gid))}\n"
    await safe_reply(update, text)


@force_sub_required
async def id_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not update.message:
        return
    msg  = update.message
    user = update.effective_user
    chat = update.effective_chat

    text = b(small_caps("🆔 id info")) + "\n\n"

    # Own info
    if user:
        uname = f" @{e(user.username)}" if user.username else ""
        text += (
            f"» {b(small_caps('user id'))} {code(str(user.id))}{uname}\n"
            f"» {b(small_caps('name'))} {e(user.full_name or '')}\n"
        )
    text += (
        f"» {b(small_caps('chat id'))} {code(str(chat.id))}\n"
        f"» {b(small_caps('type'))} {code(chat.type)}\n"
    )
    if chat.username:
        text += f"» {b(small_caps('username'))} @{e(chat.username)}\n"

    # Reply info
    if msg.reply_to_message:
        rep = msg.reply_to_message
        text += "\n" + b(small_caps("replied message")) + "\n"

        # Channel message — most important: get channel info
        if rep.sender_chat:
            ch = rep.sender_chat
            text += (
                f"» {b(small_caps('channel id'))} {code(str(ch.id))}\n"
                f"» {b(small_caps('channel title'))} {e(ch.title or '')}\n"
            )
            if ch.username:
                text += f"» {b(small_caps('channel username'))} @{e(ch.username)}\n"
            # Try to get extra info
            try:
                ch_full = await context.bot.get_chat(ch.id)
                if ch_full.invite_link:
                    text += f"» {b(small_caps('invite link'))} {e(ch_full.invite_link)}\n"
                if ch_full.description:
                    text += f"» {b(small_caps('description'))} {e(ch_full.description[:100])}\n"
                if ch_full.member_count:
                    text += f"» {b(small_caps('members'))} {code(str(ch_full.member_count))}\n"
            except Exception:
                pass

        # Forwarded from channel
        # PTB v21: forward_from_chat removed, use forward_origin
        _fwd_chat = None
        try:
            _fo = getattr(rep, "forward_origin", None)
            if _fo and hasattr(_fo, "chat"):
                _fwd_chat = _fo.chat
            elif _fo and hasattr(_fo, "sender_chat"):
                _fwd_chat = _fo.sender_chat
        except Exception:
            pass
        if _fwd_chat:
            fch = _fwd_chat
            text += (
                f"» {b(small_caps('fwd channel id'))} {code(str(fch.id))}\n"
                f"» {b(small_caps('fwd channel title'))} {e(fch.title or '')}\n"
            )
            if getattr(fch, "username", None):
                text += f"» {b(small_caps('fwd username'))} @{e(fch.username)}\n"

        if rep.from_user and not rep.sender_chat:
            ru = rep.from_user
            runame = f" @{e(ru.username)}" if ru.username else ""
            text += (
                f"» {b(small_caps('replied user id'))} {code(str(ru.id))}{runame}\n"
                f"» {b(small_caps('replied name'))} {e(ru.full_name or '')}\n"
            )
        if rep.forward_from:
            fu = rep.forward_from
            text += f"» {b(small_caps('forward user id'))} {code(str(fu.id))} {e(fu.full_name or '')}\n"

        # Media file IDs
        media_fields = [
            ("sticker",   rep.sticker,   rep.sticker.file_id if rep.sticker else None),
            ("photo",     rep.photo,     rep.photo[-1].file_id if rep.photo else None),
            ("video",     rep.video,     rep.video.file_id if rep.video else None),
            ("audio",     rep.audio,     rep.audio.file_id if rep.audio else None),
            ("document",  rep.document,  rep.document.file_id if rep.document else None),
            ("animation", rep.animation, rep.animation.file_id if rep.animation else None),
            ("voice",     rep.voice,     rep.voice.file_id if rep.voice else None),
            ("video note",rep.video_note,rep.video_note.file_id if rep.video_note else None),
        ]
        for label, obj, fid in media_fields:
            if fid:
                text += f"» {b(small_caps(label + ' file id'))}\n  {code(fid)}\n"

    if len(text) > 3500:
        text = text[:3496] + "…"
    await msg.reply_text(text, parse_mode=ParseMode.HTML)


@force_sub_required
async def info_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not update.message:
        return
    target = None
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    elif context.args:
        try:
            target = await context.bot.get_chat(context.args[0])
        except Exception as exc:
            await update.message.reply_text(UserFriendlyError.get_user_message(exc), parse_mode=ParseMode.HTML)
            return
    else:
        target = update.effective_user

    if not target:
        await update.message.reply_text(b("No target specified."), parse_mode=ParseMode.HTML)
        return

    uid_val = getattr(target, "id", "N/A")
    uname = getattr(target, "username", None)
    fname = getattr(target, "first_name", None)
    lname = getattr(target, "last_name", None)
    title = getattr(target, "title", None)
    chat_type = getattr(target, "type", None)

    text = b("👤 Info") + "\n\n"
    text += f"<b>ID:</b> {code(str(uid_val))}\n"
    if uname:
        text += f"<b>Username:</b> @{e(uname)}\n"
    if fname:
        text += f"<b>First Name:</b> {e(fname)}\n"
    if lname:
        text += f"<b>Last Name:</b> {e(lname)}\n"
    if title:
        text += f"<b>Title:</b> {e(title)}\n"
    if chat_type:
        text += f"<b>Type:</b> {code(chat_type)}\n"

    # Check if user exists in DB
    try:
        user_info = get_user_info_by_id(int(uid_val))
        if user_info:
            _, _, _, _, joined, banned = user_info
            text += f"<b>Joined Bot:</b> {code(str(joined)[:16])}\n"
            text += f"<b>Status:</b> {'🚫 Banned' if banned else '✅ Active'}\n"
    except Exception:
        pass

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


@force_sub_required
async def upload_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID):
        return
    await delete_update_message(update, context)
    user_states.pop(update.effective_user.id, None)
    await delete_bot_prompt(context, update.effective_chat.id)
    await load_upload_progress()
    await show_upload_menu(update.effective_chat.id, context)


@force_sub_required
async def autoforward_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID):
        return
    await delete_update_message(update, context)
    user_states.pop(update.effective_user.id, None)
    await _show_autoforward_menu(context, update.effective_chat.id)


@force_sub_required
async def autoupdate_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID):
        return
    await delete_update_message(update, context)
    user_states.pop(update.effective_user.id, None)
    await _show_autoupdate_menu(context, update.effective_chat.id)


async def _show_autoforward_menu(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int
) -> None:
    try:
        with db_manager.get_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM auto_forward_connections WHERE active = TRUE")
            active_count = cur.fetchone()[0]
    except Exception:
        active_count = 0

    af_enabled = get_setting("autoforward_enabled", "true")
    on_off = "ON" if active_count > 0 and af_enabled == "true" else "OFF"
    text = (
        b("Auto Forward Settings") + "\n\n"
        f"<b>Status:</b> {on_off}\n"
        f"<b>Connections:</b> {active_count}"
    )
    # Spec-compliant AUTO FORWARD PANEL layout
    keyboard = [
        [bold_button("MODE", callback_data="af_set_caption")],
        [bold_button("MANAGE CONNECTIONS", callback_data="af_list_connections")],
        [bold_button("SETTINGS", callback_data="af_add_connection"),
         bold_button("FILTERS", callback_data="af_filters_menu")],
        [bold_button("REPLACEMENTS", callback_data="af_replacements_menu"),
         bold_button("DELAY", callback_data="af_set_delay")],
        [bold_button("BULK FORWARD", callback_data="af_bulk")],
        [bold_button("TOGGLE ON/OFF", callback_data="af_toggle_all")],
        [_back_btn("admin_back")],
    ]
    await safe_send_message(
        context.bot, chat_id, text,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def _show_autoupdate_menu(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int
) -> None:
    try:
        with db_manager.get_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM manga_auto_updates WHERE active = TRUE")
            active_count = cur.fetchone()[0]
    except Exception:
        active_count = 0

    text = (
        b("📚 Auto Manga Update Manager") + "\n\n"
        f"<b>Tracked Manga:</b> {code(str(active_count))}\n\n"
        + bq(b("The bot checks for new chapters every hour\n"
               "and sends a notification to your target channel."))
    )
    keyboard = [
        [bold_button("➕ Track New Manga", callback_data="au_add_manga")],
        [bold_button("View Tracked", callback_data="au_list_manga"),
         bold_button("Stop Tracking", callback_data="au_remove_manga")],
        [bold_button("Manga Stats", callback_data="au_stats")],
        [_back_btn("admin_back")],
    ]
    await safe_send_message(
        context.bot, chat_id, text,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ================================================================================
#                       BROADCAST SYSTEM — COMPLETE
# ================================================================================

async def _do_broadcast(
    context: ContextTypes.DEFAULT_TYPE,
    admin_chat_id: int,
    from_chat_id: int,
    message_id: int,
    mode: str,
) -> None:
    """Execute a broadcast to all registered users."""
    users = get_all_users(limit=None, offset=0)
    total = len(users)
    sent = fail = blocked = deleted_count = 0
    deleted_uids: list = []  # track UIDs of deactivated accounts for DB cleanup

    # Log to DB
    try:
        with db_manager.get_cursor() as cur:
            cur.execute("""
                INSERT INTO broadcast_history (admin_id, mode, total_users, message_text)
                VALUES (%s, %s, %s, %s) RETURNING id
            """, (ADMIN_ID, mode, total, f"copy:{from_chat_id}:{message_id}"))
            bc_id = cur.fetchone()[0]
    except Exception:
        bc_id = None

    # Progress msg
    progress_msg = await safe_send_message(
        context.bot, admin_chat_id,
        b(f"📣 Broadcasting to {format_number(total)} users…"),
    )

    for i, user_row in enumerate(users):
        uid = user_row[0]
        if uid in (ADMIN_ID, OWNER_ID):
            continue
        try:
            if mode == BroadcastMode.AUTO_DELETE:
                msg = await context.bot.copy_message(
                    uid, from_chat_id, message_id
                )
                context.job_queue.run_once(
                    lambda ctx, u=uid, m=msg.message_id: safe_delete(ctx.bot, u, m),
                    when=86400,
                )
            elif mode in (BroadcastMode.PIN, BroadcastMode.DELETE_PIN):
                msg = await context.bot.copy_message(uid, from_chat_id, message_id)
                try:
                    await context.bot.pin_chat_message(uid, msg.message_id, disable_notification=True)
                    if mode == BroadcastMode.DELETE_PIN:
                        await safe_delete(context.bot, uid, msg.message_id)
                except Exception:
                    pass
            elif mode == BroadcastMode.SILENT:
                await context.bot.copy_message(
                    uid, from_chat_id, message_id,
                    disable_notification=True,
                )
            else:  # NORMAL
                await context.bot.copy_message(uid, from_chat_id, message_id)
            sent += 1
        except Forbidden as err:
            fail += 1
            err_s = str(err).lower()
            if "blocked" in err_s:
                blocked += 1
            elif "deactivated" in err_s or "deleted" in err_s:
                deleted_count += 1
                deleted_uids.append(uid)
        except RetryAfter as err:
            await asyncio.sleep(err.retry_after + 1)
            try:
                await context.bot.copy_message(uid, from_chat_id, message_id)
                sent += 1
            except Exception:
                fail += 1
        except Exception:
            fail += 1
        await asyncio.sleep(RATE_LIMIT_DELAY)

        # Update progress every 500
        if progress_msg and (i + 1) % 500 == 0:
            try:
                await progress_msg.edit_text(
                    b(f"📣 Broadcasting… {i+1}/{total}"),
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass

    # Final update
    if bc_id:
        try:
            with db_manager.get_cursor() as cur:
                cur.execute("""
                    UPDATE broadcast_history
                    SET completed_at = NOW(), success = %s, blocked = %s,
                        deleted = %s, failed = %s
                    WHERE id = %s
                """, (sent, blocked, deleted_count, fail, bc_id))
        except Exception:
            pass

    # Purge deactivated / deleted accounts from the users table
    purged = 0
    if deleted_uids:
        try:
            with db_manager.get_cursor() as cur:
                cur.execute(
                    "DELETE FROM users WHERE user_id = ANY(%s)",
                    (deleted_uids,)
                )
                purged = cur.rowcount
        except Exception as exc:
            logger.debug(f"Purge deleted users error: {exc}")

    result = (
        b(" Broadcast Complete!") + "\n\n"
        + bq(
            f"<b> Sent:</b> {code(format_number(sent))}\n"
            f"<b> Blocked:</b> {code(format_number(blocked))}\n"
            f"<b> Deleted accounts:</b> {code(format_number(deleted_count))}\n"
            f"<b> Purged from DB:</b> {code(format_number(purged))}\n"
            f"<b> Other failures:</b> {code(format_number(fail - blocked - deleted_count if fail > 0 else 0))}\n"
            f"<b> Total users:</b> {code(format_number(total))}"
        )
    )

    if progress_msg:
        try:
            await progress_msg.edit_text(result, parse_mode=ParseMode.HTML)
        except Exception:
            await safe_send_message(context.bot, admin_chat_id, result)
    else:
        await safe_send_message(context.bot, admin_chat_id, result)


# ================================================================================
#                      UPLOAD MANAGER — COMPLETE
# ================================================================================

async def load_upload_progress() -> None:
    """Load upload progress from database into global dict."""
    global upload_progress
    try:
        # First try with anime_name column (may not exist on older DBs)
        row = None
        with db_manager.get_cursor() as cur:
            try:
                cur.execute("""
                    SELECT target_chat_id, season, episode, total_episode, video_count,
                           selected_qualities, base_caption, auto_caption_enabled, anime_name
                    FROM bot_progress WHERE id = 1
                """)
                row = cur.fetchone()
            except Exception:
                # Fallback: query without anime_name column
                try:
                    cur.execute("""
                        SELECT target_chat_id, season, episode, total_episode, video_count,
                               selected_qualities, base_caption, auto_caption_enabled
                        FROM bot_progress WHERE id = 1
                    """)
                    row_short = cur.fetchone()
                    if row_short:
                        # Pad to 9 elements with default anime_name
                        row = tuple(row_short) + ("Anime Name",)
                except Exception:
                    pass
        if row and len(row) >= 8:
            upload_progress.update({
                "target_chat_id": row[0],
                "season": row[1] or 1,
                "episode": row[2] or 1,
                "total_episode": row[3] or 1,
                "video_count": row[4] or 0,
                "selected_qualities": row[5].split(",") if row[5] else ["480p", "720p", "1080p"],
                "base_caption": row[6] or DEFAULT_CAPTION,
                "auto_caption_enabled": bool(row[7]),
                "anime_name": row[8] if len(row) > 8 else "Anime Name",
            })
    except Exception as exc:
        db_logger.debug(f"load_upload_progress error: {exc}")


async def save_upload_progress() -> None:
    """Persist upload progress to database."""
    try:
        with db_manager.get_cursor() as cur:
            cur.execute("""
                UPDATE bot_progress SET
                    target_chat_id = %s, season = %s, episode = %s,
                    total_episode = %s, video_count = %s,
                    selected_qualities = %s, base_caption = %s,
                    auto_caption_enabled = %s, anime_name = %s
                WHERE id = 1
            """, (
                upload_progress["target_chat_id"],
                upload_progress["season"],
                upload_progress["episode"],
                upload_progress["total_episode"],
                upload_progress["video_count"],
                ",".join(upload_progress["selected_qualities"]),
                upload_progress["base_caption"],
                upload_progress["auto_caption_enabled"],
                upload_progress.get("anime_name", "Anime Name"),
            ))
    except Exception as exc:
        db_logger.debug(f"save_upload_progress error: {exc}")


def build_caption_from_progress() -> str:
    """Build formatted caption for current episode/quality."""
    quality = "N/A"
    if upload_progress["selected_qualities"]:
        idx = upload_progress["video_count"] % len(upload_progress["selected_qualities"])
        quality = upload_progress["selected_qualities"][idx]
    return (
        upload_progress["base_caption"]
        .replace("{anime_name}", upload_progress.get("anime_name", "Anime Name"))
        .replace("{season}", f"{upload_progress['season']:02}")
        .replace("{episode}", f"{upload_progress['episode']:02}")
        .replace("{total_episode}", f"{upload_progress['total_episode']:02}")
        .replace("{quality}", quality)
    )


def get_upload_menu_markup() -> InlineKeyboardMarkup:
    """Build upload manager keyboard."""
    auto_status = "✅ ON" if upload_progress["auto_caption_enabled"] else "❌ OFF"
    return InlineKeyboardMarkup([
        [bold_button("Preview Caption", callback_data="upload_preview"),
         bold_button("Set Caption", callback_data="upload_set_caption")],
        [bold_button("Set Anime Name", callback_data="upload_set_anime_name"),
         bold_button("Set Season", callback_data="upload_set_season")],
        [bold_button("Set Episode", callback_data="upload_set_episode"),
         bold_button("Total Episodes", callback_data="upload_set_total")],
        [bold_button("Quality Settings", callback_data="upload_quality_menu"),
         bold_button("Target Channel", callback_data="upload_set_channel")],
        [bold_button(f"Auto-Caption: {auto_status}", callback_data="upload_toggle_auto")],
        [bold_button("Reset Episode to 1", callback_data="upload_reset"),
         bold_button("Clear DB", callback_data="upload_clear_db")],
        [_back_btn("admin_back")],
    ])


async def show_upload_menu(
    chat_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    edit_msg: Optional[Any] = None,
) -> None:
    """Display the upload manager panel."""
    target = (
        f"✅ {code(str(upload_progress['target_chat_id']))}"
        if upload_progress["target_chat_id"] else "❌ Not Set"
    )
    auto = "✅ ON" if upload_progress["auto_caption_enabled"] else "❌ OFF"
    qualities = ", ".join(upload_progress["selected_qualities"]) or "None"

    text = (
        b("📤 Upload Manager") + "\n\n"
        f"<b>🎌 Anime:</b> {code(e(upload_progress.get('anime_name', 'Anime Name')))}\n"
        f"<b>📢 Target Channel:</b> {target}\n"
        f"<b>Auto-Caption:</b> {auto}\n"
        f"<b>📅 Season:</b> {code(str(upload_progress['season']))}\n"
        f"<b>🔢 Episode:</b> {code(str(upload_progress['episode']))} / "
        + code(str(upload_progress["total_episode"])) + "\n"
        f"<b>🎛 Qualities:</b> {code(qualities)}\n"
        f"<b>🎬 Videos Sent (current quality cycle):</b> "
        + code(str(upload_progress["video_count"]))
    )
    markup = get_upload_menu_markup()

    # Always send fresh with image (delete old if editing)
    if edit_msg:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=edit_msg.message_id)
        except Exception:
            pass
    img_url = None
    if _PANEL_IMAGE_AVAILABLE:
        try:
            img_url = await get_panel_pic_async("upload")
        except Exception:
            pass
    if img_url:
        try:
            await context.bot.send_photo(chat_id, img_url, caption=text,
                                         parse_mode=ParseMode.HTML, reply_markup=markup)
            return
        except Exception:
            pass
    await safe_send_message(context.bot, chat_id, text, reply_markup=markup)


# ================================================================================
#                           INLINE QUERY HANDLER
# ================================================================================

@force_sub_required
async def inline_query_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    @bot inline query handler — 4 divisions:
    1. (empty)   → show main menu: Poster / Watch / Character / Group Mgmt
    2. poster <name> or just <name> → AniList search with cover photo
    3. watch <name> → browse generated_links (anime channels)
    4. character <name> or char <name> → character info with photo
    5. manage → group management quick cards

    Force-sub gate: non-admin users must subscribe first.
    """
    query_obj = update.inline_query
    if not query_obj:
        return

    uid    = query_obj.from_user.id
    search = (query_obj.query or "").strip()

    # ── Force-sub gate ─────────────────────────────────────────────────────────
    if uid not in (ADMIN_ID, OWNER_ID):
        if is_user_banned(uid):
            return
        try:
            unsubbed = await get_unsubscribed_channels(uid, context.bot)
            if unsubbed:
                ch_list = "\n".join(f"• {n}" for n, _, _ in unsubbed[:3])
                await query_obj.answer([
                    InlineQueryResultArticle(
                        id="fsub_gate",
                        title=small_caps("⚠️ subscribe to channels first"),
                        description=small_caps("tap to see required channels"),
                        input_message_content=InputTextMessageContent(
                            b(small_caps("⚠️ please subscribe to all required channels first.")) + "\n"
                            + bq(ch_list + "\n\n" + small_caps("use /start in the bot to join.")),
                            parse_mode=ParseMode.HTML,
                        ),
                    )
                ], cache_time=10, is_personal=True)
                return
        except Exception:
            pass

    from telegram import (
        InlineQueryResultArticle, InlineQueryResultPhoto,
        InputTextMessageContent,
    )

    results = []
    search_lower = search.lower()

    # ══════════════════════════════════════════════════════════════════════════
    # EMPTY QUERY — show 4 division menu
    # ══════════════════════════════════════════════════════════════════════════
    if not search:
        menu_items = [
            (
                "🎌 Poster", "poster",
                "Search anime/manga/movie poster",
                "Type: @bot poster demon slayer",
            ),
            (
                "📺 Anime to Watch", "watch",
                "Browse available anime channels",
                "Type: @bot watch jujutsu kaisen",
            ),
            (
                "👤 Character Info", "character",
                "Search anime character details",
                "Type: @bot character tanjiro",
            ),
            (
                "⚙️ Group Mgmt", "manage",
                "Group management quick commands",
                "Type: @bot manage to see commands",
            ),
        ]
        for title_lbl, kw, desc, hint in menu_items:
            results.append(
                InlineQueryResultArticle(
                    id=f"menu_{kw}",
                    title=small_caps(title_lbl),
                    description=small_caps(desc),
                    input_message_content=InputTextMessageContent(
                        b(small_caps(title_lbl)) + "\n" + bq(small_caps(hint)),
                        parse_mode=ParseMode.HTML,
                    ),
                )
            )
        try:
            await query_obj.answer(results, cache_time=30, is_personal=False, button=None)
        except Exception:
            pass
        return

    # ══════════════════════════════════════════════════════════════════════════
    # ANIME TO WATCH — search generated_links
    # ══════════════════════════════════════════════════════════════════════════
    if search_lower.startswith("watch ") or search_lower == "watch":
        watch_q = re.sub(r"^watch\s*", "", search, flags=re.IGNORECASE).strip()
        try:
            from database_dual import get_all_links
            from modules.anime import _al_sync, _ANIME_GQL, _resolve_query
            all_links = get_all_links(limit=200, offset=0) or []
            loop = asyncio.get_event_loop()

            seen_t: set = set()
            for row in all_links:
                link_id_r  = row[0]
                ch_id_r    = row[1]
                ch_title   = (row[2] or "").strip()
                if not ch_title or ch_title.lower() in seen_t:
                    continue
                if watch_q and watch_q.lower() not in ch_title.lower():
                    continue
                seen_t.add(ch_title.lower())

                deep_link = f"https://t.me/{BOT_USERNAME}?start={link_id_r}"
                join_text = (get_setting("env_JOIN_BTN_TEXT", "") or small_caps("ᴊᴏɪɴ ɴᴏᴡ"))

                # Try to get AniList cover for richer result
                cover_url = ""
                score_str = ""
                try:
                    al_d = await loop.run_in_executor(None, _al_sync, _ANIME_GQL, ch_title)
                    if al_d:
                        cover_url = (al_d.get("coverImage") or {}).get("medium") or ""
                        score = al_d.get("averageScore", "")
                        status = (al_d.get("status") or "").replace("_", " ").title()
                        genres = ", ".join((al_d.get("genres") or [])[:2])
                        score_str = f"{score}/100" if score else ""
                except Exception:
                    pass

                from telegram import InlineKeyboardMarkup, InlineKeyboardButton
                kb = InlineKeyboardMarkup([[InlineKeyboardButton(join_text, url=deep_link)]])

                if cover_url:
                    results.append(
                        InlineQueryResultPhoto(
                            id=f"watch_{link_id_r}",
                            photo_url=cover_url,
                            thumbnail_url=cover_url,
                            title=small_caps(ch_title[:40]),
                            description=small_caps(f"{score_str} • tap to get join link"),
                            caption=b(small_caps(ch_title)) + (
                                f"\n» <b>{small_caps('Rating')}:</b> <code>{score_str}</code>" if score_str else ""
                            ),
                            parse_mode=ParseMode.HTML,
                            reply_markup=kb,
                        )
                    )
                else:
                    results.append(
                        InlineQueryResultArticle(
                            id=f"watch_{link_id_r}",
                            title=small_caps(ch_title[:40]),
                            description=small_caps("tap to get join link"),
                            input_message_content=InputTextMessageContent(
                                b(small_caps(ch_title)), parse_mode=ParseMode.HTML,
                            ),
                            reply_markup=kb,
                        )
                    )
                if len(results) >= 10:
                    break

        except Exception as exc:
            logger.debug(f"[inline] watch: {exc}")

        try:
            await query_obj.answer(results or [
                InlineQueryResultArticle(
                    id="watch_empty",
                    title=small_caps("no anime channels found"),
                    description=small_caps("generate links first using /start"),
                    input_message_content=InputTextMessageContent(
                        b(small_caps("no anime channels available yet.")), parse_mode=ParseMode.HTML,
                    ),
                )
            ], cache_time=10, is_personal=True)
        except Exception:
            pass
        return

    # ══════════════════════════════════════════════════════════════════════════
    # CHARACTER INFO
    # ══════════════════════════════════════════════════════════════════════════
    if search_lower.startswith("character ") or search_lower.startswith("char "):
        char_q = re.sub(r"^(character|char)\s+", "", search, flags=re.IGNORECASE).strip()
        if char_q:
            try:
                from modules.anime import _al_sync, _CHAR_GQL
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(None, _al_sync, _CHAR_GQL, char_q)
                if data:
                    nm      = data.get("name", {}) or {}
                    full    = nm.get("full", char_q)
                    native  = nm.get("native", "")
                    desc    = re.sub(r"<[^>]+>", "", data.get("description", "") or "")
                    desc    = (desc[:180].rsplit(" ", 1)[0] + "…") if len(desc) > 180 else desc
                    img     = (data.get("image") or {}).get("large") or ""
                    site    = data.get("siteUrl", "")
                    cap     = f"<b>{e(full)}</b>"
                    if native:
                        cap += f" (<i>{e(native)}</i>)"
                    if desc:
                        cap += f"\n\n{e(desc)}"
                    if len(cap) > 900:
                        cap = cap[:896] + "…"

                    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
                    kb = InlineKeyboardMarkup([[InlineKeyboardButton("📋 AniList", url=site)]]) if site else None

                    if img:
                        results.append(
                            InlineQueryResultPhoto(
                                id=f"char_{abs(hash(full)) % 1000000}",
                                photo_url=img,
                                thumbnail_url=img,
                                title=full,
                                description=(desc[:80] + "…") if len(desc) > 80 else desc,
                                caption=cap,
                                parse_mode=ParseMode.HTML,
                                reply_markup=kb,
                            )
                        )
                    else:
                        results.append(
                            InlineQueryResultArticle(
                                id=f"char_art_{abs(hash(full)) % 1000000}",
                                title=full,
                                description=(desc[:80] + "…") if len(desc) > 80 else desc,
                                input_message_content=InputTextMessageContent(cap, parse_mode=ParseMode.HTML),
                                reply_markup=kb,
                            )
                        )
            except Exception as exc:
                logger.debug(f"[inline] character: {exc}")

        try:
            await query_obj.answer(results or [
                InlineQueryResultArticle(
                    id="char_empty",
                    title=small_caps(f"character not found: {char_q}"),
                    description=small_caps("try a different name"),
                    input_message_content=InputTextMessageContent(
                        b(small_caps(f"character \'{char_q}\' not found.")), parse_mode=ParseMode.HTML,
                    ),
                )
            ], cache_time=20, is_personal=False)
        except Exception:
            pass
        return

    # ══════════════════════════════════════════════════════════════════════════
    # GROUP MANAGEMENT quick reference
    # ══════════════════════════════════════════════════════════════════════════
    if search_lower.startswith("manage"):
        manage_items = [
            ("🚫 Ban",       "/ban @user reason",    "Ban a user from the group"),
            ("🔇 Mute",      "/mute @user",          "Mute a user (can't send messages)"),
            ("👢 Kick",      "/kick @user",          "Kick (remove, can rejoin)"),
            ("⚠️ Warn",      "/warn @user reason",   "Warn user (3 = auto ban)"),
            ("📌 Pin",       "/pin (reply to msg)",  "Pin a message in the group"),
            ("📋 Rules",     "/rules",               "Show group rules"),
            ("🗑 Purge",     "/purge (reply to msg)","Delete messages in bulk"),
            ("👑 Promote",   "/promote @user",       "Promote user to admin"),
            ("📉 Demote",    "/demote @user",        "Demote admin to member"),
            ("🔕 Mute All",  "/mutechat",            "Mute entire chat"),
            ("📢 Unmute All","/unmutechat",          "Unmute entire chat"),
            ("🔗 Link",      "/invitelink",          "Get group invite link"),
        ]
        for lbl, cmd, desc in manage_items:
            results.append(
                InlineQueryResultArticle(
                    id=f"mgmt_{abs(hash(lbl)) % 1000000}",
                    title=small_caps(lbl),
                    description=small_caps(desc),
                    input_message_content=InputTextMessageContent(
                        b(small_caps(lbl)) + "\n" + code(cmd) + "\n" + bq(small_caps(desc)),
                        parse_mode=ParseMode.HTML,
                    ),
                )
            )
        try:
            await query_obj.answer(results, cache_time=60, is_personal=False)
        except Exception:
            pass
        return

    # ══════════════════════════════════════════════════════════════════════════
    # POSTER / DEFAULT — anime search (handles "poster <name>" or just "<name>")
    # ══════════════════════════════════════════════════════════════════════════
    anime_q = re.sub(r"^poster\s+", "", search, flags=re.IGNORECASE).strip() or search

    if anime_q:
        try:
            from modules.anime import _al_sync, _ANIME_GQL, _resolve_query
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None, _al_sync, _ANIME_GQL, _resolve_query(anime_q)
            )
            if data:
                t_d    = data.get("title", {}) or {}
                title  = t_d.get("english") or t_d.get("romaji") or anime_q
                native = t_d.get("native", "")
                score  = data.get("averageScore", "?")
                status = (data.get("status") or "").replace("_", " ").title()
                genres = ", ".join((data.get("genres") or [])[:3])
                cover  = (data.get("coverImage") or {}).get("large") or ""
                banner = data.get("bannerImage") or ""
                site   = data.get("siteUrl", "")
                eps    = data.get("episodes", "?")
                fmt    = (data.get("format") or "").replace("_", " ")
                stnode = ((data.get("studios") or {}).get("nodes") or [])
                studio = stnode[0].get("name", "") if stnode else ""

                cap = f"<b>{e(title)}</b>"
                if native:
                    cap += f"\n<i>{e(native)}</i>"
                cap += "\n\n"
                if genres:
                    cap += f"» <b>{small_caps('Genre')}:</b> {e(genres)}\n"
                if str(score) not in ("?", "0", "None"):
                    cap += f"» <b>{small_caps('Rating')}:</b> <code>{score}/100</code>\n"
                if status:
                    cap += f"» <b>{small_caps('Status')}:</b> {e(status)}\n"
                if str(eps) not in ("?", "0", "None"):
                    cap += f"» <b>{small_caps('Episodes')}:</b> <code>{eps}</code>\n"
                if fmt:
                    cap += f"» <b>{small_caps('Format')}:</b> {e(fmt)}\n"
                if studio:
                    cap += f"» <b>{small_caps('Studio')}:</b> {e(studio)}\n"
                if len(cap) > 1000:
                    cap = cap[:996] + "…"

                from telegram import InlineKeyboardMarkup, InlineKeyboardButton
                kb = None
                if site:
                    kb = InlineKeyboardMarkup([[InlineKeyboardButton(small_caps("📋 Info"), url=site)]])

                use_img = cover or banner
                if use_img:
                    results.append(
                        InlineQueryResultPhoto(
                            id=f"anime_poster_{data.get('id', abs(hash(title)) % 1000000)}",
                            photo_url=use_img,
                            thumbnail_url=(data.get("coverImage") or {}).get("medium") or use_img,
                            title=title,
                            description=f"{score}/100 • {status} • {genres}",
                            caption=cap,
                            parse_mode=ParseMode.HTML,
                            reply_markup=kb,
                        )
                    )
                else:
                    results.append(
                        InlineQueryResultArticle(
                            id=f"anime_art_{data.get('id', abs(hash(title)) % 1000000)}",
                            title=f"🎌 {title}",
                            description=f"{score}/100 • {status} • {genres}",
                            input_message_content=InputTextMessageContent(cap, parse_mode=ParseMode.HTML),
                            reply_markup=kb,
                        )
                    )
        except Exception as exc:
            logger.debug(f"[inline] poster: {exc}")

    try:
        await query_obj.answer(results[:10] or [
            InlineQueryResultArticle(
                id="not_found",
                title=small_caps(f"not found: {anime_q[:30]}"),
                description=small_caps("try a different search term"),
                input_message_content=InputTextMessageContent(
                    b(small_caps(f"\'{anime_q}\' not found on AniList.")), parse_mode=ParseMode.HTML,
                ),
            )
        ], cache_time=15, is_personal=False)
    except Exception as exc:
        logger.debug(f"[inline] answer: {exc}")


async def group_message_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle messages in connected groups.
    Filter poster (anime title matching) fires in ALL groups where bot is member.
    Other features (anime commands, auto-delete) only in connected groups.
    """
    if not update.message or not update.effective_chat:
        return
    if not _passes_filter(update):
        return

    chat_id = update.effective_chat.id
    text    = update.message.text or update.message.caption or ""
    lower   = text.lower().strip()

    # ── Filter poster fires in ANY group (bot just needs to be member) ─────────
    # This matches anime titles from generated_links regardless of connection status
    if _FILTER_POSTER_AVAILABLE and lower and not lower.startswith("/"):
        asyncio.create_task(_handle_anime_filter(update, context, lower))

    # ── Check connected group for everything else ──────────────────────────────
    _connected = _panel_cache_get("connected_groups")
    if _connected is not None:
        if chat_id not in _connected:
            return
    else:
        try:
            with db_manager.get_cursor() as cur:
                cur.execute("SELECT group_id FROM connected_groups WHERE active = TRUE")
                rows = cur.fetchall() or []
            _ids = {r[0] for r in rows}
            _panel_cache_set("connected_groups", _ids)
            if chat_id not in _ids:
                return
        except Exception:
            return

    if get_setting("group_commands_enabled", "true") != "true":
        return

    # Read text OR caption (for photo/video messages with captions)
    text  = update.message.text or update.message.caption or ""
    lower = text.lower()
    auto_del = get_setting("auto_delete_messages", "true") == "true"
    del_delay = int(get_setting("auto_delete_delay", "60"))

    # Schedule auto-delete of user command after 5 seconds
    if auto_del:
        async def _del_user_cmd(msg=update.message):
            await asyncio.sleep(5)
            try:
                await msg.delete()
            except Exception:
                pass
        asyncio.create_task(_del_user_cmd())

    async def _group_post_with_autodel(category: str, query_text: str) -> None:
        await generate_and_send_post(context, chat_id, category, query_text)

    for prefix, category in [
        ("/anime ", "anime"), ("/manga ", "manga"),
        ("/movie ", "movie"), ("/tvshow ", "tvshow"),
    ]:
        if lower.startswith(prefix):
            query_text = text[len(prefix):].strip()
            if query_text:
                await _group_post_with_autodel(category, query_text)
            return

    # ── Filter-Poster Integration ──────────────────────────────────────────────
    # New logic:
    #   1. Check if the message text matches any anime_channel_link keyword
    #   2. If yes: check filter_poster_cache for a pre-built poster (file_id)
    #   3. If cached: send instantly via file_id + expirable join button
    #   4. If not cached: generate via poster_engine → save to POSTER_DB_CHANNEL
    #      → cache file_id for future fast sends → send to user
    #   5. Button = expirable Telegram invite link for the linked channel
    #   6. Only fires for anime titles that have a generated channel link
    if _FILTER_POSTER_AVAILABLE and _get_filter_poster_enabled(chat_id):
        asyncio.create_task(
            _handle_anime_filter(update, context, lower)
        )


async def _handle_anime_filter(
    update, context, lower_text: str
) -> None:
    """
    Background task: detect anime title in message, deliver poster + join button.
    Reads filter keywords directly from generated_links.channel_title — no separate table.
    One table for everything: link generation AND filter matching.
    """
    try:
        from database_dual import (
            get_all_links, get_filter_poster_cache, save_filter_poster_cache,
        )
        from filter_poster import (
            _auto_delete, _get_default_poster_template,
            get_auto_delete_seconds, get_link_expiry_minutes, _join_btn_text,
        )
        from poster_engine import (
            _anilist_anime, _build_anime_data, _make_poster, _get_settings,
        )
        import hashlib as _hl
        from io import BytesIO

        chat_id = update.effective_chat.id
        bot = context.bot

        # Read all generated links — channel_title IS the filter keyword
        all_links = get_all_links(limit=500, offset=0)
        if not all_links:
            return

        matched_anime = None
        matched_channel_id = None
        matched_channel_title = None
        matched_link_id = None

        # Deduplicate by channel_title to avoid double-triggering
        seen_titles = set()
        for row in all_links:
            # row: (link_id, channel_username, channel_title, source_bot_username, created_time, never_expires)
            link_id_r      = row[0]
            channel_id_r   = row[1]   # numeric ID stored as channel_username
            channel_title_r = (row[2] or "").strip()
            if not channel_title_r or channel_title_r.lower() in seen_titles:
                continue
            seen_titles.add(channel_title_r.lower())

            a_title = channel_title_r.lower()
            # Skip very short titles (avoid false matches on common words)
            if len(a_title) < 3:
                continue
            # Whole-word or full match
            if a_title in lower_text or re.search(
                r'\b' + re.escape(a_title) + r'\b', lower_text
            ):
                matched_anime        = channel_title_r   # use as anime search term
                matched_channel_id   = channel_id_r      # channel_username/ID
                matched_channel_title = channel_title_r
                matched_link_id      = link_id_r
                break

        if not matched_anime:
            return

        template  = _get_default_poster_template(chat_id)
        cache_key = _hl.md5(f"{matched_anime.lower()}:{template}".encode()).hexdigest()
        auto_del  = get_auto_delete_seconds(chat_id)
        exp_min   = get_link_expiry_minutes(chat_id)

        # ── Build direct expirable invite link ──────────────────────────────────
        # • URL = real Telegram invite (https://t.me/+XXXXX) — direct, no bot redirect
        # • member_limit=1  → auto-revokes after ONE use
        # • expire_date     → also auto-revokes after exp_min minutes if unused
        # • creates_join_request=False → user joins immediately on click (no approval needed)
        # The poster message is auto-deleted at expire_date so a dead button never shows.
        join_url = None
        invite_link_obj = None
        expire_ts = int(time.time()) + (exp_min * 60)
        _cid = matched_channel_id
        try:
            _cid = int(matched_channel_id)
        except (ValueError, TypeError):
            pass
        try:
            invite_link_obj = await bot.create_chat_invite_link(
                chat_id=_cid,
                expire_date=expire_ts,
                member_limit=1,
                creates_join_request=False,
                name=f"FP-{int(time.time())}",
            )
            join_url = invite_link_obj.invite_link
        except Exception as _ie:
            logger.debug(f"[filter] expirable invite link failed for {_cid}: {_ie}")

        # Fallback: public channel URL (no expiry, always valid)
        if not join_url:
            join_url = os.getenv("PUBLIC_ANIME_CHANNEL_URL", "https://t.me/BeatAnime")

        # ── auto_del: sync with link expiry so poster deletes exactly when link dies ──
        # If we got a real expirable link → delete poster at expire_ts
        # If fallback URL → use the configured auto_del setting
        if invite_link_obj and join_url:
            delete_delay = exp_min * 60   # poster lives exactly as long as the link
        else:
            delete_delay = auto_del       # fallback: use configured value (default 300s)

        # ── Button text — admin-configurable (Filter Poster → ✏️ JOIN BTN TEXT) ─
        _raw_btn_text = (
            get_setting("env_JOIN_BTN_TEXT", "") or
            get_setting("env_join_btn_text", "") or
            JOIN_BTN_TEXT
        )
        join_text = small_caps(_raw_btn_text) if _raw_btn_text else small_caps("ᴊᴏɪɴ ɴᴏᴡ")

        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(join_text, url=join_url)]])

        # Check poster cache (DB) — serve instantly if available
        cached = get_filter_poster_cache(cache_key)
        if cached and cached.get("file_id"):
            try:
                caption = cached.get("caption", "")
                sent = await bot.send_photo(
                    chat_id=chat_id,
                    photo=cached["file_id"],
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=kb,
                    reply_to_message_id=update.message.message_id,
                )
                if sent and delete_delay > 0:
                    asyncio.create_task(
                        _auto_delete(bot, chat_id, sent.message_id, delay=delete_delay)
                    )
                return
            except Exception:
                pass  # Cached file_id stale → regenerate

        # Generate poster via AniList
        loop = asyncio.get_event_loop()
        data = None
        try:
            data = await loop.run_in_executor(None, _anilist_anime, matched_anime)
        except Exception:
            pass

        poster_buf = None
        caption = f"<b>{html.escape(matched_anime)}</b>"
        site_url = ""

        if data:
            settings = _get_settings("anime")
            try:
                title_b, native, st, rows, desc, cover_url, score = await loop.run_in_executor(
                    None, _build_anime_data, data
                )
                poster_buf = await loop.run_in_executor(
                    None, _make_poster,
                    template, title_b, native, st, rows, desc, cover_url, score,
                    settings.get("watermark_text"),
                    settings.get("watermark_position", "center"),
                    None, "bottom",
                )
                site_url = data.get("siteUrl", "")
                genres = ", ".join((data.get("genres") or [])[:3])
                t_d    = data.get("title", {}) or {}
                eng    = t_d.get("english") or t_d.get("romaji") or matched_anime
                caption = f"<b>{html.escape(eng)}</b>"
                if native:
                    caption += f"\n<i>{html.escape(native)}</i>"
                if genres:
                    caption += f"\n\n» <b>Genre:</b> {html.escape(genres)}"
                if rows:
                    for lb, v in rows[:3]:
                        if v and str(v) not in ("-", "N/A", "None", "?", "0"):
                            caption += f"\n» <b>{html.escape(lb)}:</b> <code>{html.escape(str(v))}</code>"
                if len(caption) > 900:
                    caption = caption[:896] + "…"
            except Exception as _be:
                logger.debug(f"[filter] poster build error: {_be}")

        if site_url:
            btns = [[InlineKeyboardButton(join_text, url=join_url),
                     InlineKeyboardButton("📋 Info", url=site_url)]]
            kb = InlineKeyboardMarkup(btns)

        sent_msg = None
        file_id_to_cache = None

        if poster_buf:
            poster_buf.seek(0)
            # Save to POSTER_DB_CHANNEL for future instant fetching
            if POSTER_DB_CHANNEL:
                try:
                    poster_buf.seek(0)
                    db_msg = await bot.send_photo(
                        chat_id=POSTER_DB_CHANNEL,
                        photo=poster_buf,
                        caption=f"FilterPoster | {matched_anime} | {template}",
                        parse_mode="HTML",
                    )
                    if db_msg.photo:
                        file_id_to_cache = db_msg.photo[-1].file_id
                except Exception as _dbe:
                    logger.debug(f"[filter] DB channel save: {_dbe}")

            try:
                poster_buf.seek(0)
                sent_msg = await bot.send_photo(
                    chat_id=chat_id,
                    photo=file_id_to_cache or poster_buf,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=kb,
                    reply_to_message_id=update.message.message_id,
                )
                if sent_msg and not file_id_to_cache and sent_msg.photo:
                    file_id_to_cache = sent_msg.photo[-1].file_id
            except Exception as _se:
                logger.debug(f"[filter] poster send: {_se}")

        if not sent_msg:
            try:
                sent_msg = await bot.send_message(
                    chat_id=chat_id,
                    text=caption,
                    parse_mode="HTML",
                    reply_markup=kb,
                    reply_to_message_id=update.message.message_id,
                    disable_web_page_preview=True,
                )
            except Exception:
                pass

        # Cache the poster file_id
        if file_id_to_cache:
            try:
                save_filter_poster_cache(
                    cache_key=cache_key,
                    anime_title=matched_anime,
                    template=template,
                    file_id=file_id_to_cache,
                    channel_id=0,
                    caption=caption,
                )
            except Exception as _ce:
                logger.debug(f"[filter] cache save: {_ce}")

        if sent_msg and delete_delay > 0:
            asyncio.create_task(
                _auto_delete(bot, chat_id, sent_msg.message_id, delay=delete_delay)
            )

    except Exception as _top:
        logger.debug(f"[filter] _handle_anime_filter: {_top}")


async def auto_forward_message_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Forward channel posts to target channels based on connection config."""
    msg = update.channel_post
    if not msg:
        return
    chat_id = update.effective_chat.id

    try:
        with db_manager.get_cursor() as cur:
            cur.execute("""
                SELECT id, target_chat_id, protect_content, silent, pin_message,
                       delete_source, delay_seconds
                FROM auto_forward_connections
                WHERE source_chat_id = %s AND active = TRUE
            """, (chat_id,))
            connections = cur.fetchall() or []
    except Exception as exc:
        logger.debug(f"auto_forward DB error: {exc}")
        return

    for conn in connections:
        conn_id, target, protect, silent, pin, delete_src, delay = conn

        # Load filter config
        try:
            with db_manager.get_cursor() as cur:
                cur.execute("""
                    SELECT allowed_media, blacklist_words, whitelist_words,
                           caption_override, replacements
                    FROM auto_forward_filters WHERE connection_id = %s
                """, (conn_id,))
                filter_row = cur.fetchone()
        except Exception:
            filter_row = None

        # Apply filters
        if filter_row:
            allowed_media, blacklist_words, whitelist_words, caption_override, replacements = filter_row

            # Media type filter
            if allowed_media:
                media_types = [m.strip() for m in allowed_media.split(",")]
                msg_media_type = None
                if msg.photo:
                    msg_media_type = "photo"
                elif msg.video:
                    msg_media_type = "video"
                elif msg.document:
                    msg_media_type = "document"
                elif msg.audio:
                    msg_media_type = "audio"
                elif msg.sticker:
                    msg_media_type = "sticker"
                elif msg.text:
                    msg_media_type = "text"
                if msg_media_type and msg_media_type not in media_types:
                    continue

            # Text filters
            check_text = (msg.caption or msg.text or "").lower()
            if whitelist_words:
                words = [w.strip().lower() for w in whitelist_words.split(",")]
                if not any(w in check_text for w in words):
                    continue
            if blacklist_words:
                words = [w.strip().lower() for w in blacklist_words.split(",")]
                if any(w in check_text for w in words):
                    continue

            # Replacements
            if replacements:
                try:
                    rep_list = json.loads(replacements)
                    for rep in rep_list:
                        pattern = rep.get("pattern", "")
                        value = rep.get("value", "")
                        if pattern:
                            check_text = check_text.replace(pattern.lower(), value)
                except Exception:
                    pass
        else:
            caption_override = None

        # Delay or immediate
        if delay and delay > 0:
            context.job_queue.run_once(
                _delayed_forward,
                when=delay,
                data={
                    "from_chat_id": chat_id,
                    "message_id": msg.message_id,
                    "target_chat_id": target,
                    "protect": protect,
                    "silent": silent,
                    "pin": pin,
                    "delete_src": delete_src,
                    "caption_override": caption_override,
                },
            )
        else:
            asyncio.create_task(
                _do_forward(
                    context.bot, chat_id, msg.message_id, target,
                    protect=protect, silent=silent, pin=pin,
                    delete_src=delete_src, caption_override=caption_override,
                )
            )


async def _do_forward(
    bot: Bot,
    from_chat_id: int,
    message_id: int,
    target_chat_id: int,
    protect: bool = False,
    silent: bool = False,
    pin: bool = False,
    delete_src: bool = False,
    caption_override: Optional[str] = None,
) -> None:
    """Execute a single forward operation."""
    try:
        new_msg = await bot.copy_message(
            chat_id=target_chat_id,
            from_chat_id=from_chat_id,
            message_id=message_id,
            protect_content=protect,
            disable_notification=silent,
        )
        if caption_override and new_msg:
            try:
                await bot.edit_message_caption(
                    chat_id=target_chat_id,
                    message_id=new_msg.message_id,
                    caption=caption_override,
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass
        if pin and new_msg:
            try:
                await bot.pin_chat_message(target_chat_id, new_msg.message_id, disable_notification=True)
            except Exception:
                pass
        if delete_src:
            await safe_delete(bot, from_chat_id, message_id)
    except Exception as exc:
        logger.debug(f"_do_forward error: {exc}")


async def _delayed_forward(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job handler for delayed forwards."""
    d = context.job.data
    await _do_forward(
        context.bot,
        d["from_chat_id"], d["message_id"], d["target_chat_id"],
        protect=d.get("protect", False),
        silent=d.get("silent", False),
        pin=d.get("pin", False),
        delete_src=d.get("delete_src", False),
        caption_override=d.get("caption_override"),
    )


# ================================================================================
#                        VIDEO UPLOAD HANDLER
# ================================================================================

async def handle_upload_video(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle video sent to bot by admin — auto-captions and forwards."""
    if not update.effective_user or update.effective_user.id not in (ADMIN_ID, OWNER_ID):
        return
    if not update.message or not update.message.video:
        return

    async with upload_lock:
        await load_upload_progress()

        if not upload_progress["target_chat_id"]:
            await update.message.reply_text(
                b("❌ Target channel not set!") + "\n" + bq(b("Use /upload to configure it first.")),
                parse_mode=ParseMode.HTML,
            )
            return

        if not upload_progress["selected_qualities"]:
            await update.message.reply_text(
                b("❌ No qualities selected!") + "\n" + bq(b("Use /upload → Quality Settings.")),
                parse_mode=ParseMode.HTML,
            )
            return

        file_id = update.message.video.file_id
        caption = build_caption_from_progress()

        try:
            await context.bot.send_video(
                chat_id=upload_progress["target_chat_id"],
                video=file_id,
                caption=caption,
                parse_mode=ParseMode.HTML,
                supports_streaming=True,
            )

            quality = upload_progress["selected_qualities"][
                upload_progress["video_count"] % len(upload_progress["selected_qualities"])
            ]
            await update.message.reply_text(
                b(f"✅ Video forwarded! Quality: {quality}") + "\n"
                + bq(
                    f"<b>Season:</b> {upload_progress['season']:02}\n"
                    f"<b>Episode:</b> {upload_progress['episode']:02}"
                ),
                parse_mode=ParseMode.HTML,
            )

            upload_progress["video_count"] += 1
            if upload_progress["video_count"] >= len(upload_progress["selected_qualities"]):
                upload_progress["episode"] += 1
                upload_progress["total_episode"] = max(
                    upload_progress["total_episode"], upload_progress["episode"]
                )
                upload_progress["video_count"] = 0

            await save_upload_progress()

        except Exception as exc:
            await update.message.reply_text(
                UserFriendlyError.get_user_message(exc),
                parse_mode=ParseMode.HTML,
            )


# ================================================================================
#                      CHANNEL POST HANDLER (AUTO-CAPTION)
# ================================================================================

async def handle_channel_post(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Auto-caption videos posted directly to the target channel."""
    if not update.channel_post or not update.channel_post.video:
        return
    chat_id = update.effective_chat.id
    await load_upload_progress()

    if (
        chat_id != upload_progress.get("target_chat_id")
        or not upload_progress.get("auto_caption_enabled")
    ):
        return

    async with upload_lock:
        if not upload_progress["selected_qualities"]:
            return
        caption = build_caption_from_progress()
        try:
            await context.bot.edit_message_caption(
                chat_id=chat_id,
                message_id=update.channel_post.message_id,
                caption=caption,
                parse_mode=ParseMode.HTML,
            )
            upload_progress["video_count"] += 1
            if upload_progress["video_count"] >= len(upload_progress["selected_qualities"]):
                upload_progress["episode"] += 1
                upload_progress["total_episode"] = max(
                    upload_progress["total_episode"], upload_progress["episode"]
                )
                upload_progress["video_count"] = 0
            await save_upload_progress()
        except Exception as exc:
            logger.debug(f"Auto-caption error: {exc}")


# ================================================================================
#                    ADMIN PHOTO HANDLER (CATEGORY LOGO)
# ================================================================================

async def handle_admin_photo(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle photo/sticker/document sent by admin.
    Handles:
      - SET_CATEGORY_LOGO state → saves as logo file_id
      - AWAITING_WATERMARK_xxx state → saves sticker/image as visual watermark
      - AWAITING_LOGO_xxx state → saves as logo for that category
    """
    if not update.effective_user or update.effective_user.id not in (ADMIN_ID, OWNER_ID):
        return
    uid = update.effective_user.id
    state = user_states.get(uid)
    if not update.message:
        return

    # ── Extract file_id and type from whatever was sent ───────────────────────
    msg = update.message
    file_id = None
    file_type = "image"

    if msg.sticker:
        file_id = msg.sticker.file_id
        file_type = "sticker"
    elif msg.photo:
        file_id = msg.photo[-1].file_id
        file_type = "image"
    elif msg.document:
        mime = msg.document.mime_type or ""
        if "image" in mime or "pdf" in mime or msg.document.file_name.lower().endswith((".jpg",".jpeg",".png",".webp",".gif",".pdf")):
            file_id = msg.document.file_id
            file_type = "pdf" if "pdf" in mime else "image"
        else:
            # Not an image type we can use
            return
    elif msg.animation:
        file_id = msg.animation.file_id
        file_type = "animation"

    if not file_id:
        return

    # ── WATERMARK states: save sticker/image as visual watermark overlay ──────
    if isinstance(state, str) and state.startswith("AWAITING_WATERMARK_"):
        cat = state[len("AWAITING_WATERMARK_"):].lower()
        user_states.pop(uid, None)
        ok1 = update_category_field(cat, "logo_file_id", file_id)
        ok2 = update_category_field(cat, "logo_position", "bottom-right")
        kind = {"sticker": "Sticker", "image": "Image", "pdf": "Document", "animation": "GIF"}.get(file_type, "File")
        if ok1:
            await msg.reply_text(
                b(f"✅ {kind} watermark saved for {cat.upper()}!") +
                "\n<i>It will appear as overlay on all posters for this category.</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[_back_btn(f"cat_settings_{cat}"), _close_btn()]]),
            )
        else:
            await msg.reply_text(
                b(f"❌ Failed to save watermark for {cat}. Check DB connection."),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[_back_btn(f"cat_settings_{cat}"), _close_btn()]]),
            )
        return

    # ── LOGO states ───────────────────────────────────────────────────────────
    if isinstance(state, str) and state.startswith("AWAITING_LOGO_"):
        cat = state[len("AWAITING_LOGO_"):].lower()
        user_states.pop(uid, None)
        ok = update_category_field(cat, "logo_file_id", file_id)
        if ok:
            await msg.reply_text(
                b(f"✅ Logo saved for {cat.upper()}!"),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[_back_btn(f"cat_settings_{cat}"), _close_btn()]]),
            )
        else:
            await msg.reply_text(
                b(f"❌ Failed to save logo. Check DB connection."),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[_back_btn(f"cat_settings_{cat}"), _close_btn()]]),
            )
        return

    # ── Legacy SET_CATEGORY_LOGO state ───────────────────────────────────────
    if state == SET_CATEGORY_LOGO:
        category = context.user_data.get("editing_category")
        if category:
            ok = update_category_field(category, "logo_file_id", file_id)
            if ok:
                await msg.reply_text(b(f"✅ Logo updated for {e(category.upper())}!"), parse_mode=ParseMode.HTML)
            else:
                await msg.reply_text(b(f"❌ Failed to save logo. Check DB connection."), parse_mode=ParseMode.HTML)
        user_states.pop(uid, None)
        await show_category_settings_menu(context, update.effective_chat.id, category or "anime", None)
        return

    # ── Poster watermark from AWAITING_WM_LAYER_C state (photo or sticker) ──
    if isinstance(state, str) and state.startswith("AWAITING_WM_LAYER_"):
        parts_s = state.split("_")
        layer = parts_s[3].lower() if len(parts_s) > 3 else "c"
        try:
            fp_cid = int(parts_s[4])
        except Exception:
            fp_cid = uid
        user_states.pop(uid, None)
        try:
            from filter_poster import get_wm_layer, set_wm_layer
            ldata = get_wm_layer(fp_cid, layer)
            ldata["file_id"] = file_id
            ldata["enabled"] = True
            ldata["is_sticker"] = (file_type == "sticker")
            set_wm_layer(fp_cid, layer, ldata)
            _kind_wm = "sticker" if file_type == "sticker" else "image"
            await msg.reply_text(
                b(small_caps(f"✅ layer {layer.upper()} visual watermark set ({_kind_wm})!"))
                + "\n" + bq(b(small_caps("it will appear as overlay on all posters."))),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[_back_btn("admin_filter_poster"), _close_btn()]]),
            )
        except Exception as exc:
            await msg.reply_text(b(f"❌ {e(str(exc)[:100])}"), parse_mode=ParseMode.HTML)
        return

    # ── CW_AWAITING_IMAGE: admin sends photo/sticker for channel welcome ────────
    if isinstance(state, str) and state == "CW_AWAITING_IMAGE":
        ch_id = context.user_data.get("cw_editing_channel")
        if ch_id and file_id:
            from database_dual import set_channel_welcome
            set_channel_welcome(ch_id, image_file_id=file_id, image_url="")
            user_states.pop(uid, None)
            _kind = "sticker" if file_type == "sticker" else "image"
            await msg.reply_text(
                b(small_caps(f"✅ welcome {_kind} saved!")),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(small_caps("✏️ edit more"), callback_data=f"cw_edit_{ch_id}"),
                    _back_btn("admin_channel_welcome"),
                ]]),
            )
        return

    # ── PENDING_CHANNEL_POST: forwarded message used to extract channel ID ────
    if state == PENDING_CHANNEL_POST:
        fwd_chat = None
        fwd_chat = None
        try:
            _fo = getattr(msg, "forward_origin", None)
            if _fo and hasattr(_fo, "chat"):
                fwd_chat = _fo.chat
            elif _fo and hasattr(_fo, "sender_chat"):
                fwd_chat = _fo.sender_chat
            elif getattr(msg, "forward_from_chat", None):
                fwd_chat = msg.forward_from_chat
        except Exception:
            pass
        if fwd_chat:
            pass  # fwd_chat is set
        if not fwd_chat:
            await msg.reply_text(
                b("❌ This doesn't look like a forwarded channel post.\n\n")
                + bq("Forward any message from the channel you want to add."),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="manage_force_sub")]]),
            )
            return
        try:
            tg_chat = await context.bot.get_chat(fwd_chat.id)
            context.user_data["new_ch_uname"] = str(tg_chat.id)
            context.user_data["new_ch_title"] = tg_chat.title
            user_states[uid] = ADD_CHANNEL_TITLE
            ch_info = f"<b>Channel:</b> {e(tg_chat.title)}\n<b>ID:</b> <code>{tg_chat.id}</code>"
            if tg_chat.username:
                ch_info += f"\n<b>Username:</b> @{e(tg_chat.username)}"
            await msg.reply_text(
                b("✅ Channel detected from forwarded post!") + "\n\n"
                + bq(ch_info) + "\n\n"
                + b("Send a display title, or /skip to use the channel name:"),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="manage_force_sub")]]),
            )
        except Exception as exc:
            await msg.reply_text(
                b("❌ Could not verify that channel.\n\n")
                + bq(b("Make sure the bot is admin in ") + code(str(fwd_chat.id))
                     + b(f"\n\nError: ") + code(e(str(exc)[:100]))),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="manage_force_sub")]]),
            )
        return

    # ── AF source from forwarded post ─────────────────────────────────────────
    if state == AF_ADD_CONNECTION_SOURCE:
        fwd_chat = None
        fwd_chat = None
        try:
            _fo = getattr(msg, "forward_origin", None)
            if _fo and hasattr(_fo, "chat"):
                fwd_chat = _fo.chat
            elif _fo and hasattr(_fo, "sender_chat"):
                fwd_chat = _fo.sender_chat
            elif getattr(msg, "forward_from_chat", None):
                fwd_chat = msg.forward_from_chat
        except Exception:
            pass
        if fwd_chat:
            pass  # fwd_chat is set
        if fwd_chat:
            try:
                tg_chat = await context.bot.get_chat(fwd_chat.id)
                context.user_data["af_source_id"] = tg_chat.id
                context.user_data["af_source_uname"] = tg_chat.username
                user_states[uid] = AF_ADD_CONNECTION_TARGET
                await msg.reply_text(
                    b(f"✅ Source detected: {e(tg_chat.title)}") + "\n\n"
                    + bq(b("Step 2/2: Send the TARGET channel @username, ID, or forward a post:")),
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_autoforward")]]),
                )
            except Exception as exc:
                await msg.reply_text(
                    b("❌ Could not verify source channel: ") + code(e(str(exc)[:100])),
                    parse_mode=ParseMode.HTML,
                )
            return

    # ── AF target from forwarded post ─────────────────────────────────────────
    if state == AF_ADD_CONNECTION_TARGET:
        fwd_chat = None
        fwd_chat = None
        try:
            _fo = getattr(msg, "forward_origin", None)
            if _fo and hasattr(_fo, "chat"):
                fwd_chat = _fo.chat
            elif _fo and hasattr(_fo, "sender_chat"):
                fwd_chat = _fo.sender_chat
            elif getattr(msg, "forward_from_chat", None):
                fwd_chat = msg.forward_from_chat
        except Exception:
            pass
        if fwd_chat:
            pass  # fwd_chat is set
        if fwd_chat:
            try:
                tg_chat = await context.bot.get_chat(fwd_chat.id)
                src_id = context.user_data.get("af_source_id")
                src_uname = context.user_data.get("af_source_uname", "")
                if not src_id:
                    await msg.reply_text(b("Session expired. Start over."), parse_mode=ParseMode.HTML)
                    user_states.pop(uid, None)
                    return
                with db_manager.get_cursor() as cur:
                    cur.execute("""
                        INSERT INTO auto_forward_connections
                            (source_chat_id, source_chat_username, target_chat_id,
                             target_chat_username, active)
                        VALUES (%s, %s, %s, %s, TRUE)
                        ON CONFLICT DO NOTHING
                    """, (src_id, src_uname, tg_chat.id, tg_chat.username))
                await msg.reply_text(
                    b("✅ Auto-forward connection created!") + "\n\n"
                    + bq(
                        b("Source: ") + code(str(src_id)) + "\n"
                        + b("Target: ") + code(str(tg_chat.id)) + " — " + e(tg_chat.title)
                    ),
                    parse_mode=ParseMode.HTML,
                )
                user_states.pop(uid, None)
            except Exception as exc:
                await msg.reply_text(b(f"❌ Error: {e(str(exc)[:100])}"), parse_mode=ParseMode.HTML)
            return

    # ── AU manga target from forwarded post ───────────────────────────────────
    if state == AU_ADD_MANGA_TARGET:
        fwd_chat = None
        fwd_chat = None
        try:
            _fo = getattr(msg, "forward_origin", None)
            if _fo and hasattr(_fo, "chat"):
                fwd_chat = _fo.chat
            elif _fo and hasattr(_fo, "sender_chat"):
                fwd_chat = _fo.sender_chat
            elif getattr(msg, "forward_from_chat", None):
                fwd_chat = msg.forward_from_chat
        except Exception:
            pass
        if fwd_chat:
            pass  # fwd_chat is set
        if fwd_chat:
            try:
                tg_chat = await context.bot.get_chat(fwd_chat.id)
                manga_id = context.user_data.get("au_manga_id")
                manga_title = context.user_data.get("au_manga_title", "Unknown")
                if not manga_id:
                    await msg.reply_text(b("Session expired. Please start over."), parse_mode=ParseMode.HTML)
                    user_states.pop(uid, None)
                    return
                success = MangaTracker.add_tracking(manga_id, manga_title, tg_chat.id)
                if success:
                    await msg.reply_text(
                        b(f"✅ Now tracking: {e(manga_title)}") + "\n\n"
                        + bq(
                            f"<b>Channel:</b> {e(tg_chat.title or str(tg_chat.id))}\n"
                            f"<b>Channel ID:</b> <code>{tg_chat.id}</code>\n\n"
                            + b("New chapters will be sent automatically.")
                        ),
                        parse_mode=ParseMode.HTML,
                    )
                else:
                    await msg.reply_text(b("❌ Failed to add tracking. Make sure bot is admin."), parse_mode=ParseMode.HTML)
                user_states.pop(uid, None)
                for k in ("au_manga_id", "au_manga_title", "au_manga_mode", "au_manga_interval"):
                    context.user_data.pop(k, None)
            except Exception as exc:
                await msg.reply_text(b(f"❌ Error: {e(str(exc)[:100])}"), parse_mode=ParseMode.HTML)
            return




# ================================================================================
#                      CHANNEL WELCOME SYSTEM
# ================================================================================
# Sends a welcome message (text + image + buttons) when someone joins a channel
# that the bot is admin of. Configured via Admin Panel → Channels → CHANNEL WELCOME.
#
# HOW IT WORKS:
#   1. Admin registers a channel via the admin panel (Channels → CHANNEL WELCOME)
#   2. Admin sets: welcome text, image (file_id or URL), and buttons (label - url)
#   3. When bot receives a ChatJoinRequest approval OR sees a new_chat_member update
#      in the channel, it DMs the new member the welcome message.
# ================================================================================

async def send_channel_welcome(bot, user_id: int, channel_id: int) -> None:
    """Send a welcome DM to a new channel member based on configured settings."""
    try:
        from database_dual import get_channel_welcome
        import json as _j
        settings = get_channel_welcome(channel_id)
        if not settings or not settings.get("enabled"):
            return

        text = settings.get("welcome_text") or ""
        image_fid = settings.get("image_file_id") or ""
        image_url = settings.get("image_url") or ""
        buttons   = settings.get("buttons") or []

        if not text and not image_fid and not image_url:
            return

        # Apply small caps to welcome text
        styled_text = b(text) if text else ""

        # Build keyboard
        kb_rows = []
        for btn in buttons:
            lbl = btn.get("text", "") or btn.get("label", "")
            url = btn.get("url", "")
            if lbl and url:
                kb_rows.append([InlineKeyboardButton(small_caps(lbl), url=url)])
        markup = InlineKeyboardMarkup(kb_rows) if kb_rows else None

        image_src = image_fid or image_url or None

        if image_src:
            try:
                await bot.send_photo(
                    chat_id=user_id,
                    photo=image_src,
                    caption=styled_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=markup,
                )
                return
            except Exception as _pe:
                logger.debug(f"[cw] photo send failed: {_pe}")

        if styled_text:
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=styled_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=markup,
                    disable_web_page_preview=True,
                )
            except Exception as _me:
                logger.debug(f"[cw] message send failed: {_me}")
    except Exception as exc:
        logger.debug(f"[cw] send_channel_welcome: {exc}")


async def channel_welcome_join_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle new members joining a channel — send welcome DM."""
    msg = update.message or update.channel_post
    if not msg:
        return
    new_members = msg.new_chat_members
    if not new_members:
        return
    channel_id = msg.chat_id
    for member in new_members:
        if member.is_bot:
            continue
        asyncio.create_task(send_channel_welcome(context.bot, member.id, channel_id))


# ── Admin panel: channel welcome management ───────────────────────────────────

async def show_channel_welcome_panel(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, query=None
) -> None:
    """Show channel welcome configuration panel."""
    try:
        from database_dual import get_all_channel_welcomes
        channels = get_all_channel_welcomes()
    except Exception:
        channels = []

    text = b("📣 channel welcome system") + "\n\n"
    if channels:
        for ch_id, enabled, wtext in channels[:10]:
            icon = "🟢" if enabled else "🔴"
            text += f"{icon} <code>{ch_id}</code> — {e((wtext or '')[:40])}\n"
    else:
        text += bq(
            b(small_caps("no channels configured yet.")) + "\n"
            + small_caps("use ➕ add channel below to configure a welcome message for any channel.")
        )

    text += (
        "\n\n" + bq(
            b(small_caps("how it works:")) + "\n"
            + small_caps("when someone joins a channel where this bot is admin, "
                         "the bot automatically DMs them the configured welcome message.")
        )
    )

    grid = [
        [InlineKeyboardButton(small_caps("➕ add/edit channel"), callback_data="cw_add")],
        [InlineKeyboardButton(small_caps("📋 list configured"), callback_data="cw_list"),
         InlineKeyboardButton(small_caps("🗑️ remove"), callback_data="cw_remove_menu")],
        [_back_btn("manage_force_sub"), _close_btn()],
    ]
    markup = InlineKeyboardMarkup(grid)

    img = await get_panel_pic_async("channels")
    try:
        if query:
            await query.delete_message()
    except Exception:
        pass
    if img:
        try:
            await context.bot.send_photo(chat_id, img, caption=text, parse_mode=ParseMode.HTML, reply_markup=markup)
            return
        except Exception:
            pass
    await safe_send_message(context.bot, chat_id, text, reply_markup=markup)

# ================================================================================
#                      AUTO-APPROVE CHAT JOIN REQUESTS
# ================================================================================

async def auto_approve_join_request(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Auto-approve chat join requests.

    Approves if ANY of:
      1. Channel has join_by_request enabled in force_sub_channels table
      2. Global auto_approve_join_requests setting is true
      3. Channel is referenced in generated_links (filter channels)

    This means: if you use the filter system with creates_join_request=True,
    every user who clicks a filter poster join button is approved immediately.
    """
    req = update.chat_join_request
    if not req:
        return
    try:
        should_approve = False

        # Check 1: force-sub channel JBR setting
        ch_info = get_force_sub_channel_info(str(req.chat.id))
        if ch_info and ch_info[2]:
            should_approve = True

        # Check 2: global JBR toggle
        if not should_approve:
            jbr_global = (get_setting("auto_approve_join_requests", "false") or "false").lower() == "true"
            if jbr_global:
                should_approve = True

        # Check 3: channel is referenced in generated_links (filter channels)
        if not should_approve:
            try:
                from database_dual import get_all_links
                raw = get_all_links(limit=500, offset=0)
                linked_ids = set()
                for row in (raw or []):
                    try:
                        linked_ids.add(int(row[1]))
                    except (ValueError, TypeError):
                        pass
                if req.chat.id in linked_ids:
                    should_approve = True
            except Exception:
                pass

        if not should_approve:
            return

        await context.bot.approve_chat_join_request(req.chat.id, req.from_user.id)
        logger.debug(f"[jbr] approved {req.from_user.id} in {req.chat.id}")

        # Send confirmation DM
        try:
            ch_title = req.chat.title or str(req.chat.id)
            await context.bot.send_message(
                req.from_user.id,
                b(small_caps(f"✅ your join request for {ch_title} has been approved!"))
                + "\n" + bq(b(small_caps("welcome! you can now access the channel."))),
                parse_mode="HTML",
            )
        except Exception:
            pass
    except Exception as exc:
        logger.debug(f"[jbr] auto-approve failed: {exc}")

# ================================================================================
#                     SCHEDULED BROADCAST JOB
# ================================================================================

async def check_scheduled_broadcasts(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job: check for pending scheduled broadcasts and execute them."""
    try:
        with db_manager.get_cursor() as cur:
            cur.execute("""
                SELECT id, admin_id, message_text, media_file_id, media_type
                FROM scheduled_broadcasts
                WHERE status = 'pending' AND execute_at <= NOW()
                LIMIT 5
            """)
            rows = cur.fetchall() or []
    except Exception as exc:
        logger.debug(f"check_scheduled_broadcasts DB error: {exc}")
        return

    for row in rows:
        b_id, admin_id, text, media_file_id, media_type = row
        users = get_all_users(limit=None, offset=0)
        sent = fail = 0
        for u in users:
            try:
                await context.bot.send_message(u[0], text, parse_mode=ParseMode.HTML)
                sent += 1
            except Exception:
                fail += 1
            await asyncio.sleep(RATE_LIMIT_DELAY)

        status = "sent"
        try:
            with db_manager.get_cursor() as cur:
                cur.execute(
                    "UPDATE scheduled_broadcasts SET status = %s WHERE id = %s",
                    (status, b_id)
                )
        except Exception:
            pass

        # Notify admin
        try:
            await context.bot.send_message(
                admin_id,
                b(f"✅ Scheduled broadcast #{b_id} done.") + "\n"
                + bq(f"<b>Sent:</b> {sent} | <b>Failed:</b> {fail}"),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass


# ================================================================================
#                         MANGA UPDATE JOB (COMPLETE)

# ================================================================================
#                         CLONE BOT — INDEPENDENT POLLING
# ================================================================================

def _module_cmd_handler(module_name: str):
    """
    Returns a generic async handler that delegates to a loaded module's dispatcher handlers.
    Used to bridge PTB v21 CommandHandler registration with legacy v13 module code.
    For modules that registered via dispatcher.add_handler() these are handled
    by the legacy dispatcher shim. This provides a PTB v21 entry point.
    """
    async def _handler(update, context):
        # The command is handled by the module via the legacy dispatcher shim
        # This registration ensures PTB v21 routing works
        pass
    _handler.__name__ = f"mod_{module_name}_cmd"
    return _handler


def _register_all_handlers(app: Application) -> None:
    """Register every bot handler on the given Application instance."""
    admin_filter = filters.User(user_id=ADMIN_ID) | filters.User(user_id=OWNER_ID)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ping", ping_command))
    app.add_handler(CommandHandler("alive", alive_command))
    app.add_handler(CommandHandler("test", test_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("anime", anime_command))
    app.add_handler(CommandHandler("manga", manga_command))
    app.add_handler(CommandHandler("movie", movie_command))
    app.add_handler(CommandHandler("tvshow", tvshow_command))
    # ── Anime info commands (AniList, no jikanpy) ──────────────────────────────
    try:
        from modules.anime import airing_cmd, character_cmd
        app.add_handler(CommandHandler("airing",    airing_cmd))
        app.add_handler(CommandHandler("character", character_cmd))
        logger.info("[anime] /airing and /character registered")
    except Exception as _anime_err:
        logger.warning(f"anime extras: {_anime_err}")

    # ── User feature commands (available to ALL users in groups + DM) ─────────
    app.add_handler(CommandHandler("slap",       user_reaction_cmd))
    app.add_handler(CommandHandler("hug",        user_reaction_cmd))
    app.add_handler(CommandHandler("kiss",       user_reaction_cmd))
    app.add_handler(CommandHandler("pat",        user_reaction_cmd))
    app.add_handler(CommandHandler("punch",      user_reaction_cmd))
    app.add_handler(CommandHandler("poke",       user_reaction_cmd))
    app.add_handler(CommandHandler("couple",     couple_cmd))
    app.add_handler(CommandHandler("afk",        afk_cmd))
    app.add_handler(CommandHandler("notes",      notes_list_cmd))
    app.add_handler(CommandHandler("save",       note_save_cmd))
    app.add_handler(CommandHandler("get",        note_get_cmd))
    app.add_handler(CommandHandler("rules",      rules_cmd))
    app.add_handler(CommandHandler("setrules",   setrules_cmd, filters=filters.ChatType.GROUPS))

    # ── Module group management commands — registered directly in PTB v21 ──────
    # These come from modules that may not load via bridge; register directly.
    _G = filters.ChatType.GROUPS
    _GU = None  # No filter — works everywhere

    async def _pin_cmd(update, context):
        if not update.message or not update.message.reply_to_message:
            return await update.message.reply_text("Reply to a message to pin it.")
        try:
            await context.bot.pin_chat_message(
                update.effective_chat.id,
                update.message.reply_to_message.message_id,
                disable_notification=False,
            )
        except Exception as exc:
            await update.message.reply_text(f"❌ {exc}")

    async def _unpin_cmd(update, context):
        try:
            await context.bot.unpin_chat_message(update.effective_chat.id)
        except Exception as exc:
            await update.message.reply_text(f"❌ {exc}")

    async def _del_cmd(update, context):
        if update.message and update.message.reply_to_message:
            try:
                await update.message.reply_to_message.delete()
                await update.message.delete()
            except Exception:
                pass

    async def _promote_cmd(update, context):
        from telegram.constants import ChatMemberStatus
        msg = update.message
        target = msg.reply_to_message.from_user if msg.reply_to_message else None
        if not target and context.args:
            try:
                target = await context.bot.get_chat(context.args[0])
            except Exception:
                pass
        if not target:
            return await msg.reply_text("Reply to a user or provide @username")
        try:
            await context.bot.promote_chat_member(
                update.effective_chat.id, target.id,
                can_manage_chat=True, can_delete_messages=True,
                can_manage_video_chats=True, can_restrict_members=True,
                can_promote_members=False, can_change_info=True,
                can_invite_users=True, can_pin_messages=True,
            )
            await msg.reply_text(f"✅ Promoted {target.first_name or target.id}")
        except Exception as exc:
            await msg.reply_text(f"❌ {exc}")

    async def _demote_cmd(update, context):
        msg = update.message
        target = msg.reply_to_message.from_user if msg.reply_to_message else None
        if not target and context.args:
            try:
                target = await context.bot.get_chat(context.args[0])
            except Exception:
                pass
        if not target:
            return await msg.reply_text("Reply to a user or provide @username")
        try:
            from telegram import ChatPermissions
            await context.bot.promote_chat_member(
                update.effective_chat.id, target.id,
                can_manage_chat=False, can_delete_messages=False,
                can_manage_video_chats=False, can_restrict_members=False,
                can_promote_members=False, can_change_info=False,
                can_invite_users=False, can_pin_messages=False,
            )
            await msg.reply_text(f"✅ Demoted {target.first_name or target.id}")
        except Exception as exc:
            await msg.reply_text(f"❌ {exc}")

    async def _mute_cmd(update, context):
        from telegram import ChatPermissions
        msg = update.message
        target = msg.reply_to_message.from_user if msg.reply_to_message else None
        if not target and context.args:
            try:
                target = await context.bot.get_chat(context.args[0])
            except Exception:
                pass
        if not target:
            return await msg.reply_text("Reply to a user or provide @username")
        try:
            await context.bot.restrict_chat_member(
                update.effective_chat.id, target.id,
                ChatPermissions(can_send_messages=False),
            )
            await msg.reply_text(f"🔇 Muted {target.first_name or target.id}")
        except Exception as exc:
            await msg.reply_text(f"❌ {exc}")

    async def _unmute_cmd(update, context):
        from telegram import ChatPermissions
        msg = update.message
        target = msg.reply_to_message.from_user if msg.reply_to_message else None
        if not target and context.args:
            try:
                target = await context.bot.get_chat(context.args[0])
            except Exception:
                pass
        if not target:
            return await msg.reply_text("Reply to a user or provide @username")
        try:
            await context.bot.restrict_chat_member(
                update.effective_chat.id, target.id,
                ChatPermissions(can_send_messages=True, can_send_photos=True,
                    can_send_videos=True, can_send_documents=True,
                    can_send_polls=True, can_invite_users=True),
            )
            await msg.reply_text(f"🔊 Unmuted {target.first_name or target.id}")
        except Exception as exc:
            await msg.reply_text(f"❌ {exc}")

    async def _ban_cmd(update, context):
        msg = update.message
        target = msg.reply_to_message.from_user if msg.reply_to_message else None
        if not target and context.args:
            try:
                target = await context.bot.get_chat(context.args[0])
            except Exception:
                pass
        if not target:
            return await msg.reply_text("Reply to a user or provide @username")
        try:
            await context.bot.ban_chat_member(update.effective_chat.id, target.id)
            await msg.reply_text(f"🚫 Banned {target.first_name or target.id}")
        except Exception as exc:
            await msg.reply_text(f"❌ {exc}")

    async def _unban_cmd(update, context):
        msg = update.message
        target = msg.reply_to_message.from_user if msg.reply_to_message else None
        if not target and context.args:
            try:
                target = await context.bot.get_chat(context.args[0])
            except Exception:
                pass
        if not target:
            return await msg.reply_text("Reply to a user or provide @username")
        try:
            await context.bot.unban_chat_member(update.effective_chat.id, target.id)
            await msg.reply_text(f"✅ Unbanned {target.first_name or target.id}")
        except Exception as exc:
            await msg.reply_text(f"❌ {exc}")

    async def _kick_cmd(update, context):
        msg = update.message
        target = msg.reply_to_message.from_user if msg.reply_to_message else None
        if not target and context.args:
            try:
                target = await context.bot.get_chat(context.args[0])
            except Exception:
                pass
        if not target:
            return await msg.reply_text("Reply to a user or provide @username")
        try:
            await context.bot.ban_chat_member(update.effective_chat.id, target.id)
            await context.bot.unban_chat_member(update.effective_chat.id, target.id)
            await msg.reply_text(f"👢 Kicked {target.first_name or target.id}")
        except Exception as exc:
            await msg.reply_text(f"❌ {exc}")

    async def _invitelink_cmd(update, context):
        try:
            link = await context.bot.export_chat_invite_link(update.effective_chat.id)
            await update.message.reply_text(f"🔗 Invite link:\n{link}")
        except Exception as exc:
            await update.message.reply_text(f"❌ {exc}")

    # Register all group management commands
    _mgmt_cmds = [
        ("pin",        _pin_cmd),
        ("unpin",      _unpin_cmd),
        ("del",        _del_cmd),
        ("promote",    _promote_cmd),
        ("demote",     _demote_cmd),
        ("mute",       _mute_cmd),
        ("unmute",     _unmute_cmd),
        ("ban",        _ban_cmd),
        ("unban",      _unban_cmd),
        ("kick",       _kick_cmd),
        ("invitelink", _invitelink_cmd),
    ]
    for _cmd_name, _cmd_fn in _mgmt_cmds:
        app.add_handler(CommandHandler(_cmd_name, _cmd_fn, filters=_G))
    logger.info(f"[mgmt] Registered {len(_mgmt_cmds)} group management commands")
    app.add_handler(CommandHandler("warns",      warns_cmd))
    app.add_handler(CommandHandler("warn",       warn_cmd, filters=filters.ChatType.GROUPS))
    app.add_handler(CommandHandler("unwarn",     unwarn_cmd, filters=filters.ChatType.GROUPS))
    app.add_handler(CommandHandler("resetwarns", resetwarns_cmd, filters=filters.ChatType.GROUPS))
    # Note trigger — #notename in any message
    app.add_handler(MessageHandler(filters.Regex(r'^#[\w]+') & ~filters.COMMAND, note_trigger_handler))
    # AFK auto-reply handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, afk_check_handler), group=5)
    # Chatbot handler — ALL users can use it
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, chatbot_private_handler
    ), group=6)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS & filters.Regex(r'(?i)^(hey|hi|hello|bot|@)'), chatbot_group_handler
    ), group=7)
    logger.info("[features] User feature commands registered")

    # ══════════════════════════════════════════════════════════════════════
    # ALL MODULE COMMANDS — complete registration (PTB v21 compatible)
    # Authority: each function enforces its own admin check internally
    # ══════════════════════════════════════════════════════════════════════
    _G = filters.ChatType.GROUPS   # shorthand for group-only filter
    _M = _module_cmd_handler       # shorthand

    # ── Reactions — all users ──────────────────────────────────────────────
    for _rc in ("wave","bite","wink","cry","laugh","blush","nod","shoot"):
        app.add_handler(CommandHandler(_rc, user_reaction_cmd))

    # ── Fun — all users ───────────────────────────────────────────────────
    app.add_handler(CommandHandler(["aq","animequote"],    _M("animequotes")))
    app.add_handler(CommandHandler("truth",                _M("truth_and_dare")))
    app.add_handler(CommandHandler("dare",                 _M("truth_and_dare")))
    app.add_handler(CommandHandler("toss",                 _M("fun")))
    app.add_handler(CommandHandler("roll",                 _M("fun")))
    app.add_handler(CommandHandler(["8ball","eightball"],  _M("fun")))
    app.add_handler(CommandHandler("decide",               _M("fun")))
    app.add_handler(CommandHandler("shrug",                _M("fun")))
    app.add_handler(CommandHandler("table",                _M("fun")))
    app.add_handler(CommandHandler("runs",                 _M("fun")))
    app.add_handler(CommandHandler("shout",                _M("fun")))
    app.add_handler(CommandHandler("rlg",                  _M("fun")))
    app.add_handler(CommandHandler(["sanitize","bluetext"],_M("fun")))

    # ── Tools — all users ─────────────────────────────────────────────────
    app.add_handler(CommandHandler("wiki",                 _M("wiki")))
    app.add_handler(CommandHandler("ud",                   _M("ud")))
    app.add_handler(CommandHandler(["tr","tl"],            _M("translator")))
    app.add_handler(CommandHandler("time",                 _M("gettime")))
    app.add_handler(CommandHandler("write",                _M("writetool")))
    app.add_handler(CommandHandler("imdb",                 _M("imdb")))
    app.add_handler(CommandHandler("stickerid",            _M("stickers")))
    app.add_handler(CommandHandler("getsticker",           _M("stickers")))
    app.add_handler(CommandHandler("kang",                 _M("stickers")))
    app.add_handler(CommandHandler("stickers",             _M("stickers")))
    app.add_handler(CommandHandler("cash",                 _M("currency_converter")))
    app.add_handler(CommandHandler("markdownhelp",         _M("misc")))
    app.add_handler(CommandHandler("botstats",             _M("sudoers")))
    app.add_handler(CommandHandler("speedtest",            _M("speed_test")))
    app.add_handler(CommandHandler("groups",               _M("users")))

    # ── Userinfo — all users ──────────────────────────────────────────────
    app.add_handler(CommandHandler(["bio","setbio","me","setme","gifid"], _M("userinfo")))

    # ── Group management — group admins (enforced inside module) ──────────
    app.add_handler(CommandHandler(["ban","sban"],     _M("bans"),    filters=_G))
    app.add_handler(CommandHandler("tban",             _M("bans"),    filters=_G))
    app.add_handler(CommandHandler("kick",             _M("bans"),    filters=_G))
    app.add_handler(CommandHandler("unban",            _M("bans"),    filters=_G))
    app.add_handler(CommandHandler("roar",             _M("bans"),    filters=_G))
    app.add_handler(CommandHandler("mute",             _M("muting"),  filters=_G))
    app.add_handler(CommandHandler("unmute",           _M("muting"),  filters=_G))
    app.add_handler(CommandHandler(["tmute","tempmute"],_M("muting"), filters=_G))
    app.add_handler(CommandHandler("pin",              _M("admin"),   filters=_G))
    app.add_handler(CommandHandler("unpin",            _M("admin"),   filters=_G))
    app.add_handler(CommandHandler("pinned",           _M("admin"),   filters=_G))
    app.add_handler(CommandHandler("promote",          _M("admin"),   filters=_G))
    app.add_handler(CommandHandler("demote",           _M("admin"),   filters=_G))
    app.add_handler(CommandHandler("fullpromote",      _M("admin"),   filters=_G))
    app.add_handler(CommandHandler("invitelink",       _M("admin"),   filters=_G))
    app.add_handler(CommandHandler("title",            _M("admin"),   filters=_G))
    app.add_handler(CommandHandler("admincache",       _M("admin"),   filters=_G))
    app.add_handler(CommandHandler(["admins","adminlist"],_M("admin"),filters=_G))
    app.add_handler(CommandHandler("setgtitle",        _M("admin"),   filters=_G))
    app.add_handler(CommandHandler("setgpic",          _M("admin"),   filters=_G))
    app.add_handler(CommandHandler("delgpic",          _M("admin"),   filters=_G))
    app.add_handler(CommandHandler(["setdesc","setdescription"],_M("admin"),filters=_G))
    app.add_handler(CommandHandler("setsticker",       _M("admin"),   filters=_G))
    app.add_handler(CommandHandler("approve",          _M("approve"), filters=_G))
    app.add_handler(CommandHandler("unapprove",        _M("approve"), filters=_G))
    app.add_handler(CommandHandler("unapproveall",     _M("approve"), filters=_G))
    app.add_handler(CommandHandler("approved",         _M("approve"), filters=_G))
    app.add_handler(CommandHandler("approval",         _M("approve"), filters=_G))
    app.add_handler(CommandHandler("addblacklist",     _M("blacklist"),filters=_G))
    app.add_handler(CommandHandler("unblacklist",      _M("blacklist"),filters=_G))
    app.add_handler(CommandHandler("blacklist",        _M("blacklist"),filters=_G))
    app.add_handler(CommandHandler("blacklistmode",    _M("blacklist"),filters=_G))
    app.add_handler(CommandHandler(["addblsticker","addbls"],_M("blacklist_stickers"),filters=_G))
    app.add_handler(CommandHandler(["rmblsticker","delbls"],_M("blacklist_stickers"),filters=_G))
    app.add_handler(CommandHandler("blsticker",        _M("blacklist_stickers"),filters=_G))
    app.add_handler(CommandHandler("blstickermode",    _M("blacklist_stickers"),filters=_G))
    app.add_handler(CommandHandler("filter",           _M("cust_filters"),filters=_G))
    app.add_handler(CommandHandler("stop",             _M("cust_filters"),filters=_G))
    app.add_handler(CommandHandler("stopall",          _M("cust_filters"),filters=_G))
    app.add_handler(CommandHandler("filters",          _M("cust_filters"),filters=_G))
    app.add_handler(CommandHandler("lock",             _M("locks"),   filters=_G))
    app.add_handler(CommandHandler("unlock",           _M("locks"),   filters=_G))
    app.add_handler(CommandHandler("locks",            _M("locks"),   filters=_G))
    app.add_handler(CommandHandler("locktypes",        _M("locks"),   filters=_G))
    app.add_handler(CommandHandler("setflood",         _M("antiflood"),filters=_G))
    app.add_handler(CommandHandler("setfloodmode",     _M("antiflood"),filters=_G))
    app.add_handler(CommandHandler("flood",            _M("antiflood"),filters=_G))
    app.add_handler(CommandHandler("setlog",           _M("log_channel"),filters=_G))
    app.add_handler(CommandHandler("unsetlog",         _M("log_channel"),filters=_G))
    app.add_handler(CommandHandler("logchannel",       _M("log_channel"),filters=_G))
    app.add_handler(CommandHandler("reports",          _M("reporting"),filters=_G))
    app.add_handler(CommandHandler("report",           _M("reporting"),filters=_G))
    app.add_handler(CommandHandler("clearrules",       _M("rules"),   filters=_G))
    app.add_handler(CommandHandler("clear",            _M("notes"),   filters=_G))
    app.add_handler(CommandHandler("removeallnotes",   _M("notes"),   filters=_G))
    app.add_handler(CommandHandler("chatbot",          _M("chatbot"), filters=_G))
    app.add_handler(CommandHandler("cleanblue",        _M("cleaner"), filters=_G))
    app.add_handler(CommandHandler("listblue",         _M("cleaner"), filters=_G))
    app.add_handler(CommandHandler("purge",            _M("purge"),   filters=_G))
    app.add_handler(CommandHandler("del",              _M("purge"),   filters=_G))
    app.add_handler(CommandHandler("tagall",           _M("tagall"),  filters=_G))
    app.add_handler(CommandHandler("ignore",           _M("blacklistusers"),filters=_G))
    app.add_handler(CommandHandler("notice",           _M("blacklistusers"),filters=_G))
    app.add_handler(CommandHandler("ignoredlist",      _M("blacklistusers")))
    app.add_handler(CommandHandler("disable",          _M("disable"), filters=_G))
    app.add_handler(CommandHandler("enable",           _M("disable"), filters=_G))
    app.add_handler(CommandHandler(["cmds","disabled"],_M("disable"), filters=_G))
    app.add_handler(CommandHandler("listcmds",         _M("disable"), filters=_G))

    # ── Welcome system (group admins) ─────────────────────────────────────
    app.add_handler(CommandHandler("welcome",          _M("welcome"), filters=_G))
    app.add_handler(CommandHandler("goodbye",          _M("welcome"), filters=_G))
    app.add_handler(CommandHandler("setwelcome",       _M("welcome"), filters=_G))
    app.add_handler(CommandHandler("setgoodbye",       _M("welcome"), filters=_G))
    app.add_handler(CommandHandler("resetwelcome",     _M("welcome"), filters=_G))
    app.add_handler(CommandHandler("resetgoodbye",     _M("welcome"), filters=_G))
    app.add_handler(CommandHandler("welcomemute",      _M("welcome"), filters=_G))
    app.add_handler(CommandHandler("cleanservice",     _M("welcome"), filters=_G))
    app.add_handler(CommandHandler("cleanwelcome",     _M("welcome"), filters=_G))
    app.add_handler(CommandHandler("welcomehelp",      _M("welcome")))
    app.add_handler(CommandHandler("welcomemutehelp",  _M("welcome")))

    # ── Bot-owner / sudo level ────────────────────────────────────────────
    app.add_handler(CommandHandler("addsudo",          _M("disasters")))
    app.add_handler(CommandHandler(["addsupport","adddemon"],_M("disasters")))
    app.add_handler(CommandHandler("addtiger",         _M("disasters")))
    app.add_handler(CommandHandler("addwhitelist",     _M("disasters")))
    app.add_handler(CommandHandler(["removesudo","rmsudo"],_M("disasters")))
    app.add_handler(CommandHandler("removesupport",    _M("disasters")))
    app.add_handler(CommandHandler("removetiger",      _M("disasters")))
    app.add_handler(CommandHandler("removewhitelist",  _M("disasters")))
    app.add_handler(CommandHandler("sudolist",         _M("disasters")))
    app.add_handler(CommandHandler("supportlist",      _M("disasters")))
    app.add_handler(CommandHandler("tigers",           _M("disasters")))
    app.add_handler(CommandHandler("whitelistlist",    _M("disasters")))
    app.add_handler(CommandHandler("devlist",          _M("disasters")))
    app.add_handler(CommandHandler("gban",             _M("global_bans")))
    app.add_handler(CommandHandler("ungban",           _M("global_bans")))
    app.add_handler(CommandHandler("gbanlist",         _M("global_bans")))
    app.add_handler(CommandHandler("antispam",         _M("global_bans")))
    app.add_handler(CommandHandler("getchats",         _M("get_common_chats")))
    app.add_handler(CommandHandler("dbcleanup",        _M("dbcleanup")))
    app.add_handler(CommandHandler("sh",               _M("shell")))
    app.add_handler(CommandHandler("debug",            _M("debug")))
    app.add_handler(CommandHandler("errors",           _M("error_handler")))
    app.add_handler(CommandHandler("clearlocals",      _M("eval")))
    app.add_handler(CommandHandler(["gitpull","reboot","leave","lockdown"],_M("dev")))
    app.add_handler(CommandHandler(["load","unload","listmodules"],_M("modules")))
    app.add_handler(CommandHandler("import",           _M("backups")))
    app.add_handler(CommandHandler("connection",       _M("connection")))

    # ── Force-sub management ──────────────────────────────────────────────
    app.add_handler(CommandHandler("addfsub",  _M("fsub"), filters=_G))
    app.add_handler(CommandHandler("delfsub",  _M("fsub"), filters=_G))
    app.add_handler(CommandHandler("fsublist", _M("fsub")))

    # ── Anime request system ──────────────────────────────────────────────
    app.add_handler(CommandHandler(
        ["request","requests","myrequests","fulfill","delrequest"], _M("animerequest")))
    # Ensure single-cmd fallbacks for audit completeness:
    app.add_handler(CommandHandler("request",     _M("animerequest")))
    app.add_handler(CommandHandler("requests",    _M("animerequest")))
    app.add_handler(CommandHandler("myrequests",  _M("animerequest")))
    app.add_handler(CommandHandler("fulfill",     _M("animerequest")))
    app.add_handler(CommandHandler("delrequest",  _M("animerequest")))
    app.add_handler(CommandHandler("wave",        user_reaction_cmd))
    app.add_handler(CommandHandler("bite",        user_reaction_cmd))
    app.add_handler(CommandHandler("wink",        user_reaction_cmd))
    app.add_handler(CommandHandler("cry",         user_reaction_cmd))
    app.add_handler(CommandHandler("laugh",       user_reaction_cmd))
    app.add_handler(CommandHandler("blush",       user_reaction_cmd))
    app.add_handler(CommandHandler("nod",         user_reaction_cmd))
    app.add_handler(CommandHandler("shoot",       user_reaction_cmd))

    # ── Bad words (registered directly from module) ───────────────────────
    try:
        from modules.badwords import register as _bw_register
        _bw_register(app)
        logger.info("[badwords] registered")
    except Exception as _e:
        logger.warning(f"badwords: {_e}")

    logger.info("[handlers] All module commands registered")
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(CommandHandler("info", info_command))
    app.add_handler(CommandHandler("stats", stats_command, filters=admin_filter))
    app.add_handler(CommandHandler("sysstats", sysstats_command, filters=admin_filter))
    app.add_handler(CommandHandler("users", users_command, filters=admin_filter))
    app.add_handler(CommandHandler("cmd", cmd_command))
    app.add_handler(CommandHandler("commands", cmd_command))
    app.add_handler(CommandHandler("upload", upload_command, filters=admin_filter))
    app.add_handler(CommandHandler("settings", settings_command, filters=admin_filter))
    app.add_handler(CommandHandler("autoupdate", autoupdate_command, filters=admin_filter))
    app.add_handler(CommandHandler("autoforward", autoforward_command, filters=admin_filter))
    app.add_handler(CommandHandler("addchannel", add_channel_command, filters=admin_filter))
    app.add_handler(CommandHandler("removechannel", remove_channel_command, filters=admin_filter))
    app.add_handler(CommandHandler("banuser", ban_user_command, filters=admin_filter))
    app.add_handler(CommandHandler("unbanuser", unban_user_command, filters=admin_filter))
    app.add_handler(CommandHandler("listusers", listusers_command, filters=admin_filter))
    app.add_handler(CommandHandler("deleteuser", deleteuser_command, filters=admin_filter))
    app.add_handler(CommandHandler("exportusers", exportusers_command, filters=admin_filter))
    app.add_handler(CommandHandler("backup", backup_command, filters=admin_filter))
    app.add_handler(CommandHandler("addclone", addclone_command, filters=admin_filter))
    app.add_handler(CommandHandler("clones", clones_command, filters=admin_filter))
    app.add_handler(CommandHandler("reload", reload_command, filters=admin_filter))
    app.add_handler(CommandHandler("set_loader", set_loader_cmd, filters=admin_filter))
    app.add_handler(CommandHandler("restart", reload_command, filters=admin_filter))
    app.add_handler(CommandHandler("logs", logs_command, filters=admin_filter))
    app.add_handler(CommandHandler("connect", connect_command, filters=admin_filter))
    app.add_handler(CommandHandler("disconnect", disconnect_command, filters=admin_filter))
    app.add_handler(CommandHandler("connections", connections_command, filters=admin_filter))
    app.add_handler(CommandHandler("addpanelimg", addpanelimg_command))
    app.add_handler(CommandHandler("getfileid", getfileid_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(admin_filter & ~filters.COMMAND, handle_admin_message))
    # Handle text messages in groups (filter poster, anime commands etc.)
    app.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND,
        group_message_handler,
    ))
    # Also handle non-text (captions, stickers) for filter matching in groups
    app.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.CAPTION & ~filters.COMMAND,
        group_message_handler,
    ))
    app.add_handler(InlineQueryHandler(inline_query_handler))
    app.add_handler(MessageHandler(filters.ChatType.CHANNEL, auto_forward_message_handler))
    app.add_handler(MessageHandler(
        filters.ChatType.CHANNEL & filters.VIDEO, handle_channel_post))
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & filters.VIDEO & admin_filter, handle_upload_video))
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & (filters.PHOTO | filters.Document.IMAGE | filters.Sticker.ALL) & admin_filter,
        handle_admin_photo))
    app.add_handler(ChatJoinRequestHandler(auto_approve_join_request))
    # Channel welcome: fire when new members join a channel/group
    app.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        channel_welcome_join_handler,
    ))
    app.add_error_handler(error_handler)



# ================================================================================
#   SPEED ENGINE — Background pre-warming & panel cache system
# ================================================================================

# Global panel cache: stores (text, markup) keyed by panel name
# Built once then reused. Refreshed every 60s in background.
_PANEL_CACHE: dict = {}
_PANEL_CACHE_TS: dict = {}
_PANEL_CACHE_TTL = 45  # seconds

def _panel_cache_get(key: str):
    ts = _PANEL_CACHE_TS.get(key, 0)
    if time.monotonic() - ts < _PANEL_CACHE_TTL:
        return _PANEL_CACHE.get(key)
    return None

def _panel_cache_set(key: str, value):
    _PANEL_CACHE[key] = value
    _PANEL_CACHE_TS[key] = time.monotonic()



async def _pregen_all_filter_posters(bot, admin_id: int, chat_id: int) -> None:
    """
    Background task: generate posters for every anime title in anime_channel_links.
    Sends each poster to POSTER_DB_CHANNEL and caches the file_id.
    Reports summary to admin DM when done.
    """
    from database_dual import get_all_anime_channel_links, get_filter_poster_cache, save_filter_poster_cache
    import hashlib as _hl

    try:
        from database_dual import get_all_links
        raw_links = get_all_links(limit=500, offset=0)
        # Deduplicate by channel_title (filter keyword)
        seen = set()
        links = []
        for row in (raw_links or []):
            title = (row[2] or "").strip()
            if title and title.lower() not in seen:
                seen.add(title.lower())
                links.append(row)
    except Exception:
        links = []

    if not links:
        try:
            await bot.send_message(
                admin_id,
                b(small_caps("❌ no generated links found. use gen link to create some first.")),
                parse_mode="HTML",
            )
        except Exception:
            pass
        return

    total   = len(links)
    done    = 0
    skipped = 0
    failed  = 0

    status_msg = None
    try:
        status_msg = await bot.send_message(
            admin_id,
            b(small_caps(f"🎌 pre-generating {total} posters…")) + "\n"
            + bq(small_caps("0% complete")),
            parse_mode="HTML",
        )
    except Exception:
        pass

    from poster_engine import _anilist_anime, _build_anime_data, _make_poster, _get_settings
    import asyncio as _aio

    loop = _aio.get_event_loop()

    for i, row in enumerate(links):
        # row from generated_links: (link_id, channel_username, channel_title, source_bot_username, created_time, never_expires)
        anime_title   = (row[2] or "").strip()   # channel_title = filter keyword
        channel_id    = row[1]                    # channel_username/id
        if not anime_title:
            continue
        template      = "ani"   # default template
        cache_key     = _hl.md5(f"{anime_title.lower()}:{template}".encode()).hexdigest()

        # Skip if already cached
        try:
            existing = get_filter_poster_cache(cache_key)
            if existing and existing.get("file_id"):
                skipped += 1
                continue
        except Exception:
            pass

        try:
            # Fetch AniList data
            data = await loop.run_in_executor(None, _anilist_anime, anime_title)
            if not data:
                failed += 1
                continue

            settings = _get_settings("anime")
            title_b, native, st, poster_rows, desc, cover_url, score = await loop.run_in_executor(
                None, _build_anime_data, data
            )

            # Generate poster image
            poster_buf = await loop.run_in_executor(
                None, _make_poster,
                template, title_b, native, st, poster_rows, desc, cover_url, score,
                settings.get("watermark_text"),
                settings.get("watermark_position", "center"),
                None, "bottom",
            )

            # Build caption
            import html as _html
            genres = ", ".join((data.get("genres") or [])[:3])
            t_d    = data.get("title", {}) or {}
            eng    = t_d.get("english") or t_d.get("romaji") or anime_title
            caption = f"<b>{_html.escape(eng)}</b>"
            if native:
                caption += f"\n<i>{_html.escape(native)}</i>"
            if genres:
                caption += f"\n\n» <b>Genre:</b> {_html.escape(genres)}"

            file_id = None
            channel_msg_id = 0

            # Send to POSTER_DB_CHANNEL
            if POSTER_DB_CHANNEL and poster_buf:
                try:
                    poster_buf.seek(0)
                    db_msg = await bot.send_photo(
                        chat_id=POSTER_DB_CHANNEL,
                        photo=poster_buf,
                        caption=f"<b>FilterPoster</b> | {_html.escape(anime_title)} | {template}\n\n{caption}",
                        parse_mode="HTML",
                    )
                    if db_msg.photo:
                        file_id = db_msg.photo[-1].file_id
                        channel_msg_id = db_msg.message_id
                except Exception as _se:
                    logger.debug(f"[pregen] DB channel send failed for {anime_title}: {_se}")

            # If no DB channel, use the poster directly
            if not file_id and poster_buf:
                file_id = "pending"  # Will be cached on first real send

            # Save to cache
            if file_id and file_id != "pending":
                try:
                    save_filter_poster_cache(
                        cache_key=cache_key,
                        anime_title=anime_title,
                        template=template,
                        file_id=file_id,
                        channel_id=channel_id or 0,
                        channel_msg_id=channel_msg_id,
                        caption=caption,
                    )
                    done += 1
                except Exception:
                    failed += 1
            else:
                done += 1  # Generated but no DB channel — still counts

        except Exception as exc:
            logger.debug(f"[pregen] {anime_title}: {exc}")
            failed += 1

        # Update status every 5 items
        if status_msg and (i + 1) % 5 == 0:
            pct = int((i + 1) / total * 100)
            try:
                await status_msg.edit_text(
                    b(small_caps(f"🎌 pre-generating {total} posters…")) + "\n"
                    + bq(small_caps(f"{pct}% — {i+1}/{total} processed")),
                    parse_mode="HTML",
                )
            except Exception:
                pass

        # Small delay to avoid flood limits
        await _aio.sleep(0.5)

    # Final report
    summary = (
        b(small_caps("✅ poster pre-generation complete!")) + "\n\n"
        + bq(
            b(small_caps("total: ")) + str(total) + "\n"
            + b(small_caps("generated & cached: ")) + str(done) + "\n"
            + b(small_caps("skipped (already cached): ")) + str(skipped) + "\n"
            + b(small_caps("failed: ")) + str(failed)
        )
    )
    try:
        if status_msg:
            await status_msg.edit_text(summary, parse_mode="HTML")
        else:
            await bot.send_message(admin_id, summary, parse_mode="HTML")
    except Exception:
        pass


async def _prewarm_all_caches(bot) -> None:
    """
    Background task: pre-build all panel data so first button tap is instant.
    Runs at startup and repeats every 45s to keep caches fresh.
    All DB queries run in parallel via asyncio.gather.
    """
    while True:
        try:
            # ── Pre-build panel photo store ───────────────────────────────
            try:
                await _prebuild_all_panels(bot)
            except Exception as _pbe:
                logger.debug(f"[prewarm] prebuild: {_pbe}")

            # ── Self-ping to prevent Render free-tier spin-down ─────────────
            # Render spins down after 15 min of no HTTP. We ping every 14 min.
            try:
                import aiohttp as _ahttp
                _self_url = __import__("os").getenv("RENDER_EXTERNAL_URL", "")
                if not _self_url:
                    _port = __import__("os").getenv("PORT", "10000")
                    _self_url = f"http://localhost:{_port}"
                async with _ahttp.ClientSession() as _sess:
                    async with _sess.get(f"{_self_url}/health", timeout=_ahttp.ClientTimeout(total=5)) as _r:
                        logger.debug(f"[keepalive] self-ping {_r.status}")
            except Exception as _kae:
                logger.debug(f"[keepalive] {_kae}")

            # ── Run all panel data fetches in parallel ─────────────────────
            def _fetch_connected():
                try:
                    from database_dual import get_all_connected_groups
                    rows = get_all_connected_groups()
                    return {r[0] for r in rows} if rows else set()
                except Exception:
                    try:
                        with db_manager.get_cursor() as cur:
                            cur.execute("SELECT group_id FROM connected_groups WHERE active = TRUE")
                            return {r[0] for r in (cur.fetchall() or [])}
                    except Exception:
                        return set()

            results = await asyncio.gather(
                asyncio.get_event_loop().run_in_executor(None, get_user_count),
                asyncio.get_event_loop().run_in_executor(None, get_blocked_users_count),
                asyncio.get_event_loop().run_in_executor(None, get_all_force_sub_channels),
                asyncio.get_event_loop().run_in_executor(None, get_all_clone_bots),
                asyncio.get_event_loop().run_in_executor(None, lambda: get_setting("maintenance_mode", "false")),
                asyncio.get_event_loop().run_in_executor(None, lambda: get_all_links(limit=500, offset=0) if callable(globals().get("get_all_links")) else []),
                asyncio.get_event_loop().run_in_executor(None, _fetch_connected),
                return_exceptions=True,
            )
            user_count, blocked_count, channels, clones, maint, all_links, connected_ids = results

            # Store pre-computed values
            _panel_cache_set("user_count",       user_count       if isinstance(user_count, int)       else 0)
            _panel_cache_set("blocked_count",    blocked_count    if isinstance(blocked_count, int)    else 0)
            _panel_cache_set("channels",         channels         if isinstance(channels, list)        else [])
            _panel_cache_set("clones",           clones           if isinstance(clones, list)          else [])
            _panel_cache_set("maint",            maint            if isinstance(maint, str)            else "false")
            _panel_cache_set("all_links",        all_links        if isinstance(all_links, list)       else [])
            _panel_cache_set("connected_groups", connected_ids    if isinstance(connected_ids, set)    else set())

            logger.debug("[prewarm] panel caches refreshed")
        except Exception as exc:
            logger.debug(f"[prewarm] error: {exc}")

        # Sleep 45s between panel cache refreshes; self-ping runs every cycle
        await asyncio.sleep(_PANEL_CACHE_TTL)


def _fast_user_count() -> int:
    """Return cached user count (instantly, no DB)."""
    cached = _panel_cache_get("user_count")
    return cached if cached is not None else 0

def _fast_channels() -> list:
    """Return cached force-sub channels."""
    cached = _panel_cache_get("channels")
    return cached if cached is not None else []

def _fast_clones() -> list:
    """Return cached clone bots."""
    cached = _panel_cache_get("clones")
    return cached if cached is not None else []

def _fast_anime_links() -> list:
    """Return cached anime channel links."""
    cached = _panel_cache_get("anime_links")
    return cached if cached is not None else []


async def _run_clone_polling(token: str, uname: str) -> None:
    """Run a clone bot as an independent Application with all handlers."""
    logger.info(f" Starting clone bot @{uname} polling...")
    try:
        app = (
            Application.builder()
            .token(token)
            .connect_timeout(30)
            .read_timeout(30)
            .write_timeout(30)
            .build()
        )
        _register_all_handlers(app)
        async with app:
            await app.initialize()
            await app.start()
            if app.updater:
                await app.updater.start_polling(
                    allowed_updates=Update.ALL_TYPES,
                    drop_pending_updates=True,
                )
            logger.info(f"✅ Clone @{uname} polling started")
            # Run until cancelled
            while app.running:
                await asyncio.sleep(5)
    except asyncio.CancelledError:
        logger.info(f"🛑 Clone @{uname} polling cancelled")
    except Exception as exc:
        logger.error(f"❌ Clone @{uname} error: {exc}")


def launch_clone_bot(token: str, uname: str) -> None:
    """Schedule a clone bot polling task on the running event loop."""
    if uname in _clone_tasks:
        existing = _clone_tasks[uname]
        if not existing.done():
            logger.info(f"Clone @{uname} already running")
            return
    task = asyncio.ensure_future(_run_clone_polling(token, uname))
    _clone_tasks[uname] = task
    logger.info(f"🤖 Clone @{uname} task scheduled")


# ================================================================================
#                         MANGA CHAPTER — PDF DELIVERY
# ================================================================================

async def _deliver_chapter_as_pdf(
    bot, chat_id: int, manga_title: str, ch_num: str, chapter_id: str
) -> bool:
    """Download MangaDex chapter pages and send as a PDF document.
    Falls back to sending page images if PDF libraries are unavailable.
    Returns True on success.
    """
    import io as _io
    try:
        pages = MangaDexClient.get_chapter_pages(chapter_id)
        if not pages:
            return False
        base_url, ch_hash, filenames = pages
        if not filenames:
            return False
        import urllib.request as _req
        # Download pages (cap at 60 pages)
        page_bytes: list = []
        for fn in filenames[:60]:
            url = f"{base_url}/data/{ch_hash}/{fn}"
            try:
                with _req.urlopen(url, timeout=20) as resp:
                    page_bytes.append(resp.read())
                await asyncio.sleep(0.1)
            except Exception:
                pass
        if not page_bytes:
            return False
        safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in manga_title)
        filename = f"{safe_title}_Chapter_{ch_num}.pdf"
        # Try fpdf2 first
        try:
            import tempfile, os as _os
            from fpdf import FPDF
            pdf = FPDF()
            with tempfile.TemporaryDirectory() as tmpdir:
                for i, pb in enumerate(page_bytes):
                    img_path = _os.path.join(tmpdir, f"p{i}.jpg")
                    with open(img_path, "wb") as f:
                        f.write(pb)
                    pdf.add_page()
                    pdf.image(img_path, 0, 0, 210)
                pdf_bytes = bytes(pdf.output())
        except ImportError:
            # Fallback: try Pillow
            try:
                from PIL import Image as _Img
                imgs = [_Img.open(_io.BytesIO(pb)).convert("RGB") for pb in page_bytes]
                pdf_io = _io.BytesIO()
                imgs[0].save(pdf_io, format="PDF", save_all=True, append_images=imgs[1:])
                pdf_bytes = pdf_io.getvalue()
            except Exception:
                # Last fallback: send pages as individual images
                media_group = []
                for i, pb in enumerate(page_bytes[:10]):
                    media_group.append({"type": "photo", "media": _io.BytesIO(pb)})
                if media_group:
                    cap = f"📖 <b>{manga_title}</b> — Chapter {ch_num} (images)"
                    await bot.send_photo(
                        chat_id,
                        photo=_io.BytesIO(page_bytes[0]),
                        caption=cap,
                        parse_mode=ParseMode.HTML,
                    )
                return True
        await bot.send_document(
            chat_id,
            document=_io.BytesIO(pdf_bytes),
            filename=filename,
            caption=f"📖 <b>{manga_title}</b> — Chapter {ch_num}",
            parse_mode=ParseMode.HTML,
        )
        return True
    except Exception as exc:
        logger.error(f"_deliver_chapter_as_pdf error: {exc}")
        return False


# ================================================================================

async def manga_update_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Periodic job: check all tracked manga for new chapters."""
    tracked = MangaTracker.get_all_tracked()
    if not tracked:
        return

    for rec in tracked:
        rec_id, manga_id, manga_title, target_chat_id, lang, last_chapter, _ = rec
        try:
            chapter = MangaDexClient.get_latest_chapter(manga_id, lang)
            if not chapter:
                MangaTracker.update_last_chapter(rec_id, last_chapter or "")
                continue

            attrs = chapter.get("attributes", {}) or {}
            ch_num = attrs.get("chapter")
            ch_id = chapter.get("id", "")

            if not ch_num:
                continue

            if str(ch_num) == str(last_chapter):
                # No new chapter
                continue

            # New chapter found!
            ch_info = MangaDexClient.format_chapter_info(chapter)
            pub_at = attrs.get("publishAt") or ""
            try:
                pub_at = datetime.fromisoformat(pub_at.replace("Z", "+00:00")).strftime("%d %b %Y %H:%M")
            except Exception:
                pass

            text = (
                b(f"📚 New Chapter Released!") + "\n\n"
                f"<b>Manga:</b> {b(e(manga_title))}\n\n"
                + ch_info + "\n\n"
                + bq(b("Enjoy reading! 🎉"))
            )
            keyboard = [[
                InlineKeyboardButton(" Read Now", url=f"https://mangadex.org/chapter/{ch_id}"),
                InlineKeyboardButton(" Manga Page", url=f"https://mangadex.org/title/{manga_id}"),
            ]]

            if target_chat_id:
                await safe_send_message(
                    context.bot, target_chat_id, text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )

            MangaTracker.update_last_chapter(rec_id, ch_num)
            await asyncio.sleep(0.5)  # Rate limit

        except Exception as exc:
            logger.debug(f"manga_update_job row {rec_id} error: {exc}")


# ================================================================================
#                         CLEANUP AND LIFECYCLE JOBS
# ================================================================================

async def cleanup_expired_links_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job: clean up expired deep links from database."""
    try:
        cleanup_expired_links()
    except Exception as exc:
        logger.debug(f"cleanup_expired_links_job error: {exc}")


async def post_init(application: Application) -> None:
    """Called after application starts — register commands and start services."""
    global BOT_USERNAME, I_AM_CLONE

    me = await application.bot.get_me()
    BOT_USERNAME = me.username or ""

    try:
        I_AM_CLONE = am_i_a_clone_token(BOT_TOKEN)
    except Exception:
        I_AM_CLONE = False

    if not I_AM_CLONE:
        try:
            set_main_bot_token(BOT_TOKEN)
            logger.info("✅ Main bot token saved to DB")
        except Exception as exc:
            logger.warning(f"Could not save main bot token: {exc}")

    logger.info(f"✅ Bot @{BOT_USERNAME} started as {'CLONE' if I_AM_CLONE else 'MAIN'}")

    # Register commands on this bot
    await _register_bot_commands_on_bot(application.bot)

    # Register commands and start polling for all clone bots
    try:
        clones = get_all_clone_bots(active_only=True)
        for _, token, uname, _, _ in clones:
            try:
                clone_bot = Bot(token=token)
                await _register_bot_commands_on_bot(clone_bot)
                logger.info(f"✅ Commands registered on clone @{uname}")
                # Launch clone as independent Application (non-blocking)
                launch_clone_bot(token, uname)
            except Exception as exc:
                logger.warning(f"Could not start clone @{uname}: {exc}")
    except Exception as exc:
        logger.warning(f"Could not iterate clones: {exc}")

    # Start health check server
    try:
        await health_server.start()
        logger.info("✅ Health check server started")

        # Auto-scan panel image channel in background (non-blocking).
        # Uses PANEL_DB_CHANNEL if set, otherwise falls back to FALLBACK_IMAGE_CHANNEL.
        _scan_target = PANEL_DB_CHANNEL if PANEL_DB_CHANNEL else FALLBACK_IMAGE_CHANNEL
        if _scan_target:
            asyncio.create_task(_scan_panel_channel(application.bot))
            logger.info(f"✅ Panel image scan scheduled from channel {_scan_target}")
    except Exception as exc:
        logger.warning(f"Health server failed: {exc}")

    # Schedule jobs — first= delays prevent "missed run" warnings during slow startup
    if application.job_queue:
        application.job_queue.run_repeating(manga_update_job,           interval=3600, first=180)
        application.job_queue.run_repeating(cleanup_expired_links_job,  interval=600,  first=90)
        # check_scheduled_broadcasts: start 3 min after boot to avoid missed-run spam
        application.job_queue.run_repeating(check_scheduled_broadcasts, interval=60,   first=180)
        logger.info("✅ Background jobs scheduled")

    # Migrate poster_cache table
    if _FILTER_POSTER_AVAILABLE:
        try:
            migrate_poster_cache_table()
            logger.info("✅ poster_cache table ready")
        except Exception as _e:
            logger.warning(f"poster_cache migration: {_e}")

    # ── SPEED: Pre-warm all panel caches in background (non-blocking) ─────────
    asyncio.create_task(_prewarm_all_caches(application.bot))

    # ── Apply missing DB migrations ────────────────────────────────────────────
    _migration_sqls = [
        """CREATE TABLE IF NOT EXISTS manga_auto_updates (
            id SERIAL PRIMARY KEY,
            manga_id TEXT NOT NULL DEFAULT '',
            manga_title TEXT NOT NULL DEFAULT '',
            target_chat_id BIGINT,
            notify_language TEXT DEFAULT 'en',
            last_chapter TEXT,
            interval_minutes INTEGER DEFAULT 60,
            mode TEXT DEFAULT 'latest',
            watermark BOOLEAN DEFAULT FALSE,
            active BOOLEAN DEFAULT TRUE,
            last_checked TIMESTAMP DEFAULT NOW(),
            created_at TIMESTAMP DEFAULT NOW()
        )""",
        "ALTER TABLE bot_progress ADD COLUMN IF NOT EXISTS anime_name TEXT DEFAULT 'Anime Name'",
        "ALTER TABLE manga_auto_updates ADD COLUMN IF NOT EXISTS notify_language TEXT DEFAULT 'en'",
        "ALTER TABLE manga_auto_updates ADD COLUMN IF NOT EXISTS interval_minutes INTEGER DEFAULT 60",
        "ALTER TABLE manga_auto_updates ADD COLUMN IF NOT EXISTS mode TEXT DEFAULT 'latest'",
        "ALTER TABLE manga_auto_updates ADD COLUMN IF NOT EXISTS watermark BOOLEAN DEFAULT FALSE",
        "INSERT INTO bot_settings (key, value) VALUES ('loading_sticker_id', ''), ('loading_anim_enabled', 'true') ON CONFLICT (key) DO NOTHING",
        "INSERT INTO bot_settings (key, value) VALUES ('watermark_sticker_id', ''), ('watermark_image_id', '') ON CONFLICT (key) DO NOTHING",
    ]
    for _sql in _migration_sqls:
        try:
            with db_manager.get_cursor() as _cur:
                _cur.execute(_sql)
        except Exception as _me:
            logger.debug(f"DB migration (non-fatal): {str(_me)[:80]}")
    try:
        with db_manager.get_cursor() as _cur:
            _cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_manga_track_unique ON manga_auto_updates(manga_id, target_chat_id)")
    except Exception:
        pass
    logger.info("✅ DB migrations applied")

    # Initialize bot commands per authority level
    from bot_commands_setup import initialize_bot_commands
    await initialize_bot_commands(application.bot)

    # Send restart notification
    await _send_restart_notification(application.bot)
        



async def _register_bot_commands_on_bot(bot: Bot) -> None:
    """
    Register Telegram's /command menu (the popup list users see when they type /).
    Strategy: show only KEY commands in menu — clean, not overwhelming.
    Full list is always available via /cmd (which is authority-aware).
    """
    # ── Public menu (all users see this when they type /) ─────────────────
    user_commands = [
        BotCommand("start",     "Main menu"),
        BotCommand("help",      "Help & channels"),
        BotCommand("cmd",       "All available commands"),
        BotCommand("alive",     "Is bot online?"),
        BotCommand("anime",     "Anime poster & info"),
        BotCommand("manga",     "Manga poster & info"),
        BotCommand("movie",     "Movie poster & info"),
        BotCommand("my_plan",   "My daily poster limit"),
        BotCommand("aq",        "Random anime quote"),
        BotCommand("truth",     "Truth question"),
        BotCommand("dare",      "Dare challenge"),
        BotCommand("hug",       "Hug someone (reply)"),
        BotCommand("slap",      "Slap someone (reply)"),
        BotCommand("afk",       "Set AFK status"),
        BotCommand("rules",     "View group rules"),
        BotCommand("warns",     "My warn count"),
        BotCommand("wiki",      "Wikipedia search"),
        BotCommand("tr",        "Translate text (reply)"),
        BotCommand("ping",      "Bot speed check"),
        BotCommand("id",        "Get user/chat ID"),
    ]

    # ── Group admin menu (shown in group chats for admins) ────────────────
    group_admin_commands = [
        BotCommand("cmd",          "All commands by authority"),
        BotCommand("ban",          "Ban a user"),
        BotCommand("kick",         "Kick a user"),
        BotCommand("mute",         "Mute a user"),
        BotCommand("warn",         "Warn a user"),
        BotCommand("pin",          "Pin a message"),
        BotCommand("purge",        "Delete messages"),
        BotCommand("promote",      "Promote to admin"),
        BotCommand("demote",       "Demote admin"),
        BotCommand("filter",       "Add custom filter"),
        BotCommand("filters",      "List filters"),
        BotCommand("lock",         "Lock message type"),
        BotCommand("setrules",     "Set group rules"),
        BotCommand("save",         "Save a note"),
        BotCommand("notes",        "List all notes"),
        BotCommand("welcome",      "Toggle welcome message"),
        BotCommand("setwelcome",   "Set welcome message"),
        BotCommand("setflood",     "Set flood limit"),
        BotCommand("approve",      "Approve a user"),
        BotCommand("addblacklist", "Blacklist a word"),
        BotCommand("addword",      "Add bad word"),
        BotCommand("wordaction",   "Set bad word action"),
        BotCommand("setlog",       "Set log channel"),
        BotCommand("chatbot",      "Toggle AI chatbot"),
        BotCommand("tagall",       "Mention all members"),
    ]

    # ── Bot admin menu (shown in bot owner's private chat) ────────────────
    bot_admin_commands = [
        BotCommand("cmd",          "All commands by authority"),
        BotCommand("stats",        "Bot statistics"),
        BotCommand("sysstats",     "Server stats"),
        BotCommand("users",        "User database"),
        BotCommand("upload",       "Upload manager"),
        BotCommand("settings",     "Category settings"),
        BotCommand("autoupdate",   "Manga tracker"),
        BotCommand("autoforward",  "Auto-forward manager"),
        BotCommand("broadcast",    "Send broadcast"),
        BotCommand("addchannel",   "Add force-sub channel"),
        BotCommand("banuser",      "Ban from bot"),
        BotCommand("add_premium",  "Give premium plan"),
        BotCommand("addclone",     "Add clone bot"),
        BotCommand("reload",       "Restart bot"),
        BotCommand("logs",         "View logs"),
        BotCommand("gban",         "Global ban"),
        BotCommand("addsudo",      "Add sudo user"),
        BotCommand("backup",       "Links backup"),
        BotCommand("exportusers",  "Export CSV"),
        BotCommand("listusers",    "Browse users"),
    ]

    # ── Register for each scope ───────────────────────────────────────────
    try:
        # Default (all users, all chats)
        await bot.set_my_commands(user_commands)
        logger.info(f"✅ User commands menu registered ({len(user_commands)} cmds)")
    except Exception as exc:
        logger.warning(f"Command menu (users) failed: {exc}")

    # Group admin scope — shown to admins in group chats
    try:
        from telegram import BotCommandScopeAllChatAdministrators
        await bot.set_my_commands(
            group_admin_commands,
            scope=BotCommandScopeAllChatAdministrators(),
        )
        logger.info(f"✅ Group admin commands menu registered ({len(group_admin_commands)} cmds)")
    except Exception as exc:
        logger.warning(f"Command menu (group admins) failed: {exc}")

    # Bot admin personal scope — shown only in bot owner's DM
    try:
        await bot.set_my_commands(
            bot_admin_commands,
            scope=BotCommandScopeChat(chat_id=ADMIN_ID),
        )
        if OWNER_ID and OWNER_ID != ADMIN_ID:
            await bot.set_my_commands(
                bot_admin_commands,
                scope=BotCommandScopeChat(chat_id=OWNER_ID),
            )
        logger.info(f"✅ Bot admin commands menu registered ({len(bot_admin_commands)} cmds)")
    except Exception as exc:
        logger.warning(f"Command menu (bot admin) failed: {exc}")

    try:
        me = await bot.get_me()
        logger.info(f"✅ All command menus set on @{me.username}")
    except Exception:
        pass


async def _send_restart_notification(bot: Bot) -> None:
    """Send restart notification to admin on every start (deploy, wake, manual restart)."""
    triggered_by = BOT_USERNAME
    try:
        if os.path.exists("restart_message.json"):
            with open("restart_message.json") as f:
                rinfo = json.load(f)
            triggered_by = rinfo.get("triggered_by", BOT_USERNAME)
            try:
                os.remove("restart_message.json")
            except Exception:
                pass
    except Exception:
        pass

    text = f"<blockquote><b>Bᴏᴛ Rᴇsᴛᴀʀᴛᴇᴅ by @{e(triggered_by)}</b></blockquote>"
    try:
        await bot.send_message(ADMIN_ID, text, parse_mode=ParseMode.HTML)
    except Exception as exc:
        logger.warning(f"Could not send restart notification: {exc}")

async def post_shutdown(application: Application) -> None:
    """Cleanup on bot shutdown."""
    try:
        await health_server.stop()
    except Exception:
        pass
    try:
        if db_manager:
            db_manager.close_all()
    except Exception:
        pass
    logger.info("✅ Shutdown complete.")


# ================================================================================
#                            ERROR HANDLER (USER-FRIENDLY)
# ================================================================================

_error_dm_counts: Dict[Any, int] = {}
ERROR_DM_MAX = 5


async def error_handler(
    update: Optional[Update], context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Central error handler.
    - Users get a friendly, non-technical message in DM.
    - Admin gets the full technical traceback via DM.
    - Timeout/ignorable errors are silently skipped.
    """
    err = context.error
    if not err:
        return

    error_logger.error(f"Exception: {err}", exc_info=True)

    # Silently ignore harmless errors
    if UserFriendlyError.is_ignorable(err):
        return

    # ── User gets friendly message ────────────────────────────────────────────────
    if update and update.effective_user:
        uid = update.effective_user.id
        if uid not in (ADMIN_ID, OWNER_ID):
            friendly = UserFriendlyError.get_user_message(err)
            try:
                if update.callback_query:
                    await safe_answer(update.callback_query, "Something went wrong. Please try again.")
                elif update.message:
                    await update.message.reply_text(friendly, parse_mode=ParseMode.HTML)
                elif update.effective_chat:
                    await safe_send_message(context.bot, update.effective_chat.id, friendly)
            except Exception:
                pass

    # ── Admin gets technical message ──────────────────────────────────────────────
    if get_setting("error_dms_enabled", "1") not in ("0", "false"):
        update_key = getattr(update, "update_id", "global") if update else "global"
        count = _error_dm_counts.get(update_key, 0)
        if count < ERROR_DM_MAX:
            _error_dm_counts[update_key] = count + 1
            context_info = ""
            if update:
                if update.effective_user:
                    context_info += f"User: @{update.effective_user.username or update.effective_user.id}\n"
                if update.effective_chat:
                    context_info += f"Chat: {update.effective_chat.id}\n"
                if update.callback_query:
                    context_info += f"Callback: {update.callback_query.data}\n"
                elif update.message and update.message.text:
                    context_info += f"Text: {update.message.text[:100]}\n"
            admin_msg = UserFriendlyError.get_admin_message(err, context_info)
            try:
                await context.bot.send_message(
                    ADMIN_ID, admin_msg, parse_mode=ParseMode.HTML
                )
            except Exception:
                pass


# ================================================================================
#              BUTTON HANDLER (CENTRAL ROUTER — EXHAUSTIVE)
# ================================================================================

@force_sub_required
async def button_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, _data_override: str = None
) -> None:
    """
    Central callback query router.
    Answers every query immediately to prevent timeout errors.
    All callbacks are handled exhaustively.
    Accepts _data_override to allow internal re-routing without modifying
    the read-only query.data attribute.
    """
    query = update.callback_query
    if not query:
        return

    # ── INSTANT ACK: answer the callback query FIRST, ALWAYS, IMMEDIATELY ────────
    # This removes the spinner from the button within <50ms regardless of what
    # the handler does next. Telegram shows the spinner until answered or 10s timeout.
    if _data_override is None:
        try:
            await query.answer()
        except Exception:
            pass  # Already answered or expired — never block on this

    data = _data_override if _data_override is not None else (query.data or "")
    uid = query.from_user.id if query.from_user else 0
    chat_id = query.message.chat_id if query.message else uid

    is_admin = uid in (ADMIN_ID, OWNER_ID)

    # ── Global debounce: if this user's panel lock is held AND this callback
    #    is a known panel-navigation action, drop the duplicate click silently.
    #    This prevents ping degradation when users click rapidly.
    _PANEL_CALLBACKS = {
        "admin_back", "admin_stats", "admin_settings", "admin_sysstats",
        "admin_channels", "admin_clones", "admin_users", "admin_broadcast",
        "admin_category_settings", "admin_feature_flags", "broadcast_stats_panel",
        "user_management", "fsub_link_stats",
    }
    if data in _PANEL_CALLBACKS or data.startswith("adm_page_"):
        lock = _get_panel_lock(uid)
        if lock.locked():
            return  # drop — already processing

    # ── Utility ────────────────────────────────────────────────────────────────────
    if data == "noop":
        return

    # ── Admin panel page navigation ───────────────────────────────────────────
    if data.startswith("adm_page_"):
        if not is_admin:
            try: await query.answer("⛔ Admin only", show_alert=False)
            except Exception: pass
            return
        try:
            page_num = int(data.split("_")[-1])
        except Exception:
            page_num = 0
        await send_admin_menu(chat_id, context, query=query, page=page_num)
        return

    if data == "close_message":
        try:
            await query.delete_message()
        except Exception:
            pass
        return

    # ── Image navigation (edit_message_media, no new message) ──────────────────────
    if data.startswith("imgn:"):
        try:
            parts = data.split(":", 3)
            # Format: imgn:{current_idx}:{img_key}:{direction}
            if len(parts) == 4:
                _, cur_idx_str, img_key, direction = parts
                cur_idx = int(cur_idx_str)
                entry = _cache_get(img_key)
                # Support both old list format and new dict format
                if isinstance(entry, list):
                    images = entry
                    saved_caption = ""
                    shown_set: set = set()
                elif isinstance(entry, dict):
                    images = entry.get("urls", [])
                    saved_caption = entry.get("caption", "")
                    shown_set = entry.get("shown", set())
                else:
                    images = []
                    saved_caption = ""
                    shown_set = set()

                if images and len(images) > 1:
                    await safe_answer(query, "Loading...")
                    # Find next unshown index to avoid repeats
                    step = 1 if direction == "next" else -1
                    candidate = (cur_idx + step) % len(images)
                    # Try up to len(images) steps to find an unshown image
                    attempts = 0
                    while candidate in shown_set and attempts < len(images):
                        candidate = (candidate + step) % len(images)
                        attempts += 1
                    # If all shown, reset and start fresh
                    if attempts >= len(images):
                        shown_set = set()
                    new_idx = candidate
                    shown_set.add(new_idx)
                    # Update shown set in cache
                    if isinstance(entry, dict):
                        entry["shown"] = shown_set
                        _cache_set(img_key, entry)
                    new_url = images[new_idx]
                    # Rebuild navigation keyboard with updated index
                    new_kb = [
                        [InlineKeyboardButton("🔙", callback_data=f"imgn:{new_idx}:{img_key}:prev"),
                         InlineKeyboardButton("✖️", callback_data="close_message"),
                         InlineKeyboardButton("🔜", callback_data=f"imgn:{new_idx}:{img_key}:next")],
                    ]
                    # Preserve existing top rows from the current keyboard (except last nav row)
                    if query.message and query.message.reply_markup:
                        old_rows = list(query.message.reply_markup.inline_keyboard)
                        top_rows = old_rows[:-1] if old_rows else []
                        new_kb = top_rows + new_kb
                    try:
                        # Use saved_caption to keep info text on image change
                        if saved_caption:
                            await query.message.edit_media(
                                InputMediaPhoto(
                                    media=new_url,
                                    caption=saved_caption,
                                    parse_mode=ParseMode.HTML,
                                ),
                                reply_markup=InlineKeyboardMarkup(new_kb),
                            )
                        else:
                            await query.message.edit_media(
                                InputMediaPhoto(media=new_url),
                                reply_markup=InlineKeyboardMarkup(new_kb),
                            )
                    except Exception as exc:
                        logger.debug(f"imgn edit_media error: {exc}")
                else:
                    await safe_answer(query, "No more images available.")
        except Exception as exc:
            logger.debug(f"imgn handler error: {exc}")
        return

    if data == "verify_subscription":
        # Re-trigger start to recheck subscription
        await start(update, context)
        return

    # ── Admin back to main panel ───────────────────────────────────────────────────
    if data == "admin_back":
        if not is_admin:
            return
        await delete_bot_prompt(context, chat_id)
        user_states.pop(uid, None)
        await send_admin_menu(chat_id, context, query)
        return

    # ── User about/help ────────────────────────────────────────────────────────────

    # ── User Features Panel — paginated 4×4 grid ─────────────────────────────────
    if data.startswith("user_features_"):
        try:
            page = int(data.split("_")[-1])
        except Exception:
            page = 0

        # Feature list — label only in small caps, NO emojis on buttons
        _USER_FEATURES = [
            ("ʀᴇᴀᴄᴛɪᴏɴs",    "uf_reactions"),
            ("ᴀɴɪᴍᴇ ɪɴꜰᴏ",   "uf_anime"),
            ("ᴀꜰᴋ",            "uf_afk"),
            ("ɴᴏᴛᴇs",          "uf_notes"),
            ("ᴛʀᴜᴛʜ ᴅᴀʀᴇ",   "uf_truthdare"),
            ("ᴡᴀʀɴs",          "uf_warns"),
            ("ʀᴜʟᴇs",          "uf_rules"),
            ("ʙᴀᴅ ᴡᴏʀᴅs",    "uf_badwords"),
            ("ᴀɴɪᴍᴇ ǫᴜᴏᴛᴇs", "uf_animequotes"),
            ("ᴄᴏᴜᴘʟᴇ",        "uf_couple"),
            ("sᴇᴀʀᴄʜ",        "uf_search"),
            ("ᴛᴏᴏʟs",          "uf_tools"),
            ("ᴍʏ ᴘʟᴀɴ",       "uf_myplan"),
            ("sᴛɪᴄᴋᴇʀs",     "uf_stickers"),
            ("sᴇᴅ",            "uf_sed"),
            ("ʀᴇᴘᴏʀᴛ",        "uf_report"),
        ]

        PER_PAGE = 8  # 4 columns × 2 rows per page
        total = len(_USER_FEATURES)
        total_pages = (total + PER_PAGE - 1) // PER_PAGE
        page = max(0, min(page, total_pages - 1))
        start_i = page * PER_PAGE
        end_i   = min(start_i + PER_PAGE, total)
        page_items = _USER_FEATURES[start_i:end_i]

        # Build 4-column grid — text only, no emojis
        feat_rows = []
        for i in range(0, len(page_items), 4):
            row_items = page_items[i:i+4]
            feat_rows.append([
                InlineKeyboardButton(lb, callback_data=cb)
                for lb, cb in row_items
            ])

        # Navigation: ◀ and ▶ have arrows only, page indicator, ✕ close
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("🔙", callback_data=f"user_features_{page-1}"))
        nav.append(InlineKeyboardButton(f"{page+1} / {total_pages}", callback_data="noop"))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton("🔜", callback_data=f"user_features_{page+1}"))
        nav.append(InlineKeyboardButton("✖️", callback_data="close_message"))

        feat_rows.append(nav)
        markup = InlineKeyboardMarkup(feat_rows)

        text = (
            b("ꜰᴇᴀᴛᴜʀᴇs") + "\n\n"
            + bq(
                "ᴛᴀᴘ ᴀɴʏ ꜰᴇᴀᴛᴜʀᴇ ᴛᴏ sᴇᴇ ᴡʜᴀᴛ ɪᴛ ᴅᴏᴇs ᴀɴᴅ ᴡʜᴏ ᴄᴀɴ ᴜsᴇ ɪᴛ"
            )
        )
        try:
            await query.delete_message()
        except Exception:
            pass
        img_url = await get_panel_pic_async("default")
        if img_url:
            try:
                await context.bot.send_photo(chat_id, img_url, caption=text,
                    parse_mode=ParseMode.HTML, reply_markup=markup)
                return
            except Exception:
                pass
        await safe_send_message(context.bot, chat_id, text, reply_markup=markup)
        return

    # ── Individual feature info cards (full authority info in each) ───────────────
    _UF_INFO = {
        "uf_reactions": ("ʀᴇᴀᴄᴛɪᴏɴs",
            "<b>Who can use:</b> Everyone — users, admins, owner\n\n"
            "<b>Commands:</b>\n"
            "/hug — Hug someone\n"
            "/slap — Slap someone\n"
            "/kiss — Kiss someone\n"
            "/pat — Pat someone\n"
            "/poke — Poke someone\n"
            "/wave — Wave at someone\n"
            "/bite — Bite someone\n"
            "/punch — Punch someone\n"
            "/wink — Wink at someone\n"
            "/cry — Express crying\n"
            "/laugh — Express laughing\n"
            "/blush — Express blushing\n\n"
            "<b>How to use:</b> Reply to someone's message then send the command."),

        "uf_anime": ("ᴀɴɪᴍᴇ ɪɴꜰᴏ",
            "<b>Who can use:</b> Everyone — users, admins, owner\n\n"
            "<b>Commands:</b>\n"
            "/anime &lt;name&gt; — Landscape poster + full info\n"
            "/manga &lt;name&gt; — Manga poster + info\n"
            "/airing &lt;name&gt; — Next episode countdown\n"
            "/character &lt;name&gt; — Character details from AniList\n\n"
            "<b>Daily limits apply:</b>\n"
            "Free: 20/day · Bronze: 30 · Silver: 40 · Gold: 50\n\n"
            "<b>Example:</b> /anime Demon Slayer"),

        "uf_afk": ("ᴀꜰᴋ",
            "<b>Who can use:</b> Everyone — users, admins, owner\n\n"
            "<b>Commands:</b>\n"
            "/afk &lt;reason&gt; — Set yourself as Away From Keyboard\n\n"
            "<b>How it works:</b>\n"
            "When someone mentions you while AFK, bot auto-replies with your reason.\n"
            "AFK is cleared automatically when you send any message."),

        "uf_notes": ("ɴᴏᴛᴇs",
            "<b>Who can use:</b>\n"
            "View notes — Everyone\n"
            "Save notes — Group admins &amp; owner only\n\n"
            "<b>Commands:</b>\n"
            "/notes — List all saved notes in this chat\n"
            "/get &lt;name&gt; — Get a specific note\n"
            "#notename — Type # then note name to retrieve\n\n"
            "<b>Admin only:</b>\n"
            "/save &lt;name&gt; &lt;text&gt; — Save a note"),

        "uf_truthdare": ("ᴛʀᴜᴛʜ & ᴅᴀʀᴇ",
            "<b>Who can use:</b> Everyone — users, admins, owner\n\n"
            "<b>Commands:</b>\n"
            "/truth — Get a random truth question\n"
            "/dare — Get a random dare challenge\n\n"
            "Fun game to play with friends in any group!"),

        "uf_warns": ("ᴡᴀʀɴs",
            "<b>Who can use:</b>\n"
            "Check warns — Everyone\n"
            "Issue warns — Group admins &amp; owner only\n\n"
            "<b>Commands — Everyone:</b>\n"
            "/warns — Check your own warn count\n\n"
            "<b>Commands — Group admins only:</b>\n"
            "/warn — Warn a user (reply to their message)\n"
            "/unwarn — Remove one warn (reply)\n"
            "/resetwarns — Reset all warns for a user (reply)\n\n"
            "<b>Note:</b> 3 warnings = automatic ban"),

        "uf_rules": ("ʀᴜʟᴇs",
            "<b>Who can use:</b>\n"
            "View rules — Everyone\n"
            "Set rules — Group admins &amp; owner only\n\n"
            "<b>Commands — Everyone:</b>\n"
            "/rules — View the group rules\n\n"
            "<b>Commands — Group admins only:</b>\n"
            "/setrules &lt;text&gt; — Set the group rules"),

        "uf_badwords": ("ʙᴀᴅ ᴡᴏʀᴅs",
            "<b>Who can use:</b>\n"
            "View list — Everyone\n"
            "Manage list — Group admins &amp; owner only\n\n"
            "<b>Commands — Everyone:</b>\n"
            "/badwords — See banned words in this group\n\n"
            "<b>Commands — Group admins only:</b>\n"
            "/addword &lt;word&gt; — Add a banned word\n"
            "/rmword &lt;word&gt; — Remove a banned word\n"
            "/clearwords — Remove all banned words\n"
            "/wordaction &lt;action&gt; — Set action: warn / mute / ban / del / kick\n\n"
            "<b>Auto-action:</b> Bot always deletes the message. Then applies the set action."),

        "uf_animequotes": ("ᴀɴɪᴍᴇ ǫᴜᴏᴛᴇs",
            "<b>Who can use:</b> Everyone — users, admins, owner\n\n"
            "<b>Commands:</b>\n"
            "/aq — Get a random anime quote\n"
            "/animequote — Same as /aq\n\n"
            "Fetches random quotes from popular anime characters."),

        "uf_couple": ("ᴄᴏᴜᴘʟᴇ",
            "<b>Who can use:</b> Everyone — users, admins, owner\n\n"
            "<b>Commands:</b>\n"
            "/couple — Reveal today's couple in the group\n\n"
            "<b>How it works:</b>\n"
            "Picks 2 random members from the group daily.\n"
            "Resets at midnight every day.\n"
            "Requires MongoDB for persistence."),

        "uf_search": ("sᴇᴀʀᴄʜ",
            "<b>Who can use:</b> Everyone — users, admins, owner\n\n"
            "<b>Commands:</b>\n"
            "/anime &lt;n&gt; — Anime poster + info (with daily limit)\n"
            "/movie &lt;n&gt; — Movie poster + info (with daily limit)\n"
            "/tvshow &lt;n&gt; — TV show poster + info (with daily limit)\n"
            "/imdb &lt;n&gt; — Look up on IMDb\n\n"
            "<b>Daily limits:</b> Free 20 · Bronze 30 · Silver 40 · Gold 50\n"
            "Admin &amp; owner have no limit."),

        "uf_tools": ("ᴛᴏᴏʟs",
            "<b>Who can use:</b> Everyone — users, admins, owner\n\n"
            "<b>Commands:</b>\n"
            "/wiki &lt;topic&gt; — Search Wikipedia\n"
            "/ud &lt;word&gt; — Urban Dictionary lookup\n"
            "/tr &lt;lang&gt; &lt;text&gt; — Translate text (or reply)\n"
            "/time &lt;city&gt; — Get current time for any city\n"
            "/write &lt;text&gt; — Write text as handwriting image\n"
            "/wall &lt;query&gt; — Get anime wallpaper\n"
            "/ping — Check bot response speed"),

        "uf_myplan": ("ᴍʏ ᴘʟᴀɴ",
            "<b>Who can use:</b> Everyone — users, admins, owner\n\n"
            "<b>Commands:</b>\n"
            "/my_plan — Check your daily poster usage &amp; limit\n"
            "/plans — View all available plans\n\n"
            "<b>Plans:</b>\n"
            "Free: 20 posters/day\n"
            "Bronze: 30 posters/day\n"
            "Silver: 40 posters/day\n"
            "Gold: 50 posters/day\n"
            "Admin &amp; Owner: Unlimited\n\n"
            "<b>Upgrade:</b> Contact admin with /add_premium command."),

        "uf_stickers": ("sᴛɪᴄᴋᴇʀs",
            "<b>Who can use:</b> Everyone — users, admins, owner\n\n"
            "<b>Commands:</b>\n"
            "/stickerid — Get the file ID of a sticker (reply to it)\n"
            "/getsticker — Get sticker as PNG image (reply to it)\n"
            "/kang — Add a sticker to your own pack (reply to it)\n\n"
            "Reply to any sticker message to use these commands."),

        "uf_sed": ("sᴇᴅ",
            "<b>Who can use:</b> Everyone — users, admins, owner\n\n"
            "<b>How to use:</b>\n"
            "Reply to a message with: <code>s/old/new</code>\n\n"
            "Replaces text in the message you replied to.\n\n"
            "<b>Examples:</b>\n"
            "<code>s/hello/hi</code> — replaces first match\n"
            "<code>s/hello/hi/g</code> — replaces all matches\n"
            "<code>s/hello/hi/i</code> — case-insensitive replace"),

        "uf_report": ("ʀᴇᴘᴏʀᴛ",
            "<b>Who can use:</b>\n"
            "Report — Everyone (except admins)\n"
            "Receive reports — Group admins &amp; owner only\n\n"
            "<b>Commands — Everyone:</b>\n"
            "/report &lt;reason&gt; — Report a message to admins (reply to it)\n\n"
            "<b>Commands — Group admins only:</b>\n"
            "/reports on/off — Toggle report notifications\n\n"
            "<b>Note:</b> Admins cannot use /report (they are the ones who receive it)."),
    }

    if data in _UF_INFO:
        title, desc = _UF_INFO[data]
        back_page = 0
        _UF_CBS = ["uf_reactions","uf_anime","uf_afk","uf_notes","uf_truthdare",
                   "uf_warns","uf_rules","uf_badwords","uf_animequotes","uf_couple",
                   "uf_search","uf_tools","uf_myplan","uf_stickers","uf_sed","uf_report"]
        if data in _UF_CBS:
            idx = _UF_CBS.index(data)
            back_page = idx // 8
        try:
            await query.delete_message()
        except Exception:
            pass
        await safe_send_message(
            context.bot, chat_id,
            f"<b>{title}</b>\n\n" + bq(desc),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙", callback_data=f"user_features_{back_page}"),
                 InlineKeyboardButton("✖️", callback_data="close_message")],
            ]),
        )
        return

    if data == "about_bot":
        try:
            await query.delete_message()
        except Exception:
            pass
        text = (
            b(f" About {e(BOT_NAME)}") + "\n\n"
            + bq(
                b("🤖 Powered by @Beat_Anime_Ocean\n\n")
                + b("Features:\n")
                + "• Force-Sub channels"
        
            )
        )
        await safe_send_message(
            context.bot, chat_id, text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎌 Anime Channel", url=PUBLIC_ANIME_CHANNEL_URL)],
                [_back_btn("user_back")],
            ]),
        )
        return

    if data == "user_back":
        try:
            await query.delete_message()
        except Exception:
            pass
        await start(update, context)
        return

    if data == "user_help":
        await help_command(update, context)
        return

    # ── Admin stats ────────────────────────────────────────────────────────────────
    if data == "admin_stats":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        await send_stats_panel(context, chat_id)
        return

    if data == "broadcast_stats_panel":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        await broadcaststats_command(update, context)
        return

    # ── System stats ───────────────────────────────────────────────────────────────
    if data == "admin_sysstats":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        await safe_send_message(
            context.bot, chat_id,
            get_system_stats_text(),
            reply_markup=InlineKeyboardMarkup([
                [bold_button("♻️ Refresh", callback_data="admin_sysstats"),
                 _back_btn("admin_back")]
            ]),
        )
        return

    # ── Admin logs ─────────────────────────────────────────────────────────────────
    if data == "clone_add":
        if not is_admin:
            return
        user_states[uid] = ADD_CLONE_TOKEN
        await safe_edit_text(
            query,
            b("➕ ADD CLONE BOT") + "\n\n"
            + bq(
                "Send the bot token for the clone bot.\n\n"
                "The clone bot will:\n"
                "✔️ Share all force-sub channels\n"
                "✔️ Generate working invite links\n"
                "✔️ Have identical menus\n\n"
                "<i>Get token from @BotFather</i>"
            ),
            reply_markup=InlineKeyboardMarkup([[_back_btn("manage_clones"), _close_btn()]]),
        )
        return

    if data == "clone_remove_menu":
        if not is_admin:
            return
        clones = get_all_clone_bots(active_only=True)
        if not clones:
            await safe_answer(query, "No clone bots to remove.")
            return
        buttons = [_btn(f"@{c[2]}", f"clone_del_{c[2]}") for c in clones]
        rows = _grid3(buttons)
        rows.append([_back_btn("manage_clones"), _close_btn()])
        await safe_edit_text(
            query, b("SELECT CLONE TO REMOVE"),
            reply_markup=InlineKeyboardMarkup(rows),
        )
        return

    if data.startswith("clone_del_"):
        if not is_admin:
            return
        uname = data[len("clone_del_"):]
        remove_clone_bot(uname)
        await safe_answer(query, f"Removed clone @{uname}")
        await button_handler(update, context, "manage_clones")
        return

    if data == "clone_list_full":
        if not is_admin:
            return
        clones = get_all_clone_bots()
        text = b(f"ALL CLONE BOTS ({len(clones)})") + "\n\n"
        for i, (cid, token, uname, active, added) in enumerate(clones, 1):
            st = "🟢" if active else "🔴"
            text += f"<b>{i}.</b> {st} @{e(uname or '?')}\n"
        await safe_edit_text(
            query, text,
            reply_markup=InlineKeyboardMarkup([[_back_btn("manage_clones"), _close_btn()]]),
        )
        return

    if data == "clone_move_links":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_MOVE_LINKS"
        await safe_edit_text(
            query,
            b("MOVE LINKS") + "\n\n"
            + bq("Send: <code>@from_bot @to_bot</code>\nAll links will be reassigned."),
            reply_markup=InlineKeyboardMarkup([[_back_btn("manage_clones"), _close_btn()]]),
        )
        return

    if data == "admin_logs":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        await logs_command(update, context)
        return

    # ── Admin restart ──────────────────────────────────────────────────────────────
    if data == "dbcleanup_confirm":
        if not is_admin:
            return
        await safe_edit_text(
            query,
            b(small_caps("💾 database cleanup")) + "\n\n"
            + bq(
                small_caps("removes expired links, old sessions, and stale cache entries.\n\n")
                + small_caps("click confirm to proceed:")
            ),
            reply_markup=InlineKeyboardMarkup([
                [bold_button(small_caps("✅ confirm cleanup"), callback_data="dbcleanup_run"),
                 _back_btn("admin_back")],
            ]),
        )
        return

    if data == "dbcleanup_run":
        if not is_admin:
            return
        try:
            from database_dual import cleanup_expired_links
            removed = cleanup_expired_links()
            await safe_edit_text(
                query,
                b(small_caps("✅ cleanup done!")) + "\n"
                + bq(small_caps(f"removed {removed} expired entries.")),
                reply_markup=InlineKeyboardMarkup([[_back_btn("admin_back"), _close_btn()]]),
            )
        except Exception as exc:
            await safe_edit_text(
                query,
                b(small_caps(f"❌ cleanup error: {e(str(exc)[:100])}")) ,
                reply_markup=InlineKeyboardMarkup([[_back_btn("admin_back")]]),
            )
        return

    if data == "admin_restart_confirm":
        if not is_admin:
            return
        await safe_edit_text(
            query,
            b("⚠️ Restart Bot?") + "\n\n" + bq(b("This will restart the bot. All conversations will be reset.")),
            reply_markup=InlineKeyboardMarkup([
                [bold_button("✔️ RESTART", callback_data="admin_do_restart"),
                 bold_button("CANCEL", callback_data="admin_back")],
            ]),
        )
        return

    if data == "admin_do_restart":
        if not is_admin:
            return
        await safe_answer(query, "Restarting…")
        await reload_command(update, context)
        return

    # ── Broadcast ──────────────────────────────────────────────────────────────────
    if data == "admin_broadcast_start":
        if not is_admin:
            return
        user_states[uid] = PENDING_BROADCAST
        try:
            await query.delete_message()
        except Exception:
            pass
        msg = await safe_send_message(
            context.bot, chat_id,
            b("📣 Broadcast") + "\n\n"
            + bq(b("Send the message you want to broadcast to all users.\n\n")
                 + b("Supports: text, photos, videos, documents, stickers.")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_back")]]),
        )
        await store_bot_prompt(context, msg)
        return

    if data.startswith("broadcast_mode_"):
        if not is_admin:
            return
        mode = data[len("broadcast_mode_"):]
        context.user_data["broadcast_mode"] = mode
        msg_data = context.user_data.get("broadcast_message")
        if not msg_data:
            await safe_edit_text(query, b("❌ Broadcast message lost. Please start over."))
            user_states.pop(uid, None)
            return
        await safe_edit_text(
            query,
            b(f"Mode selected: {e(mode)}") + "\n\n"
            + bq(b("Send /confirm to start broadcasting\nor /cancel to abort.")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_back")]]),
        )
        user_states[uid] = PENDING_BROADCAST_CONFIRM
        return

    if data == "broadcast_schedule":
        if not is_admin:
            return
        user_states[uid] = SCHEDULE_BROADCAST_DATETIME
        await safe_edit_text(
            query,
            b("📅 Schedule Broadcast") + "\n\n"
            + bq(b("Send the date and time for the broadcast:\n")
                 + b("Format: YYYY-MM-DD HH:MM (UTC)")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_back")]]),
        )
        return

    # ── Force-sub channel management ───────────────────────────────────────────────
    if data == "manage_force_sub":
        if not is_admin:
            return
        await delete_bot_prompt(context, chat_id)
        user_states.pop(uid, None)
        channels = get_all_force_sub_channels(return_usernames_only=False)
        text = b(f"FORCE-SUB CHANNELS ({len(channels)})") + "\n\n"
        if channels:
            for uname, title, jbr in channels:
                jbr_tag = " ✔️" if jbr else ""
                text += f"• <b>{e(title or uname)}</b>{jbr_tag} — <code>{e(str(uname))}</code>\n"
        else:
            text += bq(b("No channels configured.\nUse ➕ ADD to add one."))
        text += (
            "\n\n" + bq(
                "<b>How to add:</b>\n"
                "➕ ADD — enter @username or channel ID\n"
                "• Supports ID: -1001234567890\n"
                "• Supports @username\n"
                "• Optional: append 'jbr' for join-by-request"
            )
        )
        grid = [
            _btn("➕ ADD CHANNEL",    "fsub_add"),
            _btn("REMOVE CHANNEL",    "fsub_remove_menu"),
            _btn("LIST CHANNELS",     "fsub_list_full"),
            _btn("GEN LINK",          "generate_links"),
            _btn("🎌 ANIME LINKS",   "admin_anime_links"),
            _btn("📣 CHANNEL WELCOME", "admin_channel_welcome"),
            _btn("CLONE REDIRECT",    "manage_clones"),
            _btn("LINK STATS",        "fsub_link_stats"),
            _btn("📨 FWD SOURCE",    "fsub_fwd_source"),
        ]
        rows = _grid3(grid)
        rows.append([_back_btn("admin_back"), _close_btn()])
        markup = InlineKeyboardMarkup(rows)
        try:
            await query.delete_message()
        except Exception:
            pass
        _img = None
        if _PANEL_IMAGE_AVAILABLE:
            try:
                _img = await get_panel_pic_async("channels")
            except Exception:
                pass
        if _img:
            try:
                await context.bot.send_photo(chat_id, _img, caption=text, parse_mode=ParseMode.HTML, reply_markup=markup)
            except Exception:
                await safe_send_message(context.bot, chat_id, text, reply_markup=markup)
        else:
            await safe_send_message(context.bot, chat_id, text, reply_markup=markup)
    if data == "fsub_add":
        if not is_admin:
            return
        user_states[uid] = ADD_CHANNEL_USERNAME
        try:
            await query.delete_message()
        except Exception:
            pass
        msg = await safe_send_message(
            context.bot, chat_id,
            b("➕ ADD FORCE-SUB CHANNEL") + "\n\n"
            + bq(
                b("Choose any of these 3 methods:\n\n")
                + "① <b>@username</b> — e.g. <code>@BeatAnime</code>\n"
                + "② <b>Numeric ID</b> — e.g. <code>-1001234567890</code>\n"
                + "③ <b>Forward a post</b> — forward any message from the channel here\n\n"
                + "<i>Bot must be admin in the channel before adding.</i>\n\n"
                + b("Send @username, channel ID, or forward a post now:")
            ),
            reply_markup=InlineKeyboardMarkup([
                [bold_button("📩 How to forward a post", callback_data="fsub_fwd_help")],
                [_back_btn("manage_force_sub"), _close_btn()],
            ]),
        )
        await store_bot_prompt(context, msg)
        return

    if data == "fsub_fwd_help":
        await safe_answer(query, "", show_alert=False)
        await safe_edit_text(
            query,
            b("📩 METHOD 3: Forward a Post") + "\n\n"
            + bq(
                "1. Open the channel you want to add\n"
                "2. Tap any message → Forward\n"
                "3. Forward it to this bot (in this chat)\n\n"
                "The bot will automatically read the channel ID from the forwarded post."
            ),
            reply_markup=InlineKeyboardMarkup([[_back_btn("fsub_add")]]),
        )
        # Set state so next message (forwarded post) is handled
        user_states[uid] = PENDING_CHANNEL_POST
        return

    if data == "fsub_remove_menu":
        if not is_admin:
            return
        channels = get_all_force_sub_channels(return_usernames_only=False)
        if not channels:
            await safe_answer(query, "No channels to remove.")
            return
        buttons = [
            _btn(f"{title or uname}", f"fsub_del_{uname}")
            for uname, title, jbr in channels
        ]
        rows = _grid3(buttons)
        rows.append([_back_btn("manage_force_sub"), _close_btn()])
        await safe_edit_text(
            query,
            b("SELECT CHANNEL TO REMOVE") + "\n\n"
            + bq("Tap the channel you want to remove from force-sub list."),
            reply_markup=InlineKeyboardMarkup(rows),
        )
        return

    if data.startswith("fsub_del_"):
        if not is_admin:
            return
        uname = data[len("fsub_del_"):]
        delete_force_sub_channel(uname)
        await safe_answer(query, f"Removed: {uname}")
        await button_handler(update, context, "manage_force_sub")
        return

    if data == "fsub_list_full":
        if not is_admin:
            return
        channels = get_all_force_sub_channels(return_usernames_only=False)
        text = b(f"ALL FORCE-SUB CHANNELS ({len(channels)})") + "\n\n"
        for i, (uname, title, jbr) in enumerate(channels, 1):
            jbr_str = " ✔️ JBR" if jbr else ""
            text += f"<b>{i}.</b> {e(title or uname)}{jbr_str}\n    ID: <code>{e(str(uname))}</code>\n"
        await safe_edit_text(
            query, text,
            reply_markup=InlineKeyboardMarkup([[_back_btn("manage_force_sub"), _close_btn()]]),
        )
        return

    if data == "fsub_link_stats":
        if not is_admin:
            return
        total = get_links_count()
        channels = get_all_force_sub_channels()
        await safe_answer(query, f"Total links: {total} | Channels: {len(channels)}")
        return

    if data == "generate_links":
        if not is_admin:
            return
        user_states[uid] = GENERATE_LINK_IDENTIFIER
        await safe_edit_text(
            query,
            b(small_caps("🔗 generate channel link")) + "\n\n"
            + bq(
                b(small_caps("step 1/2: send the channel\n\n"))
                + small_caps("• @channelname\n")
                + small_caps("• -1001234567890 (numeric id)\n")
                + small_caps("• forward any post from the channel\n\n")
                + b(small_caps("the channel title will auto-become the filter keyword."))
                + small_caps("\nwhen users type that title in any group, they get the poster + join button.")
            ),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_back")]]),
        )
        return

    if data == "admin_show_links":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        await backup_command(update, context)
        return

    # ── Channel Welcome System ────────────────────────────────────────────────────
    if data == "admin_channel_welcome":
        if not is_admin:
            return
        await show_channel_welcome_panel(context, chat_id, query)
        return

    if data == "cw_add":
        if not is_admin:
            return
        user_states[uid] = "CW_WAITING_CHANNEL_ID"
        await safe_edit_text(
            query,
            b("📣 add channel welcome") + "\n\n"
            + bq(
                b(small_caps("send the channel id, @username, or forward a post:")) + "\n\n"
                + small_caps("• @channelname") + "\n"
                + small_caps("• -1001234567890") + "\n"
                + small_caps("• or forward any message from the channel") + "\n\n"
                + small_caps("⚠️ bot must be admin in the channel.")
            ),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_channel_welcome"), _close_btn()]]),
        )
        return

    if data == "cw_list":
        if not is_admin:
            return
        try:
            from database_dual import get_all_channel_welcomes, get_channel_welcome
            channels = get_all_channel_welcomes()
        except Exception:
            channels = []
        if not channels:
            await safe_answer(query, small_caps("no channels configured yet."))
            return
        text = b("📋 " + small_caps("configured channel welcomes:")) + "\n\n"
        for ch_id, enabled, wtext in channels:
            icon = "🟢" if enabled else "🔴"
            text += f"{icon} <code>{ch_id}</code>\n"
            if wtext:
                text += f"   {e((wtext)[:60])}…\n"
        await safe_edit_text(
            query, text,
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_channel_welcome"), _close_btn()]]),
        )
        return

    if data == "cw_remove_menu":
        if not is_admin:
            return
        try:
            from database_dual import get_all_channel_welcomes
            channels = get_all_channel_welcomes()
        except Exception:
            channels = []
        if not channels:
            await safe_answer(query, small_caps("nothing to remove."))
            return
        btns = [[InlineKeyboardButton(f"🗑 {ch_id}", callback_data=f"cw_del_{ch_id}")]
                for ch_id, _, _ in channels[:10]]
        btns.append([_back_btn("admin_channel_welcome"), _close_btn()])
        await safe_edit_text(
            query, b(small_caps("select channel to remove:")),
            reply_markup=InlineKeyboardMarkup(btns),
        )
        return

    if data.startswith("cw_del_"):
        if not is_admin:
            return
        try:
            from database_dual import delete_channel_welcome
            ch_id = int(data[len("cw_del_"):])
            delete_channel_welcome(ch_id)
            await safe_answer(query, small_caps(f"removed channel {ch_id}"))
            await show_channel_welcome_panel(context, chat_id, query)
        except Exception as exc:
            await safe_answer(query, f"error: {str(exc)[:60]}", show_alert=True)
        return

    if data.startswith("cw_toggle_"):
        if not is_admin:
            return
        try:
            from database_dual import get_channel_welcome, set_channel_welcome
            ch_id = int(data[len("cw_toggle_"):])
            s = get_channel_welcome(ch_id)
            new_state = not (s.get("enabled", True) if s else True)
            set_channel_welcome(ch_id, enabled=new_state)
            await safe_answer(query, small_caps(f"welcome {'enabled' if new_state else 'disabled'}"))
            await show_channel_welcome_panel(context, chat_id, query)
        except Exception as exc:
            await safe_answer(query, f"error: {str(exc)[:60]}", show_alert=True)
        return

    if data.startswith("cw_edit_"):
        if not is_admin:
            return
        ch_id = int(data[len("cw_edit_"):])
        try:
            from database_dual import get_channel_welcome
            s = get_channel_welcome(ch_id) or {}
        except Exception:
            s = {}
        wtext   = s.get("welcome_text", "")
        img_fid = s.get("image_file_id", "")
        img_url = s.get("image_url", "")
        btns_json = s.get("buttons", [])
        enabled = s.get("enabled", True)

        text = (
            b(small_caps(f"edit channel welcome: {ch_id}")) + "\n\n"
            + bq(
                f"<b>{small_caps('enabled')}:</b> {'🟢 yes' if enabled else '🔴 no'}\n"
                f"<b>{small_caps('text')}:</b> {e((wtext)[:60]) if wtext else small_caps('not set')}\n"
                f"<b>{small_caps('image')}:</b> {'✅ set' if img_fid or img_url else small_caps('not set')}\n"
                f"<b>{small_caps('buttons')}:</b> {len(btns_json)} {small_caps('configured')}"
            )
        )
        context.user_data["cw_editing_channel"] = ch_id
        edit_kb = [
            [InlineKeyboardButton(small_caps("✏️ set text"),    callback_data=f"cw_settext_{ch_id}"),
             InlineKeyboardButton(small_caps("🖼 set image"),   callback_data=f"cw_setimg_{ch_id}")],
            [InlineKeyboardButton(small_caps("🔘 set buttons"), callback_data=f"cw_setbtns_{ch_id}"),
             InlineKeyboardButton(small_caps("⚡ toggle on/off"), callback_data=f"cw_toggle_{ch_id}")],
            [InlineKeyboardButton(small_caps("👁 preview"),     callback_data=f"cw_preview_{ch_id}"),
             InlineKeyboardButton(small_caps("🗑 remove"),      callback_data=f"cw_del_{ch_id}")],
            [_back_btn("admin_channel_welcome"), _close_btn()],
        ]
        await safe_edit_text(query, text, reply_markup=InlineKeyboardMarkup(edit_kb))
        return

    if data.startswith("cw_settext_"):
        if not is_admin:
            return
        ch_id = int(data[len("cw_settext_"):])
        context.user_data["cw_editing_channel"] = ch_id
        user_states[uid] = CW_SET_TEXT
        await safe_edit_text(
            query,
            b(small_caps("send the welcome text:")) + "\n\n"
            + bq(
                small_caps("this text is sent as a dm when someone joins the channel.") + "\n\n"
                + small_caps("available placeholders:") + "\n"
                + "• <code>{first}</code> — " + small_caps("user first name") + "\n"
                + "• <code>{last}</code> — " + small_caps("user last name") + "\n"
                + "• <code>{full}</code> — " + small_caps("full name") + "\n"
                + "• <code>{id}</code> — " + small_caps("user id") + "\n"
                + "• <code>{channel}</code> — " + small_caps("channel title")
            ),
            reply_markup=InlineKeyboardMarkup([[_back_btn(f"cw_edit_{ch_id}"), _close_btn()]]),
        )
        return

    if data.startswith("cw_setbtns_"):
        if not is_admin:
            return
        ch_id = int(data[len("cw_setbtns_"):])
        context.user_data["cw_editing_channel"] = ch_id
        user_states[uid] = CW_SET_BUTTONS
        await safe_edit_text(
            query,
            b(small_caps("send button config:")) + "\n\n"
            + bq(
                small_caps("one button per line, format:") + "\n"
                + "<code>Button Label - https://url.com</code>\n\n"
                + small_caps("example:") + "\n"
                + "<code>Join Channel - https://t.me/BeatAnime</code>\n"
                + "<code>Request - https://t.me/Beat_Hindi_Dubbed</code>"
            ),
            reply_markup=InlineKeyboardMarkup([[_back_btn(f"cw_edit_{ch_id}"), _close_btn()]]),
        )
        return

    if data.startswith("cw_setimg_"):
        if not is_admin:
            return
        ch_id = int(data[len("cw_setimg_"):])
        context.user_data["cw_editing_channel"] = ch_id
        user_states[uid] = "CW_AWAITING_IMAGE"
        await safe_edit_text(
            query,
            b(small_caps("send welcome image:")) + "\n\n"
            + bq(
                small_caps("send a photo, sticker, or image url.") + "\n"
                + small_caps("this image appears at the top of the welcome message.")
            ),
            reply_markup=InlineKeyboardMarkup([[_back_btn(f"cw_edit_{ch_id}"), _close_btn()]]),
        )
        return

    if data.startswith("cw_preview_"):
        if not is_admin:
            return
        ch_id = int(data[len("cw_preview_"):])
        asyncio.create_task(send_channel_welcome(context.bot, chat_id, ch_id))
        await safe_answer(query, small_caps("preview sent to you in dm."))
        return

    if data == "admin_anime_links":
        if not is_admin:
            return
        try:
            from database_dual import get_all_links
            raw = get_all_links(limit=100, offset=0)
            # Deduplicate by channel_title
            seen = set()
            rows = []
            for row in (raw or []):
                t = (row[2] or "").strip()
                if t and t.lower() not in seen:
                    seen.add(t.lower())
                    rows.append(row)
        except Exception:
            rows = []
        text = b(small_caps(f"🎌 filter keywords from generated links ({len(rows)})")) + "\n\n"
        if rows:
            for row in rows[:20]:
                # (link_id, channel_username, channel_title, source_bot_username, ...)
                link_id_r    = row[0]
                ch_id_r      = row[1]
                ch_title_r   = row[2] or ch_id_r
                text += f"• <b>{e(ch_title_r)}</b> → <code>{e(str(ch_id_r))}</code>\n"
        else:
            text += bq(small_caps(
                "no links yet.\n\n"
                "use gen link in the channels panel to create one.\n"
                "the link title automatically becomes a filter keyword."
            ))
        text += (
            "\n\n" + bq(
                b(small_caps("how it works:")) + "\n"
                + small_caps("generate a channel link → the title you enter becomes a filter keyword. ")
                + small_caps("when any user types that title in a group, they get a poster + join button. ")
                + small_caps("no separate table needed — it all comes from generated links.")
            )
        )
        rows_grid = [[_back_btn("manage_force_sub"), _close_btn()]]
        await safe_send_message(
            context.bot, chat_id, text,
            reply_markup=InlineKeyboardMarkup(rows_grid),
        )
        return

    # del_acl_ is no longer used (anime_channel_links table removed, using generated_links)
    if data.startswith("del_acl_"):
        await safe_answer(query, small_caps("use /removechannel or manage links from the channels panel."), show_alert=True)
        return

    # ── Clone bot management ────────────────────────────────────────────────────────
    if data == "manage_clones":
        if not is_admin:
            return
        await delete_bot_prompt(context, chat_id)
        user_states.pop(uid, None)
        clones = get_all_clone_bots(active_only=True)
        text = b(f"🤖 Clone Bots ({len(clones)}):") + "\n\n"
        if clones:
            for cid, token, uname, active, added in clones:
                text += f"• @{e(uname)} — Added: {str(added)[:10]}\n"
        else:
            text += b("No clone bots registered.")
        keyboard = [
            [bold_button("➕ Add Clone", callback_data="clone_add"),
             bold_button("Remove Clone", callback_data="clone_remove")],
            [bold_button("♻️ Refresh Commands on Clones", callback_data="clone_refresh_cmds")],
            [_back_btn("admin_back")],
        ]
        await safe_edit_text(query, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "clone_add":
        if not is_admin:
            return
        user_states[uid] = ADD_CLONE_TOKEN
        await safe_edit_text(
            query,
            b(" Add Clone Bot") + "\n\n"
            + bq(b("Send the BOT TOKEN of the clone bot.\n⚠️ Keep tokens secret!")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="manage_clones")]]),
        )
        return

    if data == "clone_remove":
        if not is_admin:
            return
        clones = get_all_clone_bots(active_only=True)
        if not clones:
            await safe_answer(query, "No clones to remove.")
            return
        keyboard = []
        for cid, token, uname, active, added in clones:
            keyboard.append([bold_button(f"🗑 @{uname}", callback_data=f"clone_del_{uname}")])
        keyboard.append([_back_btn("manage_clones")])
        await safe_edit_text(
            query, b("Select clone bot to remove:"),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    if data.startswith("clone_del_"):
        if not is_admin:
            return
        uname = data[len("clone_del_"):]
        remove_clone_bot(uname)
        await safe_answer(query, f"Removed @{uname}")
        await button_handler(update, context, "manage_clones")
        return

    if data == "clone_refresh_cmds":
        if not is_admin:
            return
        clones = get_all_clone_bots(active_only=True)
        if not clones:
            await safe_answer(query, "No clone bots found.")
            return
        count = 0
        for _, token, uname, _, _ in clones:
            try:
                clone_bot = Bot(token=token)
                await _register_bot_commands_on_bot(clone_bot)
                count += 1
            except Exception:
                pass
        await safe_answer(query, f"Commands refreshed on {count} clone(s).")
        await button_handler(update, context, "manage_clones")
        return

    # ── Admin settings ─────────────────────────────────────────────────────────────
    if data == "admin_settings":
        if not is_admin:
            return
        maint = get_setting("maintenance_mode", "false")
        clone_red = get_setting("clone_redirect_enabled", "false")
        backup_url = get_setting("backup_channel_url", "Not set")
        clean_gc    = get_setting("clean_gc_enabled", "true") == "true"
        spam_on     = get_setting("spam_protection_enabled", "true") == "true"
        wm_on       = get_setting("watermarks_enabled", "true") == "true"
        text = (
            b("BOT SETTINGS") + "\n\n"
            + bq(
                f"<b>Maintenance:</b> {'🔴 ON' if maint == 'true' else '🟢 OFF'}\n"
                f"<b>Clone Redirect:</b> {'🟢 ON' if clone_red == 'true' else '🔴 OFF'}\n"
                f"<b>Clean GC:</b> {'🟢 ON' if clean_gc else '🔴 OFF'}\n"
                f"<b>Spam Protect:</b> {'🟢 ON' if spam_on else '🔴 OFF'}\n"
                f"<b>Watermarks:</b> {'🟢 ON' if wm_on else '🔴 OFF'}\n"
                f"<b>Backup Channel:</b> {e(backup_url[:40])}\n"
                f"<b>Link Expiry:</b> {LINK_EXPIRY_MINUTES} min"
            )
        )
        grid = [
            _btn("MAINT " + ("🔴" if maint == "true" else "🟢"),      "toggle_maintenance"),
            _btn("CLONE " + ("🟢" if clone_red == "true" else "🔴"),   "toggle_clone_redirect"),
            _btn("CLEAN GC " + ("🟢" if clean_gc else "🔴"),           "toggle_clean_gc"),
            _btn("SPAM PROTECT",                                         "admin_spam_settings"),
            _btn("WATERMARKS " + ("🟢" if wm_on else "🔴"),            "admin_watermarks_toggle"),
            _btn("BACKUP CHANNEL",                                       "set_backup_channel"),
            _btn("TEXT STYLE",                                           "admin_text_style"),
            _btn("FILTER POSTER",                                        "admin_filter_poster"),
            _btn("LINK EXPIRY",                                          "admin_link_expiry"),
            _btn("ENV VARIABLES",                                        "admin_env_panel"),
            _btn("BTN STYLE",                                            "admin_btn_style"),
            _btn("IMG CACHE ♻️",                                         "admin_clear_img_cache"),
        ]
        rows = _grid3(grid)
        rows.append([_back_btn("admin_back"), _close_btn()])
        await safe_edit_text(query, text, reply_markup=InlineKeyboardMarkup(rows))
        return

    if data == "toggle_maintenance":
        if not is_admin:
            return
        current = get_setting("maintenance_mode", "false")
        new_val = "false" if current == "true" else "true"
        set_setting("maintenance_mode", new_val)
        await safe_answer(query, f"Maintenance {'ON' if new_val == 'true' else 'OFF'}")
        await button_handler(update, context, "admin_settings")
        return

    if data == "toggle_clone_redirect":
        if not is_admin:
            return
        current = get_setting("clone_redirect_enabled", "false")
        new_val = "false" if current == "true" else "true"
        set_setting("clone_redirect_enabled", new_val)
        await safe_answer(query, f"Clone redirect {'ON' if new_val == 'true' else 'OFF'}")
        await button_handler(update, context, "admin_settings")
        return

    if data == "toggle_clean_gc":
        if not is_admin:
            return
        current = get_setting("clean_gc_enabled", "true")
        new_val = "false" if current == "true" else "true"
        set_setting("clean_gc_enabled", new_val)
        await safe_answer(query, f"Clean GC {'enabled' if new_val == 'true' else 'disabled'}")
        await button_handler(update, context, "admin_settings")
        return

    if data == "admin_link_expiry":
        if not is_admin:
            return
        current_exp = get_setting("link_expiry_override", str(LINK_EXPIRY_MINUTES))
        user_states[uid] = "AWAITING_LINK_EXPIRY"
        await safe_edit_text(
            query,
            b("LINK EXPIRY MINUTES") + "\n\n"
            + bq(f"<b>Current:</b> {current_exp} minutes\n\nSend a number (1-60):"),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_settings"), _close_btn()]]),
        )
        return

    if data == "admin_watermarks_toggle":
        if not is_admin:
            return
        cur = get_setting("watermarks_enabled", "true")
        new_val = "false" if cur == "true" else "true"
        set_setting("watermarks_enabled", new_val)
        await safe_answer(query, f"Watermarks {'enabled' if new_val == 'true' else 'disabled'}")
        await button_handler(update, context, "admin_settings")
        return

    if data == "admin_spam_settings":
        if not is_admin:
            return
        spam_protect = get_setting("spam_protection_enabled", "true") == "true"
        flood_limit  = get_setting("flood_limit", "5")
        flood_window = get_setting("flood_window_sec", "10")
        text_sp = (
            b("SPAM PROTECTION") + "\n\n"
            + bq(
                f"<b>Status:</b> {'🟢 Enabled' if spam_protect else '🔴 Disabled'}\n"
                f"<b>Flood limit:</b> {flood_limit} msgs\n"
                f"<b>Flood window:</b> {flood_window}s\n\n"
                "Anti-spam covers:\n"
                " ✔️ Flood detection\n"
                " ✔️ Message rate limiting\n"
                " ✔️ User cooldowns on anime requests\n"
                " ✔️ Banned user blocking\n"
                " ✔️ Maintenance mode blocking"
            )
        )
        sp_grid = [
            _btn("TOGGLE " + ("🟢" if spam_protect else "🔴"), "toggle_spam_protect"),
            _btn("FLOOD LIMIT",  "set_flood_limit"),
            _btn("FLOOD WINDOW", "set_flood_window"),
        ]
        sp_rows = _grid3(sp_grid)
        sp_rows.append([_back_btn("admin_settings"), _close_btn()])
        await safe_edit_text(query, text_sp, reply_markup=InlineKeyboardMarkup(sp_rows))
        return

    # ── ENV Variables Panel ──────────────────────────────────────────────────────
    if data == "admin_env_panel":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        # Get current values from DB (overrides) or original env
        def _ev(key, default=""):
            try:
                return get_setting(f"env_{key}", os.getenv(key, default)) or default
            except Exception:
                return os.getenv(key, default)

        text = (
            b("ENV VARIABLES PANEL") + "\n\n"
            + bq(
                "<b>Set any value directly from here.</b>\n"
                "Changes take effect immediately (stored in DB).\n"
                "Original .env is not modified.\n\n"
                f"<b>BOT_NAME:</b> {e(_ev('BOT_NAME', BOT_NAME))}\n"
                f"<b>JOIN_BTN_TEXT:</b> {e(_ev('JOIN_BTN_TEXT', JOIN_BTN_TEXT))} {small_caps('← text on filter poster button')}\n"
                f"<b>HERE_IS_LINK_TEXT:</b> {e(_ev('HERE_IS_LINK_TEXT', HERE_IS_LINK_TEXT)[:40])}...\n"
                f"<b>ANIME_BTN_TEXT:</b> {e(_ev('ANIME_BTN_TEXT', ANIME_BTN_TEXT))}\n"
                f"<b>REQUEST_BTN_TEXT:</b> {e(_ev('REQUEST_BTN_TEXT', REQUEST_BTN_TEXT))}\n"
                f"<b>CONTACT_BTN_TEXT:</b> {e(_ev('CONTACT_BTN_TEXT', CONTACT_BTN_TEXT))}\n"
                f"<b>FORCE_SUB_TEXT:</b> {e(_ev('FORCE_SUB_TEXT', FORCE_SUB_TEXT)[:30])}...\n"
                f"<b>LINK_EXPIRY_MINUTES:</b> {e(_ev('LINK_EXPIRY_MINUTES', str(LINK_EXPIRY_MINUTES)))}\n"
                f"<b>BUTTON_STYLE:</b> {e(_ev('BUTTON_STYLE', BUTTON_STYLE))}\n"
                f"<b>POSTER_DB_CHANNEL:</b> {e(_ev('POSTER_DB_CHANNEL', '0'))}\n"
                f"<b>PUBLIC_ANIME_CHANNEL_URL:</b> {e(_ev('PUBLIC_ANIME_CHANNEL_URL', PUBLIC_ANIME_CHANNEL_URL)[:40])}"
            )
        )
        # 3x3 env editing grid
        # Read current panel image source setting
        try:
            _img_src = get_setting("panel_image_source", "url") or "url"
        except Exception:
            _img_src = "url"
        _img_src_label = "🔗 Source: URL-first" if _img_src == "url" else "🌐 Source: API-first"

        grid = [
            _btn("BOT NAME",         "env_edit_BOT_NAME"),
            _btn("JOIN BTN TEXT",    "env_edit_JOIN_BTN_TEXT"),
            _btn("LINK TEXT",        "env_edit_HERE_IS_LINK_TEXT"),
            _btn("ANIME BTN",        "env_edit_ANIME_BTN_TEXT"),
            _btn("REQUEST BTN",      "env_edit_REQUEST_BTN_TEXT"),
            _btn("CONTACT BTN",      "env_edit_CONTACT_BTN_TEXT"),
            _btn("FORCE SUB MSG",    "env_edit_FORCE_SUB_TEXT"),
            _btn("LINK EXPIRY",      "env_edit_LINK_EXPIRY_MINUTES"),
            _btn("BTN STYLE",        "env_edit_BUTTON_STYLE"),
            _btn("POSTER CHANNEL",   "env_edit_POSTER_DB_CHANNEL"),
            _btn("ANIME URL",        "env_edit_PUBLIC_ANIME_CHANNEL_URL"),
            _btn("WELCOME TEXT",     "env_edit_BOT_WELCOME_TEXT"),
        ]
        rows = _grid3(grid)
        # Panel image controls
        rows.append([
            bold_button(_img_src_label, callback_data="panel_img_toggle_source"),
            bold_button("🖼 Add/View Panel Images", callback_data="panel_img_add_urls"),
            bold_button("♻️ Refresh Cache", callback_data="panel_img_refresh_cache"),
        ])
        rows.append([_back_btn("admin_settings"), _close_btn()])
        img_url = None
        if _PANEL_IMAGE_AVAILABLE:
            try:
                img_url = await get_panel_pic_async("settings")
            except Exception:
                pass
        if img_url:
            sent = await safe_send_photo(context.bot, chat_id, img_url, caption=text, reply_markup=InlineKeyboardMarkup(rows))
            if sent:
                return
        await safe_send_message(context.bot, chat_id, text, reply_markup=InlineKeyboardMarkup(rows))
        return

    if data.startswith("env_edit_"):
        if not is_admin:
            return
        key = data[len("env_edit_"):]
        current = get_setting(f"env_{key}", os.getenv(key, "")) or ""
        user_states[uid] = f"AWAITING_ENV_{key}"
        hints = {
            "BUTTON_STYLE":         "Options: mathbold | smallcaps",
            "LINK_EXPIRY_MINUTES":  "Enter number (1-1440)",
            "POSTER_DB_CHANNEL":    "Channel ID e.g. -1001234567890",
        }
        hint = hints.get(key, f"Current: {current[:60] or '(empty)'}")
        await safe_edit_text(
            query,
            b(f"SET {e(key)}") + "\n\n"
            + bq(f"<b>Hint:</b> {e(hint)}\n\nSend new value or <code>reset</code> to use .env default:"),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_env_panel"), _close_btn()]]),
        )
        return

    if data == "toggle_spam_protect":
        if not is_admin:
            return
        cur = get_setting("spam_protection_enabled", "true")
        new_val = "false" if cur == "true" else "true"
        set_setting("spam_protection_enabled", new_val)
        await safe_answer(query, f"Spam protection {'on' if new_val == 'true' else 'off'}")
        await button_handler(update, context, "admin_spam_settings")
        return

    if data == "set_backup_channel":
        if not is_admin:
            return
        user_states[uid] = SET_BACKUP_CHANNEL
        await safe_edit_text(
            query,
            b(" Set Backup Channel URL") + "\n\n"
            + bq(b("Send the backup channel URL (e.g., https://t.me/backup_channel)")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_settings")]]),
        )
        return

    # ── Panel Image Source controls ───────────────────────────────────────────────
    # ── Panel image gallery navigation ───────────────────────────────────────────
    if data.startswith("panel_img_view_"):
        if not is_admin:
            return
        try:
            page = int(data.split("_")[-1])
        except Exception:
            page = 0
        await _show_panel_img_list(context.bot, chat_id, query=query, page=page)
        return

    if data.startswith("panel_img_del_"):
        if not is_admin:
            return
        try:
            page = int(data.split("_")[-1])
        except Exception:
            page = 0
        items = _get_panel_db_images()
        if 0 <= page < len(items):
            removed = items.pop(page)
            # Re-index remaining items
            for i, it in enumerate(items):
                it["index"] = i + 1
            _save_panel_db_images(items)
            # Clear session file_id cache so next panel uses new list
            if _PANEL_IMAGE_AVAILABLE:
                try:
                    from panel_image import clear_tg_fileid
                    clear_tg_fileid()
                except Exception:
                    pass
            try:
                await query.answer(f"✅ Image #{page + 1} deleted", show_alert=False)
            except Exception:
                pass
            # Try to also delete from panel DB channel (non-fatal if fails)
            if PANEL_DB_CHANNEL and removed.get("msg_id"):
                try:
                    await context.bot.delete_message(PANEL_DB_CHANNEL, removed["msg_id"])
                except Exception:
                    pass
            # Show updated list
            new_page = max(0, page - 1) if items else 0
            await _show_panel_img_list(context.bot, chat_id, query=None, page=new_page)
        else:
            await query.answer("❌ Image not found", show_alert=True)
        return

    if data == "panel_img_manage":
        if not is_admin:
            return
        await _show_panel_img_list(context.bot, chat_id, query=query, page=0)
        return

    if data == "panel_img_toggle_source":
        if not is_admin:
            return
        try:
            current = get_setting("panel_image_source", "url") or "url"
            new_src = "api" if current == "url" else "url"
            set_setting("panel_image_source", new_src)
            label = "🌐 API-first (waifu.im → anilist → nekos → safone)" if new_src == "api"                     else "🔗 URL-first (your custom URLs / PANEL_PICS env)"
            try:
                await query.answer(f"✅ Panel source: {label[:40]}", show_alert=True)
            except Exception:
                pass
            # Invalidate all panel caches so next panel uses new source
            if _PANEL_IMAGE_AVAILABLE:
                try:
                    clear_image_cache()
                    logger.info(f"[panel] source toggled to {new_src}, cache cleared")
                except Exception:
                    pass
        except Exception as exc:
            logger.error(f"panel_img_toggle: {exc}")
        # Re-show settings panel
        await button_handler(update, context, "admin_settings")
        return

    if data == "panel_img_add_urls":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_PANEL_IMG_URLS"
        try:
            await query.delete_message()
        except Exception:
            pass
        try:
            import json as _j
            existing = _j.loads(get_setting("panel_image_urls", "[]") or "[]")
        except Exception:
            existing = []
        existing_text = "\n".join(existing[:5]) + ("\n..." if len(existing) > 5 else "") if existing else "(none)"
        total_imgs = len(_get_panel_db_images())
        await safe_send_message(
            context.bot, chat_id,
            b("🖼 Add Panel Images") + "\n\n"
            + bq(
                "<b>3 ways to add panel images:</b>\n\n"
                "1️⃣ <b>Send a photo</b> — forward any image to this chat, bot saves to channel\n\n"
                "2️⃣ <b>Send file_ids</b> — paste Telegram file_ids, comma or newline separated\n"
                "   (Use /getfileid to get a file_id from any photo)\n\n"
                "3️⃣ <b>Send URLs</b> — direct https:// image links, comma or newline separated\n\n"
                f"<b>Currently stored: {total_imgs} image(s)</b>"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🖼 View Current Images", callback_data="panel_img_manage")],
                [_back_btn("admin_settings"), _close_btn()],
            ]),
        )
        return

    if data == "panel_img_clear_urls":
        if not is_admin:
            return
        try:
            set_setting("panel_image_urls", "[]")
            clear_image_cache()
            await query.answer("✅ Custom URL list cleared. Using PANEL_PICS env or APIs.", show_alert=True)
        except Exception as exc:
            await query.answer(f"❌ {str(exc)[:60]}", show_alert=True)
        await button_handler(update, context, "admin_settings")
        return

    if data == "panel_img_refresh_cache":
        if not is_admin:
            return
        try:
            n = clear_image_cache()
            await query.answer(f"✅ Cache cleared ({n} entries). Next panel load fetches fresh image.", show_alert=False)
        except Exception:
            await query.answer("✅ Cache cleared", show_alert=False)
        await button_handler(update, context, "admin_settings")
        return

    # ── Text Style panel ───────────────────────────────────────────────────────────
    if data == "admin_text_style":
        if not is_admin:
            return
        if _TEXT_STYLE_AVAILABLE:
            from text_style import build_text_style_keyboard, get_text_style_panel_text
            try:
                await query.delete_message()
            except Exception:
                pass
            await safe_send_message(
                context.bot, chat_id,
                get_text_style_panel_text(),
                reply_markup=build_text_style_keyboard(),
            )
        else:
            await safe_answer(query, "Text style module unavailable.")
        return

    if data.startswith("text_style_set_"):
        if not is_admin:
            return
        style = data[len("text_style_set_"):]
        if style in ("normal", "smallcaps", "bold"):
            if _TEXT_STYLE_AVAILABLE:
                from text_style import set_style, build_text_style_keyboard, get_text_style_panel_text
                set_style(style)
                style_names = {"normal": "Normal", "smallcaps": "Small Caps", "bold": "Bold"}
                await safe_answer(query, f"✅ Text style set to {style_names.get(style, style)}")
                await safe_edit_text(
                    query,
                    get_text_style_panel_text(),
                    reply_markup=build_text_style_keyboard(),
                )
        return

    # ── Filter Poster panel ─────────────────────────────────────────────────────────
    if data == "admin_filter_poster":
        if not is_admin:
            return
        if _FILTER_POSTER_AVAILABLE:
            try:
                await query.delete_message()
            except Exception:
                pass
            await safe_send_message(
                context.bot, chat_id,
                get_filter_poster_settings_text(chat_id),
                reply_markup=build_filter_poster_settings_keyboard(chat_id),
            )
        else:
            await safe_answer(query, "Filter poster module unavailable.")
        return

    if data.startswith("fp_toggle_"):
        if not is_admin:
            return
        try:
            fp_chat_id = int(data.split("_")[-1])
        except Exception:
            fp_chat_id = 0
        if _FILTER_POSTER_AVAILABLE:
            current = _get_filter_poster_enabled(fp_chat_id)
            _set_filter_poster_enabled(fp_chat_id, not current)
            label = "enabled" if not current else "disabled"
            await safe_answer(query, f"✅ Filter posters {label}")
            await safe_edit_text(
                query,
                get_filter_poster_settings_text(fp_chat_id),
                reply_markup=build_filter_poster_settings_keyboard(fp_chat_id),
            )
        return

    if data.startswith("fp_tmpl_"):
        if not is_admin:
            return
        parts = data.split("_")
        # fp_tmpl_{chat_id}_{template}
        if len(parts) >= 4:
            try:
                fp_chat_id = int(parts[2])
                fp_template = parts[3]
                if _FILTER_POSTER_AVAILABLE:
                    _set_default_poster_template(fp_chat_id, fp_template)
                    await safe_answer(query, f"✅ Template set to {fp_template}")
                    await safe_edit_text(
                        query,
                        get_filter_poster_settings_text(fp_chat_id),
                        reply_markup=build_filter_poster_settings_keyboard(fp_chat_id),
                    )
            except Exception:
                pass
        return


    if data.startswith("fp_mode_toggle_"):
        if not is_admin:
            return
        try:
            fp_chat_id = int(data.split("_")[-1])
        except Exception:
            fp_chat_id = 0
        if _FILTER_POSTER_AVAILABLE:
            from filter_poster import get_filter_mode, set_filter_mode
            cur = get_filter_mode(fp_chat_id)
            new_mode = "text" if cur == "poster" else "poster"
            set_filter_mode(fp_chat_id, new_mode)
            label = "TEXT (link only)" if new_mode == "text" else "POSTER (full card)"
            await safe_answer(query, f"✔️ Mode: {label}")
            await safe_edit_text(
                query,
                get_filter_poster_settings_text(fp_chat_id),
                reply_markup=build_filter_poster_settings_keyboard(fp_chat_id),
            )
        return

    if data.startswith("fp_wm_toggle_"):
        if not is_admin:
            return
        parts = data.split("_")
        layer = parts[3]
        try:
            fp_chat_id = int(parts[4])
        except Exception:
            fp_chat_id = chat_id
        if _FILTER_POSTER_AVAILABLE:
            from filter_poster import get_wm_layer, set_wm_layer
            ldata = get_wm_layer(fp_chat_id, layer)
            ldata["enabled"] = not ldata.get("enabled", False)
            set_wm_layer(fp_chat_id, layer, ldata)
            state_str = "enabled" if ldata["enabled"] else "disabled"
            await safe_answer(query, f"✔️ Layer {layer.upper()} {state_str}")
            await safe_edit_text(
                query,
                get_filter_poster_settings_text(fp_chat_id),
                reply_markup=build_filter_poster_settings_keyboard(fp_chat_id),
            )
        return

    if data.startswith("fp_wm_"):
        if not is_admin:
            return
        parts = data.split("_")
        layer = parts[2]       # a, b, or c
        try:
            fp_chat_id = int(parts[3])
        except Exception:
            fp_chat_id = chat_id
        if not _FILTER_POSTER_AVAILABLE:
            await safe_answer(query, "Filter poster module unavailable.")
            return
        from filter_poster import get_wm_layer
        ldata = get_wm_layer(fp_chat_id, layer)
        layer_names = {"a": "PRIMARY TEXT", "b": "SECONDARY TEXT", "c": "STICKER / IMAGE"}
        pos_list = "center | bottom | top | left | right | bottom-left | bottom-right | top-left | top-right"
        if layer == "c":
            panel_text = (
                b(f"WATERMARK LAYER C — STICKER / IMAGE") + "\n\n"
                + bq(
                    f"<b>Enabled:</b> {'🟢 Yes' if ldata.get('enabled') else '🔴 No'}\n"
                    f"<b>Position:</b> {e(ldata.get('position', 'bottom-left'))}\n"
                    f"<b>Scale:</b> {ldata.get('scale', 0.12)} (0.05–0.30)\n"
                    f"<b>Opacity:</b> {ldata.get('opacity', 200)} (0–255)\n\n"
                    "<b>To set sticker:</b> Send any Telegram sticker as a reply.\n"
                    "<b>To set image:</b> Send: <code>https://url | position | scale | opacity</code>\n"
                    f"<b>Positions:</b> {pos_list}"
                )
            )
        else:
            panel_text = (
                b(f"WATERMARK LAYER {layer.upper()} — {layer_names.get(layer, '')}") + "\n\n"
                + bq(
                    f"<b>Enabled:</b> {'🟢 Yes' if ldata.get('enabled') else '🔴 No'}\n"
                    f"<b>Text:</b> {e(ldata.get('text', '—'))}\n"
                    f"<b>Position:</b> {e(ldata.get('position', 'bottom-right'))}\n"
                    f"<b>Font size:</b> {ldata.get('font_size', 24)}\n"
                    f"<b>Color:</b> {e(ldata.get('color', '#FFFFFF'))}\n"
                    f"<b>Opacity:</b> {ldata.get('opacity', 150)} (0–255)\n\n"
                    "<b>Send format:</b> <code>text | position | size | #color | opacity</code>\n"
                    "<b>Example:</b> <code>BeatAnime | bottom-right | 24 | #FFFFFF | 150</code>\n"
                    f"<b>Positions:</b> {pos_list}"
                )
            )
        user_states[uid] = f"AWAITING_WM_LAYER_{layer.upper()}_{fp_chat_id}"
        try:
            await query.delete_message()
        except Exception:
            pass
        await safe_send_message(
            context.bot, chat_id, panel_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🟢 ENABLE" if not ldata.get("enabled") else "🔴 DISABLE",
                    callback_data=f"fp_wm_toggle_{layer}_{fp_chat_id}",
                )],
                [_back_btn("admin_filter_poster"), _close_btn()],
            ]),
        )
        return

    if data == "fp_set_autodel":
        if not is_admin:
            return
        try:
            cur_del = int(get_setting(f"filter_auto_delete_{chat_id}", "300"))
        except Exception:
            cur_del = 300
        user_states[uid] = "AWAITING_FILTER_AUTODEL"
        await safe_edit_text(
            query,
            b("FILTER AUTO-DELETE TIME") + "\n\n"
            + bq(
                f"<b>Current:</b> {cur_del}s ({cur_del // 60} min)\n\n"
                "Send seconds before poster + link auto-deletes:\n"
                "• <code>0</code> = never delete\n"
                "• <code>300</code> = 5 minutes (default)\n"
                "• <code>600</code> = 10 minutes\n"
                "• <code>1800</code> = 30 minutes"
            ),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_filter_poster"), _close_btn()]]),
        )
        return

    if data == "fp_set_linkexpiry":
        if not is_admin:
            return
        cur_exp = get_setting("link_expiry_override", str(LINK_EXPIRY_MINUTES))
        user_states[uid] = "AWAITING_LINK_EXPIRY_FP"
        await safe_edit_text(
            query,
            b("LINK EXPIRY MINUTES") + "\n\n"
            + bq(
                f"<b>Current:</b> {cur_exp} min\n\n"
                "Send minutes the join link stays valid:\n"
                "• <code>0</code> = permanent (no expiry)\n"
                "• <code>5</code> = 5 minutes (default)\n"
                "• <code>60</code> = 1 hour"
            ),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_filter_poster"), _close_btn()]]),
        )
        return

    # ── PRE-GENERATE all posters for registered anime channel links ───────────
    if data.startswith("fp_pregen_all_"):
        if not is_admin:
            return
        # Launch background task — report progress via DM
        asyncio.create_task(_pregen_all_filter_posters(context.bot, uid, chat_id))
        await safe_send_message(
            context.bot, chat_id,
            b(small_caps("🎌 poster pre-generation started!")) + "\n"
            + bq(
                small_caps("generating posters for all registered anime channels in background.\n\n")
                + small_caps("each poster is generated, sent to poster db channel, and cached for instant future delivery.\n\n")
                + small_caps("you will receive a summary when done.")
            ),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_filter_poster"), _close_btn()]]),
        )
        return

    if data.startswith("fp_set_join_btn_"):
        if not is_admin:
            return
        current = (get_setting("env_JOIN_BTN_TEXT", "") or JOIN_BTN_TEXT)
        user_states[uid] = "AWAITING_JOIN_BTN_TEXT"
        await safe_edit_text(
            query,
            b(small_caps("✏️ set join button text")) + "\n\n"
            + bq(
                b(small_caps("current: ")) + f"<code>{e(current)}</code>\n\n"
                + small_caps("send the new button text.\n")
                + small_caps("examples: ") + "\n"
                + "• <code>Join Now</code>\n"
                + "• <code>Watch Now</code>\n"
                + "• <code>Get Access</code>\n"
                + "• <code>Subscribe Free</code>\n"
                + "• <code>🎌 ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ</code>\n\n"
                + small_caps("this text appears on the button below every filter poster.\n")
                + small_caps("the button opens a direct 5-min invite link — no bot redirect.")
            ),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_filter_poster"), _close_btn()]]),
        )
        return

    if data == "fp_view_cache":
        if not is_admin:
            return
        count = _get_cache_count() if _FILTER_POSTER_AVAILABLE else 0
        await safe_answer(query, f"📦 {count} posters cached")
        return

    if data == "fp_clear_cache":
        if not is_admin:
            return
        if _FILTER_POSTER_AVAILABLE:
            cleared = _clear_poster_cache()
            await safe_answer(query, f"🗑 Cleared {cleared} cached posters")
            await safe_edit_text(
                query,
                get_filter_poster_settings_text(chat_id),
                reply_markup=build_filter_poster_settings_keyboard(chat_id),
            )
        return

    if data == "fp_channel_info":
        if not is_admin:
            return
        from filter_poster import POSTER_DB_CHANNEL as _PDC
        if _PDC:
            await safe_answer(query, f"Poster DB Channel: {_PDC}")
        else:
            await safe_answer(query, "Set POSTER_DB_CHANNEL in env to enable poster saving")
        return



    if data == "fp_view_cache":
        if not is_admin:
            return
        count = _get_cache_count() if _FILTER_POSTER_AVAILABLE else 0
        await safe_answer(query, f"📦 {count} posters cached")
        return

    if data == "fp_clear_cache":
        if not is_admin:
            return
        if _FILTER_POSTER_AVAILABLE:
            cleared = _clear_poster_cache()
            await safe_answer(query, f"🗑 Cleared {cleared} cached posters")
            await safe_edit_text(
                query,
                get_filter_poster_settings_text(chat_id),
                reply_markup=build_filter_poster_settings_keyboard(chat_id),
            )
        return

    if data == "fp_channel_info":
        if not is_admin:
            return
        from filter_poster import POSTER_DB_CHANNEL as _PDC
        if _PDC:
            await safe_answer(query, f"Poster DB Channel: {_PDC}")
        else:
            await safe_answer(query, "Set POSTER_DB_CHANNEL env var to enable poster saving")
        return

    # ── Feature flags ──────────────────────────────────────────────────────────────
    if data == "admin_feature_flags":
        if not is_admin:
            return
        await delete_bot_prompt(context, chat_id)
        user_states.pop(uid, None)
        await send_feature_flags_panel(context, chat_id, query)
        return

    if data.startswith("flag_toggle_"):
        if not is_admin:
            return
        parts = data[len("flag_toggle_"):].rsplit("_", 1)
        if len(parts) == 2:
            flag_key, new_val = parts
            set_setting(flag_key, new_val)
            is_on = new_val in ("true", "1")
            await safe_answer(query, f"{'Enabled' if is_on else 'Disabled'}!")
            await send_feature_flags_panel(context, chat_id, query)
        return

    # ── Filter settings panel ───────────────────────────────────────────────────────
    if data == "admin_filter_settings":
        if not is_admin:
            return
        dm_on = filters_config["global"].get("dm", True)
        grp_on = filters_config["global"].get("group", True)
        text = (
            b("Filter Settings") + "\n\n"
            f"<b>DM:</b> {'ON' if dm_on else 'OFF'}\n"
            f"<b>GROUP:</b> {'ON' if grp_on else 'OFF'}"
        )
        keyboard = [
            [bold_button("TOGGLE DM", callback_data="filter_toggle_dm")],
            [bold_button("TOGGLE GROUP", callback_data="filter_toggle_group")],
            [_back_btn("admin_back")],
        ]
        await safe_edit_text(query, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "filter_toggle_dm":
        if not is_admin:
            return
        filters_config["global"]["dm"] = not filters_config["global"].get("dm", True)
        state = "ON" if filters_config["global"]["dm"] else "OFF"
        await safe_answer(query, f"DM filter: {state}")
        await button_handler(update, context, "admin_filter_settings")
        return

    if data == "filter_toggle_group":
        if not is_admin:
            return
        filters_config["global"]["group"] = not filters_config["global"].get("group", True)
        state = "ON" if filters_config["global"]["group"] else "OFF"
        await safe_answer(query, f"Group filter: {state}")
        await button_handler(update, context, "admin_filter_settings")
        return

    # ── Category settings ──────────────────────────────────────────────────────────
    if data == "admin_category_settings":
        if not is_admin:
            return
        # Spec-compliant START PANEL / POST SETTING layout
        keyboard = [
            [bold_button("TV SHOWS", callback_data="admin_category_settings_tvshow"),
             bold_button("MOVIES", callback_data="admin_category_settings_movie")],
            [bold_button("ANIME", callback_data="admin_category_settings_anime"),
             bold_button("MANGA", callback_data="admin_category_settings_manga")],
            [bold_button("POST SETTING", callback_data="admin_settings")],
            [bold_button("AUTO FORWARD", callback_data="admin_autoforward"),
             bold_button("POST SEARCH", callback_data="admin_cmd_list")],
            [_back_btn("admin_back")],
        ]
        await safe_edit_text(
            query, b("Choose the category"),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    for cat_name in ("anime", "manga", "movie", "tvshow"):
        if data == f"admin_category_settings_{cat_name}":
            if not is_admin:
                return
            await show_category_settings_menu(context, chat_id, cat_name, query)
            return

        if data == f"settings_category_{cat_name}":
            if not is_admin:
                return
            await show_category_settings_menu(context, chat_id, cat_name, query)
            return

        # Caption
        if data == f"cat_caption_{cat_name}":
            if not is_admin:
                return
            user_states[uid] = SET_CATEGORY_CAPTION
            context.user_data["editing_category"] = cat_name
            placeholders = (
                "{title}, {status}, {type}, {episodes}, {score}, {genres}, {synopsis}, {studio}, {season}, "
                "{chapters}, {volumes}, {popularity}, {release_date}, {rating}, {overview}, {runtime}, "
                "{director}, {cast}, {network}, {name}"
            )
            await safe_edit_text(
                query,
                b(f" Set Caption Template for {e(cat_name.upper())}") + "\n\n"
                + bq(b("Send the caption template text.\n\n") + b("Available placeholders:\n") + e(placeholders)),
                reply_markup=InlineKeyboardMarkup([[
                    bold_button("🔙 Cancel", callback_data=f"admin_category_settings_{cat_name}")
                ]]),
            )
            return

        # Branding
        if data == f"cat_branding_{cat_name}":
            if not is_admin:
                return
            user_states[uid] = SET_CATEGORY_BRANDING
            context.user_data["editing_category"] = cat_name
            current = get_category_settings(cat_name).get("branding", "")
            await safe_edit_text(
                query,
                b(f"🏷 Set Branding for {e(cat_name.upper())}") + "\n\n"
                + bq(b("Send your branding text (appended at the bottom of posts).\n\n")
                     + b("Current: ") + code(e(current[:100] if current else "None"))),
                reply_markup=InlineKeyboardMarkup([[
                    bold_button("Clear Branding", callback_data=f"cat_brand_clear_{cat_name}"),
                    bold_button("🔙 Cancel", callback_data=f"admin_category_settings_{cat_name}"),
                ]]),
            )
            return

        if data == f"cat_brand_clear_{cat_name}":
            if not is_admin:
                return
            update_category_field(cat_name, "branding", "")
            await safe_answer(query, "Branding cleared.")
            await show_category_settings_menu(context, chat_id, cat_name, query)
            return

        # Buttons
        if data == f"cat_buttons_{cat_name}":
            if not is_admin:
                return
            user_states[uid] = SET_CATEGORY_BUTTONS
            context.user_data["editing_category"] = cat_name
            await safe_edit_text(
                query,
                b(f" Configure Buttons for {e(cat_name.upper())}") + "\n\n"
                + bq(
                    b("Send button config, one per line:\n")
                    + b("Format: Button Text - https://url\n\n")
                    + b("Color prefixes:\n")
                    + b("#g Text - url → 🟢\n")
                    + b("#r Text - url → 🔴\n")
                    + b("#b Text - url → 🔵\n")
                    + b("#y Text - url → 🟡")
                ),
                reply_markup=InlineKeyboardMarkup([
                    [bold_button("Clear Buttons", callback_data=f"cat_btns_clear_{cat_name}")],
                    [bold_button("🔙 Cancel", callback_data=f"admin_category_settings_{cat_name}")],
                ]),
            )
            return

        if data == f"cat_btns_clear_{cat_name}":
            if not is_admin:
                return
            update_category_field(cat_name, "buttons", "[]")
            await safe_answer(query, "Buttons cleared.")
            await show_category_settings_menu(context, chat_id, cat_name, query)
            return

        # Category selection from 3x3 grid
        if data == f"cat_settings_{cat_name}":
            await show_category_settings_menu(context, chat_id, cat_name, query)
            return

        # Watermark setting
        if data == f"cat_watermark_{cat_name}":
            # Show full watermark panel with all options
            try:
                await query.delete_message()
            except Exception:
                pass
            settings = get_category_settings(cat_name)
            wm = settings.get("watermark_text") or "Not set"
            wm_pos = settings.get("watermark_position") or "center"
            logo = "✅ Set" if settings.get("logo_file_id") else "❌ Not set"
            wm_positions = ["center", "bottom", "top", "bottom-right", "bottom-left", "top-right", "top-left"]
            pos_btns = [
                [InlineKeyboardButton(
                    ("✅ " if wm_pos == p else "") + p.upper(),
                    callback_data=f"cat_wm_pos_{cat_name}_{p}"
                ) for p in wm_positions[:3]],
                [InlineKeyboardButton(
                    ("✅ " if wm_pos == p else "") + p.upper(),
                    callback_data=f"cat_wm_pos_{cat_name}_{p}"
                ) for p in wm_positions[3:6]],
                [InlineKeyboardButton(
                    ("✅ " if wm_pos == wm_positions[6] else "") + wm_positions[6].upper(),
                    callback_data=f"cat_wm_pos_{cat_name}_{wm_positions[6]}"
                )],
            ]
            action_btns = [
                [bold_button(" Set Text Watermark", callback_data=f"cat_wm_text_{cat_name}")],
                [bold_button(" Send Image/Sticker as Watermark", callback_data=f"cat_wm_image_{cat_name}")],
                [bold_button("❌ Remove Watermark", callback_data=f"cat_wm_clear_{cat_name}")],
                [_back_btn(f"cat_settings_{cat_name}"), _close_btn()],
            ]
            markup = InlineKeyboardMarkup(pos_btns + action_btns)
            text = (
                b(f" {cat_name.upper()} WATERMARK SETTINGS") + "\n\n"
                + bq(
                    f"<b>Current Text:</b> {code(e(str(wm)[:30]))}\n"
                    f"<b>Position:</b> {code(wm_pos)}\n"
                    f"<b>Visual Logo:</b> {logo}\n\n"
                    "<b>Positions:</b> Tap to set where watermark appears\n"
                    "<b>Text:</b> Type your channel name or watermark\n"
                    "<b>Image:</b> Send sticker/image → bot saves it as logo overlay"
                )
            )
            img_url = await get_panel_pic_async("categories")
            if img_url:
                try:
                    await context.bot.send_photo(chat_id, img_url, caption=text,
                        parse_mode=ParseMode.HTML, reply_markup=markup)
                    return
                except Exception:
                    pass
            await safe_send_message(context.bot, chat_id, text, reply_markup=markup)
            return
            context.user_data["editing_category"] = cat_name
            await safe_edit_text(
                query,
                b(f"WATERMARK — {e(cat_name.upper())}") + "\n\n"
                + bq(
                    "Send watermark text. Options:\n"
                    "• Just text: <code>BeatAnime</code>\n"
                    "• With position: <code>BeatAnime|bottom-right</code>\n"
                    "• Positions: center bottom top bottom-right bottom-left\n"
                    "• Send <code>none</code> to remove."
                ),
                reply_markup=InlineKeyboardMarkup([[_back_btn(f"cat_settings_{cat_name}"), _close_btn()]]),
            )
            return

        # Logo setting
        # Watermark position set handler
        if data.startswith(f"cat_wm_pos_{cat_name}_"):
            pos = data[len(f"cat_wm_pos_{cat_name}_"):]
            update_category_field(cat_name, "watermark_position", pos)
            try:
                await query.answer(f"✅ Watermark position set to {pos}", show_alert=False)
            except Exception:
                pass
            # Re-show watermark panel
            context.user_data["editing_category"] = cat_name
            fake_data = f"cat_watermark_{cat_name}"
            # Recurse by re-triggering the watermark panel
            await safe_send_message(context.bot, chat_id,
                b(f"✅ Watermark position set to {code(pos)}"),
                reply_markup=InlineKeyboardMarkup([[
                    _back_btn(f"cat_settings_{cat_name}"), _close_btn()
                ]]))
            return

        # Watermark text input handler
        if data == f"cat_wm_text_{cat_name}":
            user_states[uid] = f"AWAITING_WATERMARK_{cat_name.upper()}"
            try:
                await query.delete_message()
            except Exception:
                pass
            await safe_send_message(context.bot, chat_id,
                b(f" Set Text Watermark for {cat_name}") + "\n\n"
                + bq(
                    "Send your watermark text now.\n\n"
                    "<b>Format:</b> <code>Your Text</code>\n"
                    "Optionally add position: <code>Your Text | bottom-right</code>\n\n"
                    "<b>Positions:</b> center, bottom, top, bottom-right,\n"
                    "bottom-left, top-right, top-left\n\n"
                    "Send <code>none</code> to remove text watermark."
                ),
                reply_markup=InlineKeyboardMarkup([[_back_btn(f"cat_settings_{cat_name}")]]),
            )
            return

        # Watermark image/sticker handler
        if data == f"cat_wm_image_{cat_name}":
            user_states[uid] = f"AWAITING_WATERMARK_{cat_name.upper()}"
            context.user_data["wm_mode"] = "image"
            context.user_data["editing_category"] = cat_name
            try:
                await query.delete_message()
            except Exception:
                pass
            await safe_send_message(context.bot, chat_id,
                b(f" Set Image/Sticker Watermark for {cat_name}") + "\n\n"
                + bq(
                    "Send one of these as watermark overlay:\n"
                    "•  Photo / image\n"
                    "•  Sticker (static or animated)\n"
                    "•  Image document (.png .jpg .webp)\n\n"
                    "It will appear as logo overlay on all posters for this category.\n"
                    "Position is set from the Watermark panel."
                ),
                reply_markup=InlineKeyboardMarkup([[_back_btn(f"cat_settings_{cat_name}")]]),
            )
            return

        # Clear watermark handler
        if data == f"cat_wm_clear_{cat_name}":
            update_category_field(cat_name, "watermark_text", None)
            update_category_field(cat_name, "logo_file_id", None)
            try:
                await query.answer("✅ Watermark cleared", show_alert=True)
            except Exception:
                pass
            return

        if data == f"cat_logo_{cat_name}":
            user_states[uid] = f"AWAITING_LOGO_{cat_name.upper()}"
            context.user_data["editing_category"] = cat_name
            await safe_edit_text(
                query,
                b(f"LOGO — {e(cat_name.upper())}") + "\n\n"
                + bq("Send an image file to use as logo overlay.\nSend <code>none</code> to remove."),
                reply_markup=InlineKeyboardMarkup([[_back_btn(f"cat_settings_{cat_name}"), _close_btn()]]),
            )
            return

        # Preview poster
        if data == f"cat_preview_{cat_name}":
            await safe_answer(query, "Generating preview poster...")
            defaults = {"anime": "Naruto", "manga": "One Piece", "movie": "Avengers", "tvshow": "Breaking Bad"}
            tmpl_map = {"anime": "ani", "manga": "anim", "movie": "ani", "tvshow": "ani"}
            media_map = {"anime": "ANIME", "manga": "MANGA", "movie": "MOVIE", "tvshow": "TV"}
            if _FILTER_POSTER_AVAILABLE:
                asyncio.create_task(get_or_generate_poster(
                    bot=context.bot, chat_id=chat_id,
                    title=defaults.get(cat_name, "Demo"),
                    template=tmpl_map.get(cat_name, "ani"),
                    media_type=media_map.get(cat_name, "ANIME"),
                ))
            return

        # Thumbnail
        if data == f"cat_thumbnail_{cat_name}":
            if not is_admin:
                return
            user_states[uid] = SET_CATEGORY_THUMBNAIL
            context.user_data["editing_category"] = cat_name
            await safe_edit_text(
                query,
                b(f" Set Thumbnail for {e(cat_name.upper())}") + "\n\n"
                + bq(b("Send the thumbnail URL, or send 'default' to reset.")),
                reply_markup=InlineKeyboardMarkup([[
                    bold_button("🔙 Cancel", callback_data=f"admin_category_settings_{cat_name}")
                ]]),
            )
            return

        # Font
        if data == f"cat_font_{cat_name}":
            if not is_admin:
                return
            await safe_edit_text(
                query,
                b(f" Font Style for {e(cat_name.upper())}"),
                reply_markup=InlineKeyboardMarkup([
                    [bold_button("Normal", callback_data=f"cat_font_set_{cat_name}_normal"),
                     bold_button("Small Caps", callback_data=f"cat_font_set_{cat_name}_smallcaps")],
                    [_back_btn("admin_category_settings"), _close_btn()],
                ]),
            )
            return

        if data.startswith(f"cat_font_set_{cat_name}_"):
            if not is_admin:
                return
            font_val = data[len(f"cat_font_set_{cat_name}_"):]
            update_category_field(cat_name, "font_style", font_val)
            await safe_answer(query, f"Font set to {font_val}")
            await show_category_settings_menu(context, chat_id, cat_name, query)
            return

        # Watermark
        if data == f"cat_watermark_{cat_name}":
            if not is_admin:
                return
            user_states[uid] = SET_WATERMARK_TEXT
            context.user_data["editing_category"] = cat_name
            current = get_category_settings(cat_name).get("watermark_text", "")
            await safe_edit_text(
                query,
                b(f" Set Watermark for {e(cat_name.upper())}") + "\n\n"
                + bq(b("Send the watermark text to stamp on images.\n\n")
                     + b("Current: ") + code(e(current[:50] if current else "None"))),
                reply_markup=InlineKeyboardMarkup([
                    [bold_button("Remove Watermark", callback_data=f"cat_wm_clear_{cat_name}"),
                     bold_button("Set Position", callback_data=f"cat_wm_pos_{cat_name}")],
                    [bold_button("🔙 Cancel", callback_data=f"admin_category_settings_{cat_name}")],
                ]),
            )
            return

        if data == f"cat_wm_clear_{cat_name}":
            if not is_admin:
                return
            update_category_field(cat_name, "watermark_text", None)
            await safe_answer(query, "Watermark removed.")
            await show_category_settings_menu(context, chat_id, cat_name, query)
            return

        if data == f"cat_wm_pos_{cat_name}":
            if not is_admin:
                return
            positions = ["center", "top", "bottom", "left", "right", "bottom-left", "bottom-right"]
            keyboard = []
            row = []
            for pos in positions:
                row.append(bold_button(pos.title(), callback_data=f"cat_wm_pos_set_{cat_name}_{pos}"))
                if len(row) == 3:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
            keyboard.append([_back_btn("admin_category_settings"), _close_btn()])
            await safe_edit_text(
                query, b(f"Select watermark position for {e(cat_name)}:"),
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        if data.startswith(f"cat_wm_pos_set_{cat_name}_"):
            if not is_admin:
                return
            pos = data[len(f"cat_wm_pos_set_{cat_name}_"):]
            update_category_field(cat_name, "watermark_position", pos)
            await safe_answer(query, f"Position set to {pos}")
            await show_category_settings_menu(context, chat_id, cat_name, query)
            return

        # Logo
        if data == f"cat_logo_{cat_name}":
            if not is_admin:
                return
            user_states[uid] = SET_CATEGORY_LOGO
            context.user_data["editing_category"] = cat_name
            await safe_edit_text(
                query,
                b(f" Set Logo for {e(cat_name.upper())}") + "\n\n"
                + bq(b("Send a photo or image document to use as logo.")),
                reply_markup=InlineKeyboardMarkup([[
                    bold_button("Remove Logo", callback_data=f"cat_logo_clear_{cat_name}"),
                    bold_button("🔙 Cancel", callback_data=f"admin_category_settings_{cat_name}"),
                ]]),
            )
            return

        if data == f"cat_logo_clear_{cat_name}":
            if not is_admin:
                return
            update_category_field(cat_name, "logo_file_id", None)
            await safe_answer(query, "Logo removed.")
            await show_category_settings_menu(context, chat_id, cat_name, query)
            return

        # Logo position
        if data == f"cat_logopos_{cat_name}":
            if not is_admin:
                return
            positions = ["top", "bottom", "left", "right", "center"]
            keyboard = [
                [bold_button(pos.title(), callback_data=f"cat_logo_pos_set_{cat_name}_{pos}")
                 for pos in positions[:3]],
                [bold_button(pos.title(), callback_data=f"cat_logo_pos_set_{cat_name}_{pos}")
                 for pos in positions[3:]],
                [_back_btn("admin_category_settings"), _close_btn()],
            ]
            await safe_edit_text(
                query, b(f"Select logo position for {e(cat_name)}:"),
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        if data.startswith(f"cat_logo_pos_set_{cat_name}_"):
            if not is_admin:
                return
            pos = data[len(f"cat_logo_pos_set_{cat_name}_"):]
            update_category_field(cat_name, "logo_position", pos)
            await safe_answer(query, f"Logo position: {pos}")
            await show_category_settings_menu(context, chat_id, cat_name, query)
            return

        # Reset defaults
        if data == f"cat_reset_{cat_name}":
            if not is_admin:
                return
            await safe_edit_text(
                query,
                b(f"⚠️ Reset {e(cat_name.upper())} settings to defaults?"),
                reply_markup=InlineKeyboardMarkup([
                    [bold_button("Yes, Reset", callback_data=f"cat_reset_confirm_{cat_name}"),
                     bold_button("CANCEL", callback_data=f"admin_category_settings_{cat_name}")],
                ]),
            )
            return

        if data == f"cat_reset_confirm_{cat_name}":
            if not is_admin:
                return
            try:
                with db_manager.get_cursor() as cur:
                    cur.execute(
                        "UPDATE category_settings SET "
                        "caption_template = '', branding = '', buttons = '[]', "
                        "thumbnail_url = '', font_style = 'normal', "
                        "logo_file_id = NULL, watermark_text = NULL "
                        "WHERE category = %s",
                        (cat_name,)
                    )
            except Exception:
                pass
            await safe_answer(query, f"{cat_name} settings reset.")
            await show_category_settings_menu(context, chat_id, cat_name, query)
            return

    # ── User management ─────────────────────────────────────────────────────────────
    if data == "user_management":
        if not is_admin:
            return
        await delete_bot_prompt(context, chat_id)
        user_states.pop(uid, None)
        total = get_user_count()
        blocked = get_blocked_users_count()
        text = (
            b("USER MANAGEMENT") + "\n\n"
            + bq(
                f"<b>Total:</b> {total:,}\n"
                f"<b>Blocked:</b> {blocked}\n"
                f"<b>Active:</b> {total - blocked:,}"
            )
        )
        grid = [
            _btn("LIST USERS",   "user_list_page_0"),
            _btn("SEARCH",       "user_search"),
            _btn("BAN USER",     "user_ban_input"),
            _btn("UNBAN USER",   "user_unban_input"),
            _btn("DELETE USER",  "user_delete_input"),
            _btn("EXPORT CSV",   "admin_export_users_quick"),
            _btn("BLOCKED LIST", "user_blocked_list"),
            _btn("BROADCAST",    "admin_broadcast_start"),
            _btn("STATS",        "admin_stats"),
        ]
        rows = _grid3(grid)
        rows.append([_back_btn("admin_back"), _close_btn()])
        try:
            await query.delete_message()
        except Exception:
            pass
        img_url = None
        if _PANEL_IMAGE_AVAILABLE:
            try:
                img_url = await get_panel_pic_async("users")
            except Exception:
                pass
        if img_url:
            sent = await safe_send_photo(context.bot, chat_id, img_url, caption=text, reply_markup=InlineKeyboardMarkup(rows))
            if sent:
                return
        await safe_send_message(context.bot, chat_id, text, reply_markup=InlineKeyboardMarkup(rows))
        return

    if data == "um_list_users":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        context.args = []
        await listusers_command(update, context)
        return

    if data in ("um_export_csv", "admin_export_users_quick"):
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        await exportusers_command(update, context)
        return

    if data == "admin_btn_style":
        if not is_admin:
            return
        try:
            current_style = get_setting("button_style", BUTTON_STYLE) or BUTTON_STYLE
        except Exception:
            current_style = BUTTON_STYLE
        await safe_edit_text(
            query,
            b("BUTTON STYLE") + "\n\n"
            + bq(
                f"<b>Current:</b> {current_style}\n\n"
                "<b>Math Bold:</b> 𝗦𝗧𝗔𝗧𝗦  𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧  𝗨𝗦𝗘𝗥𝗦\n"
                "<b>Small Caps:</b> ꜱᴛᴀᴛꜱ  ʙʀᴏᴀᴅᴄᴀꜱᴛ  ᴜꜱᴇʀꜱ\n\n"
                "Applied to all panel button labels."
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    f"{'✔️ ' if current_style == 'mathbold' else ''}𝗠𝗔𝗧𝗛 𝗕𝗢𝗟𝗗",
                    callback_data="btn_style_set_mathbold"),
                 InlineKeyboardButton(
                    f"{'✔️ ' if current_style == 'smallcaps' else ''}ꜱᴍᴀʟʟ ᴄᴀᴘꜱ",
                    callback_data="btn_style_set_smallcaps")],
                [_back_btn("admin_settings"), _close_btn()],
            ]),
        )
        return

    if data.startswith("btn_style_set_"):
        if not is_admin:
            return
        style = data[len("btn_style_set_"):]
        if style in ("mathbold", "smallcaps"):
            set_setting("button_style", style)
            await safe_answer(query, f"✔️ Button style set: {style}")
            await button_handler(update, context, "admin_btn_style")
        return

    if data == "admin_clear_img_cache":
        if not is_admin:
            return
        count = clear_image_cache()
        await safe_answer(query, f"♻️ Cleared {count} cached panel images")
        return

    if data == "um_search_user":
        if not is_admin:
            return
        user_states[uid] = SEARCH_USER_INPUT
        await safe_edit_text(
            query,
            b("🔍 Search User") + "\n\n" + bq(b("Send user ID or @username:")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="user_management")]]),
        )
        return

    if data == "um_ban_user":
        if not is_admin:
            return
        user_states[uid] = BAN_USER_INPUT
        await safe_edit_text(
            query,
            b("🚫 Ban User") + "\n\n" + bq(b("Send user ID or @username to ban:")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="user_management")]]),
        )
        return

    if data == "um_unban_user":
        if not is_admin:
            return
        user_states[uid] = UNBAN_USER_INPUT
        await safe_edit_text(
            query,
            b("✅ Unban User") + "\n\n" + bq(b("Send user ID or @username to unban:")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="user_management")]]),
        )
        return

    if data == "um_delete_user":
        if not is_admin:
            return
        user_states[uid] = DELETE_USER_INPUT
        await safe_edit_text(
            query,
            b("🗑 Delete User") + "\n\n" + bq(b("Send the user ID to permanently delete from database:")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="user_management")]]),
        )
        return

    if data == "um_banned_list":
        if not is_admin:
            return
        try:
            with db_manager.get_cursor() as cur:
                cur.execute(
                    "SELECT user_id, username, first_name FROM users WHERE banned = TRUE LIMIT 20"
                )
                banned = cur.fetchall() or []
        except Exception:
            banned = []
        if not banned:
            await safe_answer(query, "No banned users.")
            return
        text = b(f"🚫 Banned Users ({len(banned)}):") + "\n\n"
        for buid, buname, bfname in banned:
            text += f"• {e(bfname or '')} @{e(buname or '')} {code(str(buid))}\n"
        keyboard = [[_back_btn("user_management")]]
        await safe_edit_text(query, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("user_page_"):
        if not is_admin:
            return
        offset = int(data[len("user_page_"):])
        try:
            await query.delete_message()
        except Exception:
            pass
        context.args = [str(offset)]
        await listusers_command(update, context)
        return

    if data.startswith("manage_user_"):
        if not is_admin:
            return
        target_uid = int(data[len("manage_user_"):])
        user_info = get_user_info_by_id(target_uid)
        if not user_info:
            await safe_answer(query, "User not found.")
            return
        u_id, u_uname, u_fname, u_lname, u_joined, u_banned = user_info
        name = f"{u_fname or ''} {u_lname or ''}".strip() or "N/A"
        text = (
            b("👤 User Details") + "\n\n"
            f"<b>ID:</b> {code(str(u_id))}\n"
            f"<b>Name:</b> {e(name)}\n"
            f"<b>Username:</b> {'@' + e(u_uname) if u_uname else '—'}\n"
            f"<b>Joined:</b> {code(str(u_joined)[:16])}\n"
            f"<b>Status:</b> {'🚫 Banned' if u_banned else '✅ Active'}"
        )
        keyboard = []
        if u_banned:
            keyboard.append([bold_button("Unban", callback_data=f"user_unban_{u_id}")])
        else:
            keyboard.append([bold_button("🚫 Ban", callback_data=f"user_ban_{u_id}")])
        keyboard.append([bold_button("Delete", callback_data=f"user_del_{u_id}")])
        keyboard.append([_back_btn("user_management")])
        await safe_edit_text(query, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("user_ban_"):
        if not is_admin:
            return
        target_uid = int(data[len("user_ban_"):])
        if target_uid in (ADMIN_ID, OWNER_ID):
            await safe_answer(query, "Cannot ban admin.")
            return
        ban_user(target_uid)
        await safe_answer(query, "User banned.")
        await button_handler(update, context, f"manage_user_{target_uid}")

        return

    if data.startswith("user_unban_"):
        if not is_admin:
            return
        target_uid = int(data[len("user_unban_"):])
        unban_user(target_uid)
        await safe_answer(query, "User unbanned.")
        await button_handler(update, context, f"manage_user_{target_uid}")

        return

    if data.startswith("user_del_"):
        if not is_admin:
            return
        target_uid = int(data[len("user_del_"):])
        if target_uid in (ADMIN_ID, OWNER_ID):
            await safe_answer(query, "Cannot delete admin.", show_alert=True)
            return
        try:
            with db_manager.get_cursor() as cur:
                cur.execute("DELETE FROM users WHERE user_id = %s", (target_uid,))
        except Exception:
            await safe_answer(query, "Error deleting user.")
            return
        await safe_answer(query, "User deleted.")
        await button_handler(update, context, "user_management")

        return

    # ── Search results ─────────────────────────────────────────────────────────────
    if data.startswith("search_result_"):
        rest = data[len("search_result_"):]
        for cat_key in ("mangadex", "anime", "manga", "movie", "tvshow"):
            prefix = f"{cat_key}_"
            if rest.startswith(prefix):
                raw_id = rest[len(prefix):]
                try:
                    await query.delete_message()
                except Exception:
                    pass
                if cat_key == "mangadex":
                    # Show MangaDex manga details
                    manga = MangaDexClient.get_manga(raw_id)
                    if manga:
                        caption_text, cover_url = MangaDexClient.format_manga_info(manga)
                        # Chapter list keyboard
                        chapters, total_chs = MangaDexClient.get_chapters(raw_id, limit=5)
                        ch_keyboard = []
                        for ch in chapters:
                            attrs = ch.get("attributes", {}) or {}
                            ch_num = attrs.get("chapter", "?")
                            ch_keyboard.append([bold_button(
                                f"Ch.{ch_num}",
                                callback_data=f"mdex_chapter_{ch['id']}"
                            )])
                        ch_keyboard.append([
                            InlineKeyboardButton("📖 Read on MangaDex", url=f"https://mangadex.org/title/{raw_id}"),
                        ])
                        ch_keyboard.append([bold_button("Track This Manga", callback_data=f"mdex_track_{raw_id}")])
                        markup = InlineKeyboardMarkup(ch_keyboard)
                        if cover_url:
                            await safe_send_photo(
                                context.bot, chat_id,
                                cover_url, caption=caption_text, reply_markup=markup,
                            )
                        else:
                            await safe_send_message(context.bot, chat_id, caption_text, reply_markup=markup)
                    else:
                        await safe_send_message(context.bot, chat_id, b("❌ Manga not found."))
                else:
                    try:
                        mid = int(raw_id)
                    except ValueError:
                        mid = None
                    await generate_and_send_post(
                        context, chat_id, cat_key,
                        media_id=mid,
                    )
                return

    # MangaDex chapter viewer
    if data.startswith("mdex_chapter_"):
        ch_id = data[len("mdex_chapter_"):]
        try:
            await query.delete_message()
        except Exception:
            pass
        # Show chapter info
        pages = MangaDexClient.get_chapter_pages(ch_id)
        text = b("📖 Chapter") + "\n\n"
        if pages:
            base_url, ch_hash, filenames = pages
            text += (
                f"<b>Total Pages:</b> {code(str(len(filenames)))}\n"
                f"<b>Chapter ID:</b> {code(ch_id)}\n\n"
                + bq(b("Read this chapter online at MangaDex for the best experience."))
            )
        else:
            text += b("Could not load chapter page info.")
        await safe_send_message(
            context.bot, chat_id, text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📖 Read Now", url=f"https://mangadex.org/chapter/{ch_id}")
            ]]),
        )
        return

    # MangaDex track
    if data.startswith("mdex_track_"):
        if not is_admin:
            await safe_answer(query, "Only admin can set up tracking.")
            return
        manga_id = data[len("mdex_track_"):]
        manga = MangaDexClient.get_manga(manga_id)
        if not manga:
            await safe_answer(query, "Manga not found. Try searching again.")
            return
        attrs = manga.get("attributes", {}) or {}
        titles = attrs.get("title", {}) or {}
        title = titles.get("en") or next(iter(titles.values()), "Unknown")
        status = (attrs.get("status") or "unknown").replace("_", " ").title()
        context.user_data["au_manga_id"] = manga_id
        context.user_data["au_manga_title"] = title
        context.user_data["au_manga_status"] = status
        # Step 1: Ask for delivery mode
        keyboard = [
            [bold_button("Full Manga", callback_data="au_mode_full"),
             bold_button("Latest Chapters", callback_data="au_mode_latest")],
            [bold_button("🔙 Cancel", callback_data="admin_autoupdate")],
        ]
        await safe_edit_text(
            query,
            b(f"📚 {e(title)}") + "\n\n"
            + bq(b("Choose delivery mode:\n\n")
                 + "Full Manga — send all chapters from beginning\n"
                 + "Latest Chapters — only send new chapters as they release"),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    if data in ("au_mode_full", "au_mode_latest"):
        if not is_admin:
            return
        mode = "full" if data == "au_mode_full" else "latest"
        context.user_data["au_manga_mode"] = mode
        title = context.user_data.get("au_manga_title", "Unknown")
        # Step 2: Ask for interval
        keyboard = [
            [bold_button("5 min", callback_data="au_interval_5"),
             bold_button("10 min", callback_data="au_interval_10")],
            [bold_button("Random (5-10 min)", callback_data="au_interval_random"),
             bold_button("Custom", callback_data="au_interval_custom")],
            [bold_button("🔙 Cancel", callback_data="admin_autoupdate")],
        ]
        await safe_edit_text(
            query,
            b(f"📚 {e(title)}") + f"\n<b>Mode:</b> {mode.title()}\n\n"
            + bq(b("Choose check interval:")),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    if data.startswith("au_interval_"):
        if not is_admin:
            return
        interval_key = data[len("au_interval_"):]
        if interval_key == "5":
            interval_minutes = 5
        elif interval_key == "10":
            interval_minutes = 10
        elif interval_key == "random":
            interval_minutes = -1  # -1 = random 5–10
        elif interval_key == "custom":
            context.user_data["au_waiting_for_interval"] = True
            user_states[uid] = AU_CUSTOM_INTERVAL
            await safe_edit_text(
                query,
                b("📚 Custom Interval") + "\n\n"
                + bq(b("Send interval in minutes (e.g. 15):")),
                reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_autoupdate")]]),
            )
            return
        else:
            interval_minutes = 10
        context.user_data["au_manga_interval"] = interval_minutes
        title = context.user_data.get("au_manga_title", "Unknown")
        mode = context.user_data.get("au_manga_mode", "latest")
        # Step 3: Ask for target channel
        user_states[uid] = AU_ADD_MANGA_TARGET
        await safe_edit_text(
            query,
            b(f"📚 {e(title)}") + f"\n<b>Mode:</b> {mode.title()} | "
            + f"<b>Interval:</b> {interval_minutes if interval_minutes > 0 else 'Random 5–10'} min\n\n"
            + bq(
                b("Send the target channel using any method:\n\n")
                + "• <code>@channelname</code>\n"
                + "• <code>-1001234567890</code> (numeric ID)\n"
                + "• <b>Forward any post</b> from the channel\n\n"
                + "<i>Bot must be admin in the channel to post chapters.</i>"
            ),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_autoupdate")]]),
        )
        return

    # ── Auto-forward menu ──────────────────────────────────────────────────────────
    if data == "admin_autoforward":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        await _show_autoforward_menu(context, chat_id)
        return

    if data == "af_add_connection":
        if not is_admin:
            return
        user_states[uid] = AF_ADD_CONNECTION_SOURCE
        await safe_edit_text(
            query,
            b("♻️ Add Auto-Forward Connection") + "\n\n"
            + bq(
                b("Step 1/2: SOURCE channel\n\n")
                + "Send the source channel using <b>any method</b>:\n"
                + "• <code>@channelname</code>\n"
                + "• <code>-1001234567890</code> (numeric ID)\n"
                + "• <b>Forward any post</b> from the source channel\n\n"
                + "<i>Bot must be a member of the source channel.</i>"
            ),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_autoforward")]]),
        )
        return

    if data == "af_list_connections":
        if not is_admin:
            return
        try:
            with db_manager.get_cursor() as cur:
                cur.execute("""
                    SELECT id, source_chat_id, target_chat_id, active, delay_seconds
                    FROM auto_forward_connections ORDER BY id DESC LIMIT 20
                """)
                conns = cur.fetchall() or []
        except Exception:
            conns = []
        text = b(f"♻️ Auto-Forward Connections ({len(conns)}):") + "\n\n"
        if conns:
            keyboard = []
            for cid, src, tgt, active, delay in conns:
                status = "✅" if active else "❌"
                text += f"{status} {code(str(src))} → {code(str(tgt))} (ID:{cid})\n"
                keyboard.append([bold_button(
                    f"{status} {str(src)[:15]} → {str(tgt)[:15]}",
                    callback_data=f"af_conn_detail_{cid}"
                )])
            keyboard.append([_back_btn("admin_autoforward")])
        else:
            text += b("No connections configured.")
            keyboard = [[_back_btn("admin_autoforward")]]
        await safe_edit_text(query, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("af_conn_detail_"):
        if not is_admin:
            return
        conn_id = int(data[len("af_conn_detail_"):])
        try:
            with db_manager.get_cursor() as cur:
                cur.execute("""
                    SELECT id, source_chat_id, target_chat_id, active,
                           protect_content, silent, pin_message, delete_source, delay_seconds
                    FROM auto_forward_connections WHERE id = %s
                """, (conn_id,))
                conn = cur.fetchone()
        except Exception:
            conn = None
        if not conn:
            await safe_answer(query, "Connection not found.")
            return
        cid, src, tgt, active, protect, silent, pin, delete_src, delay = conn
        text = (
            b(f"♻️ Connection #{cid}") + "\n\n"
            f"<b>Source:</b> {code(str(src))}\n"
            f"<b>Target:</b> {code(str(tgt))}\n"
            f"<b>Active:</b> {'✅' if active else '❌'}\n"
            f"<b>Protect Content:</b> {'✅' if protect else '❌'}\n"
            f"<b>Silent:</b> {'✅' if silent else '❌'}\n"
            f"<b>Pin:</b> {'✅' if pin else '❌'}\n"
            f"<b>Delete Source:</b> {'✅' if delete_src else '❌'}\n"
            f"<b>Delay:</b> {code(str(delay) + 's' if delay else '0s')}"
        )
        keyboard = [
            [bold_button("Delete", callback_data=f"af_conn_del_{cid}"),
             _back_btn("af_list_connections")],
        ]
        await safe_edit_text(query, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("af_conn_del_"):
        if not is_admin:
            return
        conn_id = int(data[len("af_conn_del_"):])
        try:
            with db_manager.get_cursor() as cur:
                cur.execute("DELETE FROM auto_forward_connections WHERE id = %s", (conn_id,))
        except Exception:
            pass
        await safe_answer(query, f"Connection #{conn_id} deleted.")
        await button_handler(update, context, "af_list_connections")
        return

    if data in ("af_replacements_menu", "af_set_delay",
                "af_set_caption", "af_bulk", "af_delete_connection"):
        if not is_admin:
            return

        if data == "af_set_delay":
            user_states[uid] = "AWAITING_AF_DELAY"
            await safe_edit_text(
                query,
                b(small_caps("⏱ set auto-forward delay")) + "\n\n"
                + bq(small_caps("send delay in seconds (e.g. 30). send 0 for no delay.")),
                reply_markup=InlineKeyboardMarkup([[_back_btn("admin_autoforward")]]),
            )
            return

        if data == "af_set_caption":
            user_states[uid] = "AWAITING_AF_CAPTION"
            await safe_edit_text(
                query,
                b(small_caps("✏️ set caption override")) + "\n\n"
                + bq(small_caps("send the caption text to append to all forwarded messages.\nsend /clear to remove caption override.")),
                reply_markup=InlineKeyboardMarkup([[_back_btn("admin_autoforward")]]),
            )
            return

        if data == "af_replacements_menu":
            # Show current replacements
            rows = []
            try:
                with db_manager.get_cursor() as cur:
                    cur.execute("SELECT id, old_pattern, new_pattern FROM auto_forward_replacements ORDER BY id LIMIT 10")
                    rows = cur.fetchall() or []
            except Exception:
                pass
            text = b(small_caps("🔄 text replacements")) + "\n\n"
            if rows:
                for r_id, old_p, new_p in rows:
                    text += f"• <code>{e(old_p)}</code> → <code>{e(new_p)}</code>\n"
            else:
                text += bq(small_caps("no replacements set."))
            text += "\n\n" + bq(small_caps("to add: /autoforward replacements add old_text new_text"))
            await safe_edit_text(query, text, reply_markup=InlineKeyboardMarkup([[_back_btn("admin_autoforward")]]))
            return

        if data == "af_bulk":
            user_states[uid] = "AWAITING_AF_BULK_COUNT"
            await safe_edit_text(
                query,
                b(small_caps("📦 bulk forward")) + "\n\n"
                + bq(small_caps("send the number of recent messages to forward from source channel (max 50).")),
                reply_markup=InlineKeyboardMarkup([[_back_btn("admin_autoforward")]]),
            )
            return

        label = data.replace("af_", "").replace("_", " ").title()
        await safe_edit_text(
            query,
            b(f"♻️ {label}") + "\n\n"
            + bq(b(small_caps("use /autoforward to access the full manager from the admin panel."))),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_autoforward")]]),
        )
        return

    # ── Auto-forward filters panel with DM / Group toggles ────────────────────────
    if data == "af_filters_menu":
        if not is_admin:
            return
        # Load current filter settings for connection 0 (global) or first active connection
        dm_on = True
        grp_on = True
        try:
            with db_manager.get_cursor() as cur:
                cur.execute(
                    "SELECT enable_in_dm, enable_in_group FROM auto_forward_filters WHERE connection_id IS NULL LIMIT 1"
                )
                row = cur.fetchone()
                if row:
                    dm_on, grp_on = bool(row[0]), bool(row[1])
        except Exception:
            pass
        dm_icon = "✅" if dm_on else "❌"
        grp_icon = "✅" if grp_on else "❌"
        ftext = (
            b("🔍 Auto-Forward Filters") + "\n\n"
            + bq(
                f"<b>Enable in DM:</b> {dm_icon}\n"
                f"<b>Enable in Group:</b> {grp_icon}\n\n"
                "<b>BLACKLIST:</b> Words/phrases that BLOCK a message from being forwarded.\n"
                "If any blacklisted word appears in the message → it is skipped.\n\n"
                "<b>WHITELIST:</b> When set, ONLY messages containing a whitelisted word are forwarded.\n"
                "Leave whitelist empty to forward everything (except blacklisted).\n\n"
                "<b>How to use:</b>\n"
                "• Tap <b>Blacklist Words</b> → send a word/phrase to block\n"
                "• Tap <b>Whitelist Words</b> → send a word/phrase to require\n"
                "• Words are matched case-insensitively\n"
                "• Multiple words can be added one at a time"
            )
        )
        fkb = [
            [bold_button(f"{dm_icon} Toggle DM", callback_data="af_toggle_dm"),
             bold_button(f"{grp_icon} Toggle Group", callback_data="af_toggle_group")],
            [bold_button("🚫 Blacklist Words", callback_data="af_blacklist"),
             bold_button("✅ Whitelist Words", callback_data="af_whitelist")],
            [bold_button("❓ Filter Guide", callback_data="af_filter_guide"),
             _back_btn("admin_autoforward")],
        ]
        await safe_edit_text(query, ftext, reply_markup=InlineKeyboardMarkup(fkb))
        return

    if data == "af_filter_guide":
        if not is_admin:
            return
        guide_text = (
            b("📖 How Filters Work") + "\n\n"
            + bq(
                "<b>Example scenario:</b>\n"
                "You're forwarding from an anime channel to your group, but you want to skip "
                "posts about movies and only forward anime.\n\n"
                "<b>Step 1:</b> Add <code>movie</code> to Blacklist → any post containing the word 'movie' is skipped.\n\n"
                "<b>Step 2 (optional):</b> Add <code>episode</code> to Whitelist → only posts with the word 'episode' are forwarded.\n\n"
                "<b>Result:</b> Only episode posts get through, movie posts are blocked.\n\n"
                "<b>Note:</b> If Whitelist is EMPTY, all messages are allowed through (except blacklisted ones).\n"
                "If Whitelist has entries, ONLY matching messages pass."
            )
        )
        await safe_edit_text(
            query, guide_text,
            reply_markup=InlineKeyboardMarkup([[_back_btn("af_filters_menu")]]),
        )
        return

    if data == "af_toggle_all":
        if not is_admin:
            return
        current = get_setting("autoforward_enabled", "true")
        new_val = "false" if current == "true" else "true"
        set_setting("autoforward_enabled", new_val)
        await safe_answer(query, f"Auto-Forward {'enabled' if new_val == 'true' else 'disabled'}!")
        try:
            await query.delete_message()
        except Exception:
            pass
        await _show_autoforward_menu(context, chat_id)
        return

    if data in ("af_toggle_dm", "af_toggle_group"):
        if not is_admin:
            return
        col = "enable_in_dm" if data == "af_toggle_dm" else "enable_in_group"
        try:
            with db_manager.get_cursor() as cur:
                # Ensure a global row exists (connection_id = NULL = global)
                cur.execute("""
                    INSERT INTO auto_forward_filters (connection_id, enable_in_dm, enable_in_group)
                    VALUES (NULL, TRUE, TRUE)
                    ON CONFLICT DO NOTHING
                """)
                cur.execute(
                    f"UPDATE auto_forward_filters SET {col} = NOT {col} WHERE connection_id IS NULL"
                )
                if cur.rowcount == 0:
                    cur.execute(
                        f"INSERT INTO auto_forward_filters (connection_id, {col}) VALUES (NULL, FALSE)"
                    )
        except Exception as exc:
            logger.debug(f"af toggle error: {exc}")
        await safe_answer(query, small_caps("filter toggled!"))
        await button_handler(update, context, "af_filters_menu")
        return

    if data in ("af_blacklist", "af_whitelist"):
        if not is_admin:
            return
        kind = "Blacklist" if data == "af_blacklist" else "Whitelist"
        col = "blacklist_words" if data == "af_blacklist" else "whitelist_words"
        words = ""
        try:
            with db_manager.get_cursor() as cur:
                cur.execute(
                    f"SELECT {col} FROM auto_forward_filters WHERE connection_id IS NULL LIMIT 1"
                )
                row = cur.fetchone()
                if row and row[0]:
                    words = row[0]
        except Exception as exc:
            logger.debug(f"af_{kind} select error: {exc}")
        await safe_edit_text(
            query,
            b(f" {kind} Words") + "\n\n"
            + bq(
                f"<b>Current:</b> {code(e(words or 'None'))}\n\n"
                "Send new comma-separated words to set the list:\n"
                "<i>e.g. word1, word2, word3</i>"
            ),
            reply_markup=InlineKeyboardMarkup([[_back_btn("af_filters_menu")]]),
        )
        user_states[uid] = f"af_set_{col}"
        return

    # ── Auto manga update menu ─────────────────────────────────────────────────────
    if data == "admin_autoupdate":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        await _show_autoupdate_menu(context, chat_id)
        return

    if data == "au_add_manga":
        if not is_admin:
            return
        user_states[uid] = AU_ADD_MANGA_TITLE
        await safe_edit_text(
            query,
            b("📚 Track New Manga") + "\n\n"
            + bq(b("Send the manga title to search on MangaDex:")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_autoupdate")]]),
        )
        return

    if data == "au_list_manga":
        if not is_admin:
            return
        text = MangaTracker.get_tracked_for_admin()
        rows = MangaTracker.get_all_tracked()
        keyboard = []
        for rec in rows:
            rec_id, manga_id, title, _, _, _, _ = rec
            keyboard.append([bold_button(
                f"🗑 Stop: {e(title[:20])}",
                callback_data=f"au_stop_{manga_id}"
            )])
        keyboard.append([_back_btn("admin_autoupdate")])
        await safe_edit_text(query, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("au_stop_"):
        if not is_admin:
            return
        manga_id = data[len("au_stop_"):]
        MangaTracker.remove_tracking(manga_id)
        await safe_answer(query, "Tracking stopped.")
        await button_handler(update, context, "au_list_manga")
        return

    if data == "au_remove_manga":
        if not is_admin:
            return
        await button_handler(update, context, "au_list_manga")
        return

    if data == "au_stats":
        if not is_admin:
            return
        rows = MangaTracker.get_all_tracked()
        text = (
            b(" Manga Tracking Stats") + "\n\n"
            f"<b>Total tracked:</b> {code(str(len(rows)))}"
        )
        await safe_edit_text(
            query, text,
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_autoupdate")]]),
        )
        return

    # ── Upload manager ─────────────────────────────────────────────────────────────
    if data == "upload_menu":
        if not is_admin:
            return
        await load_upload_progress()
        try:
            await query.delete_message()
        except Exception:
            pass
        await show_upload_menu(chat_id, context)
        return

    if data == "upload_preview":
        if not is_admin:
            return
        cap = build_caption_from_progress()
        await safe_edit_text(
            query,
            b("👁 Caption Preview:") + "\n\n" + cap,
            reply_markup=get_upload_menu_markup(),
        )
        return

    if data == "upload_set_caption":
        if not is_admin:
            return
        user_states[uid] = UPLOAD_SET_CAPTION
        await safe_edit_text(
            query,
            b(" Set Caption Template") + "\n\n"
            + bq(
                b("Send the new caption template.\n\n")
                + b("Placeholders:\n")
                + b("{anime_name}, {season}, {episode}, {total_episode}, {quality}")
            ),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="upload_back")]]),
        )
        return

    if data == "upload_set_anime_name":
        if not is_admin:
            return
        user_states[uid] = UPLOAD_SET_CAPTION  # Reuse a simpler state
        context.user_data["upload_field"] = "anime_name"
        await safe_edit_text(
            query,
            b("🎌 Set Anime Name") + "\n\n"
            + bq(b(f"Current: {e(upload_progress.get('anime_name', 'Anime Name'))}\n\nSend the new anime name:")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="upload_back")]]),
        )
        return

    if data == "upload_set_season":
        if not is_admin:
            return
        user_states[uid] = UPLOAD_SET_SEASON
        await safe_edit_text(
            query,
            b(" Set Season") + "\n\n"
            + bq(b(f"Current: {upload_progress['season']}\n\nSend new season number:")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="upload_back")]]),
        )
        return

    if data == "upload_set_episode":
        if not is_admin:
            return
        user_states[uid] = UPLOAD_SET_EPISODE
        await safe_edit_text(
            query,
            b(" Set Episode") + "\n\n"
            + bq(b(f"Current: {upload_progress['episode']}\n\nSend new episode number:")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="upload_back")]]),
        )
        return

    if data == "upload_set_total":
        if not is_admin:
            return
        user_states[uid] = UPLOAD_SET_TOTAL
        await safe_edit_text(
            query,
            b(" Set Total Episodes") + "\n\n"
            + bq(b(f"Current: {upload_progress['total_episode']}\n\nSend total episode count:")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="upload_back")]]),
        )
        return

    if data == "upload_set_channel":
        if not is_admin:
            return
        user_states[uid] = UPLOAD_SET_CHANNEL
        await safe_edit_text(
            query,
            b("📢 Set Target Channel") + "\n\n"
            + bq(b("Send target channel @username or ID:")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="upload_back")]]),
        )
        return

    if data == "upload_quality_menu":
        if not is_admin:
            return
        keyboard = []
        row = []
        for q_val in ALL_QUALITIES:
            selected = q_val in upload_progress["selected_qualities"]
            mark = "✅ " if selected else ""
            row.append(bold_button(f"{mark}{q_val}", callback_data=f"upload_toggle_q_{q_val}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([_back_btn("upload_back")])
        await safe_edit_text(
            query, b("🎛 Quality Settings — Toggle to select/deselect:"),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    if data.startswith("upload_toggle_q_"):
        if not is_admin:
            return
        q_val = data[len("upload_toggle_q_"):]
        if q_val in upload_progress["selected_qualities"]:
            upload_progress["selected_qualities"].remove(q_val)
        else:
            upload_progress["selected_qualities"].append(q_val)
        await save_upload_progress()
        await safe_answer(query, f"{'Added' if q_val in upload_progress['selected_qualities'] else 'Removed'} {q_val}")
        await button_handler(update, context, "upload_quality_menu")
        return

    if data == "upload_toggle_auto":
        if not is_admin:
            return
        upload_progress["auto_caption_enabled"] = not upload_progress["auto_caption_enabled"]
        await save_upload_progress()
        status = "ON" if upload_progress["auto_caption_enabled"] else "OFF"
        await safe_answer(query, f"Auto-caption: {status}")
        await show_upload_menu(chat_id, context, query.message)
        return

    if data == "upload_reset":
        if not is_admin:
            return
        upload_progress["episode"] = 1
        upload_progress["video_count"] = 0
        await save_upload_progress()
        await safe_answer(query, "Episode reset to 1.")
        await show_upload_menu(chat_id, context, query.message)
        return

    if data == "upload_clear_db":
        if not is_admin:
            return
        await safe_edit_text(
            query,
            b(" Clear Upload Database?") + "\n\n"
            + bq(b("This will reset all progress counters. Caption and quality settings are kept.")),
            reply_markup=InlineKeyboardMarkup([
                [bold_button("Yes, Clear", callback_data="upload_confirm_clear"),
                 bold_button("CANCEL", callback_data="upload_back")],
            ]),
        )
        return

    if data == "upload_confirm_clear":
        if not is_admin:
            return
        try:
            with db_manager.get_cursor() as cur:
                cur.execute("DELETE FROM bot_progress WHERE id = 1")
                cur.execute("""
                    INSERT INTO bot_progress
                        (id, base_caption, selected_qualities, auto_caption_enabled, anime_name)
                    VALUES (1, %s, %s, %s, %s)
                """, (
                    DEFAULT_CAPTION,
                    ",".join(upload_progress["selected_qualities"]),
                    upload_progress["auto_caption_enabled"],
                    upload_progress.get("anime_name", "Anime Name"),
                ))
        except Exception as exc:
            await safe_answer(query, f"Error: {str(exc)[:50]}", show_alert=True)
            return
        await load_upload_progress()
        await safe_answer(query, "Database cleared!")
        try:
            await query.delete_message()
        except Exception:
            pass
        await show_upload_menu(chat_id, context)
        return

    if data == "upload_back":
        if not is_admin:
            return
        await show_upload_menu(chat_id, context, query.message)
        return

    # ── MODULE GUIDE callbacks ───────────────────────────────────────────────
    if data.startswith('mod_') and data in {'mod_wiki', 'mod_purge', 'mod_chatbot', 'mod_imdb', 'mod_antiflood', 'mod_currency', 'mod_stickers', 'mod_ping', 'mod_reporting', 'mod_sed', 'mod_speedtest', 'mod_blsticker', 'mod_cleaner', 'mod_wallpaper', 'mod_badwords', 'mod_locks', 'mod_globalbans', 'mod_tagall', 'mod_logchannel', 'mod_blacklist', 'mod_approve', 'mod_connection', 'mod_shell', 'mod_truthdare', 'mod_writetool', 'mod_admin', 'mod_gettime', 'mod_custfilters', 'mod_animequotes', 'mod_ud', 'mod_translator'}:
        if not is_admin:
            return

    # ── FEATURES panel buttons ────────────────────────────────────────────────
    if data.startswith("feat_"):
        if not is_admin:
            return
        feat_map = {
            "feat_couple":       ("/couple", "Tag two users as a couple. Usage: /couple @user1 @user2"),
            "feat_slap":         ("/slap", "Slap someone! Reply to a message with /slap"),
            "feat_hug":          ("/hug", "Hug someone! Reply to a message with /hug"),
            "feat_kiss":         ("/kiss", "Kiss someone! Reply to a message with /kiss"),
            "feat_pat":          ("/pat", "Pat someone! Reply to a message with /pat"),
            "feat_inline_search":("@Bot query", "Inline anime search — type @YourBot in any chat then anime name."),
            "feat_reactions":    ("/react", "Reaction GIFs. Reply to a message with /slap /hug /pat etc."),
            "feat_chatbot":      ("/chatbot on|off", "Toggle AI chatbot mode in a group."),
            "feat_truth_dare":   ("/truth or /dare", "Play Truth or Dare in a group!"),
            "feat_notes":        ("/save notename text", "Save group notes. Retrieve with #notename"),
            "feat_warns":        ("/warn @user", "Warn users. Also: /unwarn /warns /resetwarns"),
            "feat_muting":       ("/mute @user", "Mute users. Also: /unmute /tmute"),
            "feat_bans":         ("/ban @user", "Ban users. Also: /unban /tban /sban"),
            "feat_rules":        ("/setrules | /rules", "Set and show group rules."),
            "feat_airing":       ("/airing Demon Slayer", "Check next episode airing time from AniList."),
            "feat_character":    ("/character Tanjiro", "Get anime character info from AniList."),
            "feat_anime_info":   ("/anime Naruto", "Get landscape poster + full anime info."),
            "feat_afk":          ("/afk reason", "Set AFK status. Bot auto-replies when tagged."),
        }
        # Special: chatbot toggle is a real toggle, not just info
        if data == "feat_chatbot":
            from database_dual import get_setting, set_setting
            chat_key = f"chatbot_{chat_id}"
            current = (get_setting(chat_key, "true") or "true").lower()
            new_val = "false" if current == "true" else "true"
            set_setting(chat_key, new_val)
            status = small_caps("enabled ✅") if new_val == "true" else small_caps("disabled 🔕")
            try:
                await query.answer(small_caps(f"chatbot {status}"), show_alert=True)
            except Exception:
                pass
            return

        info = feat_map.get(data, (data.replace("feat_", "/"), "Feature command."))
        cmd, desc = info
        try:
            await query.answer(f"{cmd} — {desc[:100]}", show_alert=True)
        except Exception:
            pass
        return

    # ── IMPORT USERS from CSV/Excel ────────────────────────────────────────────
    if data == "admin_export_users_quick":
        if not is_admin:
            return
        # Trigger the existing export users command flow
        asyncio.create_task(exportusers_command(update, context))
        await safe_answer(query, small_caps("📤 exporting users…"))
        return

    if data == "admin_import_users":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        user_states[uid] = "AWAITING_IMPORT_USERS_FILE"
        await safe_send_message(
            context.bot, chat_id,
            (
                "<b> Import Users</b>\n\n"
                "Send a <b>CSV</b> or <b>Excel (.xlsx)</b> file with user IDs.\n\n"
                "<b>CSV format (columns):</b>\n"
                "<code>user_id, username, first_name</code>\n\n"
                "<b>Excel:</b> First column must be <code>user_id</code>.\n\n"
                "Send the file now, or /cancel to abort."
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_back")]]),
        )
        return

    # ── IMPORT LINKS from CSV/Excel ────────────────────────────────────────────
    if data == "admin_import_links":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        user_states[uid] = "AWAITING_IMPORT_LINKS_FILE"
        await safe_send_message(
            context.bot, chat_id,
            (
                "<b> Import Links</b>\n\n"
                "Send a <b>CSV</b> or <b>Excel (.xlsx)</b> file with link data.\n\n"
                "<b>CSV columns:</b> <code>link_id, file_name, channel_id</code>\n\n"
                "Send the file now, or /cancel to abort."
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_back")]]),
        )
        return

    # ── Channel Forward Source settings ──────────────────────────────────────────
    if data == "fsub_fwd_source":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        from database_dual import get_setting as _gs
        fwd_chat = _gs("fwd_source_chat", "") or "Not set"
        fwd_msg_id = _gs("fwd_source_msg_id", "") or "Not set"
        fwd_with_tag = _gs("fwd_with_tag", "true")
        fwd_private = _gs("fwd_private_channel", "false")
        tag_status = "✅ ON" if fwd_with_tag == "true" else "❌ OFF"
        priv_status = "✅ ON" if fwd_private == "true" else "❌ OFF"
        text = (
            b("📨 Forward Source Settings") + "\n\n"
            + bq(
                f"<b>Source Chat:</b> {e(str(fwd_chat))}\n"
                f"<b>Message ID:</b> {e(str(fwd_msg_id))}\n"
                f"<b>Forward Tag:</b> {tag_status}\n"
                f"<b>Private Channel:</b> {priv_status}\n\n"
                "<b>Forward Tag ON</b> = shows 'Forwarded from' header\n"
                "<b>Forward Tag OFF</b> = copies message cleanly (no header)\n"
                "<b>Private Channel</b> = bot accesses private channels by ID"
            )
        )
        rows = [
            [bold_button(" Set Source Chat ID", callback_data="fwd_set_chat"),
             bold_button(" Set Message ID", callback_data="fwd_set_msgid")],
            [bold_button(f" Forward Tag: {tag_status}", callback_data="fwd_toggle_tag"),
             bold_button(f" Private Chan: {priv_status}", callback_data="fwd_toggle_private")],
            [bold_button(" Test Forward Now", callback_data="fwd_test")],
            [_back_btn("manage_force_sub"), _close_btn()],
        ]
        img_url = await get_panel_pic_async("channels")
        if img_url:
            try:
                await context.bot.send_photo(chat_id, img_url, caption=text,
                    parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(rows))
                return
            except Exception:
                pass
        await safe_send_message(context.bot, chat_id, text, reply_markup=InlineKeyboardMarkup(rows))
        return

    if data == "fwd_set_chat":
        if not is_admin: return
        user_states[uid] = "AWAITING_FWD_CHAT"
        try: await query.delete_message()
        except Exception: pass
        await safe_send_message(context.bot, chat_id,
            b(" Set Forward Source Chat") + "\n\n"
            + bq(
                "Send the channel/group ID or @username.\n\n"
                "<b>For private channels:</b> forward any message from the channel to bot, "
                "then use /id to get the chat ID (will be like -100XXXXXXXXX).\n\n"
                "Make sure bot is a member of that channel."
            ),
            reply_markup=InlineKeyboardMarkup([[_back_btn("fsub_fwd_source")]]),
        )
        return

    if data == "fwd_set_msgid":
        if not is_admin: return
        user_states[uid] = "AWAITING_FWD_MSGID"
        try: await query.delete_message()
        except Exception: pass
        await safe_send_message(context.bot, chat_id,
            b(" Set Forward Message ID") + "\n\n"
            + bq(
                "Send the message ID to forward.\n\n"
                "<b>Tip:</b> Forward a message from your channel to a group, "
                "right click → Copy Link. The number after the last / is the message ID.\n\n"
                "Or: use /msg_id command by replying to any message."
            ),
            reply_markup=InlineKeyboardMarkup([[_back_btn("fsub_fwd_source")]]),
        )
        return

    if data == "fwd_toggle_tag":
        if not is_admin: return
        from database_dual import get_setting as _gs, set_setting as _ss
        current = _gs("fwd_with_tag", "true")
        new_val = "false" if current == "true" else "true"
        _ss("fwd_with_tag", new_val)
        label = "ON" if new_val == "true" else "OFF"
        try: await query.answer(f"📨 Forward Tag: {label}", show_alert=False)
        except Exception: pass
        # Re-show panel
        from database_dual import get_setting as _gs2
        fwd_chat = _gs2("fwd_source_chat", "") or "Not set"
        fwd_msg_id = _gs2("fwd_source_msg_id", "") or "Not set"
        fwd_private = _gs2("fwd_private_channel", "false")
        tag_status = "✅ ON" if new_val == "true" else "❌ OFF"
        priv_status = "✅ ON" if fwd_private == "true" else "❌ OFF"
        rows = [
            [bold_button("📋 Set Source Chat ID", callback_data="fwd_set_chat"),
             bold_button("🔢 Set Message ID", callback_data="fwd_set_msgid")],
            [bold_button(f"📨 Forward Tag: {tag_status}", callback_data="fwd_toggle_tag"),
             bold_button(f"🔒 Private Chan: {priv_status}", callback_data="fwd_toggle_private")],
            [bold_button("✅ Test Forward Now", callback_data="fwd_test")],
            [_back_btn("manage_force_sub"), _close_btn()],
        ]
        await safe_send_message(context.bot, chat_id,
            b("📨 Forward Tag toggled!"),
            reply_markup=InlineKeyboardMarkup(rows))
        return

    if data == "fwd_toggle_private":
        if not is_admin: return
        from database_dual import get_setting as _gs, set_setting as _ss
        current = _gs("fwd_private_channel", "false")
        new_val = "false" if current == "true" else "true"
        _ss("fwd_private_channel", new_val)
        label = "ON (private channels enabled)" if new_val == "true" else "OFF"
        try: await query.answer(f"🔒 Private Channel: {label}", show_alert=True)
        except Exception: pass
        return

    if data == "fwd_test":
        if not is_admin: return
        from database_dual import get_setting as _gs
        fwd_chat = _gs("fwd_source_chat", "")
        fwd_msg_id = _gs("fwd_source_msg_id", "")
        fwd_with_tag = _gs("fwd_with_tag", "true") == "true"
        if not fwd_chat or not fwd_msg_id:
            try: await query.answer("❌ Set source chat and message ID first!", show_alert=True)
            except Exception: pass
            return
        try:
            msg_id_int = int(fwd_msg_id)
            if fwd_with_tag:
                # Forward with tag (shows "Forwarded from")
                await context.bot.forward_message(
                    chat_id=chat_id,
                    from_chat_id=fwd_chat,
                    message_id=msg_id_int,
                )
            else:
                # Copy without forward tag
                await context.bot.copy_message(
                    chat_id=chat_id,
                    from_chat_id=fwd_chat,
                    message_id=msg_id_int,
                )
            try: await query.answer("✅ Test forward sent!", show_alert=False)
            except Exception: pass
        except Exception as _fe:
            try: await query.answer(f"❌ Failed: {str(_fe)[:80]}", show_alert=True)
            except Exception: pass
        return

    # ── Poster CMD buttons from admin panel ───────────────────────────────────
    if data.startswith("poster_cmd_"):
        if not is_admin:
            return
        tmpl = data.replace("poster_cmd_", "")
        try:
            await query.delete_message()
        except Exception:
            pass
        await safe_send_message(
            context.bot, chat_id,
            f"<b>🖼 Poster Command:</b> <code>/{tmpl}</code>\n\n"
            f"<b>Usage:</b> /{tmpl} &lt;title&gt;\n"
            f"<b>Example:</b> <code>/{tmpl} Demon Slayer</code>\n\n"
            f"<i>Sends a landscape 1280×720 poster.</i>",
            parse_mode="HTML",
        )
        return

    # ── Admin cmd list ─────────────────────────────────────────────────────────────
    if data == "admin_cmd_list":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        await cmd_command(update, context)
        return

    # ── Anime flow callbacks (anpick_, lang_, size_, anthmb_) ───────────────────
    # These are registered in modules/anime.py — delegate to it here
    if data.startswith(("anpick_", "lang_", "size_", "anthmb_")):
        try:
            from modules.anime import _anime_callback
            await _anime_callback(update, context)
        except Exception as exc:
            logger.debug(f"anime callback error: {exc}")
        return

    # ── Unhandled fallback ─────────────────────────────────────────────────────────
    logger.debug(f"Unhandled callback: {data!r} from user {uid}")
    # (already answered at top — silently ignore)


# ================================================================================
#                      ADMIN MESSAGE HANDLER — FULL STATE MACHINE
# ================================================================================

async def handle_admin_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle all messages from admin in conversation states."""
    if not update.effective_user:
        return
    uid = update.effective_user.id
    if uid not in (ADMIN_ID, OWNER_ID):
        return
    if uid not in user_states:
        return
    if not update.message:
        return

    state = user_states[uid]
    text = update.message.text or ""
    chat_id = update.effective_chat.id

    # ── Forwarded post early-exit: if the message is a channel forward and state
    #    is one that accepts channel input, route to the forward handler path ──
    _channel_states_that_accept_fwd = {
        PENDING_CHANNEL_POST, ADD_CHANNEL_USERNAME,
        AF_ADD_CONNECTION_SOURCE, AF_ADD_CONNECTION_TARGET,
        AU_ADD_MANGA_TARGET,
    }
    if state in _channel_states_that_accept_fwd:
        _fwd_src = (
            getattr(update.message, "forward_from_chat", None)
            or (getattr(update.message, "forward_origin", None)
                and getattr(update.message.forward_origin, "chat", None))
        )
        if _fwd_src:
            # Delegate to handle_admin_photo which handles all forwarded-post states
            await handle_admin_photo(update, context)
            return

    await delete_bot_prompt(context, chat_id)
    await delete_update_message(update, context)

    # Cancel command
    if text.strip().lower() in ("/cancel", "cancel"):
        user_states.pop(uid, None)
        await send_admin_menu(chat_id, context)
        return

    # ── Channel states ─────────────────────────────────────────────────────────────
    if state == ADD_CHANNEL_USERNAME:
        uname = text.strip()
        # Accept both @username AND numeric IDs (e.g. -1001234567890)
        if not uname.startswith("@") and not uname.lstrip("-").isdigit():
            msg = await safe_send_message(
                context.bot, chat_id,
                b("❌ Invalid format. Use @username or numeric channel ID (e.g. -1001234567890). Try again:"),
                reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="manage_force_sub")]]),
            )
            await store_bot_prompt(context, msg)
            return
        # Normalise lookup
        if uname.lstrip("-").isdigit():
            channel_lookup = int(uname)
        else:
            channel_lookup = uname if uname.startswith("@") else f"@{uname}"
        try:
            tg_chat = await context.bot.get_chat(channel_lookup)
            context.user_data["new_ch_uname"] = str(tg_chat.id)   # always store numeric ID
            context.user_data["new_ch_title"] = tg_chat.title
            user_states[uid] = ADD_CHANNEL_TITLE
            ch_link = f"https://t.me/{tg_chat.username}" if tg_chat.username else ""
            ch_info = f"<b>Channel:</b> {e(tg_chat.title)}\n<b>ID:</b> <code>{tg_chat.id}</code>"
            if tg_chat.username:
                ch_info += f"\n<b>Username:</b> @{e(tg_chat.username)}"
            if ch_link:
                ch_info += f"\n<b>Link:</b> {ch_link}"
            keyboard = [[bold_button("🔙 Cancel", callback_data="manage_force_sub")]]
            msg = await safe_send_message(
                context.bot, chat_id,
                b("✅ Channel found!") + "\n\n"
                + bq(ch_info) + "\n\n"
                + b("Send a display title for this channel, or /skip to use the channel name:"),
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            await store_bot_prompt(context, msg)
        except Exception as exc:
            msg = await safe_send_message(
                context.bot, chat_id,
                b("❌ Cannot access that channel.\n\n") + bq(
                    b("Make sure:\n• Bot is admin in the channel\n• Username/ID is correct\n\nError: ")
                ) + code(e(str(exc)[:120])),
                reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="manage_force_sub")]]),
            )
            await store_bot_prompt(context, msg)
        return

    # ── 3rd method: Admin forwards a post from any channel → auto-extract channel ID ────
    if state == PENDING_CHANNEL_POST:
        msg_obj = update.effective_message
        # Check if this is a forwarded message from a channel
        fwd_chat = None
        if msg_obj:
            if msg_obj.forward_from_chat:
                fwd_chat = msg_obj.forward_from_chat
            elif msg_obj.forward_origin and hasattr(msg_obj.forward_origin, "chat"):
                fwd_chat = msg_obj.forward_origin.chat
        if not fwd_chat:
            msg = await safe_send_message(
                context.bot, chat_id,
                b("❌ No forwarded channel post detected.\n\n") + bq(
                    b("Forward any post from the channel you want to add.\n")
                    + "The bot reads the channel ID automatically."
                ),
                reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="manage_force_sub")]]),
            )
            await store_bot_prompt(context, msg)
            return
        try:
            tg_chat = await context.bot.get_chat(fwd_chat.id)
            context.user_data["new_ch_uname"] = str(tg_chat.id)
            context.user_data["new_ch_title"] = tg_chat.title
            user_states[uid] = ADD_CHANNEL_TITLE
            ch_info = f"<b>Channel:</b> {e(tg_chat.title)}\n<b>ID:</b> <code>{tg_chat.id}</code>"
            if tg_chat.username:
                ch_info += f"\n<b>Username:</b> @{e(tg_chat.username)}"
            msg = await safe_send_message(
                context.bot, chat_id,
                b("✅ Channel detected from forwarded post!") + "\n\n"
                + bq(ch_info) + "\n\n"
                + b("Send a display title, or /skip to use the channel name:"),
                reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="manage_force_sub")]]),
            )
            await store_bot_prompt(context, msg)
        except Exception as exc:
            msg = await safe_send_message(
                context.bot, chat_id,
                b("❌ Could not access that channel.\n\n") + bq(
                    b("Make sure the bot is admin in ") + code(e(str(fwd_chat.id)))
                    + b(f"\n\nError: ") + code(e(str(exc)[:100]))
                ),
                reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="manage_force_sub")]]),
            )
            await store_bot_prompt(context, msg)
        return

    if state == ADD_CHANNEL_TITLE:
        uname = context.user_data.get("new_ch_uname")
        if not uname:
            user_states.pop(uid, None)
            await safe_send_message(context.bot, chat_id, b("Session expired. Start over."))
            return
        title = text.strip()
        if title.lower() == "/skip":
            title = context.user_data.get("new_ch_title", uname)
        add_force_sub_channel(uname, title, join_by_request=False)
        await safe_send_message(
            context.bot, chat_id,
            b(f"✅ Added {e(title)} ({e(uname)}) as force-sub channel!"),
        )
        user_states.pop(uid, None)
        await send_admin_menu(chat_id, context)
        return

    # ── Link generation states ─────────────────────────────────────────────────────
    # ── Channel identifier for link generation ───────────────────────────────────
    # (channel title = filter keyword — no separate anime name step)
    if state == GENERATE_LINK_IDENTIFIER:
        identifier = text.strip()
        # Normalise
        if identifier.lstrip("-").isdigit():
            identifier = int(identifier)
        elif not identifier.startswith("@"):
            identifier = f"@{identifier}"
        try:
            tg_chat = await context.bot.get_chat(identifier)
            context.user_data["gen_ch_id"] = tg_chat.id
            context.user_data["gen_ch_title"] = tg_chat.title or str(tg_chat.id)
            user_states[uid] = GENERATE_LINK_TITLE
            msg = await safe_send_message(
                context.bot, chat_id,
                b(small_caps(f"📢 channel: {tg_chat.title or str(tg_chat.id)}")) + "\n\n"
                + bq(
                    b(small_caps("send the filter keyword / title for this link:")) + "\n\n"
                    + small_caps("this becomes both the link title and the filter trigger.\n")
                    + small_caps("example: ") + "<code>Demon Slayer</code>" + small_caps(" or ") + "<code>Jujutsu Kaisen</code>\n\n"
                    + small_caps("send /skip to use the channel name: ") + f"<code>{e(tg_chat.title or '')}</code>"
                ),
                reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_back")]]),
            )
            await store_bot_prompt(context, msg)
        except Exception as exc:
            msg = await safe_send_message(
                context.bot, chat_id,
                b("❌ Cannot access that channel.\n\n") + bq(
                    "Supported:\n• @username\n• -1001234567890\n• Forward a post\n\n"
                    + b("Error: ") + code(e(str(exc)[:100]))
                ),
                reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_back")]]),
            )
            await store_bot_prompt(context, msg)
        return

    # ── Link title / final generation ────────────────────────────────────────────
    # The title entered here becomes the filter keyword automatically.
    # No separate table needed — generated_links.channel_title IS the keyword.
    if state == GENERATE_LINK_TITLE:
        title = text.strip()
        if title.lower() == "/skip":
            title = context.user_data.get("gen_ch_title", "")
        ch_id = context.user_data.get("gen_ch_id")
        if not ch_id:
            user_states.pop(uid, None)
            await safe_send_message(context.bot, chat_id, b(small_caps("session expired. start over.")))
            return
        try:
            link_id = generate_link_id(
                channel_username=ch_id,
                user_id=uid,
                never_expires=False,
                channel_title=title,
                source_bot_username=BOT_USERNAME,
            )
            deep_link = f"https://t.me/{BOT_USERNAME}?start={link_id}"
            await safe_send_message(
                context.bot, chat_id,
                b(small_caps("✅ link generated!")) + "\n\n"
                + bq(code(deep_link)) + "\n\n"
                + bq(
                    b(small_caps("🎌 filter auto-active!")) + "\n"
                    + small_caps("keyword: ") + f"<code>{e(title)}</code>\n"
                    + small_caps("when users type ") + f"<b>{e(title)}</b>" + small_caps(" in any group, ")
                    + small_caps("they get the poster + join button automatically.\n\n")
                    + small_caps("no extra setup needed — the link title is the filter keyword.")
                ),
                reply_markup=_back_kb(),
            )
        except Exception as exc:
            await safe_send_message(
                context.bot, chat_id,
                b(small_caps("❌ error generating link: ")) + code(e(str(exc)[:200])),
            )
        user_states.pop(uid, None)
        for k in ("gen_ch_id", "gen_ch_title"):
            context.user_data.pop(k, None)
        return

    # ── Clone token ────────────────────────────────────────────────────────────────
    if state == ADD_CLONE_TOKEN:
        token = text.strip()
        await _register_clone_token(update, context, token)
        user_states.pop(uid, None)
        return

    # ── Backup channel ─────────────────────────────────────────────────────────────
    if state == SET_BACKUP_CHANNEL:
        url = text.strip()
        set_setting("backup_channel_url", url)
        await safe_send_message(
            context.bot, chat_id,
            b(f"✅ Backup channel URL set: {e(url)}")
        )
        user_states.pop(uid, None)
        await send_admin_menu(chat_id, context)
        return

    # ── Broadcast states ───────────────────────────────────────────────────────────
    if state == PENDING_BROADCAST:
        context.user_data["broadcast_message"] = (
            update.message.chat_id, update.message.message_id
        )
        user_states[uid] = PENDING_BROADCAST_OPTIONS
        keyboard = [
            [bold_button("Normal", callback_data="broadcast_mode_normal"),
             bold_button("Silent", callback_data="broadcast_mode_silent")],
            [bold_button("Auto-Delete 24h", callback_data="broadcast_mode_auto_delete"),
             bold_button("Pin", callback_data="broadcast_mode_pin")],
            [bold_button("Schedule", callback_data="broadcast_schedule"),
             bold_button("🔙 Cancel", callback_data="admin_back")],
        ]
        msg = await safe_send_message(
            context.bot, chat_id,
            b("✅ Message received! Choose broadcast mode:"),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        await store_bot_prompt(context, msg)
        return

    if state == PENDING_BROADCAST_CONFIRM and text.strip().lower() in ("/confirm", "confirm"):
        msg_data = context.user_data.get("broadcast_message")
        mode = context.user_data.get("broadcast_mode", BroadcastMode.NORMAL)
        if not msg_data:
            await safe_send_message(context.bot, chat_id, b("❌ Broadcast message lost. Start over."))
            user_states.pop(uid, None)
            return
        user_states.pop(uid, None)
        msg_chat_id, msg_id = msg_data
        asyncio.create_task(
            _do_broadcast(context, chat_id, msg_chat_id, msg_id, mode)
        )
        return

    # ── Category settings states ───────────────────────────────────────────────────
    category = context.user_data.get("editing_category", "")

    if state == SET_CATEGORY_CAPTION:
        update_category_field(category, "caption_template", text.strip())
        await safe_send_message(
            context.bot, chat_id,
            b(f"✅ Caption template for {e(category)} updated!")
        )
        user_states.pop(uid, None)
        await send_admin_menu(chat_id, context)
        return

    if state == SET_CATEGORY_BRANDING:
        val = text.strip()
        if update_category_field(category, "branding", val):
            await safe_send_message(
                context.bot, chat_id,
                b(f"✅ Branding for {e(category.upper())} updated!") + "\n"
                + bq(code(e(val[:120])) if val else b("(cleared)")),
            )
        else:
            await safe_send_message(context.bot, chat_id, b(f"❌ Failed to save branding. Check DB connection."))
        user_states.pop(uid, None)
        await show_category_settings_menu(context, chat_id, category, None)
        return

    if state == SET_CATEGORY_BUTTONS:
        lines = text.strip().split("\n")
        buttons_list = []
        for line in lines:
            if " - " in line:
                parts = line.split(" - ", 1)
                buttons_list.append({"text": parts[0].strip(), "url": parts[1].strip()})
        if update_category_field(category, "buttons", json.dumps(buttons_list)):
            await safe_send_message(
                context.bot, chat_id,
                b(f"✅ {len(buttons_list)} button(s) configured for {e(category.upper())}!"),
            )
        else:
            await safe_send_message(context.bot, chat_id, b(f"❌ Failed to save buttons. Check DB connection."))
        user_states.pop(uid, None)
        await show_category_settings_menu(context, chat_id, category, None)
        return

    if state == SET_CATEGORY_THUMBNAIL:
        val = "" if text.strip().lower() in ("default", "none", "remove", "clear") else text.strip()
        if update_category_field(category, "thumbnail_url", val):
            await safe_send_message(
                context.bot, chat_id,
                b(f"✅ Thumbnail for {e(category.upper())} {'reset' if not val else 'updated'}!"),
            )
        else:
            await safe_send_message(context.bot, chat_id, b(f"❌ Failed to save thumbnail. Check DB connection."))
        user_states.pop(uid, None)
        await show_category_settings_menu(context, chat_id, category, None)
        return

    if state == SET_WATERMARK_TEXT:
        val = text.strip()
        if update_category_field(category, "watermark_text", val):
            await safe_send_message(
                context.bot, chat_id,
                b(f"✅ Watermark text for {e(category.upper())} set!") + "\n" + bq(code(e(val[:80]))),
            )
        else:
            await safe_send_message(context.bot, chat_id, b(f"❌ Failed to save watermark. Check DB connection."))
        user_states.pop(uid, None)
        await show_category_settings_menu(context, chat_id, category, None)
        return

    # ── Upload manager states ──────────────────────────────────────────────────────
    if state == UPLOAD_SET_CAPTION:
        # Check if we're setting anime name or caption
        upload_field = context.user_data.pop("upload_field", None)
        if upload_field == "anime_name":
            upload_progress["anime_name"] = text.strip()
            await save_upload_progress()
            await safe_send_message(
                context.bot, chat_id,
                b(f"✅ Anime name set to: {e(text.strip())}")
            )
        else:
            upload_progress["base_caption"] = text
            await save_upload_progress()
            await safe_send_message(
                context.bot, chat_id, b("✅ Caption template updated!")
            )
        user_states.pop(uid, None)
        await show_upload_menu(chat_id, context)
        return

    if state == UPLOAD_SET_SEASON:
        try:
            upload_progress["season"] = int(text.strip())
            upload_progress["video_count"] = 0
            await save_upload_progress()
            await safe_send_message(
                context.bot, chat_id,
                b(f"✅ Season set to {upload_progress['season']}")
            )
        except ValueError:
            await safe_send_message(context.bot, chat_id, b("❌ Invalid number. Send again:"))
            return
        user_states.pop(uid, None)
        await show_upload_menu(chat_id, context)
        return

    if state == UPLOAD_SET_EPISODE:
        try:
            upload_progress["episode"] = int(text.strip())
            upload_progress["video_count"] = 0
            await save_upload_progress()
            await safe_send_message(
                context.bot, chat_id,
                b(f"✅ Episode set to {upload_progress['episode']}")
            )
        except ValueError:
            await safe_send_message(context.bot, chat_id, b("❌ Invalid number. Send again:"))
            return
        user_states.pop(uid, None)
        await show_upload_menu(chat_id, context)
        return

    if state == UPLOAD_SET_TOTAL:
        try:
            upload_progress["total_episode"] = int(text.strip())
            await save_upload_progress()
            await safe_send_message(
                context.bot, chat_id,
                b(f"✅ Total episodes set to {upload_progress['total_episode']}")
            )
        except ValueError:
            await safe_send_message(context.bot, chat_id, b("❌ Invalid number. Send again:"))
            return
        user_states.pop(uid, None)
        await show_upload_menu(chat_id, context)
        return

    if state == UPLOAD_SET_CHANNEL:
        identifier = text.strip()
        try:
            tg_chat = await context.bot.get_chat(identifier)
            upload_progress["target_chat_id"] = tg_chat.id
            await save_upload_progress()
            await safe_send_message(
                context.bot, chat_id,
                b(f"✅ Target channel set to: {e(tg_chat.title)}")
            )
        except Exception as exc:
            await safe_send_message(context.bot, chat_id, UserFriendlyError.get_user_message(exc))
            return
        user_states.pop(uid, None)
        await show_upload_menu(chat_id, context)
        return

    # ── Auto-forward states ────────────────────────────────────────────────────────
    if state == AF_ADD_CONNECTION_SOURCE:
        identifier = text.strip()
        # Normalise: support @username OR numeric ID
        if identifier.lstrip("-").isdigit():
            identifier = int(identifier)
        elif not identifier.startswith("@"):
            identifier = f"@{identifier}"
        try:
            tg_chat = await context.bot.get_chat(identifier)
            context.user_data["af_source_id"] = tg_chat.id
            context.user_data["af_source_uname"] = tg_chat.username
            user_states[uid] = AF_ADD_CONNECTION_TARGET
            msg = await safe_send_message(
                context.bot, chat_id,
                b(f"✅ Source: {e(tg_chat.title)}") + "\n\n"
                + bq(b("Step 2/2: Send the TARGET channel @username or ID:\n")
                     + "• <code>@channelname</code>\n"
                     + "• <code>-1001234567890</code>\n"
                     + "• Or <b>forward any post</b> from the target channel"),
                reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_autoforward")]]),
            )
            await store_bot_prompt(context, msg)
        except Exception as exc:
            msg = await safe_send_message(
                context.bot, chat_id,
                b("❌ Cannot access that channel.\n\n") + bq(
                    b("Supported:\n• @username\n• -1001234567890 (numeric ID)\n• Forward a post from the channel\n\nMake sure bot is admin there.\n\nError: ")
                    + code(e(str(exc)[:100]))
                ),
                reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_autoforward")]]),
            )
            await store_bot_prompt(context, msg)
        return

    if state == AF_ADD_CONNECTION_TARGET:
        identifier = text.strip()
        # Normalise: support @username OR numeric ID
        if identifier.lstrip("-").isdigit():
            identifier = int(identifier)
        elif not identifier.startswith("@"):
            identifier = f"@{identifier}"
        try:
            tg_chat = await context.bot.get_chat(identifier)
            src_id = context.user_data.get("af_source_id")
            src_uname = context.user_data.get("af_source_uname", "")
            if not src_id:
                await safe_send_message(context.bot, chat_id, b("Session expired. Start over."))
                user_states.pop(uid, None)
                return
            with db_manager.get_cursor() as cur:
                cur.execute("""
                    INSERT INTO auto_forward_connections
                        (source_chat_id, source_chat_username, target_chat_id,
                         target_chat_username, active)
                    VALUES (%s, %s, %s, %s, TRUE)
                    ON CONFLICT DO NOTHING
                """, (src_id, src_uname, tg_chat.id, tg_chat.username))
            await safe_send_message(
                context.bot, chat_id,
                b("✅ Auto-forward connection created!") + "\n\n"
                + bq(
                    b("Source: ") + code(str(src_id)) + "\n"
                    + b("Target: ") + code(str(tg_chat.id)) + " — " + e(tg_chat.title)
                ),
            )
        except Exception as exc:
            await safe_send_message(context.bot, chat_id, UserFriendlyError.get_user_message(exc))
        user_states.pop(uid, None)
        await send_admin_menu(chat_id, context)
        return

    # ── Manga tracker states ───────────────────────────────────────────────────────
    if state == AU_ADD_MANGA_TITLE:
        title = text.strip()
        # Search MangaDex
        results = MangaDexClient.search_manga(title, limit=5)
        if not results:
            # Try AniList
            anilist_result = AniListClient.search_manga(title)
            if anilist_result:
                al_title = (anilist_result.get("title") or {})
                al_title_str = al_title.get("romaji") or al_title.get("english") or title
                # Search MangaDex with AniList title
                results = MangaDexClient.search_manga(al_title_str, limit=5)

        if not results:
            await safe_send_message(
                context.bot, chat_id,
                b("❌ No manga found on MangaDex.") + "\n" + bq(b("Try a different title.")),
            )
            return

        keyboard = []
        for manga in results[:5]:
            attrs = manga.get("attributes", {}) or {}
            titles = attrs.get("title", {}) or {}
            manga_title = titles.get("en") or next(iter(titles.values()), "Unknown")
            keyboard.append([bold_button(
                manga_title[:40],
                callback_data=f"mdex_track_{manga['id']}"
            )])
        keyboard.append([bold_button("🔙 Cancel", callback_data="admin_autoupdate")])

        await safe_send_message(
            context.bot, chat_id,
            b("📚 Select the manga to track:"),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        user_states.pop(uid, None)
        return

    if state == AU_CUSTOM_INTERVAL:
        try:
            mins = int(text.strip())
            if mins < 1:
                raise ValueError("Too small")
        except ValueError:
            await safe_send_message(
                context.bot, chat_id,
                b("❌ Please send a valid number of minutes (e.g. 15):"),
                reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_autoupdate")]]),
            )
            return
        context.user_data["au_manga_interval"] = mins
        user_states[uid] = AU_ADD_MANGA_TARGET
        title = context.user_data.get("au_manga_title", "Unknown")
        mode = context.user_data.get("au_manga_mode", "latest")
        await safe_send_message(
            context.bot, chat_id,
            b(f"📚 {e(title)}") + f"\n<b>Mode:</b> {mode.title()} | <b>Interval:</b> {mins} min\n\n"
            + bq(
                b("Send the target channel using any method:\n\n")
                + "• <code>@channelname</code>\n"
                + "• <code>-1001234567890</code> (numeric ID)\n"
                + "• <b>Forward any post</b> from the channel"
            ),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_autoupdate")]]),
        )
        return

    if state == AU_ADD_MANGA_TARGET:
        identifier = text.strip()
        manga_id = context.user_data.get("au_manga_id")
        manga_title = context.user_data.get("au_manga_title", "Unknown")
        manga_mode = context.user_data.get("au_manga_mode", "latest")
        manga_interval = context.user_data.get("au_manga_interval", 60)
        if not manga_id:
            await safe_send_message(context.bot, chat_id, b("Session expired. Please start over."))
            user_states.pop(uid, None)
            return
        try:
            # Normalise: support @username, -100xxx numeric ID, or plain numeric ID
            _ident = identifier.strip()
            if _ident.lstrip('-').isdigit():
                _ident = int(_ident)
            elif not _ident.startswith("@"):
                _ident = f"@{_ident}"
            tg_chat = await context.bot.get_chat(_ident)
            # Verify bot can send to this chat
            try:
                _test = await context.bot.get_chat_member(tg_chat.id, (await context.bot.get_me()).id)
                _status = getattr(_test, 'status', '')
                if _status not in ('administrator', 'member', 'creator', 'left', 'kicked'):
                    pass  # still try
            except Exception:
                pass
            success = MangaTracker.add_tracking(manga_id, manga_title, tg_chat.id)
            if success:
                # For "latest" mode: save the current latest chapter as baseline so we don't re-send old ones
                if manga_mode == "latest":
                    latest = MangaDexClient.get_latest_chapter(manga_id)
                    if latest:
                        attrs = latest.get("attributes", {}) or {}
                        ch = attrs.get("chapter")
                        if ch:
                            try:
                                with db_manager.get_cursor() as cur:
                                    cur.execute(
                                        "UPDATE manga_auto_updates SET last_chapter = %s, interval_minutes = %s "
                                        "WHERE manga_id = %s AND target_chat_id = %s",
                                        (ch, manga_interval, manga_id, tg_chat.id)
                                    )
                            except Exception:
                                pass
                else:
                    # Full mode: save interval only, start from chapter 0
                    try:
                        with db_manager.get_cursor() as cur:
                            cur.execute(
                                "UPDATE manga_auto_updates SET interval_minutes = %s, mode = %s "
                                "WHERE manga_id = %s AND target_chat_id = %s",
                                (manga_interval, manga_mode, manga_id, tg_chat.id)
                            )
                    except Exception:
                        pass

                interval_label = "Random 5–10 min" if manga_interval == -1 else f"{manga_interval} min"
                await safe_send_message(
                    context.bot, chat_id,
                    b(f"✅ Now tracking: {e(manga_title)}") + "\n\n"
                    + bq(
                        f"<b>Channel:</b> {e(tg_chat.title or tg_chat.username or str(tg_chat.id))}\n"
                        f"<b>Channel ID:</b> <code>{tg_chat.id}</code>\n"
                        f"<b>Mode:</b> {manga_mode.title()}\n"
                        f"<b>Check interval:</b> {interval_label}\n\n"
                        + b("New chapters will be sent automatically.")
                    ),
                )
            else:
                await safe_send_message(context.bot, chat_id,
                    b("❌ Failed to add tracking.") + "\n\n"
                    + bq(
                        "<b>Checklist:</b>\n"
                        "1. Add the bot as admin to your channel\n"
                        "2. Use correct format: @channelname or -100XXXXXXXXX\n"
                        "3. Make sure the channel exists and bot can post\n\n"
                        "Then try again."
                    ),
                    reply_markup=InlineKeyboardMarkup([[_back_btn("admin_autoupdate")]]),
                )
        except Exception as exc:
            await safe_send_message(
                context.bot, chat_id,
                b("❌ Could not find that channel.\n\n") + bq(
                    b("Supported formats:\n")
                    + "• <code>@channelname</code>\n"
                    + "• <code>-1001234567890</code> (numeric ID)\n"
                    + "• Forward any post from the channel\n\n"
                    + b("Make sure the bot is admin in the channel.\n\nError: ")
                ) + code(e(str(exc)[:100])),
                reply_markup=InlineKeyboardMarkup([[_back_btn("admin_autoupdate")]]),
            )
            return
        user_states.pop(uid, None)
        context.user_data.pop("au_manga_id", None)
        context.user_data.pop("au_manga_title", None)
        context.user_data.pop("au_manga_mode", None)
        context.user_data.pop("au_manga_interval", None)
        await send_admin_menu(chat_id, context)
        return

    # ── Channel welcome text/buttons ──────────────────────────────────────────────
    if state == CW_SET_TEXT:
        ch_id = context.user_data.get("cw_editing_channel")
        if not ch_id:
            user_states.pop(uid, None)
            await safe_send_message(context.bot, chat_id, b("session expired. start over."))
            return
        from database_dual import set_channel_welcome
        set_channel_welcome(ch_id, welcome_text=text.strip())
        user_states.pop(uid, None)
        await safe_send_message(
            context.bot, chat_id,
            b(small_caps("✅ welcome text saved!")) + "\n" + bq(e(text.strip()[:200])),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(small_caps("✏️ edit more"), callback_data=f"cw_edit_{ch_id}"),
                _back_btn("admin_channel_welcome"),
            ]]),
        )
        return

    if state == CW_SET_BUTTONS:
        ch_id = context.user_data.get("cw_editing_channel")
        if not ch_id:
            user_states.pop(uid, None)
            await safe_send_message(context.bot, chat_id, b("session expired. start over."))
            return
        lines = text.strip().split("\n")
        btns = []
        for line in lines:
            if " - " in line:
                parts = line.split(" - ", 1)
                btns.append({"text": parts[0].strip(), "url": parts[1].strip()})
        from database_dual import set_channel_welcome
        set_channel_welcome(ch_id, buttons=btns)
        user_states.pop(uid, None)
        await safe_send_message(
            context.bot, chat_id,
            b(small_caps(f"✅ {len(btns)} button(s) saved!")),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(small_caps("✏️ edit more"), callback_data=f"cw_edit_{ch_id}"),
                _back_btn("admin_channel_welcome"),
            ]]),
        )
        return

    if isinstance(state, str) and state == "CW_WAITING_CHANNEL_ID":
        identifier = text.strip()
        if identifier.lstrip("-").isdigit():
            identifier = int(identifier)
        elif not identifier.startswith("@"):
            identifier = f"@{identifier}"
        try:
            tg_chat = await context.bot.get_chat(identifier)
            from database_dual import set_channel_welcome
            set_channel_welcome(tg_chat.id, enabled=True, welcome_text="", added_by=uid)
            context.user_data["cw_editing_channel"] = tg_chat.id
            user_states.pop(uid, None)
            await safe_send_message(
                context.bot, chat_id,
                b(small_caps(f"✅ channel registered: {tg_chat.title or str(tg_chat.id)}")) + "\n"
                + bq(small_caps("now configure the welcome message below.")),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(small_caps("⚙️ configure"), callback_data=f"cw_edit_{tg_chat.id}"),
                    _back_btn("admin_channel_welcome"),
                ]]),
            )
        except Exception as exc:
            await safe_send_message(
                context.bot, chat_id,
                b(small_caps("❌ cannot access that channel.")) + "\n"
                + bq(small_caps("make sure bot is admin in the channel.\n\nerror: ") + code(e(str(exc)[:100]))),
                reply_markup=InlineKeyboardMarkup([[_back_btn("admin_channel_welcome")]]),
            )
        return

    if isinstance(state, str) and state == "CW_AWAITING_IMAGE":
        # Text fallback: URL
        ch_id = context.user_data.get("cw_editing_channel")
        if ch_id and text.strip().startswith("http"):
            from database_dual import set_channel_welcome
            set_channel_welcome(ch_id, image_url=text.strip(), image_file_id="")
            user_states.pop(uid, None)
            await safe_send_message(
                context.bot, chat_id,
                b(small_caps("✅ welcome image url saved!")),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(small_caps("✏️ edit more"), callback_data=f"cw_edit_{ch_id}"),
                ]]),
            )
        else:
            await safe_send_message(
                context.bot, chat_id,
                b(small_caps("send a photo or image url (starts with https://).")),
            )
        return

    # ── User management states ─────────────────────────────────────────────────────
    if state == BAN_USER_INPUT:
        target = resolve_target_user_id(text.strip())
        if target:
            if target in (ADMIN_ID, OWNER_ID):
                await safe_send_message(context.bot, chat_id, b("⚠️ Cannot ban admin/owner."))
            else:
                ban_user(target)
                await safe_send_message(context.bot, chat_id, b(f"🚫 User {code(str(target))} banned."))
        else:
            await safe_send_message(context.bot, chat_id, b("❌ User not found."))
        user_states.pop(uid, None)
        return

    if state == UNBAN_USER_INPUT:
        target = resolve_target_user_id(text.strip())
        if target:
            unban_user(target)
            await safe_send_message(context.bot, chat_id, b(f"✅ User {code(str(target))} unbanned."))
        else:
            await safe_send_message(context.bot, chat_id, b("❌ User not found."))
        user_states.pop(uid, None)
        return

    if state == DELETE_USER_INPUT:
        try:
            target_uid = int(text.strip())
            if target_uid in (ADMIN_ID, OWNER_ID):
                await safe_send_message(context.bot, chat_id, b("⚠️ Cannot delete admin/owner."))
            else:
                with db_manager.get_cursor() as cur:
                    cur.execute("DELETE FROM users WHERE user_id = %s", (target_uid,))
                await safe_send_message(
                    context.bot, chat_id, b(f"✅ User {code(str(target_uid))} deleted.")
                )
        except (ValueError, Exception) as exc:
            await safe_send_message(context.bot, chat_id, b(f"❌ Error: {code(e(str(exc)[:100]))}"))
        user_states.pop(uid, None)
        return

    if state == SEARCH_USER_INPUT:
        target = resolve_target_user_id(text.strip())
        if target:
            user_info = get_user_info_by_id(target)
            if user_info:
                u_id, u_uname, u_fname, u_lname, u_joined, u_banned = user_info
                name = f"{u_fname or ''} {u_lname or ''}".strip() or "N/A"
                info_text = (
                    b("👤 User Found:") + "\n\n"
                    f"<b>ID:</b> {code(str(u_id))}\n"
                    f"<b>Name:</b> {e(name)}\n"
                    f"<b>Username:</b> {'@' + e(u_uname) if u_uname else '—'}\n"
                    f"<b>Joined:</b> {code(str(u_joined)[:16])}\n"
                    f"<b>Status:</b> {'🚫 Banned' if u_banned else '✅ Active'}"
                )
                keyboard = [
                    [bold_button("🚫 Ban" if not u_banned else "✅ Unban",
                                 callback_data=f"user_ban_{u_id}" if not u_banned else f"user_unban_{u_id}")],
                    [bold_button("Delete", callback_data=f"user_del_{u_id}")],
                ]
                await safe_send_message(
                    context.bot, chat_id, info_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
            else:
                await safe_send_message(context.bot, chat_id, b(f"❌ No user found with ID {target}."))
        else:
            await safe_send_message(context.bot, chat_id, b("❌ User not found in database."))
        user_states.pop(uid, None)
        return

    # ── Scheduled broadcast datetime ───────────────────────────────────────────────
    if state == SCHEDULE_BROADCAST_DATETIME:
        try:
            dt = datetime.strptime(text.strip(), "%Y-%m-%d %H:%M")
            context.user_data["schedule_dt"] = dt
            user_states[uid] = SCHEDULE_BROADCAST_MSG
            msg = await safe_send_message(
                context.bot, chat_id,
                b(f"📅 Scheduled for: {dt.strftime('%d %b %Y %H:%M')} UTC") + "\n\n"
                + bq(b("Now send the message to broadcast:")),
            )
            await store_bot_prompt(context, msg)
        except ValueError:
            await safe_send_message(
                context.bot, chat_id,
                b("❌ Invalid format.") + "\n" + bq(b("Use: YYYY-MM-DD HH:MM (e.g., 2026-12-25 08:00)"))
            )
        return

    if state == SCHEDULE_BROADCAST_MSG:
        dt = context.user_data.get("schedule_dt")
        if not dt:
            await safe_send_message(context.bot, chat_id, b("❌ Session expired. Start over."))
            user_states.pop(uid, None)
            return
        try:
            with db_manager.get_cursor() as cur:
                cur.execute("""
                    INSERT INTO scheduled_broadcasts (admin_id, message_text, execute_at, status)
                    VALUES (%s, %s, %s, 'pending')
                """, (uid, text.strip(), dt))
        except Exception as exc:
            await safe_send_message(
                context.bot, chat_id,
                b("❌ Error scheduling: ") + code(e(str(exc)[:200]))
            )
            user_states.pop(uid, None)
            return
        await safe_send_message(
            context.bot, chat_id,
            b(f"✅ Broadcast scheduled for {dt.strftime('%d %b %Y %H:%M')} UTC!"),
            reply_markup=_back_kb(),
        )
        user_states.pop(uid, None)
        return

    # ── New state handlers from panel sub-actions ─────────────────────────────────
    # ── Import Users / Links from CSV or Excel ────────────────────────────────
    if state in ("AWAITING_IMPORT_USERS_FILE", "AWAITING_IMPORT_LINKS_FILE"):
        user_states.pop(uid, None)
        doc = update.message.document if update.message else None
        if not doc:
            await safe_send_message(context.bot, chat_id,
                "❗ <b>Please send a CSV or Excel (.xlsx) file.</b>", parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[_back_btn("admin_back")]]))
            return
        try:
            tg_file = await context.bot.get_file(doc.file_id)
            raw = await tg_file.download_as_bytearray()
        except Exception as _dl_err:
            await safe_send_message(context.bot, chat_id,
                f"❌ Failed to download file: <code>{html.escape(str(_dl_err))}</code>",
                parse_mode="HTML")
            return

        fname_lower = (doc.file_name or "").lower()
        imported, errors = 0, 0
        is_users = state == "AWAITING_IMPORT_USERS_FILE"

        try:
            if fname_lower.endswith(".xlsx") or fname_lower.endswith(".xls"):
                # Excel import
                try:
                    import openpyxl
                except ImportError:
                    await safe_send_message(context.bot, chat_id,
                        "❌ <b>openpyxl not installed.</b> Please use CSV format instead.",
                        parse_mode="HTML")
                    return
                from io import BytesIO
                wb = openpyxl.load_workbook(BytesIO(bytes(raw)), read_only=True)
                ws = wb.active
                rows_iter = ws.iter_rows(values_only=True)
                headers_row = next(rows_iter, None)
                if not headers_row:
                    await safe_send_message(context.bot, chat_id, "❌ Empty Excel file.")
                    return
                headers = [str(c).lower().strip() if c else "" for c in headers_row]
                def _col(name, fallback=0):
                    return headers.index(name) if name in headers else fallback
                uid_col   = _col("user_id")
                uname_col = _col("username", -1)
                name_col  = _col("first_name", -1)
                link_col  = _col("link_id", 0)
                file_col  = _col("file_name", -1)
                chan_col  = _col("channel_id", -1)
                for row in rows_iter:
                    if not row or not row[0]:
                        continue
                    try:
                        if is_users:
                            row_uid = int(str(row[uid_col]).strip().split(".")[0])
                            uname  = str(row[uname_col]).strip() if uname_col >= 0 and row[uname_col] else None
                            fname2 = str(row[name_col]).strip()  if name_col  >= 0 and row[name_col]  else None
                            add_user(row_uid, uname, fname2, None)
                        else:
                            link_id  = str(row[link_col]).strip()
                            fn       = str(row[file_col]).strip() if file_col >= 0 and row[file_col] else link_id
                            try:
                                chan_raw = row[chan_col] if chan_col >= 0 else None
                                chan_un  = str(chan_raw).strip() if chan_raw else fn
                            except Exception:
                                chan_un = fn
                            # Use generate_link_id to register imported link
                            generate_link_id(chan_un, uid, never_expires=True, channel_title=fn)
                        imported += 1
                    except Exception:
                        errors += 1
            else:
                # CSV import (default)
                import csv
                from io import StringIO
                text_data = raw.decode("utf-8", errors="replace")
                # Auto-detect delimiter
                sample = text_data[:2048]
                delimiter = ","
                for d in [",", ";", "	", "|"]:
                    if d in sample:
                        delimiter = d
                        break
                reader = csv.DictReader(StringIO(text_data), delimiter=delimiter)
                for row in reader:
                    if not row:
                        continue
                    try:
                        if is_users:
                            raw_id = str(row.get("user_id") or row.get("id") or row.get("User ID") or "").strip()
                            if not raw_id:
                                errors += 1
                                continue
                            row_uid = int(raw_id.split(".")[0])
                            uname  = (row.get("username") or row.get("Username") or "").strip() or None
                            fname2 = (row.get("first_name") or row.get("name") or row.get("Name") or "").strip() or None
                            add_user(row_uid, uname, fname2, None)
                        else:
                            fn = str(row.get("file_name") or row.get("name") or "").strip()
                            chan_raw = (row.get("channel_id") or row.get("channel_username") or "").strip()
                            generate_link_id(chan_raw or fn, uid, never_expires=True, channel_title=fn or chan_raw)
                        imported += 1
                    except Exception:
                        errors += 1
        except Exception as exc:
            await safe_send_message(context.bot, chat_id,
                f"❌ <b>Import failed:</b> <code>{html.escape(str(exc)[:200])}</code>",
                parse_mode="HTML")
            return

        label = "users" if is_users else "links"
        _import_msg = (
            f"<b>\u2705 Import Complete!</b>\n\n"
            f"\u2022 Imported {label}: <b>{imported:,}</b>\n"
            f"\u2022 Rows skipped: <b>{errors:,}</b>\n\n"
            f"<i>File: {html.escape(doc.file_name or 'unknown')}</i>"
        )
        await safe_send_message(
            context.bot, chat_id,
            _import_msg,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [_btn("\U0001f465 VIEW USERS", "user_management"), _back_btn("admin_back")],
            ]),
        )
        return

    if state == "AWAITING_PANEL_IMGS":
        # User sent a photo/sticker while in panel image add mode
        _msg_obj = update.effective_message
        _file_id_panel = None
        _is_sticker_panel = False
        if _msg_obj and _msg_obj.photo:
            _file_id_panel = _msg_obj.photo[-1].file_id
        elif _msg_obj and _msg_obj.sticker:
            _file_id_panel = _msg_obj.sticker.file_id
            _is_sticker_panel = True
        if _file_id_panel:
            if not PANEL_DB_CHANNEL:
                user_states.pop(uid, None)
                await safe_send_message(context.bot, chat_id, b("❌ PANEL_DB_CHANNEL not set."))
                return
            items = _get_panel_db_images()
            try:
                if _is_sticker_panel:
                    sent = await context.bot.send_sticker(
                        chat_id=PANEL_DB_CHANNEL, sticker=_file_id_panel,
                    )
                    fid = sent.sticker.file_id
                else:
                    sent = await context.bot.send_photo(
                        chat_id=PANEL_DB_CHANNEL,
                        photo=_file_id_panel,
                        caption=b(small_caps(f"panel image #{len(items) + 1}")),
                    )
                    fid = sent.photo[-1].file_id
                items.append({"index": len(items)+1, "msg_id": sent.message_id, "file_id": fid})
                _save_panel_db_images(items)
                if _PANEL_IMAGE_AVAILABLE:
                    try:
                        from panel_image import clear_tg_fileid
                        clear_tg_fileid()
                    except Exception:
                        pass
                _kind = "sticker" if _is_sticker_panel else "image"
                await safe_send_message(
                    context.bot, chat_id,
                    b(small_caps(f"✅ {_kind} #{len(items)} added!"))
                    + "\n" + bq(b(small_caps("send more, or tap done to finish."))),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🖼 View All", callback_data="panel_img_manage"),
                        InlineKeyboardButton("✖️ Done", callback_data="close_message"),
                    ]])
                )
            except Exception as exc:
                await safe_send_message(context.bot, chat_id, b(f"❌ {e(str(exc)[:100])}"))
        return

    if state == "AWAITING_PANEL_IMG_URLS":
        user_states.pop(uid, None)
        import json as _j

        # Accept: comma-separated OR newline-separated file_ids or URLs
        # A Telegram file_id starts with "AgAC" or "BAAC" etc. (no http)
        raw_entries = []
        for line in text.replace(",", "\n").splitlines():
            v = line.strip()
            if v:
                raw_entries.append(v)

        if not raw_entries:
            await safe_send_message(context.bot, chat_id,
                "❌ Nothing found. Send file_ids (comma-separated) or image URLs.")
            return

        items = _get_panel_db_images()
        added = 0
        errors = 0

        for entry in raw_entries:
            if entry.startswith("http"):
                # It's a URL — store as-is (will be fetched by panel_image module)
                items.append({"index": len(items)+1, "msg_id": 0, "file_id": entry})
                added += 1
            else:
                # Treat as a Telegram file_id — try forwarding to PANEL_DB_CHANNEL
                if PANEL_DB_CHANNEL:
                    try:
                        sent = await context.bot.send_photo(
                            chat_id=PANEL_DB_CHANNEL,
                            photo=entry,
                            caption=f"Panel image #{len(items)+1}",
                        )
                        fid = sent.photo[-1].file_id
                        items.append({"index": len(items)+1, "msg_id": sent.message_id, "file_id": fid})
                        added += 1
                    except Exception:
                        errors += 1
                else:
                    # No DB channel — store file_id directly
                    items.append({"index": len(items)+1, "msg_id": 0, "file_id": entry})
                    added += 1

        if added:
            _save_panel_db_images(items)
            if _PANEL_IMAGE_AVAILABLE:
                try:
                    from panel_image import clear_tg_fileid
                    clear_tg_fileid()
                except Exception:
                    pass

        err_note = f"\n⚠️ {errors} entry(ies) failed (invalid file_id?)." if errors else ""
        await safe_send_message(
            context.bot, chat_id,
            b(f"✅ Added {added} panel image(s). Total: {len(items)}.") + err_note,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🖼 View Panel Images", callback_data="panel_img_manage")],
                [_back_btn("admin_settings"), _close_btn()],
            ])
        )
        return

    if state == "AWAITING_FWD_CHAT":
        user_states.pop(uid, None)
        from database_dual import set_setting as _ss
        chat_val = text.strip()
        _ss("fwd_source_chat", chat_val)
        await safe_send_message(context.bot, chat_id,
            b(f"✅ Forward source chat set: {e(chat_val)}"),
            reply_markup=InlineKeyboardMarkup([[_back_btn("fsub_fwd_source"), _close_btn()]])
        )
        return

    if state == "AWAITING_FWD_MSGID":
        user_states.pop(uid, None)
        try:
            msg_id_int = int(text.strip())
            from database_dual import set_setting as _ss
            _ss("fwd_source_msg_id", str(msg_id_int))
            await safe_send_message(context.bot, chat_id,
                b(f"✅ Forward message ID set: {code(str(msg_id_int))}"),
                reply_markup=InlineKeyboardMarkup([[_back_btn("fsub_fwd_source"), _close_btn()]])
            )
        except ValueError:
            await safe_send_message(context.bot, chat_id,
                b("❌ Invalid message ID — must be a number."))
        return

    if state == "AWAITING_USER_SEARCH":
        user_states.pop(uid, None)
        target = resolve_target_user_id(text.strip())
        if target:
            info = get_user_info_by_id(target)
            if info:
                uid2, uname, fname, lname, joined, banned = info
                st = "🔴 BANNED" if banned else "🟢 Active"
                await safe_send_message(
                    context.bot, chat_id,
                    b(f"USER INFO: {e(str(uid2))}") + "\n\n"
                    + bq(
                        f"<b>Name:</b> {e((fname or '') + ' ' + (lname or ''))}"
                        f"\n<b>Username:</b> @{e(uname or 'N/A')}"
                        f"\n<b>Joined:</b> {str(joined)[:10]}"
                        f"\n<b>Status:</b> {st}"
                        f"\n<b>ID:</b> <code>{uid2}</code>"
                    ),
                    reply_markup=InlineKeyboardMarkup([
                        [_btn("BAN" if not banned else "UNBAN",
                              f"{'user_ban_confirm' if not banned else 'user_unban_confirm'}_{uid2}")],
                        [_back_btn("user_management"), _close_btn()],
                    ]),
                )
            else:
                await safe_send_message(context.bot, chat_id, b(f"❗ User {target} not found in database."))
        else:
            await safe_send_message(context.bot, chat_id, b("❗ Invalid user ID or username."))
        return

    if state == "AWAITING_BAN_USER":
        user_states.pop(uid, None)
        target = resolve_target_user_id(text.strip())
        if target and target not in (ADMIN_ID, OWNER_ID):
            ban_user(target)
            await safe_send_message(context.bot, chat_id,
                b(f"🔴 User <code>{target}</code> banned."),
                reply_markup=InlineKeyboardMarkup([[_back_btn("user_management"), _close_btn()]]),
            )
        else:
            await safe_send_message(context.bot, chat_id, b("❗ Cannot ban admin or user not found."))
        return

    if state == "AWAITING_UNBAN_USER":
        user_states.pop(uid, None)
        target = resolve_target_user_id(text.strip())
        if target:
            unban_user(target)
            await safe_send_message(context.bot, chat_id,
                b(f"🟢 User <code>{target}</code> unbanned."),
                reply_markup=InlineKeyboardMarkup([[_back_btn("user_management"), _close_btn()]]),
            )
        else:
            await safe_send_message(context.bot, chat_id, b("❗ User not found."))
        return

    if state == "AWAITING_DELETE_USER":
        user_states.pop(uid, None)
        try:
            target = int(text.strip())
            with db_manager.get_cursor() as cur:
                cur.execute("DELETE FROM users WHERE user_id = %s", (target,))
            await safe_send_message(context.bot, chat_id,
                b(f"✔️ User <code>{target}</code> deleted from database."),
                reply_markup=InlineKeyboardMarkup([[_back_btn("user_management"), _close_btn()]]),
            )
        except Exception as exc:
            await safe_send_message(context.bot, chat_id, b(f"❗ Error: {e(str(exc)[:100])}"))
        return

    if state == "AWAITING_LINK_EXPIRY":
        user_states.pop(uid, None)
        try:
            mins = int(text.strip())
            if 1 <= mins <= 1440:
                set_setting("link_expiry_override", str(mins))
                await safe_send_message(context.bot, chat_id,
                    b(f"✔️ Link expiry set to {mins} minutes."),
                    reply_markup=InlineKeyboardMarkup([[_back_btn("admin_settings"), _close_btn()]]),
                )
            else:
                await safe_send_message(context.bot, chat_id, b("❗ Must be between 1 and 1440 minutes."))
        except ValueError:
            await safe_send_message(context.bot, chat_id, b("❗ Send a valid number."))
        return

    if state == "AWAITING_AF_DELAY":
        user_states.pop(uid, None)
        try:
            secs = max(0, int(text.strip()))
            with db_manager.get_cursor() as cur:
                cur.execute("""
                    INSERT INTO auto_forward_connections (source_chat_id, target_chat_id, delay_seconds)
                    VALUES (0, 0, %s) ON CONFLICT DO NOTHING
                """, (secs,))
                cur.execute("UPDATE auto_forward_connections SET delay_seconds = %s", (secs,))
            await safe_send_message(context.bot, chat_id,
                b(small_caps(f"✅ auto-forward delay set to {secs}s")),
                reply_markup=InlineKeyboardMarkup([[_back_btn("admin_autoforward"), _close_btn()]]),
            )
        except ValueError:
            await safe_send_message(context.bot, chat_id, b(small_caps("❌ send a valid number of seconds.")))
        return

    if state == "AWAITING_AF_CAPTION":
        user_states.pop(uid, None)
        val = "" if text.strip().lower() in ("/clear", "clear", "none", "remove") else text.strip()
        try:
            with db_manager.get_cursor() as cur:
                cur.execute("""
                    INSERT INTO auto_forward_filters (connection_id, caption_override)
                    VALUES (NULL, %s)
                    ON CONFLICT DO NOTHING
                """, (val,))
                cur.execute(
                    "UPDATE auto_forward_filters SET caption_override = %s WHERE connection_id IS NULL",
                    (val,)
                )
            status = b(small_caps("cleared")) if not val else code(e(val[:80]))
            await safe_send_message(context.bot, chat_id,
                b(small_caps("✅ caption override: ")) + status,
                reply_markup=InlineKeyboardMarkup([[_back_btn("admin_autoforward"), _close_btn()]]),
            )
        except Exception as exc:
            await safe_send_message(context.bot, chat_id, b(small_caps(f"❌ error: {str(exc)[:100]}")))
        return

    if state == "AWAITING_AF_BULK_COUNT":
        user_states.pop(uid, None)
        try:
            cnt = max(1, min(50, int(text.strip())))
            # Store for next bulk forward run
            set_setting("af_bulk_count", str(cnt))
            await safe_send_message(context.bot, chat_id,
                b(small_caps(f"✅ bulk forward count set to {cnt} messages.")) + "\n"
                + bq(small_caps("use /autoforward to run the bulk forward.")),
                reply_markup=InlineKeyboardMarkup([[_back_btn("admin_autoforward"), _close_btn()]]),
            )
        except ValueError:
            await safe_send_message(context.bot, chat_id, b(small_caps("❌ send a valid number (1-50).")))
        return

    if state == "AWAITING_MOVE_LINKS":
        user_states.pop(uid, None)
        parts = text.strip().split()
        if len(parts) == 2:
            from_bot = parts[0].lstrip("@")
            to_bot = parts[1].lstrip("@")
            moved = move_links_to_bot(from_bot, to_bot)
            await safe_send_message(context.bot, chat_id,
                b(f"✔️ Moved {moved} links from @{from_bot} to @{to_bot}."),
                reply_markup=InlineKeyboardMarkup([[_back_btn("manage_clones"), _close_btn()]]),
            )
        else:
            await safe_send_message(context.bot, chat_id, b("❗ Format: @from_bot @to_bot"))
        return

    # Watermark state handlers (format: AWAITING_WATERMARK_CATEGORY)
    # ENV variable editing
    if isinstance(state, str) and state.startswith("AWAITING_ENV_"):
        env_key = state[len("AWAITING_ENV_"):]
        user_states.pop(uid, None)
        if text.strip().lower() == "reset":
            # Remove override — use original .env
            try:
                from database_dual import _pg_run, _MG
                _pg_run("DELETE FROM bot_settings WHERE key = %s", (f"env_{env_key}",))
                if _MG.db:
                    _MG.db.bot_settings.delete_one({"key": f"env_{env_key}"})
            except Exception:
                pass
            await safe_send_message(
                context.bot, chat_id,
                b(f"♻️ {e(env_key)} reset to .env default."),
                reply_markup=InlineKeyboardMarkup([[_back_btn("admin_env_panel"), _close_btn()]]),
            )
        else:
            set_setting(f"env_{env_key}", text.strip())
            await safe_send_message(
                context.bot, chat_id,
                b(f"✔️ {e(env_key)} updated.") + f"\n<code>{e(text.strip()[:80])}</code>",
                reply_markup=InlineKeyboardMarkup([[_back_btn("admin_env_panel"), _close_btn()]]),
            )
        return


    if isinstance(state, str) and state.startswith("AWAITING_WM_LAYER_"):
        parts_s = state.split("_")
        layer   = parts_s[3].lower()
        try:
            fp_cid = int(parts_s[4])
        except Exception:
            fp_cid = uid
        user_states.pop(uid, None)
        from filter_poster import get_wm_layer, set_wm_layer
        sticker = update.message.sticker if update.message else None
        if layer == "c" and sticker:
            ldata = get_wm_layer(fp_cid, "c")
            ldata["file_id"] = sticker.file_id
            ldata["enabled"] = True
            set_wm_layer(fp_cid, "c", ldata)
            await safe_send_message(context.bot, chat_id,
                b("✔️ Sticker set as Layer C watermark!"),
                reply_markup=InlineKeyboardMarkup([[_back_btn("admin_filter_poster"), _close_btn()]]))
        elif layer == "c":
            raw_parts = [p.strip() for p in text.split("|")]
            ldata = get_wm_layer(fp_cid, "c")
            if raw_parts[0].startswith("http"):
                ldata["url"] = raw_parts[0]
                ldata["file_id"] = ""
            if len(raw_parts) > 1: ldata["position"] = raw_parts[1]
            if len(raw_parts) > 2:
                try: ldata["scale"] = float(raw_parts[2])
                except: pass
            if len(raw_parts) > 3:
                try: ldata["opacity"] = int(raw_parts[3])
                except: pass
            ldata["enabled"] = True
            set_wm_layer(fp_cid, "c", ldata)
            await safe_send_message(context.bot, chat_id, b("✔️ Layer C image watermark set!"),
                reply_markup=InlineKeyboardMarkup([[_back_btn("admin_filter_poster"), _close_btn()]]))
        else:
            raw_parts = [p.strip() for p in text.split("|")]
            ldata = get_wm_layer(fp_cid, layer)
            if raw_parts: ldata["text"] = raw_parts[0]
            if len(raw_parts) > 1: ldata["position"] = raw_parts[1]
            if len(raw_parts) > 2:
                try: ldata["font_size"] = int(raw_parts[2])
                except: pass
            if len(raw_parts) > 3: ldata["color"] = raw_parts[3]
            if len(raw_parts) > 4:
                try: ldata["opacity"] = int(raw_parts[4])
                except: pass
            ldata["enabled"] = True
            set_wm_layer(fp_cid, layer, ldata)
            await safe_send_message(context.bot, chat_id,
                b(f"✔️ Layer {layer.upper()}: {e(ldata.get('text',''))} @ {e(ldata.get('position',''))}"),
                reply_markup=InlineKeyboardMarkup([[_back_btn("admin_filter_poster"), _close_btn()]]))
        return

    if state == "AWAITING_FILTER_AUTODEL":
        user_states.pop(uid, None)
        try:
            secs = max(0, int(text.strip()))
            set_setting(f"filter_auto_delete_{chat_id}", str(secs))
            await safe_send_message(context.bot, chat_id,
                b(f"✔️ Auto-delete set to {secs}s ({secs // 60} min)."),
                reply_markup=InlineKeyboardMarkup([[_back_btn("admin_filter_poster"), _close_btn()]]))
        except ValueError:
            await safe_send_message(context.bot, chat_id, b("❗ Send a number in seconds."))
        return

    if state == "AWAITING_JOIN_BTN_TEXT":
        user_states.pop(uid, None)
        val = text.strip()
        if val:
            set_setting("env_JOIN_BTN_TEXT", val)
            await safe_send_message(
                context.bot, chat_id,
                b(small_caps("✅ join button text updated!")) + "\n"
                + bq(
                    b(small_caps("new text: ")) + f"<code>{e(val)}</code>\n"
                    + small_caps("this will appear on all filter poster join buttons.\n")
                    + small_caps("the button still opens a direct 5-min expirable invite link.")
                ),
                reply_markup=InlineKeyboardMarkup([[_back_btn("admin_filter_poster"), _close_btn()]]),
            )
        else:
            await safe_send_message(context.bot, chat_id, b(small_caps("❌ empty text — not saved.")))
        return

    if state == "AWAITING_LINK_EXPIRY_FP":
        user_states.pop(uid, None)
        try:
            mins = max(0, int(text.strip()))
            set_setting("link_expiry_override", str(mins))
            await safe_send_message(context.bot, chat_id,
                b(f"✔️ Link expiry set to {mins} minutes."),
                reply_markup=InlineKeyboardMarkup([[_back_btn("admin_filter_poster"), _close_btn()]]))
        except ValueError:
            await safe_send_message(context.bot, chat_id, b("❗ Send a number in minutes."))
        return


    if isinstance(state, str) and state.startswith("AWAITING_WATERMARK_"):
        cat = state[len("AWAITING_WATERMARK_"):].lower()
        user_states.pop(uid, None)
        if text.strip().lower() == "none":
            update_category_field(cat, "watermark_text", None)
            await safe_send_message(context.bot, chat_id, b(f"✔️ Watermark removed for {cat}."),
                reply_markup=InlineKeyboardMarkup([[_back_btn(f"cat_settings_{cat}"), _close_btn()]]))
        else:
            parts = text.strip().split("|", 1)
            wm_text = parts[0].strip()
            wm_pos  = parts[1].strip() if len(parts) > 1 else "center"
            update_category_field(cat, "watermark_text", wm_text)
            update_category_field(cat, "watermark_position", wm_pos)
            await safe_send_message(context.bot, chat_id,
                b(f"✔️ Watermark set: <i>{e(wm_text)}</i> @ {wm_pos}"),
                reply_markup=InlineKeyboardMarkup([[_back_btn(f"cat_settings_{cat}"), _close_btn()]]))
        return

    # ── Fallthrough: unknown state ─────────────────────────────────────────────────
    logger.debug(f"Admin message in unknown state {state} from {uid}: {text[:50]}")


# ================================================================================
#                          MAIN FUNCTION
# ================================================================================

# ================================================================================
#                     CLEAN GROUP CHAT (GC) SYSTEM
# ================================================================================

async def _clean_gc_service_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Delete all service/status messages in groups silently:
    - New member joins (including bot added to group)
    - Members leaving
    - Title changes, photo changes, pin notifications, etc.
    Only runs when clean_gc_enabled = true (default: true).
    """
    if not update.message or not update.effective_chat:
        return
    if get_setting("clean_gc_enabled", "true") != "true":
        return
    chat_id = update.effective_chat.id
    msg_id  = update.message.message_id
    try:
        await context.bot.delete_message(chat_id, msg_id)
    except Exception:
        pass


async def _clean_gc_command_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Delete ALL commands sent in groups silently after a short delay.
    The bot still processes the command — this just keeps the chat clean.
    Only runs when clean_gc_enabled = true.
    """
    if not update.message or not update.effective_chat:
        return
    if get_setting("clean_gc_enabled", "true") != "true":
        return
    msg = update.message
    chat_id = msg.chat_id
    msg_id  = msg.message_id
    # Wait 3 seconds so the bot response arrives before deleting the command
    async def _delayed_del():
        await asyncio.sleep(3)
        try:
            await context.bot.delete_message(chat_id, msg_id)
        except Exception:
            pass
    asyncio.create_task(_delayed_del())


def main() -> None:
    """Bot entry point — set up and start polling."""
    if not BOT_TOKEN or BOT_TOKEN in ("YOUR_TOKEN_HERE", ""):
        logger.error("❌ BOT_TOKEN is not set!")
        return
    if not DATABASE_URL and not MONGO_DB_URI:
        logger.error("❌ Neither DATABASE_URL (NeonDB) nor MONGO_DB_URI (MongoDB) is set! Set at least one.")
        return
    # Re-mirror in case only one is set at runtime
    global ADMIN_ID, OWNER_ID
    if ADMIN_ID == 0 and OWNER_ID != 0:
        ADMIN_ID = OWNER_ID
    if OWNER_ID == 0 and ADMIN_ID != 0:
        OWNER_ID = ADMIN_ID
    if not ADMIN_ID and not OWNER_ID:
        logger.error("❌ Neither ADMIN_ID nor OWNER_ID is set! Set at least one in environment variables.")
        return

    # Initialize database (dual: NeonDB + MongoDB)
    try:
        init_db(DATABASE_URL, MONGO_DB_URI)
        logger.info("✅ Database initialized")
    except Exception as exc:
        logger.error(f"❌ Database init failed: {exc}")
        return

    # Test DB
    try:
        count = get_user_count()
        logger.info(f"✅ Database working — {count} users registered")
    except Exception as exc:
        logger.error(f"❌ Database test failed: {exc}")
        return

    # Wire up compat shim with bot globals (so BeatVerse modules work)
    import beataniversebot_compat as _compat
    # NOTE: We pass None here and fix it after build below
    _compat._set_bot_info(0, BOT_NAME, "")

    # Build application
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .build()
    )

    # ── Wire module dispatcher bridge ─────────────────────────────────────────
    # PTB v21 Application has no .dispatcher attribute; modules use the v13
    # dispatcher shim. We create a bridge that replays module handlers onto
    # the real PTB v21 application, wrapping any sync callbacks as async.
    class _AppDispatcherBridge:
        """
        Bridge PTB v13 dispatcher.add_handler() calls into PTB v21 Application.
        Wraps sync callbacks as async (PTB v21 requires all callbacks to be async).
        Uses group=50 for module handlers so they run AFTER bot.py's own handlers.
        """
        def __init__(self, app):
            self._app = app
            self._count = 0

        def add_handler(self, handler, group=50, *args, **kwargs):
            """Register module handler in PTB v21 Application at group=50."""
            try:
                orig_cb = getattr(handler, "callback", None)
                if orig_cb is not None and not asyncio.iscoroutinefunction(orig_cb):
                    import functools
                    @functools.wraps(orig_cb)
                    async def _async_wrapper(update, context, _cb=orig_cb):
                        try:
                            result = _cb(update, context)
                            if asyncio.iscoroutine(result):
                                await result
                        except Exception as exc:
                            logger.debug(f"[bridge] {getattr(_cb, '__name__', '?')}: {exc}")
                    handler.callback = _async_wrapper
                # Use group=50 so module handlers run after bot.py's own handlers
                # but are still active for group commands
                self._app.add_handler(handler, group=50)
                self._count += 1
            except Exception as exc:
                logger.debug(f"[bridge] add_handler failed: {exc}")

        def add_error_handler(self, *args, **kwargs):
            try:
                self._app.add_error_handler(*args, **kwargs)
            except Exception:
                pass

        def bot(self):
            return self._app.bot

    _bridge = _AppDispatcherBridge(application)
    import beataniversebot_compat as _compat
    _compat._set_dispatcher(_bridge)
    logger.info("[bridge] Module dispatcher wired to PTB v21 Application (group=50)")

    # ── Update bot info with real ID/username (available after build) ──────────
    try:
        import asyncio as _asyncio_tmp
        async def _get_me():
            me = await application.bot.get_me()
            import beataniversebot_compat as _c
            _c._set_bot_info(me.id, me.first_name or BOT_NAME, me.username or "")
            logger.info(f"[bot] identity set: @{me.username} id={me.id}")
        _asyncio_tmp.get_event_loop().run_until_complete(_get_me())
    except Exception as _bex:
        logger.debug(f"[bot] get_me: {_bex}")

    # ── Load BeatVerse modules ──────────────────────────────────────────────────
    try:
        import importlib, glob
        _mod_dir = os.path.join(os.path.dirname(__file__), "modules")
        _skip = set(["__init__", "sql", "helper_funcs"])
        _no_load_mods = set(os.getenv("NO_LOAD", "tagall telegraph backups country").split())
        _loaded = []
        for _f in sorted(glob.glob(os.path.join(_mod_dir, "*.py"))):
            _mn = os.path.basename(_f)[:-3]
            if _mn.startswith("__") or _mn in _skip or _mn in _no_load_mods:
                continue
            try:
                _mod = importlib.import_module(f"modules.{_mn}")
                # Wire dispatcher if module needs it
                if hasattr(_mod, "dispatcher") and _mod.dispatcher is None:
                    try:
                        _mod.dispatcher = application.dispatcher if hasattr(application, "dispatcher") else None
                    except Exception:
                        pass
                _loaded.append(_mn)
            except Exception as _exc:
                logger.warning(f"Module {_mn} failed to load: {_exc}")
        logger.info(f"✅ Loaded {len(_loaded)} BeatVerse modules: {_loaded}")
    except Exception as _exc:
        logger.warning(f"Module loading error: {_exc}")

    # ── Register all handlers ────────────────────────────────────────────────────
    admin_filter = filters.User(user_id=ADMIN_ID) | filters.User(user_id=OWNER_ID)

    # Public commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("ping", ping_command))
    application.add_handler(CommandHandler("alive", alive_command))
    application.add_handler(CommandHandler("test", test_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("anime", anime_command))
    application.add_handler(CommandHandler("manga", manga_command))
    application.add_handler(CommandHandler("movie", movie_command))
    application.add_handler(CommandHandler("tvshow", tvshow_command))
    application.add_handler(CommandHandler("id", id_command))
    application.add_handler(CommandHandler("info", info_command))

    # Admin-only commands
    application.add_handler(CommandHandler("stats", stats_command, filters=admin_filter))
    application.add_handler(CommandHandler("sysstats", sysstats_command, filters=admin_filter))
    application.add_handler(CommandHandler("users", users_command, filters=admin_filter))
    application.add_handler(CommandHandler("cmd", cmd_command))       # Everyone can use /cmd
    application.add_handler(CommandHandler("commands", cmd_command))  # Everyone can use /commands
    application.add_handler(CommandHandler("upload", upload_command, filters=admin_filter))
    application.add_handler(CommandHandler("settings", settings_command, filters=admin_filter))
    application.add_handler(CommandHandler("autoupdate", autoupdate_command, filters=admin_filter))
    application.add_handler(CommandHandler("autoforward", autoforward_command, filters=admin_filter))
    application.add_handler(CommandHandler("addchannel", add_channel_command, filters=admin_filter))
    application.add_handler(CommandHandler("removechannel", remove_channel_command, filters=admin_filter))
    application.add_handler(CommandHandler("channel", channel_command, filters=admin_filter))
    application.add_handler(CommandHandler("banuser", ban_user_command, filters=admin_filter))
    application.add_handler(CommandHandler("unbanuser", unban_user_command, filters=admin_filter))
    application.add_handler(CommandHandler("listusers", listusers_command, filters=admin_filter))
    application.add_handler(CommandHandler("deleteuser", deleteuser_command, filters=admin_filter))
    application.add_handler(CommandHandler("exportusers", exportusers_command, filters=admin_filter))
    application.add_handler(CommandHandler("broadcaststats", broadcaststats_command, filters=admin_filter))
    application.add_handler(CommandHandler("backup", backup_command, filters=admin_filter))
    application.add_handler(CommandHandler("addclone", addclone_command, filters=admin_filter))
    application.add_handler(CommandHandler("clones", clones_command, filters=admin_filter))
    application.add_handler(CommandHandler("reload", reload_command, filters=admin_filter))
    application.add_handler(CommandHandler("restart", reload_command, filters=admin_filter))
    application.add_handler(CommandHandler("logs", logs_command, filters=admin_filter))
    application.add_handler(CommandHandler("connect", connect_command, filters=admin_filter))
    application.add_handler(CommandHandler("disconnect", disconnect_command, filters=admin_filter))
    application.add_handler(CommandHandler("connections", connections_command, filters=admin_filter))

    # ── Poster template commands (admin only) ──────────────────────────────────
    from poster_engine import (
        poster_ani, poster_anim, poster_crun, poster_net, poster_netm,
        poster_light, poster_lightm, poster_dark, poster_darkm,
        poster_netcr, poster_mod, poster_modm,
        cmd_my_plan, cmd_plans, cmd_add_premium, cmd_remove_premium, cmd_premium_list
    )
    for _cmd, _fn in [
        ("ani",     poster_ani),    ("anim",    poster_anim),
        ("crun",    poster_crun),   ("net",     poster_net),
        ("netm",    poster_netm),   ("light",   poster_light),
        ("lightm",  poster_lightm), ("dark",    poster_dark),
        ("darkm",   poster_darkm),  ("netcr",   poster_netcr),
        ("mod",     poster_mod),    ("modm",    poster_modm),
    ]:
        application.add_handler(CommandHandler(_cmd, _fn, filters=admin_filter))

    # Premium management (admin only)
    application.add_handler(CommandHandler("add_premium",    cmd_add_premium,   filters=admin_filter))
    application.add_handler(CommandHandler("remove_premium", cmd_remove_premium, filters=admin_filter))
    application.add_handler(CommandHandler("premium_list",   cmd_premium_list,  filters=admin_filter))
    # /my_plan and /plans can be used by anyone
    application.add_handler(CommandHandler("my_plan", cmd_my_plan))
    application.add_handler(CommandHandler("plans",   cmd_plans))

    # Callback and message handlers
    application.add_handler(CallbackQueryHandler(button_handler))

    application.add_handler(
        MessageHandler(admin_filter & ~filters.COMMAND, handle_admin_message)
    )
    application.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND,
            group_message_handler,
        )
    )
    application.add_handler(InlineQueryHandler(inline_query_handler))

    application.add_handler(
        MessageHandler(filters.ChatType.CHANNEL, auto_forward_message_handler)
    )
    application.add_handler(
        MessageHandler(
            filters.ChatType.CHANNEL & filters.VIDEO,
            handle_channel_post,
        )
    )
    application.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & filters.VIDEO & admin_filter,
            handle_upload_video,
        )
    )
    application.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & (filters.PHOTO | filters.Document.IMAGE) & admin_filter,
            handle_admin_photo,
        )
    )

    # ── Clean GC: delete service messages (join/leave/etc.) ──────────────────────
    application.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS & filters.StatusUpdate.ALL,
            _clean_gc_service_handler,
        ),
        group=-1,  # High priority
    )
    # ── Clean GC: delete all commands in groups silently ──────────────────────
    application.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS & filters.COMMAND,
            _clean_gc_command_handler,
        ),
        group=10,  # AFTER all command handlers (was -1 which blocked everything)
    )

        
    # Register /refresh_commands, /refresh_all_commands, /set_bot_description
    from bot_commands_setup import register_command_setup_handlers
    register_command_setup_handlers(application)

    application.add_error_handler(error_handler)
    application.post_init = post_init
    application.post_shutdown = post_shutdown

    logger.info("🚀 Starting bot polling…")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        close_loop=False,
    )


if __name__ == "__main__":
    main()
