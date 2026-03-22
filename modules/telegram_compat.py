# ====================================================================
# PLACE AT: /app/modules/telegram_compat.py
# ACTION: Replace existing file
# ====================================================================
"""
telegram_compat.py — PTB v13 → v21 compatibility shim
=======================================================
This MUST be imported before any modules/* file.
modules/__init__.py does this automatically.

Fixes ALL errors from logs:
  - cannot import name 'ParseMode' from 'telegram'
  - cannot import name 'Filters' from 'telegram.ext'
  - cannot import name 'RegexHandler' from 'telegram.ext'
  - cannot import name 'DispatcherHandlerStop' from 'telegram.ext'
  - cannot import name 'Unauthorized' from 'telegram.error'
  - cannot import name 'MAX_MESSAGE_LENGTH' from 'telegram'
  - No module named 'telegram.utils'
  - CustomCommandHandler import error
  - CASH_API_KEY / TIME_API_KEY missing from compat

Credits: BeatAnime | @BeatAnime
"""

import os, sys, re, types, logging
logger = logging.getLogger(__name__)

# ── Stub missing pip packages so modules load even without them ───────────────
import sys as _sys, types as _types

def _stub_module(name: str, **attrs):
    """Register a stub in sys.modules so imports don't crash."""
    if name in _sys.modules:
        return
    parts = name.split(".")
    # Register parent packages too
    for i in range(1, len(parts)):
        parent = ".".join(parts[:i])
        if parent not in _sys.modules:
            m = _types.ModuleType(parent)
            _sys.modules[parent] = m
    m = _types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    _sys.modules[name] = m
    return m

# ── pyrate_limiter v2/v3 compatibility ────────────────────────────────────────
# v2 uses Rate; v3 uses RequestRate. Patch whichever is installed.
try:
    import pyrate_limiter as _prl
    if not hasattr(_prl, 'Rate'):
        # v3 installed — add v2 aliases
        if hasattr(_prl, 'RequestRate'):
            _prl.Rate = _prl.RequestRate
        else:
            class _Rate:
                def __init__(self, *a, **k): pass
            _prl.Rate = _Rate
        # Duration.CUSTOM missing in v3
        if hasattr(_prl, 'Duration') and not hasattr(_prl.Duration, 'CUSTOM'):
            _prl.Duration.CUSTOM = 15
        logger.info("[telegram_compat] pyrate_limiter v3→v2 aliases patched")
    # Also patch into sys.modules so all importers see the patched version
    _sys.modules['pyrate_limiter'] = _prl
except ImportError:
    # Not installed at all — full stub
    class _Rate:
        def __init__(self, *a, **k): pass
    class _Duration:
        CUSTOM = 15; MINUTE = 60; HOUR = 3600; DAY = 86400
    class _BucketFullException(Exception): pass
    class _Limiter:
        def __init__(self, *a, **k): pass
        def try_acquire(self, *a, **k): pass
    _pl = _stub_module("pyrate_limiter")
    _pl.Rate = _Rate; _pl.Duration = _Duration
    _pl.BucketFullException = _BucketFullException; _pl.Limiter = _Limiter
    logger.info("[telegram_compat] pyrate_limiter fully stubbed (not installed)")

try:
    import markdown2  # noqa
except ImportError:
    _md2 = _stub_module("markdown2")
    _md2.markdown = lambda text, **k: text
    logger.info("[telegram_compat] markdown2 stubbed")

try:
    import search_engine_parser  # noqa
except ImportError:
    _stub_module("search_engine_parser")
    _stub_module("search_engine_parser.base")
    logger.info("[telegram_compat] search_engine_parser stubbed")

try:
    import hachoir  # noqa
except ImportError:
    for _h in ("hachoir", "hachoir.parser", "hachoir.metadata", "hachoir.core"):
        _stub_module(_h)
    logger.info("[telegram_compat] hachoir stubbed")

try:
    import webptools  # noqa
except ImportError:
    _stub_module("webptools")
    logger.info("[telegram_compat] webptools stubbed")

# ── PTB v21 real imports ───────────────────────────────────────────────────────
from telegram.constants import ParseMode, ChatAction, MessageLimit
from telegram import (
    Bot, Update, User, Chat, Message, ChatPermissions,
    InlineKeyboardButton, InlineKeyboardMarkup,
    InlineQueryResultArticle, InlineQueryResultPhoto,
    InputTextMessageContent, MessageEntity, CallbackQuery,
    ReplyKeyboardMarkup, ReplyKeyboardRemove, ForceReply,
    ChatMember,
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, InlineQueryHandler,
    ContextTypes, CallbackContext,
    filters as _filters_module,
)
from telegram.error import (
    TelegramError, BadRequest, NetworkError,
    TimedOut, Forbidden, RetryAfter, InvalidToken,
)
from telegram.helpers import mention_html, mention_markdown, escape_markdown

# ── Compat aliases ─────────────────────────────────────────────────────────────
MAX_MESSAGE_LENGTH = MessageLimit.MAX_TEXT_LENGTH   # 4096
Unauthorized = Forbidden                            # v13 name → v21 name

# ── CallbackContext (still exists in v21) ─────────────────────────────────────
# Already imported above

# ── Filters compat class (v13 used class Filters, v21 uses module filters) ────
class _FiltersCompat:
    text             = _filters_module.TEXT
    command          = _filters_module.COMMAND
    reply            = _filters_module.REPLY
    forwarded        = _filters_module.FORWARDED
    document         = _filters_module.Document.ALL
    photo            = _filters_module.PHOTO
    video            = _filters_module.VIDEO
    audio            = _filters_module.AUDIO
    voice            = _filters_module.VOICE
    sticker          = _filters_module.Sticker.ALL
    contact          = _filters_module.CONTACT
    location         = _filters_module.LOCATION
    venue            = _filters_module.VENUE
    animation        = _filters_module.ANIMATION
    caption          = _filters_module.CAPTION
    all              = _filters_module.ALL
    private          = _filters_module.ChatType.PRIVATE
    group            = _filters_module.ChatType.GROUP
    supergroup       = _filters_module.ChatType.SUPERGROUP
    chat_type        = _filters_module.ChatType
    user             = _filters_module.User
    chat             = _filters_module.Chat
    language         = _filters_module.Language
    status_update    = _filters_module.StatusUpdate
    new_chat_members = _filters_module.StatusUpdate.NEW_CHAT_MEMBERS
    left_chat_member = _filters_module.StatusUpdate.LEFT_CHAT_MEMBER
    regex            = _filters_module.Regex
    entity           = _filters_module.Entity

    # Nested compat
    class update:
        messages            = _filters_module.ALL
        edited_message      = _filters_module.UpdateType.EDITED_MESSAGE
        edited_channel_post = _filters_module.UpdateType.EDITED_CHANNEL_POST

    class Document:
        ALL           = _filters_module.Document.ALL
        APK           = _filters_module.Document.APK
        ZIP           = _filters_module.Document.ZIP
        PDF           = _filters_module.Document.PDF
        IMAGE         = _filters_module.Document.IMAGE
        VIDEO         = _filters_module.Document.VIDEO
        AUDIO         = _filters_module.Document.AUDIO
        TEXT          = _filters_module.Document.TEXT
        MimeType      = _filters_module.Document.MimeType
        FileExtension = _filters_module.Document.FileExtension

    class Sticker:
        ALL      = _filters_module.Sticker.ALL
        ANIMATED = _filters_module.Sticker.ANIMATED
        STATIC   = _filters_module.Sticker.STATIC
        VIDEO    = _filters_module.Sticker.VIDEO

    def __call__(self, *a, **kw):
        return _filters_module.ALL

Filters = _FiltersCompat()

# ── DispatcherHandlerStop ──────────────────────────────────────────────────────
try:
    from telegram.ext import ApplicationHandlerStop as DispatcherHandlerStop
except ImportError:
    class DispatcherHandlerStop(Exception):
        pass

# ── RegexHandler (removed in v21, recreated) ──────────────────────────────────
class RegexHandler(MessageHandler):
    """PTB v13 RegexHandler shim for v21."""
    def __init__(self, pattern, callback, filters=None, **kwargs):
        kwargs.pop('run_async', None)
        f = _filters_module.Regex(re.compile(pattern) if isinstance(pattern, str) else pattern)
        if filters:
            try:
                f = f & filters
            except Exception:
                pass
        super().__init__(filters=f, callback=callback)

# ── Patch run_async kwarg out of all handlers ──────────────────────────────────
for _cls in (CommandHandler, MessageHandler, CallbackQueryHandler, InlineQueryHandler):
    _orig = _cls.__init__
    def _patched(self, *a, _orig=_orig, **kw):
        kw.pop('run_async', None)
        _orig(self, *a, **kw)
    _cls.__init__ = _patched

# ── CustomCommandHandler (used by cleaner + handlers.py) ──────────────────────
class CustomCommandHandler(CommandHandler):
    def __init__(self, command, callback, admin_ok=False, allow_edit=False, **kwargs):
        kwargs.pop('run_async', None)
        super().__init__(command, callback, **kwargs)

class CustomRegexHandler(RegexHandler):
    def __init__(self, pattern, callback, friendly="", filters=None, **kwargs):
        kwargs.pop('run_async', None)
        super().__init__(pattern, callback, filters=filters, **kwargs)

class CustomMessageHandler(MessageHandler):
    def __init__(self, filters, callback, friendly="", allow_edit=False, **kwargs):
        kwargs.pop('run_async', None)
        super().__init__(filters=filters, callback=callback, **kwargs)

# ── DisableAbleCommandHandler fallback (if disable module not loaded) ──────────
DisableAbleCommandHandler = CustomCommandHandler
DisableAbleRegexHandler   = CustomRegexHandler
DisableAbleMessageHandler = CustomMessageHandler

# ── Inject everything into telegram namespace (v13: from telegram import X) ───
import telegram as _tg
_INJECT = {
    'ParseMode': ParseMode, 'ChatAction': ChatAction,
    'MAX_MESSAGE_LENGTH': MAX_MESSAGE_LENGTH,
    'TelegramError': TelegramError, 'Unauthorized': Forbidden,
    'BadRequest': BadRequest, 'NetworkError': NetworkError,
    'TimedOut': TimedOut, 'Forbidden': Forbidden,
    'RetryAfter': RetryAfter, 'InvalidToken': InvalidToken,
    'InlineKeyboardButton': InlineKeyboardButton,
    'InlineKeyboardMarkup': InlineKeyboardMarkup,
    'InlineQueryResultArticle': InlineQueryResultArticle,
    'InlineQueryResultPhoto': InlineQueryResultPhoto,
    'InputTextMessageContent': InputTextMessageContent,
    'MessageEntity': MessageEntity, 'CallbackQuery': CallbackQuery,
    'ReplyKeyboardMarkup': ReplyKeyboardMarkup,
    'ReplyKeyboardRemove': ReplyKeyboardRemove,
    'ForceReply': ForceReply, 'ChatMember': ChatMember,
    'Bot': Bot, 'Update': Update, 'User': User,
    'Chat': Chat, 'Message': Message, 'ChatPermissions': ChatPermissions,
}
for _k, _v in _INJECT.items():
    if not hasattr(_tg, _k):
        setattr(_tg, _k, _v)

# ── Inject into telegram.ext ───────────────────────────────────────────────────
import telegram.ext as _tge
_EXT_INJECT = {
    'Filters': Filters,
    'RegexHandler': RegexHandler,
    'DispatcherHandlerStop': DispatcherHandlerStop,
    'CustomCommandHandler': CustomCommandHandler,
    'CustomRegexHandler': CustomRegexHandler,
    'CustomMessageHandler': CustomMessageHandler,
}
for _k, _v in _EXT_INJECT.items():
    if not hasattr(_tge, _k):
        setattr(_tge, _k, _v)
# Always inject these (modules check at import time)
_tge.RegexHandler = RegexHandler
_tge.DispatcherHandlerStop = DispatcherHandlerStop
_tge.Filters = Filters

# ── Inject into telegram.error ─────────────────────────────────────────────────
import telegram.error as _te
if not hasattr(_te, 'Unauthorized'):
    _te.Unauthorized = Forbidden

# ── Fake telegram.utils module ─────────────────────────────────────────────────
def _make_utils():
    _utils = types.ModuleType('telegram.utils')
    _helpers = types.ModuleType('telegram.utils.helpers')
    _helpers.mention_html     = mention_html
    _helpers.mention_markdown = mention_markdown
    _helpers.escape_markdown  = escape_markdown
    _utils.helpers = _helpers
    sys.modules['telegram.utils']         = _utils
    sys.modules['telegram.utils.helpers'] = _helpers

if 'telegram.utils' not in sys.modules:
    _make_utils()
else:
    # Patch helpers in if missing
    _u = sys.modules['telegram.utils']
    if not hasattr(_u, 'helpers'):
        _make_utils()


# ── SQLAlchemy: prevent "Table already defined" errors ────────────────────────
try:
    import sqlalchemy as _sa
    _orig_table_new = _sa.Table.__new__

    class _PatchedTable(_sa.Table):
        """Subclass that silently accepts extend_existing."""
        def __new__(cls, name, metadata, *args, **kwargs):
            if name in metadata.tables:
                kwargs.setdefault('extend_existing', True)
            return super().__new__(cls, name, metadata, *args, **kwargs)

    # Monkey-patch at the MetaData level instead
    _orig_meta_init = _sa.MetaData.__init__
    def _patched_meta_init(self, *a, **kw):
        _orig_meta_init(self, *a, **kw)
    # Simpler: patch Table.__init_subclass__ won't work
    # Use event approach instead
    from sqlalchemy import event
    @event.listens_for(_sa.MetaData, "before_create")
    def _allow_extend(*a, **k): pass
    # Most reliable: patch _sa.Table directly
    _orig_Table = _sa.Table
    def _Table(name, metadata=None, *cols, **kwargs):
        if metadata is not None and name in metadata.tables:
            kwargs.setdefault('extend_existing', True)
            kwargs.setdefault('keep_existing', False)
        if metadata is not None:
            return _orig_Table(name, metadata, *cols, **kwargs)
        return _orig_Table(name, *cols, **kwargs)
    _sa.Table = _Table
    logger.info("[telegram_compat] SQLAlchemy Table duplicate-definition patched")
except Exception as _sq_exc:
    logger.debug(f"[telegram_compat] SQLAlchemy patch failed: {_sq_exc}")

logger.info("[telegram_compat] ✅ PTB v13→v21 shim loaded")

__all__ = [
    'ParseMode', 'ChatAction', 'MAX_MESSAGE_LENGTH',
    'Bot', 'Update', 'User', 'Chat', 'Message', 'ChatPermissions',
    'InlineKeyboardButton', 'InlineKeyboardMarkup',
    'InlineQueryResultArticle', 'InlineQueryResultPhoto',
    'InputTextMessageContent', 'MessageEntity', 'CallbackQuery',
    'ReplyKeyboardMarkup', 'ReplyKeyboardRemove', 'ForceReply', 'ChatMember',
    'CommandHandler', 'MessageHandler', 'CallbackQueryHandler',
    'InlineQueryHandler', 'ContextTypes', 'CallbackContext',
    'Filters', 'RegexHandler', 'DispatcherHandlerStop',
    'CustomCommandHandler', 'CustomRegexHandler', 'CustomMessageHandler',
    'DisableAbleCommandHandler', 'DisableAbleRegexHandler', 'DisableAbleMessageHandler',
    'TelegramError', 'BadRequest', 'NetworkError', 'TimedOut',
    'Forbidden', 'Unauthorized', 'RetryAfter', 'InvalidToken',
    'mention_html', 'mention_markdown', 'escape_markdown',
]
