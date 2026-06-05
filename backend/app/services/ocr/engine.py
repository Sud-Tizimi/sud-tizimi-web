"""OCR engine — PaddleOCR / Tesseract / Gemini / Stub.

Three backends are tried in priority order so the platform works in as many
environments as possible:

    1. Gemini       (cloud; needs ``GEMINI_API_KEY``)
    2. PaddleOCR    (best quality; TZ-recommended; heavy install)
    3. Tesseract    (via pytesseract; common, lighter)
    4. Stub         (always available; returns an explicit "not installed" note)

The backend is selected once, lazily, on first use. Output is normalised to a
single shape regardless of backend:

    {"text": str, "boxes": [{"text","bbox":[x1,y1,x2,y2],"confidence"}], "confidence": float}

Boxes are normalised 0..1 so they map onto any rendering of the same image.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from app.config import get_settings
from app.services.ocr.preprocess import preprocess_image

_log = logging.getLogger(__name__)

# Cached settings proxy — engine is long-lived; _settings.ocr_provider can
# change at runtime via the admin/runtime layer.
_settings = get_settings()


@dataclass
class OcrOutput:
    text: str = ""
    boxes: list[dict] = field(default_factory=list)
    confidence: float = 0.0
    engine: str = "stub"
    lang: str | None = None

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "boxes": self.boxes,
            "confidence": self.confidence,
            "engine": self.engine,
            "lang": self.lang,
        }


class _PaddleBackend:
    name = "paddleocr"

    def __init__(self, lang: str) -> None:
        from paddleocr import PaddleOCR  # type: ignore

        self.lang = lang
        self._ocr = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)

    def run(self, image_path: str) -> OcrOutput:
        raw = self._ocr.ocr(image_path, cls=True)
        boxes: list[dict] = []
        texts: list[str] = []
        confs: list[float] = []
        for page in raw or []:
            for line in page or []:
                box, (text, conf) = line[0], line[1]
                xs = [p[0] for p in box]
                ys = [p[1] for p in box]
                bbox = [min(xs), min(ys), max(xs), max(ys)]
                if conf >= _settings.ocr_min_confidence:
                    boxes.append({"text": text, "bbox": bbox, "confidence": float(conf)})
                    texts.append(text)
                    confs.append(float(conf))
        return OcrOutput(
            text="\n".join(texts),
            boxes=boxes,
            confidence=(sum(confs) / len(confs)) if confs else 0.0,
            engine=self.name,
            lang=self.lang,
        )


_TESSERACT_PATHS = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    "/usr/bin/tesseract",
    "/opt/homebrew/bin/tesseract",
    "/usr/local/bin/tesseract",
)
_TESS_LANG_MAP = {"en": "eng", "ru": "rus", "uz": "uzb", "ch": "chi_sim"}


def _resolve_tess_lang(lang: str) -> str:
    """Allow 'uzb+rus+eng' (pass-through) or short codes like 'en' -> 'eng'."""
    if "+" in lang or len(lang) > 3:
        return lang
    return _TESS_LANG_MAP.get(lang, lang)


class _TesseractBackend:
    name = "tesseract"

    def __init__(self, lang: str) -> None:
        import pytesseract  # type: ignore

        cmd = _settings.tesseract_cmd
        if not cmd:
            cmd = next((p for p in _TESSERACT_PATHS if os.path.exists(p)), None)
        if cmd:
            pytesseract.pytesseract.tesseract_cmd = cmd

        if _settings.tessdata_dir:
            os.environ["TESSDATA_PREFIX"] = _settings.tessdata_dir

        pytesseract.get_tesseract_version()

        self.lang = _resolve_tess_lang(lang)
        self._pt = pytesseract
        self._config = ""

    def run(self, image_path: str) -> OcrOutput:
        """Run several OCR variants and keep the best.

        Printed text reads best from the original image (PSM 3); handwriting and
        faint scans read better from an Otsu-binarised, upscaled image (PSM 6).
        We try both and pick whichever recognises more text with high confidence,
        so each image automatically gets the treatment that suits it.
        """
        from PIL import Image  # type: ignore

        base = Image.open(image_path)
        candidates: list[tuple] = [(base, 3)]
        binarized = self._binarize(image_path)
        if binarized is not None:
            candidates.append((binarized, 6))
        handwriting = self._enhance_handwriting(image_path)
        if handwriting is not None:
            candidates.append((handwriting, 11))

        best: OcrOutput | None = None
        best_score = -1.0
        for img, psm in candidates:
            out = self._ocr_image(img, psm)
            score = sum(b["confidence"] for b in out.boxes)
            if score > best_score:
                best_score, best = score, out
        return best or OcrOutput(engine=self.name, lang=self.lang)

    def _ocr_image(self, img, psm: int) -> OcrOutput:
        iw, ih = img.size
        iw = max(iw, 1)
        ih = max(ih, 1)
        data = self._pt.image_to_data(
            img, lang=self.lang, config=f"--psm {psm}",
            output_type=self._pt.Output.DICT,
        )
        boxes: list[dict] = []
        texts: list[str] = []
        confs: list[float] = []
        n = len(data.get("text", []))
        for i in range(n):
            text = (data["text"][i] or "").strip()
            conf = float(data["conf"][i]) / 100.0 if data["conf"][i] not in ("-1", -1) else 0.0
            if text and conf >= _settings.ocr_min_confidence:
                x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                boxes.append({
                    "text": text,
                    "bbox": [round(x / iw, 4), round(y / ih, 4),
                             round((x + w) / iw, 4), round((y + h) / ih, 4)],
                    "confidence": round(conf, 4),
                })
                texts.append(text)
                confs.append(conf)
        return OcrOutput(
            text=" ".join(texts),
            boxes=boxes,
            confidence=(sum(confs) / len(confs)) if confs else 0.0,
            engine=self.name,
            lang=self.lang,
        )

    @staticmethod
    def _binarize(image_path: str):
        try:
            import cv2  # type: ignore
            from PIL import Image  # type: ignore

            img = cv2.imread(image_path)
            if img is None:
                return None
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape[:2]
            longest = max(h, w)
            if longest < 1900:
                s = 1900 / max(longest, 1)
                gray = cv2.resize(gray, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC)
            _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return Image.fromarray(th)
        except Exception:  # pragma: no cover
            return None

    @staticmethod
    def _enhance_handwriting(image_path: str):
        try:
            import cv2  # type: ignore
            import numpy as np  # type: ignore
            from PIL import Image  # type: ignore

            img = cv2.imread(image_path)
            if img is None:
                return None
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            longest = max(gray.shape[:2])
            if longest < 2200:
                s = 2200 / max(longest, 1)
                gray = cv2.resize(gray, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC)
            gray = cv2.fastNlMeansDenoising(gray, h=7)
            sharp = cv2.filter2D(gray, -1, np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]]))
            return Image.fromarray(sharp)
        except Exception:  # pragma: no cover
            return None


class _GeminiBackend:
    """Google AI Studio (Gemini) OCR — best for handwriting. Per-word boxes."""

    name = "gemini"
    wants_preprocess = False

    def __init__(self, lang: str, cfg: dict) -> None:
        from app.services.ocr import gemini as _g

        if not _g.is_configured(cfg):
            raise RuntimeError("Gemini not configured")
        self.lang = lang
        self._g = _g
        self._key = cfg["gemini_api_key"]
        self._model = cfg["gemini_model"]

    def run(self, image_path: str) -> OcrOutput:
        out = self._g.recognize(image_path, api_key=self._key, model=self._model, lang=self.lang)
        return OcrOutput(
            text=out["text"],
            boxes=out["boxes"],
            confidence=out["confidence"],
            engine=out["engine"],
            lang=out["lang"],
        )


class _StubBackend:
    name = "stub"

    def __init__(self, lang: str) -> None:
        self.lang = lang

    def run(self, image_path: str) -> OcrOutput:
        _log.warning(
            "No OCR backend installed — returning stub. "
            "Install 'paddleocr' or 'pytesseract'+Tesseract, or set GEMINI_API_KEY for real OCR."
        )
        return OcrOutput(text="", boxes=[], confidence=0.0, engine=self.name, lang=self.lang)


def _build_backend(lang: str, cfg: dict):
    """Pick the OCR backend: Gemini if configured, else local engines."""
    if cfg.get("ocr_provider") == "gemini" and cfg.get("gemini_api_key"):
        try:
            backend = _GeminiBackend(lang, cfg)
            _log.info("OCR backend: gemini (model=%s)", cfg.get("gemini_model"))
            return backend
        except Exception as exc:
            _log.warning("Gemini backend unavailable, falling back to local: %s", exc)
    for builder in (_PaddleBackend, _TesseractBackend):
        try:
            backend = builder(lang)
            _log.info("OCR backend: %s (lang=%s)", backend.name, lang)
            return backend
        except Exception as exc:
            _log.debug("OCR backend %s unavailable: %s", builder.name, exc)
    _log.info("OCR backend: stub (no real engine installed)")
    return _StubBackend(lang)


class OcrEngine:
    """Public OCR facade."""

    def __init__(self) -> None:
        self._backends: dict[str, object] = {}

    def _current_backend(self, lang: str):
        provider = _settings.ocr_provider
        # "auto" — use Gemini only if its key is configured
        if provider == "auto":
            effective = "gemini" if _settings.gemini_api_key else "tesseract"
        else:
            effective = provider
        cfg = {
            "ocr_provider": effective,
            "gemini_api_key": _settings.gemini_api_key,
            "gemini_model": _settings.ocr_gemini_model,
        }
        if lang not in self._backends:
            self._backends[lang] = _build_backend(lang, cfg)
        return self._backends[lang]

    def recognize(
        self,
        image_path: str | Path,
        *,
        lang: str | None = None,
        preprocess: bool = True,
    ) -> OcrOutput:
        """Recognise text in a single image."""
        lang = lang or _settings.ocr_lang
        backend = self._current_backend(lang)
        path = str(image_path)
        if preprocess and getattr(backend, "wants_preprocess", True):
            path = preprocess_image(path)
        try:
            return backend.run(path)
        except Exception as exc:  # pragma: no cover
            _log.error("OCR run failed on %s: %s", path, exc)
            return OcrOutput(engine=getattr(backend, "name", "stub"), lang=lang)

    @property
    def is_real(self) -> bool:
        """True if a real (non-stub) backend is active for the default lang."""
        return not isinstance(self._current_backend(_settings.ocr_lang), _StubBackend)

    @property
    def active_engine(self) -> str:
        return getattr(self._current_backend(_settings.ocr_lang), "name", "stub")


ocr_engine = OcrEngine()
