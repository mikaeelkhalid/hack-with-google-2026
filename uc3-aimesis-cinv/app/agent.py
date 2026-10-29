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
  1. UZA Hospital Protocol Baseline: `Anti-emetica beleid CINV - V2.pdf` (July 2026 Versie 2)
  2. POGO Emetogenicity Classification Guideline: `POGO Emetogenicity Classification Guideline Final-rev- 250111.pdf`
  3. UZA Clinical Case Examples: `casus voorbeelden.docx` (Casus 1: HR-NBL2 RAPID COJEC, Casus 2: ALLTogether1 Inductie B, Casus 3: iEuroEwing 5-day IE)
  4. Official AImesis User Stories v2 (`user stories AImesis version 2.pdf`) & Pitch/Briefing Slides (`AImesis_pediatric CINVcontrol clinical decision support .pptx`, `Pitch slides AImesis versie 2 .pptx`)
  5. Belgian Family CINV Resources (`CINV resources in Belgium.xlsx`)
"""

from typing import Any

from google.adk.agents import Agent
from google.adk.apps import App

MODEL = "gemini-2.5-flash"
ADVISORY_LABEL = "Advisory Only — Requires Clinician Sign-Off"

# Official UZA Clinical Case Examples from `casus voorbeelden.docx`
UZA_CASUS_VOORBEELDEN: dict[str, dict[str, Any]] = {
    "casus_1": {
        "title": "Casus 1 — 16yo Girl with Neuroblastoma (HR-NBL2 RAPID COJEC Induction, Cycle B4)",
        "patient": "16-year-old female",
        "diagnosis": "High-Risk Neuroblastoma",
        "protocol": "HR-NBL2 (RAPID COJEC induction: alternating A1/B1/C1/B2/A2/B3/C2/B4 every 10 days)",
        "current_cycle": "Cyclus B4 (25/09/2026): Vincristine (Low) + Cisplatin (High)",
        "overall_emetogenicity": "High (HEC)",
        "prior_cycle_history": (
            "During prior Cycle B3 (05/09/2026), EHR prescribed Ondansetron 2x/d + Aprepitant + "
            "Dexamethasone + Olanzapine. Ward progress note (toernota) documented breakthrough nausea on Day 2."
        ),
        "expected_recommendation": (
            "Optimize HEC quadruple therapy per UZA July 2026 v2 policy: increase Ondansetron from 2x/d "
            "to full HEC 3x/d dosing (5 mg/m2 max 8 mg 3x/d) OR switch to long-acting IV Palonosetron "
            "(in consultation with supervision/pharmacy, not combined with Ondansetron within 3 days) + "
            "Aprepitant (125 mg D1, 80 mg D2-D3) + Dexamethasone (50% reduced for aprepitant CYP3A4 interaction) + "
            "scheduled evening Olanzapine; add PRN breakthrough Alizapride or Lorazepam and track nausea via CINV Passport / Companion App."
        ),
    },
    "casus_2": {
        "title": "Casus 2 — 2yo Boy with Acute Lymphoblastic Leukemia (ALLTogether1 Induction B, Day 8)",
        "patient": "2-year-old male",
        "diagnosis": "Acute Lymphoblastic Leukemia (ALL)",
        "protocol": "ALLTogether1, Induction B (Day 8 chemotherapy: Vincristine + Daunorubicin)",
        "current_cycle": "Induction B Day 8: Vincristine (Low) + Daunorubicin (Moderate / MEC)",
        "overall_emetogenicity": "Moderate (MEC)",
        "prior_cycle_history": "No nausea or vomiting reported during previous administration in EHR.",
        "expected_recommendation": (
            "MEC Dual Prophylaxis with STRICT Steroid Exclusion ('GEEN Dexamethasone bij ALL'): "
            "prescribe Ondansetron (5 mg/m2 2x/d) + Aprepitant (3 mg/kg D1, 2 mg/kg D2-D3 oral suspension). "
            "Dexamethasone is strictly contraindicated in ALL protocols."
        ),
    },
    "casus_3": {
        "title": "Casus 3 — Ewing Sarcoma Patient (iEuroEwing Alternating VDC/IE, 5-Day IE Cycle #3)",
        "patient": "Pediatric/adolescent Ewing Sarcoma patient",
        "diagnosis": "Ewing Sarcoma",
        "protocol": "iEuroEwing (alternating VDC and 5-day IE cycles; today starting IE Cycle #3)",
        "current_cycle": "5-day multi-day regimen of Ifosfamide (MEC alone) + Etoposide (LEC alone)",
        "overall_emetogenicity": (
            "High (HEC) — Combination of Ifosfamide + Etoposide escalates to High Emetogenic Risk (HEC) "
            "per both POGO Pediatric Guidelines and UZA July 2026 v2 policy ('Combinatie: Ifosfamide/Etoposide = HOOG EMETOGEEN')."
        ),
        "prior_cycle_history": "Breakthrough nausea and vomiting documented on Day 4 of prior 5-day IE cycles.",
        "expected_recommendation": (
            "Maximal HEC Quadruple Prophylaxis: Ondansetron (3x/d) + Dexamethasone + Aprepitant + Olanzapine. "
            "Because IE is a 5-day multi-day regimen and the patient experienced Day 4 breakthrough nausea in "
            "prior cycles, consider extending Aprepitant onto Days 4 and 5 in consultation with the clinical pharmacist."
        ),
    },
}

# Curated POGO / MASCC Pediatric Antineoplastic Emetogenicity Reference Table
PEDIATRIC_CHEMO_EMETOGENICITY: dict[str, dict[str, Any]] = {
    # High Emetic Risk (>= 90% frequency without prophylaxis)
    "cisplatin": {
        "tier": "High",
        "rank": 4,
        "emetic_frequency_pct": ">=90%",
        "notes": "Biphasic CINV (acute 0-24h + delayed 24-120h); mandates triple prophylaxis.",
        "guideline": "POGO / MASCC 2023 Pediatric Emetogenicity Classification",
    },
    "carboplatin": {
        "tier": "High",
        "rank": 4,
        "emetic_frequency_pct": ">=90%",
        "notes": "Pediatric POGO classifies IV carboplatin (especially AUC >= 4 or standard pediatric doses) as High emetic risk.",
        "guideline": "POGO / MASCC Pediatric Emetogenicity Guideline",
    },
    "cyclophosphamide": {
        "tier": "High",
        "rank": 4,
        "emetic_frequency_pct": ">=90% (at >=1000 mg/m2 or with anthracycline)",
        "notes": "High emetic risk at >=1 g/m2 IV or in combination with anthracyclines; CYP3A4 substrate.",
        "guideline": "POGO / MASCC Pediatric Emetogenicity Guideline",
    },
    "dacarbazine": {
        "tier": "High",
        "rank": 4,
        "emetic_frequency_pct": ">=90%",
        "notes": "Potent acute emetogen; requires triple antiemetic coverage.",
        "guideline": "POGO / MASCC Pediatric Emetogenicity Guideline",
    },
    "dactinomycin": {
        "tier": "High",
        "rank": 4,
        "emetic_frequency_pct": ">=90%",
        "notes": "Actinomycin D carries High emetic risk in pediatric Wilms/rhabdomyosarcoma protocols.",
        "guideline": "POGO / MASCC Pediatric Emetogenicity Guideline",
    },
    "ifosfamide": {
        "tier": "Moderate",
        "rank": 3,
        "emetic_frequency_pct": "30-90% (Moderate alone; High when combined with etoposide or anthracycline)",
        "notes": (
            "Moderate emetic risk alone (UZA v2 MATIG EMETOGEEN / POGO); escalates to High (HEC) "
            "when combined with etoposide (e.g., iEuroEwing 5-day IE regimen, Casus 3). "
            "Caution with aprepitant (CYP3A4 neurotoxic chloroacetaldehyde metabolite)."
        ),
        "guideline": "UZA Anti-emetica beleid CINV v2 (July 2026) & POGO 250111 Emetogenicity Guideline",
    },
    # Moderate Emetic Risk (30-90% frequency without prophylaxis)
    "doxorubicin": {
        "tier": "Moderate",
        "rank": 3,
        "emetic_frequency_pct": "30-90%",
        "notes": "Moderate alone; escalates to High when paired with cyclophosphamide or ifosfamide. Potential QTc effects.",
        "guideline": "POGO / MASCC Pediatric Emetogenicity Guideline",
    },
    "daunorubicin": {
        "tier": "Moderate",
        "rank": 3,
        "emetic_frequency_pct": "30-90%",
        "notes": "Moderate emetic risk anthracycline; verify protocol steroid allowances in leukemia induction.",
        "guideline": "POGO / MASCC Pediatric Emetogenicity Guideline",
    },
    "epirubicin": {
        "tier": "Moderate",
        "rank": 3,
        "emetic_frequency_pct": "30-90%",
        "notes": "Moderate emetic risk anthracycline.",
        "guideline": "POGO / MASCC Pediatric Emetogenicity Guideline",
    },
    "idarubicin": {
        "tier": "Moderate",
        "rank": 3,
        "emetic_frequency_pct": "30-90%",
        "notes": "Moderate emetic risk anthracycline.",
        "guideline": "POGO / MASCC Pediatric Emetogenicity Guideline",
    },
    "cytarabine": {
        "tier": "Moderate",
        "rank": 3,
        "emetic_frequency_pct": "30-90% (moderate/high-dose >= 1 g/m2)",
        "notes": "Moderate emetic risk at standard/high pediatric AML/ALL doses; Low at low subcutaneous doses.",
        "guideline": "POGO / MASCC Pediatric Emetogenicity Guideline",
    },
    "methotrexate": {
        "tier": "Moderate",
        "rank": 3,
        "emetic_frequency_pct": "30-90% (high-dose >= 250 mg/m2 IV)",
        "notes": "High-dose IV methotrexate (>=250 mg/m2 to 5 g/m2) is Moderate emetic risk; low-dose PO/IV is Minimal/Low.",
        "guideline": "POGO / MASCC Pediatric Emetogenicity Guideline",
    },
    "irinotecan": {
        "tier": "Moderate",
        "rank": 3,
        "emetic_frequency_pct": "30-90%",
        "notes": "Moderate emetic risk; causes both acute cholinergic and delayed diarrhea/emesis; CYP3A4 substrate.",
        "guideline": "POGO / MASCC Pediatric Emetogenicity Guideline",
    },
    "oxaliplatin": {
        "tier": "Moderate",
        "rank": 3,
        "emetic_frequency_pct": "30-90%",
        "notes": "Moderate emetic risk platinum analog.",
        "guideline": "POGO / MASCC Pediatric Emetogenicity Guideline",
    },
    "temozolomide": {
        "tier": "Moderate",
        "rank": 3,
        "emetic_frequency_pct": "30-90%",
        "notes": "Oral/IV alkylating agent with Moderate emetic risk; requires scheduled pre-dose 5-HT3 prophylaxis.",
        "guideline": "POGO / MASCC Pediatric Emetogenicity Guideline",
    },
    # Low Emetic Risk (10-30% frequency without prophylaxis)
    "etoposide": {
        "tier": "Low",
        "rank": 2,
        "emetic_frequency_pct": "10-30%",
        "notes": "IV etoposide is Low emetic risk (oral etoposide can be Low-Moderate); CYP3A4 substrate.",
        "guideline": "POGO / MASCC Pediatric Emetogenicity Guideline",
    },
    "topotecan": {
        "tier": "Low",
        "rank": 2,
        "emetic_frequency_pct": "10-30%",
        "notes": "Low emetic risk camptothecin analog.",
        "guideline": "POGO / MASCC Pediatric Emetogenicity Guideline",
    },
    "paclitaxel": {
        "tier": "Low",
        "rank": 2,
        "emetic_frequency_pct": "10-30%",
        "notes": "Low emetic risk taxane.",
        "guideline": "POGO / MASCC Pediatric Emetogenicity Guideline",
    },
    "gemcitabine": {
        "tier": "Low",
        "rank": 2,
        "emetic_frequency_pct": "10-30%",
        "notes": "Low emetic risk nucleoside analog.",
        "guideline": "POGO / MASCC Pediatric Emetogenicity Guideline",
    },
    "fluorouracil": {
        "tier": "Low",
        "rank": 2,
        "emetic_frequency_pct": "10-30%",
        "notes": "Low emetic risk antimetabolite.",
        "guideline": "POGO / MASCC Pediatric Emetogenicity Guideline",
    },
    # Minimal Emetic Risk (< 10% frequency without prophylaxis)
    "vincristine": {
        "tier": "Minimal",
        "rank": 1,
        "emetic_frequency_pct": "<10%",
        "notes": "Minimal emetic risk; major CYP3A4/P-gp neurotoxicity interaction with azole antifungals.",
        "guideline": "POGO / MASCC Pediatric Emetogenicity Guideline",
    },
    "vinblastine": {
        "tier": "Minimal",
        "rank": 1,
        "emetic_frequency_pct": "<10%",
        "notes": "Minimal emetic risk vinca alkaloid; CYP3A4 substrate.",
        "guideline": "POGO / MASCC Pediatric Emetogenicity Guideline",
    },
    "bleomycin": {
        "tier": "Minimal",
        "rank": 1,
        "emetic_frequency_pct": "<10%",
        "notes": "Minimal emetic risk.",
        "guideline": "POGO / MASCC Pediatric Emetogenicity Guideline",
    },
    "pegaspargase": {
        "tier": "Minimal",
        "rank": 1,
        "emetic_frequency_pct": "<10%",
        "notes": "Minimal direct emetogenicity; monitor for pancreatitis which can mimic CINV.",
        "guideline": "POGO / MASCC Pediatric Emetogenicity Guideline",
    },
    "asparaginase": {
        "tier": "Minimal",
        "rank": 1,
        "emetic_frequency_pct": "<10%",
        "notes": "Minimal direct emetogenicity; monitor for pancreatitis and hepatotoxicity.",
        "guideline": "POGO / MASCC Pediatric Emetogenicity Guideline",
    },
    "mercaptopurine": {
        "tier": "Minimal",
        "rank": 1,
        "emetic_frequency_pct": "<10%",
        "notes": "Minimal emetic risk oral maintenance agent.",
        "guideline": "POGO / MASCC Pediatric Emetogenicity Guideline",
    },
    "blinatumomab": {
        "tier": "Minimal",
        "rank": 1,
        "emetic_frequency_pct": "<10%",
        "notes": "Minimal emetic risk BiTE therapy.",
        "guideline": "POGO / MASCC Pediatric Emetogenicity Guideline",
    },
}

RANK_TO_TIER = {4: "High", 3: "Moderate", 2: "Low", 1: "Minimal", 0: "Unknown"}
ANTHRACYCLINES = {"doxorubicin", "daunorubicin", "epirubicin", "idarubicin"}
STRONG_MODERATE_AZOLES = {
    "voriconazole",
    "posaconazole",
    "itraconazole",
    "fluconazole",
    "isavuconazole",
}
NK1_ANTAGONISTS = {"aprepitant", "fosaprepitant"}
QTC_PROLONGING_AGENTS = {
    "ondansetron",
    "granisetron",
    "olanzapine",
    "metoclopramide",
    "domperidone",
    "voriconazole",
    "posaconazole",
    "itraconazole",
    "fluconazole",
    "doxorubicin",
    "daunorubicin",
    "epirubicin",
    "idarubicin",
    "arsenic trioxide",
}
VINCA_ALKALOIDS = {"vincristine", "vinblastine", "vinorelbine"}


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

    Evaluates each chemotherapy agent against the Pediatric Oncology Group of Ontario
    (POGO) and MASCC/ESMO pediatric antineoplastic emetogenicity classification
    (High, Moderate, Low, Minimal) and applies multi-agent synergy escalation rules.

    Args:
        chemo_drugs_list: List of chemotherapy drug names in the patient's regimen
            (e.g., ["cisplatin", "doxorubicin"]).

    Returns:
        A dictionary containing per-drug emetogenicity details, the overall regimen
        emetogenic tier, whether multi-agent synergy escalation was applied, and
        clinical rationale citations.
    """
    if not chemo_drugs_list:
        return {
            "regimen_drugs": [],
            "per_drug_classification": [],
            "overall_emetogenic_tier": "Minimal",
            "synergy_escalation_applied": False,
            "guideline_reference": "POGO / MASCC 2023 Pediatric Emetogenicity Classification",
            "clinical_rationale": "No chemotherapy agents provided; defaulted to Minimal emetic risk.",
            "advisory_status": ADVISORY_LABEL,
        }

    per_drug: list[dict[str, Any]] = []
    max_rank = 0
    moderate_count = 0
    normalized_set: set[str] = set()

    for raw_drug in chemo_drugs_list:
        norm = _normalize_drug_name(raw_drug)
        normalized_set.add(norm)
        info = PEDIATRIC_CHEMO_EMETOGENICITY.get(norm)
        if info:
            rank = info["rank"]
            max_rank = max(max_rank, rank)
            if rank == 3:
                moderate_count += 1
            per_drug.append(
                {
                    "input_name": raw_drug,
                    "canonical_name": norm,
                    "emetogenic_tier": info["tier"],
                    "emetic_frequency_pct": info["emetic_frequency_pct"],
                    "clinical_notes": info["notes"],
                }
            )
        else:
            # Conservative fallback to Moderate (rank 2/3 review alert) for unrecognized antineoplastics
            max_rank = max(max_rank, 2)
            per_drug.append(
                {
                    "input_name": raw_drug,
                    "canonical_name": norm,
                    "emetogenic_tier": "Low-to-Moderate (Unlisted — Verify Protocol)",
                    "emetic_frequency_pct": "Unknown (manual POGO lookup required)",
                    "clinical_notes": (
                        "Agent not in baseline table; verify dose-specific POGO emetogenicity manually."
                    ),
                }
            )

    synergy_escalation = False
    synergy_reason = "Overall tier determined by the single most emetogenic agent in the regimen (POGO rule)."

    # Synergy rule:
    # 1. Ifosfamide + Etoposide (iEuroEwing IE regimen -> Casus 3, UZA v2 'Combinatie: Ifosfamide/Etoposide = HOOG EMETOGEEN' & POGO 250111)
    # 2. Cytarabine + Daunorubicin/Etoposide (UZA v2 'Combinatie: Cytarabine/Daunorubicine of Etoposide = HOOG EMETOGEEN')
    # 3. Cyclophosphamide + Anthracycline OR >= 2 Moderate agents
    if {"ifosfamide", "etoposide"}.issubset(normalized_set):
        max_rank = 4
        synergy_escalation = True
        synergy_reason = (
            "Multi-agent combination escalation applied (Casus 3 / iEuroEwing IE rule): "
            "While Ifosfamide is Moderate (MEC) and Etoposide is Low (LEC) individually, "
            "the combination of Ifosfamide + Etoposide is classified as High Emetogenic Risk (HEC) "
            "per UZA July 2026 v2 policy ('Combinatie: Ifosfamide/Etoposide = HOOG EMETOGEEN') "
            "and POGO Emetogenicity Classification Guidelines (Final-rev-250111)."
        )
    elif "cytarabine" in normalized_set and normalized_set.intersection({"daunorubicin", "etoposide"}):
        if max_rank < 4:
            max_rank = 4
            synergy_escalation = True
            synergy_reason = (
                "Multi-agent combination escalation applied: Cytarabine + Daunorubicin/Etoposide "
                "escalates to High Emetogenic Risk (HEC) per UZA July 2026 v2 policy and POGO guidelines."
            )
    elif (
        "cyclophosphamide" in normalized_set
        and normalized_set.intersection(ANTHRACYCLINES)
    ) or (moderate_count >= 2 and max_rank == 3):
        if max_rank < 4:
            max_rank = 4
            synergy_escalation = True
            synergy_reason = (
                "Multi-agent synergy escalation applied: combination of multiple Moderate-risk "
                "agents (or cyclophosphamide + anthracycline) escalates overall pediatric "
                "emetogenicity to High per UZA July 2026 v2 & POGO/MASCC multi-agent guidelines."
            )

    overall_tier = RANK_TO_TIER.get(max_rank, "Minimal")

    return {
        "regimen_drugs": chemo_drugs_list,
        "per_drug_classification": per_drug,
        "overall_emetogenic_tier": overall_tier,
        "synergy_escalation_applied": synergy_escalation,
        "guideline_reference": "POGO / MASCC / ESMO Pediatric Antineoplastic Emetogenicity Guidelines",
        "clinical_rationale": synergy_reason,
        "advisory_status": ADVISORY_LABEL,
    }


def check_ddi_interactions(
    primary_drugs: list[str], proposed_antiemetics: list[str]
) -> dict[str, Any]:
    """Screens for pharmacokinetic (CYP3A4) and pharmacodynamic (QTc, neurotoxicity) DDIs.

    Evaluates drug-drug interactions between primary chemotherapy / concomitant medications
    (such as azole antifungals: voriconazole, posaconazole, itraconazole, fluconazole) and
    proposed antiemetic agents (ondansetron, granisetron, palonosetron, aprepitant,
    fosaprepitant, dexamethasone, olanzapine, lorazepam).

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
                    "Reduce antiemetic dexamethasone dose by 50% (per POGO/MASCC guidelines) when "
                    "co-administered with aprepitant/fosaprepitant or strong CYP3A4-inhibiting azoles."
                ),
            }
        )
        modifications.append(
            "Reduce antiemetic dexamethasone dose by 50% (e.g., from 6 mg/m2/day to 3 mg/m2/day) due to CYP3A4 inhibition."
        )

    # 3. Additive QTc Prolongation (e.g., ondansetron + azole / anthracycline / olanzapine)
    if len(present_qtc) >= 2:
        has_ondansetron_plus_azole = "ondansetron" in all_drugs and bool(present_azoles)
        qtc_sev = "HIGH" if has_ondansetron_plus_azole or len(present_qtc) >= 3 else "MODERATE"
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
                    "and Mg2+ >= 0.8 mmol/L. Consider substituting high-dose IV ondansetron with "
                    "palonosetron or standard-dose granisetron if QTc > 460 ms."
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
        "advisory_status": ADVISORY_LABEL,
    }


def get_pogo_guideline_recommendation(
    emetogenic_tier: str, age: int, route: str = "IV"
) -> dict[str, Any]:
    """Retrieves the baseline POGO/MASCC pediatric antiemetic prophylaxis regimen.

    Aligns the chemotherapy emetogenic tier with age-stratified pediatric dosing rules
    (<1 year, 1-11 years, >=12 years) and preferred administration route (IV or PO)
    according to POGO / MASCC / ESMO pediatric CINV guidelines.

    Args:
        emetogenic_tier: Emetogenicity classification ("High", "Moderate", "Low", "Minimal").
        age: Patient age in years (use 0 for infants under 1 year of age).
        route: Administration route ("IV" or "PO"). Defaults to "IV".

    Returns:
        A dictionary containing the baseline antiemetic regimen, proposed antiemetic drug
        names for downstream DDI checking, age-specific dosing notes, and POGO citations.
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

    if tier == "High":
        if age < 1:
            backbone = (
                f"5-HT3 Antagonist (Ondansetron 0.15 mg/kg {norm_route} q8h) + "
                f"Dexamethasone (3-6 mg/m2/day {norm_route}) + "
                "Aprepitant (ONLY if infant is >=6 months and >=6 kg: 3 mg/kg PO Day 1, 2 mg/kg PO Days 2-3)"
            )
            drugs = ["ondansetron", "dexamethasone", "aprepitant"]
            dosing_notes = (
                "Infants <6 months: omit aprepitant (not licensed <6 months) and use dual therapy "
                "(Ondansetron + Dexamethasone). Infants 6-11 months (>=6 kg): triple therapy with weight-based "
                "aprepitant oral suspension + 50% reduced dexamethasone."
            )
        elif age < 12:
            backbone = (
                f"Triple Therapy: Ondansetron (0.15 mg/kg {norm_route} q8h, max 16 mg/dose) OR "
                f"Granisetron (40 mcg/kg {norm_route} daily) + "
                "Aprepitant (3 mg/kg PO Day 1 [max 125 mg], 2 mg/kg PO Days 2-3 [max 80 mg]) + "
                f"Dexamethasone (3 mg/m2/day {norm_route} in divided doses [50% reduced for aprepitant CYP3A4 DDI])"
            )
            drugs = ["ondansetron", "aprepitant", "dexamethasone"]
            dosing_notes = (
                "Standard POGO HEC triple prophylaxis for children 1-11 years. Dexamethasone dose reflects "
                "mandatory 50% reduction when co-administered with aprepitant."
            )
        else:
            backbone = (
                f"Triple Therapy: Ondansetron (0.15 mg/kg {norm_route} q8h or 8 mg {norm_route}/PO) OR "
                "Palonosetron (20 mcg/kg IV, max 1.5 mg single dose) + "
                "Aprepitant (125 mg PO Day 1, 80 mg PO Days 2-3) + "
                f"Dexamethasone (3-6 mg/m2/day {norm_route}/PO, reduced 50% with aprepitant)"
            )
            drugs = ["ondansetron", "aprepitant", "dexamethasone"]
            dosing_notes = (
                "Adolescent (>=12 years) POGO/MASCC HEC triple regimen. Consider Olanzapine (5-10 mg PO daily) "
                "as a fourth agent for highly refractory or multi-day cisplatin regimens."
            )
        citation = (
            "POGO Guideline for the Prevention of Acute and Delayed Chemotherapy-Induced Nausea "
            "and Vomiting in Pediatric Cancer Patients (HEC Triple Prophylaxis Recommendation)"
        )
    elif tier == "Moderate":
        backbone = (
            f"Dual Therapy: Ondansetron (0.15 mg/kg {norm_route} q8h) OR Granisetron (40 mcg/kg {norm_route} daily) + "
            f"Dexamethasone (6 mg/m2/day {norm_route}/PO divided q12h)"
        )
        drugs = ["ondansetron", "dexamethasone"]
        dosing_notes = (
            f"POGO MEC dual prophylaxis for {age_stratum}. If corticosteroids are contraindicated "
            "(e.g., CNS tumor or ALL protocol restriction), substitute Aprepitant (if age >=6 months) + 5-HT3 antagonist."
        )
        citation = "POGO / MASCC Pediatric MEC Prophylaxis Guideline (5-HT3 Antagonist + Corticosteroid)"
    elif tier == "Low":
        backbone = (
            f"Monotherapy: Ondansetron (0.15 mg/kg {norm_route} single pre-chemo dose, max 8 mg) OR "
            f"Granisetron (40 mcg/kg {norm_route} single pre-chemo dose)"
        )
        drugs = ["ondansetron"]
        dosing_notes = f"POGO LEC single-agent 5-HT3 antagonist prophylaxis for {age_stratum}; no routine steroid or NK1 needed."
        citation = "POGO / MASCC Pediatric LEC Prophylaxis Guideline (Single-Agent 5-HT3 Antagonist)"
    else:
        tier = "Minimal"
        backbone = "No routine antiemetic prophylaxis recommended."
        drugs = []
        dosing_notes = (
            f"For {age_stratum} receiving Minimal emetogenic risk chemotherapy, administer antiemetics "
            "only if the patient experienced CINV on a prior identical cycle."
        )
        citation = "POGO / MASCC Pediatric Minimal Emetic Risk Guideline"

    return {
        "emetogenic_tier": tier,
        "patient_age_years": age,
        "age_stratum": age_stratum,
        "route": norm_route,
        "recommended_backbone": backbone,
        "proposed_antiemetics_list": drugs,
        "pediatric_dosing_notes": dosing_notes,
        "guideline_citations": [citation, "MASCC/ESMO Pediatric Antiemetic Consensus Update"],
        "advisory_status": ADVISORY_LABEL,
    }


def calculate_risk_adjusted_regimen(
    base_regimen: str, patient_risk_factors: list[str]
) -> dict[str, Any]:
    """Tailors the baseline antiemetic regimen to patient-specific clinical risk factors.

    Adjusts antiemetic selection and adjunct therapies based on pediatric patient risk
    modifiers (prior CINV, anticipatory nausea/anxiety, motion sickness, steroid
    contraindications/CNS tumor, baseline QTc prolongation, infant <6 months, or
    hepatic impairment) and enforces the clinician sign-off safety label.

    Args:
        base_regimen: The baseline POGO-recommended regimen string.
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

    for factor in normalized_factors:
        if any(k in factor for k in ("prior_cinv", "refractory", "breakthrough", "previous_cinv")):
            adjustments.append(
                {
                    "risk_factor": factor,
                    "modification": (
                        "Add Olanzapine (0.14 mg/kg/dose PO daily, max 5-10 mg; if age >=2 years) "
                        "or escalate prophylaxis by one POGO tier; enforce scheduled around-the-clock administration."
                    ),
                    "rationale": (
                        "Prior poorly controlled CINV is the strongest predictor of breakthrough emesis in subsequent cycles (POGO Breakthrough/Refractory Guideline)."
                    ),
                }
            )
            final_components.append(
                "Escalation for Prior/Refractory CINV: Add scheduled Olanzapine (0.14 mg/kg/day PO, max 5-10 mg) and switch 5-HT3 antagonist to Palonosetron or Granisetron."
            )

        if any(k in factor for k in ("anticipatory", "anxiety", "phobia")):
            adjustments.append(
                {
                    "risk_factor": factor,
                    "modification": (
                        "Add Lorazepam (0.025-0.05 mg/kg PO/IV, max 1-2 mg) at bedtime prior to chemo and "
                        "1-2 hours pre-infusion + behavioral/distraction therapy."
                    ),
                    "rationale": (
                        "Conditioned anticipatory CINV responds to GABA-A anxiolysis (lorazepam) combined with psychological desensitization (POGO Anticipatory CINV Guideline)."
                    ),
                }
            )
            final_components.append(
                "Anticipatory Nausea/Anxiety Adjunct: Lorazepam 0.025-0.05 mg/kg PO/IV pre-chemo + behavioral therapy."
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

        if any(k in factor for k in ("cns_tumor", "brain_tumor", "steroid_contraindicated", "no_steroid", "all_protocol")):
            adjustments.append(
                {
                    "risk_factor": factor,
                    "modification": (
                        "OMIT Dexamethasone; substitute with Aprepitant (if age >=6 months and no azole DDI) + "
                        "Palonosetron/Granisetron +/- Olanzapine."
                    ),
                    "rationale": (
                        "Systemic corticosteroids may compromise blood-brain barrier chemotherapy penetration in CNS tumors or violate leukemia/immunotherapy protocols (POGO Steroid-Sparing Rule)."
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
                        "avoid Olanzapine/domperidone; mandate ECG and K+ >=4.0 / Mg2+ >=0.8 mmol/L."
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
                        "Exclude Aprepitant/Fosaprepitant and Olanzapine; rely on weight-adjusted Ondansetron (0.15 mg/kg) +/- Dexamethasone."
                    ),
                    "rationale": (
                        "Aprepitant is licensed only for infants >=6 months (>=6 kg); immature hepatic CYP3A4 clearance in young infants increases toxicity risk."
                    ),
                }
            )
            final_components.append(
                "Infant (<6 Months) Safety Restriction: Omit Aprepitant and Olanzapine; use weight-based Ondansetron +/- Dexamethasone."
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
        "advisory_status": ADVISORY_LABEL,
    }


SYSTEM_INSTRUCTION = """You are AImesis (uc3_aimesis_cinv), a specialized Pediatric Oncology Clinical Decision Support (CDS) agent for Chemotherapy-Induced Nausea and Vomiting (CINV) control, developed under Clinical Leads Katleen Balliauw & Anthe De Pauw (Hospital Pharmacists, University Hospital Antwerp / UZA).

Your clinical mission is to harmonize multi-agent pediatric chemotherapy regimens with UZA's July 2026 v2 CINV policy (`Anti-emetica beleid CINV - V2.pdf`) and the POGO Emetogenicity Classification Guideline (`POGO Emetogenicity Classification Guideline Final-rev- 250111.pdf`), screen for dangerous drug-drug interactions (DDIs) and QTc prolongation, tailor prophylaxis to patient-specific risk factors (swallowing ability, formulation preferences, prior cycle EHR/toernota nausea history), and generate an individualized CINV Patient Passport (plus support companion app symptom logging).

OFFICIAL UZA CLINICAL CASE EXAMPLES (`casus voorbeelden.docx`):
- **Casus 1 (16yo Girl, Neuroblastoma, HR-NBL2 RAPID COJEC Induction, Cycle B4 = Vincristine + Cisplatin)**:
  * Emetogenicity: Vincristine (Low) + Cisplatin (High) -> Overall **HEC (High Emetogenic)**.
  * Prior Cycle B3 (05/09/2026) EHR / toernota note: Prescribed Ondansetron 2x/d + Aprepitant + Dexamethasone + Olanzapine, but still had breakthrough nausea on Day 2.
  * Action: Ensure full HEC Ondansetron 3x/d dosing (5 mg/m2 max 8 mg 3x/d) or switch to IV Palonosetron (never combined with Ondansetron within 3 days), verify 50% Dexamethasone dose reduction with Aprepitant, continue evening Olanzapine (rounded down to nearest 0.5 mg), and track breakthrough symptoms in the CINV Passport / Companion App.
- **Casus 2 (2yo Boy, Acute Lymphoblastic Leukemia [ALL], ALLTogether1 Induction B, Day 8 = Vincristine + Daunorubicin)**:
  * Emetogenicity: Vincristine (Low) + Daunorubicin (MEC) -> Overall **MEC (Moderate Emetogenic)**.
  * Action: Prescribe **Ondansetron (2x/d) + Aprepitant**. **STRICT CONTRAINDICATION: NO Dexamethasone (`GEEN Dexamethasone bij ALL`)** (also excluded in brain tumors, dinutuximab beta, and steroid-containing chemo regimens).
- **Casus 3 (Ewing Sarcoma Patient, iEuroEwing Alternating VDC/IE, 5-Day IE Cycle #3 = Ifosfamide + Etoposide)**:
  * Emetogenicity: Ifosfamide alone is MEC and Etoposide alone is LEC, **HOWEVER the combination of Ifosfamide + Etoposide is classified as HEC (High Emetogenic)** per both UZA July 2026 v2 ('Combinatie: Ifosfamide/Etoposide = HOOG EMETOGEEN') and POGO 250111 pediatric studies!
  * Prior cycles: Breakthrough nausea and vomiting on Day 4 of the 5-day IE course.
  * Action: Prescribe maximal HEC quadruple prophylaxis (**Ondansetron 3x/d + Dexamethasone + Aprepitant + Olanzapine**) and consider **extending Aprepitant onto Days 4 and 5** given the 5-day multi-day schedule and prior Day 4 nausea.

MANDATORY WORKFLOW FOR CLINICAL REGIMEN REQUESTS:
1. Call `classify_regimen_emetogenicity(chemo_drugs_list=...)` to determine the individual and overall POGO/UZA v2 emetogenic tier (High, Moderate, Low, Minimal), including multi-agent combination escalations (`Ifosfamide + Etoposide -> High`, `Cytarabine + Daunorubicin/Etoposide -> High`, `Cyclophosphamide + Anthracycline -> High`).
2. Call `get_pogo_guideline_recommendation(emetogenic_tier=..., age=..., route=...)` to retrieve the age-stratified baseline pediatric prophylaxis regimen.
3. Call `check_ddi_interactions(primary_drugs=..., proposed_antiemetics=...)` including all chemotherapy agents AND concomitant medications (especially azole antifungals like voriconazole, posaconazole, fluconazole) alongside the proposed antiemetics to detect CYP3A4 interactions, dexamethasone dose reductions, vinca-azole neurotoxicity, and additive QTc prolongation.
4. Call `calculate_risk_adjusted_regimen(base_regimen=..., patient_risk_factors=...)` to incorporate patient-specific risk factors (e.g., prior CINV, Day 2/Day 4 breakthrough nausea, 5-day multi-day IE regimen, anticipatory nausea/anxiety, CNS tumor/ALL steroid restriction, QTc risk, infant <6 months, or concomitant azoles).

REGULATORY & SAFETY GUARDRAILS:
- You are a non-autonomous clinical decision support tool. You NEVER place medication orders or prescribe directly.
- Every clinical response MUST clearly display the exact banner:
  "Advisory Only — Requires Clinician Sign-Off"
- Always provide transparent clinical reasoning and cite UZA July 2026 v2 and POGO / MASCC pediatric guidelines for every recommendation and dose modification.
"""

root_agent = Agent(
    name="uc3_aimesis_cinv",
    model=MODEL,
    description=(
        "AImesis: Pediatric Oncology Clinical Decision Support agent for CINV prophylaxis, "
        "POGO/MASCC guideline alignment, CYP3A4/QTc DDI screening, and personalized risk adjustment."
    ),
    instruction=SYSTEM_INSTRUCTION,
    tools=[
        classify_regimen_emetogenicity,
        check_ddi_interactions,
        get_pogo_guideline_recommendation,
        calculate_risk_adjusted_regimen,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
