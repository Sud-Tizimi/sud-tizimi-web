"""Word parser (DOCX).

Extracts text, headings, tables and image counts while preserving document
order (paragraphs and tables interleaved as they appear).
"""
from __future__ import annotations

import logging

from app.services.ocr.parsers.base import BaseParser, ParsedPage, ParseResult, ParsedTable

_log = logging.getLogger(__name__)

try:
    import docx  # type: ignore
    from docx.oxml.ns import qn
    from docx.table import Table as _DocxTable
    from docx.text.paragraph import Paragraph as _DocxParagraph

    _HAS_DOCX = True
except Exception:  # pragma: no cover
    _HAS_DOCX = False


def _iter_block_items(parent):
    """Yield paragraphs and tables in the order they appear in the document."""
    body = parent.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield _DocxParagraph(child, parent)
        elif child.tag == qn("w:tbl"):
            yield _DocxTable(child, parent)


class DocxParser(BaseParser):
    name = "docx"
    extensions = ("docx",)

    def parse(self, file_path: str, **kwargs) -> ParseResult:
        if not _HAS_DOCX:
            return ParseResult(parser=self.name, metadata={"error": "python-docx not installed"})

        document = docx.Document(file_path)
        lines: list[str] = []
        blocks: list[dict] = []
        tables: list[ParsedTable] = []

        for item in _iter_block_items(document):
            if isinstance(item, _DocxParagraph):
                text = item.text.strip()
                if not text:
                    continue
                style = (item.style.name or "").lower() if item.style else ""
                is_heading = style.startswith("heading") or style == "title"
                blocks.append({"type": "heading" if is_heading else "text", "text": text})
                lines.append(("# " if is_heading else "") + text)
            elif isinstance(item, _DocxTable):
                rows = [[cell.text.strip() for cell in row.cells] for row in item.rows]
                if rows:
                    tables.append(ParsedTable(page_number=1, rows=rows))
                    blocks.append({"type": "table", "rows": rows})
                    lines.extend("\t".join(r) for r in rows)

        image_count = sum(
            1 for rel in document.part.rels.values() if "image" in rel.reltype
        )

        page = ParsedPage(page_number=1, text="\n".join(lines), blocks=blocks)
        meta = {
            "page_count": 1,
            "paragraphs": sum(1 for b in blocks if b["type"] in ("text", "heading")),
            "tables": len(tables),
            "images": image_count,
        }
        try:
            props = document.core_properties
            meta.update({k: v for k, v in {
                "title": props.title, "author": props.author,
                "subject": props.subject,
            }.items() if v})
        except Exception:  # pragma: no cover
            pass

        _log.info("Parsed DOCX %s: %d blocks, %d tables", file_path, len(blocks), len(tables))
        return ParseResult(parser=self.name, pages=[page], tables=tables, metadata=meta)


docx_parser = DocxParser()
