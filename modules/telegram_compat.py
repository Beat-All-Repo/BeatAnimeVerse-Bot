"""
telegram_compat.py
===================
PTB v13 → v21 compatibility shim for BeatVerse modules.

All modules in the modules/ directory were written for python-telegram-bot v13.x.
The main bot runs on PTB v21.x. Many names moved or changed.

This shim re-exports everything the modules need under the old names.

Import order in modules/__init__.py ensures this runs before any module loads.

Credits: BeatAnime | @BeatAnime | @Beat_Anime_Discussion
"""

# ── PTB v21 constants now live in telegram.constants ─────────────────────────
from telegram.constants import ParseMode, ChatAction, MessageLimit
from telegram import (
    Bot, Update, User, Chat, Message, ChatPermissions,
    InlineKeyboardButton, InlineKeyboardMarkup,
    InlineQueryResultArticle, InlineQueryResultPhoto,
    InputTextMessageContent, MessageEntity, CallbackQuery,
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, InlineQueryHandler,
    ContextTypes, filters as _filters_module,
)
from telegram.error import (
    TelegramError, BadRequest, NetworkError,
    TimedOut, Forbidden, RetryAfter, InvalidToken,
)
from telegram.helpers import mention_html, escape_markdown

# ── MAX_MESSAGE_LENGTH moved to MessageLimit ──────────────────────────────────
MAX_MESSAGE_LENGTH = MessageLimit.MAX_TEXT_LENGTH  # 4096

# ── Unauthorized → Forbidden in v20+ ─────────────────────────────────────────
Unauthorized = Forbidden

# ── CallbackContext — still exists in v21 ────────────────────────────────────
from telegram.ext import CallbackContext

# ── Filters → filters (lowercased, new API) ───────────────────────────────────
# PTB v13 used class Filters, v21 uses module filters
# We create a compat class that wraps common Filters.xxx attributes

class _FiltersCompat:
    """
    Compat wrapper: modules do `from telegram.ext import Filters`
    then use Filters.text, Filters.command, Filters.reply, etc.
    This maps them to PTB v21 filters module equivalents.
    """
    # Text types
    text            = _filters_module.TEXT
    command         = _filters_module.COMMAND
    reply           = _filters_module.REPLY
    forwarded       = _filters_module.FORWARDED
    document        = _filters_module.Document.ALL
    photo           = _filters_module.PHOTO
    video           = _filters_module.VIDEO
    audio           = _filters_module.AUDIO
    voice           = _filters_module.VOICE
    sticker         = _filters_module.Sticker.ALL
    contact         = _filters_module.CONTACT
    location        = _filters_module.LOCATION
    venue           = _filters_module.VENUE
    game            = _filters_module.GAME
    invoice         = _filters_module.INVOICE
    animation       = _filters_module.ANIMATION
    caption         = _filters_module.CAPTION
    entity          = _filters_module.Entity
    all             = _filters_module.ALL

    # Chat types
    private         = _filters_module.ChatType.PRIVATE
    group           = _filters_module.ChatType.GROUP
    supergroup      = _filters_module.ChatType.SUPERGROUP
    chat_type       = _filters_module.ChatType

    # User/chat filters
    user            = _filters_module.User
    chat            = _filters_module.Chat
    language        = _filters_module.Language

    # Status updates
    status_update   = _filters_module.StatusUpdate
    new_chat_members = _filters_module.StatusUpdate.NEW_CHAT_MEMBERS
    left_chat_member = _filters_module.StatusUpdate.LEFT_CHAT_MEMBER

    # Regex
    regex           = _filters_module.Regex

    # Document subtypes
    class Document:
        ALL         = _filters_module.Document.ALL
        APK         = _filters_module.Document.APK
        ZIP         = _filters_module.Document.ZIP
        PDF         = _filters_module.Document.PDF
        IMAGE       = _filters_module.Document.IMAGE
        VIDEO       = _filters_module.Document.VIDEO
        AUDIO       = _filters_module.Document.AUDIO
        TEXT        = _filters_module.Document.TEXT
        MimeType    = _filters_module.Document.MimeType
        FileExtension = _filters_module.Document.FileExtension

    # Sticker subtypes
    class Sticker:
        ALL         = _filters_module.Sticker.ALL
        ANIMATED    = _filters_module.Sticker.ANIMATED
        STATIC      = _filters_module.Sticker.STATIC
        VIDEO       = _filters_module.Sticker.VIDEO

    def __call__(self, *args, **kwargs):
        """Callable fallback."""
        return _filters_module.ALL


Filters = _FiltersCompat()

# ── DispatcherHandlerStop — v21 replacement ────────────────────────────────────
# In PTB v13 you could raise DispatcherHandlerStop to stop handler chain.
# In PTB v21 this is ApplicationHandlerStop.
try:
    from telegram.ext import ApplicationHandlerStop as DispatcherHandlerStop
except ImportError:
    class DispatcherHandlerStop(Exception):
        """Compat stub for DispatcherHandlerStop."""
        pass

# ── run_async kwarg removed in v21 ───────────────────────────────────────────
# PTB v13: CommandHandler("cmd", fn, run_async=True)
# PTB v21: run_async doesn't exist — everything is async natively
# We monkey-patch CommandHandler, MessageHandler, CallbackQueryHandler
# to silently ignore run_async kwarg

_orig_CommandHandler_init = CommandHandler.__init__
def _patched_ch_init(self, *args, **kwargs):
    kwargs.pop('run_async', None)
    _orig_CommandHandler_init(self, *args, **kwargs)
CommandHandler.__init__ = _patched_ch_init

_orig_MessageHandler_init = MessageHandler.__init__
def _patched_mh_init(self, *args, **kwargs):
    kwargs.pop('run_async', None)
    _orig_MessageHandler_init(self, *args, **kwargs)
MessageHandler.__init__ = _patched_mh_init

_orig_CQH_init = CallbackQueryHandler.__init__
def _patched_cqh_init(self, *args, **kwargs):
    kwargs.pop('run_async', None)
    _orig_CQH_init(self, *args, **kwargs)
CallbackQueryHandler.__init__ = _patched_cqh_init

# ── Monkey-patch telegram module namespace ────────────────────────────────────
# Some modules do `import telegram` then use `telegram.ParseMode`
# or `telegram.MAX_MESSAGE_LENGTH` — inject these into the telegram namespace
import telegram as _tg
if not hasattr(_tg, 'ParseMode'):
    _tg.ParseMode = ParseMode
if not hasattr(_tg, 'MAX_MESSAGE_LENGTH'):
    _tg.MAX_MESSAGE_LENGTH = MAX_MESSAGE_LENGTH
if not hasattr(_tg, 'TelegramError'):
    _tg.TelegramError = TelegramError
if not hasattr(_tg, 'Unauthorized'):
    _tg.Unauthorized = Forbidden

# ── Inject into telegram namespace (v13 modules do: from telegram import ParseMode) ──
import telegram as _tg
_inject_tg = {
    'ParseMode': ParseMode,
    'MAX_MESSAGE_LENGTH': MAX_MESSAGE_LENGTH,
    'TelegramError': TelegramError,
    'Unauthorized': Forbidden,
    'ChatAction': ChatAction,
    'InlineKeyboardButton': InlineKeyboardButton,
    'InlineKeyboardMarkup': InlineKeyboardMarkup,
    'InlineQueryResultArticle': InlineQueryResultArticle,
    'InlineQueryResultPhoto': InlineQueryResultPhoto,
    'InputTextMessageContent': InputTextMessageContent,
    'MessageEntity': MessageEntity,
    'CallbackQuery': CallbackQuery,
    'Bot': Bot, 'Update': Update, 'User': User,
    'Chat': Chat, 'Message': Message, 'ChatPermissions': ChatPermissions,
}
for _k, _v in _inject_tg.items():
    if not hasattr(_tg, _k):
        setattr(_tg, _k, _v)

# ── Inject into telegram.ext namespace ───────────────────────────────────────
import telegram.ext as _tge
if not hasattr(_tge, 'Filters'):
    _tge.Filters = Filters
if not hasattr(_tge, 'CallbackContext'):
    pass  # Already exists in v21

# ── RegexHandler — removed in PTB v21, recreate it ───────────────────────────
import re as _re
class RegexHandler(MessageHandler):
    """PTB v13 RegexHandler compat for v21."""
    def __init__(self, pattern, callback, **kwargs):
        kwargs.pop('run_async', None)
        super().__init__(
            filters=_filters_module.Regex(_re.compile(pattern)),
            callback=callback,
        )

_tge.RegexHandler = RegexHandler

# ── DispatcherHandlerStop injection ───────────────────────────────────────────
_tge.DispatcherHandlerStop = DispatcherHandlerStop

# ── Unauthorized injection into telegram.error ────────────────────────────────
import telegram.error as _te
if not hasattr(_te, 'Unauthorized'):
    _te.Unauthorized = Forbidden

# ── Fake telegram.utils module (used by many old modules) ─────────────────────
import sys as _sys
import types as _types

if 'telegram.utils' not in _sys.modules:
    _utils_mod = _types.ModuleType('telegram.utils')
    _sys.modules['telegram.utils'] = _utils_mod

if 'telegram.utils.helpers' not in _sys.modules:
    _utils_helpers = _types.ModuleType('telegram.utils.helpers')
    _utils_helpers.mention_html = mention_html
    _utils_helpers.escape_markdown = escape_markdown
    _sys.modules['telegram.utils.helpers'] = _utils_helpers
    _sys.modules['telegram.utils'].helpers = _utils_helpers

# ── Export everything modules might need ──────────────────────────────────────
__all__ = [
    'ParseMode', 'ChatAction', 'MAX_MESSAGE_LENGTH',
    'Bot', 'Update', 'User', 'Chat', 'Message', 'ChatPermissions',
    'InlineKeyboardButton', 'InlineKeyboardMarkup',
    'InlineQueryResultArticle', 'InlineQueryResultPhoto',
    'InputTextMessageContent', 'MessageEntity', 'CallbackQuery',
    'CommandHandler', 'MessageHandler', 'CallbackQueryHandler',
    'InlineQueryHandler', 'ContextTypes', 'CallbackContext',
    'Filters', 'DispatcherHandlerStop', 'RegexHandler',
    'TelegramError', 'BadRequest', 'NetworkError', 'TimedOut',
    'Forbidden', 'Unauthorized', 'RetryAfter', 'InvalidToken',
    'mention_html', 'escape_markdown',
]
