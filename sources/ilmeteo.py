"""
sources/ilmeteo.py
==================
Source ilmeteo.it — HTML parsing of the model comparison page.
Returns (list[IlMeteoHour], list[str]) instead of the standard protocol
because ilmeteo.it has a multi-model structure per hour.

NOTE: The URL suffixes /domani and /dopodomani are part of the ilmeteo.it
URL structure and must remain in Italian to function correctly.
"""

from __future__ import annotations
import re
import logging
from datetime import datetime

from config import http, ROME_TZ, target_date
from icons import SIMBOLI_METEO
from sources.base import IlMeteoHour, IlMeteoModel

log = logging.getLogger(__name__)

# URL suffixes are part of the website's Italian URL structure — do not translate
_URL_SUFFIX = {"today": "", "tomorrow": "/domani", "day_after_tomorrow": "/dopodomani"}


def fetch(day: str) -> tuple[list[IlMeteoHour], list[str]]:
    url = f"https://www.ilmeteo.it/confronta-meteo/Bologna{_URL_SUFFIX[day]}?tipo=1h"
    log.info("[ilmeteo.it] %s", url)

    resp = http.get(url, timeout=30)
    resp.raise_for_status()

    td        = target_date(day)
    target_id = f"day_{td.day:02d}_{td.month:02d}"
    rows, names = _parse(resp.text, target_id)

    if day == "today":
        current_hour = datetime.now(ROME_TZ).hour
        rows = [r for r in rows if r.hour >= current_hour]

    log.info("    → %d hours · models: %s", len(rows), names)
    return rows, names


# ── HTML Parsing ──────────────────────────────────────────────────────────────

def _parse(full_html: str, target_id: str) -> tuple[list[IlMeteoHour], list[str]]:
    day_block_match = re.search(
        f'id="{target_id}"[^>]*>(.*?)(?=<div[^>]+id="day_|$)',
        full_html, re.DOTALL,
    )
    if not day_block_match:
        log.debug("Block %s not found in HTML, using fallback", target_id)
        day_html = full_html
    else:
        day_html = day_block_match.group(1)

    model_names = re.findall(r'alt="([^"]+) logo"', day_html)
    if not model_names:
        model_names = ["COMPOSITE", "ECMWF", "UKMO"]

    row_pat  = re.compile(r'<tr[^>]*>\s*<th[^>]*scope="row"[^>]*>(\d+)</th>(.*?)</tr>', re.DOTALL)
    td_pat   = re.compile(r'<td[^>]*class="single-data"[^>]*>(.*?)</td>', re.DOTALL)
    sym_pat  = re.compile(r'icona_simbolo (ss\d+)')
    temp_pat = re.compile(r'container-temp.*?<span>\s*([\d,\.]+)°', re.DOTALL)
    rain_pat = re.compile(r'data-precipitation="([\d,\.]+)"')
    wdeg_pat = re.compile(r'rotate\((\d+)deg\)')
    wkmh_pat = re.compile(r'container-wind.*?<span>\s*([\d/]+)\s*</span>', re.DOTALL)

    rows: list[IlMeteoHour] = []
    for m in row_pat.finditer(day_html):
        hour, row_html = int(m.group(1)), m.group(2)
        models: list[IlMeteoModel] = []
        for td in td_pat.finditer(row_html):
            cell   = td.group(1)
            sym_m  = sym_pat.search(cell)
            temp_m = temp_pat.search(cell)
            rain_m = rain_pat.search(cell)
            wdeg_m = wdeg_pat.search(cell)
            wkmh_m = wkmh_pat.search(cell)
            icon   = sym_m.group(1) if sym_m else ""
            models.append(IlMeteoModel(
                icon_class = icon,
                desc       = SIMBOLI_METEO.get(icon, icon or "?"),
                temp       = temp_m.group(1).replace(",", ".") if temp_m else "—",
                rain_mm    = rain_m.group(1).replace(",", ".") if rain_m else "",
                vento_deg  = int(wdeg_m.group(1)) if wdeg_m else 0,
                vento_kmh  = wkmh_m.group(1).strip() if wkmh_m else "—",
                prec_prob  = None,
            ))
        if models:
            rows.append(IlMeteoHour(hour=hour, models=models))

    return rows, model_names
