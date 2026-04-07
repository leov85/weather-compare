#!/usr/bin/env python3
"""
main.py  — Weather Comparison Bologna (v4 — modular architecture)
================================================================
Usage:
    python main.py                          # auto: <20h → today+tomorrow, ≥20h → tomorrow
    python main.py today tomorrow day_after_tomorrow
    python main.py --test-json              # use last saved JSON
    python main.py --no-scraping            # skip 3bmeteo and meteo.it
    python main.py --no-telegram            # do not send to Telegram
    python main.py --keep-html              # also save the HTML file
    python main.py --summary                # show only Hour, Avg Rain Prob, and Avg Temp

Dependencies:
    pip install "weasyprint<53" requests pillow python-dotenv pytz
"""

import sys
import os
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path

from config import ROME_TZ
from sources.base import IlMeteoHour, HourlyData, dict_to_hourly, ilmeteo_dict_to_hour
from sources import (
    fetch_ilmeteo, fetch_ecmwf, fetch_gfs,
    fetch_visual_crossing, fetch_3bmeteo, fetch_meteoit,
)
from render  import build_html, html_to_png
from notify  import telegram_send

log = logging.getLogger(__name__)


# ── CLI Utilities ─────────────────────────────────────────────────────────────

def resolve_days(args: list[str]) -> list[str]:
    valid = {"today", "tomorrow", "day_after_tomorrow"}
    order = ["today", "tomorrow", "day_after_tomorrow"]
    if args:
        selected_days = [a.lower() for a in args if a.lower() in valid]
        if not selected_days:
            print("Invalid arguments. Use: today / tomorrow / day_after_tomorrow")
            sys.exit(1)
        return [d for d in order if d in selected_days]
    now = datetime.now(ROME_TZ)
    return ["today", "tomorrow"] if now.hour < 20 else ["tomorrow"]


def _safe(fn, label: str, default):
    """Calls fn(), logs error and returns default on exception."""
    try:
        return fn()
    except Exception as e:
        log.error("[ERROR %s]: %s", label, e)
        return default


# ── Loading data from JSON (--test-json) ──────────────────────────────────────

def _load_from_json(json_path: Path, day: str):
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    d = data.get("days", {}).get(day, {})

    ilm_dicts = d.get("ilmeteo", {}).get("data", [])
    ilm_rows  = [ilmeteo_dict_to_hour(r) for r in ilm_dicts]
    ilm_names = d.get("ilmeteo", {}).get("models", [])
    om_ecmwf  = [dict_to_hourly(r) for r in d.get("openmeteo_ecmwf", [])]
    om_gfs    = [dict_to_hourly(r) for r in d.get("openmeteo_gfs", [])]
    vc_rows   = [dict_to_hourly(r) for r in d.get("visual_crossing", [])]
    bm_rows   = [dict_to_hourly(r) for r in d.get("3bmeteo", [])]
    mit_rows  = [dict_to_hourly(r) for r in d.get("meteo_it", [])]
    return ilm_rows, ilm_names, om_ecmwf, om_gfs, vc_rows, bm_rows, mit_rows


# ── Data Serialization for export JSON ────────────────────────────────────────

def _serialize_ilm(rows: list[IlMeteoHour]) -> list[dict]:
    return [
        {
            "hour": r.hour,
            "models": [
                {
                    "icon_class": m.icon_class, "desc": m.desc,
                    "temp": m.temp, "rain_mm": m.rain_mm,
                    "vento_deg": m.vento_deg, "vento_kmh": m.vento_kmh,
                    "prec_prob": m.prec_prob,
                }
                for m in r.models
            ],
        }
        for r in rows
    ]


def _serialize(rows: list[HourlyData]) -> list[dict]:
    return [r.__dict__ for r in rows]


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Weather Comparison Bologna → PNG → Telegram")
    parser.add_argument("days",          nargs="*",          help="today / tomorrow / day_after_tomorrow")
    parser.add_argument("--output-dir",  default=".",        help="Output folder")
    parser.add_argument("--no-telegram", action="store_true", help="Do not send to Telegram")
    parser.add_argument("--keep-html",   action="store_true", help="Keep intermediate HTML file")
    parser.add_argument("--no-scraping", action="store_true",
                        help="Skip 3bmeteo and meteo.it (faster)")
    parser.add_argument("--test-json",   action="store_true",
                        help="Use last saved JSON instead of fetching new data")
    parser.add_argument("--summary",     action="store_true",
                        help="Show only Hour, Avg Rain Prob, and Avg Temp columns")
    args = parser.parse_args()

    subfolder = os.path.join(args.output_dir, "output_weather")
    os.makedirs(subfolder, exist_ok=True)

    days = resolve_days(args.days)
    now  = datetime.now(ROME_TZ)
    ts   = now.strftime("%Y.%m.%d.%H.%M")

    # Find test JSON if requested
    test_json_path: Path | None = None
    if args.test_json:
        json_files = sorted(Path(subfolder).glob("*_meteo_data.json"))
        if json_files:
            test_json_path = json_files[-1]
            log.info("[TEST MODE] Loading data from: %s", test_json_path.name)
        else:
            log.warning("[TEST MODE] No JSON found, proceeding with live data.")

    log.info("=" * 60)
    log.info("  Weather Comparison Bologna  |  %s", now.strftime("%d/%m/%Y %H:%M"))
    log.info("  Days: %s", days)
    log.info("  Output folder: %s", subfolder)
    log.info("=" * 60)

    generated: list[tuple[str, str]] = []
    export: dict = {
        "metadata": {"generated_at": now.isoformat(), "location": "Bologna"},
        "days": {},
    }

    for day in days:
        log.info("\n── %s %s", day.upper(), "─" * (50 - len(day)))

        # ── Data Fetching ─────────────────────────────────────────────────────
        if test_json_path and day in (json.loads(test_json_path.read_text("utf-8"))
                                       .get("days", {})):
            log.info("    [TEST] Using JSON data for %s", day)
            (ilm_rows, ilm_names,
             om_ecmwf, om_gfs,
             vc_rows, bm_rows, mit_rows) = _load_from_json(test_json_path, day)
        else:
            ilm_rows, ilm_names = _safe(
                lambda d=day: fetch_ilmeteo(d), "ilmeteo", ([], [])
            )
            om_ecmwf = _safe(lambda d=day: fetch_ecmwf(d),           "OpenMeteo ECMWF", [])
            om_gfs   = _safe(lambda d=day: fetch_gfs(d),             "OpenMeteo GFS",   [])
            vc_rows  = _safe(lambda d=day: fetch_visual_crossing(d),  "VisualCrossing",  [])

            if args.no_scraping:
                bm_rows = mit_rows = []
            else:
                bm_rows  = _safe(lambda d=day: fetch_3bmeteo(d),   "3bmeteo",  [])
                mit_rows = _safe(lambda d=day: fetch_meteoit(d),    "meteo.it", [])

        # ── JSON Export ───────────────────────────────────────────────────────
        export["days"][day] = {
            "ilmeteo":        {"models": ilm_names, "data": _serialize_ilm(ilm_rows)},
            "openmeteo_ecmwf": _serialize(om_ecmwf),
            "openmeteo_gfs":   _serialize(om_gfs),
            "visual_crossing": _serialize(vc_rows),
            "3bmeteo":         _serialize(bm_rows),
            "meteo_it":        _serialize(mit_rows),
        }

        if not any([ilm_rows, om_ecmwf, om_gfs, vc_rows, bm_rows, mit_rows]):
            log.warning("  No data for %s, skipping.", day)
            continue

        # ── Render HTML → PNG ─────────────────────────────────────────────────
        page_html = build_html(day, ilm_rows, ilm_names,
                                   om_ecmwf, om_gfs, vc_rows, bm_rows, mit_rows,
                                   summary=args.summary)

        if args.keep_html:
            hp = os.path.join(subfolder, f"meteo_{day}.html")
            Path(hp).write_text(page_html, encoding="utf-8")
            log.info("[HTML] %s", hp)

        png_path = os.path.join(subfolder, f"meteo_{day}.png")
        try:
            html_to_png(page_html, png_path)
            generated.append((day, png_path))
        except Exception as e:
            log.error("[PNG ERROR]: %s", e)
            continue

        if not args.no_telegram:
            telegram_send(png_path, day)

    # ── Save unique JSON ──────────────────────────────────────────────────────
    json_path = os.path.join(subfolder, f"{ts}_meteo_data.json")
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(export, f, indent=2, ensure_ascii=False)
        log.info("[JSON] Data saved to: %s", json_path)
    except Exception as e:
        log.error("[JSON ERROR]: %s", e)

    log.info("─" * 60)
    if generated:
        log.info("Generated files:")
        for d, p in generated:
            log.info("  📷  %s  (%d KB)", p, Path(p).stat().st_size // 1024)
    else:
        log.info("No files generated.")


if __name__ == "__main__":
    main()
