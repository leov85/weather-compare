"""
render/screenshot.py
====================
Converts HTML to PNG using WeasyPrint + Pillow post-processing
(automatic cropping of excess white borders).
"""

from __future__ import annotations
import os
import logging
from pathlib import Path

from PIL import Image, ImageChops

log = logging.getLogger(__name__)


def html_to_png(page_html: str, out_path: str, resolution: int = 150) -> None:
    """
    Renders page_html into a cropped PNG file.

    Parameters
    ----------
    page_html  : complete HTML string
    out_path   : output PNG file path
    resolution : DPI for WeasyPrint (default 150 → good quality for Telegram)
    """
    try:
        from weasyprint import HTML
        HTML(string=page_html).write_png(out_path, resolution=resolution)
        _crop_whitespace(out_path, padding=25)
        if os.path.exists(out_path):
            kb = Path(out_path).stat().st_size // 1024
            log.info("[PNG] %s  (%d KB)", out_path, kb)

    except AttributeError:
        log.error(
            "[html_to_png] WeasyPrint ≥53 does not support write_png. "
            "Install: pip install \"weasyprint<53\""
        )
        raise

    except OSError as e:
        log.error(
            "[html_to_png] System error (GTK3 missing?). "
            "Make sure you have GTK3-Runtime installed and added to PATH. "
            "Detail: %s", e
        )
        raise

    except Exception as e:
        log.error("[html_to_png]: %s", e)
        raise


def _crop_whitespace(path: str, padding: int = 25) -> None:
    """Crops excess white borders from the PNG and overwrites it."""
    try:
        with Image.open(path) as img:
            bg = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "RGBA":
                bg.paste(img, (0, 0), img)
            else:
                bg.paste(img, (0, 0))

            inverted = ImageChops.invert(bg)
            bbox = inverted.point(lambda p: p if p > 40 else 0).getbbox()

            if bbox:
                w, h = img.size
                new_bbox = (
                    max(0, bbox[0] - padding),
                    max(0, bbox[1] - padding),
                    min(w, bbox[2] + padding),
                    min(h, bbox[3] + padding),
                )
                bg.crop(new_bbox).save(path)
    except Exception as e:
        log.warning("[crop_whitespace] %s", e)
