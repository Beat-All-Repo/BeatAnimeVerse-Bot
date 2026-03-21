# ====================================================================
# PLACE AT: /app/BeatVerseProbot/__init__.py
# ACTION: CREATE new folder + file
# ====================================================================
"""
BeatVerseProbot — compatibility stub package.
All modules that import from BeatVerseProbot get safe stubs here.
No functionality is removed — these are shims so legacy modules load.
"""
import os, logging
logger = logging.getLogger(__name__)

# Common constants modules expect
TOKEN = os.getenv("BOT_TOKEN", "")
STATS = {}
USER_INFO = {}
DATA_IMPORT = {}
DATA_EXPORT = {}
CHAT_SETTINGS = {}
HELPABLE = {}
IMPORTED = {}
