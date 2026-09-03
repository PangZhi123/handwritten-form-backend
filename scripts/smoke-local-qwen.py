from __future__ import annotations

import json
import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "src"))

from handwritten_form_api.imaging import decode_source
from handwritten_form_api.ocr import QwenVlDocumentAnalyzer
from handwritten_form_api.template_schema import describe_template

IMG = BASE / "test-data" / "case-01" / "table_handwritten_img.jpg"
TMPL = BASE / "test-data" / "case-01" / "table_template.docx"

schema = describe_template(TMPL)
print("=== TEMPLATE SCHEMA ===")
print("tableCount:", schema["tableCount"])
for table in schema["tables"]:
    print(f"  table {table['tableIndex']}: {table['rows']}x{table['cols']}, "
          f"cells={len(table['cells'])}, valid(non-merged)="
          f"{sum(1 for c in table['cells'] if not c['merged'])}")

images = decode_source(IMG)
print("=== IMAGE ===")
for i, image in enumerate(images):
    print(f"  page {i}: shape={image.shape}")

print("=== CALL LOCAL OLLAMA ===")
analyzer = QwenVlDocumentAnalyzer(
    base_url=os.getenv("HF_MODEL_BASE_URL", "http://127.0.0.1:11434/v1"),
    api_key=os.getenv("HF_MODEL_API_KEY", "ollama"),
    model=os.getenv("HF_MODEL_NAME", "handwritten-form-qwen3-vl:4b-ctx"),
    timeout=900,
    retries=1,
    max_tokens=8192,
    max_concurrency=1,
)
tables = analyzer.analyze(images, schema, "zh-CN")
print("=== RESULT ===")
for table in tables:
    print(f"TABLE {table.table_index}: {table.rows}x{table.cols}")
    for cell in table.cells:
        print(f"  row={cell.row} col={cell.col} conf={cell.confidence:.2f} text={cell.text!r}")
print("OK")
