"""CP2 — OCR & document text extraction. Stub."""


class OCRService:
    """Photo/document -> plain text, then attached to the case."""

    async def extract_text(self, file_path: str) -> str:
        raise NotImplementedError("CP2: OCRService.extract_text not implemented yet")
