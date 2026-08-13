"""Regression coverage for the Case → Documents → Submit flow.

The full HTTP/MySQL test is opt-in because this repository has no isolated
test database configuration. It creates uniquely named users/cases, uses a
temporary storage root, and removes every row/file it owns in teardown.
Run it explicitly with ``FAYSAL_RUN_DB_INTEGRATION=1``.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import shutil
import tempfile
import unittest
import uuid
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.config import get_settings
from app.core.enums import UserRole
from app.core.security import hash_password
from app.db.models.case import Case
from app.db.models.ai_analysis import AIAnalysis
from app.db.models.document import Document
from app.db.models.user import User
from app.main import app
from app.services import document_service
from app.services.ocr import engine as ocr_engine_module


class _ChunkedUpload:
    def __init__(self, filename: str, chunks: list[bytes]) -> None:
        self.filename = filename
        self._chunks = iter(chunks)

    async def read(self, _: int = -1) -> bytes:
        return next(self._chunks, b"")


class _FailingWriter:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    async def write(self, _: bytes) -> None:
        raise OSError("simulated_storage_write_failure")


class _RecordingSession:
    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, item: object) -> None:
        self.added.append(item)

    async def flush(self) -> None:
        return None


class DocumentStorageRegressionTests(unittest.IsolatedAsyncioTestCase):
    async def test_write_error_leaves_no_document_or_partial_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "broken.pdf"
            session = _RecordingSession()
            upload = _ChunkedUpload("broken.pdf", [b"partial bytes"])
            actor = SimpleNamespace(id="assistant-1", role=UserRole.ASSISTANT)

            with (
                patch.object(document_service, "build_storage_path", return_value=destination),
                patch.object(document_service.aiofiles, "open", return_value=_FailingWriter()),
                self.assertRaisesRegex(OSError, "simulated_storage_write_failure"),
            ):
                await document_service.upload_document(
                    session, actor=actor, file=upload, case_id=None
                )

            self.assertEqual(session.added, [])
            self.assertFalse(destination.exists())
            self.assertEqual(list(Path(temp_dir).iterdir()), [])

    async def test_oversized_stream_leaves_no_partial_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "too-large.pdf"
            upload = _ChunkedUpload("too-large.pdf", [b"123", b"456"])

            with self.assertRaises(HTTPException) as raised:
                await document_service._read_into_storage(upload, destination, max_bytes=5)

            self.assertEqual(raised.exception.status_code, 413)
            self.assertFalse(destination.exists())
            self.assertEqual(list(Path(temp_dir).iterdir()), [])


@unittest.skipUnless(
    os.getenv("FAYSAL_RUN_DB_INTEGRATION") == "1",
    "requires a disposable local MySQL database; set FAYSAL_RUN_DB_INTEGRATION=1",
)
class CaseDocumentSubmitIntegrationTests(unittest.TestCase):
    """Real API + MySQL + storage regression for PDF/DOCX/JPG uploads."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.run_id = uuid.uuid4().hex
        cls.assistant_id = str(uuid.uuid4())
        cls.judge_id = str(uuid.uuid4())
        cls.assistant_email = f"e2e-assistant-{cls.run_id}@example.com"
        cls.judge_email = f"e2e-judge-{cls.run_id}@example.com"
        cls.password = "integration-password-123"
        cls.storage_root = tempfile.mkdtemp(prefix="faysal-upload-e2e-")
        cls.previous_storage_root = os.environ.get("STORAGE_ROOT")
        cls.previous_ocr_lang = os.environ.get("OCR_LANG")
        cls.previous_ocr_provider = os.environ.get("OCR_PROVIDER")
        os.environ["STORAGE_ROOT"] = cls.storage_root
        # The local developer image has the English traineddata pack.  The
        # production default remains configurable as uzb+rus+eng.
        os.environ["OCR_LANG"] = "eng"
        os.environ["OCR_PROVIDER"] = "tesseract"
        cls.previous_engine_lang = ocr_engine_module._settings.ocr_lang
        cls.previous_engine_provider = ocr_engine_module._settings.ocr_provider
        ocr_engine_module._settings.ocr_lang = "eng"
        ocr_engine_module._settings.ocr_provider = "tesseract"
        ocr_engine_module.ocr_engine._backends.clear()
        get_settings.cache_clear()
        asyncio.run(cls._provision_users())
        cls.client = TestClient(app)
        cls.client.__enter__()

    @classmethod
    async def _provision_users(cls) -> None:
        engine = create_async_engine(get_settings().database_url)
        try:
            async with AsyncSession(engine) as session:
                session.add_all(
                    [
                        User(
                            id=cls.assistant_id,
                            email=cls.assistant_email,
                            full_name="E2E Assistant",
                            hashed_password=hash_password(cls.password),
                            role=UserRole.ASSISTANT,
                            court=None,
                        ),
                        User(
                            id=cls.judge_id,
                            email=cls.judge_email,
                            full_name="E2E Judge",
                            hashed_password=hash_password(cls.password),
                            role=UserRole.JUDGE,
                            court="E2E Court",
                        ),
                    ]
                )
                await session.commit()
        finally:
            await engine.dispose()

    @classmethod
    async def _cleanup_database(cls) -> None:
        engine = create_async_engine(get_settings().database_url)
        try:
            async with AsyncSession(engine) as session:
                case_rows = await session.execute(
                    select(Case.id).where(
                        (Case.assistant_id == cls.assistant_id)
                        | (Case.assigned_judge_id == cls.judge_id)
                    )
                )
                case_ids = list(case_rows.scalars())
                if case_ids:
                    await session.execute(delete(Document).where(Document.case_id.in_(case_ids)))
                    await session.execute(delete(Case).where(Case.id.in_(case_ids)))
                await session.execute(
                    delete(User).where(User.id.in_([cls.assistant_id, cls.judge_id]))
                )
                await session.commit()
        finally:
            await engine.dispose()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.__exit__(None, None, None)
        try:
            asyncio.run(cls._cleanup_database())
        finally:
            shutil.rmtree(cls.storage_root, ignore_errors=True)
            if cls.previous_storage_root is None:
                os.environ.pop("STORAGE_ROOT", None)
            else:
                os.environ["STORAGE_ROOT"] = cls.previous_storage_root
            if cls.previous_ocr_lang is None:
                os.environ.pop("OCR_LANG", None)
            else:
                os.environ["OCR_LANG"] = cls.previous_ocr_lang
            if cls.previous_ocr_provider is None:
                os.environ.pop("OCR_PROVIDER", None)
            else:
                os.environ["OCR_PROVIDER"] = cls.previous_ocr_provider
            ocr_engine_module._settings.ocr_lang = cls.previous_engine_lang
            ocr_engine_module._settings.ocr_provider = cls.previous_engine_provider
            ocr_engine_module.ocr_engine._backends.clear()
            get_settings.cache_clear()

    @staticmethod
    def _sample_files() -> list[tuple[str, bytes, str]]:
        return [
            ("claim.pdf", b"%PDF-1.4\n% Faysal upload regression\n", "application/pdf"),
            (
                "contract.docx",
                b"PK\x03\x04faysal-docx-regression-bytes",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
            ("scan.jpg", b"\xff\xd8\xff\xe0Faysal-JPG-regression\xff\xd9", "image/jpeg"),
        ]

    async def _get_document(self, document_id: str) -> Document | None:
        engine = create_async_engine(get_settings().database_url)
        try:
            async with AsyncSession(engine) as session:
                return await session.get(Document, document_id)
        finally:
            await engine.dispose()

    async def _get_case(self, case_id: str) -> Case | None:
        engine = create_async_engine(get_settings().database_url)
        try:
            async with AsyncSession(engine) as session:
                return await session.get(Case, case_id)
        finally:
            await engine.dispose()

    async def _get_analysis(self, analysis_id: str) -> AIAnalysis | None:
        engine = create_async_engine(get_settings().database_url)
        try:
            async with AsyncSession(engine) as session:
                return await session.get(AIAnalysis, analysis_id)
        finally:
            await engine.dispose()

    async def _latest_analysis_for_document(self, document_id: str) -> AIAnalysis | None:
        engine = create_async_engine(get_settings().database_url)
        try:
            async with AsyncSession(engine) as session:
                rows = await session.execute(
                    select(AIAnalysis)
                    .where(AIAnalysis.document_id == document_id)
                    .order_by(AIAnalysis.started_at.desc(), AIAnalysis.id.desc())
                    .limit(1)
                )
                return rows.scalar_one_or_none()
        finally:
            await engine.dispose()

    @staticmethod
    def _analysis_files() -> list[tuple[str, bytes, str]]:
        import fitz
        from docx import Document as DocxDocument

        pdf = fitz.open()
        page = pdf.new_page()
        page.insert_text(
            (72, 72),
            "Da'vo arizasi. Qarzdorlikni undirish va shartnoma majburiyati.",
        )
        pdf_bytes = pdf.tobytes()
        pdf.close()

        docx = DocxDocument()
        docx.add_paragraph(
            "Da'vogar javobgardan qarz va shartnoma bo'yicha majburiyatni undirishni so'raydi."
        )
        docx_buffer = BytesIO()
        docx.save(docx_buffer)

        return [
            ("analysis-claim.pdf", pdf_bytes, "application/pdf"),
            (
                "analysis-contract.docx",
                docx_buffer.getvalue(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
        ]

    @staticmethod
    def _ocr_image_bytes(image_format: str, *, blank: bool = False) -> bytes:
        from PIL import Image, ImageDraw, ImageFont

        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 64)
        image = Image.new("RGB", (1800, 520), "white")
        if not blank:
            ImageDraw.Draw(image).multiline_text(
                (70, 70),
                "FAYSAL OCR CLAIM\nDEBT CONTRACT REVIEW\nAMOUNT 1500000 UZS",
                fill="black",
                font=font,
                spacing=28,
            )
        buffer = BytesIO()
        image.save(buffer, image_format)
        return buffer.getvalue()

    @classmethod
    def _ocr_files(cls) -> list[tuple[str, bytes, str, str]]:
        import fitz

        jpg = cls._ocr_image_bytes("JPEG")
        png = cls._ocr_image_bytes("PNG")
        scanned_pdf = fitz.open()
        page = scanned_pdf.new_page(width=1200, height=420)
        page.insert_image(page.rect, stream=png)
        scanned_pdf_bytes = scanned_pdf.tobytes()
        scanned_pdf.close()

        text_pdf = fitz.open()
        page = text_pdf.new_page()
        page.insert_text(
            (72, 72),
            "Da'vo arizasi qarzdorlikni undirish va shartnoma majburiyati.",
        )
        text_pdf_bytes = text_pdf.tobytes()
        text_pdf.close()
        return [
            ("visible-text.jpg", jpg, "image/jpeg", "ocr"),
            ("visible-text.png", png, "image/png", "ocr"),
            ("scanned.pdf", scanned_pdf_bytes, "application/pdf", "ocr"),
            ("text-layer.pdf", text_pdf_bytes, "application/pdf", "text"),
        ]

    def _assistant_headers(self) -> dict[str, str]:
        login = self.client.post(
            "/api/auth/login",
            data={"username": self.assistant_email, "password": self.password},
        )
        self.assertEqual(login.status_code, 200, login.text)
        return {"Authorization": f"Bearer {login.json()['accessToken']}"}

    def _create_case(self, headers: dict[str, str], label: str) -> str:
        create_case = self.client.post(
            "/api/cases",
            headers=headers,
            json={
                "caseNumber": f"E2E-{label}-{uuid.uuid4().hex[:12].upper()}",
                "citizenName": "AI Analysis Regression Citizen",
                "description": "Temporary AI analysis integration test",
                "assignedJudgeId": self.judge_id,
            },
        )
        self.assertEqual(create_case.status_code, 201, create_case.text)
        return create_case.json()["id"]

    def test_upload_download_hashes_and_submit_uploaded_case(self) -> None:
        headers = self._assistant_headers()
        case_id = self._create_case(headers, "UPLOAD")

        for filename, content, content_type in self._sample_files():
            upload = self.client.post(
                f"/api/cases/{case_id}/documents",
                headers=headers,
                files={"file": (filename, content, content_type)},
            )
            self.assertEqual(upload.status_code, 201, upload.text)
            payload = upload.json()
            self.assertEqual(payload["size"], len(content))
            document = asyncio.run(self._get_document(payload["id"]))
            self.assertIsNotNone(document)
            assert document is not None
            storage_path = Path(self.storage_root) / document.storage_path
            self.assertEqual(storage_path.stat().st_size, len(content))
            self.assertEqual(
                hashlib.sha256(storage_path.read_bytes()).hexdigest(),
                hashlib.sha256(content).hexdigest(),
            )
            download = self.client.get(
                f"/api/documents/{payload['id']}/download", headers=headers
            )
            self.assertEqual(download.status_code, 200, download.text)
            self.assertEqual(download.content, content)
            self.assertEqual(
                hashlib.sha256(download.content).hexdigest(),
                hashlib.sha256(content).hexdigest(),
            )

        after_upload = self.client.get(f"/api/cases/{case_id}", headers=headers)
        self.assertEqual(after_upload.status_code, 200, after_upload.text)
        self.assertEqual(after_upload.json()["status"], "uploaded")

        submit = self.client.post(f"/api/cases/{case_id}/submit", headers=headers)
        self.assertEqual(submit.status_code, 200, submit.text)
        self.assertEqual(submit.json()["case"]["status"], "under_review")
        stored_case = asyncio.run(self._get_case(case_id))
        self.assertIsNotNone(stored_case)
        assert stored_case is not None
        self.assertEqual(stored_case.status.value, "under_review")

    def test_pdf_docx_document_and_case_analysis_use_unambiguous_camelcase_dtos(self) -> None:
        headers = self._assistant_headers()
        case_id = self._create_case(headers, "ANALYSIS")
        document_ids: list[str] = []

        for filename, content, content_type in self._analysis_files():
            upload = self.client.post(
                f"/api/cases/{case_id}/documents",
                headers=headers,
                files={"file": (filename, content, content_type)},
            )
            self.assertEqual(upload.status_code, 201, upload.text)
            document_ids.append(upload.json()["id"])

        document_analysis_ids: list[str] = []
        for document_id in document_ids:
            response = self.client.post(
                f"/api/documents/{document_id}/analysis", headers=headers
            )
            self.assertEqual(response.status_code, 200, response.text)
            record = response.json()
            document_analysis_ids.append(record["id"])
            self.assertEqual(record["documentId"], document_id)
            self.assertEqual(record["status"], "done")
            self.assertTrue(record["result"])
            self.assertIn("confidencePercent", record["result"])
            self.assertIn("humanReview", record["result"])
            self.assertIn("matchedSources", record["result"])
            self.assertNotIn("confidence_percent", record["result"])
            self.assertNotIn("human_review", record["result"])
            self.assertNotIn("matched_sources", record["result"])

            stored = asyncio.run(self._get_analysis(record["id"]))
            self.assertIsNotNone(stored)
            assert stored is not None
            self.assertEqual(stored.document_id, document_id)
            self.assertEqual(stored.status.value, "done")
            self.assertTrue(stored.result_json)
            self.assertIn("confidence_percent", stored.result_json)

            history = self.client.get(
                f"/api/documents/{document_id}/analysis", headers=headers
            )
            self.assertEqual(history.status_code, 200, history.text)
            self.assertEqual(history.json()["records"][0]["id"], record["id"])
            self.assertEqual(history.json()["records"][0]["documentId"], document_id)

        # Regression: document records already exist when case analysis starts.
        # The POST response must nevertheless be the exact new NULL-document row.
        pre_case_history = self.client.get(f"/api/cases/{case_id}/analysis", headers=headers)
        self.assertEqual(pre_case_history.status_code, 200, pre_case_history.text)
        self.assertEqual(pre_case_history.json()["records"], [])
        case_response = self.client.post(f"/api/cases/{case_id}/analysis", headers=headers)
        self.assertEqual(case_response.status_code, 200, case_response.text)
        case_record = case_response.json()
        self.assertIsNone(case_record["documentId"])
        self.assertNotIn(case_record["id"], document_analysis_ids)
        self.assertEqual(case_record["status"], "done")
        self.assertTrue(case_record["result"])
        self.assertIn("confidencePercent", case_record["result"])
        self.assertIn("humanReview", case_record["result"])
        self.assertIn("matchedSources", case_record["result"])

        stored_case_analysis = asyncio.run(self._get_analysis(case_record["id"]))
        self.assertIsNotNone(stored_case_analysis)
        assert stored_case_analysis is not None
        self.assertIsNone(stored_case_analysis.document_id)
        self.assertEqual(stored_case_analysis.status.value, "done")
        self.assertTrue(stored_case_analysis.result_json)

        first_history = self.client.get(f"/api/cases/{case_id}/analysis", headers=headers)
        second_history = self.client.get(f"/api/cases/{case_id}/analysis", headers=headers)
        self.assertEqual(first_history.status_code, 200, first_history.text)
        self.assertEqual(second_history.status_code, 200, second_history.text)
        first_records = first_history.json()["records"]
        second_records = second_history.json()["records"]
        self.assertEqual([r["id"] for r in first_records], [r["id"] for r in second_records])
        self.assertEqual(first_records[0]["id"], case_record["id"])
        self.assertTrue(all(record["documentId"] is None for record in first_records))

    def test_local_ocr_e2e_for_images_and_scanned_pdf(self) -> None:
        """Real API + storage + Tesseract regression (not a mocked OCR test)."""
        headers = self._assistant_headers()
        case_id = self._create_case(headers, "OCR")

        for filename, content, content_type, expected_method in self._ocr_files():
            upload = self.client.post(
                f"/api/cases/{case_id}/documents",
                headers=headers,
                files={"file": (filename, content, content_type)},
            )
            self.assertEqual(upload.status_code, 201, upload.text)
            document_id = upload.json()["id"]

            response = self.client.post(
                f"/api/documents/{document_id}/analysis", headers=headers
            )
            self.assertEqual(response.status_code, 200, response.text)
            record = response.json()
            self.assertEqual(record["status"], "done")
            self.assertEqual(record["documentId"], document_id)
            self.assertTrue(record["result"]["anonymizedText"])
            metadata = record["result"]["metadata"]
            self.assertEqual(metadata["extractionMethod"], expected_method)
            self.assertEqual(metadata["ocrUsed"], expected_method == "ocr")
            self.assertEqual(metadata["ocrRequired"], expected_method == "ocr")

            stored = asyncio.run(self._get_analysis(record["id"]))
            self.assertIsNotNone(stored)
            assert stored is not None
            self.assertEqual(
                stored.result_json["metadata"]["extraction_method"], expected_method
            )

        blank = self._ocr_image_bytes("PNG", blank=True)
        upload = self.client.post(
            f"/api/cases/{case_id}/documents",
            headers=headers,
            files={"file": ("blank.png", blank, "image/png")},
        )
        self.assertEqual(upload.status_code, 201, upload.text)
        blank_document_id = upload.json()["id"]
        response = self.client.post(
            f"/api/documents/{blank_document_id}/analysis", headers=headers
        )
        self.assertEqual(response.status_code, 500, response.text)
        failed = asyncio.run(self._latest_analysis_for_document(blank_document_id))
        self.assertIsNotNone(failed)
        assert failed is not None
        self.assertEqual(failed.status.value, "failed")
        self.assertIsNone(failed.result_json)
        self.assertIn("ocr_text_is_empty", failed.error_message or "")
