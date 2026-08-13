"""Unit regression coverage for the AI document-extraction decision tree."""
from __future__ import annotations

import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, patch

import fitz
from PIL import Image, ImageDraw, ImageFont

from app.services.ai_law.document_loader import (
    DocumentExtractionError,
    ExtractedDocumentText,
    extract_text_for_analysis,
)


def _font() -> ImageFont.FreeTypeFont:
    for candidate in (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, 56)
    raise unittest.SkipTest("a TrueType font is required to build OCR fixtures")


def _text_image(image_format: str) -> bytes:
    image = Image.new("RGB", (1600, 480), "white")
    ImageDraw.Draw(image).multiline_text(
        (60, 60),
        "FAYSAL OCR CLAIM\nDEBT CONTRACT REVIEW\nAMOUNT 1500000 UZS",
        fill="black",
        font=_font(),
        spacing=24,
    )
    data = BytesIO()
    image.save(data, image_format)
    return data.getvalue()


def _text_pdf() -> bytes:
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text(
        (72, 72),
        "Da'vo arizasi qarzdorlikni undirish va shartnoma majburiyati.",
    )
    data = pdf.tobytes()
    pdf.close()
    return data


def _scanned_pdf() -> bytes:
    image_bytes = _text_image("PNG")
    pdf = fitz.open()
    page = pdf.new_page(width=1200, height=420)
    page.insert_image(page.rect, stream=image_bytes)
    data = pdf.tobytes()
    pdf.close()
    return data


class DocumentExtractionDecisionTests(unittest.IsolatedAsyncioTestCase):
    async def _write_and_extract(self, filename: str, content: bytes):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / filename
            path.write_bytes(content)
            return await extract_text_for_analysis(content, path, filename)

    async def test_text_pdf_uses_fast_parser_without_ocr(self) -> None:
        with patch(
            "app.services.ai_law.document_loader._extract_with_local_ocr",
            new_callable=AsyncMock,
        ) as ocr:
            result = await self._write_and_extract("text.pdf", _text_pdf())

        self.assertEqual(result.extraction_method, "text")
        self.assertFalse(result.ocr_used)
        self.assertIn("qarzdorlik", result.text)
        ocr.assert_not_awaited()

    async def test_scanned_pdf_falls_back_to_ocr(self) -> None:
        expected = ExtractedDocumentText(
            "FAYSAL OCR CLAIM DEBT CONTRACT REVIEW AMOUNT 1500000 UZS",
            1,
            "ocr",
            True,
        )
        with patch(
            "app.services.ai_law.document_loader._extract_with_local_ocr",
            new_callable=AsyncMock,
            return_value=expected,
        ) as ocr:
            result = await self._write_and_extract("scanned.pdf", _scanned_pdf())

        self.assertEqual(result, expected)
        ocr.assert_awaited_once()

    async def test_jpg_uses_ocr_not_binary_utf8_decode(self) -> None:
        expected = ExtractedDocumentText("OCR text from JPG document", 1, "ocr", True)
        with patch(
            "app.services.ai_law.document_loader._extract_with_local_ocr",
            new_callable=AsyncMock,
            return_value=expected,
        ) as ocr:
            result = await self._write_and_extract("scan.jpg", _text_image("JPEG"))

        self.assertEqual(result, expected)
        ocr.assert_awaited_once()

    async def test_png_uses_ocr_not_binary_utf8_decode(self) -> None:
        expected = ExtractedDocumentText("OCR text from PNG document", 1, "ocr", True)
        with patch(
            "app.services.ai_law.document_loader._extract_with_local_ocr",
            new_callable=AsyncMock,
            return_value=expected,
        ) as ocr:
            result = await self._write_and_extract("scan.png", _text_image("PNG"))

        self.assertEqual(result, expected)
        ocr.assert_awaited_once()

    async def test_empty_ocr_text_is_controlled_extraction_error(self) -> None:
        with patch(
            "app.services.ai_law.document_loader.process_document",
            new_callable=AsyncMock,
            return_value={"pages": [{"text": ""}]},
        ):
            with self.assertRaisesRegex(DocumentExtractionError, "ocr_text_is_empty"):
                await self._write_and_extract("blank.png", _text_image("PNG"))
