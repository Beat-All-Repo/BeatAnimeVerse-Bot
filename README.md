# 🎌 BeatAniVerse Bot — Complete Edition

> **All-in-one Telegram Bot**: Link Provider + Group Management + Poster Generation
> Credits: **BeatAnime** | [@BeatAnime](https://t.me/BeatAnime) | [@Beat_Anime_Discussion](https://t.me/Beat_Anime_Discussion)

---

## 📦 File Structure

```
BeatAniVerse-v2/
├── bot.py                    ← Main bot (7986 lines, original logic + patches)
├── database_dual.py          ← Dual DB layer (NeonDB + MongoDB, all functions)
├── database_safe.py          ← Original NeonDB-only layer (kept for reference)
├── poster_engine.py          ← 6-layer poster generation (12 templates)
├── beataniversebot_compat.py ← Compat shim for BeatVerse modules
├── health_check.py           ← HTTP health server for Render keepalive
├── requirements.txt
├── Dockerfile
├── render.yml
├── .env.example
├── fonts/                    ← Poster fonts (Poppins, Bebas Neue, etc.)
├── iconspng/                 ← Poster icons (Netflix, Crunchyroll, AniList logos)
└── modules/                  ← 77 BeatVerse group management modules
    ├── admin.py              ← Group admin: title, description, stickers
    ├── afk.py                ← AFK system
    ├── anime.py              ← Anime info (Jikan + AniList)
    ├── animequotes.py        ← Random anime quotes
    ├── animerequest.py       ← Anime request system (anti-spam, cooldown)
    ├── antiflood.py          ← Anti-flood with configurable actions
    ├── approve.py            ← User approval system
    ├── bans.py               ← Ban / unban / kick / temp-ban
    ├── blacklist.py          ← Message blacklist
    ├── blacklist_stickers.py ← Sticker blacklist
    ├── blacklistusers.py     ← User blacklist
    ├── chatbot.py            ← AI chatbot integration (MongoDB)
    ├── cleaner.py            ← Auto-delete service messages
    ├── connection.py         ← Manage multiple groups from PM
    ├── couples.py            ← Couple of the day (MongoDB)
    ├── currency_converter.py ← Live currency conversion
    ├── cust_filters.py       ← Custom keyword filters
    ├── dbcleanup.py          ← DB maintenance tools
    ├── disable.py            ← Disable/enable commands per chat
    ├── disasters.py          ← Global disaster/sudo user management
    ├── eval.py               ← Python eval (owner only)
    ├── fonts.py              ← Font stylizer
    ├── fsub.py               ← Force subscription (SQL-backed)
    ├── fun.py                ← Fun commands (flip, roll, etc.)
    ├── global_bans.py        ← Global ban system
    ├── google.py             ← Google search integration
    ├── imdb.py               ← IMDB movie/show lookup
    ├── inline.py             ← Inline query mode
    ├── locks.py              ← Chat locks (media, stickers, etc.)
    ├── log_channel.py        ← Event logging to channel
    ├── logo.py               ← Logo generator
    ├── memify.py             ← Meme generator
    ├── misc.py               ← Miscellaneous commands
    ├── muting.py             ← Mute / unmute / temp-mute
    ├── nightmode.py          ← Scheduled chat lock (night mode)
    ├── notes.py              ← Saved notes system
    ├── purge.py              ← Message purging
    ├── reactions.py          ← Reaction messages
    ├── reporting.py          ← User reporting system
    ├── rules.py              ← Group rules
    ├── sed.py                ← Text find & replace
    ├── shell.py              ← Shell execution (owner only)
    ├── stickers.py           ← Sticker pack management
    ├── sudoers.py            ← Sudo user management
    ├── tagall.py             ← Tag all members
    ├── telegraph.py          ← Telegraph post creator
    ├── translator.py         ← Text translation
    ├── truth_and_dare.py     ← Truth or dare game
    ├── ud.py                 ← Urban Dictionary lookup
    ├── userinfo.py           ← User info command
    ├── users.py              ← User tracking
    ├── wallpaper.py          ← Wallpaper search
    ├── warns.py              ← Warning system
    ├── welcome.py            ← Custom welcome/goodbye messages
    ├── wiki.py               ← Wikipedia search
    ├── writetool.py          ← Text styling tools
    ├── zip.py                ← File zip/unzip
    └── sql/                  ← 24 SQLAlchemy model files
```

---

## ✅ Complete Feature List

### 🔗 Link Provider (from Beat Anime Link Provider Bot)
| Feature | Command |
|---------|---------|
| Add force-sub channel (by ID **or** @username) | `/addchannel @username_or_id [Title] [jbr]` |
| Remove force-sub channel | `/removechannel @username_or_id` |
| List all force-sub channels | `/channel` |
| Generate expiring channel links (5 min) | Admin panel → Generate Link |
| Bot deep links **never expire** | `/start link_XXX` |
| Clone bot management | `/addclone TOKEN`, `/clones` |
| Full broadcast system | Admin panel → Broadcast |
| Auto-forward with filters + replacements | `/autoforward` |
| Upload manager (multi-quality captions) | `/upload` |
| Manga chapter tracker (MangaDex) | `/autoupdate` |
| Scheduled broadcasts | Admin panel → Schedule |
| User ban/unban/export | `/banuser`, `/unbanuser`, `/exportusers` |
| Group connections | `/connect`, `/disconnect` |
| Feature flags | Admin panel → Feature Flags |
| Category settings (watermark, logo, template, buttons) | `/settings` |

### 🎨 Poster Generation (from Postermaking Bot)
| Template | Command | Type |
|----------|---------|------|
| AniList Anime | `/ani <title>` | Anime |
| AniList Manga | `/anim <title>` | Manga |
| Crunchyroll | `/crun <title>` | Anime |
| Netflix Anime | `/net <title>` | Anime |
| Netflix Manga | `/netm <title>` | Manga |
| Light Anime | `/light <title>` | Anime |
| Light Manga | `/lightm <title>` | Manga |
| Dark Anime | `/dark <title>` | Anime |
| Dark Manga | `/darkm <title>` | Manga |
| Netflix × Crunchyroll | `/netcr <title>` | Anime |
| Modern Anime | `/mod <title>` | Anime |
| Modern Manga | `/modm <title>` | Manga |

> **All poster commands are admin-only.** Users see only `/my_plan` and `/plans`.

**Poster layers (6-layer compositing):**
1. Gradient background
2. Blurred cover art (full bleed background)
3. Cover art overlay (rounded corners + drop shadow)
4. Score badge + accent bar + template logo
5. Title, native title, status pill, info rows, description
6. Watermark (position from DB settings) + footer bar

**Premium tiers:**
| Tier | Daily Limit | Command |
|------|-------------|---------|
| Free | 20 posters | — |
| 🥉 Bronze | 30 posters | `/add_premium ID bronze 7d` |
| 🥈 Silver | 40 posters | `/add_premium ID silver 1m` |
| 🥇 Gold | 50 posters | `/add_premium ID gold permanent` |

### 🤖 Group Management (from BeatVerse Bot)
All 77 modules fully included:
- **Admin**: promote, demote, pin, set title/description/stickers, invite links
- **Anti-flood**: configurable kick/ban/mute/warn on flood
- **Bans**: ban, unban, kick, temp-ban with time formats
- **Blacklists**: text blacklist, sticker blacklist, user blacklist
- **Filters**: custom keyword → response filters (text, photo, sticker, document)
- **Locks**: lock/unlock media types, stickers, polls, bots
- **Notes**: `/save`, `/get`, `#notename` shortcut
- **Rules**: `/setrules`, `/rules`
- **Warns**: `/warn`, `/warns`, `/resetwarns`, configurable warn action
- **Welcome**: custom welcome/goodbye with HTML buttons and user mention
- **AFK**: `/afk` with reason, auto-unmention
- **Muting**: `/mute`, `/unmute`, `/tmute` (timed mute)
- **Purge**: `/purge`, `/del`
- **Connection**: manage multiple groups from PM
- **Night mode**: scheduled lock/unlock
- **Anime request**: `/request <anime>` with AniList validation + spam protection
- **Couples**: `/couple` (picks 2 users daily, MongoDB-backed)
- **Fun**: various fun commands
- **Inline mode**: search anime/manga inline
- **IMDB**: movie/show lookup
- **Wikipedia/Google**: search integration
- **Currency converter**: live rates
- **Translator**: multi-language
- **Sudoers/Disasters/Global bans**: tiered privilege system

---

## 🚀 Deployment (Render Free Tier)

### Step 1 — Set Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BOT_TOKEN` | ✅ | Bot token from @BotFather |
| `ADMIN_ID` | ✅ | Your Telegram numeric user ID |
| `OWNER_ID` | ✅ | Same as ADMIN_ID |
| `DATABASE_URL` | ✅* | NeonDB PostgreSQL URL |
| `MONGO_DB_URI` | ✅* | MongoDB Atlas URI |
| `BOT_NAME` | ✅ | e.g. `BeatAniVerse Bot` |
| `PUBLIC_ANIME_CHANNEL_URL` | ✅ | e.g. `https://t.me/BeatAnime` |
| `HELP_TEXT_CUSTOM` | ⭕ | What users see on /help (HTML supported) |
| `HELP_CHANNEL_1_URL` | ⭕ | First channel button URL |
| `HELP_CHANNEL_1_NAME` | ⭕ | First channel button label |
| `HELP_CHANNEL_2_URL` | ⭕ | Second channel button URL |
| `HELP_CHANNEL_3_URL` | ⭕ | Third channel button URL |
| `TMDB_API_KEY` | ⭕ | For /movie and /tvshow |
| `LINK_EXPIRY_MINUTES` | ⭕ | Default: 5 |
| `WELCOME_SOURCE_CHANNEL` | ⭕ | Channel ID to copy welcome from |
| `WELCOME_SOURCE_MESSAGE_ID` | ⭕ | Message ID to copy |

> **\*** Set at least one of DATABASE_URL or MONGO_DB_URI. Both recommended.

### Step 2 — Keep Alive (Prevent Render sleep)
1. Go to [uptimerobot.com](https://uptimerobot.com)
2. Add monitor: `https://your-app.onrender.com/health`
3. Interval: every 5 minutes

---

## 🔒 Access Control

| Command Type | Who Can Use |
|---|---|
| `/start`, `/ping`, `/alive`, `/id`, `/info` | Everyone |
| `/help` | Everyone — but users only see custom ENV info + channel buttons |
| `/my_plan`, `/plans` | Everyone |
| `/request`, `/myrequests` | Everyone (with cooldown + spam protection) |
| `/couple`, fun commands, `/afk`, `/rules`, etc. | Everyone in groups |
| `/anime`, `/manga`, `/movie`, `/tvshow` | **Admin only** (silent for users) |
| All 12 poster commands `/ani`, `/crun`, etc. | **Admin only** (silent for users) |
| All management commands | **Admin only** |

---

## 🗄️ Databases

### NeonDB (PostgreSQL)
Used for: all link provider data, force-sub channels, generated links, clone bots, broadcast history, auto-forward, upload progress, category settings, connected groups, scheduled broadcasts, all SQL-backed group management modules (notes, warns, bans, blacklists, filters, locks, welcome, etc.)

### MongoDB
Used for: poster premium plans, daily usage tracking, couples, chatbot data, user mirror (for speed)

---

## 📢 Credits

- 📣 **Channel**: [@BeatAnime](https://t.me/BeatAnime)  
- 💬 **Discussion**: [@Beat_Anime_Discussion](https://t.me/Beat_Anime_Discussion)
- 🎬 **Hindi Dubbed**: [@Beat_Hindi_Dubbed](https://t.me/Beat_Hindi_Dubbed)
- 👤 **Admin**: [@Beat_Anime_Ocean](https://t.me/Beat_Anime_Ocean)

*© 2025–2026 BeatAnime. All rights reserved.*
