# ====================================================================
# PLACE AT: /app/panel_image.py
# ACTION: Replace existing file
# ====================================================================
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BeatAniVerse Bot — Panel Image System
=======================================
Fetches 4K SFW anime wallpapers from multiple APIs.
Used as background images for all admin panels.

APIs (in priority order, with fallback):
  1. Waifu.im         — https://api.waifu.im/search  (SFW, high quality)
  2. Nekos.best       — https://nekos.best/api/v2/    (SFW, curated)
  3. Pic.re           — https://pic.re/image           (SFW anime)
  4. AnimePics.io     — CORS-safe endpoint             (HD anime)
  5. AniAPI (TMDB backdrop fallback)                   (anime title stills)
  6. Static fallback URLs (always works)

Image format: landscape / YouTube-thumbnail ratio (1280×720 approx.)
All images: SFW, anime style, modern aesthetic.

Credits: BeatAnime | @BeatAnime | @Beat_Anime_Discussion
"""

import os
import time
import random
import logging
import hashlib
from typing import Optional, List, Dict, Any

import requests

logger = logging.getLogger(__name__)

# ── PANEL_PICS env: comma-separated URLs used as panel backgrounds ─────────────
# Example: PANEL_PICS=https://i.imgur.com/abc.jpg,https://i.imgur.com/xyz.jpg
_PANEL_PICS_ENV: list = [
    u.strip() for u in os.getenv("PANEL_PICS", "").split(",")
    if u.strip().startswith("http")
]

# ── API keys from env ──────────────────────────────────────────────────────────
WALL_API_KEY: str = os.getenv("WALL_API_KEY", "")
TMDB_API_KEY: str = os.getenv("TMDB_API_KEY", "")

# ── Image cache (url → ts) — avoid re-fetching same url repeatedly ───────────
_img_cache: Dict[str, str] = {}   # panel_type → last_url
_cache_ts:  Dict[str, float] = {}
_CACHE_TTL  = 1800  # 30 minutes per panel type

# ── Static fallback images (guaranteed to work) ───────────────────────────────
_STATIC_FALLBACKS = [
    "https://images.alphacoders.com/133/thumb-1920-1330574.jpg",
    "https://images.alphacoders.com/133/thumb-1920-1330590.jpg",
    "https://images.alphacoders.com/130/thumb-1920-1301234.jpg",
    "https://images.alphacoders.com/131/thumb-1920-1315677.jpg",
    "https://i.imgur.com/WdTdHhv.jpeg",
    "https://i.imgur.com/YeQjKJh.jpeg",
    "https://i.imgur.com/V8gkYXC.jpeg",
    "https://i.imgur.com/aLqjMV7.jpeg",
    "https://cdn.myanimelist.net/images/anime/1988/119092.jpg",
    "https://cdn.myanimelist.net/images/anime/1223/121781.jpg",
    "https://cdn.myanimelist.net/images/anime/1170/124216.jpg",
]

# ── Tags per panel type for varied images ────────────────────────────────────
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

# ── Pre-warm cache with static images — first panel load is INSTANT ───────────
# Background APIs will refresh these after TTL expires (30 min)
import random as _rand
for _panel_key in list(_PANEL_TAGS.keys()) + ["default", "admin", "channels", "users", "broadcast", "upload", "flags", "style", "poster", "clones"]:
    if _panel_key not in _img_cache:
        _img_cache[_panel_key] = _rand.choice(_STATIC_FALLBACKS)
        _cache_ts[_panel_key] = 0  # Expired so first real call refreshes from API

# ── Waifu categories that are always SFW ─────────────────────────────────────
_WAIFU_IM_TAGS = [
    "maid", "waifu", "elf", "oppai", "school",
    "uniform", "raiden-shogun", "kamisato-ayaka",
    "marin-kitagawa", "holo",
]


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
    _cache_ts[panel] = _now()


# ── API 1: waifu.im ────────────────────────────────────────────────────────────
def _fetch_waifu_im(panel: str) -> Optional[str]:
    tags = _PANEL_TAGS.get(panel, _PANEL_TAGS["default"])
    tag  = random.choice(tags)
    try:
        r = requests.get(
            "https://api.waifu.im/search",
            params={
                "included_tags": tag,
                "is_nsfw": "false",
                "many": "true",
                "limit": "10",
            },
            timeout=5,
            headers={"Accept": "application/json"},
        )
        if r.status_code == 200:
            data = r.json()
            images = data.get("images", [])
            if images:
                # Pick one with width >= 1280 if possible
                hd = [i for i in images if i.get("width", 0) >= 1280]
                chosen = random.choice(hd if hd else images)
                return chosen.get("url")
    except Exception as exc:
        logger.debug(f"waifu.im error: {exc}")
    return None


# ── API 2: nekos.best ─────────────────────────────────────────────────────────
_NEKOS_ENDPOINTS = ["waifu", "neko", "kitsune", "shinobu", "megumin",
                    "zero_two", "aqua", "rem", "mai"]

def _fetch_nekos_best(panel: str) -> Optional[str]:
    endpoint = random.choice(_NEKOS_ENDPOINTS)
    try:
        r = requests.get(
            f"https://nekos.best/api/v2/{endpoint}",
            params={"amount": "5"},
            timeout=5,
        )
        if r.status_code == 200:
            data = r.json()
            results = data.get("results", [])
            if results:
                chosen = random.choice(results)
                url = chosen.get("url", "")
                # nekos.best returns .png/.jpg SFW images
                if url.endswith((".jpg", ".jpeg", ".png", ".webp")):
                    return url
    except Exception as exc:
        logger.debug(f"nekos.best error: {exc}")
    return None


# ── API 3: pic.re ─────────────────────────────────────────────────────────────
def _fetch_pic_re() -> Optional[str]:
    try:
        r = requests.get(
            "https://pic.re/image",
            params={"type": "sfw"},
            timeout=5,
            allow_redirects=False,
        )
        # pic.re returns 302 redirect to image URL
        if r.status_code in (200, 302):
            url = r.headers.get("Location") or r.url
            if url and url.startswith("http") and "pic.re" not in url:
                return url
            # If 200, try parsing JSON
            if r.status_code == 200:
                try:
                    d = r.json()
                    return d.get("url") or d.get("image_url")
                except Exception:
                    pass
    except Exception as exc:
        logger.debug(f"pic.re error: {exc}")
    return None


# ── API 4: Safone API (anime wallpaper) ───────────────────────────────────────
_ANIME_QUERIES = [
    "anime landscape", "anime city night", "anime scenery",
    "anime 4k wallpaper", "anime fantasy", "anime sky",
    "anime village", "anime ocean", "anime sakura",
    "attack on titan scenery", "demon slayer scenery",
    "ghibli wallpaper", "anime rain", "anime sunset",
]

def _fetch_safone_wall() -> Optional[str]:
    query = random.choice(_ANIME_QUERIES)
    try:
        r = requests.get(
            "https://api.safone.me/wall",
            params={"query": query, "type": "sfw"},
            timeout=5,
        )
        if r.status_code == 200:
            data = r.json()
            results = data.get("results", [])
            if results:
                chosen = random.choice(results[:5])
                return chosen.get("imageUrl") or chosen.get("url")
    except Exception as exc:
        logger.debug(f"safone wall error: {exc}")
    return None


# ── API 5: AniList cover images for anime (high quality) ─────────────────────
_ANILIST_POPULAR = [
    "Demon Slayer", "Attack on Titan", "Jujutsu Kaisen",
    "Chainsaw Man", "One Piece", "Naruto Shippuden",
    "Sword Art Online", "Re:Zero", "That Time I Got Reincarnated",
    "My Hero Academia", "Violet Evergarden", "Your Lie in April",
    "A Silent Voice", "Weathering with You", "Spirited Away",
    "Princess Mononoke", "Made in Abyss", "Frieren", "Blue Lock",
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
            headers={"Content-Type": "application/json"},
            timeout=5,
        )
        if r.status_code == 200:
            data = r.json().get("data", {}).get("Media", {})
            url = data.get("bannerImage") or \
                  (data.get("coverImage") or {}).get("extraLarge")
            if url:
                return url
    except Exception as exc:
        logger.debug(f"anilist banner error: {exc}")
    return None


# ── API 6: TMDB backdrop (movie/show backdrops — cinematic) ──────────────────
_TMDB_ANIME_IDS = [
    # Popular anime movie IDs
    "14160",  # Spirited Away
    "8392",   # Princess Mononoke
    "149870", # Your Name
    "378064", # A Silent Voice
    "431580", # Akira
    "15120",  # Howl's Moving Castle
    "527774", # Violet Evergarden movie
]

def _fetch_tmdb_backdrop() -> Optional[str]:
    if not TMDB_API_KEY:
        return None
    movie_id = random.choice(_TMDB_ANIME_IDS)
    try:
        r = requests.get(
            f"https://api.themoviedb.org/3/movie/{movie_id}/images",
            params={"api_key": TMDB_API_KEY},
            timeout=5,
        )
        if r.status_code == 200:
            data = r.json()
            backdrops = data.get("backdrops", [])
            if backdrops:
                # Pick widest backdrop
                best = max(backdrops, key=lambda x: x.get("width", 0))
                path = best.get("file_path", "")
                if path:
                    return f"https://image.tmdb.org/t/p/original{path}"
    except Exception as exc:
        logger.debug(f"tmdb backdrop error: {exc}")
    return None


# ── Main fetcher with full fallback chain ─────────────────────────────────────

def get_panel_image(panel: str = "default", force_refresh: bool = False) -> Optional[str]:
    """
    Get a SFW anime image URL for a panel background.
    Priority:
      1. PANEL_PICS env variable (comma-separated URLs) — random pick, instant
      2. Parallel API fetch (waifu.im + anilist)
      3. Static fallback (always works)
    Results cached 30 minutes per panel type.
    """
    # PANEL_PICS env takes top priority — instant, no API needed
    if _PANEL_PICS_ENV:
        url = random.choice(_PANEL_PICS_ENV)
        _set_cache(panel, url)
        return url

    if not force_refresh and _is_cached(panel):
        return _img_cache[panel]

    import concurrent.futures

    # Run waifu.im + anilist in parallel — take the first one that succeeds
    fetchers = [
        ("waifu.im",  lambda: _fetch_waifu_im(panel)),
        ("anilist",   _fetch_anilist_banner),
        ("nekos",     _fetch_nekos_best if __import__('random').random() > 0.4 else lambda: None),
    ]

    result_url: Optional[str] = None

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
            futs = {ex.submit(fn): name for name, fn in fetchers}
            for fut in concurrent.futures.as_completed(futs, timeout=5):
                try:
                    url = fut.result()
                    if url and url.startswith("http"):
                        result_url = url
                        logger.debug(f"Panel image [{panel}] from {futs[fut]}: {url[:60]}")
                        break
                except Exception:
                    pass
    except concurrent.futures.TimeoutError:
        logger.debug(f"Panel image [{panel}] timed out — using static fallback")
    except Exception as exc:
        logger.debug(f"Panel image error: {exc}")

    if not result_url:
        result_url = random.choice(_STATIC_FALLBACKS)
        logger.debug(f"Panel image [{panel}] static fallback")

    _set_cache(panel, result_url)
    return result_url


def get_panel_image_sync(panel: str = "default") -> Optional[str]:
    """Synchronous wrapper — same as get_panel_image."""
    return get_panel_image(panel)


async def get_panel_image_async(panel: str = "default") -> Optional[str]:
    """
    Async wrapper — INSTANT return using cache, refreshes in background.
    First call returns static fallback immediately (pre-warmed).
    Subsequent calls get fresh API images after cache TTL expires.
    """
    import asyncio

    # Return cached value immediately (even if expired) for instant panel load
    cached = _img_cache.get(panel)
    if cached:
        # If cache is stale, refresh in background without blocking
        if not _is_cached(panel):
            loop = asyncio.get_event_loop()
            loop.run_in_executor(None, get_panel_image, panel)
        return cached

    # No cache at all — fetch synchronously (only happens if pre-warm missed)
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, get_panel_image, panel)


def clear_image_cache(panel: str = None) -> int:
    """Clear image cache. If panel is None, clears all."""
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
    """Return info about cached images."""
    now = _now()
    status = {}
    for panel, url in _img_cache.items():
        age = int(now - _cache_ts.get(panel, now))
        status[panel] = {"url": url[:50] + "...", "age_sec": age}
    return status
