"""Image pre-processing for OCR (gentle upscale for small images).

Graceful degradation: if OpenCV/NumPy are missing, the source path is
returned unchanged so the pipeline never breaks. Heavy preprocessing
(binarisation, deskew) is intentionally avoided — tests showed it hurts
accuracy on clean/digital scans.
"""
from __future__ import annotations

import logging
from pathlib import Path

_log = logging.getLogger(__name__)

try:
    import cv2  # type: ignore
    import numpy as np  # type: ignore

    _HAS_CV2 = True
except Exception:  # pragma: no cover - optional dependency
    _HAS_CV2 = False


def available() -> bool:
    return _HAS_CV2


# Below this longest-side size (px) text is too small; upscale helps OCR.
_MIN_LONG_SIDE = 1500
_TARGET_LONG_SIDE = 1800


def preprocess_image(src_path: str | Path, out_path: str | Path | None = None) -> str:
    """Return a path to an image tuned for OCR.

    Strategy:
      * Large, already-crisp images  -> used as-is (best results).
      * Small images                 -> upscaled (Tesseract reads big text
                                        far better than tiny text).

    If OpenCV is unavailable the source path is returned untouched.
    """
    src_path = Path(src_path)
    if not _HAS_CV2:
        return str(src_path)

    try:
        img = cv2.imread(str(src_path))
        if img is None:
            return str(src_path)

        h, w = img.shape[:2]
        longest = max(h, w)
        if longest >= _MIN_LONG_SIDE:
            # Clean / high-res image: leave it alone — preprocessing only hurts.
            return str(src_path)

        # Small image: upscale (cubic) and grayscale to help recognition.
        scale = _TARGET_LONG_SIDE / max(longest, 1)
        up = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(up, cv2.COLOR_BGR2GRAY)

        out = Path(out_path) if out_path else src_path.with_name(src_path.stem + "_pre.png")
        cv2.imwrite(str(out), gray)
        return str(out)
    except Exception as exc:  # pragma: no cover
        _log.warning("Preprocess failed (%s); using original image", exc)
        return str(src_path)
