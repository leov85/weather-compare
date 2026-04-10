"""
icons.py
========
Static weather icon maps: CSS sprite codes, WMO codes, meteo.it codes.
Isolated here to keep config.py clean from static data.

NOTE: The strings in THREEBMETEO_ALT_TO_CLASS and the Italian abbreviations
in WIND_DIR_TO_DEG (SSO, SO, OSO, etc.) must remain in Italian because they
are matched against scraped content from the 3bmeteo.com website.
"""

SIMBOLI_METEO: dict[str, str] = {
    "ss1":   "Sunny",            "ss2":   "Strong Sun",
    "ss3":   "Partly Cloudy",    "ss4":   "Cloudy",
    "ss4b":  "Very Cloudy",      "ss5":   "Rain and Sun",
    "ss6":   "Drizzle",          "ss7":   "Snow and Sun",
    "ss8":   "Cloudy",           "ss9":   "Light Rain",
    "ss10":  "Rain",             "ss11":  "Snow",
    "ss12":  "Mixed Rain/Snow",  "ss13":  "Thunderstorm",
    "ss14":  "Fog",              "ss15":  "Foggy with Sun",
    "ss16":  "Thunderstorm with Sun", "ss17": "Hail",
    "ss18":  "Snow",             "ss19":  "Night Showers",
    "ss20":  "Showers with Sun", "ss21":  "Showers",
    "ss101": "Clear",            "ss102": "Clear",
    "ss103": "Partly Cloudy",    "ss104": "Cloudy",
    "ss104b":"Very Cloudy",      "ss105": "Rain",
    "ss106": "Mixed Rain/Snow",  "ss107": "Snow",
    "ss108": "Cloudy",           "ss109": "Light Rain",
    "ss110": "Rain",             "ss111": "Snow",
    "ss112": "Mixed Rain/Snow",  "ss113": "Thunderstorm",
}

# WMO codes → CSS sprite class
WMO_ICON: dict[int, str] = {
    0: "ss1",  1: "ss3",  2: "ss4",  3: "ss8",
    45: "ss14", 48: "ss14",
    51: "ss9",  53: "ss9",  55: "ss10",
    61: "ss9",  63: "ss10", 65: "ss10",
    71: "ss11", 73: "ss11", 75: "ss11",
    80: "ss5",  81: "ss5",  82: "ss5",
    95: "ss13", 96: "ss13", 99: "ss13",
}

# meteo.it forecast codes → CSS sprite class
METEOIT_PREVISION_CODE_MAP: dict[int, str] = {
    1: "ss8",   2: "ss101", 5: "ss1",   7: "ss11",
    10: "ss4",  11: "ss104", 12: "ss109", 15: "ss9",
    18: "ss9",  21: "ss3",  22: "ss103", 23: "ss13",
    25: "ss13", 26: "ss4",  27: "ss104", 28: "ss8",
    30: "ss11", 33: "ss9",  36: "ss13",
}

# Night icon mapping (day → night)
NIGHT_MAP: dict[str, str] = {
    "ss1":  "ss101", "ss2":  "ss102", "ss3":  "ss103",
    "ss4":  "ss104", "ss4b": "ss104b","ss5":  "ss105",
    "ss6":  "ss106", "ss7":  "ss107", "ss8":  "ss108",
    "ss9":  "ss109", "ss10": "ss110", "ss11": "ss111",
    "ss12": "ss112", "ss13": "ss113", "ss14": "ss114",
}


def to_night_class(cls: str) -> str:
    """Returns the night variant of a sprite class (if is_day == 0)."""
    if not cls or not cls.startswith("ss"):
        return cls
    return NIGHT_MAP.get(cls, cls)


# 3bmeteo alt text → CSS sprite class
# Keys MUST remain in Italian: they are matched against scraped alt attributes
# from www.3bmeteo.com, which is an Italian-language website.
THREEBMETEO_ALT_TO_CLASS: dict[str, str] = {
    "sereno":           "ss1",
    "poco nuvoloso":    "ss3",
    "nuvoloso":         "ss8",
    "coperto":          "ss8",
    "pioggia":          "ss10",
    "pioviggine":       "ss9",
    "temporale":        "ss13",
    "neve":             "ss11",
    "nebbia":           "ss14",
    "nubi sparse":      "ss3",
    "velature sparse":  "ss3",
    "velature lievi":   "ss3",
    "velature estese":  "ss3",
    "parz nuvoloso":    "ss3",
    "pioggia e schiarite": "ss5",
    "nubi basse":         "ss14",
    "nubi basse e schiarite": "ss14",
}

# Wind directions → degrees
# Standard international abbreviations (N, NE, E, SE, S, SW, W, NW …)
# plus Italian abbreviations used by 3bmeteo (SSO, SO, OSO, O, ONO, NO, NNO)
# — the Italian ones MUST stay as-is to match scraped content.
WIND_DIR_TO_DEG: dict[str, int] = {
    "N": 0,   "NNE": 22,  "NE": 45,  "ENE": 67,
    "E": 90,  "ESE": 112, "SE": 135, "SSE": 157,
    "S": 180, "SSW": 202, "SW": 225, "WSW": 247,
    "W": 270, "WNW": 292, "NW": 315, "NNW": 337,
    # Italian abbreviations scraped from 3bmeteo — do not translate
    "SSO": 202, "SO": 225, "OSO": 247, "O": 270,
    "ONO": 292, "NO": 315, "NNO": 337,
}

# CSS sprite: class → background-position
SPRITE_CSS: dict[str, str] = {
    "ss1":   "0 0",          "ss2":   "-34px 0",
    "ss3":   "-70px 0",      "ss4":   "-104px 0",
    "ss4b":  "-139px 0",     "ss5":   "-173px 0",
    "ss6":   "-208px 0",     "ss7":   "-242px 0",
    "ss8":   "-277px 0",     "ss9":   "-311px 0",
    "ss10":  "-346px 0",     "ss11":  "-381px 0",
    "ss12":  "-415px 0",     "ss13":  "-450px 0",
    "ss14":  "-484px 0",     "ss15":  "-519px 0",
    "ss16":  "-554px 0",     "ss17":  "-588px 0",
    "ss18":  "-623px 0",     "ss19":  "-262px -34px",
    "ss20":  "-296px -34px", "ss21":  "-332px -34px",
    "ss22":  "-366px -34px", "ss23":  "-400px -34px",
    "ss24":  "-434px -34px",
    "ss101": "-658px 0",     "ss102": "-692px 0",
    "ss103": "-727px 0",     "ss104": "-761px 0",
    "ss104b":"-796px 0",     "ss105": "-830px 0",
    "ss106": "-865px 0",     "ss107": "-899px 0",
    "ss108": "-934px 0",     "ss109": "-968px 0",
    "ss110": "-1003px 0",    "ss111": "-1037px 0",
    "ss112": "-1072px 0",    "ss113": "-1106px 0",
}


def build_sprite_css() -> str:
    """Generates CSS sprite rules based on SPRITE_CSS."""
    return "\n".join(
        f"  .{cls}{{background-position:{pos}}}"
        for cls, pos in SPRITE_CSS.items()
    )
