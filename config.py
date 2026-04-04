"""
config.py
=========
Centralized configuration: constants, environment variables,
logging, HTTP session with retry, timezone.
"""

import os
import logging
from datetime import datetime, timedelta

import pytz
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

# ── .env ──────────────────────────────────────────────────────────────────
load_dotenv(os.path.join("utils", ".env"))

# ── Geographic Constants ──────────────────────────────────────────────────
ROME_TZ      = pytz.timezone("Europe/Rome")
BOLOGNA_LAT  = 44.4949
BOLOGNA_LON  = 11.3426

# ── Credentials / API Keys ────────────────────────────────────────────────
TELEGRAM_TOKEN  = os.getenv("TELEGRAM_TOKEN",            "")
TELEGRAM_CHATID = os.getenv("TELEGRAM_CHAT_ID",          "")
VC_KEY          = os.getenv("VISUALCROSSING_API_KEY",    "")
VERIFY_SSL      = os.getenv("VERIFY_SSL", "True").lower() == "true"

# ── Common User-Agent ─────────────────────────────────────────────────────
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# ── Logging ───────────────────────────────────────────────────────────────
log_dir = "log"
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s [%(name)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            os.path.join(log_dir, "weather_comparison.log"), encoding="utf-8"
        ),
    ],
)
logging.getLogger("weasyprint").setLevel(logging.ERROR)
log = logging.getLogger(__name__)

# ── Windows: GTK for WeasyPrint ───────────────────────────────────────────
if os.name == "nt":
    os.environ["GIO_USE_VFS"] = "local"
    os.environ["G_MESSAGES_DEBUG"] = "none"
    gtk_bin = r"C:\Program Files\GTK3-Runtime Win64\bin"
    if os.path.exists(gtk_bin):
        os.add_dll_directory(gtk_bin)
    else:
        log.warning("WARNING: GTK3 Runtime not found in '%s'. Image generation will fail.", gtk_bin)

# ── HTTP Session with Auto-Retry ──────────────────────────────────────────
_retry = Retry(
    total=3,
    backoff_factor=1.5,
    status_forcelist=[429, 500, 502, 503, 504],
)
http = requests.Session()
http.headers.update({"User-Agent": UA})
http.verify = VERIFY_SSL

if not VERIFY_SSL:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

http.mount("https://", HTTPAdapter(max_retries=_retry))

# ── Date Utilities ────────────────────────────────────────────────────────
def day_offset(day: str) -> int:
    return {"today": 0, "tomorrow": 1, "day_after_tomorrow": 2}[day]


def target_date(day: str):
    return (datetime.now(ROME_TZ) + timedelta(days=day_offset(day))).date()


def deg_to_arrow(deg) -> str:
    if deg is None:
        return "—"
    arrows = ["↓", "↙", "←", "↖", "↑", "↗", "→", "↘"]
    return arrows[round(int(deg) / 45) % 8]
