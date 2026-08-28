from __future__ import annotations

from pathlib import Path

from .docx_mapping import fill_template
from .errors import BusinessError, fail
from .imaging import decode_source
from .ocr import DocumentAnalyzer, StructureMismatch
from .template_schema import describe_template


class ConversionPipeline:
    def __init__(self, analyzer: DocumentAnalyzer, low_confidence_threshold: float = 0.7):
        self.analyzer = analyzer
        self.low_confidence_threshold = low_confidence_threshold

    def run(
        self,
        sources: list[Path],
        template: Path,
        output: Path,
        language: str,
        preserve_original_text: bool,
    ) -> dict:
        images = []
        for source in sources:
            images.extend(decode_source(source))
        if not images:
            raise fail("HF0201", "源文件没有可处理页面")
        template_schema = describe_template(template)
        try:
            recognized = self.analyzer.analyze(images, template_schema, language)
        except StructureMismatch as exc:
            raise fail("HF0204", str(exc)) from exc
        except Exception as exc:
            raise fail("HF0301", str(exc), 500) from exc
        try:
            filled = fill_template(template, output, recognized, preserve_original_text)
        except BusinessError:
            raise
        except Exception as exc:
            raise fail("HF0302", str(exc), 500) from exc
        all_cells = [cell for table in recognized for cell in table.cells]
        return {
            "recognizedTableCount": len(recognized),
            "recognizedCellCount": len(all_cells),
            "filledCellCount": filled,
            "lowConfidenceCellCount": sum(
                bool(cell.text) and cell.confidence < self.low_confidence_threshold for cell in all_cells
            ),
            "recognition": {
                "tables": [
                    {
                        "tableIndex": table.table_index,
                        "rows": table.rows,
                        "cols": table.cols,
                        "cells": [
                            {"row": cell.row, "col": cell.col, "text": cell.text,
                             "confidence": cell.confidence}
                            for cell in table.cells
                        ],
                    }
                    for table in recognized
                ]
            },
        }
