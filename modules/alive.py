# ==============================================================================
# PLACE AT: /app/modules/alive.py
# ACTION: Replace existing file
# ==============================================================================
"""alive.py — /alive command, works with PTB v21 + pyrogram stub."""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, CommandHandler
from beataniversebot_compat import BOT_NAME, BOT_USERNAME, OWNER_ID, START_IMG, SUPPORT_CHAT, dispatcher

logger = logging.getLogger(__name__)

try:
    from telegram import __version__ as telever
except Exception:
    telever = "N/A"
try:
    from telethon import __version__ as tlhver
except Exception:
    tlhver = "N/A"
try:
    from pyrogram import __version__ as pyrover
except Exception:
    pyrover = "N/A"


async def alive_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/alive — show bot is running with version info."""
    user = update.effective_user
    mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>' if user else "you"

    text = (
        f"<b>ʜᴇʏ {mention},\n\nɪ ᴀᴍ {BOT_NAME}</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        f"» <b>ᴍʏ ᴅᴇᴠᴇʟᴏᴘᴇʀ :</b> <a href='https://t.me/BeatAnime'>Beat</a>\n\n"
        f"» <b>ʟɪʙʀᴀʀʏ ᴠᴇʀsɪᴏɴ :</b> <code>{telever}</code>\n\n"
        f"» <b>ᴛᴇʟᴇᴛʜᴏɴ ᴠᴇʀsɪᴏɴ :</b> <code>{tlhver}</code>\n\n"
        f"» <b>ᴘʏʀᴏɢʀᴀᴍ ᴠᴇʀsɪᴏɴ :</b> <code>{pyrover}</code>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
    )
    buttons = [[
        InlineKeyboardButton("ʜᴇʟᴘ", url=f"https://t.me/{BOT_USERNAME}?start=help"),
        InlineKeyboardButton("sᴜᴘᴘᴏʀᴛ", url=f"https://t.me/{SUPPORT_CHAT}"),
    ]]
    markup = InlineKeyboardMarkup(buttons)

    if START_IMG:
        try:
            await update.message.reply_photo(photo=START_IMG, caption=text,
                                              parse_mode=ParseMode.HTML, reply_markup=markup)
            return
        except Exception:
            pass
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)


# Also register via dispatcher shim for legacy compatibility
try:
    from modules.disable import DisableAbleCommandHandler
    ALIVE_HANDLER = DisableAbleCommandHandler("alive", alive_cmd, run_async=True)
    dispatcher.add_handler(ALIVE_HANDLER)
except Exception:
    pass

__mod_name__ = "Aʟɪᴠᴇ"
__command_list__ = ["alive"]
