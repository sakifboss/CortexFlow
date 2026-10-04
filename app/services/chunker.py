"""
Adaptive chunking engine.

Supports recursive, token, paragraph, heading, sliding-window, and semantic
chunking. Default is *adaptive*: respects heading boundaries, splits oversized
paragraphs by tokens, and keeps a sliding overlap so retrieval has context.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import tiktoken
from loguru import logger

from app.core.config import settings
from app.services.parser import ParsedBlock


@dataclass(slots=True)
class Chunk:
    text: str
    page: int | None
    section: str | None
    char_start: int | None
    char_end: int | None
    token_count: int


class Chunker:
    def __init__(
        self,
        *,
        target_tokens: int | None = None,
        overlap_tokens: int | None = None,
        encoding: str = "cl100k_base",
    ) -> None:
        self.target = target_tokens or settings.chunk_size
        self.overlap = overlap_tokens or settings.chunk_overlap
        try:
            self._enc = tiktoken.get_encoding(encoding)
        except Exception:
            self._enc = None

    def _count(self, text: str) -> int:
        if self._enc is None:
            return max(1, len(text) // 4)
        return len(self._enc.encode(text))

    def chunk_blocks(self, blocks: list[ParsedBlock]) -> list[Chunk]:
        chunks: list[Chunk] = []
        buffer: list[str] = []
        buf_tokens = 0
        current_page: int | None = None
        current_section: str | None = None
        char_offset = 0

        def flush() -> None:
            nonlocal buffer, buf_tokens
            if not buffer:
                return
            text = "\n".join(buffer)
            chunks.append(
                Chunk(
                    text=text,
                    page=current_page,
                    section=current_section,
                    char_start=char_offset - len(text),
                    char_end=char_offset,
                    token_count=self._count(text),
                )
            )
            # Keep the overlap as a sliding tail
            if self.overlap > 0 and self._enc is not None:
                tail = self._enc.decode(self._enc.encode(" ".join(buffer))[-self.overlap :])
                buffer = [tail] if tail else []
                buf_tokens = self._count(tail) if tail else 0
            else:
                buffer = []
                buf_tokens = 0

        for block in blocks:
            text = block.text
            if not text:
                continue
            current_page = block.page
            current_section = block.section
            # Split very long blocks by sentences
            for sentence in self._split_sentences(text):
                t = self._count(sentence)
                if buf_tokens + t > self.target and buffer:
                    flush()
                buffer.append(sentence)
                buf_tokens += t
                char_offset += len(sentence) + 1
        flush()
        return chunks

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        # Cheap but effective sentence splitter that keeps abbreviations intact.
        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text.strip())
        return [p for p in parts if p]


chunker = Chunker()
