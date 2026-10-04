"""
Citation engine — strict post-processing of LLM output.

Goals:
  1. Parse every [n] marker in the model output.
  2. Map each marker to a retrieved source chunk (CitationRef).
  3. Drop (or flag) any sentence that lacks a citation.
  4. Return grounded spans + citation list for the UI.

This is the single source of truth for "never hallucinate citations".
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from app.contexts.citation.schemas import CitationRef, GroundedSpan
from app.services.vector import VectorHit

_CITATION_RE = re.compile(r"\[(\d+)\]")


@dataclass(slots=True)
class GroundedAnswer:
    text: str
    citations: list[CitationRef]
    spans: list[GroundedSpan]
    ungrounded_sentences: list[str]


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text.strip())
    return [p for p in parts if p.strip()]


class CitationEngine:
    def ground(
        self,
        *,
        raw_answer: str,
        hits: list[VectorHit],
        document_titles: dict[uuid.UUID, str],
    ) -> GroundedAnswer:
        # Build the citation table from the top hits, in retrieval order.
        citations: list[CitationRef] = []
        hit_by_idx: dict[int, VectorHit] = {}
        for i, hit in enumerate(hits, start=1):
            citations.append(
                CitationRef(
                    id=i,
                    document_id=hit.document_id,
                    document_title=document_titles.get(hit.document_id, "Source"),
                    chunk_id=hit.chunk_id,
                    page=hit.page,
                    section=hit.section,
                    snippet=hit.text[:400],
                    score=hit.score,
                )
            )
            hit_by_idx[i] = hit

        # Validate citation markers — keep only those that map to real sources.
        valid_text = raw_answer
        for match in _CITATION_RE.finditer(raw_answer):
            idx = int(match.group(1))
            if idx not in hit_by_idx:
                valid_text = valid_text.replace(match.group(0), "")

        # Build grounded spans and flag ungrounded sentences.
        spans: list[GroundedSpan] = []
        ungrounded: list[str] = []
        for sentence in _split_sentences(valid_text):
            refs = [int(n) for n in _CITATION_RE.findall(sentence)]
            refs = [r for r in refs if r in hit_by_idx]
            if refs:
                spans.append(GroundedSpan(text=sentence, citations=refs))
            else:
                # Factual-looking sentence without grounding → flag, don't drop.
                if len(sentence) > 25 and not sentence.lower().startswith(("surely", "of course", "here is", "here are")):
                    ungrounded.append(sentence)
                else:
                    spans.append(GroundedSpan(text=sentence, citations=[]))

        return GroundedAnswer(
            text=valid_text.strip(),
            citations=citations,
            spans=spans,
            ungrounded_sentences=ungrounded,
        )


citation_engine = CitationEngine()
