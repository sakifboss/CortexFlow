"""
OCR service — Tesseract (default) with optional PaddleOCR for tables/equations.

Render each image-only PDF page to a PNG at 300 DPI and run OCR, returning
text blocks with bounding boxes that map back to source coordinates for
precise citations.
"""
from __future__ import annotations

import io

from loguru import logger

from app.services.parser import ParsedBlock


class OCRService:
    def __init__(self, *, engine: str = "tesseract") -> None:
        self.engine = engine

    def ocr_image(self, image_bytes: bytes) -> list[ParsedBlock]:
        from PIL import Image

        try:
            import pytesseract

            img = Image.open(io.BytesIO(image_bytes))
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        except Exception as exc:  # pragma: no cover - env dependent
            logger.warning("Tesseract OCR failed: {}", exc)
            return []

        blocks: list[ParsedBlock] = []
        n = len(data["text"])
        current = []
        last_block = -1
        for i in range(n):
            txt = (data["text"][i] or "").strip()
            if not txt:
                continue
            block_num = data["block_num"][i]
            if block_num != last_block and current:
                blocks.append(
                    ParsedBlock(
                        text=" ".join(current),
                        bbox=[
                            float(data["left"][i - 1]),
                            float(data["top"][i - 1]),
                            float(data["left"][i - 1] + data["width"][i - 1]),
                            float(data["top"][i - 1] + data["height"][i - 1]),
                        ],
                    )
                )
                current = []
            current.append(txt)
            last_block = block_num
        if current:
            blocks.append(ParsedBlock(text=" ".join(current)))
        return blocks

    def ocr_pdf_page(self, page) -> list[ParsedBlock]:  # type: ignore[no-untyped-def]
        """Render a fitz page and OCR it."""
        pix = page.get_pixmap(dpi=300)
        return self.ocr_image(pix.tobytes("png"))


ocr = OCRService()
