"""
render/html_builder.py
======================
Builds the HTML page for the weather comparison.
Separated from PNG rendering to allow testing HTML output
without depending on WeasyPrint.
"""

from __future__ import annotations
import os
import base64
import logging
from datetime import datetime

from config import ROME_TZ, deg_to_arrow, target_date
from icons import build_sprite_css, to_night_class
from sources.base import HourlyData, IlMeteoHour, estimate_prob, avg_temp

log = logging.getLogger(__name__)

# Color palette per source
_C = {
    "ilm":  "#1a4a8a",  "ilm_bg":  "#eef3fb",
    "oecm": "#2e7d32",  "oecm_bg": "#edf7ee",
    "ogfs": "#00695c",  "ogfs_bg": "#e0f2f1",
    "vc":   "#6a1b9a",  "vc_bg":   "#f3e5f5",
    "bm":   "#b71c1c",  "bm_bg":   "#fce4ec",
    "mit":  "#e65100",  "mit_bg":  "#fff3e0",
    "sum":  "#37474f",
}

_ICON_PATH = os.path.join("utils", "s-cartoon2016b-34.png")
_CSS_FILE   = os.path.join(os.path.dirname(__file__), "static", "style.css")


def _load_icon_base64() -> str:
    if os.path.exists(_ICON_PATH):
        with open(_ICON_PATH, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return ""


def _load_static_css() -> str:
    """Loads the main CSS from the static folder."""
    if os.path.exists(_CSS_FILE):
        with open(_CSS_FILE, "r", encoding="utf-8") as f:
            return f.read()
    log.warning("[html_builder] CSS file not found: %s", _CSS_FILE)
    return ""


def _get_icon_html(cls: str) -> str:
    if not cls:
        return '<span style="font-size:18px">❓</span>'
    return f'<span class="s {cls}"></span>'


# ── Cell Helpers ──────────────────────────────────────────────────────────────

def _api_cell(r: HourlyData | None, bg: str, night_cls_fn) -> str:
    if not r:
        return f'<td class="na" style="background:{bg}">—</td>'
    icon_cls = night_cls_fn(r.icon_class)
    rain = (f'<br><span class="rain">💧{r.rain_mm} mm</span>'
            if r.rain_mm else "")
    prob = (f'<span class="prob"> {r.prec_prob}%</span>'
            if r.prec_prob is not None and r.prec_prob > 0 else "")
    umid = (f'<span class="umid"> 💦{r.humidity}%</span>'
            if r.humidity else "")
    return (
        f'<td style="background:{bg};font-size:11px;padding:4px 6px;'
        f'text-align:center;vertical-align:middle;border-right:1px solid #ddd;'
        f'white-space:nowrap;width:110px;min-width:110px;max-width:110px">'
        f'<div style="display:flex;justify-content:center;align-items:center">'
        f'{_get_icon_html(icon_cls)}{prob}</div>'
        f'<b>{r.temp}°</b>{rain}<br>'
        f'<span class="wind">{deg_to_arrow(r.vento_deg)} {r.vento_kmh} km/h</span>'
        f'{umid}</td>'
    )


def _scr_cell(r: HourlyData | None, bg: str, night_cls_fn) -> str:
    if not r:
        return f'<td class="na" style="background:{bg}">—</td>'
    icon_cls = night_cls_fn(r.icon_class)
    rain = (f'<br><span class="rain">💧{r.rain_mm} mm</span>'
            if r.rain_mm else "")
    prob = (f'<span class="prob"> {r.prec_prob}%</span>'
            if r.prec_prob is not None and r.prec_prob > 0 else "")
    umid = (f' <span class="umid">💦{r.humidity}%</span>'
            if r.humidity is not None else "")
    return (
        f'<td style="background:{bg};font-size:11px;padding:4px 6px;'
        f'text-align:center;vertical-align:middle;border-right:1px solid #ddd;'
        f'white-space:nowrap;width:110px;min-width:110px;max-width:110px">'
        f'<div style="display:flex;justify-content:center;align-items:center">'
        f'{_get_icon_html(icon_cls)}{prob}</div>'
        f'<b>{r.temp}°</b>{rain}<br>'
        f'<span class="wind">{deg_to_arrow(r.vento_deg)} {r.vento_kmh} km/h{umid}</span>'
        f'</td>'
    )


def _ilm_cell(mod, bg: str) -> str:
    rain = (f'<br><span class="rain">💧{mod.rain_mm} mm</span>'
            if mod.rain_mm else "")
    return (
        f'<td style="background:{bg};font-size:11px;padding:4px 6px;'
        f'text-align:center;vertical-align:middle;border-right:1px solid #c5d5ef;'
        f'white-space:nowrap;width:110px;min-width:110px;max-width:110px">'
        f'{_get_icon_html(mod.icon_class)}'
        f'<b>{mod.temp}°</b>{rain}<br>'
        f'<span class="wind">{deg_to_arrow(mod.vento_deg)} {mod.vento_kmh} km/h</span>'
        f'</td>'
    )


def _rain_summary_cell(prob_values: list[int | None]) -> str:
    valid = [v for v in prob_values if v is not None]
    if not valid:
        label, bg, fg = "—", "#f0f0f0", "#999"
    else:
        avg = round(sum(valid) / len(valid))
        if avg >= 60:
            label, bg, fg = f"Yes ({avg}%)",    "#d32f2f", "#fff"
        elif avg >= 40:
            label, bg, fg = f"Maybe ({avg}%)", "#f57c00", "#fff"
        else:
            label, bg, fg = f"No ({avg}%)",    "#388e3c", "#fff"
    n_src = (f'<br><span style="font-size:9px;opacity:.8">{len(valid)} sources</span>'
             if valid else "")
    return (
        f'<td style="background:{bg};color:{fg};font-weight:700;'
        f'font-size:12px;padding:5px 8px;text-align:center;vertical-align:middle;'
        f'white-space:nowrap;width:100px;min-width:100px;border-left:2px solid rgba(0,0,0,.15)">'
        f'{label}{n_src}</td>'
    )


def _temp_avg_cell(all_temps: list[str | None]) -> str:
    avg_t = avg_temp(all_temps)
    try:
        t_num = float(avg_t)
        if   t_num <= 0:  t_bg, t_fg = "#1565c0", "#fff"
        elif t_num <= 10: t_bg, t_fg = "#0288d1", "#fff"
        elif t_num <= 18: t_bg, t_fg = "#2e7d32", "#fff"
        elif t_num <= 25: t_bg, t_fg = "#f57c00", "#fff"
        else:             t_bg, t_fg = "#c62828", "#fff"
    except (ValueError, TypeError):
        t_bg, t_fg = "#90a4ae", "#fff"

    n_valid = len([x for x in all_temps if x and x != "—"])
    n_src   = f'<br><span style="font-size:9px;opacity:.8">{n_valid} sources</span>'
    return (
        f'<td style="background:{t_bg};color:{t_fg};font-weight:700;'
        f'font-size:12px;padding:5px 8px;text-align:center;vertical-align:middle;'
        f'white-space:nowrap;width:100px;min-width:100px;border-left:2px solid rgba(0,0,0,.15)">'
        f'🌡 {avg_t}°{n_src}</td>'
    )


# ── Tbody ─────────────────────────────────────────────────────────────────────

def _build_tbody(
    all_hours:   list[int],
    ilm_idx:     dict[int, IlMeteoHour],
    oecmwf_idx:  dict[int, HourlyData],
    ogfs_idx:    dict[int, HourlyData],
    vc_idx:      dict[int, HourlyData],
    bm_idx:      dict[int, HourlyData],
    mit_idx:     dict[int, HourlyData],
    is_day_map:  dict[int, int],
    n_ilm:       int,
    summary:     bool = False,
) -> str:
    C = _C
    
    # Flags for dynamic column rendering
    show_ilm = bool(ilm_idx) and not summary
    show_ecm = bool(oecmwf_idx) and not summary
    show_gfs = bool(ogfs_idx) and not summary
    show_vc  = bool(vc_idx) and not summary
    show_bm  = bool(bm_idx) and not summary
    show_mit = bool(mit_idx) and not summary

    def night(cls: str, hour: int) -> str:
        if is_day_map.get(hour, 1) == 1:
            return cls
        return to_night_class(cls)

    tbody = ""
    for hour in all_hours:
        row_bg = ' style="background:#f8f9fa"' if hour % 2 == 0 else ""
        tbody += f"<tr{row_bg}>"
        tbody += f'<td class="hour">{hour:02d}:00</td>'

        if show_ilm:
            ilm = ilm_idx.get(hour)
            for i in range(n_ilm):
                if ilm and i < len(ilm.models):
                    tbody += _ilm_cell(ilm.models[i], C["ilm_bg"])
                else:
                    tbody += f'<td class="na" style="background:{C["ilm_bg"]}">—</td>'

        if show_ecm:
            tbody += _api_cell(oecmwf_idx.get(hour), C["oecm_bg"], lambda c, h=hour: night(c, h))
        if show_gfs:
            tbody += _api_cell(ogfs_idx.get(hour),   C["ogfs_bg"], lambda c, h=hour: night(c, h))
        if show_vc:
            tbody += _api_cell(vc_idx.get(hour),     C["vc_bg"],   lambda c, h=hour: night(c, h))
        if show_bm:
            tbody += _scr_cell(bm_idx.get(hour),     C["bm_bg"],   lambda c, h=hour: night(c, h))
        if show_mit:
            tbody += _scr_cell(mit_idx.get(hour),    C["mit_bg"],  lambda c, h=hour: night(c, h))

        # ── Rain? ─────────────────────────────────────────────────────────────
        probs: list[int | None] = []
        ilm = ilm_idx.get(hour)
        if ilm and not summary:
            for mod in ilm.models[:3]:
                p = estimate_prob(HourlyData(
                    hour=hour, icon_class=mod.icon_class,
                    rain_mm=mod.rain_mm, prec_prob=mod.prec_prob,
                ))
                if p is not None:
                    probs.append(p)
        
        for src_dict in [oecmwf_idx, ogfs_idx, vc_idx, bm_idx, mit_idx]:
            if src_dict:
                p = estimate_prob(src_dict.get(hour))
                if p is not None:
                    probs.append(p)
        tbody += _rain_summary_cell(probs)

        # ── Avg Temp ──────────────────────────────────────────────────────────
        temps: list[str | None] = []
        if ilm and not summary:
            temps += [m.temp for m in ilm.models[:3]]

        for src_dict in [oecmwf_idx, ogfs_idx, vc_idx, bm_idx, mit_idx]:
            if src_dict:
                r = src_dict.get(hour)
                if r:
                    temps.append(r.temp)

        tbody += _temp_avg_cell(temps)

        if not summary:
            tbody += (f'<td class="hour" style="border-left:2px solid #ddd; '
                  f'border-right:none">{hour:02d}:00</td>')
        tbody += "</tr>\n"

    return tbody


# ── Header ────────────────────────────────────────────────────────────────────

def _build_header_row2(
    names: list[str], 
    show_ilm: bool, 
    show_ecm: bool, 
    show_gfs: bool
) -> str:
    """Returns the content for the second row of the table header."""
    C = _C
    row2 = ""
    if show_ilm:
        row2 += "".join(
            f'<th style="background:{C["ilm"]};color:#fff;padding:6px 5px;'
            f'font-size:16px;border-right:1px solid #2a5ca0">{n}</th>'
            for n in names
        )
    
    if show_ecm:
        row2 += (f'<th style="background:{C["oecm"]};color:#fff;padding:6px 5px;'
                 f'font-size:16px;border-right:1px solid rgba(255,255,255,.3)">'
                 f'ECMWF IFS<br><span style="font-weight:400;font-size:9px">'
                 f'open-meteo.com</span></th>')
    if show_gfs:
        row2 += (f'<th style="background:{C["ogfs"]};color:#fff;padding:6px 5px;'
                 f'font-size:16px;border-right:1px solid rgba(255,255,255,.3)">'
                 f'GFS<br><span style="font-weight:400;font-size:9px">'
                 f'open-meteo.com</span></th>')
    return row2


# ── Public Entry Point ────────────────────────────────────────────────────────

def build_html(
    day:       str,
    ilm_rows:  list[IlMeteoHour],
    ilm_names: list[str],
    om_ecmwf:  list[HourlyData],
    om_gfs:    list[HourlyData],
    vc_rows:   list[HourlyData],
    bm_rows:   list[HourlyData],
    mit_rows:  list[HourlyData],
    summary:   bool = False,
) -> str:
    now_str   = datetime.now(ROME_TZ).strftime("%d/%m/%Y %H:%M")
    target_dt = target_date(day)
    day_label = {"today": "Today", "tomorrow": "Tomorrow", "day_after_tomorrow": "Day After Tomorrow"}[day]
    day_name  = target_dt.strftime("%A")
    date_str  = target_dt.strftime("%d/%m/%Y")

    def idx(rows): return {r.hour: r for r in rows}

    ilm_idx    = {r.hour: r for r in ilm_rows}
    oecmwf_idx = idx(om_ecmwf)
    ogfs_idx   = idx(om_gfs)
    vc_idx     = idx(vc_rows)
    bm_idx     = idx(bm_rows)
    mit_idx    = idx(mit_rows)

    all_hours = sorted(set(
        list(ilm_idx) + list(oecmwf_idx) + list(ogfs_idx) +
        list(vc_idx)  + list(bm_idx)     + list(mit_idx)
    ))

    is_day_map = {r.hour: r.is_day for r in om_ecmwf}
    if not is_day_map:
        is_day_map = {r.hour: r.is_day for r in om_gfs}

    n_ilm  = 3
    names  = (ilm_names[:3] + ["M1", "M2", "M3"])[:3]
    
    icon_base64 = _load_icon_base64()
    static_css  = _load_static_css()
    sprite_css  = build_sprite_css()
    # Dynamic background for the base sprite class
    dynamic_icon_css = f".s {{ background-image: url('data:image/png;base64,{icon_base64}'); }}"

    C = _C
    hour_hdr = "background:#444;color:#fff;font-size:24px;width:80px"
    
    # Column availability logic
    show_ilm = bool(ilm_rows) and not summary
    show_ecm = bool(om_ecmwf) and not summary
    show_gfs = bool(om_gfs) and not summary
    show_vc  = bool(vc_rows) and not summary
    show_bm  = bool(bm_rows) and not summary
    show_mit = bool(mit_rows) and not summary

    tbody    = _build_tbody(all_hours, ilm_idx, oecmwf_idx, ogfs_idx,
                             vc_idx, bm_idx, mit_idx, is_day_map, n_ilm, summary)
    row2_ths = _build_header_row2(names, show_ilm, show_ecm, show_gfs)
    
    # Construct Row 1 Headers
    h_row1 = f'<th rowspan="2" style="{hour_hdr}">Hour</th>'
    
    if show_ilm:
        h_row1 += (f'<th colspan="{n_ilm}" style="background:{C["ilm"]};color:#fff;'
                   f'font-size:16px;font-weight:700;padding:7px;'
                   f'border-right:3px solid rgba(255,255,255,.3)">'
                   f'ilmeteo.it — Modelli Numerici</th>')
    
    om_colspan = (1 if show_ecm else 0) + (1 if show_gfs else 0)
    if om_colspan > 0:
        h_row1 += (f'<th colspan="{om_colspan}" style="background:{C["oecm"]};color:#fff;'
                   f'font-size:16px;font-weight:700;padding:7px;'
                   f'border-right:1px solid rgba(255,255,255,.3)">OpenMeteo</th>')
                   
    if show_vc:
        h_row1 += (f'<th rowspan="2" style="background:{C["vc"]};color:#fff;font-size:19px;'
                   f'padding:7px;border-right:1px solid rgba(255,255,255,.3)">'
                   f'Visual Crossing<br><span style="font-weight:400;font-size:10px">'
                   f'visualcrossing.com</span></th>')
    if show_bm:
        h_row1 += (f'<th rowspan="2" style="background:{C["bm"]};color:#fff;font-size:19px;'
                   f'padding:7px;border-right:1px solid rgba(255,255,255,.3)">'
                   f'3bMeteo<br><span style="font-weight:400;font-size:10px">'
                   f'scraping</span></th>')
    if show_mit:
        h_row1 += (f'<th rowspan="2" style="background:{C["mit"]};color:#fff;font-size:19px;'
                   f'padding:7px;border-right:3px solid rgba(0,0,0,.2)">'
                   f'meteo.it<br><span style="font-weight:400;font-size:10px">'
                   f'scraping</span></th>')
                   
    h_row1 += (f'<th rowspan="2" style="background:{C["sum"]};color:#fff;font-size:19px;'
               f'padding:7px 10px">🌧 Rain?</th>')
    h_row1 += (f'<th rowspan="2" style="background:#455a64;color:#fff;font-size:19px;'
               f'padding:7px 10px;border-left:2px solid rgba(0,0,0,.2)">🌡 Avg. Temp</th>')
    if not summary:
        h_row1 += f'<th rowspan="2" style="{hour_hdr};border-left:2px solid #ddd">Hour</th>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
{static_css}
{dynamic_icon_css}
{sprite_css}
</style>
</head>
<body>
  <h1>🌦 Weather Comparison Bologna — {day_label}<br>{day_name} {date_str}</h1>
  <div class="sub">
    Generated {now_str} · 44.49°N 11.34°E ·
    Sources: ilmeteo.it · OpenMeteo (ECMWF+GFS) · Visual Crossing · 3bMeteo · meteo.it
  </div>
    <table>
    <thead>
      <tr>
        {h_row1}
      </tr>
      <tr>{row2_ths}</tr>
    </thead>
    <tbody>
{tbody}    </tbody>
  </table>
</body>
</html>"""
