"""
sources/threebmeteo.py
======================
Source 3bmeteo.com — HTML scraping with requests.

NOTE: The Italian strings in THREEBMETEO_ALT_TO_CLASS (icons.py) and the
regex patterns here must remain in Italian because they match scraped content
from the 3bmeteo.com website, which is written in Italian.
"""

from __future__ import annotations
import re
import logging
from datetime import datetime

from config import http, ROME_TZ, target_date
from icons import THREEBMETEO_ALT_TO_CLASS, WIND_DIR_TO_DEG
from sources.base import HourlyData

log = logging.getLogger(__name__)

_URLS = {
    "today":              "https://www.3bmeteo.com/meteo/bologna",
    "tomorrow":           "https://www.3bmeteo.com/meteo/bologna/1",
    "day_after_tomorrow": "https://www.3bmeteo.com/meteo/bologna/2",
}

# Module-level compiled regex
_HOUR_PAT       = re.compile(r'ds-forecast-time">(\d{1,2})</span>')
_DESC_PAT       = re.compile(r'fc-accordion-condition">.*?<span[^>]*>\s*([^<]+?)\s*</span>', re.DOTALL)
_TEMP_PAT       = re.compile(r'data-temp-c="([\d.-]+)"')
_RAIN_MM_PAT    = re.compile(r'alt="Precipitazioni".*?>\s*([\d.,]+)\s*mm', re.DOTALL)
_WIND_SPEED_PAT = re.compile(r'data-wind-kmh="(\d+)"')
_WIND_DIR_PAT   = re.compile(r'data-wind-dir="([a-zA-Z]{1,3})"')
_HUMIDITY_PAT   = re.compile(r'data-param="umidita".*?>\s*(\d+)%', re.DOTALL)


def fetch(day: str) -> list[HourlyData]:
    url = _URLS[day]
    log.info("[3bmeteo.com]     %s", url)
    now = datetime.now(ROME_TZ)
    current_hour = now.hour if day == "today" else 0

    resp = http.get(url, timeout=30)
    resp.raise_for_status()
    page_html = resp.text

    # Isolate hourly table, discard historical data and footer
    table_content = re.split(
        r'id="content-esaorario"|id="citynewsdomain"',
        page_html, flags=re.I
    )[0]

    hourly_blocks = re.findall(
        r'(<li class="fc-accordion-item".*?)(?=<li class="fc-accordion-item"|\Z)',
        table_content, re.DOTALL
    )

    rows: list[HourlyData] = []
    for blk in hourly_blocks:
        hour_m = _HOUR_PAT.search(blk)
        if not hour_m:
            continue
        hour = int(hour_m.group(1))
        if day == "today" and hour < current_hour:
            continue

        desc_m       = _DESC_PAT.search(blk)
        temp_m       = _TEMP_PAT.search(blk)
        rain_mm_m    = _RAIN_MM_PAT.search(blk)
        wind_speed_m = _WIND_SPEED_PAT.search(blk)
        wind_dir_m   = _WIND_DIR_PAT.search(blk)
        humidity_m   = _HUMIDITY_PAT.search(blk)

        # desc is the text from the condition span — kept in Italian
        # as it must match the keys in THREEBMETEO_ALT_TO_CLASS
        desc       = desc_m.group(1).strip().lower() if desc_m else ""
        icon_class = THREEBMETEO_ALT_TO_CLASS.get(desc, "")

        vento_deg: int | None = None
        if wind_dir_m:
            vento_deg = WIND_DIR_TO_DEG.get(wind_dir_m.group(1).upper())

        rows.append(HourlyData(
            hour       = hour,
            icon_class = icon_class,
            desc       = desc,
            temp       = temp_m.group(1).replace(",", ".") if temp_m else "—",
            rain_mm    = rain_mm_m.group(1).replace(",", ".") if rain_mm_m else "",
            prec_prob  = None,
            vento_deg  = vento_deg,
            vento_kmh  = wind_speed_m.group(1) if wind_speed_m else "—",
            humidity   = int(humidity_m.group(1)) if humidity_m else None,
        ))

    rows.sort(key=lambda r: r.hour)
    log.info("    → %d hours%s", len(rows), " (layout not recognized)" if not rows else "")
    return rows
