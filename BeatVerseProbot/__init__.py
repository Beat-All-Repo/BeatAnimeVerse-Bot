# ==============================================================================
# PLACE AT: /app/BeatVerseProbot/__init__.py
# ACTION: Replace existing file
# ==============================================================================
"""
BeatVerseProbot — compatibility stub package.
Patches sys.modules so all BeatVerseProbot.* imports resolve safely.
"""
import os, sys, types, logging
logger = logging.getLogger(__name__)

# ── Common constants ───────────────────────────────────────────────────────────
TOKEN = os.getenv("BOT_TOKEN", "")
STATS = {}
USER_INFO = {}
DATA_IMPORT = {}
DATA_EXPORT = {}
CHAT_SETTINGS = {}
HELPABLE = {}
IMPORTED = {}
MIGRATEABLE = []
USER_SETTINGS = {}
EXPORTED = {}

# ── Ensure all BeatVerseProbot.* paths exist in sys.modules ───────────────────
_this = sys.modules[__name__]

def _make_stub(name: str, **attrs):
    """Create and register a stub module."""
    if name in sys.modules:
        return sys.modules[name]
    m = types.ModuleType(name)
    m.__package__ = name.rsplit(".", 1)[0] if "." in name else name
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m

# Register all submodule paths that modules/* might try to import
_stub_paths = [
    "BeatVerseProbot",
    "BeatVerseProbot.modules",
    "BeatVerseProbot.modules.fun_strings",
    "BeatVerseProbot.modules.helper_funcs",
    "BeatVerseProbot.utils",
    "BeatVerseProbot.utils.mongo",
    "BeatVerseProbot.utils.fonts",
    "BeatVerseProbot.events",
    "BeatVerseProbot.__main__",
]

for _path in _stub_paths:
    if _path not in sys.modules:
        _make_stub(_path)

# Patch self into sys.modules properly
sys.modules["BeatVerseProbot"] = _this

# ── events.register decorator ─────────────────────────────────────────────────
def _register(*args, **kwargs):
    def decorator(func): return func
    if args and callable(args[0]): return args[0]
    return decorator

_events_mod = sys.modules.get("BeatVerseProbot.events") or _make_stub("BeatVerseProbot.events")
_events_mod.register = _register
setattr(_this, "events", _events_mod)

# ── fun_strings forward ────────────────────────────────────────────────────────
_fun_mod = sys.modules.get("BeatVerseProbot.modules.fun_strings") or _make_stub("BeatVerseProbot.modules.fun_strings")
try:
    from modules.fun_strings import RUN_STRINGS, SLAP_TEMPLATES, PAT_TEMPLATES, ITEMS
    _fun_mod.RUN_STRINGS = RUN_STRINGS
    _fun_mod.SLAP_TEMPLATES = SLAP_TEMPLATES
    _fun_mod.PAT_TEMPLATES = PAT_TEMPLATES
    _fun_mod.ITEMS = ITEMS
except Exception:
    _fun_mod.RUN_STRINGS = ("Running!",)
    _fun_mod.SLAP_TEMPLATES = ("{user1} slapped {user2}.",)
    _fun_mod.PAT_TEMPLATES = ("{user1} patted {user2}.",)
    _fun_mod.ITEMS = ("bat",)
setattr(_this, "fun_strings_mod", _fun_mod)

# ── __main__ stubs ─────────────────────────────────────────────────────────────
_main_mod = sys.modules.get("BeatVerseProbot.__main__") or _make_stub("BeatVerseProbot.__main__")
for _attr in ("TOKEN","STATS","USER_INFO","DATA_IMPORT","DATA_EXPORT",
              "CHAT_SETTINGS","HELPABLE","IMPORTED","MIGRATEABLE","USER_SETTINGS","EXPORTED"):
    setattr(_main_mod, _attr, globals().get(_attr, {}))

logger.debug("[BeatVerseProbot] stub package fully initialised")
