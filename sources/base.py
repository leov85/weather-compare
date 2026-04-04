"""
sources/base.py
===============
Shared data structures for all hourly weather data
and utility functions used by multiple sources.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class HourlyData:
    """
    Normalized hourly record.
    Each source returns list[HourlyData] or, in the case of ilmeteo.it
    (which has multiple numerical models per hour), IlMeteoHour.
    """
    hour:       int
    icon_class: str         = ""
    desc:       str         = ""
    temp:       str         = "—"   # string "22.5" or "—"
    prec_prob:  int | None  = None  # 0–100, None = not available
    rain_mm:    str         = ""    # string "1.2" or ""
    vento_deg:  int | None  = None
    vento_kmh:  str         = "—"
    humidity:   int | None  = None
    is_day:     int         = 1
    # Optional fields present only in some sources
    rain_only_mm: str       = ""
    clouds:       int | None = None
    prec_type:    int | None = None


@dataclass
class IlMeteoModel:
    """A single numerical model within an hour of ilmeteo.it."""
    icon_class: str  = ""
    desc:       str  = ""
    temp:       str  = "—"
    rain_mm:    str  = ""
    vento_deg:  int  = 0
    vento_kmh:  str  = "—"
    prec_prob:  int | None = None


@dataclass
class IlMeteoHour:
    """An hour of ilmeteo.it: contains multiple numerical models."""
    hour:    int
    models:  list[IlMeteoModel] = field(default_factory=list)


# ── Common Protocol for Sources ──────────────────────────────────────────────

class MeteoSource(Protocol):
    name: str

    def fetch(self, day: str) -> list[HourlyData]:
        ...


# ── Shared Helpers ────────────────────────────────────────────────────────────

def estimate_prob(r: HourlyData | None) -> int | None:
    """
    Estimates rain probability (0–100) from an HourlyData.
    Uses prec_prob if available, otherwise infers from rain_mm or icon class.
    """
    if r is None:
        return None
    if r.prec_prob is not None:
        return r.prec_prob
    is_rainy = False
    try:
        if r.rain_mm and float(r.rain_mm.replace(",", ".")) > 0:
            is_rainy = True
    except (ValueError, TypeError):
        pass
    if not is_rainy:
        rainy_classes = {
            "ss5","ss6","ss7","ss9","ss10","ss11","ss12","ss13",
            "ss16","ss17","ss18","ss21",
            "ss105","ss106","ss107","ss109","ss110","ss111",
            "ss112","ss113","ss116","ss117","ss118",
        }
        if r.icon_class in rainy_classes:
            is_rainy = True
    return 100 if is_rainy else 0


def avg_temp(temps: list[str | None]) -> str:
    """Calculates average temperature from a list of strings (or None) → formatted string."""
    vals = []
    for t in temps:
        if t is None or t == "—":
            continue
        try:
            vals.append(float(str(t).replace(",", ".")))
        except (ValueError, TypeError):
            pass
    if not vals:
        return "—"
    return f"{sum(vals) / len(vals):.1f}"


def dict_to_hourly(d: dict) -> HourlyData:
    """
    Converts a dict (saved legacy JSON format) to HourlyData.
    Used by the --test-json loader in main.py.
    """
    return HourlyData(
        hour=d.get("hour") or d.get("ora", 0),
        icon_class=d.get("icon_class", ""),
        desc=d.get("desc", ""),
        temp=d.get("temp", "—"),
        prec_prob=d.get("prec_prob"),
        rain_mm=d.get("rain_mm") or d.get("pioggia_mm", ""),
        vento_deg=d.get("vento_deg"),
        vento_kmh=d.get("vento_kmh", "—"),
        humidity=d.get("humidity") or d.get("umidita"),
        is_day=d.get("is_day", 1),
        rain_only_mm=d.get("rain_only_mm", ""),
        clouds=d.get("clouds") or d.get("nubi"),
        prec_type=d.get("prec_type"),
    )


def ilmeteo_dict_to_hour(d: dict) -> IlMeteoHour:
    """Converts a legacy ilmeteo dict to IlMeteoHour."""
    models = [
        IlMeteoModel(
            icon_class=m.get("icon_class", ""),
            desc=m.get("desc", ""),
            temp=m.get("temp", "—"),
            rain_mm=m.get("rain_mm") or m.get("pioggia_mm", ""),
            vento_deg=m.get("vento_deg", 0),
            vento_kmh=m.get("vento_kmh", "—"),
            prec_prob=m.get("prec_prob"),
        )
        for m in (d.get("models") or d.get("modelli", []))
    ]
    return IlMeteoHour(hour=d.get("hour") or d.get("ora", 0), models=models)
