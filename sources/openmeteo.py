"""
sources/openmeteo.py
====================
Source Open-Meteo — free API, two models: ECMWF IFS and GFS.
"""

from __future__ import annotations
import logging
from datetime import datetime

from config import http, ROME_TZ, BOLOGNA_LAT, BOLOGNA_LON, target_date
from icons import SIMBOLI_METEO, WMO_ICON
from sources.base import HourlyData

log = logging.getLogger(__name__)

_API_URL = "https://api.open-meteo.com/v1/forecast"
_HOURLY_PARAMS = (
    "temperature_2m,relative_humidity_2m,precipitation,rain,"
    "weather_code,cloud_cover,wind_speed_10m,wind_direction_10m,"
    "precipitation_probability,precipitation_type,is_day"
)


def _fetch(day: str, model: str) -> list[HourlyData]:
    td  = target_date(day)
    now = datetime.now(ROME_TZ)
    try:
        r = http.get(_API_URL, params={
            "latitude":      BOLOGNA_LAT,
            "longitude":     BOLOGNA_LON,
            "hourly":        _HOURLY_PARAMS,
            "models":        model,
            "timezone":      "Europe/Rome",
            "forecast_days": 3,
        }, timeout=15)
        r.raise_for_status()
        h = r.json()["hourly"]
    except Exception as e:
        log.error("[OpenMeteo %s]: %s", model, e)
        return []

    current_hour = now.hour if day == "today" else 0
    n = len(h["time"])
    rows: list[HourlyData] = []

    for i, t in enumerate(h["time"]):
        if not t.startswith(td.isoformat()):
            continue
        hour = int(t[11:13])
        if day == "today" and hour < current_hour:
            continue

        wmo        = h["weather_code"][i]
        icon_class = WMO_ICON.get(wmo, "")
        t_val = h["temperature_2m"][i]
        p_val = h["precipitation"][i]
        r_val = h.get("rain", [0] * n)[i]
        w_val = h["wind_speed_10m"][i]

        rows.append(HourlyData(
            hour         = hour,
            icon_class   = icon_class,
            desc         = SIMBOLI_METEO.get(icon_class, str(wmo)),
            temp         = f"{t_val:.1f}" if t_val is not None else "—",
            prec_prob    = h.get("precipitation_probability", [None] * n)[i],
            rain_mm      = f"{p_val:.1f}" if p_val is not None and p_val > 0 else "",
            rain_only_mm = f"{r_val:.1f}" if r_val is not None and r_val > 0 else "",
            vento_deg    = h["wind_direction_10m"][i],
            vento_kmh    = f"{w_val:.0f}" if w_val is not None else "—",
            humidity     = h["relative_humidity_2m"][i],
            clouds       = h.get("cloud_cover", [0] * n)[i],
            prec_type    = h.get("precipitation_type", [0] * n)[i],
            is_day       = h.get("is_day", [1] * n)[i],
        ))

    return rows


def fetch_ecmwf(day: str) -> list[HourlyData]:
    log.info("[OpenMeteo ECMWF] %s...", day)
    rows = _fetch(day, "ecmwf_ifs")
    log.info("    → %d hours", len(rows))
    return rows


def fetch_gfs(day: str) -> list[HourlyData]:
    log.info("[OpenMeteo GFS]   %s...", day)
    rows = _fetch(day, "gfs_seamless")
    log.info("    → %d hours", len(rows))
    return rows
