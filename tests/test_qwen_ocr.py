import json
from unittest.mock import patch

import numpy as np

from handwritten_form_api.ocr import QwenVlDocumentAnalyzer


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        content = {
            "structureMatched": True,
            "mismatchReason": "",
            "tables": [{
                "tableIndex": 0, "rows": 1, "cols": 2,
                "cells": [{"row": 0, "col": 1, "text": "张三", "confidence": 0.91}],
            }],
        }
        return json.dumps({"choices": [{"message": {"content": json.dumps(content, ensure_ascii=False)}}]}).encode()


def test_qwen_receives_template_and_all_images_once():
    schema = {"tableCount": 1, "tables": [{
        "tableIndex": 0, "rows": 1, "cols": 2,
        "cells": [
            {"row": 0, "col": 0, "anchorRow": 0, "anchorCol": 0, "merged": False, "fixedText": "姓名"},
            {"row": 0, "col": 1, "anchorRow": 0, "anchorCol": 1, "merged": False, "fixedText": ""},
        ],
    }]}
    analyzer = QwenVlDocumentAnalyzer("http://model/v1", "local", "qwen", retries=0)
    images = [np.full((40, 120, 3), 255, dtype=np.uint8), np.full((40, 120, 3), 255, dtype=np.uint8)]
    with patch("urllib.request.urlopen", return_value=FakeResponse()) as called:
        tables = analyzer.analyze(images, schema, "zh-CN")
    assert tables[0].cells[0].text == "张三"
    assert called.call_count == 1
    body = json.loads(called.call_args.args[0].data.decode("utf-8"))
    image_parts = [part for part in body["messages"][1]["content"] if part["type"] == "image_url"]
    assert len(image_parts) == 2

