"""
notify/telegram.py
==================
Weather comparison PNG delivery via Telegram Bot API.
"""

from __future__ import annotations
import logging
from datetime import datetime

from config import http, ROME_TZ, TELEGRAM_TOKEN, TELEGRAM_CHATID, target_date

log = logging.getLogger(__name__)

_API_BASE = "https://api.telegram.org/bot"


def send(image_path: str, day: str) -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHATID:
        log.info("[Telegram] Token/ChatID not configured → skip")
        return

    target_dt = target_date(day)
    day_label = {"today": "Today", "tomorrow": "Tomorrow", "day_after_tomorrow": "Day After Tomorrow"}[day]
    now_str   = datetime.now(ROME_TZ).strftime("%d/%m/%Y %H:%M")
    caption   = (
        f"🌦 <b>Weather Comparison Bologna — {day_label} {target_dt.strftime('%d/%m')}</b>\n"
        f"📊 ilmeteo (COMPOSITE·ECMWF·UKMO) · OpenMeteo (ECMWF+GFS) "
        f"· VisualCrossing · 3bMeteo · meteo.it\n"
        f"🕐 {now_str}"
    )

    try:
        with open(image_path, "rb") as f:
            resp = http.post(
                f"{_API_BASE}{TELEGRAM_TOKEN}/sendPhoto",
                data={
                    "chat_id":    TELEGRAM_CHATID,
                    "caption":    caption,
                    "parse_mode": "HTML",
                },
                files={"photo": f},
                timeout=90,
            )
        if resp.ok:
            log.info("[Telegram] ✅ sent")
        else:
            log.warning("[Telegram] ❌ %d: %s", resp.status_code, resp.text[:200])
    except Exception as e:
        log.error("[Telegram] ❌ %s", e)
