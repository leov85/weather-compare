"""
sources/visual_crossing.py
==========================
Source Visual Crossing — paid API (1000 req/day free tier).
API key configured in .env as VISUALCROSSING_API_KEY.
"""

from __future__ import annotations
import logging
from datetime import datetime

from config import http, ROME_TZ, VC_KEY, target_date
from sources.base import HourlyData

log = logging.getLogger(__name__)

_BASE_URL = (
    "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/"
    "services/timeline/Bologna,Italy"
)

# Mapping: VC icon substring → CSS sprite class
_ICON_MAP = (
    ("rain",          "ss10"),
    ("snow",          "ss11"),
    ("thunder",       "ss13"),
    ("fog",           "ss14"),
    ("partly-cloudy", "ss3"),
    ("cloudy",        "ss8"),
    ("clear",         "ss1"),
)


def _vc_icon(icon_str: str) -> str:
    for keyword, cls in _ICON_MAP:
        if keyword in icon_str:
            return cls
    return ""


def fetch(day: str) -> list[HourlyData]:
    if not VC_KEY:
        log.info("[VisualCrossing] VISUALCROSSING_API_KEY not set → skip")
        return []

    td  = target_date(day)
    now = datetime.now(ROME_TZ)
    ds  = td.isoformat()
    log.info("[VisualCrossing] %s...", ds)

    try:
        r = http.get(
            f"{_BASE_URL}/{ds}/{ds}",
            params={
                "unitGroup":   "metric",
                "include":     "hours",
                "key":         VC_KEY,
                "contentType": "json",
                "lang":        "it",
            },
            timeout=15,
        )
        if r.status_code == 401:
            log.warning("[VisualCrossing] Invalid API key")
            return []
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        log.error("[VisualCrossing]: %s", e)
        return []

    current_hour = now.hour if day == "today" else 0
    rows: list[HourlyData] = []

    for day_data in data.get("days", []):
        for h in day_data.get("hours", []):
            hour = int(h["datetime"][:2])
            if day == "today" and hour < current_hour:
                continue
            prec_mm = h.get("precip", 0) or 0
            rows.append(HourlyData(
                hour       = hour,
                icon_class = _vc_icon(h.get("icon", "")),
                desc       = h.get("conditions", ""),
                temp       = f"{h.get('temp', 0):.1f}",
                prec_prob  = int(h.get("precipprob", 0) or 0),
                rain_mm    = f"{prec_mm:.1f}" if prec_mm > 0 else "",
                vento_deg  = h.get("winddir", 0),
                vento_kmh  = f"{h.get('windspeed', 0):.0f}",
                humidity   = int(h.get("humidity", 0)),
            ))

    log.info("    → %d hours", len(rows))
    return rows
