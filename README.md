# Weather Comparison Bot — Bologna (v1.1.0)

Fetches hourly weather data from **6 sources**, renders a comparison table as a PNG image, and sends it to a **Telegram chat**.

---

## Table of Contents

1. [Overview](#overview)
2. [Project Structure](#project-structure)
3. [How It Works](#how-it-works)
4. [Setup](#setup)
5. [Configuration](#configuration)
6. [Usage](#usage)
7. [Output](#output)
8. [Adding a New Source](#adding-a-new-source)
9. [Architecture Reference](#architecture-reference)
10. [Troubleshooting](#troubleshooting)

---

## Overview

The bot compares hourly weather forecasts for **Bologna, Italy** (44.4949°N, 11.3426°E) from six different providers:

| # | Source | Type | Key data |
|---|--------|------|----------|
| 1 | **ilmeteo.it** | HTML scraping | 3 numerical models per hour (COMPOSITE, ECMWF, UKMO) |
| 2 | **OpenMeteo — ECMWF IFS** | Free API | Temperature, precipitation, wind, humidity |
| 3 | **OpenMeteo — GFS** | Free API | Temperature, precipitation, wind, humidity |
| 4 | **Visual Crossing** | Paid API (1000 req/day free) | Full hourly data incl. precipitation probability |
| 5 | **3bmeteo.com** | HTML scraping | Temperature, rain, wind, humidity |
| 6 | **meteo.it** | HTML scraping + embedded JSON | Temperature, precipitation probability, wind |

Each run produces:
- A **PNG image** per requested day (today / tomorrow / day after tomorrow)
- A **JSON snapshot** of all raw data (for replay with `--test-json`)
- An optional **Telegram message** with the PNG attached

---

## Project Structure

```
weather-bot-v4/
├── main.py                      # Entry point — orchestration, CLI, JSON export
├── config.py                    # Constants, env vars, logging, HTTP session, date utils
├── icons.py                     # Weather icon maps, sprite CSS, wind direction tables
│
├── sources/
│   ├── __init__.py              # Re-exports all fetch_* functions
│   ├── base.py                  # HourlyData, IlMeteoHour, shared helpers
│   ├── ilmeteo.py               # ilmeteo.it — HTML parsing, multi-model
│   ├── openmeteo.py             # Open-Meteo API — ECMWF IFS + GFS
│   ├── visual_crossing.py       # Visual Crossing API
│   ├── threebmeteo.py           # 3bmeteo.com — HTML scraping
│   └── meteoit.py               # meteo.it — HTML scraping + embedded JSON
│
├── render/
│   ├── __init__.py
│   ├── html_builder.py          # build_html() — assembles the comparison table as HTML
│   └── screenshot.py            # html_to_png() — WeasyPrint render + Pillow crop
│
├── notify/
│   ├── __init__.py
│   └── telegram.py              # send() — uploads PNG to Telegram via Bot API
│
├── utils/
│   ├── .env                     # Your secrets (not committed to git)
│   ├── env.example              # Template for .env
│   └── s-cartoon2016b-34.png    # Weather icon sprite sheet (required)
│
├── output_weather/              # Auto-created — PNG images + JSON snapshots
└── log/
    └── weather_comparison.log   # Rotating log (also printed to stdout)
```

---

## How It Works

```
main.py
  │
  ├─ resolve_days()          Determines which days to process (CLI args or auto)
  │
  ├─ for each day:
  │   ├─ fetch_ilmeteo()     → list[IlMeteoHour]   (multi-model per hour)
  │   ├─ fetch_ecmwf()       → list[HourlyData]
  │   ├─ fetch_gfs()         → list[HourlyData]
  │   ├─ fetch_visual_crossing() → list[HourlyData]
  │   ├─ fetch_3bmeteo()     → list[HourlyData]    (scraping, skipped with --no-scraping)
  │   ├─ fetch_meteoit()     → list[HourlyData]    (scraping, skipped with --no-scraping)
  │   │
  │   ├─ build_html()        Assembles all data into an HTML comparison table
  │   ├─ html_to_png()       Renders HTML → PNG via WeasyPrint, then crops whitespace
  │   └─ telegram_send()     Uploads PNG to Telegram (skipped with --no-telegram)
  │
  └─ Saves all raw data to output_weather/YYYY.MM.DD.HH.MM_meteo_data.json
```

### Data model

All sources (except ilmeteo.it) normalize their output into `HourlyData`:

```python
@dataclass
class HourlyData:
    hour:         int           # 0–23
    icon_class:   str           # CSS sprite class, e.g. "ss1", "ss10"
    desc:         str           # Human-readable description, e.g. "Rain"
    temp:         str           # "22.5" or "—"
    prec_prob:    int | None    # 0–100 or None if not provided
    rain_mm:      str           # "1.2" or ""
    vento_deg:    int | None    # Wind direction in degrees
    vento_kmh:    str           # "15" or "—"
    humidity:     int | None    # 0–100 or None
    is_day:       int           # 1 = day, 0 = night
    rain_only_mm: str           # Rain component only (OpenMeteo)
    clouds:       int | None    # Cloud cover % (OpenMeteo)
    prec_type:    int | None    # Precipitation type code (OpenMeteo)
```

ilmeteo.it uses `IlMeteoHour` (contains a list of `IlMeteoModel`, one per numerical model).

---

## Setup

### 1. Install Python dependencies

```bash
pip install "weasyprint<53" requests pillow python-dotenv pytz
```

> **WeasyPrint version constraint**: versions ≥ 53 removed the `write_png()` method. Pin to `<53`.

### 2. Install GTK3 (Windows only)

WeasyPrint requires GTK3 on Windows to render HTML to PNG.

Download and install from:
https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases

The installer automatically adds GTK3 to your PATH. If you install it to a non-default location, update the path in `config.py`:

```python
gtk_bin = r"C:\Program Files\GTK3-Runtime Win64\bin"
```

On **Linux/macOS** GTK3 is usually available via the system package manager:

```bash
# Ubuntu/Debian
sudo apt install libpango-1.0-0 libpangocairo-1.0-0 libcairo2

# macOS (Homebrew)
brew install pango cairo
```

### 3. Place the icon sprite

Copy `s-cartoon2016b-34.png` into the `utils/` folder. This sprite sheet is used to render weather icons in the output image.

### 4. Create your `.env` file

```bash
cp utils/env.example utils/.env
```

Then edit `utils/.env` with your credentials (see [Configuration](#configuration)).

---

## Configuration

All sensitive values go in `utils/.env`. The file is loaded automatically at startup by `config.py`.

```env
# Required for Telegram delivery
TELEGRAM_TOKEN=123456:ABC-your-bot-token
TELEGRAM_CHAT_ID=-1001234567890

# Optional — Visual Crossing API (free tier: 1000 req/day)
# Without this key, Visual Crossing is silently skipped
VISUALCROSSING_API_KEY=your_key_here

# SSL verification (set False only if behind a corporate proxy)
VERIFY_SSL=True
```

### Getting a Telegram bot token

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` and follow the prompts
3. Copy the token (format: `123456789:ABC...`) into `TELEGRAM_TOKEN`
4. To get your chat ID, send a message to your bot then visit:
   `https://api.telegram.org/bot<TOKEN>/getUpdates`

### Getting a Visual Crossing API key

Register at https://www.visualcrossing.com/weather-api — the free tier provides 1000 API calls per day, which is sufficient for daily use.

---

## Usage

```bash
# Auto mode: if current hour < 20 → fetch today + tomorrow
#            if current hour ≥ 20 → fetch tomorrow only
python main.py

# Specify days explicitly
python main.py today
python main.py tomorrow
python main.py today tomorrow day_after_tomorrow

# Skip HTML scrapers (3bmeteo + meteo.it) — faster, API-only
python main.py --no-scraping

# Do not send the result to Telegram
python main.py --no-telegram

# Keep the intermediate HTML file alongside the PNG
python main.py --keep-html

# Replay from the most recent saved JSON (no network requests)
python main.py --test-json

# Write outputs to a custom folder
python main.py --output-dir /path/to/output

# Combine flags
python main.py today tomorrow --no-scraping --keep-html --no-telegram
```

### Scheduling (Linux cron)

To run the bot every morning at 07:00:

```bash
crontab -e
# Add:
0 7 * * * cd /path/to/weather-bot-v4 && python main.py >> /path/to/cron.log 2>&1
```

### Scheduling (Windows Task Scheduler)

1. Open Task Scheduler → Create Basic Task
2. Trigger: Daily at 07:00
3. Action: Start a program → `python.exe`
4. Arguments: `main.py`
5. Start in: `C:\path\to\weather-bot-v4`

---

## Output

### PNG image

Each day produces a file like `output_weather/meteo_today.png` — a wide table with one row per hour, showing all sources side by side.

Columns:
- **Hour** (left + right)
- **ilmeteo.it** — 3 sub-columns (COMPOSITE, ECMWF, UKMO), each showing icon + temperature + rain + wind
- **ECMWF IFS** (OpenMeteo) — icon, precipitation probability, temperature, rain, wind, humidity
- **GFS** (OpenMeteo) — same format
- **Visual Crossing** — same format
- **3bMeteo** — same format (scraped)
- **meteo.it** — same format (scraped)
- **🌧 Rain?** — consensus across all sources: `Yes (N%)` / `Maybe (N%)` / `No (N%)`
- **🌡 Avg Temp** — color-coded average across all sources

### JSON snapshot

Every run saves a file like `output_weather/2026.04.03.15.09_meteo_data.json`.
Structure:

```json
{
  "metadata": { "generated_at": "...", "location": "Bologna" },
  "days": {
    "today": {
      "ilmeteo":         { "models": ["COMPOSITE","ECMWF","UKMO"], "data": [...] },
      "openmeteo_ecmwf": [ { "hour": 8, "temp": "14.2", ... }, ... ],
      "openmeteo_gfs":   [...],
      "visual_crossing": [...],
      "3bmeteo":         [...],
      "meteo_it":        [...]
    },
    "tomorrow": { ... }
  }
}
```

Use `--test-json` to re-render a PNG from the latest snapshot without making any network requests.

---

## Adding a New Source

Follow these five steps to integrate a new weather provider.

### Step 1 — Create `sources/your_source.py`

The module must expose a `fetch(day: str) -> list[HourlyData]` function.
`day` will be one of `"today"`, `"tomorrow"`, `"day_after_tomorrow"`.

```python
"""
sources/your_source.py
======================
Source YourProvider — brief description.
"""

from __future__ import annotations
import logging
from datetime import datetime

from config import http, ROME_TZ, target_date
from sources.base import HourlyData

log = logging.getLogger(__name__)

_URLS = {
    "today":              "https://api.yourprovider.com/forecast/bologna/today",
    "tomorrow":           "https://api.yourprovider.com/forecast/bologna/tomorrow",
    "day_after_tomorrow": "https://api.yourprovider.com/forecast/bologna/day2",
}


def fetch(day: str) -> list[HourlyData]:
    url = _URLS[day]
    log.info("[YourProvider] %s...", url)
    now = datetime.now(ROME_TZ)
    current_hour = now.hour if day == "today" else 0

    try:
        r = http.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        log.error("[YourProvider]: %s", e)
        return []

    rows: list[HourlyData] = []
    for h in data.get("hours", []):
        hour = int(h["hour"])
        if day == "today" and hour < current_hour:
            continue
        rows.append(HourlyData(
            hour       = hour,
            icon_class = "",                          # map to a sprite class if available
            desc       = h.get("description", ""),
            temp       = f"{h.get('temp', 0):.1f}",
            prec_prob  = h.get("precipitationProbability"),
            rain_mm    = f"{h.get('rain', 0):.1f}" if h.get("rain", 0) > 0 else "",
            vento_deg  = h.get("windDirection"),
            vento_kmh  = f"{h.get('windSpeed', 0):.0f}",
            humidity   = h.get("humidity"),
        ))

    rows.sort(key=lambda r: r.hour)
    log.info("    → %d hours", len(rows))
    return rows
```

### Step 2 — Export from `sources/__init__.py`

```python
# Add this import:
from sources.your_source import fetch as fetch_your_source

# Add to __all__:
__all__ = [
    "fetch_ilmeteo",
    "fetch_ecmwf",
    "fetch_gfs",
    "fetch_visual_crossing",
    "fetch_3bmeteo",
    "fetch_meteoit",
    "fetch_your_source",    # ← add this
]
```

### Step 3 — Fetch the data in `main.py`

**3a.** Import the function at the top:

```python
from sources import (
    fetch_ilmeteo, fetch_ecmwf, fetch_gfs,
    fetch_visual_crossing, fetch_3bmeteo, fetch_meteoit,
    fetch_your_source,    # ← add this
)
```

**3b.** Call it inside the `for day in days:` loop:

```python
your_rows = _safe(lambda d=day: fetch_your_source(d), "YourProvider", [])
```

**3c.** Add it to the JSON export block:

```python
export["days"][day] = {
    ...
    "your_source": _serialize(your_rows),    # ← add this
}
```

**3d.** Add it to the `_load_from_json` function (for `--test-json` support):

```python
your_rows = [dict_to_hourly(r) for r in d.get("your_source", [])]
```

**3e.** Update the return statement of `_load_from_json` and all callers to include `your_rows`.

**3f.** Pass it to `build_html()`:

```python
page_html = build_html(day, ilm_rows, ilm_names,
                       om_ecmwf, om_gfs, vc_rows, bm_rows, mit_rows,
                       your_rows)    # ← add this
```

**3g.** Update the `any([...])` guard:

```python
if not any([ilm_rows, om_ecmwf, om_gfs, vc_rows, bm_rows, mit_rows, your_rows]):
```

### Step 4 — Add a column in `render/html_builder.py`

**4a.** Add a color entry in the `_C` dict at the top:

```python
_C = {
    ...
    "yp":   "#00838f",  "yp_bg": "#e0f7fa",    # ← add your color
}
```

**4b.** Update the `build_html()` signature to accept the new parameter:

```python
def build_html(
    day, ilm_rows, ilm_names,
    om_ecmwf, om_gfs, vc_rows, bm_rows, mit_rows,
    your_rows,          # ← add this
) -> str:
```

**4c.** Build an index dict inside `build_html()`:

```python
your_idx = idx(your_rows)
```

**4d.** Pass it to `_build_tbody()` (update the signature there too):

```python
tbody = _build_tbody(..., your_idx, ..., n_ilm)
```

**4e.** Inside `_build_tbody()`, add the new column after the existing scrapers:

```python
tbody += _scr_cell(your_idx.get(hour), C["yp_bg"], lambda c, h=hour: night(c, h))
```

Also add it to the rain probability and average temperature calculations:

```python
# Rain probability
for src in [..., your_idx.get(hour)]:   # ← add your_idx.get(hour)
    ...

# Average temperature
for src in [..., your_idx.get(hour)]:   # ← add your_idx.get(hour)
    ...
```

**4f.** Add a header cell in `_build_header()`:

```python
row2_ths = (
    ...
    + hdr2("YourProvider", C["yp"], "yourprovider.com")    # ← add this
    + ...  # rain and avg temp columns follow
)
```

**4g.** Add a `<th>` group in the outer `<thead>` row inside `build_html()`:

```python
<th style="background:{C['yp']};...">🔵 YourProvider</th>
```

### Step 5 — Test

```bash
# Run with live data
python main.py today --no-telegram

# Verify the JSON was saved, then replay it
python main.py today --test-json --no-telegram

# Check the log
tail -50 log/weather_comparison.log
```

---

## Architecture Reference

### Module responsibilities

| Module | Responsibility |
|--------|---------------|
| `config.py` | Single source of truth for env vars, constants, logging setup, shared HTTP session, date helpers |
| `icons.py` | All static mapping tables (icon codes, sprite positions, wind directions). Isolated to keep other modules clean |
| `sources/base.py` | `HourlyData` and `IlMeteoHour` dataclasses; `estimate_prob()`, `avg_temp()`, JSON deserialization helpers |
| `sources/*.py` | One module per provider. Each exposes `fetch(day) -> list[HourlyData]` (or a specialized tuple for ilmeteo) |
| `render/html_builder.py` | Assembles all data into a single HTML string. No network calls, no file I/O |
| `render/screenshot.py` | Renders HTML → PNG via WeasyPrint, then crops whitespace with Pillow |
| `notify/telegram.py` | Sends the PNG to Telegram via Bot API. No rendering logic |
| `main.py` | CLI parsing, orchestration loop, JSON export, error handling |

### Important implementation notes

- **Scraped Italian strings**: `THREEBMETEO_ALT_TO_CLASS` keys and some `WIND_DIR_TO_DEG` entries (SSO, SO, OSO, etc.) are in Italian because they are matched against raw content scraped from Italian websites. These must not be translated.
- **ilmeteo.it URL suffixes**: `/domani` and `/dopodomani` in `ilmeteo.py` are part of the website's URL structure and must remain in Italian.
- **Visual Crossing `lang=it`**: The API is called with `lang=it` to receive Italian condition descriptions. If you prefer English descriptions, change this to `lang=en` in `visual_crossing.py`.
- **WeasyPrint version**: Pin to `<53`. Version 53+ removed `write_png()`.
- **HTTP session**: All sources share the single `http` session from `config.py`, which has a retry policy (3 retries, backoff 1.5s, on 429/5xx).

---

## Troubleshooting

**No PNG generated, error about GTK3**
Install GTK3-Runtime (Windows) or the Pango/Cairo system libraries (Linux/macOS). See [Setup](#setup).

**`AttributeError: 'HTML' object has no attribute 'write_png'`**
You have WeasyPrint ≥ 53. Downgrade: `pip install "weasyprint<53"`

**`[VisualCrossing] Invalid API key`**
Check `VISUALCROSSING_API_KEY` in `utils/.env`. The key must have no leading/trailing spaces.

**`[Telegram] ❌ 401`**
Your `TELEGRAM_TOKEN` is invalid or has been revoked. Generate a new one via `@BotFather`.

**`[Telegram] ❌ 400: Bad Request: chat not found`**
The `TELEGRAM_CHAT_ID` is wrong. For group chats the ID is negative (e.g. `-1001234567890`).

**Scraping returns 0 hours**
The website may have changed its HTML structure. Check the log for details and update the regex patterns in the relevant source module.

**Icons not showing in PNG**
Make sure `utils/s-cartoon2016b-34.png` exists. This sprite sheet is embedded as base64 directly into the HTML, so it must be present before rendering.
