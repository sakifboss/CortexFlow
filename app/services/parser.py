"""
Document parsing service.

Strategy: pick a parser by mime type, return a list of `ParsedBlock`s that
preserve layout (page, section, bbox, char offsets). OCR is applied to image
pages in PDFs and image-only uploads.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field

from loguru import logger


@dataclass(slots=True)
class ParsedBlock:
    text: str
    page: int | None = None
    section: str | None = None
    bbox: list[float] | None = None
    char_start: int | None = None
    char_end: int | None = None
    needs_ocr: bool = False


@dataclass(slots=True)
class ParsedDocument:
    title: str
    blocks: list[ParsedBlock] = field(default_factory=list)
    pages: int | None = None
    language: str | None = None
    mime_type: str = "text/plain"

    def full_text(self) -> str:
        return "\n\n".join(b.text for b in self.blocks)


class ParserService:
    """Dispatches to format-specific extractors."""

    def parse(self, *, data: bytes, mime_type: str, filename: str) -> ParsedDocument:
        if mime_type == "application/pdf" or filename.lower().endswith(".pdf"):
            return self._parse_pdf(data, filename)
        if mime_type in DOCX_MIMES or filename.lower().endswith((".docx",)):
            return self._parse_docx(data, filename)
        if filename.lower().endswith(".doc"):
            return self._parse_pandoc(data, filename, "docx")
        if filename.lower().endswith(".pptx"):
            return self._parse_pptx(data, filename)
        if filename.lower().endswith((".xlsx", ".xls")) or mime_type in XLSX_MIMES:
            return self._parse_xlsx(data, filename)
        if filename.lower().endswith((".md", ".markdown")):
            return self._parse_text(data.decode("utf-8", errors="ignore"), filename)
        if filename.lower().endswith((".html", ".htm")):
            return self._parse_html(data, filename)
        return self._parse_text(data.decode("utf-8", errors="ignore"), filename)

    # ── PDF (PyMuPDF) ────────────────────────────────────────
    def _parse_pdf(self, data: bytes, filename: str) -> ParsedDocument:
        import fitz  # PyMuPDF

        doc = fitz.open(stream=data, filetype="pdf")
        blocks: list[ParsedBlock] = []
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if text:
                blocks.append(ParsedBlock(text=text, page=page_num, bbox=None))
            else:
                # Image-only page → mark for OCR
                blocks.append(ParsedBlock(text="", page=page_num, needs_ocr=True))
        return ParsedDocument(
            title=doc.metadata.get("title") or filename,
            blocks=blocks,
            pages=doc.page_count,
            mime_type="application/pdf",
        )

    # ── DOCX ─────────────────────────────────────────────────
    def _parse_docx(self, data: bytes, filename: str) -> ParsedDocument:
        from docx import Document

        doc = Document(io.BytesIO(data))
        blocks: list[ParsedBlock] = []
        section: str | None = None
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            if para.style and para.style.name.startswith("Heading"):
                section = text
            blocks.append(ParsedBlock(text=text, section=section))
        return ParsedDocument(title=filename, blocks=blocks, mime_type=DOCX_MIMES[0])

    # ── PPTX ─────────────────────────────────────────────────
    def _parse_pptx(self, data: bytes, filename: str) -> ParsedDocument:
        from pptx import Presentation

        prs = Presentation(io.BytesIO(data))
        blocks: list[ParsedBlock] = []
        for idx, slide in enumerate(prs.slides, start=1):
            texts = []
            for shape in slide.shapes:
                if getattr(shape, "has_text_frame", False):
                    texts.append(shape.text_frame.text)
            joined = "\n".join(t for t in texts if t.strip())
            if joined:
                blocks.append(ParsedBlock(text=joined, page=idx, section=f"Slide {idx}"))
        return ParsedDocument(title=filename, blocks=blocks, mime_type="application/vnd.openxmlformats-officedocument.presentationml.presentation")

    # ── XLSX ─────────────────────────────────────────────────
    def _parse_xlsx(self, data: bytes, filename: str) -> ParsedDocument:
        import pandas as pd

        xls = pd.read_excel(io.BytesIO(data), sheet_name=None)
        blocks: list[ParsedBlock] = []
        for sheet, df in xls.items():
            blocks.append(ParsedBlock(text=df.to_csv(index=False), section=sheet))
        return ParsedDocument(title=filename, blocks=blocks, mime_type=XLSX_MIMES[0])

    # ── HTML ─────────────────────────────────────────────────
    def _parse_html(self, data: bytes, filename: str) -> ParsedDocument:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(data, "lxml")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        title = (soup.title.string.strip() if soup.title and soup.title.string else filename)
        text = soup.get_text("\n", strip=True)
        return ParsedDocument(title=title, blocks=[ParsedBlock(text=text)], mime_type="text/html")

    # ── Plain / Markdown ─────────────────────────────────────
    def _parse_text(self, text: str, filename: str) -> ParsedDocument:
        # Split markdown by headings to preserve structure
        blocks: list[ParsedBlock] = []
        section: str | None = None
        for line in text.splitlines():
            if line.startswith("#"):
                section = line.lstrip("# ").strip() or section
            elif line.strip():
                blocks.append(ParsedBlock(text=line, section=section))
        if not blocks:
            blocks = [ParsedBlock(text=text)]
        return ParsedDocument(title=filename, blocks=blocks, mime_type="text/plain")

    # ── Pandoc bridge (DOC, EPUB, RST) ───────────────────────
    def _parse_pandoc(self, data: bytes, filename: str, fmt: str) -> ParsedDocument:
        try:
            import pypandoc

            text = pypandoc.convert_text(data.decode("utf-8", errors="ignore"), "md", format=fmt)
            return self._parse_text(text, filename)
        except Exception as exc:  # pragma: no cover
            logger.warning("Pandoc failed for {}: {}", filename, exc)
            return ParsedDocument(title=filename, blocks=[ParsedBlock(text=data.decode("utf-8", errors="ignore"))])


DOCX_MIMES = [
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]
XLSX_MIMES = [
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
]


parser = ParserService()
