# ==============================================================================
# PLACE AT: /app/panel_image.py
# ACTION: Replace existing file
# ==============================================================================
#!/usr/bin/env python3
"""
BeatAniVerse Bot — Panel Image System
========================================
Priority order (toggleable from admin panel):
  SOURCE A: URL list  — PANEL_PICS env OR custom URLs saved in DB
  SOURCE B: APIs      — waifu.im → nekos.best → anilist → safone → tmdb → static

Admin can toggle PRIMARY source between URL and API via:
  Admin Panel → SETTINGS → 🖼 PANEL IMAGE SOURCE

Results cached 30 min. First load always instant (pre-warmed with static).
"""

import os, time, random, logging, asyncio
import concurrent.futures
from typing import Optional, Dict, Any

import requests

logger = logging.getLogger(__name__)

# ── PANEL_PICS env (always instant, no API) ────────────────────────────────────
_PANEL_PICS_ENV: list = [
    u.strip() for u in os.getenv("PANEL_PICS", "").split(",")
    if u.strip().startswith("http")
]

WALL_API_KEY: str = os.getenv("WALL_API_KEY", "")
TMDB_API_KEY: str = os.getenv("TMDB_API_KEY", "")

_CACHE_TTL = 1800   # 30 min

_img_cache: Dict[str, str]   = {}
_cache_ts:  Dict[str, float] = {}

# ── Static fallbacks — always work, pre-warm cache ────────────────────────────
_STATIC_FALLBACKS = [
    "https://i.imgur.com/WdTdHhv.jpeg",
    "https://i.imgur.com/YeQjKJh.jpeg",
    "https://i.imgur.com/V8gkYXC.jpeg",
    "https://i.imgur.com/aLqjMV7.jpeg",
    "https://cdn.myanimelist.net/images/anime/1988/119092.jpg",
    "https://cdn.myanimelist.net/images/anime/1223/121781.jpg",
    "https://cdn.myanimelist.net/images/anime/1170/124216.jpg",
    "https://images.alphacoders.com/133/thumb-1920-1330574.jpg",
    "https://images.alphacoders.com/133/thumb-1920-1330590.jpg",
    "https://images.alphacoders.com/130/thumb-1920-1301234.jpg",
]

_PANEL_TAGS = {
    "admin":       ["maid", "elf"],
    "stats":       ["oppai", "uniform"],
    "users":       ["waifu", "raiden-shogun"],
    "channels":    ["maid", "school"],
    "clones":      ["elf", "kamisato-ayaka"],
    "settings":    ["waifu", "maid"],
    "broadcast":   ["uniform", "holo"],
    "upload":      ["waifu", "school"],
    "categories":  ["elf", "marin-kitagawa"],
    "poster":      ["waifu", "maid"],
    "manga":       ["waifu", "uniform"],
    "autoforward": ["maid", "elf"],
    "flags":       ["raiden-shogun", "kamisato-ayaka"],
    "style":       ["waifu", "school"],
    "default":     ["waifu", "maid", "elf", "uniform"],
}

# Pre-warm with statics so first load is always instant
for _pk in list(_PANEL_TAGS.keys()) + ["default"]:
    if _pk not in _img_cache:
        _img_cache[_pk] = random.choice(_STATIC_FALLBACKS)
        _cache_ts[_pk]  = 0.0   # expired → will refresh on next non-blocking call

# ── DB helpers (read primary source setting) ──────────────────────────────────
def _get_primary_source() -> str:
    """
    Returns 'url' or 'api'.
    Reads from DB setting 'panel_image_source'. Default = 'url'.
    """
    try:
        from database_dual import get_setting
        return get_setting("panel_image_source", "url") or "url"
    except Exception:
        return "url"

def _get_custom_urls() -> list:
    """
    Returns list of custom URLs saved via admin panel (panel_image_urls setting).
    Falls back to PANEL_PICS env.
    """
    try:
        from database_dual import get_setting
        import json as _j
        raw = get_setting("panel_image_urls", "")
        if raw:
            urls = _j.loads(raw)
            if isinstance(urls, list) and urls:
                return urls
    except Exception:
        pass
    return _PANEL_PICS_ENV

def _now() -> float:
    return time.time()

def _is_cached(panel: str) -> bool:
    return (
        panel in _img_cache and
        panel in _cache_ts and
        (_now() - _cache_ts[panel]) < _CACHE_TTL
    )

def _set_cache(panel: str, url: str) -> None:
    _img_cache[panel] = url
    _cache_ts[panel]  = _now()


# ── API fetchers ──────────────────────────────────────────────────────────────
def _fetch_waifu_im(panel: str) -> Optional[str]:
    tags = _PANEL_TAGS.get(panel, _PANEL_TAGS["default"])
    tag  = random.choice(tags)
    try:
        r = requests.get(
            "https://api.waifu.im/search",
            params={"included_tags": tag, "is_nsfw": "false", "many": "true", "limit": "10"},
            timeout=5, headers={"Accept": "application/json"},
        )
        if r.status_code == 200:
            images = r.json().get("images", [])
            if images:
                hd = [i for i in images if i.get("width", 0) >= 1280]
                return random.choice(hd if hd else images).get("url")
    except Exception as exc:
        logger.debug(f"waifu.im: {exc}")
    return None

_NEKOS_ENDPOINTS = ["waifu", "neko", "kitsune", "shinobu", "megumin",
                    "zero_two", "aqua", "rem", "mai"]

def _fetch_nekos_best(panel: str) -> Optional[str]:
    try:
        r = requests.get(
            f"https://nekos.best/api/v2/{random.choice(_NEKOS_ENDPOINTS)}",
            params={"amount": "5"}, timeout=5,
        )
        if r.status_code == 200:
            results = r.json().get("results", [])
            if results:
                url = random.choice(results).get("url", "")
                if url.endswith((".jpg", ".jpeg", ".png", ".webp")):
                    return url
    except Exception as exc:
        logger.debug(f"nekos.best: {exc}")
    return None

_ANILIST_POPULAR = [
    "Demon Slayer", "Attack on Titan", "Jujutsu Kaisen", "Chainsaw Man",
    "One Piece", "Frieren", "Violet Evergarden", "Your Lie in April",
    "Made in Abyss", "Blue Lock", "Spy x Family", "Oshi no Ko",
]

def _fetch_anilist_banner() -> Optional[str]:
    title = random.choice(_ANILIST_POPULAR)
    try:
        r = requests.post(
            "https://graphql.anilist.co",
            json={
                "query": "query($s:String){Media(search:$s,type:ANIME){bannerImage coverImage{extraLarge}}}",
                "variables": {"s": title},
            },
            headers={"Content-Type": "application/json"}, timeout=5,
        )
        if r.status_code == 200:
            data = r.json().get("data", {}).get("Media", {})
            return data.get("bannerImage") or (data.get("coverImage") or {}).get("extraLarge")
    except Exception as exc:
        logger.debug(f"anilist: {exc}")
    return None

_ANIME_QUERIES = [
    "anime landscape", "anime city night", "anime scenery",
    "demon slayer scenery", "ghibli wallpaper", "anime sunset",
]

def _fetch_safone_wall() -> Optional[str]:
    try:
        r = requests.get(
            "https://api.safone.me/wall",
            params={"query": random.choice(_ANIME_QUERIES)}, timeout=5,
        )
        if r.status_code == 200:
            results = r.json().get("results", [])
            if results:
                chosen = random.choice(results[:5])
                return chosen.get("imageUrl") or chosen.get("url")
    except Exception as exc:
        logger.debug(f"safone: {exc}")
    return None

def _fetch_tmdb_backdrop() -> Optional[str]:
    if not TMDB_API_KEY:
        return None
    ids = ["14160", "8392", "149870", "378064", "431580", "15120", "527774"]
    try:
        r = requests.get(
            f"https://api.themoviedb.org/3/movie/{random.choice(ids)}/images",
            params={"api_key": TMDB_API_KEY}, timeout=5,
        )
        if r.status_code == 200:
            backdrops = r.json().get("backdrops", [])
            if backdrops:
                best = max(backdrops, key=lambda x: x.get("width", 0))
                path = best.get("file_path", "")
                if path:
                    return f"https://image.tmdb.org/t/p/original{path}"
    except Exception as exc:
        logger.debug(f"tmdb: {exc}")
    return None

def _fetch_pic_re() -> Optional[str]:
    try:
        r = requests.get("https://pic.re/image", params={"type": "sfw"},
                         timeout=5, allow_redirects=False)
        if r.status_code in (200, 302):
            url = r.headers.get("Location") or r.url
            if url and url.startswith("http") and "pic.re" not in url:
                return url
    except Exception as exc:
        logger.debug(f"pic.re: {exc}")
    return None


# ── URL-first fetch ───────────────────────────────────────────────────────────
def _fetch_from_urls() -> Optional[str]:
    """Pick from custom URL list (DB or env). Instant."""
    urls = _get_custom_urls()
    if urls:
        return random.choice(urls)
    return None

# ── API fetch (parallel, capped at 5s) ───────────────────────────────────────
def _fetch_from_apis(panel: str) -> Optional[str]:
    """Run multiple API fetchers in parallel, return first success."""
    fetchers = [
        ("waifu.im",  lambda: _fetch_waifu_im(panel)),
        ("anilist",   _fetch_anilist_banner),
        ("nekos",     lambda: _fetch_nekos_best(panel)),
        ("safone",    _fetch_safone_wall),
        ("pic.re",    _fetch_pic_re),
        ("tmdb",      _fetch_tmdb_backdrop),
    ]
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            futs = {ex.submit(fn): name for name, fn in fetchers}
            for fut in concurrent.futures.as_completed(futs, timeout=5):
                try:
                    url = fut.result()
                    if url and url.startswith("http"):
                        logger.debug(f"Panel image from {futs[fut]}: {url[:60]}")
                        return url
                except Exception:
                    pass
    except concurrent.futures.TimeoutError:
        logger.debug("API fetch timed out")
    except Exception as exc:
        logger.debug(f"API fetch error: {exc}")
    return None


# ── Main fetch function ───────────────────────────────────────────────────────
def get_panel_image(panel: str = "default", force_refresh: bool = False) -> Optional[str]:
    """
    Fetch panel image respecting primary source toggle.

    primary = 'url':
      1. Custom URLs / PANEL_PICS env  → instant
      2. APIs if URLs empty            → parallel with timeout
      3. Static fallback

    primary = 'api':
      1. APIs first                    → parallel with timeout
      2. Custom URLs / PANEL_PICS env  → fallback
      3. Static fallback
    """
    if not force_refresh and _is_cached(panel):
        return _img_cache[panel]

    primary = _get_primary_source()

    if primary == "url":
        url = _fetch_from_urls()
        if not url:
            url = _fetch_from_apis(panel)
    else:  # 'api'
        url = _fetch_from_apis(panel)
        if not url:
            url = _fetch_from_urls()

    if not url:
        url = random.choice(_STATIC_FALLBACKS)
        logger.debug(f"Panel [{panel}] static fallback")

    _set_cache(panel, url)
    return url

def get_panel_image_sync(panel: str = "default") -> Optional[str]:
    return get_panel_image(panel)

async def get_panel_image_async(panel: str = "default") -> Optional[str]:
    """
    Async wrapper.
    Returns cached value INSTANTLY. Refreshes stale cache in background.
    First call always instant (pre-warmed with static fallbacks).
    """
    cached = _img_cache.get(panel)
    if cached:
        if not _is_cached(panel):
            # Background refresh — never blocks caller
            loop = asyncio.get_event_loop()
            loop.run_in_executor(None, get_panel_image, panel, True)
        return cached
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, get_panel_image, panel)

def clear_image_cache(panel: str = None) -> int:
    count = 0
    if panel:
        if panel in _img_cache:
            del _img_cache[panel]
            del _cache_ts[panel]
            count = 1
    else:
        count = len(_img_cache)
        _img_cache.clear()
        _cache_ts.clear()
    return count

def get_cache_status() -> Dict[str, Any]:
    now = _now()
    return {
        p: {"url": u[:60] + "...", "age_sec": int(now - _cache_ts.get(p, now))}
        for p, u in _img_cache.items()
    }
