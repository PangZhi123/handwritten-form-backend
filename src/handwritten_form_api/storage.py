from __future__ import annotations

import json
from pathlib import Path

from .models import StoredResult


class ResultStore:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def save_metadata(self, file_id: str, file_name: str, path: Path, metadata: dict) -> StoredResult:
        metadata_path = path.with_suffix(".json")
        payload = {**metadata, "fileId": file_id, "fileName": file_name, "path": str(path)}
        metadata_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return StoredResult(file_id, file_name, path, metadata_path)

    def get(self, file_id: str) -> StoredResult | None:
        metadata_path = self.root / file_id / f"{file_id}.json"
        if not metadata_path.is_file():
            return None
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
        path = Path(data["path"])
        if not path.is_file():
            return None
        return StoredResult(file_id, data["fileName"], path, metadata_path)
