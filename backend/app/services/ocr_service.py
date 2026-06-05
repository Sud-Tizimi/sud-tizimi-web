"""Async-friendly facade for the OCR engine.

The underlying engine is synchronous (pytesseract / paddle / httpx). We wrap
recognize() with ``asyncio.to_thread`` so the FastAPI event loop stays free.
"""
from __future__ import annotations

import asyncio
from typing import Iterable

from app.services.ocr.engine import ocr_engine
from app.services.ocr.parsers import parse_file


async def recognize_image(image_path: str, lang: str | None = None) -> dict:
    """Run OCR on a single image and return the result dict."""
    out = await asyncio.to_thread(ocr_engine.recognize, image_path, lang=lang)
    return out.to_dict()


async def process_document(file_path: str, extension: str, lang: str | None = None) -> dict:
    """Parse + OCR a multi-page document. Returns a dict with per-page OCR output.

    Text pages get their embedded text back; scanned pages get OCR'd.
    """
    parsed = await asyncio.to_thread(parse_file, file_path, extension)
    lang = lang or None
    pages_out: list[dict] = []
    for page in parsed.pages:
        if not page.needs_ocr and page.text:
            pages_out.append({
                "text": page.text,
                "boxes": [],
                "confidence": 1.0,
                "engine": "embedded",
                "lang": lang,
                "page_number": page.page_number,
            })
            continue
        # OCR path
        target = page.image_path or file_path
        ocr = await asyncio.to_thread(ocr_engine.recognize, target, lang=lang)
        pages_out.append({
            "text": ocr.text,
            "boxes": ocr.boxes,
            "confidence": ocr.confidence,
            "engine": ocr.engine,
            "lang": ocr.lang,
            "page_number": page.page_number,
        })
    return {
        "pages": pages_out,
        "parser": parsed.parser,
        "metadata": parsed.metadata,
    }


def engine_status() -> dict:
    return {
        "real_engine": ocr_engine.is_real,
        "active_engine": ocr_engine.active_engine,
    }


def supported_extensions() -> Iterable[str]:
    from app.services.ocr.parsers.registry import supported_extensions
    return supported_extensions()
