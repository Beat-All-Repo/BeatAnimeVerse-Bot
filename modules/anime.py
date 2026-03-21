# ====================================================================
# PLACE AT: /app/modules/anime.py
# ACTION: Replace existing file
# ====================================================================
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Anime module — rewritten for PTB v21 + AniList API (no jikanpy dependency)
Generates landscape posters for /anime /manga /airing /character
"""
import html, logging, re, requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, CommandHandler

logger = logging.getLogger(__name__)
_AL_URL = "https://graphql.anilist.co"
_ABBR = {
    "aot":"attack on titan", "snk":"attack on titan",
    "bnha":"my hero academia", "mha":"my hero academia",
    "hxh":"hunter x hunter", "jjk":"jujutsu kaisen",
    "csm":"chainsaw man", "op":"one piece",
    "fma":"fullmetal alchemist", "fmab":"Fullmetal Alchemist: Brotherhood",
    "demon slayer":"Kimetsu no Yaiba",
    "kny":"Kimetsu no Yaiba", "ds":"Kimetsu no Yaiba",
    "demon slayer swordsmith":"Kimetsu no Yaiba: Katanakaji no Sato-hen",
    "re zero":"Re:Zero kara Hajimeru Isekai Seikatsu",
    "rezero":"Re:Zero kara Hajimeru Isekai Seikatsu",
    "slime":"Tensei shitara Slime Datta Ken",
    "tensura":"Tensei shitara Slime Datta Ken",
    "shield hero":"Tate no Yuusha no Nariagari",
    "sao":"Sword Art Online",
    "dbs":"dragon ball super", "dbz":"dragon ball z",
    "frieren":"Sousou no Frieren",
    "spy family":"Spy x Family",
    "blue lock":"Blue Lock",
    "oshi no ko":"Oshi no Ko",
    "classroom of elite":"Youkoso Jitsuryoku Shijou Shugi no Kyoushitsu e",
    "cote":"Youkoso Jitsuryoku Shijou Shugi no Kyoushitsu e",
    "eminence in shadow":"Kage no Jitsuryokusha ni Naritakute!",
    "konosuba":"Kono Subarashii Sekai ni Shukufuku wo!",
    "danmachi":"Dungeon ni Deai wo Motomeru no wa Machigatteiru Darou ka",
    "overlord":"Overlord",
}

_ANIME_GQL = """query($s:String){Media(search:$s,type:ANIME,sort:[SEARCH_MATCH,POPULARITY_DESC]){
  id siteUrl title{romaji english native} description(asHtml:false)
  coverImage{extraLarge large} bannerImage format status season seasonYear
  episodes duration averageScore genres studios(isMain:true){nodes{name}}
  nextAiringEpisode{episode timeUntilAiring}}}"""

_MANGA_GQL = """query($s:String){Media(search:$s,type:MANGA,sort:[SEARCH_MATCH,POPULARITY_DESC]){
  id siteUrl title{romaji english native} description(asHtml:false)
  coverImage{extraLarge large} format status chapters volumes averageScore genres}}"""

_CHAR_GQL = """query($s:String){Character(search:$s){
  name{full native} description siteUrl image{large}}}"""

_AIRING_GQL = """query($s:String){Media(search:$s,type:ANIME,sort:[SEARCH_MATCH,POPULARITY_DESC]){
  id title{romaji english native} episodes status
  nextAiringEpisode{episode timeUntilAiring}}}"""


def _al(gql, search):
    """Smart AniList search — uses mapped query first, falls back to original."""
    search_clean = search.strip()
    q_mapped = _ABBR.get(search_clean.lower(), search_clean)
    queries = [q_mapped]
    if q_mapped.lower() != search_clean.lower():
        queries.append(search_clean)
    if search_clean != search_clean.title():
        queries.append(search_clean.title())

    for q in queries:
        try:
            r = requests.post(_AL_URL, json={"query": gql, "variables": {"s": q}},
                              headers={"Content-Type":"application/json"}, timeout=12)
            if r.status_code == 200:
                d = r.json().get("data", {})
                result = d.get("Media") or d.get("Character")
                if result:
                    # Sanity check for multi-word searches
                    if isinstance(result, dict) and "title" in result:
                        titles = result.get("title") or {}
                        res_text = " ".join([
                            titles.get("english","") or "",
                            titles.get("romaji","") or "",
                        ]).lower()
                        words = [w for w in search_clean.lower().split() if len(w) > 3]
                        if words and not any(w in res_text for w in words):
                            continue
                    return result
        except Exception as e:
            logger.debug(f"AniList: {e}")
    return None


def _clean(text, mx=280):
    if not text: return "No description available."
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:mx].rsplit(" ", 1)[0] + "…" if len(text) > mx else text


async def _poster(update, context, template, media_type, query):
    try:
        from poster_engine import (_anilist_anime, _anilist_manga,
                                   _build_anime_data, _build_manga_data,
                                   _make_poster, _get_settings)
    except ImportError as e:
        await update.message.reply_text("⚠️ Poster engine unavailable.")
        logger.error(f"poster_engine: {e}")
        return

    data = _anilist_anime(query) if media_type == "ANIME" else _anilist_manga(query)
    if not data:
        await update.message.reply_text(
            f"❌ Not found: <code>{html.escape(query)}</code>", parse_mode=ParseMode.HTML)
        return

    settings = _get_settings(media_type.lower())
    if media_type == "ANIME":
        title, native, st, rows, desc, cover_url, score = _build_anime_data(data)
    else:
        title, native, st, rows, desc, cover_url, score = _build_manga_data(data)

    poster_buf = _make_poster(template, title, native, st, rows, desc, cover_url, score,
                              settings.get("watermark_text"),
                              settings.get("watermark_position", "center"),
                              None, "bottom")

    site_url = data.get("siteUrl", "")
    genres   = ", ".join((data.get("genres") or [])[:3])
    t_d      = data.get("title", {}) or {}
    eng      = t_d.get("english") or t_d.get("romaji") or title

    cap = f"<b>{html.escape(eng)}</b>\n"
    if native: cap += f"<i>{html.escape(native)}</i>\n"
    cap += "\n"
    if genres: cap += f"» <b>Genre:</b> {html.escape(genres)}\n"
    for lb, v in rows[:5]:
        if v and v not in ("-","N/A","None","?"):
            cap += f"» <b>{lb}:</b> <code>{html.escape(str(v))}</code>\n"
    cap += "\n<i>Posted via @BeatAnime</i>"
    if len(cap) > 1024: cap = cap[:1020] + "…"

    btns = [[InlineKeyboardButton("📢 BeatAnime", url="https://t.me/BeatAnime")]]
    if site_url: btns[0].append(InlineKeyboardButton("📋 AniList", url=site_url))
    markup = InlineKeyboardMarkup(btns)

    if poster_buf:
        await update.message.reply_photo(photo=poster_buf, caption=cap,
                                         parse_mode=ParseMode.HTML, reply_markup=markup)
    else:
        cv = (data.get("coverImage") or {}).get("extraLarge", "")
        lp = f'\n<a href="{html.escape(cv)}">&#8203;</a>' if cv else ""
        await update.message.reply_text(cap + lp, parse_mode=ParseMode.HTML,
                                        reply_markup=markup, disable_web_page_preview=False)


async def anime_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("<b>Usage:</b> /anime &lt;anime name&gt;\n<b>Ex:</b> <code>/anime Demon Slayer</code>", parse_mode=ParseMode.HTML)
        return
    q = " ".join(context.args)
    msg = await update.message.reply_text("🎨 <b>Generating poster…</b>", parse_mode=ParseMode.HTML)
    await _poster(update, context, "ani", "ANIME", q)
    try: await msg.delete()
    except: pass


async def manga_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("<b>Usage:</b> /manga &lt;manga name&gt;", parse_mode=ParseMode.HTML)
        return
    q = " ".join(context.args)
    msg = await update.message.reply_text("🎨 <b>Generating poster…</b>", parse_mode=ParseMode.HTML)
    await _poster(update, context, "anim", "MANGA", q)
    try: await msg.delete()
    except: pass


async def airing_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("<b>Usage:</b> /airing &lt;anime name&gt;", parse_mode=ParseMode.HTML)
        return
    data = _al(_AIRING_GQL, " ".join(context.args))
    if not data:
        await update.message.reply_text("❌ Anime not found."); return
    td = data.get("title", {}) or {}
    title = td.get("english") or td.get("romaji") or "Unknown"
    native = td.get("native", "")
    nxt = data.get("nextAiringEpisode")
    if nxt:
        secs = nxt.get("timeUntilAiring", 0)
        d, r = divmod(secs, 86400); h, r = divmod(r, 3600); m = r // 60
        ts = f"{d}d {h}h {m}m" if d else f"{h}h {m}m"
        msg = (f"<b>{html.escape(title)}</b>" + (f" (<i>{html.escape(native)}</i>)" if native else "")
               + f"\n\n📡 <b>Episode {nxt.get('episode','?')}</b> airs in <code>{ts}</code>")
    else:
        st = (data.get("status") or "").replace("_"," ").title()
        msg = (f"<b>{html.escape(title)}</b>" + (f" (<i>{html.escape(native)}</i>)" if native else "")
               + f"\n\n📺 <b>Episodes:</b> {data.get('episodes','?')}\n📌 <b>Status:</b> {html.escape(st)}")
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


async def character_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("<b>Usage:</b> /character &lt;name&gt;", parse_mode=ParseMode.HTML)
        return
    data = _al(_CHAR_GQL, " ".join(context.args))
    if not data:
        await update.message.reply_text("❌ Character not found."); return
    nm = data.get("name", {}) or {}
    full = nm.get("full", "Unknown"); native = nm.get("native", "")
    desc = _clean(data.get("description", ""), 350)
    site = data.get("siteUrl", "https://anilist.co")
    img  = (data.get("image") or {}).get("large")
    msg  = (f"<b>{html.escape(full)}</b>" + (f" (<i>{html.escape(native)}</i>)" if native else "")
            + f"\n\n{html.escape(desc)}")
    if len(msg) > 1020: msg = msg[:1016] + "…"
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("📋 AniList", url=site)]])
    if img:
        try:
            await update.message.reply_photo(photo=img, caption=msg, parse_mode=ParseMode.HTML, reply_markup=markup)
            return
        except Exception: pass
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=markup)


def register(app) -> None:
    app.add_handler(CommandHandler("anime",     anime_cmd))
    app.add_handler(CommandHandler("manga",     manga_cmd))
    app.add_handler(CommandHandler("airing",    airing_cmd))
    app.add_handler(CommandHandler("character", character_cmd))
    logger.info("[anime] Handlers registered")


__mod_name__     = "Anime"
__command_list__ = ["anime", "manga", "airing", "character"]
__help__ = """
• /anime &lt;name&gt; — landscape Netflix-style poster + info
• /manga &lt;name&gt; — landscape manga poster + info
• /airing &lt;name&gt; — next episode countdown
• /character &lt;name&gt; — character details from AniList
"""
