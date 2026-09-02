from __future__ import annotations

import base64
import json
import re
import threading
import time
import urllib.error
import urllib.request
from typing import Protocol

import cv2
import numpy as np

from .models import RecognizedCell, RecognizedTable


class DocumentAnalyzer(Protocol):
    def analyze(self, images: list[np.ndarray], template_schema: dict, language: str) -> list[RecognizedTable]: ...


class StructureMismatch(RuntimeError):
    pass


def _json_object(text: str) -> str:
    decoder = json.JSONDecoder()
    candidates: list[tuple[int, int, str]] = []
    for start, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, length = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            candidates.append((start + length, length, text[start : start + length]))
    if candidates:
        # Thinking output may contain prompt examples before the final answer.
        # Prefer the object ending latest; prefer the outer object on equal ends.
        return max(candidates, key=lambda item: (item[0], item[1]))[2]
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("响应中没有JSON对象")
    return re.sub(r",\s*([}\]])", r"\1", text[start : end + 1])


class QwenVlDocumentAnalyzer:
    """Send the DOCX schema and every source page to Qwen3-VL in one request."""

    def __init__(self, base_url: str, api_key: str, model: str, timeout: int = 600,
                 retries: int = 2, max_tokens: int = 8192, max_concurrency: int = 1):
        self.endpoint = f"{base_url.rstrip('/')}/chat/completions"
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.retries = retries
        self.max_tokens = max_tokens
        self._semaphore = threading.BoundedSemaphore(max(1, max_concurrency))

    @staticmethod
    def _image_url(image: np.ndarray) -> str:
        height, width = image.shape[:2]
        scale = min(1.0, 2048 / max(height, width))
        if scale < 1.0:
            image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 94])
        if not ok:
            raise RuntimeError("图像编码失败")
        return "data:image/jpeg;base64," + base64.b64encode(encoded).decode("ascii")

    def analyze(self, images: list[np.ndarray], template_schema: dict, language: str) -> list[RecognizedTable]:
        content = [{"type": "image_url", "image_url": {"url": self._image_url(image)}} for image in images]
        prompt_schema = {
            "tableCount": template_schema["tableCount"],
            "tables": [{
                "tableIndex": table["tableIndex"],
                "rows": table["rows"],
                "cols": table["cols"],
                "cells": [{
                    "row": cell["row"], "col": cell["col"],
                    "fixedText": cell["fixedText"],
                } for cell in table["cells"] if not cell["merged"]],
            } for table in template_schema["tables"]],
        }
        prompt = (
            "你将收到按上传顺序排列的手写表格图片，以及Word模板的精确表格结构JSON。"
            "请直接完成表格感知、手写识别和模板单元格映射。图片表格按页码、页面内从上到下/从左到右对应tableIndex。"
            "fixedText非空的是模板固定文字，必须保留，不要作为手写结果返回。"
            "rows/cols是Word合并前的内部网格坐标，不是图片中肉眼可数的线条数；合并后视觉行列数较少不代表结构不匹配。"
            "图片中的工程名称、编号、日期及其他字段值与模板fixedText不同，也不属于结构不匹配。"
            "只有表单版式或表格数量明显属于另一种表单时才设置structureMatched=false；同类表单必须设置为true。"
            "只返回结构中列出的有效单元格坐标，不要返回被合并覆盖的位置。"
            "只返回识别到非空手写内容的单元格；空白单元格必须省略，禁止为所有空白格生成text为空字符串的条目。"
            "无法确认的文字允许返回但必须降低confidence。"
            f"主要语言：{language}。模板结构："
            + json.dumps(prompt_schema, ensure_ascii=False, separators=(",", ":"))
            + "\n只输出标准JSON："
            '{"structureMatched":true,"mismatchReason":"","tables":['
            '{"tableIndex":0,"rows":2,"cols":3,"cells":['
            '{"row":0,"col":0,"text":"","confidence":0.0}]}]}。'
        )
        content.append({"type": "text", "text": prompt})
        payload = {"model": self.model, "temperature": 0, "max_tokens": self.max_tokens,
                   "response_format": {"type": "json_object"},
                   "messages": [{"role": "system", "content": "你是手写表格电子化引擎，只输出JSON。"},
                                {"role": "user", "content": content}]}
        parse_error: Exception | None = None
        data = None
        with self._semaphore:
            for parse_attempt in range(self.retries + 1):
                result = self._request_with_retry(payload)
                try:
                    message = result["choices"][0]["message"]
                    raw = (message.get("content") or message.get("reasoning_content")
                           or message.get("reasoning") or "")
                    data = json.loads(_json_object(raw))
                    break
                except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
                    parse_error = exc
                    if parse_attempt < self.retries:
                        time.sleep(min(2**parse_attempt, 4))
        if data is None:
            raise RuntimeError(f"Qwen3-VL多次返回无效JSON：{parse_error}") from parse_error
        if data.get("structureMatched") is not True:
            raise StructureMismatch(str(data.get("mismatchReason") or "模型判定表格结构不匹配"))
        return self._parse_tables(data, template_schema)

    def _request_with_retry(self, payload: dict) -> dict:
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            request = urllib.request.Request(
                self.endpoint, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
                method="POST")
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(min(2**attempt, 4))
        raise RuntimeError(f"Qwen3-VL调用失败：{last_error}") from last_error

    @staticmethod
    def _parse_tables(data: dict, template_schema: dict) -> list[RecognizedTable]:
        expected = {item["tableIndex"]: item for item in template_schema["tables"]}
        returned = data.get("tables")
        if not isinstance(returned, list) or len(returned) != len(expected):
            raise StructureMismatch("模型返回的表格数量与模板不一致")
        tables: list[RecognizedTable] = []
        for raw_table in returned:
            index = int(raw_table["tableIndex"])
            schema = expected.get(index)
            if schema is None:
                raise StructureMismatch(f"模型返回未知tableIndex={index}")
            rows, cols = int(raw_table["rows"]), int(raw_table["cols"])
            if (rows, cols) != (schema["rows"], schema["cols"]):
                raise StructureMismatch(f"tableIndex={index}行列结构不匹配")
            valid = {(cell["row"], cell["col"]) for cell in schema["cells"] if not cell["merged"]}
            cells = []
            for raw_cell in raw_table.get("cells", []):
                row, col = int(raw_cell["row"]), int(raw_cell["col"])
                if (row, col) not in valid:
                    raise StructureMismatch(f"tableIndex={index}包含无效单元格({row},{col})")
                confidence = max(0.0, min(1.0, float(raw_cell.get("confidence", 0.0))))
                cells.append(RecognizedCell(row, col, str(raw_cell.get("text", "")).strip(), confidence))
            tables.append(RecognizedTable(0, index, rows, cols, tuple(cells)))
        return sorted(tables, key=lambda item: item.table_index)


def create_document_analyzer(backend: str, *, base_url: str, api_key: str, model: str,
                             timeout: int, retries: int, max_tokens: int,
                             max_concurrency: int) -> DocumentAnalyzer:
    if backend != "qwen_vl":
        raise RuntimeError("整表直传流程当前仅支持 qwen_vl 后端")
    return QwenVlDocumentAnalyzer(base_url, api_key, model, timeout, retries, max_tokens, max_concurrency)
