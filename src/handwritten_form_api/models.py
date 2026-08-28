from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CellBox:
    row: int
    col: int
    x1: int
    y1: int
    x2: int
    y2: int


@dataclass(frozen=True)
class RecognizedCell:
    row: int
    col: int
    text: str
    confidence: float


@dataclass(frozen=True)
class RecognizedTable:
    page_index: int
    table_index: int
    rows: int
    cols: int
    cells: tuple[RecognizedCell, ...]


@dataclass(frozen=True)
class StoredResult:
    file_id: str
    file_name: str
    path: Path
    metadata_path: Path

