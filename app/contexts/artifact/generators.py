"""
Artifact generators.

Each ``ArtifactKind`` maps to a :class:`Generator` that knows how to:
  * build the system + user prompt that steers the LLM toward a strict JSON
    payload matching the kind's content schema, and
  * derive a human title from the parsed content.

The generators deliberately over-specify the JSON shape (with an inline example
and hard rules) because the default local model (``qwen2.5:3b``) is weak at
schema adherence. Parsing is handled by :func:`extract_json`, which is tolerant
of the usual failure modes (markdown fences, leading prose, trailing commas,
single quotes). Validation against the Pydantic content model happens in the
service, so even a partial payload degrades gracefully instead of 500-ing.
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.contexts.artifact.models import ArtifactKind


# ── JSON extraction ───────────────────────────────────────────────────────
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def _balanced_slice(text: str) -> str | None:
    """Return the first balanced {...} or [...] block, respecting strings."""
    start = None
    opener = closer = ""
    for i, ch in enumerate(text):
        if ch in "{[":
            start, opener = i, ch
            closer = "}" if ch == "{" else "]"
            break
    if start is None:
        return None

    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return text[start:]  # unbalanced — return best effort for the repair pass


def _repair(candidate: str) -> str:
    """Best-effort cleanup for common LLM JSON slips."""
    s = candidate.strip()
    # Remove trailing commas before a closing brace/bracket.
    s = re.sub(r",(\s*[}\]])", r"\1", s)
    # Smart quotes → straight quotes.
    s = s.replace("\u201c", '"').replace("\u201d", '"').replace("\u2019", "'")
    return s


def extract_json(text: str) -> Any:
    """Parse a JSON object/array out of a possibly-noisy LLM response.

    Raises ``ValueError`` if nothing parseable is found.
    """
    if not text or not text.strip():
        raise ValueError("empty model response")

    candidates: list[str] = []
    fenced = _FENCE_RE.findall(text)
    candidates.extend(f.strip() for f in fenced if f.strip())
    sliced = _balanced_slice(text)
    if sliced:
        candidates.append(sliced)
    candidates.append(text.strip())

    last_err: Exception | None = None
    for cand in candidates:
        for attempt in (cand, _repair(cand)):
            try:
                return json.loads(attempt)
            except Exception as exc:  # noqa: BLE001
                last_err = exc
    raise ValueError(f"no valid JSON found: {last_err}")


# ── Generator definition ──────────────────────────────────────────────────
@dataclass(slots=True)
class Generator:
    system: str
    build_user: Callable[[str, str, dict[str, Any]], str]
    title_of: Callable[[dict[str, Any]], str]


def _count(options: dict[str, Any], key: str, default: int, lo: int, hi: int) -> int:
    try:
        n = int(options.get(key, options.get("count", default)))
    except (TypeError, ValueError):
        n = default
    return max(lo, min(hi, n))


def _focus_block(focus: str) -> str:
    focus = (focus or "").strip()
    return f"\nUser focus / instruction: {focus}\n" if focus else ""


_JSON_RULES = (
    "Return ONLY a single valid JSON object. No prose, no markdown fences, no "
    "commentary before or after. Use double quotes for all keys and strings. "
    "Do not invent facts that are not supported by the context."
)


# ── Per-kind builders ─────────────────────────────────────────────────────
def _custom(ctx: str, focus: str, opts: dict) -> str:
    return (
        f"{_JSON_RULES}\n\n"
        'Shape: {"body": "<the artifact as markdown>"}\n\n'
        "Produce the artifact the user asked for, grounded in the context. "
        "Use rich markdown (headings, lists, tables, bold) where helpful. "
        "Cite supporting sources inline as [n] matching the context indices."
        f"{_focus_block(focus)}\n### Context\n{ctx}"
    )


def _audio(ctx: str, focus: str, opts: dict) -> str:
    turns = _count(opts, "turns", 14, 6, 40)
    return (
        f"{_JSON_RULES}\n\n"
        'Shape: {"title": str, "description": str, "host_a": str, "host_b": str, '
        '"turns": [{"speaker": "<host_a or host_b name>", "text": str}]}\n\n'
        f"Write an engaging, conversational podcast script with about {turns} "
        "alternating turns between two hosts who explain the material to a "
        "curious listener. Natural spoken language, a warm hand-off between "
        "hosts, concrete examples. Keep each turn 1-4 sentences. Open with a "
        "hook and close with a takeaway. Ground every claim in the context."
        f"{_focus_block(focus)}\n### Context\n{ctx}"
    )


def _slides(ctx: str, focus: str, opts: dict) -> str:
    n = _count(opts, "slides", 8, 3, 30)
    return (
        f"{_JSON_RULES}\n\n"
        'Shape: {"title": str, "subtitle": str, "slides": [{"title": str, '
        '"bullets": [str], "notes": str}]}\n\n'
        f"Build a {n}-slide deck. Slide 1 is a title slide (few/no bullets). "
        "Each content slide: a crisp title, 3-5 punchy bullets, and short "
        "speaker notes. End with a summary slide. Cite sources in bullets as "
        "[n] where relevant."
        f"{_focus_block(focus)}\n### Context\n{ctx}"
    )


def _mindmap(ctx: str, focus: str, opts: dict) -> str:
    return (
        f"{_JSON_RULES}\n\n"
        'Shape: {"root": {"label": str, "children": [{"label": str, '
        '"children": [...]}]}}\n\n'
        "Build a mind map. The root is the central topic. Add 4-7 main "
        "branches; give each 2-5 sub-nodes; go up to 3 levels deep where the "
        "content warrants it. Labels are short (2-6 words). Cover the breadth "
        "of the context."
        f"{_focus_block(focus)}\n### Context\n{ctx}"
    )


def _report(ctx: str, focus: str, opts: dict) -> str:
    return (
        f"{_JSON_RULES}\n\n"
        'Shape: {"title": str, "abstract": str, "sections": [{"heading": str, '
        '"content": "<markdown>"}], "conclusion": str}\n\n'
        "Write a thorough, well-structured report with 4-7 sections. Section "
        "content is markdown and may use sub-headings, lists and tables. "
        "Ground every factual claim and cite inline as [n] matching the "
        "context indices. Be analytical, not just descriptive."
        f"{_focus_block(focus)}\n### Context\n{ctx}"
    )


def _flashcards(ctx: str, focus: str, opts: dict) -> str:
    n = _count(opts, "cards", 12, 3, 50)
    return (
        f"{_JSON_RULES}\n\n"
        'Shape: {"title": str, "cards": [{"front": str, "back": str, '
        '"hint": str}]}\n\n'
        f"Create {n} study flashcards for active recall. Front = a question or "
        "term; back = a clear, self-contained answer; hint = an optional short "
        "nudge (may be empty). Cover the most important, testable facts in the "
        "context. Avoid duplicates."
        f"{_focus_block(focus)}\n### Context\n{ctx}"
    )


def _quiz(ctx: str, focus: str, opts: dict) -> str:
    n = _count(opts, "questions", 8, 2, 30)
    diff = str(opts.get("difficulty", "mixed"))
    return (
        f"{_JSON_RULES}\n\n"
        'Shape: {"title": str, "questions": [{"question": str, "options": '
        '[str, str, str, str], "answer_index": <0-based int>, '
        '"explanation": str}]}\n\n'
        f"Write {n} multiple-choice questions ({diff} difficulty). Exactly 4 "
        "plausible options each; exactly one correct; distractors must be "
        "believable. answer_index is the 0-based index of the correct option. "
        "Explanation states why the answer is correct. Base everything on the "
        "context."
        f"{_focus_block(focus)}\n### Context\n{ctx}"
    )


def _infographic(ctx: str, focus: str, opts: dict) -> str:
    return (
        f"{_JSON_RULES}\n\n"
        'Shape: {"title": str, "subtitle": str, "stats": [{"label": str, '
        '"value": str, "unit": str, "description": str}], "sections": '
        '[{"heading": str, "icon": "<one emoji>", "points": [str]}], '
        '"takeaway": str}\n\n'
        "Design an infographic. Extract 3-6 headline stats (numbers/metrics "
        "from the context; value is the number, unit is %/x/etc). Add 3-5 "
        "themed sections, each with a fitting emoji icon and 2-4 short points. "
        "Finish with a one-line takeaway. Only use figures present in the "
        "context; never fabricate numbers."
        f"{_focus_block(focus)}\n### Context\n{ctx}"
    )


def _datatable(ctx: str, focus: str, opts: dict) -> str:
    n = _count(opts, "rows", 10, 1, 100)
    return (
        f"{_JSON_RULES}\n\n"
        'Shape: {"title": str, "caption": str, "columns": [str], '
        '"rows": [[str, ...]]}\n\n'
        f"Extract the most relevant structured data into a table of up to {n} "
        "rows. Choose 3-6 meaningful columns. Every row must have exactly as "
        "many cells as there are columns (use \"\" for unknown cells). Values "
        "come from the context only."
        f"{_focus_block(focus)}\n### Context\n{ctx}"
    )


# ── Title derivation ──────────────────────────────────────────────────────
def _first_str(*vals: Any) -> str:
    for v in vals:
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _title_custom(c: dict) -> str:
    body = c.get("body", "") or ""
    for line in body.splitlines():
        line = line.strip().lstrip("#").strip()
        if line:
            return line[:120]
    return "Custom Artifact"


REGISTRY: dict[ArtifactKind, Generator] = {
    ArtifactKind.CUSTOM: Generator(
        system="You are CortexFlow Studio, generating a bespoke artifact grounded in the user's sources.",
        build_user=_custom, title_of=_title_custom,
    ),
    ArtifactKind.AUDIO_OVERVIEW: Generator(
        system="You are a podcast script writer producing a lively two-host deep dive.",
        build_user=_audio, title_of=lambda c: _first_str(c.get("title"), "Audio Overview"),
    ),
    ArtifactKind.SLIDE_DECK: Generator(
        system="You are a presentation designer creating a clean, information-dense slide deck.",
        build_user=_slides, title_of=lambda c: _first_str(c.get("title"), "Slide Deck"),
    ),
    ArtifactKind.MIND_MAP: Generator(
        system="You are a knowledge architect building a clear, hierarchical mind map.",
        build_user=_mindmap,
        title_of=lambda c: _first_str((c.get("root") or {}).get("label"), c.get("title"), "Mind Map"),
    ),
    ArtifactKind.REPORT: Generator(
        system="You are a senior research analyst writing a rigorous, cited report.",
        build_user=_report, title_of=lambda c: _first_str(c.get("title"), "Report"),
    ),
    ArtifactKind.FLASHCARDS: Generator(
        system="You are a study-tools expert writing high-quality flashcards for active recall.",
        build_user=_flashcards, title_of=lambda c: _first_str(c.get("title"), "Flashcards"),
    ),
    ArtifactKind.QUIZ: Generator(
        system="You are an assessment designer writing fair, unambiguous multiple-choice questions.",
        build_user=_quiz, title_of=lambda c: _first_str(c.get("title"), "Quiz"),
    ),
    ArtifactKind.INFOGRAPHIC: Generator(
        system="You are a data-visualization designer distilling sources into an infographic.",
        build_user=_infographic, title_of=lambda c: _first_str(c.get("title"), "Infographic"),
    ),
    ArtifactKind.DATA_TABLE: Generator(
        system="You are a data extraction engine turning unstructured sources into clean tables.",
        build_user=_datatable, title_of=lambda c: _first_str(c.get("title"), "Data Table"),
    ),
}


def build_messages(kind: ArtifactKind, *, context: str, focus: str, options: dict[str, Any]) -> list[dict]:
    gen = REGISTRY[kind]
    return [
        {"role": "system", "content": gen.system + "\n\n" + _JSON_RULES},
        {"role": "user", "content": gen.build_user(context, focus, options)},
    ]
