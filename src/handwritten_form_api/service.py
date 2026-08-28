from __future__ import annotations

import asyncio
import hashlib
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import UploadFile

from .config import Settings
from .errors import fail
from .ocr import DocumentAnalyzer, create_document_analyzer
from .pipeline import ConversionPipeline
from .storage import ResultStore


SOURCE_SUFFIXES = {".jpg", ".jpeg", ".png", ".pdf"}


class ConversionService:
    def __init__(self, settings: Settings, analyzer: DocumentAnalyzer | None = None):
        self.settings = settings
        self._analyzer = analyzer
        self.store = ResultStore(settings.runtime_root / "results")

    def _engine(self) -> DocumentAnalyzer:
        if self._analyzer is None:
            self._analyzer = create_document_analyzer(
                self.settings.ocr_backend,
                base_url=self.settings.model_base_url,
                api_key=self.settings.model_api_key,
                model=self.settings.model_name,
                timeout=self.settings.model_timeout_seconds,
                retries=self.settings.model_retries,
                max_tokens=self.settings.model_max_tokens,
                max_concurrency=self.settings.model_max_concurrency,
            )
        return self._analyzer

    async def _save_upload(self, upload: UploadFile, destination: Path) -> None:
        size = 0
        with destination.open("wb") as target:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > self.settings.max_file_size:
                    raise fail("HF0104")
                target.write(chunk)

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    async def convert(
        self,
        source_files: list[UploadFile] | None,
        template_file: UploadFile | None,
        document_name: str | None,
        language: str,
        preserve_original_text: bool,
    ) -> dict:
        if not source_files:
            raise fail("HF0101")
        if len(source_files) > self.settings.max_source_files:
            raise fail("HF0104")
        if template_file is None:
            raise fail("HF0102")
        suffixes = [Path(item.filename or "").suffix.lower() for item in source_files]
        if any(suffix not in SOURCE_SUFFIXES for suffix in suffixes):
            raise fail("HF0103")
        if Path(template_file.filename or "").suffix.lower() != ".docx":
            raise fail("HF0103")
        file_id = f"file_{uuid.uuid4().hex}"
        job_dir = self.settings.runtime_root / "results" / file_id
        upload_dir = job_dir / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=False)
        try:
            sources: list[Path] = []
            for index, upload in enumerate(source_files):
                path = upload_dir / f"source-{index + 1}{suffixes[index]}"
                await self._save_upload(upload, path)
                sources.append(path)
            template = upload_dir / "template.docx"
            await self._save_upload(template_file, template)
            safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", (document_name or "手写表格")).strip(" .")
            safe_name = (safe_name or "手写表格")[:128]
            file_name = f"{safe_name}_电子版.docx"
            output = job_dir / f"{file_id}.docx"
            pipeline_result = await asyncio.to_thread(
                ConversionPipeline(self._engine(), self.settings.low_confidence_threshold).run,
                sources, template, output, language, preserve_original_text
            )
            recognition = pipeline_result.pop("recognition")
            stats = pipeline_result
            created_at = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")
            metadata = {
                "createdAt": created_at,
                "sourceFileCount": len(sources),
                "sources": [
                    {"originalName": upload.filename, "storedName": path.name, "sha256": self._sha256(path)}
                    for upload, path in zip(source_files, sources)
                ],
                "template": {
                    "originalName": template_file.filename,
                    "storedName": template.name,
                    "sha256": self._sha256(template),
                },
                "model": {"backend": self.settings.ocr_backend, "name": self.settings.model_name},
                "recognition": recognition,
                **stats,
            }
            self.store.save_metadata(file_id, file_name, output, metadata)
            return {
                "resultFileId": file_id,
                "resultFileName": file_name,
                "downloadUrl": (
                    f"{self.settings.public_base_url}/api/handwritten-form/v1/files/{file_id}/download"
                    if self.settings.public_base_url
                    else f"/api/handwritten-form/v1/files/{file_id}/download"
                ),
                "fileType": "DOCX",
                "createdAt": created_at,
                "sourceFileCount": len(sources),
                **stats,
            }
        except Exception:
            if not (job_dir / f"{file_id}.docx").exists():
                shutil.rmtree(job_dir, ignore_errors=True)
            raise
