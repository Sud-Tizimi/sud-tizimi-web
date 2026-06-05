"""Formula recognition (LaTeX-OCR) — optional stub.

Reads a mathematical formula from an image and returns its textual form
(LaTeX). Uses ``pix2tex`` if installed; otherwise returns an empty stub.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

_log = logging.getLogger(__name__)

_model = None
_tried = False


@dataclass
class FormulaResult:
    latex: str = ""
    engine: str = "stub"

    def to_dict(self) -> dict:
        return {"latex": self.latex, "engine": self.engine}


def _get_model():
    global _model, _tried
    if _tried:
        return _model
    _tried = True
    try:
        from pix2tex.cli import LatexOCR  # type: ignore

        _model = LatexOCR()
        _log.info("Formula OCR backend: pix2tex")
    except Exception as exc:  # pragma: no cover
        _log.debug("pix2tex unavailable: %s", exc)
        _model = None
    return _model


def is_available() -> bool:
    return _get_model() is not None


def recognize_formula(image_path: str) -> FormulaResult:
    """Recognise a formula image, returning LaTeX (or an empty stub)."""
    model = _get_model()
    if model is None:
        return FormulaResult(latex="", engine="stub")
    try:  # pragma: no cover
        from PIL import Image  # type: ignore

        latex = model(Image.open(image_path))
        return FormulaResult(latex=str(latex), engine="pix2tex")
    except Exception as exc:  # pragma: no cover
        _log.warning("Formula OCR failed: %s", exc)
        return FormulaResult(latex="", engine="stub")
