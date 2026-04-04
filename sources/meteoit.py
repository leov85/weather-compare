"""
sources/meteoit.py
==================
Source meteo.it — HTML scraping + embedded JSON parsing.
"""

from __future__ import annotations
import re
import json
import html as html_module
import logging
from datetime import datetime

from config import http, ROME_TZ, target_date
from icons import SIMBOLI_METEO, METEOIT_PREVISION_CODE_MAP
from sources.base import HourlyData

log = logging.getLogger(__name__)

_URLS = {
    "today":              "https://www.meteo.it/meteo/bologna-oggi-37006",
    "tomorrow":           "https://www.meteo.it/meteo/bologna-domani-37006",
    "day_after_tomorrow": "https://www.meteo.it/meteo/bologna-2-giorni-37006",
}

_DAY_OVERVIEW_PAT = re.compile(
    r'<div id="day-overview"[^>]*data-dayoverview="([^"]*)"'
)


def fetch(day: str) -> list[HourlyData]:
    url = _URLS[day]
    log.info("[meteo.it]        %s", url)
    now = datetime.now(ROME_TZ)
    current_hour = now.hour if day == "today" else 0

    resp = http.get(url, timeout=30)
    resp.raise_for_status()
    raw_html = resp.text

    match = _DAY_OVERVIEW_PAT.search(raw_html)
    if not match:
        log.warning("[meteo.it] data-dayoverview not found → 0 hours")
        return []

    try:
        data = json.loads(html_module.unescape(match.group(1)))
    except json.JSONDecodeError as e:
        log.error("[meteo.it] JSON decode error: %s", e)
        return []

    rows: list[HourlyData] = []
    for h in data.get("data", {}).get("hours", []):
        time_str = h.get("time")
        if not time_str:
            continue
        hour = int(time_str[11:13])
        if day == "today" and hour < current_hour:
            continue

        prevision_code = h.get("prevision")
        icon_class     = METEOIT_PREVISION_CODE_MAP.get(prevision_code, "")

        wind_code = h.get("windDirection")
        vento_deg: int | None = (
            round(wind_code * (360 / 16)) if wind_code is not None else None
        )

        rows.append(HourlyData(
            hour       = hour,
            icon_class = icon_class,
            desc       = SIMBOLI_METEO.get(icon_class, f"Code {prevision_code}"),
            temp       = f"{h.get('temperature', 0):.0f}",
            prec_prob  = h.get("downfallPercentage"),
            rain_mm    = (
                f"{h.get('downfallQuantity', 0):.1f}"
                if h.get("downfallQuantity", 0) > 0 else ""
            ),
            vento_deg  = vento_deg,
            vento_kmh  = f"{h.get('windIntensity', 0):.0f}",
            humidity   = h.get("umidity"),
        ))

    rows.sort(key=lambda r: r.hour)
    log.info("    → %d hours", len(rows))
    return rows
