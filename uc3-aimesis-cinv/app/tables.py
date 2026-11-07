"""Clinical reference tables for Almesis Copilot (uc3-aimesis-cinv).

Grounded in:
  - UZA Anti-emetica beleid CINV - V2.pdf (July 2026 Version 2, pages 1-2)
  - POGO Emetogenicity Classification Guideline (Final-rev-250111)
  - UZA casus voorbeelden.docx (Casus 1-3)
  - CINV resources in Belgium.xlsx

Every clinical row carries `source` (document + page) and `verified` (bool).
Rows with `verified=False` are blocked unless `ALLOW_UNVERIFIED=1` is set.
"""

from __future__ import annotations

import os
from typing import Any

ADVISORY_LABEL = "Advisory Only — Requires Clinician Sign-Off"


def usable(row: dict[str, Any]) -> bool:
    """Returns True if the clinical table row is clinician-verified or unverified rows are allowed."""
    return bool(row.get("verified")) or os.getenv("ALLOW_UNVERIFIED") == "1"


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
        "source": "UZA casus voorbeelden.docx p.1 & UZA CINV v2 p.1-2",
        "verified": False,
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
        "source": "UZA casus voorbeelden.docx p.1 & UZA CINV v2 p.1-2",
        "verified": False,
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
        "source": "UZA casus voorbeelden.docx p.2 & UZA CINV v2 p.1-2",
        "verified": False,
    },
}

# Curated UZA v2 + POGO / MASCC Pediatric Antineoplastic Emetogenicity Reference Table
PEDIATRIC_CHEMO_EMETOGENICITY: dict[str, dict[str, Any]] = {
    # High Emetic Risk (>= 90% frequency without prophylaxis)
    "cisplatin": {
        "tier": "High",
        "uza_tier": "High",
        "pogo_tier": "High",
        "rank": 4,
        "emetic_frequency_pct": ">=90%",
        "notes": "Biphasic CINV (acute 0-24h + delayed 24-120h); mandates quadruple/triple prophylaxis.",
        "guideline": "UZA Anti-emetica beleid CINV v2 p.1 & POGO 250111",
        "source": "UZA CINV v2 p.1 & POGO 250111 p.12",
        "verified": False,
    },
    "carboplatin": {
        "tier": "High",
        "uza_tier": "High",
        "pogo_tier": "Moderate (High at high pediatric AUC)",
        "rank": 4,
        "emetic_frequency_pct": ">=90%",
        "notes": "UZA v2 p.1 classifies Carboplatin as High emetogenic; POGO classifies standard doses as Moderate/High.",
        "guideline": "UZA Anti-emetica beleid CINV v2 p.1 & POGO 250111",
        "source": "UZA CINV v2 p.1 & POGO 250111 p.12",
        "verified": False,
    },
    "cyclophosphamide": {
        "tier": "High",
        "uza_tier": "High (>1500 mg/m2) / Moderate (<=1500 mg/m2)",
        "pogo_tier": "High (>=1000 mg/m2) / Moderate (<1000 mg/m2)",
        "rank": 4,
        "emetic_frequency_pct": ">=90% (at >1500 mg/m2 UZA or >=1000 mg/m2 POGO, or with anthracycline)",
        "notes": "UZA v2 p.1: High at >1500 mg/m2 IV or in combination with anthracyclines; Moderate at <=1500 mg/m2. CYP3A4 substrate.",
        "guideline": "UZA Anti-emetica beleid CINV v2 p.1 & POGO 250111",
        "source": "UZA CINV v2 p.1 & POGO 250111 p.13",
        "verified": False,
    },
    "dacarbazine": {
        "tier": "High",
        "uza_tier": "High",
        "pogo_tier": "High",
        "rank": 4,
        "emetic_frequency_pct": ">=90%",
        "notes": "Potent acute emetogen; requires HEC antiemetic coverage.",
        "guideline": "UZA Anti-emetica beleid CINV v2 p.1 & POGO 250111",
        "source": "UZA CINV v2 p.1 & POGO 250111 p.12",
        "verified": False,
    },
    "dactinomycin": {
        "tier": "High",
        "uza_tier": "High (>=1.35 mg/m2) / Moderate (<1.35 mg/m2)",
        "pogo_tier": "High",
        "rank": 4,
        "emetic_frequency_pct": ">=90%",
        "notes": "Actinomycin D carries High emetic risk at >=1.35 mg/m2 IV in UZA v2 p.1 (Moderate below).",
        "guideline": "UZA Anti-emetica beleid CINV v2 p.1 & POGO 250111",
        "source": "UZA CINV v2 p.1 & POGO 250111 p.12",
        "verified": False,
    },
    "melphalan": {
        "tier": "High",
        "uza_tier": "High",
        "pogo_tier": "High",
        "rank": 4,
        "emetic_frequency_pct": ">=90%",
        "notes": "High emetic risk IV alkylating agent per UZA v2 p.1.",
        "guideline": "UZA Anti-emetica beleid CINV v2 p.1",
        "source": "UZA CINV v2 p.1",
        "verified": False,
    },
    "thiotepa": {
        "tier": "High",
        "uza_tier": "High (>=300 mg/m2) / Low (<300 mg/m2)",
        "pogo_tier": "High (>=300 mg/m2)",
        "rank": 4,
        "emetic_frequency_pct": ">=90% (at >=300 mg/m2)",
        "notes": "High emetic risk at IV >=300 mg/m2; Low at <300 mg/m2 per UZA v2 p.1.",
        "guideline": "UZA Anti-emetica beleid CINV v2 p.1",
        "source": "UZA CINV v2 p.1",
        "verified": False,
    },
    "ifosfamide": {
        "tier": "Moderate",
        "uza_tier": "Moderate (High with Etoposide)",
        "pogo_tier": "Moderate (High with Etoposide)",
        "rank": 3,
        "emetic_frequency_pct": "30-90% (Moderate alone; High when combined with etoposide or anthracycline)",
        "notes": (
            "Moderate emetic risk alone (UZA v2 p.1 MATIG EMETOGEEN / POGO); escalates to High (HEC) "
            "when combined with etoposide (e.g., iEuroEwing 5-day IE regimen, Casus 3). "
            "Caution with aprepitant (CYP3A4 neurotoxic chloroacetaldehyde metabolite)."
        ),
        "guideline": "UZA Anti-emetica beleid CINV v2 p.1 (July 2026) & POGO 250111",
        "source": "UZA CINV v2 p.1 & POGO 250111 p.15",
        "verified": False,
    },
    # Moderate Emetic Risk (30-90% frequency without prophylaxis)
    "doxorubicin": {
        "tier": "Moderate",
        "uza_tier": "High",
        "pogo_tier": "Moderate",
        "rank": 3,
        "emetic_frequency_pct": "30-90% (POGO MEC; UZA v2 p.1 classifies Doxorubicin as HOOG EMETOGEEN)",
        "notes": "UZA v2 p.1 lists Doxorubicin under HOOG EMETOGEEN; POGO classifies single-agent Doxorubicin as Moderate (escalating to High with cyclophosphamide/ifosfamide).",
        "guideline": "UZA Anti-emetica beleid CINV v2 p.1 & POGO 250111",
        "source": "UZA CINV v2 p.1 & POGO 250111 p.14",
        "verified": False,
    },
    "daunorubicin": {
        "tier": "Moderate",
        "uza_tier": "Moderate",
        "pogo_tier": "Moderate",
        "rank": 3,
        "emetic_frequency_pct": "30-90%",
        "notes": "Moderate emetic risk anthracycline (UZA v2 p.1); strictly omit dexamethasone in ALL protocols (Casus 2).",
        "guideline": "UZA Anti-emetica beleid CINV v2 p.1 & POGO 250111",
        "source": "UZA CINV v2 p.1 & POGO 250111 p.14",
        "verified": False,
    },
    "epirubicin": {
        "tier": "Moderate",
        "uza_tier": "Moderate",
        "pogo_tier": "Moderate",
        "rank": 3,
        "emetic_frequency_pct": "30-90%",
        "notes": "Moderate emetic risk anthracycline.",
        "guideline": "POGO / MASCC Pediatric Emetogenicity Guideline",
        "source": "POGO 250111 p.14",
        "verified": False,
    },
    "idarubicin": {
        "tier": "Moderate",
        "uza_tier": "Moderate",
        "pogo_tier": "Moderate",
        "rank": 3,
        "emetic_frequency_pct": "30-90%",
        "notes": "Moderate emetic risk anthracycline (UZA v2 p.1).",
        "guideline": "UZA Anti-emetica beleid CINV v2 p.1 & POGO 250111",
        "source": "UZA CINV v2 p.1 & POGO 250111 p.14",
        "verified": False,
    },
    "cytarabine": {
        "tier": "Moderate",
        "uza_tier": "High (>=3 g/m2) / Moderate (>200 mg to <3 g/m2) / Low (<=200 mg/m2)",
        "pogo_tier": "High (>=3 g/m2) / Moderate / Low",
        "rank": 3,
        "emetic_frequency_pct": "30-90% (High >= 3 g/m2; Moderate >200 mg/m2 to <3 g/m2; Low <=200 mg/m2)",
        "notes": "UZA v2 p.1 dose-dependent: High at >=3000 mg/m2; Moderate at >200 to <3000 mg/m2; Low at <=200 mg/m2.",
        "guideline": "UZA Anti-emetica beleid CINV v2 p.1 & POGO 250111",
        "source": "UZA CINV v2 p.1 & POGO 250111 p.13",
        "verified": False,
    },
    "methotrexate": {
        "tier": "Moderate",
        "uza_tier": "High (>=12 g/m2) / Moderate (>=250 mg to <12 g/m2) / Low (<250 mg/m2) / Minimal (<50 mg/m2)",
        "pogo_tier": "High (>=12 g/m2) / Moderate / Low / Minimal",
        "rank": 3,
        "emetic_frequency_pct": "30-90% (High >=12 g/m2; Moderate >=250 mg/m2; Low 50-249 mg/m2; Minimal <50 mg/m2)",
        "notes": "UZA v2 p.1 dose-dependent: High at >=12000 mg/m2 IV; Moderate at >=250 mg/m2; Low at <250 mg/m2 or IT; Minimal at <50 mg/m2.",
        "guideline": "UZA Anti-emetica beleid CINV v2 p.1 & POGO 250111",
        "source": "UZA CINV v2 p.1 & POGO 250111 p.14",
        "verified": False,
    },
    "irinotecan": {
        "tier": "Moderate",
        "uza_tier": "Moderate",
        "pogo_tier": "Moderate",
        "rank": 3,
        "emetic_frequency_pct": "30-90%",
        "notes": "Moderate emetic risk (UZA v2 p.1); causes acute cholinergic and delayed diarrhea/emesis; CYP3A4 substrate.",
        "guideline": "UZA Anti-emetica beleid CINV v2 p.1 & POGO 250111",
        "source": "UZA CINV v2 p.1 & POGO 250111 p.14",
        "verified": False,
    },
    "oxaliplatin": {
        "tier": "Moderate",
        "uza_tier": "Moderate",
        "pogo_tier": "Moderate",
        "rank": 3,
        "emetic_frequency_pct": "30-90%",
        "notes": "Moderate emetic risk platinum analog.",
        "guideline": "POGO / MASCC Pediatric Emetogenicity Guideline",
        "source": "POGO 250111 p.14",
        "verified": False,
    },
    "temozolomide": {
        "tier": "Moderate",
        "uza_tier": "Low",
        "pogo_tier": "Moderate",
        "rank": 3,
        "emetic_frequency_pct": "10-90% (UZA v2 p.1 Low; POGO Moderate)",
        "notes": "UZA v2 p.1 lists Temozolomide under LAAG EMETOGEEN (Ondansetron 1x/d); POGO lists oral/IV temozolomide as Moderate.",
        "guideline": "UZA Anti-emetica beleid CINV v2 p.1 & POGO 250111",
        "source": "UZA CINV v2 p.1 & POGO 250111 p.15",
        "verified": False,
    },
    # Low Emetic Risk (10-30% frequency without prophylaxis)
    "etoposide": {
        "tier": "Low",
        "uza_tier": "Low (High with Ifosfamide or Cytarabine)",
        "pogo_tier": "Low (High with Ifosfamide)",
        "rank": 2,
        "emetic_frequency_pct": "10-30%",
        "notes": "Low emetic risk alone (UZA v2 p.1); escalates to High (HEC) when combined with Ifosfamide (Casus 3) or Cytarabine.",
        "guideline": "UZA Anti-emetica beleid CINV v2 p.1 & POGO 250111",
        "source": "UZA CINV v2 p.1 & POGO 250111 p.16",
        "verified": False,
    },
    "topotecan": {
        "tier": "Low",
        "uza_tier": "Low",
        "pogo_tier": "Low",
        "rank": 2,
        "emetic_frequency_pct": "10-30%",
        "notes": "Low emetic risk camptothecin analog (UZA v2 p.1).",
        "guideline": "UZA Anti-emetica beleid CINV v2 p.1 & POGO 250111",
        "source": "UZA CINV v2 p.1 & POGO 250111 p.16",
        "verified": False,
    },
    "paclitaxel": {
        "tier": "Low",
        "uza_tier": "Low",
        "pogo_tier": "Low",
        "rank": 2,
        "emetic_frequency_pct": "10-30%",
        "notes": "Low emetic risk taxane.",
        "guideline": "POGO / MASCC Pediatric Emetogenicity Guideline",
        "source": "POGO 250111 p.16",
        "verified": False,
    },
    "gemcitabine": {
        "tier": "Low",
        "uza_tier": "Low",
        "pogo_tier": "Low",
        "rank": 2,
        "emetic_frequency_pct": "10-30%",
        "notes": "Low emetic risk nucleoside analog (UZA v2 p.1).",
        "guideline": "UZA Anti-emetica beleid CINV v2 p.1 & POGO 250111",
        "source": "UZA CINV v2 p.1 & POGO 250111 p.16",
        "verified": False,
    },
    "fluorouracil": {
        "tier": "Low",
        "uza_tier": "Low",
        "pogo_tier": "Low",
        "rank": 2,
        "emetic_frequency_pct": "10-30%",
        "notes": "Low emetic risk antimetabolite.",
        "guideline": "POGO / MASCC Pediatric Emetogenicity Guideline",
        "source": "POGO 250111 p.16",
        "verified": False,
    },
    # Minimal Emetic Risk (< 10% frequency without prophylaxis in POGO; Low in UZA v2 p.1 for vincas/asparaginase/blina)
    "vincristine": {
        "tier": "Minimal",
        "uza_tier": "Low",
        "pogo_tier": "Minimal",
        "rank": 1,
        "emetic_frequency_pct": "<10% (POGO Minimal; UZA v2 p.1 LAAG EMETOGEEN)",
        "notes": "Minimal/Low emetic risk; major CYP3A4/P-gp neurotoxicity interaction with azole antifungals (hold azole 24-48h).",
        "guideline": "UZA Anti-emetica beleid CINV v2 p.1 & POGO 250111",
        "source": "UZA CINV v2 p.1 & POGO 250111 p.17",
        "verified": False,
    },
    "vinblastine": {
        "tier": "Minimal",
        "uza_tier": "Low",
        "pogo_tier": "Minimal",
        "rank": 1,
        "emetic_frequency_pct": "<10%",
        "notes": "Minimal/Low emetic risk vinca alkaloid (UZA v2 p.1); CYP3A4 substrate.",
        "guideline": "UZA Anti-emetica beleid CINV v2 p.1 & POGO 250111",
        "source": "UZA CINV v2 p.1 & POGO 250111 p.17",
        "verified": False,
    },
    "bleomycin": {
        "tier": "Minimal",
        "uza_tier": "Minimal",
        "pogo_tier": "Minimal",
        "rank": 1,
        "emetic_frequency_pct": "<10%",
        "notes": "Minimal emetic risk (UZA v2 p.1).",
        "guideline": "UZA Anti-emetica beleid CINV v2 p.1 & POGO 250111",
        "source": "UZA CINV v2 p.1 & POGO 250111 p.17",
        "verified": False,
    },
    "pegaspargase": {
        "tier": "Minimal",
        "uza_tier": "Low",
        "pogo_tier": "Minimal",
        "rank": 1,
        "emetic_frequency_pct": "<10%",
        "notes": "UZA v2 p.1 lists Pegasparaginase under LAAG EMETOGEEN; POGO lists as Minimal. Monitor for pancreatitis.",
        "guideline": "UZA Anti-emetica beleid CINV v2 p.1 & POGO 250111",
        "source": "UZA CINV v2 p.1 & POGO 250111 p.17",
        "verified": False,
    },
    "asparaginase": {
        "tier": "Minimal",
        "uza_tier": "Low",
        "pogo_tier": "Minimal",
        "rank": 1,
        "emetic_frequency_pct": "<10%",
        "notes": "UZA v2 p.1 lists Asparaginase under LAAG EMETOGEEN; POGO lists as Minimal.",
        "guideline": "UZA Anti-emetica beleid CINV v2 p.1 & POGO 250111",
        "source": "UZA CINV v2 p.1 & POGO 250111 p.17",
        "verified": False,
    },
    "mercaptopurine": {
        "tier": "Minimal",
        "uza_tier": "Minimal",
        "pogo_tier": "Minimal",
        "rank": 1,
        "emetic_frequency_pct": "<10%",
        "notes": "Minimal emetic risk oral maintenance agent.",
        "guideline": "POGO / MASCC Pediatric Emetogenicity Guideline",
        "source": "POGO 250111 p.17",
        "verified": False,
    },
    "blinatumomab": {
        "tier": "Minimal",
        "uza_tier": "Low",
        "pogo_tier": "Minimal",
        "rank": 1,
        "emetic_frequency_pct": "<10%",
        "notes": "BiTE therapy (UZA v2 p.1 LAAG EMETOGEEN; POGO Minimal).",
        "guideline": "UZA Anti-emetica beleid CINV v2 p.1 & POGO 250111",
        "source": "UZA CINV v2 p.1 & POGO 250111 p.17",
        "verified": False,
    },
}

# Combination escalation rules from UZA CINV v2 p.1 & POGO 250111
COMBINATION_ESCALATION_RULES: list[dict[str, Any]] = [
    {
        "id": "combo_ifosfamide_etoposide",
        "required_drugs": {"ifosfamide", "etoposide"},
        "tier": "High",
        "rank": 4,
        "rationale": (
            "Multi-agent combination escalation applied (Casus 3 / iEuroEwing IE rule): "
            "While Ifosfamide is Moderate (MEC) and Etoposide is Low (LEC) individually, "
            "the combination of Ifosfamide + Etoposide is classified as High Emetogenic Risk (HEC) "
            "per UZA July 2026 v2 policy ('Combinatie: Ifosfamide/Etoposide = HOOG EMETOGEEN') "
            "and POGO Emetogenicity Classification Guidelines (Final-rev-250111)."
        ),
        "source": "UZA CINV v2 p.1 & POGO 250111 p.18",
        "verified": False,
    },
    {
        "id": "combo_cytarabine_dauno_or_etoposide",
        "required_drugs": {"cytarabine"},
        "any_of_drugs": {"daunorubicin", "etoposide"},
        "tier": "High",
        "rank": 4,
        "rationale": (
            "Multi-agent combination escalation applied: Cytarabine + Daunorubicin/Etoposide "
            "escalates to High Emetogenic Risk (HEC) per UZA July 2026 v2 policy ('Combinatie: Cytarabine/Daunorubicine of Etoposide') and POGO guidelines."
        ),
        "source": "UZA CINV v2 p.1 & POGO 250111 p.18",
        "verified": False,
    },
    {
        "id": "combo_cyclophosphamide_anthracycline",
        "required_drugs": {"cyclophosphamide"},
        "any_of_drugs": {"doxorubicin", "daunorubicin", "epirubicin", "idarubicin"},
        "tier": "High",
        "rank": 4,
        "rationale": (
            "Multi-agent synergy escalation applied: Cyclophosphamide + Anthracycline "
            "escalates overall pediatric emetogenicity to High per UZA July 2026 v2 p.1 & POGO/MASCC guidelines."
        ),
        "source": "UZA CINV v2 p.1 & POGO 250111 p.18",
        "verified": False,
    },
    {
        "id": "combo_two_moderate",
        "min_moderate_count": 2,
        "tier": "High",
        "rank": 4,
        "rationale": (
            "Multi-agent synergy escalation applied: combination of multiple Moderate-risk "
            "agents escalates overall pediatric emetogenicity to High per UZA July 2026 v2 & POGO/MASCC multi-agent guidelines."
        ),
        "source": "UZA CINV v2 p.1 & POGO 250111 p.18",
        "verified": False,
    },
]

RANK_TO_TIER = {4: "High", 3: "Moderate", 2: "Low", 1: "Minimal", 0: "Unknown"}
ANTHRACYCLINES = {"doxorubicin", "daunorubicin", "epirubicin", "idarubicin"}
STRONG_MODERATE_AZOLES = {
    "voriconazole",
    "posaconazole",
    "itraconazole",
    "fluconazole",
    "isavuconazole",
    "ketoconazole",
}
NK1_ANTAGONISTS = {"aprepitant", "fosaprepitant"}
QTC_PROLONGING_AGENTS = {
    "ondansetron",
    "granisetron",
    "olanzapine",
    "metoclopramide",
    "domperidone",
    "haloperidol",
    "ciprofloxacin",
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

# CredibleMeds QTc risk categories
QTC_RISK_REGISTRY: dict[str, dict[str, Any]] = {
    "ondansetron": {"category": "Known Risk", "score": 3, "source": "CredibleMeds / UZA CINV v2", "verified": False},
    "voriconazole": {"category": "Known Risk", "score": 3, "source": "CredibleMeds", "verified": False},
    "posaconazole": {"category": "Known Risk", "score": 2, "source": "CredibleMeds", "verified": False},
    "haloperidol": {"category": "Known Risk", "score": 3, "source": "CredibleMeds", "verified": False},
    "domperidone": {"category": "Known Risk", "score": 3, "source": "CredibleMeds", "verified": False},
    "ciprofloxacin": {"category": "Known Risk", "score": 3, "source": "CredibleMeds", "verified": False},
    "granisetron": {"category": "Possible Risk", "score": 1, "source": "CredibleMeds", "verified": False},
    "fluconazole": {"category": "Conditional Risk", "score": 1, "source": "CredibleMeds", "verified": False},
    "olanzapine": {"category": "Conditional Risk", "score": 1, "source": "CredibleMeds", "verified": False},
    "palonosetron": {"category": "No Added Risk", "score": 0, "source": "CredibleMeds", "verified": False},
    "aprepitant": {"category": "No Added Risk", "score": 0, "source": "CredibleMeds", "verified": False},
    "dexamethasone": {"category": "No Added Risk", "score": 0, "source": "CredibleMeds", "verified": False},
}

# Phase 3: Deterministic Dose Rules (UZA CINV v2 p.2)
DOSE_RULES: list[dict[str, Any]] = [
    {
        "drug": "ondansetron",
        "route": "PO",
        "days": "each",
        "basis": "mg_per_m2",
        "per_unit": 5.0,
        "max_mg": 8.0,
        "source": "UZA CINV v2 p.2",
        "verified": False,
    },
    {
        "drug": "ondansetron",
        "route": "IV",
        "days": "each",
        "basis": "mg_per_m2",
        "per_unit": 5.0,
        "max_mg": 8.0,
        "source": "UZA CINV v2 p.2",
        "verified": False,
    },
    {
        "drug": "aprepitant",
        "route": "PO",
        "days": "D1",
        "basis": "mg_per_kg",
        "per_unit": 3.0,
        "max_mg": 125.0,
        "source": "UZA CINV v2 p.2",
        "verified": False,
    },
    {
        "drug": "aprepitant",
        "route": "PO",
        "days": "D2-D3",
        "basis": "mg_per_kg",
        "per_unit": 2.0,
        "max_mg": 80.0,
        "source": "UZA CINV v2 p.2",
        "verified": False,
    },
    {
        "drug": "aprepitant",
        "route": "IV",
        "days": "D1",
        "basis": "mg_per_kg",
        "per_unit": 3.0,
        "max_mg": 115.0,
        "source": "UZA CINV v2 p.2",
        "verified": False,
    },
    {
        "drug": "aprepitant",
        "route": "IV",
        "days": "D2-D3",
        "basis": "mg_per_kg",
        "per_unit": 2.0,
        "max_mg": 80.0,
        "source": "UZA CINV v2 p.2",
        "verified": False,
    },
    {
        "drug": "dexamethasone",
        "route": "PO",
        "days": "each",
        "basis": "uza_bsa_split",
        "bsa_threshold": 0.6,
        "low_bsa_mg": 2.0,
        "high_bsa_mg": 4.0,
        "cyp3a4_factor": 0.5,
        "source": "UZA CINV v2 p.2",
        "verified": False,
    },
    {
        "drug": "dexamethasone",
        "route": "IV",
        "days": "each",
        "basis": "uza_bsa_split",
        "bsa_threshold": 0.6,
        "low_bsa_mg": 2.0,
        "high_bsa_mg": 4.0,
        "cyp3a4_factor": 0.5,
        "aacidexam_active_mg_per_ml": 4.0,
        "source": "UZA CINV v2 p.2",
        "verified": False,
    },
    {
        "drug": "olanzapine",
        "route": "PO",
        "days": "each",
        "basis": "mg_per_kg",
        "per_unit": 0.1,
        "max_mg": 5.0,
        "round_down_mg": 0.5,
        "source": "UZA CINV v2 p.2",
        "verified": False,
    },
    {
        "drug": "olanzapine",
        "route": "IV",
        "days": "each",
        "basis": "mg_per_kg",
        "per_unit": 0.1,
        "max_mg": 5.0,
        "round_down_mg": 0.5,
        "source": "UZA CINV v2 p.2",
        "verified": False,
    },
    {
        "drug": "lorazepam",
        "route": "PO",
        "days": "PRN q6h",
        "basis": "mg_per_kg",
        "per_unit": 0.025,
        "max_mg": 2.0,
        "source": "UZA CINV v2 p.2",
        "verified": False,
    },
    {
        "drug": "lorazepam",
        "route": "IV",
        "days": "PRN q6h",
        "basis": "mg_per_kg",
        "per_unit": 0.025,
        "max_mg": 2.0,
        "source": "UZA CINV v2 p.2",
        "verified": False,
    },
    {
        "drug": "alizapride",
        "route": "PO",
        "days": "chemo_days",
        "basis": "mg_per_kg",
        "per_unit": 1.0,
        "max_mg": 50.0,
        "source": "UZA CINV v2 p.2",
        "verified": False,
    },
    {
        "drug": "alizapride",
        "route": "IV",
        "days": "chemo_days",
        "basis": "mg_per_kg",
        "per_unit": 1.0,
        "max_mg": 50.0,
        "source": "UZA CINV v2 p.2",
        "verified": False,
    },
]

FORMULATIONS: list[dict[str, Any]] = [
    {
        "drug": "ondansetron",
        "route": "PO",
        "form": "syrup (4 mg/5 mL = 0.8 mg/mL)",
        "mg_per_ml": 0.8,
        "step_ml": 0.5,
        "source": "UZA Pharmacy Formulary / CINV v2 p.2",
        "verified": False,
    },
    {
        "drug": "ondansetron",
        "route": "IV",
        "form": "IV solution (2 mg/mL)",
        "mg_per_ml": 2.0,
        "step_ml": 0.1,
        "source": "UZA Pharmacy Formulary / CINV v2 p.2",
        "verified": False,
    },
    {
        "drug": "aprepitant",
        "route": "PO",
        "form": "oral suspension (25 mg/mL)",
        "mg_per_ml": 25.0,
        "step_ml": 0.5,
        "source": "UZA Pharmacy Formulary / CINV v2 p.2",
        "verified": False,
    },
    {
        "drug": "dexamethasone",
        "route": "PO",
        "form": "oral solution (1 mg/mL)",
        "mg_per_ml": 1.0,
        "step_ml": 0.5,
        "source": "UZA Pharmacy Formulary / CINV v2 p.2",
        "verified": False,
    },
    {
        "drug": "dexamethasone",
        "route": "IV",
        "form": "Aacidexam IV (5 mg/mL = ±4 mg/mL active base)",
        "mg_per_ml": 4.0,
        "step_ml": 0.25,
        "source": "UZA CINV v2 p.2",
        "verified": False,
    },
    {
        "drug": "olanzapine",
        "route": "PO",
        "form": "orally disintegrating tablet / liquid equiv (1 mg/mL)",
        "mg_per_ml": 1.0,
        "step_ml": 0.5,
        "source": "UZA CINV v2 p.2",
        "verified": False,
    },
]

# Phase 5: Parent Passport Schedule Rules & Multilingual Instructions
SCHEDULE_RULES: list[dict[str, Any]] = [
    {
        "drug": "ondansetron",
        "applies_to": "chemo_and_delayed",
        "delayed_days": 2,
        "clock_times": ["08:00", "20:00"],
        "source": "UZA CINV v2 p.2 (Bij ontslag: 2x/d PO, t.e.m. 3 dagen na laatste chemo)",
        "verified": False,
    },
    {
        "drug": "aprepitant",
        "applies_to": "first_3_days",
        "delayed_days": 0,
        "clock_times": ["08:00"],
        "source": "UZA CINV v2 p.2 (D1-D3 PO 1x/d)",
        "verified": False,
    },
    {
        "drug": "dexamethasone",
        "applies_to": "chemo_days_only",
        "delayed_days": 0,
        "clock_times": ["08:00", "16:00"],
        "source": "UZA CINV v2 p.2 (Dexamethasone: enkel op dagen van chemotherapie, 2x/d)",
        "verified": False,
    },
    {
        "drug": "olanzapine",
        "applies_to": "chemo_and_delayed",
        "delayed_days": 2,
        "clock_times": ["20:00"],
        "source": "UZA CINV v2 p.2 (Olanzapine: bij voorkeur 's avonds, t.e.m. 3 dagen na laatste chemo)",
        "verified": False,
    },
]

PARENT_INSTRUCTIONS: dict[str, dict[str, dict[str, Any]]] = {
    "en": {
        "ondansetron": {
            "instruction": "Give using the oral dosing syringe at morning and bedtime. Can be taken with or without food.",
            "rescue": "If your child vomits within 30 minutes of a dose, contact the oncology ward before repeating the dose.",
            "source": "UZA CINV v2 p.2 & Belgian Family Handover",
            "verified": False,
        },
        "aprepitant": {
            "instruction": "Give once daily in the morning, 1 hour before chemotherapy on Day 1 and in the morning on Days 2–3.",
            "rescue": "Do not give grapefruit juice while taking aprepitant.",
            "source": "UZA CINV v2 p.2",
            "verified": False,
        },
        "dexamethasone": {
            "instruction": "Give with food or milk in the morning and afternoon on chemotherapy days only to protect the stomach.",
            "rescue": "Never give dexamethasone if the oncology team marked 'GEEN Dexamethasone' on your child's protocol.",
            "source": "UZA CINV v2 p.2",
            "verified": False,
        },
        "olanzapine": {
            "instruction": "Give once daily in the evening (may cause mild drowsiness that helps with sleep).",
            "rescue": "Contact the pediatric oncology team if your child cannot keep fluids down for more than 12 hours.",
            "source": "UZA CINV v2 p.2",
            "verified": False,
        },
    },
    "nl": {
        "ondansetron": {
            "instruction": "Geef met het doseerspuitje 's ochtends en 's avonds (2x/dag bij ontslag). Mag met of zonder voedsel.",
            "rescue": "Braakt uw kind binnen 30 minuten na inname? Bel eerst de afdeling kinderoncologie voor u een nieuwe dosis geeft.",
            "source": "UZA CINV v2 p.2",
            "verified": False,
        },
        "aprepitant": {
            "instruction": "Geef 1x per dag 's ochtends (op dag 1 een uur voor de chemotherapie, en op dag 2 en 3 's ochtends).",
            "rescue": "Geef geen pompelmoessap tijdens de behandeling met aprepitant.",
            "source": "UZA CINV v2 p.2",
            "verified": False,
        },
        "dexamethasone": {
            "instruction": "Geef enkel op dagen van chemotherapie (2x/dag) tijdens de maaltijd of met wat melk.",
            "rescue": "OPGELET: GEEN dexamethasone geven bij ALL, hersentumoren of dinutuximab beta.",
            "source": "UZA CINV v2 p.2",
            "verified": False,
        },
        "olanzapine": {
            "instruction": "Geef 1x per dag bij voorkeur 's avonds (dosis naar beneden afgerond op 0,5 mg; kan slaperigheid geven).",
            "rescue": "Neem direct contact op met het ziekenhuis bij tekenen van uitdroging of aanhoudend braken.",
            "source": "UZA CINV v2 p.2",
            "verified": False,
        },
    },
    "fr": {
        "ondansetron": {
            "instruction": "Administrez avec la seringue orale matin et soir (2x/jour à domicile), avec ou sans nourriture.",
            "rescue": "Si votre enfant vomit dans les 30 minutes suivant la prise, appelez le service d'oncologie pédiatrique.",
            "source": "UZA CINV v2 p.2",
            "verified": False,
        },
        "aprepitant": {
            "instruction": "Administrez 1x par jour le matin (1 heure avant la chimiothérapie à J1, puis le matin à J2–J3).",
            "rescue": "Évitez le jus de pamplemousse pendant le traitement par aprépitant.",
            "source": "UZA CINV v2 p.2",
            "verified": False,
        },
        "dexamethasone": {
            "instruction": "Administrez uniquement les jours de chimiothérapie (2x/jour) pendant le repas.",
            "rescue": "ATTENTION : PAS de dexaméthasone en cas de LAL (ALL), tumeur cérébrale ou dinutuximab bêta.",
            "source": "UZA CINV v2 p.2",
            "verified": False,
        },
        "olanzapine": {
            "instruction": "Administrez 1x par jour de préférence le soir (dose arrondie au 0,5 mg inférieur).",
            "rescue": "Contactez immédiatement l'hôpital en cas de signes de déshydratation ou de vomissements persistants.",
            "source": "UZA CINV v2 p.2",
            "verified": False,
        },
    },
}

# Curated Belgian Hospital CINV Patient Resources (from CINV resources in Belgium.xlsx)
BELGIAN_CINV_PATIENT_RESOURCES: list[dict[str, str]] = [
    {
        "hospital": "UZA (Koningin Mathilde Moeder- en kindcentrum)",
        "title": "Anti-emetica beleid CINV v2 (Juli 2026) & Kinderoncologie Portal",
        "lang": "NL",
        "url": "https://www.uza.be/oncologie-hematologie-kinderen",
        "access_tier": "GREEN_CLINICAL_BASELINE",
    },
    {
        "hospital": "ZAS (Antwerp Shared-Care Network with UZA)",
        "title": "Chemotherapie: Informatie voor patiënten (PDF)",
        "lang": "NL",
        "url": "https://media.zas.be/m/1be42769d38ec4ee/original/Chemotherapie.pdf",
        "access_tier": "GREEN_DIRECT_PDF",
    },
    {
        "hospital": "CHU de Liège",
        "title": "Les nausées et les vomissements (Brochure A5 2024)",
        "lang": "FR",
        "url": "https://www.chuliege.be/cms/c_60648/fr/broch-a5-les-nausees-et-les-vomissements-2024-pp",
        "access_tier": "GREEN_DIRECT_PDF",
    },
    {
        "hospital": "Stichting tegen Kanker / Fondation contre le Cancer",
        "title": "Misselijkheid en braken / Nausées et vomissements",
        "lang": "NL/FR/DE",
        "url": "https://www.cancer.be/kanker/bijwerkingen/misselijkheid-en-braken",
        "access_tier": "GREEN_TRILINGUAL",
    },
    {
        "hospital": "KickCancer Foundation",
        "title": "Family Support & Research Hub",
        "lang": "EN/FR/NL",
        "url": "https://kickcancer.org/en",
        "access_tier": "GREEN_TRILINGUAL",
    },
    {
        "hospital": "UZ Leuven (KIDZ)",
        "title": "Misselijkheid en braken bij chemotherapie",
        "lang": "NL",
        "url": "https://www.uzleuven.be/nl/chemotherapie/bijwerkingen/misselijkheid-en-braken",
        "access_tier": "AMBER_LANGUAGE_RESET_NOTE",
    },
]
