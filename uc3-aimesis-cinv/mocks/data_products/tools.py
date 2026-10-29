"""Agent Tools for Use Case 3: AImesis CINV & Toxicology.

Provides multi-agent chemotherapy emetogenicity classification,
UZA Koningin Mathilde Moeder- en kindcentrum July 2026 v2 CINV Policy engine
(`Anti-emetica beleid CINV - V2.pdf`), POGO guideline alignment (Story 5 literature
cross-check), CYP3A4 DDI screening, CredibleMeds QTc risk assessment, and
Story 4 CINV Patient Passport generation with Belgian CINV hospital resources.
"""

from __future__ import annotations
import math
from typing import Dict, Any, List, Optional

# Curated single-agent emetogenicity levels (POGO baseline)
EMETOGENICITY_TABLE = {
    # High (>= 90%)
    "cisplatin": "High",
    "dacarbazine": "High",
    "mechlorethamine": "High",
    "streptozocin": "High",
    "carmustine": "High",
    "ifosfamide": "High",
    # Moderate (30-90%)
    "carboplatin": "Moderate",
    "doxorubicin": "Moderate",
    "daunorubicin": "Moderate",
    "cyclophosphamide": "Moderate",
    "cytarabine": "Moderate",
    "methotrexate": "Moderate",
    "irinotecan": "Moderate",
    "oxaliplatin": "Moderate",
    # Low (10-30%)
    "etoposide": "Low",
    "paclitaxel": "Low",
    "docetaxel": "Low",
    "fluorouracil": "Low",
    "mitoxantrone": "Low",
    # Minimal (< 10%)
    "vincristine": "Minimal",
    "vinblastine": "Minimal",
    "bleomycin": "Minimal",
    "asparaginase": "Minimal",
    "pegaspargase": "Minimal",
    "hydroxyurea": "Minimal"
}

# CredibleMeds QTc risk categories
QTC_RISK_REGISTRY = {
    "ondansetron": {"category": "Known Risk", "score": 3},
    "voriconazole": {"category": "Known Risk", "score": 3},
    "haloperidol": {"category": "Known Risk", "score": 3},
    "ciprofloxacin": {"category": "Known Risk", "score": 3},
    "granisetron": {"category": "Possible Risk", "score": 1},
    "fluconazole": {"category": "Conditional Risk", "score": 1},
    "olanzapine": {"category": "Conditional Risk", "score": 1},
    "palonosetron": {"category": "No Added Risk", "score": 0},
    "aprepitant": {"category": "No Added Risk", "score": 0},
    "dexamethasone": {"category": "No Added Risk", "score": 0}
}

# Curated Belgian Hospital CINV Patient Resources (from [Awaiting review] CINV resources in Belgium.xlsx)
BELGIAN_CINV_PATIENT_RESOURCES = [
    {"hospital": "UZA (Koningin Mathilde Moeder- en kindcentrum)", "title": "Anti-emetica beleid CINV v2 (Juli 2026) & Kinderoncologie Portal", "lang": "NL", "url": "https://www.uza.be/oncologie-hematologie-kinderen", "access_tier": "GREEN_CLINICAL_BASELINE"},
    {"hospital": "ZAS (Antwerp Shared-Care Network with UZA)", "title": "Chemotherapie: Informatie voor patiënten (PDF)", "lang": "NL", "url": "https://media.zas.be/m/1be42769d38ec4ee/original/Chemotherapie.pdf", "access_tier": "GREEN_DIRECT_PDF"},
    {"hospital": "CHU de Liège", "title": "Les nausées et les vomissements (Brochure A5 2024)", "lang": "FR", "url": "https://www.chuliege.be/cms/c_60648/fr/broch-a5-les-nausees-et-les-vomissements-2024-pp", "access_tier": "GREEN_DIRECT_PDF"},
    {"hospital": "Stichting tegen Kanker / Fondation contre le Cancer", "title": "Misselijkheid en braken / Nausées et vomissements", "lang": "NL/FR/DE", "url": "https://www.cancer.be/kanker/bijwerkingen/misselijkheid-en-braken", "access_tier": "GREEN_TRILINGUAL"},
    {"hospital": "KickCancer Foundation", "title": "Family Support & Research Hub", "lang": "EN/FR/NL", "url": "https://kickcancer.org/en", "access_tier": "GREEN_TRILINGUAL"},
    {"hospital": "UZ Leuven (KIDZ)", "title": "Misselijkheid en braken bij chemotherapie", "lang": "NL", "url": "https://www.uzleuven.be/nl/chemotherapie/bijwerkingen/misselijkheid-en-braken", "access_tier": "AMBER_LANGUAGE_RESET_NOTE"},
]


class AImesisTools:
    """Production tools for AImesis CINV agent."""

    def __init__(self):
        pass

    def classify_regimen_emetogenicity(self, drug_list: List[str]) -> Dict[str, Any]:
        """Calculates overall emetogenicity following POGO consensus rules."""
        normalized_drugs = [d.strip().lower() for d in drug_list]
        drug_tiers = {}

        has_high = False
        moderate_count = 0

        for d in normalized_drugs:
            tier = EMETOGENICITY_TABLE.get(d, "Moderate")
            drug_tiers[d] = tier
            if tier == "High":
                has_high = True
            elif tier == "Moderate":
                moderate_count += 1

        if has_high or moderate_count >= 2:
            overall_tier = "High"
            risk_pct = ">= 90%"
            rationale = "Regimen contains an agent with High emetic risk or multiple Moderate agents."
        elif moderate_count == 1:
            overall_tier = "Moderate"
            risk_pct = "30 - 90%"
            rationale = "Regimen contains a single Moderate emetogenicity agent."
        elif any(t == "Low" for t in drug_tiers.values()):
            overall_tier = "Low"
            risk_pct = "10 - 30%"
            rationale = "Regimen contains Low emetogenicity agents with no High or Moderate agents."
        else:
            overall_tier = "Minimal"
            risk_pct = "< 10%"
            rationale = "Regimen consists exclusively of Minimal emetogenicity agents."

        return {
            "overall_tier": overall_tier,
            "risk_percentage": risk_pct,
            "drug_breakdown": drug_tiers,
            "clinical_rationale": rationale
        }

    def evaluate_uza_cinv_policy_v2(
        self,
        drug_list: List[str],
        patient_age_years: float = 9.0,
        patient_weight_kg: float = 28.0,
        bsa_m2: float = 1.02,
        drug_doses_mg_m2: Optional[Dict[str, float]] = None,
        indication: str = "solid_tumor",
        can_swallow_tablets: bool = True,
        prior_breakthrough_cinv: bool = False,
        anticipatory_vomiting: bool = False,
    ) -> Dict[str, Any]:
        """Implements UZA Koningin Mathilde Moeder- en kindcentrum July 2026 v2 CINV Policy (Stories 1-3 & 5-6)."""
        doses = {k.strip().lower(): float(v) for k, v in (drug_doses_mg_m2 or {}).items()}
        drugs = [d.strip().lower() for d in drug_list]

        uza_tiers: Dict[str, str] = {}
        for d in drugs:
            dose = doses.get(d)
            if d in {"cisplatin", "carboplatin", "dacarbazine", "carmustine", "ifosfamide", "doxorubicin", "epirubicin"}:
                uza_tiers[d] = "High"
            elif d == "cyclophosphamide":
                uza_tiers[d] = "High" if (dose is not None and dose > 1500.0) else "Moderate"
            elif d == "cytarabine":
                if dose is not None and dose >= 3000.0:
                    uza_tiers[d] = "High"
                elif dose is not None and dose <= 200.0:
                    uza_tiers[d] = "Low"
                else:
                    uza_tiers[d] = "Moderate"
            elif d == "methotrexate":
                if dose is not None and dose >= 12000.0:
                    uza_tiers[d] = "High"
                elif dose is not None and dose >= 250.0:
                    uza_tiers[d] = "Moderate"
                elif dose is not None and dose >= 50.0:
                    uza_tiers[d] = "Low"
                else:
                    uza_tiers[d] = "Minimal" if dose is not None else "Moderate"
            else:
                uza_tiers[d] = EMETOGENICITY_TABLE.get(d, "Moderate")

        # UZA Combination Elevation Rules (Anti-emetica beleid CINV v2 p. 2)
        drug_set = set(drugs)
        combo_elevated = False
        if ("ifosfamide" in drug_set and "etoposide" in drug_set) or (
            "cyclophosphamide" in drug_set and bool(drug_set.intersection({"doxorubicin", "daunorubicin", "epirubicin", "idarubicin"}))
        ) or (
            "cytarabine" in drug_set and bool(drug_set.intersection({"daunorubicin", "etoposide"}))
        ):
            combo_elevated = True

        if combo_elevated or "High" in uza_tiers.values():
            overall_tier = "High"
        elif "Moderate" in uza_tiers.values():
            overall_tier = "Moderate"
        elif "Low" in uza_tiers.values():
            overall_tier = "Low"
        else:
            overall_tier = "Minimal"

        # UZA Hard Dexamethasone Contraindication ("GEEN dexamethasone" rule)
        ind_lower = indication.lower()
        has_steroid_in_chemo = bool(drug_set.intersection({"dexamethasone", "prednisone", "prednisolone", "methylprednisolone"}))
        has_dinutuximab = "dinutuximab" in drug_set or "dinutuximab beta" in drug_set or "dinutuximab" in ind_lower
        dexa_contraindicated = (
            has_steroid_in_chemo
            or has_dinutuximab
            or "all" in ind_lower
            or "brain" in ind_lower
            or "hersentumor" in ind_lower
            or "glioma" in ind_lower
            or "medulloblastoma" in ind_lower
        )

        # Deterministic UZA BSA & Weight Dosing Calculations
        ondansetron_single_mg = min(round(5.0 * bsa_m2, 2), 8.0)
        ondansetron_freq = "3x/d (q8h)" if overall_tier == "High" else ("2x/d (q12h)" if overall_tier == "Moderate" else "1x/d")
        route_pref = "IV or Orally Disintegrating/Syrup (swallowing override)" if not can_swallow_tablets else "PO / IV"

        aprepitant_indicated = overall_tier == "High" and patient_age_years >= 0.5 and patient_weight_kg > 6.0
        if aprepitant_indicated:
            if patient_age_years >= 12.0 and can_swallow_tablets:
                aprepitant_order = "Aprepitant PO: Day 1 = 125 mg; Days 2–3 = 80 mg 1x/d"
            else:
                d1_mg = min(round(3.0 * patient_weight_kg, 1), 125.0)
                d2_mg = min(round(2.0 * patient_weight_kg, 1), 80.0)
                aprepitant_order = f"(Fos)Aprepitant ({route_pref}): Day 1 = {d1_mg} mg (3 mg/kg, max 125 mg); Days 2–3 = {d2_mg} mg (2 mg/kg, max 80 mg)"
        else:
            aprepitant_order = "Not indicated (Moderate/Low tier or infant <6 months / <=6 kg)"

        if dexa_contraindicated:
            dexa_order = (
                "CONTRAINDICATED ('GEEN DEXAMETHASONE' — UZA July 2026 v2 Policy): "
                "Do NOT prescribe dexamethasone for CINV in ALL protocols, Brain Tumors (hersentumoren), "
                "Dinutuximab beta regimens, or chemo blocks already containing corticosteroids."
            )
        elif overall_tier in {"High", "Moderate"}:
            if bsa_m2 < 0.6:
                dexa_mg = 1.0 if aprepitant_indicated else 2.0
            else:
                dexa_mg = 2.0 if aprepitant_indicated else 4.0
            aacidexam_ml = round(dexa_mg / 4.0, 2)
            dexa_order = (
                f"Dexamethasone {dexa_mg} mg 2x/d ({'50% reduced for Aprepitant CYP3A4' if aprepitant_indicated else 'standard UZA BSA tier'}) "
                f"— UZA Aacidexam® IV Alert: 5 mg/mL ampoule contains ±4 mg/mL active dexamethasone base (= {aacidexam_ml} mL IV per dose)."
            )
        else:
            dexa_order = "Not routinely required for Low/Minimal tier"

        # UZA High-Risk Quadruple Therapy: Olanzapine rounded DOWN to nearest 0.5 mg for age >= 2y
        if overall_tier == "High" and patient_age_years >= 2.0:
            raw_olanz = min(0.1 * patient_weight_kg, 5.0)
            rounded_down_olanz = math.floor(raw_olanz * 2.0) / 2.0
            olanzapine_order = f"Olanzapine {rounded_down_olanz:.1f} mg PO 1x/d (0.1 mg/kg = {raw_olanz:.2f} mg, rounded DOWN to nearest 0.5 mg per UZA v2; max 5 mg)"
        else:
            olanzapine_order = "Not indicated (Age <2y or non-High tier)"

        personalization_overrides = []
        if not can_swallow_tablets:
            personalization_overrides.append("Swallowing override: Switched oral tablets to IV / oral suspension formulations.")
        if prior_breakthrough_cinv:
            loraz_bt = round(0.025 * patient_weight_kg, 2)
            personalization_overrides.append(
                f"Prior CINV breakthrough escalation: Consider switching Ondansetron to Palonosetron IV, or add breakthrough Lorazepam {loraz_bt} mg (0.025-0.05 mg/kg) / Alizapride {min(round(patient_weight_kg, 1), 50.0)} mg."
            )
        if anticipatory_vomiting:
            loraz_ant = round(0.04 * patient_weight_kg, 2)
            personalization_overrides.append(
                f"Anticipatory CINV protocol: Administer Lorazepam {loraz_ant} mg (0.04-0.08 mg/kg, max 2 mg) the night before AND 1–2h prior to chemotherapy."
            )

        return {
            "policy_version": "UZA Koningin Mathilde Moeder- en kindcentrum Anti-emetica beleid CINV v2 (Juli 2026)",
            "overall_tier": overall_tier,
            "uza_drug_tiers": uza_tiers,
            "combination_elevated": combo_elevated,
            "dexamethasone_contraindicated": dexa_contraindicated,
            "dosing_schedule": {
                "ondansetron": f"Ondansetron {ondansetron_single_mg} mg ({route_pref}) {ondansetron_freq} (5 mg/m2, max 8 mg/dose)",
                "dexamethasone": dexa_order,
                "aprepitant": aprepitant_order,
                "olanzapine": olanzapine_order,
            },
            "personalization_overrides": personalization_overrides,
        }

    def generate_cinv_patient_passport(
        self,
        patient_alias: str,
        uza_evaluation: Dict[str, Any],
        ddi_alerts: List[Dict[str, Any]],
        qtc_assessment: Dict[str, Any],
    ) -> Dict[str, Any]:
        """User Story 4: Generates a single-click exportable CINV Patient Passport summary for EHR & family handover."""
        sched = uza_evaluation["dosing_schedule"]
        return {
            "passport_id": f"UZA-CINV-PASS-{patient_alias.upper().replace(' ', '-')}",
            "title": "AImesis Pediatric CINV Patient Passport (UZA v2 July 2026)",
            "emetogenicity_tier": uza_evaluation["overall_tier"],
            "dexamethasone_blocked": uza_evaluation["dexamethasone_contraindicated"],
            "active_orders": [
                sched["ondansetron"],
                sched["dexamethasone"],
                sched["aprepitant"],
                sched["olanzapine"],
            ],
            "personalization_notes": uza_evaluation["personalization_overrides"],
            "safety_gate": {
                "qtc_risk_tier": qtc_assessment["risk_tier"],
                "ddi_alert_count": len(ddi_alerts),
            },
            "belgian_family_resources": BELGIAN_CINV_PATIENT_RESOURCES[:4],
            "navigation_tip": (
                "Brussels Bilingual Redirection Note: Use direct deep-links for HUDERF, Saint-Luc, and UZ Brussel "
                "(toggling EN/FR/NL flags on hospital portals resets to the main homepage)."
            ),
        }

    def check_antimicrobial_ddi(
        self,
        proposed_antiemetics: List[str],
        concurrent_medications: List[str]
    ) -> List[Dict[str, Any]]:
        """Screens antiemetics against co-administered antimicrobials and chemo."""
        antiemetics_norm = [a.strip().lower() for a in proposed_antiemetics]
        concurrent_norm = [c.strip().lower() for c in concurrent_medications]

        alerts = []
        is_azole_present = any(az in concurrent_norm for az in ["voriconazole", "posaconazole", "itraconazole", "ketoconazole"])

        if is_azole_present:
            if "dexamethasone" in antiemetics_norm:
                alerts.append({
                    "severity": "WARNING",
                    "interaction_type": "CYP3A4 Inhibition",
                    "drugs_involved": ["Azole Antifungal (Voriconazole/Posaconazole)", "Dexamethasone"],
                    "clinical_effect": "Azole antifungals are potent CYP3A4 inhibitors and increase systemic dexamethasone exposure approximately 2-fold.",
                    "recommended_action": "Reduce oral Dexamethasone dosage by 50% when co-administered with Voriconazole or Posaconazole."
                })
            if "aprepitant" in antiemetics_norm or "fosaprepitant" in antiemetics_norm:
                alerts.append({
                    "severity": "MODERATE",
                    "interaction_type": "Competitive CYP3A4 Metabolism",
                    "drugs_involved": ["Azole Antifungal", "Aprepitant"],
                    "clinical_effect": "Aprepitant is both a substrate and moderate inhibitor of CYP3A4; concurrent azole administration increases Aprepitant AUC.",
                    "recommended_action": "Monitor for heightened neurocognitive or sedative adverse effects; no immediate empiric dose reduction required."
                })
            if "vincristine" in concurrent_norm:
                alerts.append({
                    "severity": "CRITICAL_CONTRAINDICATION",
                    "interaction_type": "CYP3A4 Neurotoxicity Exacerbation",
                    "drugs_involved": ["Voriconazole", "Vincristine"],
                    "clinical_effect": "Azoles severely impair vincristine clearance, predisposing pediatric patients to debilitating peripheral/autonomic neuropathy and paralytic ileus.",
                    "recommended_action": "Withhold Voriconazole during and for 48 hours following Vincristine administration, or switch to liposomal Amphotericin B."
                })

        return alerts

    def query_pogo_guidelines(
        self,
        emetogenicity_tier: str,
        patient_age: float
    ) -> Dict[str, Any]:
        """Returns POGO-recommended antiemetic prophylaxis regimen."""
        tier = emetogenicity_tier.strip().capitalize()
        age = float(patient_age)

        if tier == "High":
            if age >= 0.5:
                regimen = [
                    "5-HT3 antagonist (Ondansetron 0.15 mg/kg IV q8h or Granisetron 40 mcg/kg IV q24h)",
                    "Dexamethasone (dose-adjusted if CYP3A4 inhibitors present)",
                    "Aprepitant (Day 1: 3 mg/kg max 125 mg; Days 2-3: 2 mg/kg max 80 mg)"
                ]
                protocol_name = "POGO High-Emetic Risk Triple Therapy"
            else:
                regimen = [
                    "5-HT3 antagonist (Ondansetron 0.15 mg/kg IV q8h)",
                    "Dexamethasone 2 mg/m2 IV q12h"
                ]
                protocol_name = "POGO High-Emetic Risk Dual Therapy (Infant < 6 months)"
        elif tier == "Moderate":
            regimen = [
                "5-HT3 antagonist (Ondansetron 0.15 mg/kg IV q8h or Granisetron 40 mcg/kg IV q24h)",
                "Dexamethasone 2 mg/m2 IV q12h"
            ]
            protocol_name = "POGO Moderate-Emetic Risk Dual Therapy"
        elif tier == "Low":
            regimen = [
                "5-HT3 antagonist (Ondansetron 0.15 mg/kg IV q8h) OR Dexamethasone"
            ]
            protocol_name = "POGO Low-Emetic Risk Monotherapy"
        else:
            regimen = ["No routine prophylaxis required; PRN rescue antiemetic available."]
            protocol_name = "POGO Minimal-Emetic Risk Standard of Care"

        return {
            "protocol_name": protocol_name,
            "emetogenicity_tier": tier,
            "patient_age": age,
            "recommended_agents": regimen,
            "refractory_guidance": "For breakthrough/refractory CINV: Add Olanzapine (0.1 mg/kg, max 5 mg daily) or Lorazepam (0.02-0.04 mg/kg IV)."
        }

    def assess_qtc_risk(
        self,
        medications: List[str],
        baseline_qtc_ms: Optional[float] = None
    ) -> Dict[str, Any]:
        """Calculates cumulative QTc prolongation risk score."""
        meds_norm = [m.strip().lower() for m in medications]
        total_score = 0
        risk_breakdown = {}

        for med in meds_norm:
            entry = QTC_RISK_REGISTRY.get(med, {"category": "No Added Risk", "score": 0})
            total_score += entry["score"]
            if entry["score"] > 0:
                risk_breakdown[med] = entry

        if total_score >= 4 or (baseline_qtc_ms and baseline_qtc_ms >= 460.0):
            risk_tier = "HIGH"
            alert = (
                f"HIGH CUMULATIVE QTc RISK (Score: {total_score}). Combination of multiple QTc-prolonging agents. "
                "Recommend baseline and daily serial 12-lead ECG monitoring. "
                "Consider substituting Ondansetron with Granisetron or Palonosetron."
            )
        elif total_score >= 2:
            risk_tier = "MODERATE"
            alert = f"MODERATE QTc RISK (Score: {total_score}). Monitor serum electrolytes (K+ >= 4.0 mEq/L, Mg2+ >= 2.0 mg/dL)."
        else:
            risk_tier = "LOW"
            alert = "LOW QTc RISK. Standard monitoring."

        return {
            "cumulative_score": total_score,
            "risk_tier": risk_tier,
            "baseline_qtc_ms": baseline_qtc_ms,
            "risk_breakdown": risk_breakdown,
            "clinical_alert": alert
        }
