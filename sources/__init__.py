"""
sources/__init__.py
===================
Exports the fetch functions of all sources with uniform names,
so main.py does not need to know the internal module names.
"""

from sources.ilmeteo         import fetch as fetch_ilmeteo
from sources.openmeteo       import fetch_ecmwf, fetch_gfs
from sources.visual_crossing import fetch as fetch_visual_crossing
from sources.threebmeteo     import fetch as fetch_3bmeteo
from sources.meteoit         import fetch as fetch_meteoit

__all__ = [
    "fetch_ilmeteo",
    "fetch_ecmwf",
    "fetch_gfs",
    "fetch_visual_crossing",
    "fetch_3bmeteo",
    "fetch_meteoit",
]
