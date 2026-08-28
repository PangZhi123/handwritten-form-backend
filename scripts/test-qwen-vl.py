from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

from handwritten_form_api.ocr import QwenVlDocumentAnalyzer


def main() -> int:
    if len(sys.argv) != 2:
        print("用法: python scripts/test-qwen-vl.py <表格图片>")
        return 2
    path = Path(sys.argv[1])
    image = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        print(f"无法读取图片: {path}")
        return 2
    analyzer = QwenVlDocumentAnalyzer(
        "http://127.0.0.1:8080/v1", "local", "qwen3-vl-30b-a3b-thinking", 600
    )
    schema = {"tableCount": 1, "tables": [{"tableIndex": 0, "rows": 1, "cols": 1,
              "cells": [{"row": 0, "col": 0, "anchorRow": 0, "anchorCol": 0,
                         "merged": False, "fixedText": ""}]}]}
    print(analyzer.analyze([image], schema, "zh-CN"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
