"""Parser registry — dispatch a file to the right parser by extension."""
from __future__ import annotations

import logging

from app.services.ocr.parsers.base import BaseParser, ParseResult
from app.services.ocr.parsers.docx_parser import docx_parser
from app.services.ocr.parsers.image_parser import image_parser
from app.services.ocr.parsers.pdf_parser import pdf_parser
from app.services.ocr.parsers.pptx_parser import pptx_parser
from app.services.ocr.parsers.text_parser import text_parser
from app.services.ocr.parsers.xlsx_parser import xlsx_parser

_log = logging.getLogger(__name__)

_REGISTRY: dict[str, BaseParser] = {}


def register(parser: BaseParser) -> None:
    for ext in parser.extensions:
        _REGISTRY[ext] = parser


register(pdf_parser)
register(image_parser)
register(docx_parser)
register(xlsx_parser)
register(pptx_parser)
register(text_parser)


def get_parser(extension: str) -> BaseParser | None:
    return _REGISTRY.get(extension.lower().lstrip("."))


def supported_extensions() -> list[str]:
    return sorted(_REGISTRY.keys())


def parse_file(file_path: str, extension: str, **kwargs) -> ParseResult:
    """Parse a file with the parser registered for ``extension``."""
    parser = get_parser(extension)
    if parser is None:
        _log.warning("No parser registered for .%s", extension)
        return ParseResult(parser="none", metadata={"error": f"unsupported: {extension}"})
    return parser.parse(file_path, **kwargs)
