"""Deterministic output guardrail callback (`after_model_callback`) for Almesis Copilot (Phase 6).

Verifies every final LLM text response before returning it to the clinician:
1. Skips intermediate tool/function-call responses.
2. Checks every `<number> mg` and `<number> mL` in the text against `facts_doses` / `facts_passport` (when present in session state).
3. Checks every `[S<n>]` citation against `facts_evidence` in session state.
4. Enforces the mandatory `ADVISORY_LABEL` ("Advisory Only — Requires Clinician Sign-Off").
"""

from __future__ import annotations

import copy
import re
from typing import Any

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse
from google.genai import types

from app.tables import ADVISORY_LABEL

_DOSE_VOL_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*(mg|ml)\b(?!\s*/)", re.IGNORECASE)
_CITATION_RE = re.compile(r"\[(S\d+)\]")


def _allowed_numbers(state: dict[str, Any]) -> tuple[bool, set[float], set[float]]:
    """Extracts allowed mg and mL numbers from `facts_doses` and `facts_passport` in state."""
    has_dose_facts = "facts_doses" in state or "facts_passport" in state
    allowed_mg: set[float] = set()
    allowed_ml: set[float] = set()

    facts_doses = state.get("facts_doses") or {}
    for row in facts_doses.get("doses") or []:
        if row.get("dose_mg") is not None:
            allowed_mg.add(round(float(row["dose_mg"]), 2))
            allowed_mg.add(round(float(row["dose_mg"]), 1))
        if row.get("actual_dose_mg") is not None:
            allowed_mg.add(round(float(row["actual_dose_mg"]), 2))
            allowed_mg.add(round(float(row["actual_dose_mg"]), 1))
        if row.get("volume_ml") is not None:
            allowed_ml.add(round(float(row["volume_ml"]), 2))
            allowed_ml.add(round(float(row["volume_ml"]), 1))

    facts_passport = state.get("facts_passport") or {}
    for day in facts_passport.get("days") or []:
        for entry in day.get("entries") or []:
            if entry.get("volume_ml") is not None:
                allowed_ml.add(round(float(entry["volume_ml"]), 2))
                allowed_ml.add(round(float(entry["volume_ml"]), 1))

    return has_dose_facts, allowed_mg, allowed_ml


def _allowed_citations(state: dict[str, Any]) -> tuple[bool, set[str]]:
    """Extracts allowed `[S<n>]` citation IDs from `facts_evidence` in state."""
    has_evidence = "facts_evidence" in state
    ev = state.get("facts_evidence") or []
    ids = {str(item.get("id")) for item in ev if isinstance(item, dict) and item.get("id")}
    return has_evidence, ids


def _sentence_has_unsupported_value(
    sentence: str,
    has_dose_facts: bool,
    allowed_mg: set[float],
    allowed_ml: set[float],
    has_evidence: bool,
    allowed_cites: set[str],
) -> bool:
    """Returns True if a sentence contains an unsupported mg/mL value or unknown [S<n>] citation."""
    if has_dose_facts:
        for match in _DOSE_VOL_RE.finditer(sentence):
            val = float(match.group(1))
            unit = match.group(2).lower()
            target_set = allowed_mg if unit == "mg" else allowed_ml
            if round(val, 2) not in target_set and round(val, 1) not in target_set:
                return True

    for cite_match in _CITATION_RE.finditer(sentence):
        cite_id = cite_match.group(1)
        if not has_evidence or cite_id not in allowed_cites:
            return True

    return False


def guard(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> LlmResponse | None:
    """Checks final LLM response text against deterministic tool facts and advisory label."""
    if llm_response is None or getattr(llm_response, "content", None) is None:
        return None
    if getattr(llm_response, "partial", False):
        return None

    parts = getattr(llm_response.content, "parts", None) or []
    if not parts:
        return None

    # Skip responses that contain function calls
    if any(getattr(p, "function_call", None) is not None for p in parts):
        return None

    text_parts = [getattr(p, "text", None) for p in parts if getattr(p, "text", None)]
    if not text_parts:
        return None

    full_text = "\n".join(text_parts)
    state: dict[str, Any] = getattr(callback_context, "state", None) or {}

    has_dose_facts, allowed_mg, allowed_ml = _allowed_numbers(state)
    has_evidence, allowed_cites = _allowed_citations(state)

    # Split into sentences/lines and check each for unsupported values
    sentences = re.split(r"(?<=[.!?])\s+|\n+", full_text)
    kept_sentences: list[str] = []
    removed_any = False

    for sent in sentences:
        if not sent.strip():
            continue
        if _sentence_has_unsupported_value(
            sent, has_dose_facts, allowed_mg, allowed_ml, has_evidence, allowed_cites
        ):
            removed_any = True
        else:
            kept_sentences.append(sent)

    missing_label = ADVISORY_LABEL not in full_text

    if not removed_any and not missing_label:
        return None

    new_body = " ".join(kept_sentences).strip()
    if removed_any:
        new_body = (
            f"Guardrail: unsupported values removed\n\n{new_body}"
            if new_body
            else "Guardrail: unsupported values removed"
        )

    if ADVISORY_LABEL not in new_body:
        new_body = f"{new_body}\n\n{ADVISORY_LABEL}".strip()

    updated = copy.deepcopy(llm_response)
    updated.content = types.Content(
        role=getattr(llm_response.content, "role", "model") or "model",
        parts=[types.Part.from_text(text=new_body)],
    )
    return updated
