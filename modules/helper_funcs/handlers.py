# ====================================================================
# PLACE AT: /app/modules/helper_funcs/handlers.py
# ACTION: Replace existing file
# ====================================================================
try:
    from pyrate_limiter import BucketFullException, Duration, Limiter, Rate
except ImportError:
    # pyrate_limiter v2 compat — v2 uses Rate, v3 uses RequestRate
    try:
        from pyrate_limiter import RequestRate as Rate, Duration, Limiter, BucketFullException
        # v3 Duration has no CUSTOM — add it
        if not hasattr(Duration, 'CUSTOM'):
            Duration.CUSTOM = 15
    except Exception:
        # Full stub fallback
        class Rate:
            def __init__(self, *a, **k): pass
        class Duration:
            CUSTOM = 15; MINUTE = 60; HOUR = 3600; DAY = 86400
        class BucketFullException(Exception): pass
        class Limiter:
            def __init__(self, *a, **k): pass
            def try_acquire(self, *a): pass
from telegram import Update
from telegram.ext import CommandHandler, MessageHandler
try:
    from telegram.ext import Filters, RegexHandler
except ImportError:
    from telegram.ext import filters as Filters
    RegexHandler = MessageHandler

import modules.sql.blacklistusers_sql as sql
from beataniversebot_compat import ALLOW_EXCL, DEMONS, DEV_USERS, DRAGONS, TIGERS, WOLVES

if ALLOW_EXCL:
    CMD_STARTERS = ("/", "!")
else:
    CMD_STARTERS = "/"


class AntiSpam:
    def __init__(self):
        self.whitelist = (
            (DEV_USERS or [])
            + (DRAGONS or [])
            + (WOLVES or [])
            + (DEMONS or [])
            + (TIGERS or [])
        )
        # Values are HIGHLY experimental, its recommended you pay attention to our commits as we will be adjusting the values over time with what suits best.
        Duration.CUSTOM = 15  # Custom duration, 15 seconds
        self.sec_limit = Rate(6, Duration.CUSTOM)  # 6 / Per 15 Seconds
        self.min_limit = Rate(20, Duration.MINUTE)  # 20 / Per minute
        self.hour_limit = Rate(100, Duration.HOUR)  # 100 / Per hour
        self.daily_limit = Rate(1000, Duration.DAY)  # 1000 / Per day
        self.rates = [self.sec_limit, self.min_limit, self.hour_limit, self.daily_limit]
        self.limiter = Limiter(self.rates)

    def check_user(self, user):
        """
        Return True if user is to be ignored else False
        """
        if user in self.whitelist:
            return False
        try:
            self.limiter.try_acquire(user)
            return False
        except BucketFullException:
            return True


SpamChecker = AntiSpam()
MessageHandlerChecker = AntiSpam()


class CustomCommandHandler(CommandHandler):
    """PTB v21 compatible — no check_update override.
    PTB v13's check_update used message.bot.username which was removed in v21.
    """
    def __init__(self, command, callback, admin_ok=False, allow_edit=False, **kwargs):
        kwargs.pop('run_async', None)  # PTB v21 compat
        super().__init__(command, callback, **kwargs)
    # Use parent CommandHandler.check_update (PTB v21 compatible)


class CustomRegexHandler(MessageHandler):
    """PTB v21: RegexHandler removed, use MessageHandler with Regex filter."""
    def __init__(self, pattern, callback, friendly="", **kwargs):
        kwargs.pop('run_async', None)
        import re as _re
        from telegram.ext import filters as _f
        super().__init__(_f.Regex(_re.compile(pattern)), callback, **kwargs)


class CustomMessageHandler(MessageHandler):
    def __init__(self, filters_arg, callback, friendly="", allow_edit=False, **kwargs):
        kwargs.pop('run_async', None)
        super().__init__(filters_arg, callback, **kwargs)
