"""PDF parser (handles text + scanned PDFs).

Text PDFs are extracted directly. Scanned pages (no embedded text) are rendered
to PNG and flagged ``needs_ocr`` so the OCR engine can read them. Built on
PyMuPDF; if PyMuPDF is not installed the parser returns an empty result.
"""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from app.services.ocr.parsers.base import BaseParser, ParsedPage, ParseResult, ParsedTable

_log = logging.getLogger(__name__)

try:
    import fitz  # type: ignore  # PyMuPDF

    _HAS_FITZ = True
except Exception:  # pragma: no cover
    _HAS_FITZ = False

_MIN_TEXT_CHARS = 12
_RENDER_DPI = 200


class PdfParser(BaseParser):
    name = "pdf"
    extensions = ("pdf",)

    def parse(self, file_path: str, **kwargs) -> ParseResult:
        if not _HAS_FITZ:
            _log.warning("PyMuPDF not installed; cannot parse PDF %s", file_path)
            return ParseResult(parser=self.name, metadata={"error": "PyMuPDF not installed"})

        render_root = Path(tempfile.mkdtemp(prefix="ocr_pdf_pages_"))

        result = ParseResult(parser=self.name)
        doc = fitz.open(file_path)
        result.metadata = {
            "page_count": doc.page_count,
            "title": doc.metadata.get("title") if doc.metadata else None,
            "author": doc.metadata.get("author") if doc.metadata else None,
        }

        stem = Path(file_path).stem
        for i, page in enumerate(doc):
            text = page.get_text("text").strip()
            rect = page.rect
            parsed = ParsedPage(
                page_number=i + 1,
                text=text,
                width=float(rect.width),
                height=float(rect.height),
            )
            if len(text) < _MIN_TEXT_CHARS:
                parsed.needs_ocr = True
                img_path = render_root / f"{stem}_p{i + 1}.png"
                try:
                    pix = page.get_pixmap(dpi=_RENDER_DPI)
                    pix.save(str(img_path))
                    parsed.image_path = str(img_path)
                except Exception as exc:  # pragma: no cover
                    _log.warning("Failed to render page %d: %s", i + 1, exc)
            else:
                for rows in self._extract_tables(page):
                    result.tables.append(ParsedTable(page_number=i + 1, rows=rows))
                    parsed.blocks.append({"type": "table", "rows": rows})
            result.pages.append(parsed)

        doc.close()
        scanned = sum(1 for p in result.pages if p.needs_ocr)
        _log.info(
            "Parsed PDF %s: %d pages (%d need OCR, %d tables)",
            file_path, result.page_count, scanned, len(result.tables),
        )
        return result

    @staticmethod
    def _extract_tables(page) -> list[list[list[str]]]:
        """Extract tables from a text page using PyMuPDF's table finder."""
        out: list[list[list[str]]] = []
        try:
            finder = page.find_tables()
        except Exception:  # pragma: no cover
            return out
        for tbl in getattr(finder, "tables", []):
            try:
                rows = tbl.extract()
            except Exception:  # pragma: no cover
                continue
            clean = [["" if c is None else str(c).strip() for c in row] for row in rows]
            clean = [r for r in clean if any(c for c in r)]
            if len(clean) >= 1:
                out.append(clean)
        return out


pdf_parser = PdfParser()
