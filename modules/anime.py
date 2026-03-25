# ====================================================================
# PLACE AT: /app/modules/anime.py  |  ACTION: Replace existing file
# ====================================================================
"""
anime.py — /anime /tvshow /net /manga /airing /character /imdb
Fully async. Features:
  ✅ AniList search with TTL cache (fast repeated queries)
  ✅ Inline search: cover image + info shown as InlineQueryResultPhoto
  ✅ GC single-letter filter: type 't' → anime starting with T as buttons
  ✅ GC filter: auto-delete 20s, one-panel-per-user, paged nav, expiry links
  ✅ NEXT IMG edits poster in place (not delete+resend)
  ✅ Custom thumbnail guard (only requesting user's photo accepted)
  ✅ Season detection, similar panel, language panel, size panel
  ✅ All existing commands preserved
"""
import asyncio, html, logging, re, time, os, requests
from io import BytesIO
from typing import Optional, List, Dict, Any, Tuple

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto,
    InlineQueryResultPhoto, InlineQueryResultArticle, InputTextMessageContent,
)
from telegram.constants import ParseMode
from telegram.ext import (
    ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters,
)

logger = logging.getLogger(__name__)
_AL_URL   = "https://graphql.anilist.co"
_TMDB_KEY = os.getenv("TMDB_API_KEY", "")

# ── small helpers ─────────────────────────────────────────────────────────────
def _sc(t):
    try:
        from bot import small_caps; return small_caps(t)
    except Exception: return t
def _b(t):  return f"<b>{_sc(t)}</b>"
def _bq(t): return f"<blockquote expandable>{t}</blockquote>"
def _e(t):  return html.escape(str(t))

# ── Templates ─────────────────────────────────────────────────────────────────
TEMPLATES = ["ani", "dark", "light", "crun", "mod", "net"]
TEMPLATE_LABELS = {"ani":"🎌 Anime","dark":" Dark","light":" Light","crun":" Crunchyroll","mod":" Modern","net":" Netflix"}

# ── Language options ──────────────────────────────────────────────────────────
LANG_OPTIONS = [
    ("Hindi","lang_hin"),("English","lang_eng"),("Hindi & English","lang_hin_eng"),
    ("Japanese & Hindi","lang_jpn_hin"),("Japanese & English","lang_jpn_eng"),
    ("Japanese & English Sub","lang_jpn_eng_sub"),("Chinese & English","lang_chn_eng"),
    ("Chinese & (Esubs)","lang_chn_esub"),("Multi Audio","lang_multi"),
]
LANG_LABELS = {cb: lbl for lbl,cb in LANG_OPTIONS}

# ── Size options ──────────────────────────────────────────────────────────────
SIZE_OPTIONS = [
    (" Poster (2:3)","size_poster","ani"),
    (" Landscape (16:9)","size_landscape","net"),
    (" Banner (3:1)","size_banner","dark"),
    (" Custom","size_custom",None),
]
SIZE_CB_TO_TEMPLATE = {cb: tmpl for _,cb,tmpl in SIZE_OPTIONS if tmpl}

# ── Abbreviation map ──────────────────────────────────────────────────────────
_ABBR: Dict[str,str] = {
    "aot":"attack on titan","snk":"attack on titan","bnha":"my hero academia","mha":"my hero academia",
    "hxh":"hunter x hunter","jjk":"jujutsu kaisen","csm":"chainsaw man","op":"one piece",
    "fma":"fullmetal alchemist","fmab":"fullmetal alchemist brotherhood","kny":"kimetsu no yaiba",
    "ds":"kimetsu no yaiba","dbs":"dragon ball super","dbz":"dragon ball z","db":"dragon ball",
    "cote":"classroom of the elite","opm":"one punch man","tpn":"promised neverland",
    "sg":"steins gate","mia":"made in abyss","ngnl":"no game no life","nge":"neon genesis evangelion",
    "eva":"neon genesis evangelion","bsd":"bungo stray dogs","sao":"sword art online",
    "re zero":"re zero","rezero":"re zero",
    "demon slayer":"Kimetsu no Yaiba","attack on titan":"Shingeki no Kyojin",
    "my hero academia":"Boku no Hero Academia","jujutsu kaisen":"Jujutsu Kaisen",
    "one punch man":"One Punch-Man","dr stone":"Dr. Stone","promised neverland":"Yakusoku no Neverland",
    "your lie in april":"Shigatsu wa Kimi no Uso","a silent voice":"Koe no Katachi",
    "sword art online":"Sword Art Online","re:zero":"Re:Zero kara Hajimeru Isekai Seikatsu",
    "slime":"Tensei shitara Slime Datta Ken","tensura":"Tensei shitara Slime Datta Ken",
    "that time i got reincarnated as a slime":"Tensei shitara Slime Datta Ken",
    "black clover":"Black Clover","tokyo revengers":"Tokyo Revengers","blue lock":"Blue Lock",
    "chainsaw man":"Chainsaw Man","spy x family":"Spy x Family","spy family":"Spy x Family",
    "bleach":"Bleach","naruto":"Naruto","made in abyss":"Made in Abyss",
    "frieren":"Sousou no Frieren","frieren beyond journeys end":"Sousou no Frieren",
    "oshi no ko":"Oshi no Ko","vinland saga":"Vinland Saga",
    "mushoku tensei":"Mushoku Tensei: Jobless Reincarnation",
    "overlord":"Overlord","no game no life":"No Game No Life",
    "hunter x hunter":"Hunter x Hunter (2011)","fullmetal alchemist":"Fullmetal Alchemist: Brotherhood",
    "fullmetal alchemist brotherhood":"Fullmetal Alchemist: Brotherhood",
    "steins gate":"Steins;Gate","steins;gate":"Steins;Gate","death note":"Death Note",
    "code geass":"Code Geass: Hangyaku no Lelouch","evangelion":"Neon Genesis Evangelion",
    "neon genesis evangelion":"Neon Genesis Evangelion","cowboy bebop":"Cowboy Bebop",
    "fairy tail":"Fairy Tail","konosuba":"Kono Subarashii Sekai ni Shukufuku wo!",
    "eminence in shadow":"Kage no Jitsuryokusha ni Naritakute!","eminence":"Kage no Jitsuryokusha ni Naritakute!",
    "classroom of the elite":"Youkoso Jitsuryoku Shijou Shugi no Kyoushitsu e",
    "shield hero":"Tate no Yuusha no Nariagari","solo leveling":"Ore dake Level Up na Ken",
    "dungeon meshi":"Dungeon Meshi","delicious in dungeon":"Dungeon Meshi",
    "toradora":"Toradora","angel beats":"Angel Beats!","black butler":"Kuroshitsuji",
    "blue exorcist":"Ao no Exorcist","bungo stray dogs":"Bungou Stray Dogs",
    "bungou stray dogs":"Bungou Stray Dogs","noragami":"Noragami","k on":"K-On!","k-on":"K-On!",
    "jojo":"JoJo no Kimyou na Bouken","jojos bizarre adventure":"JoJo no Kimyou na Bouken",
}

_SEASON_RE = [
    (r"\b(s(\d+))\b", lambda m: int(m.group(2))),
    (r"\bseason\s*(\d+)\b", lambda m: int(m.group(1))),
    (r"\b(\d+)(st|nd|rd|th)\s*season\b", lambda m: int(m.group(1))),
    (r"\b(ii)\b", lambda m: 2),(r"\b(iii)\b", lambda m: 3),
    (r"\b(iv)\b", lambda m: 4),(r"\b(final\s*season)\b", lambda m: 99),
]
_SEASON_SUFFIXES: Dict[int,List[str]] = {
    2:["Season 2","2nd Season","II","Part 2"],3:["Season 3","3rd Season","III"],
    4:["Season 4","4th Season","Final Season"],5:["Season 5","5th Season"],
    99:["Final Season","The Final Season"],
}

# ── AniList GQL ───────────────────────────────────────────────────────────────
_ANIME_GQL = """query($s:String){Media(search:$s,type:ANIME,sort:[SEARCH_MATCH,POPULARITY_DESC]){
  id siteUrl title{romaji english native} description(asHtml:false)
  coverImage{extraLarge large medium} bannerImage format status season seasonYear
  episodes duration averageScore popularity genres
  studios(isMain:true){nodes{name}}
  startDate{year month day} nextAiringEpisode{episode timeUntilAiring} countryOfOrigin}}"""

_ANIME_PAGE_GQL = """query($s:String){Page(page:1,perPage:8){media(search:$s,type:ANIME,sort:[SEARCH_MATCH,POPULARITY_DESC]){
  id title{romaji english native} coverImage{medium large} averageScore status seasonYear format}}}"""

_INLINE_GQL = """query($s:String){Page(page:1,perPage:8){media(search:$s,type:ANIME,sort:[SEARCH_MATCH,POPULARITY_DESC]){
  id siteUrl title{romaji english native} coverImage{medium large extraLarge}
  averageScore status seasonYear format episodes genres}}}"""

_MANGA_GQL = """query($s:String){Media(search:$s,type:MANGA,sort:[SEARCH_MATCH,POPULARITY_DESC]){
  id siteUrl title{romaji english native} description(asHtml:false)
  coverImage{extraLarge large} format status chapters volumes averageScore popularity genres
  startDate{year month day} countryOfOrigin}}"""

_CHAR_GQL = """query($s:String){Character(search:$s){name{full native} description siteUrl image{large}}}"""
_AIRING_GQL = """query($s:String){Media(search:$s,type:ANIME,sort:[SEARCH_MATCH,POPULARITY_DESC]){
  id title{romaji english native} episodes status nextAiringEpisode{episode timeUntilAiring}}}"""

# ── TTL Cache (5 min) ─────────────────────────────────────────────────────────
_al_cache: Dict[str, Tuple[float,Any]] = {}
_AL_CACHE_TTL = 300

def _cache_get(key):
    e = _al_cache.get(key)
    if e and (time.time()-e[0]) < _AL_CACHE_TTL: return e[1]
    return None

def _cache_set(key, val):
    _al_cache[key] = (time.time(), val)
    if len(_al_cache) > 200:
        for k,_ in sorted(_al_cache.items(), key=lambda x:x[1][0])[:50]:
            _al_cache.pop(k,None)

def _normalise(q): return re.sub(r"[^\w\s]","",q.lower()).strip()

def _extract_season(q):
    for pat, ext in _SEASON_RE:
        m = re.search(pat, q, re.IGNORECASE)
        if m:
            n = ext(m)
            clean = re.sub(r"\s+"," ",re.sub(pat,"",q,flags=re.IGNORECASE)).strip()
            return clean, n
    return q, None

def _resolve_query(raw):
    qn = _normalise(raw)
    return _ABBR.get(qn) or _ABBR.get(re.sub(r"[^a-z0-9\s]"," ",qn).strip()) or raw

def _season_queries(base, n):
    return [f"{base} {s}" for s in _SEASON_SUFFIXES.get(n,[f"Season {n}"])] + [f"{base} {n}"]

def _al_sync(gql, search):
    ck = f"{gql[:20]}:{search.lower()}"
    cached = _cache_get(ck)
    if cached is not None: return cached
    resolved = _resolve_query(search)
    queries = ([resolved] if resolved.lower()!=search.lower() else []) + [search]
    if search.title()!=search: queries.append(search.title())
    words = search.split()
    if len(words)>2: queries.append(" ".join(words[:3]))
    seen = set()
    for q in queries:
        k = q.lower()
        if k in seen: continue
        seen.add(k)
        try:
            r = requests.post(_AL_URL,json={"query":gql,"variables":{"s":q}},
                headers={"Content-Type":"application/json","Accept":"application/json"},timeout=8)
            if r.status_code!=200: continue
            data = r.json().get("data",{})
            result = data.get("Media") or data.get("Character") or data.get("Page")
            if not result: continue
            if "Media" in data:
                t = result.get("title",{}) or {}
                res_text = " ".join([t.get("english",""),t.get("romaji","")]).lower()
                sw = [w for w in search.lower().split() if len(w)>3]
                if len(sw)>=2 and not any(w in res_text for w in sw):
                    continue
            _cache_set(ck, result)
            return result
        except Exception as exc:
            logger.debug(f"[anime] AniList [{q}]: {exc}")
    return None

def _al_page_sync(search, gql=None):
    gql = gql or _ANIME_PAGE_GQL
    ck = f"page:{gql[:10]}:{search.lower()}"
    cached = _cache_get(ck)
    if cached is not None: return cached
    try:
        r = requests.post(_AL_URL,json={"query":gql,"variables":{"s":search}},
            headers={"Content-Type":"application/json"},timeout=8)
        if r.status_code==200:
            result = r.json().get("data",{}).get("Page",{}).get("media") or []
            _cache_set(ck, result)
            return result
    except Exception: pass
    return []

async def _al(gql, search):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _al_sync, gql, search)

async def _al_page(search):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _al_page_sync, search)

def _clean(text, mx=300):
    if not text: return "No description available."
    text = re.sub(r"<[^>]+>","",text)
    text = re.sub(r"\s+"," ",text).strip()
    return (text[:mx].rsplit(" ",1)[0]+"…") if len(text)>mx else text

# ── Poster generation ─────────────────────────────────────────────────────────
async def _generate_poster_buf(data, media_type, template):
    try:
        from poster_engine import _build_anime_data,_build_manga_data,_build_movie_data,_build_tv_data,_make_poster,_get_settings
    except ImportError: return None
    loop = asyncio.get_event_loop()
    settings = _get_settings(media_type.lower() if media_type!="TV" else "tvshow")
    build_fn = {"ANIME":_build_anime_data,"MANGA":_build_manga_data,"MOVIE":_build_movie_data,"TV":_build_tv_data}.get(media_type,_build_anime_data)
    try:
        title,native,st,rows,desc,cover_url,score = await loop.run_in_executor(None,build_fn,data)
        return await loop.run_in_executor(None,_make_poster,
            template,title,native,st,rows,desc,cover_url,score,
            settings.get("watermark_text"),settings.get("watermark_position","center"),None,"bottom")
    except Exception as exc:
        logger.debug(f"poster_gen [{template}]: {exc}"); return None

def _build_caption(data):
    td = data.get("title",{}) or {}
    eng = td.get("english") or td.get("romaji") or "Unknown"
    native = td.get("native","")
    genres = ", ".join((data.get("genres") or [])[:3])
    score = data.get("averageScore","?")
    status = (data.get("status") or "").replace("_"," ").title()
    eps = data.get("episodes","?")
    fmt = (data.get("format") or "").replace("_"," ")
    sn = ((data.get("studios") or {}).get("nodes") or [])
    studio = sn[0].get("name","") if sn else ""
    cap = f"<b>{_e(eng)}</b>"
    if native: cap += f"\n<i>{_e(native)}</i>"
    cap += "\n\n"
    if genres: cap += f"» <b>{_sc('Genre')}:</b> {_e(genres)}\n"
    if score and str(score) not in ("?","0","None"): cap += f"» <b>{_sc('Rating')}:</b> <code>{score}/100</code>\n"
    if status: cap += f"» <b>{_sc('Status')}:</b> {_e(status)}\n"
    if eps and str(eps) not in ("?","0","None"): cap += f"» <b>{_sc('Episodes')}:</b> <code>{eps}</code>\n"
    if fmt: cap += f"» <b>{_sc('Format')}:</b> {_e(fmt)}\n"
    if studio: cap += f"» <b>{_sc('Studio')}:</b> {_e(studio)}\n"
    desc = _clean(data.get("description",""),200)
    if desc and desc!="No description available.": cap += f"\n{_bq(_e(desc))}"
    return cap[:1024]

def _info_kb(data):
    site = data.get("siteUrl","")
    row = []
    if site: row.append(InlineKeyboardButton(_sc("📋 Info"),url=site))
    row.append(InlineKeyboardButton(_sc("📢 BeatAnime"),url="https://t.me/BeatAnime"))
    return InlineKeyboardMarkup([row])

# ── UI panels ─────────────────────────────────────────────────────────────────
async def _show_similar_panel(update, context, base_query, season_num):
    msg = update.message or (update.callback_query.message if update.callback_query else None)
    if not msg: return
    loading = None
    try: loading = await msg.reply_text(_b("🔍 searching similar titles…"),parse_mode=ParseMode.HTML)
    except Exception: pass
    results = await _al_page(base_query)
    if loading:
        try: await loading.delete()
        except Exception: pass
    if not results:
        context.user_data["anime_query"] = base_query
        context.user_data["season_num"]  = season_num
        await _show_language_panel(update, context)
        return
    context.user_data.update({"similar_results":results[:8],"season_num":season_num,"anime_query":base_query})
    btns: List[List] = []; row: List = []
    for i,item in enumerate(results[:8]):
        t = item.get("title",{}) or {}
        name = t.get("english") or t.get("romaji") or "Unknown"
        year = item.get("seasonYear","")
        lbl = f"{name[:22]} ({year})" if year else name[:28]
        row.append(InlineKeyboardButton(lbl,callback_data=f"anpick_{i}"))
        if len(row)==2: btns.append(row); row=[]
    if row: btns.append(row)
    btns.append([InlineKeyboardButton(_sc("🔍 Keep My Query"),callback_data="anpick_custom"),
                 InlineKeyboardButton(_sc("❌ Cancel"),callback_data="anpick_cancel")])
    await msg.reply_text(_b("🎌 select exact title")+"\n"+_bq(_sc("pick the correct title for the poster:")),
        parse_mode=ParseMode.HTML,reply_markup=InlineKeyboardMarkup(btns))

async def _show_language_panel(update, context):
    msg = update.message or (update.callback_query.message if update.callback_query else None)
    if not msg: return
    rows: List[List] = []; row: List = []
    for lbl,cb in LANG_OPTIONS:
        row.append(InlineKeyboardButton(_sc(lbl),callback_data=cb))
        if len(row)==2: rows.append(row); row=[]
    if row: rows.append(row)
    rows.append([InlineKeyboardButton(_sc("CANCEL"),callback_data="anpick_cancel")])
    await msg.reply_text(_b("🎧 select audio language"),parse_mode=ParseMode.HTML,reply_markup=InlineKeyboardMarkup(rows))

async def _show_size_panel(update, context):
    msg = update.message or (update.callback_query.message if update.callback_query else None)
    if not msg: return
    rows: List[List] = []; row: List = []
    for lbl,cb,_ in SIZE_OPTIONS:
        row.append(InlineKeyboardButton(_sc(lbl),callback_data=cb))
        if len(row)==2: rows.append(row); row=[]
    if row: rows.append(row)
    rows.append([InlineKeyboardButton(_sc("CANCEL"),callback_data="anpick_cancel")])
    await msg.reply_text(_b("📐 select poster type"),parse_mode=ParseMode.HTML,reply_markup=InlineKeyboardMarkup(rows))

# ── Poster delivery ───────────────────────────────────────────────────────────
async def _deliver_poster(update, context, data, template, media_type):
    msg = update.message or (update.callback_query.message if update.callback_query else None)
    if not msg: return
    loading = None
    try: loading = await msg.reply_text(_b("🎨 generating poster…"),parse_mode=ParseMode.HTML)
    except Exception: pass
    poster_buf = await _generate_poster_buf(data, media_type, template)
    if loading:
        try: await loading.delete()
        except Exception: pass
    caption = _build_caption(data)
    kb = _info_kb(data)
    sent_poster = None
    if poster_buf:
        poster_buf.seek(0)
        try:
            sent_poster = await msg.reply_photo(photo=poster_buf,caption=caption,
                parse_mode=ParseMode.HTML,reply_markup=kb)
        except Exception as exc: logger.debug(f"poster send: {exc}")
    if not sent_poster:
        cv = (data.get("coverImage") or {}).get("extraLarge","")
        lp = f'\n<a href="{_e(cv)}">&#8203;</a>' if cv else ""
        try:
            sent_poster = await msg.reply_text(caption+lp,parse_mode=ParseMode.HTML,
                reply_markup=kb,disable_web_page_preview=not cv)
        except Exception: pass
    td = data.get("title",{}) or {}
    context.user_data.update({
        "poster_data":data,"poster_media_type":media_type,"poster_template":template,
        "poster_tmpl_idx":TEMPLATES.index(template) if template in TEMPLATES else 0,
        "poster_title":td.get("english") or td.get("romaji") or "Unknown",
        "poster_msg_id":sent_poster.message_id if sent_poster else None,
        "poster_chat_id":msg.chat_id,
        "awaiting_thumbnail":True,
        "awaiting_thumbnail_uid":msg.from_user.id if msg.from_user else None,
    })
    thumb_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(_sc("🔜 NEXT IMG"),callback_data="anthmb_next"),
        InlineKeyboardButton(_sc("SKIP"),callback_data="anthmb_skip"),
    ],[InlineKeyboardButton(_sc("CANCEL"),callback_data="anthmb_cancel")]])
    await msg.reply_text(
        "📸 <b>Cᴜsᴛᴏᴍ Tʜᴜᴍʙɴᴀɪʟ</b>\n\nSᴇɴᴅ ᴍᴇ ᴀ ᴄᴜsᴛᴏᴍ ᴛʜᴜᴍʙɴᴀɪʟ ɪᴍᴀɢᴇ, ᴏʀ ᴄʟɪᴄᴋ Sᴋɪᴘ ᴛᴏ ᴜsᴇ ᴛʜɪs ᴘᴏsᴛᴇʀ.",
        parse_mode=ParseMode.HTML, reply_markup=thumb_kb)

# ── GC Single-Letter Anime Filter Panel ──────────────────────────────────────
_FILTER_PANEL_TTL = int(os.getenv("FILTER_PANEL_TTL","20"))
_FILTER_PAGE_SIZE = 8
# {uid: {"chat_id":int,"msg_id":int,"pages":list,"letter":str,"exp_min":int,"task":Task}}
_active_filter_panels: Dict[int,Dict] = {}

async def _send_alpha_filter_panel(update, context, letter):
    """Show all anime from DB starting with `letter` as paged inline buttons."""
    chat_id = update.effective_chat.id
    uid = update.effective_user.id if update.effective_user else 0

    # Cancel existing panel for this user
    prev = _active_filter_panels.get(uid)
    if prev:
        try:
            t = prev.get("task")
            if t and not t.done(): t.cancel()
        except Exception: pass
        try: await context.bot.delete_message(prev["chat_id"],prev["msg_id"])
        except Exception: pass
        _active_filter_panels.pop(uid,None)

    try:
        from database_dual import get_all_links
        all_links = get_all_links(limit=500,offset=0) or []
        try:
            from filter_poster import get_link_expiry_minutes
            exp_min = int(get_link_expiry_minutes(chat_id))
        except Exception: exp_min = 60
    except Exception: return

    ll = letter.lower()
    matched=[]; seen=set()
    for row in all_links:
        lid,cid,ctitle = row[0],row[1],(row[2] or "").strip()
        if not ctitle or ctitle.lower() in seen: continue
        if not ctitle.lower().startswith(ll): continue
        seen.add(ctitle.lower())
        matched.append((lid,cid,ctitle))

    if not matched: return  # silent — no anime with this letter

    pages = [matched[i:i+_FILTER_PAGE_SIZE] for i in range(0,len(matched),_FILTER_PAGE_SIZE)]
    total_pages = len(pages)
    _active_filter_panels[uid] = {"chat_id":chat_id,"msg_id":None,"pages":pages,
                                   "letter":letter,"exp_min":exp_min,"task":None}

    async def _build_kb(pi):
        items = pages[pi]; btns=[]; brow=[]
        for lid,cid,ct in items:
            deep = f"https://t.me/{context.bot.username}?start={lid}"
            brow.append(InlineKeyboardButton(ct[:30],url=deep))
            if len(brow)==2: btns.append(brow); brow=[]
        if brow: btns.append(brow)
        nav=[]
        if pi>0: nav.append(InlineKeyboardButton("🔙",callback_data=f"alpha_page:{uid}:{letter}:{pi-1}"))
        if pi<total_pages-1: nav.append(InlineKeyboardButton("🔜",callback_data=f"alpha_page:{uid}:{letter}:{pi+1}"))
        if nav: btns.append(nav)
        btns.append([InlineKeyboardButton("✖️ Close",callback_data=f"alpha_close:{uid}")])
        return InlineKeyboardMarkup(btns)

    text = (f"<b>🎌 ᴀɴɪᴍᴇ — <code>{letter.upper()}</code></b>\n"
            f"<i>Page 1/{total_pages} • ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇs ɪɴ {_FILTER_PANEL_TTL}s</i>\n━━━━━━━━━━━━━━━━━━━")
    kb = await _build_kb(0)

    try:
        sent = await context.bot.send_message(chat_id=chat_id,text=text,parse_mode=ParseMode.HTML,reply_markup=kb)
        _active_filter_panels[uid]["msg_id"] = sent.message_id
    except Exception:
        _active_filter_panels.pop(uid,None); return

    async def _auto_del():
        await asyncio.sleep(_FILTER_PANEL_TTL)
        try: await context.bot.delete_message(chat_id,sent.message_id)
        except Exception: pass
        _active_filter_panels.pop(uid,None)

    task = asyncio.create_task(_auto_del())
    _active_filter_panels[uid]["task"] = task

async def _alpha_filter_callback(update, context):
    query = update.callback_query
    if not query: return
    try: await query.answer()
    except Exception: pass
    cb = query.data or ""

    if cb.startswith("alpha_close:"):
        uid = int(cb.split(":")[1])
        panel = _active_filter_panels.get(uid)
        if panel:
            t = panel.get("task")
            if t and not t.done(): t.cancel()
            _active_filter_panels.pop(uid,None)
        try: await query.message.delete()
        except Exception: pass
        return

    if cb.startswith("alpha_page:"):
        parts = cb.split(":")
        if len(parts)<4: return
        uid = int(parts[1]); letter = parts[2]; pi = int(parts[3])
        panel = _active_filter_panels.get(uid)
        if not panel:
            try: await query.answer("Panel expired. Type the letter again.",show_alert=True)
            except Exception: pass
            return
        pages = panel.get("pages",[])
        total_pages = len(pages)
        if pi<0 or pi>=total_pages: return
        items = pages[pi]
        text = (f"<b>🎌 ᴀɴɪᴍᴇ — <code>{letter.upper()}</code></b>\n"
                f"<i>Page {pi+1}/{total_pages} • ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇs ɪɴ {_FILTER_PANEL_TTL}s</i>\n━━━━━━━━━━━━━━━━━━━")
        btns=[]; brow=[]
        for lid,cid,ct in items:
            deep = f"https://t.me/{context.bot.username}?start={lid}"
            brow.append(InlineKeyboardButton(ct[:30],url=deep))
            if len(brow)==2: btns.append(brow); brow=[]
        if brow: btns.append(brow)
        nav=[]
        if pi>0: nav.append(InlineKeyboardButton("🔙",callback_data=f"alpha_page:{uid}:{letter}:{pi-1}"))
        if pi<total_pages-1: nav.append(InlineKeyboardButton("🔜",callback_data=f"alpha_page:{uid}:{letter}:{pi+1}"))
        if nav: btns.append(nav)
        btns.append([InlineKeyboardButton("✖️ Close",callback_data=f"alpha_close:{uid}")])
        try:
            await query.message.edit_text(text=text,parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(btns))
        except Exception: pass

# ── Inline search (called from bot.py inline_query_handler) ──────────────────
async def inline_search_anime(search, bot_username, join_btn_text="ᴊᴏɪɴ ɴᴏᴡ"):
    """Returns list of InlineQueryResult with poster+info for a search query."""
    from uuid import uuid4
    if not search: return []
    loop = asyncio.get_event_loop()
    items = await loop.run_in_executor(None, _al_page_sync, search, _INLINE_GQL)
    if not items: return []
    results = []
    for item in items[:8]:
        t = item.get("title",{}) or {}
        title  = t.get("english") or t.get("romaji") or "Unknown"
        native = t.get("native","")
        score  = item.get("averageScore","")
        status = (item.get("status") or "").replace("_"," ").title()
        year   = item.get("seasonYear","")
        fmt    = (item.get("format") or "").replace("_"," ")
        site   = item.get("siteUrl","https://anilist.co")
        eps    = item.get("episodes","")
        genres = ", ".join((item.get("genres") or [])[:2])
        ci     = item.get("coverImage",{}) or {}
        cover  = ci.get("extraLarge") or ci.get("large") or ci.get("medium","")
        thumb  = ci.get("medium") or ci.get("large") or cover
        score_str = f"{score}/100" if score else "N/A"
        cap = f"<b>{_e(title)}</b>"
        if native: cap += f"\n<i>{_e(native)}</i>"
        cap += "\n\n"
        if genres: cap += f"» <b>Genre:</b> {_e(genres)}\n"
        if score_str!="N/A": cap += f"» <b>Rating:</b> <code>{score_str}</code>\n"
        if status: cap += f"» <b>Status:</b> {_e(status)}\n"
        if eps: cap += f"» <b>Episodes:</b> <code>{eps}</code>\n"
        if fmt: cap += f"» <b>Format:</b> {_e(fmt)}\n"
        if year: cap += f"» <b>Year:</b> <code>{year}</code>\n"
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("📋 AniList",url=site),
            InlineKeyboardButton("🔍 Watch",switch_inline_query_current_chat=f"watch {title}"),
        ]])
        if cover:
            try:
                results.append(InlineQueryResultPhoto(
                    id=str(uuid4()),photo_url=cover,thumbnail_url=thumb or cover,
                    title=title[:40],description=f"{'⭐'+score_str if score else ''} • {status} • {fmt}",
                    caption=cap,parse_mode=ParseMode.HTML,reply_markup=kb))
                continue
            except Exception: pass
        results.append(InlineQueryResultArticle(
            id=str(uuid4()),title=title[:40],
            description=f"{score_str} • {status} • {fmt}",
            input_message_content=InputTextMessageContent(cap,parse_mode=ParseMode.HTML),
            reply_markup=kb,thumb_url=thumb or ""))
    return results

# ── Callback handler ──────────────────────────────────────────────────────────
async def _anime_callback(update, context):
    query = update.callback_query
    if not query: return
    try: await query.answer()
    except Exception: pass
    cb = query.data or ""; msg = query.message

    if cb.startswith("anpick_"):
        if cb=="anpick_cancel":
            try: await msg.delete()
            except Exception: pass
            return
        if cb=="anpick_custom":
            try: await msg.delete()
            except Exception: pass
            await _show_language_panel(update,context); return
        try:
            idx = int(cb.split("_")[1])
            res = context.user_data.get("similar_results",[])
            if 0<=idx<len(res):
                t = res[idx].get("title",{}) or {}
                context.user_data["anime_query"] = t.get("english") or t.get("romaji") or ""
        except (ValueError,IndexError): pass
        try: await msg.delete()
        except Exception: pass
        await _show_language_panel(update,context); return

    if cb.startswith("lang_"):
        context.user_data["selected_lang"] = LANG_LABELS.get(cb,"English")
        try: await msg.delete()
        except Exception: pass
        await _show_size_panel(update,context); return

    if cb.startswith("size_"):
        template = SIZE_CB_TO_TEMPLATE.get(cb,"ani")
        context.user_data["poster_template"] = template
        try: await msg.delete()
        except Exception: pass
        base_q = context.user_data.get("anime_query","")
        sn     = context.user_data.get("season_num")
        mt     = context.user_data.get("media_type","ANIME")
        sqs    = _season_queries(base_q,sn) if sn and sn>1 else [base_q]
        loading=None
        try: loading = await msg.reply_text(_b(f"🔎 fetching {_e(sqs[0])}…"),parse_mode=ParseMode.HTML)
        except Exception: pass
        gql = _ANIME_GQL if mt=="ANIME" else _MANGA_GQL
        data=None; loop=asyncio.get_event_loop()
        for sq in sqs:
            data = await loop.run_in_executor(None,_al_sync,gql,sq)
            if data: break
        if loading:
            try: await loading.delete()
            except Exception: pass
        if not data:
            try: await msg.reply_text(_b(f"❌ not found: {_e(sqs[0])}"),parse_mode=ParseMode.HTML)
            except Exception: pass
            return
        await _deliver_poster(update,context,data,template,mt); return

    if cb=="anthmb_next":
        dd = context.user_data.get("poster_data"); mt = context.user_data.get("poster_media_type","ANIME")
        ti = context.user_data.get("poster_tmpl_idx",0)
        if not dd: await query.answer(_sc("session expired"),show_alert=True); return
        ti = (ti+1)%len(TEMPLATES); nt = TEMPLATES[ti]
        context.user_data.update({"poster_tmpl_idx":ti,"poster_template":nt})
        try: await query.answer(_sc(f"{TEMPLATE_LABELS.get(nt,nt)} style…"))
        except Exception: pass
        loading=None
        try: loading=await msg.reply_text(_b(_sc(f"generating {TEMPLATE_LABELS.get(nt,nt)} style…")),parse_mode=ParseMode.HTML)
        except Exception: pass
        nb = await _generate_poster_buf(dd,mt,nt)
        if loading:
            try: await loading.delete()
            except Exception: pass
        if not nb:
            try: await query.answer(_sc("could not generate poster"),show_alert=True)
            except Exception: pass
            return
        pm = context.user_data.get("poster_msg_id"); pc = context.user_data.get("poster_chat_id")
        edited=False
        if pm and pc:
            try:
                nb.seek(0)
                await query.bot.edit_message_media(chat_id=pc,message_id=pm,
                    media=InputMediaPhoto(media=nb,caption=_build_caption(dd),parse_mode=ParseMode.HTML),
                    reply_markup=_info_kb(dd))
                edited=True
            except Exception as exc: logger.debug(f"next img edit: {exc}")
        if not edited:
            try:
                nb.seek(0)
                sent=await msg.reply_photo(photo=nb,caption=_build_caption(dd),
                    parse_mode=ParseMode.HTML,reply_markup=_info_kb(dd))
                context.user_data.update({"poster_msg_id":sent.message_id,"poster_chat_id":msg.chat_id})
            except Exception as exc: logger.debug(f"next img send: {exc}")
        return

    if cb=="anthmb_skip":
        try: await msg.delete()
        except Exception: pass
        context.user_data.pop("awaiting_thumbnail",None)
        try: await query.answer(_sc("✅ using this poster"))
        except Exception: pass
        return

    if cb=="anthmb_cancel":
        try: await msg.delete()
        except Exception: pass
        pm=context.user_data.get("poster_msg_id"); pc=context.user_data.get("poster_chat_id")
        if pm and pc:
            try: await query.bot.delete_message(pc,pm)
            except Exception: pass
        context.user_data.clear()
        try: await query.answer(_sc("cancelled"))
        except Exception: pass
        return

# ── Custom thumbnail photo handler ────────────────────────────────────────────
async def _thumbnail_photo_handler(update, context):
    if not context.user_data.get("awaiting_thumbnail"): return
    msg = update.message
    if not msg or not msg.photo: return
    eu = context.user_data.get("awaiting_thumbnail_uid")
    if eu and update.effective_user and update.effective_user.id!=eu: return
    context.user_data.pop("awaiting_thumbnail",None)
    fid = msg.photo[-1].file_id
    dd = context.user_data.get("poster_data",{}); cap=_build_caption(dd) if dd else ""; kb=_info_kb(dd) if dd else None
    pm=context.user_data.get("poster_msg_id"); pc=context.user_data.get("poster_chat_id")
    if pm and pc:
        try:
            await msg.bot.edit_message_media(chat_id=pc,message_id=pm,
                media=InputMediaPhoto(media=fid,caption=cap,parse_mode=ParseMode.HTML),reply_markup=kb)
            await msg.reply_text(_b(_sc("✅ custom thumbnail applied!")),parse_mode=ParseMode.HTML)
            context.user_data.clear(); return
        except Exception: pass
    await msg.reply_photo(photo=fid,caption=cap,parse_mode=ParseMode.HTML,reply_markup=kb)
    context.user_data.clear()

# ── Command handlers ──────────────────────────────────────────────────────────
async def anime_cmd(update, context):
    if not context.args:
        await update.message.reply_text(_b("usage:")+" /anime &lt;name&gt;\n"+_bq("• /anime demon slayer\n• /anime aot s2\n• /anime jjk season 2\n• /anime frieren"),parse_mode=ParseMode.HTML); return
    raw_q=(" ".join(context.args)); base_q,sn=_extract_season(raw_q); resolved=_resolve_query(base_q)
    context.user_data.update({"media_type":"ANIME","anime_query":resolved,"season_num":sn})
    await _show_similar_panel(update,context,resolved,sn)

async def manga_cmd(update, context):
    if not context.args:
        await update.message.reply_text(_b("usage:")+" /manga &lt;name&gt;",parse_mode=ParseMode.HTML); return
    q=" ".join(context.args)
    context.user_data.update({"media_type":"MANGA","anime_query":q,"season_num":None})
    await _show_similar_panel(update,context,q,None)

async def movie_cmd(update, context):
    if not context.args:
        await update.message.reply_text(_b("usage:")+" /movie &lt;name&gt;",parse_mode=ParseMode.HTML); return
    q=" ".join(context.args)
    context.user_data.update({"media_type":"MOVIE","anime_query":q,"season_num":None})
    await _show_language_panel(update,context)

async def tvshow_cmd(update, context):
    if not context.args:
        await update.message.reply_text(_b("usage:")+" /tvshow &lt;name&gt;",parse_mode=ParseMode.HTML); return
    q=" ".join(context.args)
    context.user_data.update({"media_type":"TV","anime_query":q,"season_num":None})
    await _show_language_panel(update,context)

async def net_cmd(update, context):
    if not context.args:
        await update.message.reply_text(_b("usage:")+" /net &lt;title&gt;",parse_mode=ParseMode.HTML); return
    q=" ".join(context.args); loop=asyncio.get_event_loop()
    context.user_data.update({"media_type":"ANIME","anime_query":q,"season_num":None,"selected_lang":"English","poster_template":"net"})
    data=await loop.run_in_executor(None,_al_sync,_ANIME_GQL,q)
    if not data: await update.message.reply_text(_b(f"❌ not found: {_e(q)}"),parse_mode=ParseMode.HTML); return
    await _deliver_poster(update,context,data,"net","ANIME")

async def airing_cmd(update, context):
    if not context.args:
        await update.message.reply_text(_b("usage:")+" /airing &lt;anime name&gt;",parse_mode=ParseMode.HTML); return
    data=await _al(_AIRING_GQL," ".join(context.args))
    if not data: await update.message.reply_text("❌ Anime not found."); return
    td=data.get("title",{}) or {}; title=td.get("english") or td.get("romaji") or "Unknown"; native=td.get("native",""); nxt=data.get("nextAiringEpisode")
    if nxt:
        secs=nxt.get("timeUntilAiring",0); d,r=divmod(secs,86400); h,r2=divmod(r,3600); m=r2//60
        ts=f"{d}d {h}h {m}m" if d else f"{h}h {m}m"
        txt=f"<b>{_e(title)}</b>"+(f" (<i>{_e(native)}</i>)" if native else "")+f"\n\n <b>Episode {nxt.get('episode','?')}</b> {_sc('airs in')} <code>{ts}</code>"
    else:
        st=(data.get("status") or "").replace("_"," ").title()
        txt=f"<b>{_e(title)}</b>"+(f" (<i>{_e(native)}</i>)" if native else "")+f"\n\n <b>{_sc('Episodes')}:</b> {data.get('episodes','?')}\n <b>{_sc('Status')}:</b> {_e(st)}"
    await update.message.reply_text(txt,parse_mode=ParseMode.HTML)

async def character_cmd(update, context):
    if not context.args:
        await update.message.reply_text(_b("usage:")+" /character &lt;name&gt;",parse_mode=ParseMode.HTML); return
    data=await _al(_CHAR_GQL," ".join(context.args))
    if not data: await update.message.reply_text("❌ Character not found."); return
    nm=data.get("name",{}) or {}; full=nm.get("full","Unknown"); native=nm.get("native","")
    desc=_clean(data.get("description",""),350); site=data.get("siteUrl","https://anilist.co"); img=(data.get("image") or {}).get("large")
    txt=f"<b>{_e(full)}</b>"+(f" (<i>{_e(native)}</i>)" if native else "")+f"\n\n{_e(desc)}"
    if len(txt)>1020: txt=txt[:1016]+"…"
    kb=InlineKeyboardMarkup([[InlineKeyboardButton(" AniList",url=site)]])
    if img:
        try: await update.message.reply_photo(photo=img,caption=txt,parse_mode=ParseMode.HTML,reply_markup=kb); return
        except Exception: pass
    await update.message.reply_text(txt,parse_mode=ParseMode.HTML,reply_markup=kb)

async def imdb_cmd(update, context):
    if not context.args:
        await update.message.reply_text(_b("usage:")+" /imdb &lt;movie or show name&gt;",parse_mode=ParseMode.HTML); return
    q=" ".join(context.args); loop=asyncio.get_event_loop()
    loading=await update.message.reply_text(_b(" searching…"),parse_mode=ParseMode.HTML)
    tmdb_result=None
    if _TMDB_KEY:
        try:
            r=requests.get("https://api.themoviedb.org/3/search/multi",params={"api_key":_TMDB_KEY,"query":q},timeout=8)
            res=r.json().get("results",[])
            if res: tmdb_result=res[0]
        except Exception: pass
    try: await loading.delete()
    except Exception: pass
    if not tmdb_result:
        al=await loop.run_in_executor(None,_al_sync,_ANIME_GQL,q)
        if al:
            cap=_build_caption(al); kb=_info_kb(al); cv=(al.get("coverImage") or {}).get("extraLarge","")
            if cv:
                try: await update.message.reply_photo(photo=cv,caption=cap,parse_mode=ParseMode.HTML,reply_markup=kb); return
                except Exception: pass
            await update.message.reply_text(cap,parse_mode=ParseMode.HTML,reply_markup=kb,disable_web_page_preview=True); return
        await update.message.reply_text(_b(f"❌ not found: {_e(q)}"),parse_mode=ParseMode.HTML); return
    mtype=tmdb_result.get("media_type","movie"); title=tmdb_result.get("title") or tmdb_result.get("name") or q
    year=(tmdb_result.get("release_date") or tmdb_result.get("first_air_date") or "")[:4]
    rating=tmdb_result.get("vote_average","?"); overview=_clean(tmdb_result.get("overview",""),250)
    poster_p=tmdb_result.get("poster_path",""); tmdb_id=tmdb_result.get("id",0)
    tmdb_url=f"https://www.themoviedb.org/{mtype}/{tmdb_id}"; img_url=f"https://image.tmdb.org/t/p/w500{poster_p}" if poster_p else ""
    cap=f"<b>{_e(title)}</b>"+(f" <code>({year})</code>" if year else "")+f"\n\n» <b>{_sc('Rating')}:</b> <code>{rating}/10</code>\n» <b>{_sc('Type')}:</b> {_e(mtype.title())}"+(f"\n\n{_bq(_e(overview))}" if overview else "")
    if len(cap)>1020: cap=cap[:1016]+"…"
    kb=InlineKeyboardMarkup([[InlineKeyboardButton(" TMDB",url=tmdb_url)]])
    if img_url:
        try: await update.message.reply_photo(photo=img_url,caption=cap,parse_mode=ParseMode.HTML,reply_markup=kb); return
        except Exception: pass
    await update.message.reply_text(cap,parse_mode=ParseMode.HTML,reply_markup=kb,disable_web_page_preview=True)

# ── Register handlers ─────────────────────────────────────────────────────────
def register(app):
    for cmd,fn in [("anime",anime_cmd),("tvshow",tvshow_cmd),("movie",movie_cmd),("net",net_cmd),
                   ("manga",manga_cmd),("airing",airing_cmd),("character",character_cmd),("imdb",imdb_cmd)]:
        app.add_handler(CommandHandler(cmd,fn))
    app.add_handler(CallbackQueryHandler(_anime_callback,pattern=r"^(anpick_|lang_|size_|anthmb_)"))
    app.add_handler(CallbackQueryHandler(_alpha_filter_callback,pattern=r"^(alpha_page:|alpha_close:)"))
    app.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, _thumbnail_photo_handler))
    logger.info("[anime] Handlers registered")

try:
    from beataniversebot_compat import dispatcher
    from modules.disable import DisableAbleCommandHandler
    from telegram.ext import Filters, CallbackQueryHandler as CQH, MessageHandler as MH
    for cmd,fn in [("anime",anime_cmd),("tvshow",tvshow_cmd),("movie",movie_cmd),("net",net_cmd),
                   ("manga",manga_cmd),("airing",airing_cmd),("character",character_cmd),("imdb",imdb_cmd)]:
        dispatcher.add_handler(DisableAbleCommandHandler(cmd,fn,run_async=True))
    dispatcher.add_handler(CQH(_anime_callback,pattern=r"^(anpick_|lang_|size_|anthmb_)",run_async=True))
    dispatcher.add_handler(CQH(_alpha_filter_callback,pattern=r"^(alpha_page:|alpha_close:)",run_async=True))
    dispatcher.add_handler(MH(Filters.photo & ~Filters.command,_thumbnail_photo_handler,run_async=True))
except Exception: pass

__mod_name__     = "Aɴɪᴍᴇ"
__command_list__ = ["anime","tvshow","movie","net","manga","airing","character","imdb"]
__help__ = """
• /anime <name> — anime poster + info
• /anime aot s2 — season 2 specific poster
• /tvshow /movie /net /manga /airing /character /imdb — see each command usage
• GC: type a single letter (e.g. t) to browse anime starting with that letter
"""
