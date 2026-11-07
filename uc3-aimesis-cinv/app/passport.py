"""Multilingual CINV Parent Passport & Companion App Schedule Builder (Phase 5).

Reads deterministic dose volumes from `tool_context.state['facts_doses']`,
applies `SCHEDULE_RULES` and `PARENT_INSTRUCTIONS` (en / nl / fr), and generates
a day-by-day administration schedule using ONLY liquid volumes (`volume_ml`) — never `mg` —
alongside Belgian CINV family resources and Companion App nausea diary metadata.
"""

from __future__ import annotations

from typing import Any

from google.adk.tools import ToolContext

from app.tables import (
    ADVISORY_LABEL,
    BELGIAN_CINV_PATIENT_RESOURCES,
    PARENT_INSTRUCTIONS,
    SCHEDULE_RULES,
    usable,
)


def build_parent_passport(
    language: str = "en",
    chemo_days: int = 5,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """Builds a parent-facing day-by-day antiemetic passport in mL (en, nl, or fr).

    Args:
        language: Language code ("en", "nl", or "fr").
        chemo_days: Number of chemotherapy administration days (e.g. 5 for 5-day cisplatin/IE).
        tool_context: Optional ADK ToolContext containing `facts_doses` in state.
    """
    lang = (language or "en").strip().lower()[:2]
    if lang not in {"en", "nl", "fr"}:
        lang = "en"

    n_chemo = max(int(chemo_days or 1), 1)
    facts_doses: dict[str, Any] = {}
    if tool_context is not None and hasattr(tool_context, "state"):
        facts_doses = dict(tool_context.state.get("facts_doses") or {})

    dose_rows: list[dict[str, Any]] = list(facts_doses.get("doses") or [])
    if not dose_rows:
        # Default fallback if called before compute_antiemetic_doses
        dose_rows = [
            {"drug": "ondansetron", "days": "each", "volume_ml": 5.5, "blocked": False},
            {"drug": "aprepitant", "days": "D1", "volume_ml": 3.0, "blocked": False},
            {"drug": "aprepitant", "days": "D2-D3", "volume_ml": 2.0, "blocked": False},
        ]

    # Index usable schedule rules by drug
    sched_by_drug: dict[str, dict[str, Any]] = {}
    sources: set[str] = set()
    unverified: set[str] = set()
    for s_row in SCHEDULE_RULES:
        if usable(s_row):
            sched_by_drug[s_row["drug"]] = s_row
            sources.add(s_row["source"])
            if not s_row.get("verified"):
                unverified.add(s_row["source"])

    # Determine active drugs and their volumes (mL only)
    active_drugs: list[str] = []
    vol_by_drug_day: dict[tuple[str, str], float] = {}
    for row in dose_rows:
        if row.get("blocked") or row.get("volume_ml") is None:
            continue
        drug = str(row["drug"]).strip().lower()
        if drug not in active_drugs:
            active_drugs.append(drug)
        day_tag = str(row.get("days", "each"))
        vol_by_drug_day[(drug, day_tag)] = float(row["volume_ml"])

    max_delayed = max(
        (
            int(sched_by_drug[d].get("delayed_days", 0))
            for d in active_drugs
            if d in sched_by_drug
        ),
        default=2,
    )
    if max_delayed < 2:
        max_delayed = 2

    total_days = n_chemo + max_delayed
    days_schedule: list[dict[str, Any]] = []

    for day_num in range(1, total_days + 1):
        phase = "chemo_day" if day_num <= n_chemo else "delayed_day"
        setting = "hospital" if day_num <= n_chemo else "home"
        entries: list[dict[str, Any]] = []

        for drug in active_drugs:
            rule = sched_by_drug.get(drug)
            if not rule:
                continue
            applies = rule.get("applies_to", "chemo_and_delayed")
            if applies == "chemo_days_only" and day_num > n_chemo:
                continue
            if applies == "first_3_days" and day_num > 3:
                continue
            if applies == "chemo_and_delayed" and day_num > n_chemo + int(
                rule.get("delayed_days", 2)
            ):
                continue

            # Resolve day-specific volume_ml (e.g., aprepitant D1 vs D2-D3)
            if drug == "aprepitant":
                vol = (
                    vol_by_drug_day.get(("aprepitant", "D1"))
                    if day_num == 1
                    else vol_by_drug_day.get(("aprepitant", "D2-D3"))
                )
                if vol is None:
                    vol = vol_by_drug_day.get(("aprepitant", "each"))
            else:
                vol = vol_by_drug_day.get((drug, "each"))
                if vol is None:
                    # Fallback to any available volume for this drug
                    vol = next(
                        (v for (d_k, _), v in vol_by_drug_day.items() if d_k == drug),
                        None,
                    )

            if vol is None:
                continue

            for clock_time in rule.get("clock_times", ["08:00"]):
                entries.append(
                    {
                        "time": clock_time,
                        "drug": drug,
                        "volume_ml": round(float(vol), 2),
                    }
                )

        entries.sort(key=lambda x: x["time"])
        days_schedule.append(
            {
                "day": day_num,
                "phase": phase,
                "setting": setting,
                "entries": entries,
            }
        )

    lang_table = PARENT_INSTRUCTIONS.get(lang, {})
    instructions_out: dict[str, dict[str, str]] = {}
    for drug in active_drugs:
        info = lang_table.get(drug)
        if info and usable(info):
            sources.add(info["source"])
            if not info.get("verified"):
                unverified.add(info["source"])
            instructions_out[drug] = {
                "instruction": info.get("instruction", "Ask your care team."),
                "rescue": info.get("rescue", "Ask your care team."),
            }
        else:
            instructions_out[drug] = {
                "instruction": "Ask your care team.",
                "rescue": "Ask your care team.",
            }

    resources = [
        r
        for r in BELGIAN_CINV_PATIENT_RESOURCES
        if lang.upper() in str(r.get("lang", "")).upper()
    ] or list(BELGIAN_CINV_PATIENT_RESOURCES[:4])

    passport = {
        "language": lang,
        "chemo_days": n_chemo,
        "delayed_days": max_delayed,
        "total_days": total_days,
        "days": days_schedule,
        "instructions": instructions_out,
        "belgian_family_resources": resources,
        "companion_app_diary": {
            "enabled": True,
            "scales": [
                "Baxter Retching Faces (BARF 0-10)",
                "PeNAT Pediatric Nausea Assessment Tool",
            ],
            "red_flag_escalation": "Triggers oncology ward alert if >=3 emetic episodes in 24h or inability to keep fluids down >12h.",
        },
        "sources": sorted(sources),
        "unverified_sources": sorted(unverified),
        "advisory_status": ADVISORY_LABEL,
    }
    if tool_context is not None and hasattr(tool_context, "state"):
        tool_context.state["facts_passport"] = passport
    return passport


def _pdf_safe(text: str) -> str:
    """Normalizes Unicode punctuation to Latin-1 for standard PDF Helvetica fonts."""
    replacements = {
        "\u2014": "-",
        "\u2013": "-",
        "\u2022": "*",
        "\u2265": ">=",
        "\u2264": "<=",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2192": "->",
    }
    out = str(text)
    for k, v in replacements.items():
        out = out.replace(k, v)
    return out.encode("latin-1", errors="replace").decode("latin-1")


def build_passport_pdf_bytes(
    passport: dict[str, Any],
    patient_summary: str = "",
) -> bytes:
    """Generates a printable A4 Parent Passport PDF in mL only (NL / FR / EN)."""
    from fpdf import FPDF

    lang = str(passport.get("language", "nl")).lower()
    titles = {
        "nl": "UZA Kinderoncologie - Anti-misselijkheid Paspoort voor Ouders (mL)",
        "fr": "Oncologie Pediatrique UZA - Passeport Anti-Nausee Parents (mL)",
        "en": "UZA Pediatric Oncology - Parent Anti-Nausea Passport (mL)",
    }
    slot_labels = {
        "nl": {"morning": "[OCHTEND]", "noon": "[MIDDAG]", "evening": "[AVOND]"},
        "fr": {"morning": "[MATIN]", "noon": "[MIDI]", "evening": "[SOIR]"},
        "en": {"morning": "[MORNING]", "noon": "[NOON]", "evening": "[EVENING]"},
    }.get(lang, {"morning": "[MORNING]", "noon": "[NOON]", "evening": "[EVENING]"})

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()

    # Header banner
    pdf.set_fill_color(24, 24, 27)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(
        0,
        11,
        _pdf_safe(titles.get(lang, titles["en"])),
        new_x="LMARGIN",
        new_y="NEXT",
        fill=True,
        align="C",
    )
    pdf.ln(3)

    pdf.set_text_color(30, 30, 35)
    if patient_summary:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, _pdf_safe(patient_summary), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    # Schedule Table Header
    pdf.set_fill_color(235, 238, 245)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(28, 8, "Day", border=1, fill=True)
    pdf.cell(42, 8, "Period", border=1, fill=True)
    pdf.cell(25, 8, "Time", border=1, fill=True)
    pdf.cell(55, 8, "Medication", border=1, fill=True)
    pdf.cell(35, 8, "Volume (mL)", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 10)
    for day_obj in passport.get("days", []):
        day_label = f"Day {day_obj['day']} ({day_obj['setting']})"
        for entry in day_obj.get("entries", []):
            hr = (
                int(str(entry["time"]).split(":")[0])
                if ":" in str(entry["time"])
                else 8
            )
            slot_key = "morning" if hr < 12 else ("noon" if hr < 18 else "evening")
            period_str = f"{slot_labels.get(slot_key, '[MORNING]')}"
            pdf.cell(28, 7, _pdf_safe(day_label), border=1)
            pdf.cell(42, 7, _pdf_safe(period_str), border=1)
            pdf.cell(25, 7, _pdf_safe(str(entry["time"])), border=1)
            pdf.cell(55, 7, _pdf_safe(str(entry["drug"]).capitalize()), border=1)
            pdf.cell(
                35,
                7,
                _pdf_safe(f"{entry['volume_ml']} mL"),
                border=1,
                new_x="LMARGIN",
                new_y="NEXT",
            )

    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(
        0,
        7,
        _pdf_safe("Instructions & Vomiting Rescue Rules:"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font("Helvetica", "", 9)
    for drug_name, instr in passport.get("instructions", {}).items():
        line = f"* {drug_name.capitalize()}: {instr.get('instruction', '')} | Rescue: {instr.get('rescue', '')}"
        pdf.multi_cell(0, 5, _pdf_safe(line), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(100, 100, 110)
    pdf.cell(
        0,
        6,
        _pdf_safe(f"Safety Notice: {ADVISORY_LABEL}"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    return bytes(pdf.output())
