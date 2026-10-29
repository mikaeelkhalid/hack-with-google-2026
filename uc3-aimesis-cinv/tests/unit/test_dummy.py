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
"""Unit tests for AImesis (uc3-aimesis-cinv) deterministic tools and ADK agent wiring."""

from app.agent import (
    ADVISORY_LABEL,
    calculate_risk_adjusted_regimen,
    check_ddi_interactions,
    classify_regimen_emetogenicity,
    get_pogo_guideline_recommendation,
    root_agent,
)


def test_root_agent_wiring() -> None:
    """Verifies root_agent configuration and registered tool functions."""
    assert root_agent.name == "uc3_aimesis_cinv"
    assert root_agent.model == "gemini-2.5-flash"
    tool_names = [t.__name__ for t in root_agent.tools]
    assert tool_names == [
        "classify_regimen_emetogenicity",
        "check_ddi_interactions",
        "get_pogo_guideline_recommendation",
        "calculate_risk_adjusted_regimen",
    ]


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

    # Casus 2 (ALLTogether1 Induction B D8): Vincristine (Minimal) + Daunorubicin (Moderate) -> Moderate
    casus_2_all = classify_regimen_emetogenicity(["vincristine", "daunorubicin"])
    assert casus_2_all["overall_emetogenic_tier"] == "Moderate"


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
