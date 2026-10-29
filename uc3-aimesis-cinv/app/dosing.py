"""Deterministic pediatric antiemetic dose and liquid volume calculator (Phase 3).

Grounded in UZA Koningin Mathilde Moeder- en kindcentrum Anti-emetica beleid CINV v2 (July 2026, p.2).
All arithmetic happens in Python — never in the LLM.
"""

from __future__ import annotations

import math
from typing import Any

from google.adk.tools import ToolContext

from app.tables import ADVISORY_LABEL, DOSE_RULES, FORMULATIONS, usable

DEXA_CONTRAINDICATED_KEYWORDS = (
    "all",
    "acute lymphoblastic",
    "brain",
    "hersentumor",
    "cns",
    "glioma",
    "medulloblastoma",
    "ependymoma",
    "dinutuximab",
    "aml",
    "car-t",
    "steroid",
)


def bsa_mosteller(height_cm: float, weight_kg: float) -> float:
    """Computes Body Surface Area (m²) using the Mosteller formula: sqrt(H_cm * W_kg / 3600)."""
    if height_cm <= 0 or weight_kg <= 0:
        return 0.0
    return round(math.sqrt(height_cm * weight_kg / 3600.0), 3)


def is_dexamethasone_contraindicated(indication: str = "") -> bool:
    """Returns True if dexamethasone is strictly contraindicated per UZA CINV v2 p.2 ('GEEN Dexamethasone')."""
    ind = (indication or "").strip().lower()
    if not ind:
        return False
    return any(k in ind for k in DEXA_CONTRAINDICATED_KEYWORDS)


def compute_antiemetic_doses(
    antiemetics: list[str],
    weight_kg: float,
    height_cm: float,
    route: str = "PO",
    tool_context: ToolContext | None = None,
    indication: str = "solid_tumor",
    age_years: float = 9.0,
) -> dict[str, Any]:
    """Computes antiemetic doses in mg and practical volumes in mL from verified tables.

    Args:
        antiemetics: Antiemetic names from the recommended regimen (e.g., ["ondansetron", "aprepitant"]).
        weight_kg: Patient weight in kg, exactly as given by the clinician.
        height_cm: Patient height in cm, exactly as given by the clinician.
        route: "PO" or "IV".
        tool_context: Optional ADK ToolContext to persist `facts_doses` in session state.
        indication: Clinical indication/protocol (e.g., "ALL", "brain_tumor", "neuroblastoma").
        age_years: Patient age in years (default 9.0).
    """
    norm_route = (route or "PO").strip().upper()
    if norm_route not in {"PO", "IV"}:
        norm_route = "PO"

    bsa = bsa_mosteller(height_cm, weight_kg)
    normalized_drugs = [a.strip().lower() for a in antiemetics if a and a.strip()]
    aprepitant_active = (
        any(d in {"aprepitant", "fosaprepitant"} for d in normalized_drugs)
        and age_years >= 0.5
        and weight_kg > 6.0
    )
    dexa_blocked = is_dexamethasone_contraindicated(indication)

    out: list[dict[str, Any]] = []
    sources: set[str] = set()
    unverified: set[str] = set()
    needs_review = False

    for drug in normalized_drugs:
        if drug == "fosaprepitant":
            drug_key = "aprepitant"
        else:
            drug_key = drug

        # Hard UZA v2 p.2 contraindication checks
        if drug_key == "dexamethasone" and dexa_blocked:
            sources.add("UZA CINV v2 p.2")
            out.append(
                {
                    "drug": drug,
                    "route": norm_route,
                    "days": "NONE",
                    "dose_mg": None,
                    "blocked": True,
                    "note": (
                        "CONTRAINDICATED ('GEEN DEXAMETHASONE' — UZA CINV v2 p.2): "
                        "Do not prescribe dexamethasone in ALL, brain tumors (hersentumoren), "
                        "dinutuximab beta, AML, CAR-T, or steroid-containing chemotherapy."
                    ),
                    "source": "UZA CINV v2 p.2",
                }
            )
            continue

        if drug_key == "aprepitant" and (age_years < 0.5 or weight_kg <= 6.0):
            sources.add("UZA CINV v2 p.2")
            out.append(
                {
                    "drug": drug,
                    "route": norm_route,
                    "days": "NONE",
                    "dose_mg": None,
                    "blocked": True,
                    "note": "Contraindicated in infants <6 months or <=6 kg (UZA CINV v2 p.2: geen indicatie).",
                    "source": "UZA CINV v2 p.2",
                }
            )
            continue

        if drug_key == "olanzapine" and age_years < 2.0:
            sources.add("UZA CINV v2 p.2")
            out.append(
                {
                    "drug": drug,
                    "route": norm_route,
                    "days": "NONE",
                    "dose_mg": None,
                    "blocked": True,
                    "note": "Contraindicated in children <2 years (UZA CINV v2 p.2: geen indicatie <2j).",
                    "source": "UZA CINV v2 p.2",
                }
            )
            continue

        rules = [
            r
            for r in DOSE_RULES
            if r["drug"] == drug_key and r["route"] == norm_route and usable(r)
        ]
        if not rules:
            needs_review = True
            out.append(
                {
                    "drug": drug,
                    "route": norm_route,
                    "dose_mg": None,
                    "note": "no usable dose rule; clinician must dose",
                }
            )
            continue

        for r in rules:
            sources.add(r["source"])
            if not r.get("verified"):
                unverified.add(r["source"])

            if r["basis"] == "uza_bsa_split":
                base_mg = r["low_bsa_mg"] if bsa < r["bsa_threshold"] else r["high_bsa_mg"]
                raw = base_mg * (r["cyp3a4_factor"] if aprepitant_active else 1.0)
                dose = raw
                capped = False
            elif r["basis"] == "mg_per_kg":
                raw = r["per_unit"] * weight_kg
                dose = min(raw, r["max_mg"]) if r.get("max_mg") else raw
                capped = bool(r.get("max_mg") and raw > r["max_mg"])
            else:
                raw = r["per_unit"] * bsa
                dose = min(raw, r["max_mg"]) if r.get("max_mg") else raw
                capped = bool(r.get("max_mg") and raw > r["max_mg"])

            if r.get("round_down_mg"):
                step_mg = float(r["round_down_mg"])
                dose = math.floor((dose + 1e-9) / step_mg) * step_mg

            item: dict[str, Any] = {
                "drug": drug,
                "route": norm_route,
                "days": r["days"],
                "dose_mg": round(dose, 2) if r.get("round_down_mg") else round(dose, 1),
                "capped": capped,
                "source": r["source"],
            }

            if drug_key == "dexamethasone" and norm_route == "IV":
                item["aacidexam_note"] = (
                    "UZA Aacidexam® IV Alert: 5 mg/mL ampoule = ±4 mg/mL active dexamethasone base."
                )

            f = next(
                (
                    f_row
                    for f_row in FORMULATIONS
                    if f_row["drug"] == drug_key
                    and f_row["route"] == norm_route
                    and usable(f_row)
                ),
                None,
            )
            if f:
                sources.add(f["source"])
                if not f.get("verified"):
                    unverified.add(f["source"])
                step_ml = float(f["step_ml"])
                vol = math.floor(dose / float(f["mg_per_ml"]) / step_ml + 0.5) * step_ml
                item |= {
                    "form": f["form"],
                    "volume_ml": round(vol, 2),
                    "actual_dose_mg": round(vol * float(f["mg_per_ml"]), 2),
                    "step_ml": step_ml,
                }

            out.append(item)

    res: dict[str, Any] = {
        "bsa_m2": bsa,
        "weight_kg": weight_kg,
        "height_cm": height_cm,
        "route": norm_route,
        "indication": indication,
        "dexamethasone_contraindicated": dexa_blocked,
        "doses": out,
        "sources": sorted(sources),
        "unverified_sources": sorted(unverified),
        "needs_clinician_review": needs_review,
        "advisory_status": ADVISORY_LABEL,
    }
    if tool_context is not None and hasattr(tool_context, "state"):
        tool_context.state["facts_doses"] = res
    return res
