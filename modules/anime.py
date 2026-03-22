# ====================================================================
# PLACE AT: /app/modules/anime.py
# ACTION: Replace existing file
# ====================================================================
"""
anime.py — /anime /tvshow /net /manga /airing /character
Fully async, works for all users (not admin-only).
Handles abbreviations + partial English names + romaji fallback.
"""
import asyncio, html, logging, re, requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, CommandHandler

logger = logging.getLogger(__name__)
_AL_URL = "https://graphql.anilist.co"
_TMDB_KEY = __import__("os").getenv("TMDB_API_KEY", "")

# ── Abbreviation / common-name → proper search query ─────────────────────────
_ABBR = {
    # Short codes
    "aot": "attack on titan", "snk": "attack on titan",
    "bnha": "my hero academia", "mha": "my hero academia",
    "hxh": "hunter x hunter", "jjk": "jujutsu kaisen",
    "csm": "chainsaw man", "op": "one piece",
    "fma": "fullmetal alchemist",
    "fmab": "fullmetal alchemist brotherhood",
    "kny": "kimetsu no yaiba", "ds": "kimetsu no yaiba",
    "re zero": "re zero kara hajimeru isekai seikatsu",
    "rezero": "re zero kara hajimeru isekai seikatsu",
    "slime": "tensei shitara slime datta ken",
    "tensura": "tensei shitara slime datta ken",
    "shield hero": "tate no yuusha no nariagari",
    "sao": "sword art online",
    "dbs": "dragon ball super", "dbz": "dragon ball z", "db": "dragon ball",
    "cote": "classroom of the elite",
    "eminence in shadow": "kage no jitsuryokusha ni naritakute",
    "konosuba": "kono subarashii sekai ni shukufuku wo",
    "danmachi": "dungeon ni deai wo motomeru no wa machigatteiru darou ka",
    # English names that map to romaji
    "demon slayer": "kimetsu no yaiba",
    "demon slayer swordsmith": "kimetsu no yaiba katanakaji no sato hen",
    "frieren": "sousou no frieren",
    "frieren beyond journeys end": "sousou no frieren",
    "spy x family": "spy x family",
    "spy family": "spy x family",
    "blue lock": "blue lock",
    "oshi no ko": "oshi no ko",
    "classroom of elite": "classroom of the elite",
    "overlord": "overlord",
    "sword art online": "sword art online",
    "attack on titan": "shingeki no kyojin",
    "one punch man": "one punch man",
    "opm": "one punch man",
    "naruto": "naruto",
    "bleach": "bleach",
    "fullmetal alchemist": "fullmetal alchemist",
    "tokyo ghoul": "tokyo ghoul",
    "no game no life": "no game no life",
    "death note": "death note",
    "hunter x hunter": "hunter x hunter",
    "fairy tail": "fairy tail",
    "black clover": "black clover",
    "dr stone": "dr stone",
    "dr. stone": "dr stone",
    "food wars": "shokugeki no soma",
    "shokugeki": "shokugeki no soma",
    "vinland saga": "vinland saga",
    "jojo": "jojo no kimyou na bouken",
    "jojos bizarre adventure": "jojo no kimyou na bouken",
    "promised neverland": "yakusoku no neverland",
    "tpn": "yakusoku no neverland",
    "re:zero": "re zero kara hajimeru isekai seikatsu",
    "made in abyss": "made in abyss",
    "mia": "made in abyss",
    "violet evergarden": "violet evergarden",
    "your lie in april": "shigatsu wa kimi no uso",
    "shigatsu": "shigatsu wa kimi no uso",
    "anohana": "ano hi mita hana no namae wo bokutachi wa mada shiranai",
    "clannad": "clannad",
    "steins gate": "steins gate",
    "steins;gate": "steins gate",
    "sg": "steins gate",
    "toradora": "toradora",
    "angel beats": "angel beats",
    "sword art online alicization": "sword art online alicization",
    "black butler": "kuroshitsuji",
    "kuroshitsuji": "kuroshitsuji",
    "ao no exorcist": "ao no exorcist",
    "blue exorcist": "ao no exorcist",
    "bungou stray dogs": "bungou stray dogs",
    "bsd": "bungou stray dogs",
    "noragami": "noragami",
    "ngnl": "no game no life",
    "hibike euphonium": "hibike euphonium",
    "sound euphonium": "hibike euphonium",
    "k on": "k on",
    "k-on": "k on",
    "lucky star": "lucky star",
    "haruhi": "suzumiya haruhi no yuuutsu",
    "haruhi suzumiya": "suzumiya haruhi no yuuutsu",
    "code geass": "code geass hangyaku no lelouch",
    "code geass lelouch": "code geass hangyaku no lelouch",
    "cowboy bebop": "cowboy bebop",
    "neon genesis evangelion": "neon genesis evangelion",
    "nge": "neon genesis evangelion",
    "eva": "neon genesis evangelion",
    "evangelion": "neon genesis evangelion",
    "spirited away": "sen to chihiro no kamikakushi",
    "my neighbor totoro": "tonari no totoro",
    "princess mononoke": "mononoke hime",
    "howls moving castle": "hauru no ugoku shiro",
    "chainsaw man": "chainsaw man",
    "csm": "chainsaw man",
    "oshi no ko": "oshi no ko",
    "mushoku tensei": "mushoku tensei isekai ittara honki dasu",
    "jobless reincarnation": "mushoku tensei isekai ittara honki dasu",
    "that time i got reincarnated as a slime": "tensei shitara slime datta ken",
    "aot final season": "shingeki no kyojin the final season",
    "solo leveling": "ore dake level up na ken",
    "ore dake": "ore dake level up na ken",
    "dungeon meshi": "dungeon meshi",
    "delicious in dungeon": "dungeon meshi",
    "frieren beyond journey end": "sousou no frieren",
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


def _normalise(q: str) -> str:
    """Lower, strip, remove punctuation noise for matching."""
    return re.sub(r"[^\w\s]", "", q.lower()).strip()


def _al_sync(gql: str, search: str):
    """AniList search with smart multi-query fallback."""
    q_norm = _normalise(search)
    mapped = _ABBR.get(q_norm, search)

    queries_to_try = []
    # 1. mapped (if different from original)
    if mapped.lower() != search.lower():
        queries_to_try.append(mapped)
    # 2. original as-is
    queries_to_try.append(search)
    # 3. Title-cased
    if search.lower() != search.title().lower():
        queries_to_try.append(search.title())
    # 4. First word only (helps with "Demon Slayer Season 3" → "Demon Slayer")
    words = search.split()
    if len(words) > 2:
        queries_to_try.append(" ".join(words[:3]))
    # deduplicate keeping order
    seen = set()
    deduped = []
    for q in queries_to_try:
        qk = q.lower()
        if qk not in seen:
            seen.add(qk)
            deduped.append(q)

    for q in deduped:
        try:
            r = requests.post(
                _AL_URL,
                json={"query": gql, "variables": {"s": q}},
                headers={"Content-Type": "application/json"},
                timeout=12,
            )
            if r.status_code == 200:
                d = r.json().get("data", {})
                result = d.get("Media") or d.get("Character")
                if result:
                    return result
        except Exception as exc:
            logger.debug(f"AniList [{q}]: {exc}")
    return None


async def _al(gql: str, search: str):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _al_sync, gql, search)


def _clean(text, mx=300):
    if not text:
        return "No description available."
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return (text[:mx].rsplit(" ", 1)[0] + "…") if len(text) > mx else text


# ── Poster generation ─────────────────────────────────────────────────────────

async def _make_and_send_poster(update: Update, template: str, media_type: str, query: str):
    """Generate a poster using poster_engine and send it. Falls back to text card."""
    try:
        from poster_engine import (
            _anilist_anime, _anilist_manga, _tmdb_movie, _tmdb_tv,
            _build_anime_data, _build_manga_data,
            _build_movie_data, _build_tv_data,
            _make_poster, _get_settings,
        )
    except ImportError as exc:
        await update.message.reply_text(
            f"⚠️ Poster engine unavailable: <code>{html.escape(str(exc)[:80])}</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    loop = asyncio.get_event_loop()

    # Fetch data
    fetch_map = {
        "ANIME": _anilist_anime,
        "MANGA": _anilist_manga,
        "MOVIE": _tmdb_movie,
        "TV":    _tmdb_tv,
    }
    fetch_fn = fetch_map.get(media_type, _anilist_anime)
    data = await loop.run_in_executor(None, fetch_fn, query)

    if not data:
        await update.message.reply_text(
            f"❌ <b>Not found:</b> <code>{html.escape(query)}</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    settings = _get_settings(media_type.lower() if media_type != "TV" else "tvshow")
    build_map = {
        "ANIME": _build_anime_data,
        "MANGA": _build_manga_data,
        "MOVIE": _build_movie_data,
        "TV":    _build_tv_data,
    }
    build_fn = build_map.get(media_type, _build_anime_data)
    title, native, st, rows, desc, cover_url, score = await loop.run_in_executor(None, build_fn, data)

    poster_buf = await loop.run_in_executor(
        None,
        _make_poster,
        template, title, native, st, rows, desc, cover_url, score,
        settings.get("watermark_text"),
        settings.get("watermark_position", "center"),
        None, "bottom",
    )

    site_url = data.get("siteUrl") or data.get("url") or ""
    genres   = ", ".join((data.get("genres") or [])[:3])
    t_d      = data.get("title", {}) or {}
    eng      = t_d.get("english") or t_d.get("romaji") or title

    cap = f"<b>{html.escape(eng)}</b>\n"
    if native:
        cap += f"<i>{html.escape(native)}</i>\n"
    cap += "\n"
    if genres:
        cap += f"» <b>Genre:</b> {html.escape(genres)}\n"
    for lb, v in (rows or [])[:5]:
        if v and str(v) not in ("-", "N/A", "None", "?", "0"):
            cap += f"» <b>{html.escape(lb)}:</b> <code>{html.escape(str(v))}</code>\n"
    cap += "\n<i>Posted via @BeatAnime</i>"
    if len(cap) > 1024:
        cap = cap[:1020] + "…"

    btns = [[InlineKeyboardButton("📢 BeatAnime", url="https://t.me/BeatAnime")]]
    if site_url:
        btns[0].append(InlineKeyboardButton("📋 Info", url=site_url))
    markup = InlineKeyboardMarkup(btns)

    if poster_buf:
        try:
            poster_buf.seek(0)
            await update.message.reply_photo(
                photo=poster_buf, caption=cap,
                parse_mode=ParseMode.HTML, reply_markup=markup,
            )
            return
        except Exception as exc:
            logger.debug(f"poster send failed: {exc}")

    # Text fallback with cover image
    cv = (data.get("coverImage") or {}).get("extraLarge") or data.get("poster_path", "")
    if cv and not cv.startswith("http"):
        cv = f"https://image.tmdb.org/t/p/w500{cv}"
    lp = f'\n<a href="{html.escape(cv)}">&#8203;</a>' if cv else ""
    await update.message.reply_text(
        cap + lp, parse_mode=ParseMode.HTML,
        reply_markup=markup, disable_web_page_preview=False,
    )


# ── Command handlers ──────────────────────────────────────────────────────────

async def anime_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "<b>Usage:</b> /anime &lt;anime name&gt;\n"
            "<b>Examples:</b>\n"
            "• <code>/anime demon slayer</code>\n"
            "• <code>/anime aot</code>\n"
            "• <code>/anime jjk</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    q = " ".join(context.args)
    wait = await update.message.reply_text("🎨 <b>Generating poster…</b>", parse_mode=ParseMode.HTML)
    await _make_and_send_poster(update, "ani", "ANIME", q)
    try: await wait.delete()
    except: pass


async def tvshow_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("<b>Usage:</b> /tvshow &lt;show name&gt;", parse_mode=ParseMode.HTML)
        return
    q = " ".join(context.args)
    wait = await update.message.reply_text("🎨 <b>Generating poster…</b>", parse_mode=ParseMode.HTML)
    await _make_and_send_poster(update, "net", "TV", q)
    try: await wait.delete()
    except: pass


async def movie_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("<b>Usage:</b> /movie &lt;movie name&gt;", parse_mode=ParseMode.HTML)
        return
    q = " ".join(context.args)
    wait = await update.message.reply_text("🎨 <b>Generating poster…</b>", parse_mode=ParseMode.HTML)
    await _make_and_send_poster(update, "net", "MOVIE", q)
    try: await wait.delete()
    except: pass


async def net_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Netflix-style poster (/net) — works for anime, shows, movies."""
    if not context.args:
        await update.message.reply_text("<b>Usage:</b> /net &lt;title&gt;", parse_mode=ParseMode.HTML)
        return
    q = " ".join(context.args)
    wait = await update.message.reply_text("🎨 <b>Generating poster…</b>", parse_mode=ParseMode.HTML)
    await _make_and_send_poster(update, "net", "ANIME", q)
    try: await wait.delete()
    except: pass


async def manga_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("<b>Usage:</b> /manga &lt;manga name&gt;", parse_mode=ParseMode.HTML)
        return
    q = " ".join(context.args)
    wait = await update.message.reply_text("🎨 <b>Generating poster…</b>", parse_mode=ParseMode.HTML)
    await _make_and_send_poster(update, "anim", "MANGA", q)
    try: await wait.delete()
    except: pass


async def airing_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("<b>Usage:</b> /airing &lt;anime name&gt;", parse_mode=ParseMode.HTML)
        return
    data = await _al(_AIRING_GQL, " ".join(context.args))
    if not data:
        await update.message.reply_text("❌ Anime not found.")
        return
    td    = data.get("title", {}) or {}
    title  = td.get("english") or td.get("romaji") or "Unknown"
    native = td.get("native", "")
    nxt    = data.get("nextAiringEpisode")
    if nxt:
        secs = nxt.get("timeUntilAiring", 0)
        d, r = divmod(secs, 86400); h, r2 = divmod(r, 3600); m = r2 // 60
        ts = f"{d}d {h}h {m}m" if d else f"{h}h {m}m"
        txt = (
            f"<b>{html.escape(title)}</b>"
            + (f" (<i>{html.escape(native)}</i>)" if native else "")
            + f"\n\n📡 <b>Episode {nxt.get('episode','?')}</b> airs in <code>{ts}</code>"
        )
    else:
        st  = (data.get("status") or "").replace("_", " ").title()
        txt = (
            f"<b>{html.escape(title)}</b>"
            + (f" (<i>{html.escape(native)}</i>)" if native else "")
            + f"\n\n📺 <b>Episodes:</b> {data.get('episodes','?')}\n📌 <b>Status:</b> {html.escape(st)}"
        )
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML)


async def character_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("<b>Usage:</b> /character &lt;name&gt;", parse_mode=ParseMode.HTML)
        return
    data = await _al(_CHAR_GQL, " ".join(context.args))
    if not data:
        await update.message.reply_text("❌ Character not found.")
        return
    nm     = data.get("name", {}) or {}
    full   = nm.get("full", "Unknown")
    native = nm.get("native", "")
    desc   = _clean(data.get("description", ""), 350)
    site   = data.get("siteUrl", "https://anilist.co")
    img    = (data.get("image") or {}).get("large")
    txt = (
        f"<b>{html.escape(full)}</b>"
        + (f" (<i>{html.escape(native)}</i>)" if native else "")
        + f"\n\n{html.escape(desc)}"
    )
    if len(txt) > 1020:
        txt = txt[:1016] + "…"
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("📋 AniList", url=site)]])
    if img:
        try:
            await update.message.reply_photo(photo=img, caption=txt, parse_mode=ParseMode.HTML, reply_markup=markup)
            return
        except Exception:
            pass
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML, reply_markup=markup)


def register(app) -> None:
    app.add_handler(CommandHandler("anime",     anime_cmd))
    app.add_handler(CommandHandler("tvshow",    tvshow_cmd))
    app.add_handler(CommandHandler("movie",     movie_cmd))
    app.add_handler(CommandHandler("net",       net_cmd))
    app.add_handler(CommandHandler("manga",     manga_cmd))
    app.add_handler(CommandHandler("airing",    airing_cmd))
    app.add_handler(CommandHandler("character", character_cmd))
    logger.info("[anime] Handlers registered")


__mod_name__     = "Anime"
__command_list__ = ["anime", "tvshow", "movie", "net", "manga", "airing", "character"]
__help__ = """
• /anime &lt;name&gt; — anime poster + info (supports abbreviations like /anime aot, /anime jjk)
• /tvshow &lt;name&gt; — TV show poster
• /movie &lt;name&gt; — movie poster
• /net &lt;name&gt; — Netflix-style poster
• /manga &lt;name&gt; — manga poster + info
• /airing &lt;name&gt; — next episode countdown
• /character &lt;name&gt; — character details
"""
