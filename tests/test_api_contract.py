from pathlib import Path

import cv2
import numpy as np
from docx import Document
from fastapi.testclient import TestClient

from handwritten_form_api.config import Settings
from handwritten_form_api.models import RecognizedCell, RecognizedTable
from handwritten_form_api.service import ConversionService
import handwritten_form_api.main as main_module


class FakeAnalyzer:
    def analyze(self, images, template_schema, language):
        assert len(images) == 1
        return [RecognizedTable(0, 0, 1, 1, (RecognizedCell(0, 0, "测试", 0.95),))]


def settings(tmp_path: Path) -> Settings:
    return Settings(
        runtime_root=tmp_path,
        ocr_backend="qwen_vl",
        model_base_url="http://model/v1",
        model_name="qwen",
        model_api_key="local",
        model_timeout_seconds=10,
        model_retries=0,
        model_max_tokens=1024,
        model_max_concurrency=1,
        public_base_url="http://testserver",
        cors_origins=("http://frontend",),
        low_confidence_threshold=0.7,
        max_source_files=20,
        max_file_size=5 * 1024 * 1024,
    )


def test_convert_and_download_contract(tmp_path: Path):
    main_module.service = ConversionService(settings(tmp_path), FakeAnalyzer())
    client = TestClient(main_module.app)
    document = Document()
    document.add_table(rows=1, cols=1)
    template = tmp_path / "template.docx"
    document.save(template)
    image = np.full((120, 240, 3), 255, dtype=np.uint8)
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    response = client.post(
        "/api/handwritten-form/v1/convert",
        files=[
            ("sourceFiles", ("form.png", encoded.tobytes(), "image/png")),
            ("templateFile", ("template.docx", template.read_bytes(),
                              "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
        ],
        data={"documentName": "施工记录表", "language": "zh-CN", "preserveOriginalText": "true"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True and body["code"] == "0"
    assert body["data"]["downloadUrl"].startswith("http://testserver/")
    download = client.get(body["data"]["downloadUrl"].removeprefix("http://testserver"))
    assert download.status_code == 200
    assert download.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


def test_missing_source_uses_document_error_code(tmp_path: Path):
    main_module.service = ConversionService(settings(tmp_path), FakeAnalyzer())
    client = TestClient(main_module.app)
    response = client.post("/api/handwritten-form/v1/convert")
    assert response.status_code == 400
    assert response.json()["code"] == "HF0101"
    assert b"\\u" in response.content
