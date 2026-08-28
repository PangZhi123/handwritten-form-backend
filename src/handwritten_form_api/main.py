from __future__ import annotations

import uuid
import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError

from .config import Settings
from .errors import BusinessError, fail
from .service import ConversionService


logger = logging.getLogger("handwritten_form_api")
settings = Settings.from_env()
app = FastAPI(title="手写表格电子化算法后端", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)
service = ConversionService(settings)


def envelope(request_id: str, success: bool, code: str, message: str, data=None) -> dict:
    return {
        "requestId": request_id,
        "success": success,
        "code": code,
        "message": message,
        "data": data,
        "timestamp": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
    }


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request.state.request_id = request.headers.get("X-Request-Id", f"req_{uuid.uuid4().hex}")[:64]
    return await call_next(request)


@app.exception_handler(BusinessError)
async def business_error_handler(request: Request, exc: BusinessError):
    logger.warning("requestId=%s code=%s message=%s", request.state.request_id, exc.code, exc.message)
    return JSONResponse(
        envelope(request.state.request_id, False, exc.code, exc.message), status_code=exc.http_status
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    locations = {str(part) for error in exc.errors() for part in error.get("loc", ())}
    if "sourceFiles" in locations:
        business = fail("HF0101")
    elif "templateFile" in locations:
        business = fail("HF0102")
    else:
        business = fail("HF0103", "请求字段格式或取值不合法")
    return JSONResponse(
        envelope(request.state.request_id, False, business.code, business.message), status_code=400
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    logger.exception("requestId=%s unhandled error", request.state.request_id, exc_info=exc)
    return JSONResponse(
        envelope(request.state.request_id, False, "HF0301", "后端处理失败，请根据requestId排查日志"),
        status_code=500,
    )


@app.get("/health")
def health():
    return {"status": "ok", "version": app.version}


@app.post("/api/handwritten-form/v1/convert")
async def convert(
    request: Request,
    source_files: list[UploadFile] | None = File(None, alias="sourceFiles"),
    template_file: UploadFile | None = File(None, alias="templateFile"),
    document_name: str | None = Form(None, alias="documentName", max_length=128),
    language: str = Form("zh-CN"),
    preserve_original_text: bool = Form(True, alias="preserveOriginalText"),
):
    if language not in {"zh-CN", "en-US"}:
        raise fail("HF0103", "language仅支持zh-CN或en-US")
    data = await service.convert(
        source_files, template_file, document_name, language, preserve_original_text
    )
    return envelope(request.state.request_id, True, "0", "success", data)


@app.get("/api/handwritten-form/v1/files/{result_file_id}/download")
def download(result_file_id: str):
    if re.fullmatch(r"file_[0-9a-f]{32}", result_file_id) is None:
        raise fail("HF0401", http_status=404)
    result = service.store.get(result_file_id)
    if result is None:
        raise fail("HF0401", http_status=404)
    return FileResponse(
        result.path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=result.file_name,
    )
