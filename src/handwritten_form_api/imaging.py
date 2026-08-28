from __future__ import annotations

from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

from .errors import fail


def decode_source(path: Path) -> list[np.ndarray]:
    try:
        if path.suffix.lower() == ".pdf":
            import pypdfium2 as pdfium

            pdf = pdfium.PdfDocument(str(path))
            pages: list[np.ndarray] = []
            for page in pdf:
                bitmap = page.render(scale=2.0)
                pages.append(cv2.cvtColor(np.asarray(bitmap.to_pil()), cv2.COLOR_RGB2BGR))
            if not pages:
                raise ValueError("PDF 没有页面")
            return pages
        raw = np.fromfile(path, dtype=np.uint8)
        image = cv2.imdecode(raw, cv2.IMREAD_COLOR)
        if image is None:
            with Image.open(BytesIO(path.read_bytes())) as pil:
                pil = ImageOps.exif_transpose(pil).convert("RGB")
                image = cv2.cvtColor(np.asarray(pil), cv2.COLOR_RGB2BGR)
        return [image]
    except Exception as exc:
        raise fail("HF0201", str(exc)) from exc
