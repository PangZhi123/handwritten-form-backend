from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    runtime_root: Path
    ocr_backend: str
    model_base_url: str
    model_name: str
    model_api_key: str
    model_timeout_seconds: int
    model_retries: int
    model_max_tokens: int
    model_max_concurrency: int
    public_base_url: str
    cors_origins: tuple[str, ...]
    low_confidence_threshold: float
    max_source_files: int
    max_file_size: int

    @classmethod
    def from_env(cls) -> "Settings":
        default_root = Path(tempfile.gettempdir()) / "handwritten-form-runtime"
        return cls(
            runtime_root=Path(os.getenv("HF_RUNTIME_ROOT", default_root)),
            ocr_backend=os.getenv("HF_OCR_BACKEND", "qwen_vl").lower(),
            model_base_url=os.getenv("HF_MODEL_BASE_URL", "http://127.0.0.1:8080/v1"),
            model_name=os.getenv("HF_MODEL_NAME", "qwen3-vl-30b-a3b-thinking"),
            model_api_key=os.getenv("HF_MODEL_API_KEY", "local"),
            model_timeout_seconds=int(os.getenv("HF_MODEL_TIMEOUT_SECONDS", "600")),
            model_retries=int(os.getenv("HF_MODEL_RETRIES", "2")),
            model_max_tokens=int(os.getenv("HF_MODEL_MAX_TOKENS", "8192")),
            model_max_concurrency=int(os.getenv("HF_MODEL_MAX_CONCURRENCY", "1")),
            public_base_url=os.getenv("HF_PUBLIC_BASE_URL", "").rstrip("/"),
            cors_origins=tuple(
                item.strip()
                for item in os.getenv("HF_CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
                if item.strip()
            ),
            low_confidence_threshold=float(os.getenv("HF_LOW_CONFIDENCE_THRESHOLD", "0.70")),
            max_source_files=int(os.getenv("HF_MAX_SOURCE_FILES", "20")),
            max_file_size=int(os.getenv("HF_MAX_FILE_SIZE_MB", "30")) * 1024 * 1024,
        )
