# Copyright 2026 Google LLC
# Author: Jerome CG Paquay (@jpaquay)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Unit tests for AImesis (uc3-aimesis-cinv) deterministic tools, guardrails, and ADK agent wiring."""

from __future__ import annotations

from types import SimpleNamespace

from google.adk.models import LlmResponse
from google.genai import types
import pytest

from app.agent import (
    ADVISORY_LABEL,
    build_parent_passport,
    calculate_risk_adjusted_regimen,
    check_ddi_interactions,
    classify_regimen_emetogenicity,
    compute_antiemetic_doses,
    get_pogo_guideline_recommendation,
    guard,
    root_agent,
    search_guidelines,
)
from app.tables import SCHEDULE_RULES


def test_root_agent_wiring() -> None:
    """Verifies root_agent configuration, 7 registered tool functions, and guardrail callback."""
    assert root_agent.name == "uc3_aimesis_cinv"
    assert root_agent.model == "gemini-2.5-flash"
    tool_names = [t.__name__ for t in root_agent.tools]
    assert tool_names == [
        "classify_regimen_emetogenicity",
        "check_ddi_interactions",
        "get_pogo_guideline_recommendation",
        "calculate_risk_adjusted_regimen",
        "compute_antiemetic_doses",
        "search_guidelines",
        "build_parent_passport",
    ]
    assert root_agent.after_model_callback is guard


def test_classify_regimen_emetogenicity_high_and_synergy() -> None:
    """Verifies High emetic risk classification and multi-agent synergy escalation."""
    hec = classify_regimen_emetogenicity(["cisplatin", "etoposide"])
    assert hec["overall_emetogenic_tier"] == "High"
    assert hec["advisory_status"] == ADVISORY_LABEL

    # Two Moderate agents (doxorubicin + cytarabine) escalate to High via POGO synergy rule
    synergy = classify_regimen_emetogenicity(["doxorubicin", "cytarabine"])
    assert synergy["overall_emetogenic_tier"] == "High"
    assert synergy["synergy_escalation_applied"] is True

    # Casus 3 (iEuroEwing IE): Ifosfamide (Moderate) + Etoposide (Low) escalates to High per UZA v2 & POGO 250111
    casus_3_ie = classify_regimen_emetogenicity(["ifosfamide", "etoposide"])
    assert casus_3_ie["overall_emetogenic_tier"] == "High"
    assert casus_3_ie["synergy_escalation_applied"] is True
    assert len(casus_3_ie["unverified_sources"]) > 0

    # Casus 2 (ALLTogether1 Induction B D8): Vincristine (Minimal) + Daunorubicin (Moderate) -> Moderate
    casus_2_all = classify_regimen_emetogenicity(["vincristine", "daunorubicin"])
    assert casus_2_all["overall_emetogenic_tier"] == "Moderate"


def test_unverified_rows_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    """Phase 2 Acceptance: without ALLOW_UNVERIFIED=1, unverified table rows return needs_clinician_review=True."""
    monkeypatch.delenv("ALLOW_UNVERIFIED", raising=False)
    blocked = classify_regimen_emetogenicity(["ifosfamide", "etoposide"])
    assert blocked["needs_clinician_review"] is True
    assert len(blocked["unverified_sources"]) > 0


def test_check_ddi_interactions_azole_and_qtc() -> None:
    """Verifies CYP3A4 azole + aprepitant/dexamethasone and additive QTc detection."""
    ddi = check_ddi_interactions(
        primary_drugs=["cisplatin", "doxorubicin", "voriconazole"],
        proposed_antiemetics=["ondansetron", "aprepitant", "dexamethasone"],
    )
    assert ddi["highest_severity"] == "CRITICAL"
    assert ddi["qtc_prolongation_risk"] == "ELEVATED"
    assert ddi["safe_to_proceed_without_modification"] is False
    assert ddi["advisory_status"] == ADVISORY_LABEL
    assert any("50%" in mod for mod in ddi["recommended_modifications"])


def test_get_pogo_guideline_recommendation_age_strata() -> None:
    """Verifies age-stratified POGO guideline recommendations."""
    child_hec = get_pogo_guideline_recommendation("High", age=8, route="IV")
    assert child_hec["emetogenic_tier"] == "High"
    assert child_hec["age_stratum"] == "Child (1-11 years)"
    assert "aprepitant" in child_hec["proposed_antiemetics_list"]
    assert child_hec["advisory_status"] == ADVISORY_LABEL

    infant_hec = get_pogo_guideline_recommendation("High", age=0, route="IV")
    assert infant_hec["age_stratum"] == "Infant (<1 year)"
    assert "<6 months" in infant_hec["pediatric_dosing_notes"]


def test_calculate_risk_adjusted_regimen_modifiers() -> None:
    """Verifies risk-adjusted regimen modifications and mandatory clinician sign-off label."""
    base = get_pogo_guideline_recommendation("High", age=9, route="IV")["recommended_backbone"]
    adjusted = calculate_risk_adjusted_regimen(
        base_regimen=base,
        patient_risk_factors=["prior_cinv", "anticipatory_nausea", "cns_tumor"],
    )
    assert adjusted["advisory_status"] == ADVISORY_LABEL
    assert len(adjusted["adjustments_applied"]) == 3
    assert "Olanzapine" in adjusted["personalized_regimen_summary"]
    assert "Lorazepam" in adjusted["personalized_regimen_summary"]
    assert "Omit Dexamethasone" in adjusted["personalized_regimen_summary"]


def test_guideline_search_pages() -> None:
    """Phase 4 Acceptance: search_guidelines('dexamethasone', ctx) returns hits with page numbers from both PDFs."""
    ctx = SimpleNamespace(state={})
    res = search_guidelines("dexamethasone", ctx)
    passages = res["passages"]
    assert len(passages) >= 2
    source_types = {p["source_type"] for p in passages}
    assert "hospital" in source_types
    assert "external" in source_types
    assert all(isinstance(p["page"], int) and p["page"] >= 1 for p in passages)
    assert passages[0]["id"] == "S1"
    assert len(ctx.state["facts_evidence"]) == len(passages)


def test_passport_days_and_ml_only() -> None:
    """Phase 5 Acceptance: for 5-day chemo, days 1-7 present, only mL volumes, times from SCHEDULE_RULES, NL Dutch text."""
    ctx = SimpleNamespace(state={})
    compute_antiemetic_doses(
        antiemetics=["ondansetron", "aprepitant", "dexamethasone", "olanzapine"],
        weight_kg=24.0,
        height_cm=120.0,
        route="PO",
        tool_context=ctx,
    )
    pass_en = build_parent_passport(language="en", chemo_days=5, tool_context=ctx)
    assert [d["day"] for d in pass_en["days"]] == [1, 2, 3, 4, 5, 6, 7]

    allowed_times = {t for r in SCHEDULE_RULES for t in r["clock_times"]}
    for day in pass_en["days"]:
        for entry in day["entries"]:
            assert set(entry.keys()) == {"time", "drug", "volume_ml"}
            assert entry["time"] in allowed_times
            assert isinstance(entry["volume_ml"], float)

    pass_nl = build_parent_passport(language="nl", chemo_days=5, tool_context=ctx)
    assert "ochtend" in pass_nl["instructions"]["ondansetron"]["instruction"].lower()


def test_guardrail_callback() -> None:
    """Phase 6 Acceptance: unsupported mg values removed; supported values pass; missing ADVISORY_LABEL appended."""
    ctx = SimpleNamespace(
        state={
            "facts_doses": {
                "doses": [
                    {"drug": "ondansetron", "dose_mg": 4.5, "actual_dose_mg": 4.4, "volume_ml": 5.5}
                ]
            },
            "facts_evidence": [{"id": "S1", "file": "Anti-emetica beleid CINV - V2.pdf", "page": 2}],
        }
    )

    # 1. Draft with unsupported 12 mg gets edited
    bad_resp = LlmResponse(
        content=types.Content(
            role="model",
            parts=[
                types.Part.from_text(
                    text=f"Give Ondansetron 4.5 mg (5.5 mL) per UZA policy [S1]. Also give 12 mg extra.\n\n{ADVISORY_LABEL}"
                )
            ],
        )
    )
    edited = guard(ctx, bad_resp)
    assert edited is not None
    edited_text = edited.content.parts[0].text
    assert "Guardrail: unsupported values removed" in edited_text
    assert "12 mg" not in edited_text
    assert "4.5 mg" in edited_text
    assert ADVISORY_LABEL in edited_text

    # 2. Draft with only supported fact values and advisory label passes unchanged (returns None)
    good_resp = LlmResponse(
        content=types.Content(
            role="model",
            parts=[
                types.Part.from_text(
                    text=f"Give Ondansetron 4.5 mg (5.5 mL) per UZA policy [S1].\n\n{ADVISORY_LABEL}"
                )
            ],
        )
    )
    assert guard(ctx, good_resp) is None

    # 3. Draft without ADVISORY_LABEL gets it appended
    no_label_resp = LlmResponse(
        content=types.Content(
            role="model",
            parts=[types.Part.from_text(text="Give Ondansetron 4.5 mg (5.5 mL) per UZA policy [S1].")],
        )
    )
    appended = guard(ctx, no_label_resp)
    assert appended is not None
    assert appended.content.parts[0].text.endswith(ADVISORY_LABEL)

