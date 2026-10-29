"""Offline PDF guideline search with page-level citations (Phase 4).

Searches `docs/*.pdf` (UZA Anti-emetica beleid CINV - V2.pdf and POGO Emetogenicity
Classification Guideline Final-rev- 250111.pdf) page by page using `pypdf`.
Assigns sequential citation IDs (`S1`, `S2`, ...) and stores them in `tool_context.state['facts_evidence']`.
"""

from __future__ import annotations

import functools
import glob
import os
import re
from typing import Any

from google.adk.tools import ToolContext

DOCS = os.path.join(os.path.dirname(__file__), "..", "docs", "*.pdf")


@functools.lru_cache(maxsize=1)
def _pages() -> list[tuple[str, int, str]]:
    """Reads and caches all pages across PDF files in `docs/`."""
    from pypdf import PdfReader

    out: list[tuple[str, int, str]] = []
    for f in sorted(glob.glob(DOCS)):
        base = os.path.basename(f)
        if "briefing" in base.lower():
            continue
        reader = PdfReader(f)
        for i, page in enumerate(reader.pages, start=1):
            out.append((base, i, page.extract_text() or ""))
    return out


def search_guidelines(query: str, tool_context: ToolContext | None = None) -> dict[str, Any]:
    """Searches the UZA CINV policy and POGO guideline PDFs. Returns passages with ids (S1, S2…), file and page number.

    Args:
        query: Search terms (English or Dutch, e.g., "dexamethasone ALL" or "GEEN dexamethasone").
        tool_context: Optional ADK ToolContext to persist `facts_evidence` in session state.
    """
    terms = [t for t in re.findall(r"[a-z0-9]+", (query or "").lower()) if len(t) > 2]
    if not terms:
        terms = [(query or "").strip().lower()]

    hospital_scored: list[tuple[int, dict[str, Any]]] = []
    external_scored: list[tuple[int, dict[str, Any]]] = []

    for f, n, text in _pages():
        low = text.lower()
        score = sum(low.count(t) for t in terms if t)
        if score:
            first_match_idx = 0
            for t in terms:
                pos = low.find(t)
                if pos >= 0:
                    first_match_idx = pos
                    break
            source_type = "hospital" if "anti-emetica" in f.lower() else "external"
            item = {
                "file": f,
                "page": n,
                "snippet": text[max(first_match_idx - 150, 0) : first_match_idx + 450].strip(),
                "source_type": source_type,
            }
            if source_type == "hospital":
                hospital_scored.append((score, item))
            else:
                external_scored.append((score, item))

    hospital_hits = [h for _, h in sorted(hospital_scored, key=lambda x: -x[0])]
    external_hits = [h for _, h in sorted(external_scored, key=lambda x: -x[0])]

    # Prioritize UZA hospital policy first, followed by external POGO guideline cross-checks (up to 5 total)
    hits: list[dict[str, Any]] = []
    if hospital_hits and external_hits:
        hits.extend(hospital_hits[:2])
        hits.extend(external_hits[: 5 - len(hits)])
    else:
        hits.extend((hospital_hits + external_hits)[:5])

    ev: list[dict[str, Any]] = []
    if tool_context is not None and hasattr(tool_context, "state"):
        ev = list(tool_context.state.get("facts_evidence") or [])

    for h in hits:
        h_copy = dict(h)
        h_copy["id"] = f"S{len(ev) + 1}"
        ev.append(h_copy)

    if tool_context is not None and hasattr(tool_context, "state"):
        tool_context.state["facts_evidence"] = ev

    return {"passages": ev[-len(hits) :] if hits else []}
