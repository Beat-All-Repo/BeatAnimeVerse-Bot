#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BeatAniVerse Bot — Filter Poster Integration
=============================================
When a keyword/anime title filter is matched in a group:
  1. Checks the poster cache (DB + channel)
  2. If cached: immediately forwards the saved poster — FAST PATH
  3. If not cached: generates new poster (with <5 sec loading indicator)
     then saves to poster DB channel + caches in DB
  4. Timeout guard: if generation >5 sec, sends placeholder immediately
     then edits with result when ready

Poster DB Channel:
  • Set POSTER_DB_CHANNEL env var (channel ID like -1001234567890)
  • The bot must be admin in that channel
  • All generated posters are saved there for instant reuse

Filter matching:
  • /filter <keyword> in a group → bot replies with poster for that keyword
  • If keyword matches an anime/manga title, poster is auto-generated
  • Admin can toggle this per-chat from /settings → Filter Poster

Text Style Integration:
  • All poster captions respect the global text style setting

Credits: BeatAnime | @BeatAnime | @Beat_Anime_Discussion
"""

import os
import asyncio
import logging
import hashlib
import json
from io import BytesIO
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple, Any

from telegram import Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton, Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────
POSTER_DB_CHANNEL: int = int(os.getenv("POSTER_DB_CHANNEL", "0") or "0")
POSTER_GEN_TIMEOUT: float = 4.5        # seconds — if exceeded, send placeholder first
PUBLIC_ANIME_CHANNEL_URL: str = os.getenv("PUBLIC_ANIME_CHANNEL_URL", "https://t.me/BeatAnime")

# ── In-memory poster cache (title_hash → {msg_id, file_id, channel_id, ts}) ───
_poster_cache: Dict[str, Dict] = {}
_CACHE_TTL = 86400 * 7  # 7 days


# ── DB helpers ────────────────────────────────────────────────────────────────

def _cache_key(title: str, template: str) -> str:
    return hashlib.md5(f"{title.lower().strip()}:{template}".encode()).hexdigest()


def _get_cached_poster(title: str, template: str) -> Optional[Dict]:
    """Check in-memory cache first, then DB."""
    key = _cache_key(title, template)
    entry = _poster_cache.get(key)
    if entry:
        if (datetime.utcnow() - entry.get("ts", datetime.utcnow())).total_seconds() < _CACHE_TTL:
            return entry
        _poster_cache.pop(key, None)

    # Check DB
    try:
        from database_dual import _pg_exec, _MG
        # PostgreSQL
        row = _pg_exec("""
            SELECT file_id, channel_msg_id, channel_id, caption, created_at
            FROM poster_cache WHERE cache_key = %s
        """, (key,))
        if row:
            entry = {
                "file_id": row[0], "channel_msg_id": row[1],
                "channel_id": row[2], "caption": row[3], "ts": row[4],
            }
            _poster_cache[key] = entry
            return entry
        # MongoDB fallback
        if _MG.db:
            doc = _MG.db.poster_cache.find_one({"cache_key": key})
            if doc:
                entry = {
                    "file_id": doc.get("file_id"), "channel_msg_id": doc.get("channel_msg_id"),
                    "channel_id": doc.get("channel_id"), "caption": doc.get("caption"),
                    "ts": doc.get("created_at", datetime.utcnow()),
                }
                _poster_cache[key] = entry
                return entry
    except Exception as exc:
        logger.debug(f"get_cached_poster DB error: {exc}")
    return None


def _save_poster_cache(title: str, template: str, file_id: str,
                        channel_msg_id: int, channel_id: int, caption: str) -> None:
    """Save poster to DB cache."""
    key = _cache_key(title, template)
    entry = {
        "file_id": file_id, "channel_msg_id": channel_msg_id,
        "channel_id": channel_id, "caption": caption,
        "ts": datetime.utcnow(),
    }
    _poster_cache[key] = entry

    try:
        from database_dual import _pg_run, _MG
        _pg_run("""
            INSERT INTO poster_cache
                (cache_key, title, template, file_id, channel_msg_id, channel_id, caption)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (cache_key) DO UPDATE
                SET file_id = EXCLUDED.file_id,
                    channel_msg_id = EXCLUDED.channel_msg_id,
                    created_at = NOW()
        """, (key, title, template, file_id, channel_msg_id, channel_id, caption))

        if _MG.db:
            _MG.db.poster_cache.update_one(
                {"cache_key": key},
                {"$set": {
                    "cache_key": key, "title": title, "template": template,
                    "file_id": file_id, "channel_msg_id": channel_msg_id,
                    "channel_id": channel_id, "caption": caption,
                    "created_at": datetime.utcnow(),
                }},
                upsert=True,
            )
    except Exception as exc:
        logger.debug(f"save_poster_cache DB error: {exc}")


def _get_filter_poster_enabled(chat_id: int) -> bool:
    """Check if filter-poster integration is enabled for a chat."""
    try:
        from database_dual import get_setting
        key = f"filter_poster_enabled_{chat_id}"
        return get_setting(key, "true") == "true"
    except Exception:
        return True


def _set_filter_poster_enabled(chat_id: int, enabled: bool) -> None:
    try:
        from database_dual import set_setting
        set_setting(f"filter_poster_enabled_{chat_id}", "true" if enabled else "false")
    except Exception:
        pass


def _get_default_poster_template(chat_id: int) -> str:
    """Get the default poster template for auto-generation in a chat."""
    try:
        from database_dual import get_setting
        return get_setting(f"filter_poster_template_{chat_id}", "ani")
    except Exception:
        return "ani"


def _set_default_poster_template(chat_id: int, template: str) -> None:
    try:
        from database_dual import set_setting
        set_setting(f"filter_poster_template_{chat_id}", template)
    except Exception:
        pass


# ── Poster DB Migration ───────────────────────────────────────────────────────

def migrate_poster_cache_table() -> None:
    """Create poster_cache table if it doesn't exist."""
    try:
        from database_dual import _pg_run
        _pg_run("""
            CREATE TABLE IF NOT EXISTS poster_cache (
                id SERIAL PRIMARY KEY,
                cache_key TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                template TEXT NOT NULL,
                file_id TEXT NOT NULL,
                channel_msg_id BIGINT,
                channel_id BIGINT,
                caption TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
    except Exception as exc:
        logger.warning(f"poster_cache table migration: {exc}")


# ── Core: generate + cache poster ─────────────────────────────────────────────

async def _save_to_poster_channel(bot: Bot, photo_buf: BytesIO,
                                   caption: str, template: str) -> Optional[Tuple[str, int]]:
    """
    Upload poster to POSTER_DB_CHANNEL.
    Returns (file_id, message_id) or None.
    """
    if not POSTER_DB_CHANNEL:
        return None
    try:
        photo_buf.seek(0)
        msg = await bot.send_photo(
            chat_id=POSTER_DB_CHANNEL,
            photo=photo_buf,
            caption=f"<b>🗃 Poster Cache</b>\nTemplate: <code>{template}</code>\n\n{caption}",
            parse_mode=ParseMode.HTML,
        )
        if msg.photo:
            return msg.photo[-1].file_id, msg.message_id
    except Exception as exc:
        logger.warning(f"Could not save to poster channel: {exc}")
    return None


async def get_or_generate_poster(
    bot: Bot,
    chat_id: int,
    title: str,
    template: str,
    media_type: str = "ANIME",
    reply_to_message_id: Optional[int] = None,
) -> bool:
    """
    Main entry point: tries cache first, generates if needed.
    Sends poster to chat_id.

    If generation takes >POSTER_GEN_TIMEOUT seconds:
      → Sends a "Generating…" message immediately, then edits with poster.

    Returns True on success.
    """
    # ── 1. Check cache ────────────────────────────────────────────────────────
    cached = _get_cached_poster(title, template)
    if cached and cached.get("file_id"):
        try:
            caption = cached.get("caption", "")
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("📢 BeatAnime", url=PUBLIC_ANIME_CHANNEL_URL)
            ]])
            await bot.send_photo(
                chat_id=chat_id,
                photo=cached["file_id"],
                caption=_apply_text_style(caption),
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
                reply_to_message_id=reply_to_message_id,
            )
            logger.info(f"Poster served from cache for '{title}' ({template})")
            return True
        except Exception:
            # Cache hit but file_id invalid — regenerate
            pass

    # ── 2. Send "Generating…" placeholder (so user sees response in <1 sec) ──
    placeholder = None
    try:
        placeholder = await bot.send_message(
            chat_id=chat_id,
            text=f"<b>🎨 Generating {template.upper()} poster for:</b> <code>{title}</code>\n"
                 f"<i>This may take a moment…</i>",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_to_message_id,
        )
    except Exception:
        pass

    # ── 3. Generate poster with timeout ──────────────────────────────────────
    try:
        poster_buf, caption, data = await asyncio.wait_for(
            _generate_poster_data(title, template, media_type),
            timeout=28.0,  # hard timeout
        )
    except asyncio.TimeoutError:
        if placeholder:
            try:
                await placeholder.edit_text(
                    f"<b>⏰ Poster generation timed out for:</b> <code>{title}</code>\n"
                    f"<i>Please try again in a moment.</i>",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass
        return False
    except Exception as exc:
        logger.error(f"Poster generation error: {exc}")
        if placeholder:
            try:
                await placeholder.edit_text(
                    f"<b>❌ Could not generate poster for:</b> <code>{title}</code>",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass
        return False

    if not poster_buf and not data:
        if placeholder:
            try:
                await placeholder.edit_text(
                    f"<b>❌ Not Found:</b> <code>{title}</code>",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass
        return False

    # ── 4. Delete placeholder ─────────────────────────────────────────────────
    if placeholder:
        try:
            await placeholder.delete()
        except Exception:
            pass

    # ── 5. Send the poster ────────────────────────────────────────────────────
    site_url = data.get("siteUrl", "") if data else ""
    btns = [[InlineKeyboardButton("📢 BeatAnime", url=PUBLIC_ANIME_CHANNEL_URL)]]
    if site_url:
        btns[0].append(InlineKeyboardButton("📋 Info", url=site_url))
    kb = InlineKeyboardMarkup(btns)

    styled_caption = _apply_text_style(caption)

    sent_msg = None
    if poster_buf:
        poster_buf.seek(0)
        try:
            sent_msg = await bot.send_photo(
                chat_id=chat_id,
                photo=poster_buf,
                caption=styled_caption,
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
                reply_to_message_id=reply_to_message_id,
            )
        except Exception as exc:
            logger.error(f"Send poster photo error: {exc}")
    else:
        # Text fallback
        text_msg = styled_caption
        if site_url:
            text_msg += f"\n\n<a href='{site_url}'>🔗 View on AniList</a>"
        try:
            sent_msg = await bot.send_message(
                chat_id=chat_id,
                text=text_msg,
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
                reply_to_message_id=reply_to_message_id,
                disable_web_page_preview=False,
            )
        except Exception as exc:
            logger.error(f"Send poster text error: {exc}")

    if not sent_msg:
        return False

    # ── 6. Save to poster DB channel + cache ─────────────────────────────────
    file_id = None
    channel_msg_id = None
    if poster_buf and POSTER_DB_CHANNEL:
        result = await _save_to_poster_channel(bot, poster_buf, caption, template)
        if result:
            file_id, channel_msg_id = result
    elif sent_msg and sent_msg.photo:
        file_id = sent_msg.photo[-1].file_id

    if file_id:
        _save_poster_cache(
            title=title,
            template=template,
            file_id=file_id,
            channel_msg_id=channel_msg_id or 0,
            channel_id=POSTER_DB_CHANNEL,
            caption=caption,
        )

    return True


async def _generate_poster_data(
    title: str, template: str, media_type: str
) -> Tuple[Optional[BytesIO], str, Optional[Dict]]:
    """
    Generate poster image + caption for a given title/template/media_type.
    Returns (BytesIO_or_None, caption_str, raw_data_dict).
    Runs blocking PIL work in executor to avoid blocking event loop.
    """
    loop = asyncio.get_event_loop()

    from poster_engine import (
        _anilist_anime, _anilist_manga, _tmdb_movie, _tmdb_tv,
        _make_poster, _build_anime_data, _build_manga_data,
        _build_movie_data, _build_tv_data, _get_settings,
        TEMPLATES,
    )
    import html

    # ── Fetch data (network I/O — run in executor for non-blocking) ────────────
    data = await loop.run_in_executor(None, _fetch_data, title, media_type)
    if not data:
        return None, "", None

    # ── Build poster params ────────────────────────────────────────────────────
    if media_type == "ANIME":
        p_title, p_native, p_status, p_rows, p_desc, p_cover, p_score = _build_anime_data(data)
    elif media_type == "MANGA":
        p_title, p_native, p_status, p_rows, p_desc, p_cover, p_score = _build_manga_data(data)
    elif media_type == "MOVIE":
        p_title, p_native, p_status, p_rows, p_desc, p_cover, p_score = _build_movie_data(data)
    else:
        p_title, p_native, p_status, p_rows, p_desc, p_cover, p_score = _build_tv_data(data)

    cat = {"ANIME": "anime", "MANGA": "manga", "MOVIE": "movie", "TV": "tvshow"}.get(media_type, "anime")
    settings = _get_settings(cat)
    wm_text = settings.get("watermark_text")
    wm_pos = settings.get("watermark_position", "center")

    # ── Generate image (CPU-bound — run in executor) ───────────────────────────
    poster_buf = await loop.run_in_executor(
        None,
        _make_poster,
        template, p_title, p_native, p_status, p_rows, p_desc,
        p_cover, p_score, wm_text, wm_pos, None, "bottom",
    )

    # ── Build caption ──────────────────────────────────────────────────────────
    site_url = data.get("siteUrl", "")
    genres_list = data.get("genres") or []
    genres_str = ", ".join(genres_list[:3]) if genres_list else ""
    branding = settings.get("branding", "")

    caption = (
        f"<b>{html.escape(p_title)}</b>\n"
        + (f"<i>{html.escape(genres_str)}</i>\n" if genres_str else "")
        + (f"<b>{html.escape(branding)}</b>\n" if branding else "")
        + f"\n<i>via @BeatAnime</i>"
    )
    if len(caption) > 1024:
        caption = caption[:1020] + "…"

    return poster_buf, caption, data


def _fetch_data(title: str, media_type: str) -> Optional[Dict]:
    """Synchronous data fetch — called via run_in_executor."""
    from poster_engine import _anilist_anime, _anilist_manga, _tmdb_movie, _tmdb_tv
    try:
        if media_type == "ANIME":
            return _anilist_anime(title)
        elif media_type == "MANGA":
            return _anilist_manga(title)
        elif media_type == "MOVIE":
            return _tmdb_movie(title)
        elif media_type == "TV":
            return _tmdb_tv(title)
    except Exception as exc:
        logger.debug(f"_fetch_data error: {exc}")
    return None


# ── Text Style (applies global style to any text) ────────────────────────────

def _apply_text_style(text: str) -> str:
    """Apply global text style setting if set. Preserves HTML tags and links."""
    try:
        from database_dual import get_setting
        style = get_setting("global_text_style", "normal")
        if style == "smallcaps":
            return _to_smallcaps_html_safe(text)
        elif style == "bold":
            return _to_bold_html_safe(text)
    except Exception:
        pass
    return text


# ── Filter-Poster Settings Panel (injected into admin panel) ─────────────────

def build_filter_poster_settings_keyboard(chat_id: int = 0) -> InlineKeyboardMarkup:
    """Build the filter-poster settings panel keyboard."""
    enabled = _get_filter_poster_enabled(chat_id) if chat_id else True
    template = _get_default_poster_template(chat_id) if chat_id else "ani"
    channel_set = "✅ Set" if POSTER_DB_CHANNEL else "❌ Not Set"

    templates_row1 = [
        InlineKeyboardButton(f"{'✅ ' if template == 'ani' else ''}ani",   callback_data=f"fp_tmpl_{chat_id}_ani"),
        InlineKeyboardButton(f"{'✅ ' if template == 'crun' else ''}crun", callback_data=f"fp_tmpl_{chat_id}_crun"),
        InlineKeyboardButton(f"{'✅ ' if template == 'net' else ''}net",   callback_data=f"fp_tmpl_{chat_id}_net"),
    ]
    templates_row2 = [
        InlineKeyboardButton(f"{'✅ ' if template == 'dark' else ''}dark",   callback_data=f"fp_tmpl_{chat_id}_dark"),
        InlineKeyboardButton(f"{'✅ ' if template == 'light' else ''}light", callback_data=f"fp_tmpl_{chat_id}_light"),
        InlineKeyboardButton(f"{'✅ ' if template == 'mod' else ''}mod",     callback_data=f"fp_tmpl_{chat_id}_mod"),
    ]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"{'🟢 Filter Posters: ON' if enabled else '🔴 Filter Posters: OFF'}",
            callback_data=f"fp_toggle_{chat_id}"
        )],
        templates_row1,
        templates_row2,
        [InlineKeyboardButton(f"📦 Poster DB Channel: {channel_set}", callback_data="fp_channel_info")],
        [InlineKeyboardButton("🗃 View Cached Posters", callback_data="fp_view_cache"),
         InlineKeyboardButton("🗑 Clear Cache", callback_data="fp_clear_cache")],
        [InlineKeyboardButton("🔙 BACK", callback_data="admin_settings")],
    ])


def get_filter_poster_settings_text(chat_id: int = 0) -> str:
    enabled = _get_filter_poster_enabled(chat_id) if chat_id else True
    template = _get_default_poster_template(chat_id) if chat_id else "ani"
    total_cached = _get_cache_count()
    channel_info = f"<code>{POSTER_DB_CHANNEL}</code>" if POSTER_DB_CHANNEL else "Not configured"

    return (
        "<b>🎨 Filter Poster Integration</b>\n\n"
        f"<b>Status:</b> {'🟢 Active' if enabled else '🔴 Disabled'}\n"
        f"<b>Default Template:</b> <code>{template}</code>\n"
        f"<b>Poster DB Channel:</b> {channel_info}\n"
        f"<b>Cached Posters:</b> <code>{total_cached}</code>\n\n"
        "<i>When enabled: matching a group filter keyword generates a poster "
        "automatically. Posters are cached so repeat requests are instant.</i>\n\n"
        "<b>⚡ Speed:</b> Cached = instant  |  New = ~3-5 sec"
    )


def _get_cache_count() -> int:
    try:
        from database_dual import _pg_exec, _MG
        row = _pg_exec("SELECT COUNT(*) FROM poster_cache")
        if row:
            return row[0]
        if _MG.db:
            return _MG.db.poster_cache.count_documents({})
    except Exception:
        pass
    return len(_poster_cache)


def _clear_poster_cache() -> int:
    """Clear all cached posters. Returns count cleared."""
    count = _get_cache_count()
    _poster_cache.clear()
    try:
        from database_dual import _pg_run, _MG
        _pg_run("DELETE FROM poster_cache")
        if _MG.db:
            _MG.db.poster_cache.delete_many({})
    except Exception:
        pass
    return count
