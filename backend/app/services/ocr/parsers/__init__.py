"""Document parsers (PDF / DOCX / XLSX / PPTX / Image / Text)."""
from app.services.ocr.parsers.registry import parse_file, supported_extensions, get_parser

__all__ = ["parse_file", "supported_extensions", "get_parser"]
