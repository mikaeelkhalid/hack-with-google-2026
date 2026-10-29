# Copyright 2026 Google LLC
# Author: Jerome CG Paquay (@jpaquay)
# Clinical Leads: Katleen Balliauw & Anthe De Pauw (Hospital Pharmacists, UZA)
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

"""AImesis (uc3-aimesis-cinv): Pediatric CINV Clinical Decision Support ADK Agent.

Grounded in:
  1. UZA Hospital Protocol Baseline: `Anti-emetica beleid CINV - V2.pdf` (July 2026 Versie 2, p.1-2)
  2. POGO Emetogenicity Classification Guideline: `POGO Emetogenicity Classification Guideline Final-rev- 250111.pdf`
  3. UZA Clinical Case Examples: `casus voorbeelden.docx` (Casus 1: HR-NBL2 RAPID COJEC, Casus 2: ALLTogether1 Inductie B, Casus 3: iEuroEwing 5-day IE)
  4. Official AImesis User Stories v2 (`user stories AImesis version 2.pdf`) & Pitch/Briefing Slides
  5. Belgian Family CINV Resources (`CINV resources in Belgium.xlsx`)
"""

from __future__ import annotations

from typing import Any

from google.adk.agents import Agent
from google.adk.apps import App

from app.dosing import compute_antiemetic_doses
from app.guardrail import guard
from app.guidelines import search_guidelines
from app.passport import build_parent_passport
from app.tables import (
    ADVISORY_LABEL,
    COMBINATION_ESCALATION_RULES,
    NK1_ANTAGONISTS,
    PEDIATRIC_CHEMO_EMETOGENICITY,
    QTC_PROLONGING_AGENTS,
    QTC_RISK_REGISTRY,
    RANK_TO_TIER,
    STRONG_MODERATE_AZOLES,
    UZA_CASUS_VOORBEELDEN,
    VINCA_ALKALOIDS,
    usable,
)

MODEL = "gemini-2.5-flash"


def _normalize_drug_name(name: str) -> str:
    """Normalizes free-text drug strings to canonical lowercase lookup keys."""
    cleaned = name.strip().lower()
    aliases = {
        "5-fu": "fluorouracil",
        "5-fluorouracil": "fluorouracil",
        "actinomycin d": "dactinomycin",
        "actinomycin-d": "dactinomycin",
        "6-mp": "mercaptopurine",
        "6-mercaptopurine": "mercaptopurine",
        "ara-c": "cytarabine",
        "hd-mtx": "methotrexate",
        "mtx": "methotrexate",
        "vcr": "vincristine",
        "cdpp": "cisplatin",
        "emend": "aprepitant",
        "zofran": "ondansetron",
        "kytril": "granisetron",
        "aloxi": "palonosetron",
        "decadron": "dexamethasone",
        "zyprexa": "olanzapine",
        "ativan": "lorazepam",
        "vfend": "voriconazole",
        "noxafil": "posaconazole",
        "diflucan": "fluconazole",
    }
    return aliases.get(cleaned, cleaned)


def classify_regimen_emetogenicity(chemo_drugs_list: list[str]) -> dict[str, Any]:
    """Classifies individual pediatric chemotherapy drugs and overall regimen emetogenicity.

    Evaluates each chemotherapy agent against UZA July 2026 v2 (`Anti-emetica beleid CINV - V2.pdf` p.1)
    and POGO (`POGO 250111`) pediatric antineoplastic emetogenicity classifications
    (High, Moderate, Low, Minimal) and applies multi-agent synergy escalation rules.

    Args:
        chemo_drugs_list: List of chemotherapy drug names in the patient's regimen
            (e.g., ["cisplatin", "doxorubicin"]).

    Returns:
        A dictionary containing per-drug emetogenicity details, the overall regimen
        emetogenic tier, whether multi-agent synergy escalation was applied,
        verifiable `sources` / `unverified_sources`, and `needs_clinician_review`.
    """
    if not chemo_drugs_list:
        return {
            "regimen_drugs": [],
            "per_drug_classification": [],
            "overall_emetogenic_tier": "Minimal",
            "synergy_escalation_applied": False,
            "guideline_reference": "UZA Anti-emetica beleid CINV v2 p.1 & POGO 250111",
            "clinical_rationale": "No chemotherapy agents provided; defaulted to Minimal emetic risk.",
            "sources": [],
            "unverified_sources": [],
            "needs_clinician_review": False,
            "advisory_status": ADVISORY_LABEL,
        }

    per_drug: list[dict[str, Any]] = []
    max_rank = 0
    moderate_count = 0
    normalized_set: set[str] = set()
    sources: set[str] = set()
    unverified_sources: set[str] = set()
    needs_clinician_review = False

    for raw_drug in chemo_drugs_list:
        norm = _normalize_drug_name(raw_drug)
        normalized_set.add(norm)
        info = PEDIATRIC_CHEMO_EMETOGENICITY.get(norm)
        if info and usable(info):
            rank = info["rank"]
            max_rank = max(max_rank, rank)
            if rank == 3:
                moderate_count += 1
            src = info.get("source", "UZA CINV v2 p.1")
            sources.add(src)
            if not info.get("verified"):
                unverified_sources.add(src)
            per_drug.append(
                {
                    "input_name": raw_drug,
                    "canonical_name": norm,
                    "emetogenic_tier": info["tier"],
                    "uza_tier": info.get("uza_tier", info["tier"]),
                    "pogo_tier": info.get("pogo_tier", info["tier"]),
                    "emetic_frequency_pct": info["emetic_frequency_pct"],
                    "clinical_notes": info["notes"],
                    "source": src,
                    "verified": bool(info.get("verified")),
                }
            )
        else:
            needs_clinician_review = True
            if info and not usable(info):
                unverified_sources.add(info.get("source", "UZA CINV v2 p.1"))
            max_rank = max(max_rank, 2)
            per_drug.append(
                {
                    "input_name": raw_drug,
                    "canonical_name": norm,
                    "emetogenic_tier": "Unknown (Unverified or Unlisted — Clinician Review Required)",
                    "emetic_frequency_pct": "Unknown (manual UZA v2 / POGO lookup required)",
                    "clinical_notes": (
                        "Agent not usable without clinician verification or not in baseline table."
                    ),
                    "source": info.get("source", "p.TODO") if info else "p.TODO",
                    "verified": False,
                }
            )

    synergy_escalation = False
    synergy_reason = "Overall tier determined by the single most emetogenic agent in the regimen (UZA v2 / POGO rule)."

    # Evaluate combination escalation rules from app.tables.COMBINATION_ESCALATION_RULES
    for combo_rule in COMBINATION_ESCALATION_RULES:
        req = combo_rule.get("required_drugs")
        any_of = combo_rule.get("any_of_drugs")
        min_mod = combo_rule.get("min_moderate_count")

        matched = False
        if req and req.issubset(normalized_set):
            if any_of is None or bool(normalized_set.intersection(any_of)):
                matched = True
        elif min_mod and moderate_count >= min_mod and max_rank == 3:
            matched = True

        if matched:
            if usable(combo_rule):
                max_rank = max(max_rank, int(combo_rule["rank"]))
                synergy_escalation = True
                synergy_reason = combo_rule["rationale"]
                c_src = combo_rule.get("source", "UZA CINV v2 p.1")
                sources.add(c_src)
                if not combo_rule.get("verified"):
                    unverified_sources.add(c_src)
            else:
                needs_clinician_review = True
                unverified_sources.add(combo_rule.get("source", "UZA CINV v2 p.1"))
            break

    overall_tier = (
        "Unknown"
        if (needs_clinician_review and not sources)
        else RANK_TO_TIER.get(max_rank, "Minimal")
    )

    return {
        "regimen_drugs": chemo_drugs_list,
        "per_drug_classification": per_drug,
        "overall_emetogenic_tier": overall_tier,
        "synergy_escalation_applied": synergy_escalation,
        "guideline_reference": "UZA Anti-emetica beleid CINV v2 p.1 & POGO 250111 Emetogenicity Guidelines",
        "clinical_rationale": synergy_reason,
        "sources": sorted(sources),
        "unverified_sources": sorted(unverified_sources),
        "needs_clinician_review": needs_clinician_review,
        "advisory_status": ADVISORY_LABEL,
    }


def check_ddi_interactions(
    primary_drugs: list[str], proposed_antiemetics: list[str]
) -> dict[str, Any]:
    """Screens for pharmacokinetic (CYP3A4) and pharmacodynamic (QTc, neurotoxicity) DDIs.

    Evaluates drug-drug interactions between primary chemotherapy / concomitant medications
    (such as azole antifungals: voriconazole, posaconazole, itraconazole, fluconazole) and
    proposed antiemetic agents (ondansetron, granisetron, palonosetron, aprepitant,
    fosaprepitant, dexamethasone, olanzapine, lorazepam, domperidone, haloperidol).

    Args:
        primary_drugs: List of primary chemotherapy agents and concomitant medications
            (e.g., ["cisplatin", "doxorubicin", "voriconazole"]).
        proposed_antiemetics: List of proposed antiemetic drugs
            (e.g., ["ondansetron", "aprepitant", "dexamethasone"]).

    Returns:
        A dictionary containing detected interactions, severity ratings, QTc prolongation
        assessment, actionable dose/regimen modifications, and clinical rationale.
    """
    norm_primary = {_normalize_drug_name(d) for d in primary_drugs}
    norm_antiemetics = {_normalize_drug_name(d) for d in proposed_antiemetics}
    all_drugs = norm_primary.union(norm_antiemetics)

    interactions: list[dict[str, str]] = []
    modifications: list[str] = []
    severity_rank = 0  # 0=None, 1=Low, 2=Moderate, 3=High, 4=Critical/Contraindicated
    sources: set[str] = {"UZA CINV v2 p.2", "CredibleMeds / POGO 250111"}
    unverified_sources: set[str] = set()
    needs_clinician_review = False

    for d in all_drugs:
        qtc_row = QTC_RISK_REGISTRY.get(d)
        if qtc_row:
            sources.add(qtc_row["source"])
            if not qtc_row.get("verified"):
                unverified_sources.add(qtc_row["source"])
            if not usable(qtc_row):
                needs_clinician_review = True

    present_azoles = sorted(all_drugs.intersection(STRONG_MODERATE_AZOLES))
    present_nk1 = sorted(all_drugs.intersection(NK1_ANTAGONISTS))
    present_vincas = sorted(all_drugs.intersection(VINCA_ALKALOIDS))
    present_qtc = sorted(all_drugs.intersection(QTC_PROLONGING_AGENTS))

    # 1. Azole antifungal + NK1 receptor antagonist (aprepitant / fosaprepitant)
    if present_azoles and present_nk1:
        severity_rank = max(severity_rank, 4)
        interactions.append(
            {
                "interacting_pair": f"{', '.join(present_azoles)} + {', '.join(present_nk1)}",
                "severity": "CRITICAL / CONTRAINDICATED-OR-MAJOR-ADJUSTMENT",
                "mechanism": (
                    "Strong/moderate CYP3A4 inhibition by azole antifungals markedly increases "
                    "aprepitant/fosaprepitant systemic AUC and toxicity risk; aprepitant also acts "
                    "as a moderate CYP3A4 inhibitor/inducer altering azole trough levels."
                ),
                "clinical_action": (
                    "Omit or defer aprepitant/fosaprepitant while on strong CYP3A4 inhibitor azoles "
                    "(voriconazole/posaconazole/itraconazole), OR consult pediatric oncology clinical "
                    "pharmacist for therapeutic drug monitoring (TDM) and alternative prophylaxis."
                ),
            }
        )
        modifications.append(
            f"Hold/omit {', '.join(present_nk1)} during concomitant {', '.join(present_azoles)} therapy "
            "due to bidirectional CYP3A4 interaction; rely on 5-HT3 antagonist + CYP3A4-adjusted dexamethasone."
        )

    # 2. Aprepitant/Fosaprepitant OR Azoles + Dexamethasone (CYP3A4 inhibition -> 2x steroid exposure)
    if "dexamethasone" in norm_antiemetics and (present_nk1 or present_azoles):
        severity_rank = max(severity_rank, 3)
        inhibitors = sorted(set(present_nk1 + present_azoles))
        interactions.append(
            {
                "interacting_pair": f"{', '.join(inhibitors)} + dexamethasone",
                "severity": "HIGH (Mandatory Dose Adjustment)",
                "mechanism": (
                    "CYP3A4 inhibition by aprepitant/fosaprepitant and/or azole antifungals "
                    "reduces dexamethasone clearance by ~50%, doubling systemic corticosteroid exposure."
                ),
                "clinical_action": (
                    "Reduce antiemetic dexamethasone dose by 50% (per UZA v2 p.2 & POGO/MASCC guidelines: "
                    "BSA <0.6 m2 -> 1 mg 2x/d; BSA >=0.6 m2 -> 2 mg 2x/d) when co-administered with "
                    "aprepitant/fosaprepitant or strong CYP3A4-inhibiting azoles."
                ),
            }
        )
        modifications.append(
            "Reduce antiemetic dexamethasone dose by 50% (e.g., from 4 mg to 2 mg 2x/d for BSA >=0.6 m2, or 2 mg to 1 mg 2x/d for BSA <0.6 m2) due to CYP3A4 inhibition."
        )

    # 3. Additive QTc Prolongation (e.g., ondansetron + azole / anthracycline / olanzapine / domperidone / haloperidol)
    if len(present_qtc) >= 2:
        has_ondansetron_plus_azole = "ondansetron" in all_drugs and bool(present_azoles)
        has_high_risk_dopamine = bool(all_drugs.intersection({"domperidone", "haloperidol"}))
        qtc_sev = (
            "HIGH"
            if has_ondansetron_plus_azole or has_high_risk_dopamine or len(present_qtc) >= 3
            else "MODERATE"
        )
        severity_rank = max(severity_rank, 3 if qtc_sev == "HIGH" else 2)
        interactions.append(
            {
                "interacting_pair": " + ".join(present_qtc),
                "severity": f"{qtc_sev} (Additive QTc Prolongation)",
                "mechanism": (
                    "Additive blockade of cardiac hERG potassium channels increases risk of QTc "
                    "interval prolongation and Torsades de Pointes."
                ),
                "clinical_action": (
                    "Obtain baseline and on-treatment 12-lead ECG; maintain serum K+ >= 4.0 mmol/L "
                    "and Mg2+ >= 0.8 mmol/L. Avoid domperidone/haloperidol; consider substituting "
                    "ondansetron with palonosetron or granisetron if QTc > 460 ms."
                ),
            }
        )
        modifications.append(
            f"Perform baseline ECG and electrolyte optimization (K+, Mg2+) for additive QTc risk ({', '.join(present_qtc)}); "
            "prefer palonosetron or granisetron over high-dose IV ondansetron if QTc is borderline."
        )

    # 4. Aprepitant/Fosaprepitant + Ifosfamide (Neurotoxic metabolite risk)
    if "ifosfamide" in norm_primary and present_nk1:
        severity_rank = max(severity_rank, 3)
        interactions.append(
            {
                "interacting_pair": f"ifosfamide + {', '.join(present_nk1)}",
                "severity": "MODERATE-HIGH (Ifosfamide Encephalopathy Risk)",
                "mechanism": (
                    "CYP3A4 modulation by aprepitant may shift ifosfamide metabolism toward neurotoxic "
                    "chloroacetaldehyde, increasing pediatric encephalopathy risk."
                ),
                "clinical_action": (
                    "Monitor closely for somnolence, confusion, or cerebellar signs; ensure methylene "
                    "blue / thiamine rescue protocol readiness or evaluate NK1 risk-benefit with pharmacist."
                ),
            }
        )
        modifications.append(
            "Institute neurological monitoring for ifosfamide-induced encephalopathy when co-administering aprepitant."
        )

    # 5. Azole Antifungals + Vinca Alkaloids (Severe neurotoxicity / paralytic ileus)
    if present_azoles and present_vincas:
        severity_rank = max(severity_rank, 4)
        interactions.append(
            {
                "interacting_pair": f"{', '.join(present_azoles)} + {', '.join(present_vincas)}",
                "severity": "CRITICAL (Chemo-Azole Neurotoxicity Alert)",
                "mechanism": (
                    "Inhibition of CYP3A4 and P-glycoprotein by azoles blocks vinca alkaloid clearance, "
                    "causing severe peripheral/autonomic neuropathy, vocal cord palsy, and paralytic ileus."
                ),
                "clinical_action": (
                    "Hold azole antifungal 24-48 hours prior to and after vincristine/vinblastine "
                    "administration per institutional pediatric oncology pharmacy protocol."
                ),
            }
        )
        modifications.append(
            f"CRITICAL PHARMACY ALERT: Hold {', '.join(present_azoles)} around {', '.join(present_vincas)} dosing to prevent severe neurotoxicity."
        )

    # 6. Palonosetron + Ondansetron co-prescription check (UZA v2 p.2 rule)
    if "palonosetron" in norm_antiemetics and "ondansetron" in norm_antiemetics:
        severity_rank = max(severity_rank, 4)
        interactions.append(
            {
                "interacting_pair": "palonosetron + ondansetron",
                "severity": "CRITICAL (Duplicate 5-HT3 Blockade Contraindicated Within 3 Days)",
                "mechanism": (
                    "Palonosetron has a 40-hour half-life and high allosteric 5-HT3 receptor affinity; "
                    "UZA CINV v2 p.2 explicitly prohibits combining Palonosetron with Ondansetron within 3 days."
                ),
                "clinical_action": "Do not administer Ondansetron within 72 hours (3 days) after single-dose IV Palonosetron.",
            }
        )
        modifications.append(
            "Do NOT combine Palonosetron with Ondansetron during the first 3 days post-Palonosetron (UZA CINV v2 p.2)."
        )

    severity_map = {
        0: "NONE",
        1: "LOW",
        2: "MODERATE",
        3: "HIGH",
        4: "CRITICAL",
    }

    return {
        "primary_drugs_evaluated": primary_drugs,
        "proposed_antiemetics_evaluated": proposed_antiemetics,
        "interactions_count": len(interactions),
        "highest_severity": severity_map[severity_rank],
        "qtc_prolonging_drugs_detected": present_qtc,
        "qtc_prolongation_risk": (
            "ELEVATED" if len(present_qtc) >= 2 else ("LOW-BASELINE" if present_qtc else "MINIMAL")
        ),
        "interactions_found": interactions,
        "recommended_modifications": modifications
        or ["No major pharmacokinetic or QTc adjustments required for the evaluated drug set."],
        "safe_to_proceed_without_modification": severity_rank <= 1,
        "sources": sorted(sources),
        "unverified_sources": sorted(unverified_sources),
        "needs_clinician_review": needs_clinician_review,
        "advisory_status": ADVISORY_LABEL,
    }


def get_pogo_guideline_recommendation(
    emetogenic_tier: str, age: int, route: str = "IV"
) -> dict[str, Any]:
    """Retrieves the baseline UZA v2 & POGO/MASCC pediatric antiemetic prophylaxis regimen.

    Aligns the chemotherapy emetogenic tier with age-stratified pediatric dosing rules
    (<1 year, 1-11 years, >=12 years) and preferred administration route (IV or PO)
    according to UZA July 2026 v2 (`Anti-emetica beleid CINV - V2.pdf` p.1-2) and POGO 250111.

    Args:
        emetogenic_tier: Emetogenicity classification ("High", "Moderate", "Low", "Minimal").
        age: Patient age in years (use 0 for infants under 1 year of age).
        route: Administration route ("IV" or "PO"). Defaults to "IV".

    Returns:
        A dictionary containing the baseline antiemetic regimen, proposed antiemetic drug
        names for downstream DDI checking, age-specific dosing notes, and UZA/POGO citations.
    """
    tier = emetogenic_tier.strip().capitalize()
    norm_route = route.strip().upper() if route else "IV"
    if norm_route not in {"IV", "PO"}:
        norm_route = "IV"

    if age < 1:
        age_stratum = "Infant (<1 year)"
    elif age < 12:
        age_stratum = "Child (1-11 years)"
    else:
        age_stratum = "Adolescent (>=12 years)"

    probe_row = PEDIATRIC_CHEMO_EMETOGENICITY.get("cisplatin", {"verified": False, "source": "UZA CINV v2 p.1-2 & POGO 250111"})
    is_usable = usable(probe_row)
    sources = ["UZA CINV v2 p.1-2", "POGO 250111 p.18-24"]
    unverified_sources = list(sources) if not probe_row.get("verified") else []

    if tier == "High":
        if age < 1:
            backbone = (
                f"5-HT3 Antagonist (Ondansetron 5 mg/m2 {norm_route} 3x/d [UZA v2] / 0.15 mg/kg q8h [POGO]) + "
                f"Dexamethasone (UZA BSA <0.6 m2: 1-2 mg 2x/d {norm_route}) + "
                "Aprepitant (ONLY if infant is >=6 months and >6 kg: 3 mg/kg PO Day 1, 2 mg/kg PO Days 2-3)"
            )
            drugs = ["ondansetron", "dexamethasone", "aprepitant"]
            dosing_notes = (
                "Infants <6 months (or <=6 kg): omit aprepitant (no indication <6 months per UZA v2 p.2) and olanzapine (<2y); "
                "use dual therapy (Ondansetron + Dexamethasone). Infants 6-11 months (>6 kg): triple therapy with weight-based "
                "aprepitant oral suspension + 50% reduced dexamethasone."
            )
        elif age < 12:
            backbone = (
                f"UZA v2 Quadruple / POGO Triple Therapy: Ondansetron (5 mg/m2 {norm_route} 3x/d, max 8 mg/dose) + "
                "Aprepitant (3 mg/kg PO Day 1 [max 125 mg], 2 mg/kg PO Days 2-3 [max 80 mg]) + "
                f"Dexamethasone (UZA BSA <0.6 m2: 1 mg 2x/d; >=0.6 m2: 2 mg 2x/d {norm_route} [50% reduced for aprepitant CYP3A4]) + "
                "Olanzapine (if age >=2y: 0.1 mg/kg PO 1x/d, max 5 mg, rounded DOWN to nearest 0.5 mg)"
            )
            drugs = ["ondansetron", "aprepitant", "dexamethasone", "olanzapine"] if age >= 2 else ["ondansetron", "aprepitant", "dexamethasone"]
            dosing_notes = (
                "UZA v2 p.1-2 HEC quadruple prophylaxis (Ondansetron 3x/d + Dexamethasone + Aprepitant + Olanzapine >=2y) "
                "vs POGO HEC triple prophylaxis. Dexamethasone dose reflects mandatory 50% reduction when co-administered with aprepitant."
            )
        else:
            backbone = (
                f"UZA v2 Quadruple / POGO Triple Therapy: Ondansetron (5 mg/m2 {norm_route} 3x/d, max 8 mg/dose) OR "
                "Palonosetron (<17y: 20 mcg/kg IV max 1500 mcg; >=17y: 250 mcg single dose) + "
                "Aprepitant (125 mg PO Day 1, 80 mg PO Days 2-3) + "
                f"Dexamethasone (2 mg 2x/d {norm_route}/PO with aprepitant; 4 mg 2x/d without) + "
                "Olanzapine (0.1 mg/kg PO 1x/d, max 5 mg, rounded DOWN to nearest 0.5 mg)"
            )
            drugs = ["ondansetron", "aprepitant", "dexamethasone", "olanzapine"]
            dosing_notes = (
                "Adolescent (>=12 years) UZA v2 HEC quadruple regimen (Ondansetron 3x/d + Dexamethasone + Aprepitant + Olanzapine). "
                "Note: IV Aacidexam® 5 mg/mL contains ±4 mg/mL active dexamethasone base."
            )
        citation = (
            "UZA Anti-emetica beleid CINV v2 p.1-2 (HOOG EMETOGEEN) & POGO Guideline for Prevention of Acute and Delayed CINV"
        )
    elif tier == "Moderate":
        backbone = (
            f"Dual Therapy (UZA v2 MATIG EMETOGEEN): Ondansetron (5 mg/m2 {norm_route} 2x/d, max 8 mg/dose) + "
            f"Dexamethasone (BSA <0.6 m2: 2 mg 2x/d; >=0.6 m2: 4 mg 2x/d {norm_route}/PO) OF Aprepitant (if steroids contraindicated)"
        )
        drugs = ["ondansetron", "dexamethasone"]
        dosing_notes = (
            f"UZA v2 & POGO MEC dual prophylaxis for {age_stratum} (Ondansetron 2x/d + Dexamethasone OR Aprepitant). "
            "If corticosteroids are contraindicated ('GEEN Dexamethasone' in ALL [Casus 2], CNS/brain tumor, Dinutuximab beta), "
            "substitute Aprepitant (if age >=6 months and >6 kg) + Ondansetron 2x/d."
        )
        citation = "UZA Anti-emetica beleid CINV v2 p.1-2 (MATIG EMETOGEEN) & POGO Pediatric MEC Prophylaxis Guideline"
    elif tier == "Low":
        backbone = (
            f"Monotherapy (UZA v2 LAAG EMETOGEEN): Ondansetron (5 mg/m2 {norm_route} 1x/d pre-chemo, max 8 mg)"
        )
        drugs = ["ondansetron"]
        dosing_notes = f"UZA v2 & POGO LEC single-agent 5-HT3 antagonist prophylaxis for {age_stratum}; no routine steroid or NK1 needed."
        citation = "UZA Anti-emetica beleid CINV v2 p.1 (LAAG EMETOGEEN) & POGO Pediatric LEC Prophylaxis Guideline"
    else:
        tier = "Minimal"
        backbone = "No routine antiemetic prophylaxis recommended (Geen standaard profylaxe)."
        drugs = []
        dosing_notes = (
            f"For {age_stratum} receiving Minimal emetogenic risk chemotherapy, administer antiemetics "
            "only if the patient experienced CINV on a prior identical cycle."
        )
        citation = "UZA Anti-emetica beleid CINV v2 p.1 (MINIMAAL EMETOGEEN) & POGO Minimal Emetic Risk Guideline"

    return {
        "emetogenic_tier": tier,
        "patient_age_years": age,
        "age_stratum": age_stratum,
        "route": norm_route,
        "recommended_backbone": backbone,
        "proposed_antiemetics_list": drugs,
        "pediatric_dosing_notes": dosing_notes,
        "guideline_citations": [citation, "MASCC/ESMO Pediatric Antiemetic Consensus Update"],
        "sources": sources,
        "unverified_sources": unverified_sources,
        "needs_clinician_review": not is_usable,
        "advisory_status": ADVISORY_LABEL,
    }


def calculate_risk_adjusted_regimen(
    base_regimen: str, patient_risk_factors: list[str]
) -> dict[str, Any]:
    """Tailors the baseline antiemetic regimen to patient-specific clinical risk factors.

    Adjusts antiemetic selection and adjunct therapies based on pediatric patient risk
    modifiers (prior CINV, anticipatory nausea/anxiety, motion sickness, steroid
    contraindications/CNS tumor/ALL, baseline QTc prolongation, infant <6 months, or
    concomitant azoles) and enforces the clinician sign-off safety label.

    Args:
        base_regimen: The baseline UZA/POGO-recommended regimen string.
        patient_risk_factors: List of patient risk factor strings (e.g.,
            ["prior_cinv", "high_anxiety", "voriconazole_concomitant"]).

    Returns:
        A dictionary containing the personalized risk-adjusted regimen, specific
        clinical adjustments applied, rationale per risk factor, and the mandatory
        "Advisory Only — Requires Clinician Sign-Off" label.
    """
    normalized_factors = [f.strip().lower() for f in patient_risk_factors if f.strip()]
    adjustments: list[dict[str, str]] = []
    final_components: list[str] = [f"Baseline Backbone: {base_regimen}"]
    probe_row = PEDIATRIC_CHEMO_EMETOGENICITY.get("cisplatin", {"verified": False})
    sources = ["UZA CINV v2 p.1-2", "POGO 250111 p.20-28"]
    unverified_sources = list(sources) if not probe_row.get("verified") else []

    for factor in normalized_factors:
        if any(k in factor for k in ("prior_cinv", "refractory", "breakthrough", "previous_cinv")):
            adjustments.append(
                {
                    "risk_factor": factor,
                    "modification": (
                        "Add Olanzapine (0.1 mg/kg/dose PO 1x/d, max 5 mg, rounded DOWN to nearest 0.5 mg; if age >=2 years) "
                        "or escalate prophylaxis by one tier; consider switching Ondansetron to IV Palonosetron (never combine within 3 days) "
                        "or adding breakthrough Alizapride (1 mg/kg max 50 mg) / Lorazepam (0.025-0.05 mg/kg max 2 mg q6h)."
                    ),
                    "rationale": (
                        "Prior poorly controlled CINV is the strongest predictor of breakthrough emesis in subsequent cycles (UZA CINV v2 p.2 & POGO Breakthrough Guideline)."
                    ),
                }
            )
            final_components.append(
                "Escalation for Prior/Refractory CINV: Add scheduled Olanzapine (0.1 mg/kg/day PO rounded down to 0.5 mg, max 5 mg) and switch 5-HT3 antagonist to Palonosetron or add Alizapride/Lorazepam."
            )

        if any(k in factor for k in ("anticipatory", "anxiety", "phobia")):
            adjustments.append(
                {
                    "risk_factor": factor,
                    "modification": (
                        "Add Lorazepam (0.04-0.08 mg/kg PO/IV, max 2 mg per UZA v2 p.2; or 0.025-0.05 mg/kg) the evening before chemo and "
                        "1-2 hours pre-infusion + behavioral/distraction therapy."
                    ),
                    "rationale": (
                        "Conditioned anticipatory CINV responds to GABA-A anxiolysis (lorazepam) combined with psychological desensitization (UZA CINV v2 p.2 & POGO Anticipatory CINV Guideline)."
                    ),
                }
            )
            final_components.append(
                "Anticipatory Nausea/Anxiety Adjunct: Lorazepam 0.04-0.08 mg/kg (max 2 mg) PO/IV night before and 1-2h pre-chemo + behavioral therapy."
            )

        if "motion_sickness" in factor or "vestibular" in factor:
            adjustments.append(
                {
                    "risk_factor": factor,
                    "modification": (
                        "Maintain strict scheduled pre-infusion 5-HT3 + NK1/corticosteroid timing; minimize rapid position changes during infusion."
                    ),
                    "rationale": (
                        "History of motion sickness increases vestibular susceptibility to chemotherapy-triggered emesis."
                    ),
                }
            )
            final_components.append(
                "Vestibular Susceptibility Note: Enforce strict 30-60 min pre-infusion prophylaxis timing."
            )

        if any(k in factor for k in ("cns_tumor", "brain_tumor", "hersentumor", "steroid_contraindicated", "no_steroid", "all_protocol", "dinutuximab")):
            adjustments.append(
                {
                    "risk_factor": factor,
                    "modification": (
                        "OMIT Dexamethasone ('GEEN Dexamethasone' per UZA CINV v2 p.2); substitute with Aprepitant (if age >=6 months and >6 kg and no azole DDI) + "
                        "Ondansetron/Palonosetron +/- Olanzapine."
                    ),
                    "rationale": (
                        "Systemic corticosteroids are strictly contraindicated in ALL protocols (Casus 2), brain tumors (hersentumoren), Dinutuximab beta, and steroid-containing chemo (UZA CINV v2 p.2)."
                    ),
                }
            )
            final_components.append(
                "Steroid-Sparing Substitution: Omit Dexamethasone; use 5-HT3 antagonist + Aprepitant (or Olanzapine if NK1 contraindicated)."
            )

        if any(k in factor for k in ("qtc", "arrhythmia", "long_qt")):
            adjustments.append(
                {
                    "risk_factor": factor,
                    "modification": (
                        "Prefer Palonosetron or standard-dose Granisetron over high-dose IV Ondansetron; "
                        "avoid Olanzapine/domperidone/haloperidol; mandate ECG and K+ >=4.0 / Mg2+ >=0.8 mmol/L."
                    ),
                    "rationale": (
                        "Minimizes additive hERG channel blockade in patients with baseline QTc prolongation or concomitant QTc-prolonging drugs."
                    ),
                }
            )
            final_components.append(
                "Cardiac/QTc Safety Guardrail: Substitute high-dose Ondansetron with Palonosetron/Granisetron; verify ECG and K+/Mg2+."
            )

        if any(k in factor for k in ("under_6_months", "infant_under_6m", "<6m", "neonate")):
            adjustments.append(
                {
                    "risk_factor": factor,
                    "modification": (
                        "Exclude Aprepitant/Fosaprepitant (<6m or <=6 kg: geen indicatie) and Olanzapine (<2y: geen indicatie); rely on weight/BSA-adjusted Ondansetron +/- Dexamethasone."
                    ),
                    "rationale": (
                        "Aprepitant is indicated only for infants >=6 months (>6 kg) and Olanzapine >=2 years per UZA CINV v2 p.2."
                    ),
                }
            )
            final_components.append(
                "Infant (<6 Months) Safety Restriction: Omit Aprepitant and Olanzapine; use Ondansetron +/- Dexamethasone."
            )

        if any(k in factor for k in ("azole", "voriconazole", "posaconazole", "itraconazole")):
            adjustments.append(
                {
                    "risk_factor": factor,
                    "modification": (
                        "Hold/omit Aprepitant due to strong CYP3A4 inhibition by azole antifungal; reduce Dexamethasone dose by 50%; monitor ECG for Ondansetron+Azole QTc risk."
                    ),
                    "rationale": (
                        "Azole antifungals strongly inhibit CYP3A4 (elevating aprepitant and dexamethasone exposure) and prolong QTc."
                    ),
                }
            )
            final_components.append(
                "Azole DDI Adjustment: Omit Aprepitant, reduce Dexamethasone by 50%, and monitor ECG."
            )

        if any(k in factor for k in ("multiday", "5_day", "day_4_nausea", "ie_cycle", "casus_3")):
            adjustments.append(
                {
                    "risk_factor": factor,
                    "modification": (
                        "Enforce full HEC quadruple prophylaxis (Ondansetron 3x/d + Dexamethasone + Aprepitant + Olanzapine) "
                        "and consider extending Aprepitant onto Days 4 and 5 in consultation with the clinical pharmacist."
                    ),
                    "rationale": (
                        "In 5-day multi-day regimens (such as iEuroEwing IE: Ifosfamide + Etoposide, Casus 3) with prior "
                        "Day 4 breakthrough nausea, standard 3-day Aprepitant may leave late-cycle days unprotected."
                    ),
                }
            )
            final_components.append(
                "Multi-Day Chemo (Casus 3 iEuroEwing IE) Adjustment: Consider extending Aprepitant onto Days 4 and 5 for prior Day 4 breakthrough nausea."
            )

        if any(k in factor for k in ("ondansetron_2xd", "day_2_nausea", "rapid_cojec", "casus_1")):
            adjustments.append(
                {
                    "risk_factor": factor,
                    "modification": (
                        "Increase Ondansetron from 2x/d to full UZA v2 HEC 3x/d frequency (5 mg/m2 max 8 mg 3x/d) "
                        "OR switch to long-acting IV Palonosetron (not combined with Ondansetron within 3 days); "
                        "add breakthrough Alizapride or Lorazepam and log symptoms in the CINV Patient Passport / Companion App."
                    ),
                    "rationale": (
                        "Per UZA July 2026 v2 HEC guidelines and Casus 1 (HR-NBL2 RAPID COJEC Cycle B4), HEC regimens "
                        "require Ondansetron 3x/d (or Palonosetron switch after prior breakthrough nausea)."
                    ),
                }
            )
            final_components.append(
                "Casus 1 (HR-NBL2 RAPID COJEC) Optimization: Step up Ondansetron from 2x/d to 3x/d (or switch to Palonosetron) + log in CINV Companion App."
            )

    if not adjustments:
        adjustments.append(
            {
                "risk_factor": "standard_risk",
                "modification": "Retain baseline POGO/MASCC & UZA v2 prophylaxis regimen without additional escalation.",
                "rationale": "No high-risk patient-specific modifiers identified.",
            }
        )

    return {
        "base_regimen": base_regimen,
        "patient_risk_factors_evaluated": patient_risk_factors,
        "adjustments_applied": adjustments,
        "personalized_regimen_summary": " | ".join(final_components),
        "guideline_citations": [
            "UZA Anti-emetica beleid CINV — Juli 2026 Versie 2 (Katleen Balliauw & Anthe De Pauw, UZA)",
            "POGO Emetogenicity Classification Guideline (Final-rev-250111)",
            "ESMO/MASCC Consensus Recommendations for Pediatric CINV",
        ],
        "sources": sources,
        "unverified_sources": unverified_sources,
        "needs_clinician_review": not usable(probe_row),
        "advisory_status": ADVISORY_LABEL,
    }


SYSTEM_INSTRUCTION = """You are AImesis (uc3_aimesis_cinv), a specialized Pediatric Oncology Clinical Decision Support (CDS) agent for Chemotherapy-Induced Nausea and Vomiting (CINV) control, developed under Clinical Leads Katleen Balliauw & Anthe De Pauw (Hospital Pharmacists, University Hospital Antwerp / UZA).

Your clinical mission is to harmonize multi-agent pediatric chemotherapy regimens with UZA's July 2026 v2 CINV policy (`Anti-emetica beleid CINV - V2.pdf` p.1–2) first and the POGO Emetogenicity Classification Guideline (`POGO Emetogenicity Classification Guideline Final-rev- 250111.pdf`) as the international cross-check, screen for dangerous drug-drug interactions (DDIs) and QTc prolongation, compute exact mg/mL doses via deterministic tools, cite PDF evidence pages (`[S1]`, `[S2]`), and generate a multilingual CINV Parent Passport (EN/NL/FR) with Companion App symptom diary integration.

OFFICIAL UZA CLINICAL CASE EXAMPLES (`casus voorbeelden.docx`):
- **Casus 1 (16yo Girl, Neuroblastoma, HR-NBL2 RAPID COJEC Induction, Cycle B4 = Vincristine + Cisplatin)**:
  * Emetogenicity: Vincristine (Low) + Cisplatin (High) -> Overall **HEC (High Emetogenic)**.
  * Prior Cycle B3 (05/09/2026) EHR / toernota note: Prescribed Ondansetron 2x/d + Aprepitant + Dexamethasone + Olanzapine, but still had breakthrough nausea on Day 2.
  * Action: Ensure full HEC Ondansetron 3x/d dosing (5 mg/m2 max 8 mg 3x/d) or switch to IV Palonosetron (never combined with Ondansetron within 3 days), verify 50% Dexamethasone dose reduction with Aprepitant, continue evening Olanzapine (rounded down to nearest 0.5 mg), and track breakthrough symptoms in the CINV Passport / Companion App.
- **Casus 2 (2yo Boy, Acute Lymphoblastic Leukemia [ALL], ALLTogether1 Induction B, Day 8 = Vincristine + Daunorubicin)**:
  * Emetogenicity: Vincristine (Low) + Daunorubicin (MEC) -> Overall **MEC (Moderate Emetogenic)**.
  * Action: Prescribe **Ondansetron (2x/d) + Aprepitant**. **STRICT CONTRAINDICATION: NO Dexamethasone (`GEEN Dexamethasone bij ALL`)** (also excluded in brain tumors / hersentumoren, dinutuximab beta, AML, CAR-T, and steroid-containing chemo regimens).
- **Casus 3 (Ewing Sarcoma Patient, iEuroEwing Alternating VDC/IE, 5-Day IE Cycle #3 = Ifosfamide + Etoposide)**:
  * Emetogenicity: Ifosfamide alone is MEC and Etoposide alone is LEC, **HOWEVER the combination of Ifosfamide + Etoposide is classified as HEC (High Emetogenic)** per both UZA July 2026 v2 ('Combinatie: Ifosfamide/Etoposide = HOOG EMETOGEEN') and POGO 250111 pediatric studies!
  * Prior cycles: Breakthrough nausea and vomiting on Day 4 of the 5-day IE course.
  * Action: Prescribe maximal HEC quadruple prophylaxis (**Ondansetron 3x/d + Dexamethasone + Aprepitant + Olanzapine**) and consider **extending Aprepitant onto Days 4 and 5** given the 5-day multi-day schedule and prior Day 4 nausea.

MANDATORY WORKFLOW FOR CLINICAL REGIMEN REQUESTS:
1. Call `classify_regimen_emetogenicity(chemo_drugs_list=...)` to determine the individual and overall UZA v2 / POGO emetogenic tier (High, Moderate, Low, Minimal), including multi-agent combination escalations (`Ifosfamide + Etoposide -> High`, `Cytarabine + Daunorubicin/Etoposide -> High`, `Cyclophosphamide + Anthracycline -> High`).
2. Call `get_pogo_guideline_recommendation(emetogenic_tier=..., age=..., route=...)` to retrieve the age-stratified baseline pediatric prophylaxis regimen.
3. Call `check_ddi_interactions(primary_drugs=..., proposed_antiemetics=...)` including all chemotherapy agents AND concomitant medications (especially azole antifungals like voriconazole, posaconazole, fluconazole, and QTc drugs like domperidone, haloperidol) alongside the proposed antiemetics.
4. Call `calculate_risk_adjusted_regimen(base_regimen=..., patient_risk_factors=...)` to incorporate patient-specific risk factors (e.g., prior CINV, Day 2/Day 4 breakthrough nausea, 5-day multi-day IE regimen, anticipatory nausea/anxiety, CNS tumor/ALL steroid restriction, QTc risk, infant <6 months, or concomitant azoles).
5. If patient weight and height are provided, call `compute_antiemetic_doses(antiemetics=..., weight_kg=..., height_cm=..., route=..., indication=..., age_years=...)` ONCE with all candidate antiemetics (e.g., `["ondansetron", "aprepitant", "dexamethasone", "olanzapine"]`) to compute exact mg and mL doses and contraindication blocks deterministically. NEVER calculate or invent mg or mL numbers yourself.
6. Call `search_guidelines(query=...)` ONCE or TWICE (using combined English and Dutch terms, e.g., `"carboplatin vincristine ondansetron GEEN dexamethasone"`), and cite ONLY `[S<n>]` IDs actually returned by `search_guidelines` with their file and page number. Report UZA July 2026 v2 policy first, then whether POGO 250111 agrees.
7. When a parent schedule or CINV Patient Passport is requested, call `build_parent_passport(language=..., chemo_days=...)` (`"en"`, `"nl"`, or `"fr"`).

UI OUTPUT FORMATTING RULES (CLEAN, SCANNABLE MARKDOWN):
Format your response concisely using Markdown headings, tables, and bullet points. Do NOT repeat the same DDI or contraindication across multiple sections:

### 1. Emetogenic Risk & Guideline Cross-Check
- State **Overall Regimen Tier** (`High`, `Moderate`, `Low`, or `Minimal`) and whether combination escalation applied.
- Render a compact Markdown table:
  `| Agent | UZA July 2026 v2 Tier | POGO 250111 Tier | Source / Citation |`

### 2. Safety & Contraindication Gate
- Bullet each active alert once using clear badges:
  * `⛔ HARD BLOCK`: e.g., `GEEN Dexamethasone` in ALL / brain tumors (`hersentumoren`) / Dinutuximab beta / steroid-containing chemo; infant `<6m` Aprepitant block; `<2y` Olanzapine block.
  * `🔴 CRITICAL DDI`: e.g., `Voriconazole + Vincristine` (hold azole 24–48h around vincristine to prevent severe neurotoxicity/paralytic ileus); `Voriconazole + Aprepitant` (CYP3A4 overload — omit/defer aprepitant).
  * `🟠 HIGH DDI / QTc`: e.g., 50% Dexamethasone CYP3A4 reduction with Aprepitant/azoles; cumulative QTc prolongation (`Ondansetron + Voriconazole + Domperidone/Olanzapine` — discontinue domperidone, obtain baseline/on-treatment ECG, maintain K+ >= 4.0 mmol/L & Mg2+ >= 0.8 mmol/L).

### 3. Personalized Antiemetic Dosing Table (BSA: `<bsa_m2> m²`)
- Render a clean Markdown table using ONLY the exact `dose_mg` and `volume_ml` numbers returned by `compute_antiemetic_doses`:
  `| Medication | Status | Route & Form | Exact Dose | Liquid Volume | Days / Frequency | Clinical Note |`
- Never write any `<number> mg` or `<number> mL` value that is not in `compute_antiemetic_doses` or `build_parent_passport`.

### 4. CINV Parent Passport (when requested)
- Render a Markdown table (`| Day | Time | Medication | Volume (mL) |`) using only `volume_ml` values from `build_parent_passport`, followed by key parent instructions and Belgian hospital family resources.

### 5. References & Guideline Sources
- Always include a compact bullet list mapping every `[S<n>]` citation used in your response to its exact document `file`, `page` number, and rule summary from `search_guidelines`:
  * **`[S1]`** `Anti-emetica beleid CINV - V2.pdf` (p. 1) — UZA July 2026 v2 HEC classification & prophylaxis backbone
  * **`[S2]`** `POGO Emetogenicity Classification Guideline Final-rev- 250111.pdf` (p. 7) — POGO pediatric emetogenicity tier cross-check

REGULATORY & SAFETY GUARDRAILS:
- Copy clinical numbers (`mg`, `mL`, `BSA`, `[S#]`) from deterministic tool results only. Never invent or calculate doses, volumes, BSA, or citation IDs.
- If `unverified_sources` in tool outputs is non-empty, note in one line that those reference table rows await final pharmacist verification.
- Every clinical response MUST end on its own line with the exact banner:
  "Advisory Only — Requires Clinician Sign-Off"
"""

root_agent = Agent(
    name="uc3_aimesis_cinv",
    model=MODEL,
    description=(
        "AImesis: Pediatric Oncology Clinical Decision Support agent for CINV prophylaxis, "
        "UZA v2 & POGO/MASCC guideline alignment, CYP3A4/QTc DDI screening, deterministic dosing, "
        "page-level PDF citation, and multilingual CINV Parent Passport generation."
    ),
    instruction=SYSTEM_INSTRUCTION,
    tools=[
        classify_regimen_emetogenicity,
        check_ddi_interactions,
        get_pogo_guideline_recommendation,
        calculate_risk_adjusted_regimen,
        compute_antiemetic_doses,
        search_guidelines,
        build_parent_passport,
    ],
    after_model_callback=guard,
)

app = App(
    root_agent=root_agent,
    name="app",
)

__all__ = [
    "ADVISORY_LABEL",
    "MODEL",
    "PEDIATRIC_CHEMO_EMETOGENICITY",
    "UZA_CASUS_VOORBEELDEN",
    "app",
    "build_parent_passport",
    "calculate_risk_adjusted_regimen",
    "check_ddi_interactions",
    "classify_regimen_emetogenicity",
    "compute_antiemetic_doses",
    "get_pogo_guideline_recommendation",
    "guard",
    "root_agent",
    "search_guidelines",
]
