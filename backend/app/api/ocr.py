"""OCR endpoints — file upload (multipart) and direct image.

No auth required for OCR — it's a utility (Phase D MVP). Engine status is
read-only and safe to expose.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.api.schemas.ocr import (
    OcrBox,
    OcrEngineStatus,
    OcrProcessResponse,
    OcrResultOut,
)
from app.services import ocr_service

router = APIRouter(prefix="/ocr", tags=["ocr"])

_ALLOWED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}
_MAX_BYTES = 50 * 1024 * 1024  # 50 MB — slightly above document-upload cap


def _to_ocr_result(payload: dict, page_number: int = 1) -> OcrResultOut:
    return OcrResultOut(
        text=payload.get("text", ""),
        boxes=[OcrBox(**b) for b in payload.get("boxes", []) if isinstance(b, dict)],
        confidence=float(payload.get("confidence", 0.0)),
        engine=payload.get("engine", "stub"),
        lang=payload.get("lang"),
        page_number=payload.get("page_number", page_number),
    )


@router.get("/engine", response_model=OcrEngineStatus, summary="OCR backend status")
async def get_engine_status() -> OcrEngineStatus:
    status = ocr_service.engine_status()
    return OcrEngineStatus(
        real_engine=status["real_engine"],
        active_engine=status["active_engine"],
    )


@router.post(
    "/image",
    response_model=OcrResultOut,
    summary="OCR a single image (no persistence)",
)
async def ocr_image(
    file: UploadFile = File(...),
    lang: str | None = Form(None),
) -> OcrResultOut:
    """Run OCR on a directly-uploaded image and return text + boxes inline."""
    name = file.filename or "image"
    suffix = Path(name).suffix.lower() or ".png"
    if suffix not in _ALLOWED_IMAGE_EXT:
        raise HTTPException(
            status_code=415,
            detail=f"Only image files are accepted ({sorted(_ALLOWED_IMAGE_EXT)})",
        )

    data = await file.read()
    if len(data) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds {_MAX_BYTES // (1024*1024)} MB")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        out = await ocr_service.recognize_image(tmp_path, lang=lang)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return _to_ocr_result(out)


@router.post(
    "/process",
    response_model=OcrProcessResponse,
    summary="Parse + OCR a multi-page document (PDF, DOCX, XLSX, PPTX, image, text)",
)
async def ocr_process(
    file: UploadFile = File(...),
    lang: str | None = Form(None),
) -> OcrProcessResponse:
    name = file.filename or "document"
    ext = Path(name).suffix.lower().lstrip(".")
    if not ext or ext not in set(ocr_service.supported_extensions()):
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported extension '.{ext}'. Supported: {sorted(ocr_service.supported_extensions())}",
        )

    data = await file.read()
    if len(data) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds {_MAX_BYTES // (1024*1024)} MB")

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        result = await ocr_service.process_document(tmp_path, ext, lang=lang)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return OcrProcessResponse(
        pages=[_to_ocr_result(p, page_number=p.get("page_number", i + 1)) for i, p in enumerate(result["pages"])],
        parser=result["parser"],
        metadata=result["metadata"],
    )
