"""Minimalist clinical UI for Almesis pediatric CINV copilot (uc3-aimesis-cinv).

Built following official `developing-with-streamlit` design best practices:
- Centered single-column layout with `shadcn` minimalist theme (`.streamlit/config.toml`)
- `st.segmented_control` for visible 1-click case and language selection
- `st.badge` with Material Symbols icons (`:material/...:`) for status at a glance
- `st.container(border=True)` cards instead of heavy dividers
- Sentence casing and `title=` callouts
"""

from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace
from typing import Any

import streamlit as st
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent import (
    app as adk_app,
)
from app.agent import (
    check_ddi_interactions,
    classify_regimen_emetogenicity,
    get_pogo_guideline_recommendation,
)
from app.dosing import bsa_mosteller, compute_antiemetic_doses
from app.passport import build_parent_passport
from app.tables import ADVISORY_LABEL, PEDIATRIC_CHEMO_EMETOGENICITY

load_dotenv()

st.set_page_config(
    page_title="Almesis CINV copilot",
    page_icon=":material/medication:",
    layout="centered",
)

CASES: dict[str, dict[str, Any]] = {
    "4yo neuroblastoma (cisplatin)": {
        "age_years": 4.0,
        "weight_kg": 16.0,
        "height_cm": 102.0,
        "indication": "Solid tumor (neuroblastoma)",
        "chemo_drugs": ["cisplatin", "vincristine", "etoposide"],
        "prior_nausea": False,
        "chemo_days": 3,
    },
    "6yo leukemia / ALL (no steroids)": {
        "age_years": 6.0,
        "weight_kg": 21.0,
        "height_cm": 116.0,
        "indication": "Acute lymphoblastic leukemia (ALL)",
        "chemo_drugs": ["doxorubicin", "vincristine"],
        "prior_nausea": False,
        "chemo_days": 1,
    },
    "15yo sarcoma (5-day chemo)": {
        "age_years": 15.0,
        "weight_kg": 54.0,
        "height_cm": 168.0,
        "indication": "Solid tumor (Ewing sarcoma)",
        "chemo_drugs": ["ifosfamide", "etoposide"],
        "prior_nausea": True,
        "chemo_days": 5,
    },
}

DEFAULT_CASE = "6yo leukemia / ALL (no steroids)"
if "active_case" not in st.session_state:
    st.session_state.active_case = DEFAULT_CASE
    for k, v in CASES[DEFAULT_CASE].items():
        st.session_state[k] = v

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []


@st.cache_resource
def _get_runner() -> tuple[Runner, InMemorySessionService]:
    session_service = InMemorySessionService()
    runner = Runner(app=adk_app, session_service=session_service)
    return runner, session_service


def _ask_ai(prompt: str) -> str:
    runner, session_service = _get_runner()
    session_id = st.session_state.setdefault(
        "adk_session_id", f"st-{uuid.uuid4().hex[:8]}"
    )

    async def _run() -> str:
        existing = await session_service.get_session(
            app_name=adk_app.name, user_id="clinician", session_id=session_id
        )
        if existing is None:
            await session_service.create_session(
                app_name=adk_app.name, user_id="clinician", session_id=session_id
            )
        msg = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
        texts: list[str] = []
        async for event in runner.run_async(
            user_id="clinician", session_id=session_id, new_message=msg
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        texts.append(part.text)
        return "\n".join(texts).strip()

    return asyncio.run(_run())


# ─── HEADER ──────────────────────────────────────────────────────────────────
st.title(":material/medication: Almesis pediatric CINV copilot")
st.caption(
    f"UZA July 2026 v2 & POGO 250111 pediatric anti-nausea calculator • {ADVISORY_LABEL}"
)

# ─── SECTION 1: PATIENT PROFILE ──────────────────────────────────────────────
with st.container(border=True):
    st.subheader("1. Patient profile", icon=":material/person:")

    chosen_case = st.segmented_control(
        "Select a sample patient case",
        options=list(CASES.keys()),
        default=st.session_state.active_case,
        selection_mode="single",
    )
    if chosen_case and chosen_case != st.session_state.active_case:
        st.session_state.active_case = chosen_case
        for k, v in CASES[chosen_case].items():
            st.session_state[k] = v
        st.rerun()

    all_chemo = sorted(PEDIATRIC_CHEMO_EMETOGENICITY.keys())
    with st.expander(
        "Customize age, weight, height, or chemotherapy", icon=":material/tune:"
    ):
        c1, c2, c3 = st.columns(3)
        age_years = c1.number_input(
            "Age (years)", 0.5, 18.0, float(st.session_state.age_years), 0.5
        )
        weight_kg = c2.number_input(
            "Weight (kg)", 3.0, 100.0, float(st.session_state.weight_kg), 0.5
        )
        height_cm = c3.number_input(
            "Height (cm)", 50.0, 200.0, float(st.session_state.height_cm), 1.0
        )

        indications = [
            "Solid tumor (neuroblastoma)",
            "Acute lymphoblastic leukemia (ALL)",
            "Brain tumor (hersentumor)",
            "Solid tumor (Ewing sarcoma)",
        ]
        indication = st.selectbox(
            "Diagnosis",
            options=indications,
            index=indications.index(st.session_state.indication)
            if st.session_state.indication in indications
            else 0,
        )
        chemo_drugs = st.multiselect(
            "Chemotherapy agents",
            options=all_chemo,
            default=[d for d in st.session_state.chemo_drugs if d in all_chemo],
        )
        c4, c5 = st.columns(2, vertical_alignment="bottom")
        chemo_days = c4.number_input(
            "Chemotherapy days", 1, 10, int(st.session_state.chemo_days), 1
        )
        prior_nausea = c5.toggle(
            "Breakthrough nausea in prior cycle",
            value=bool(st.session_state.prior_nausea),
        )

    bsa = bsa_mosteller(weight_kg, height_cm)
    st.caption(
        f"**Active profile:** {age_years:g} yrs • {weight_kg:g} kg • {height_cm:g} cm "
        f"(BSA {bsa:.2f} m²) • {indication} • Chemo: {', '.join(chemo_drugs) or 'none'}"
    )

# ─── DETERMINISTIC CLINICAL PIPELINE ─────────────────────────────────────────
emet_res = classify_regimen_emetogenicity(chemo_drugs)
tier = emet_res["overall_emetogenic_tier"]
pogo_res = get_pogo_guideline_recommendation(
    emetogenic_tier=tier
    if tier in {"High", "Moderate", "Low", "Minimal"}
    else "Moderate",
    age=int(age_years),
    route="PO",
)

proposed = list(pogo_res.get("proposed_antiemetics_list") or [])
if (
    "all" in indication.lower() or "brain" in indication.lower()
) and "aprepitant" not in proposed:
    if age_years >= 0.5 and weight_kg > 6.0:
        proposed.append("aprepitant")
if prior_nausea and age_years >= 2.0 and "olanzapine" not in proposed:
    proposed.append("olanzapine")

ddi_res = check_ddi_interactions(
    primary_drugs=chemo_drugs,
    proposed_antiemetics=proposed,
)

ctx = SimpleNamespace(state={})
doses_res = compute_antiemetic_doses(
    antiemetics=proposed,
    weight_kg=weight_kg,
    height_cm=height_cm,
    route="PO",
    tool_context=ctx,  # type: ignore[arg-type]
    indication=indication,
    age_years=age_years,
)

# ─── SECTION 2: CLINICIAN DOSING PLAN ────────────────────────────────────────
with st.container(border=True):
    st.subheader("2. Clinician dosing plan (mg)", icon=":material/shield:")

    with st.container(horizontal=True):
        tier_color = (
            "red" if tier == "High" else ("orange" if tier == "Moderate" else "green")
        )
        st.badge(
            f"{tier} emetogenic risk", icon=":material/vital_signs:", color=tier_color
        )
        if doses_res["dexamethasone_contraindicated"]:
            st.badge(
                "No dexamethasone (UZA policy)",
                icon=":material/block:",
                color="red",
            )
        else:
            st.badge(
                "Dexamethasone permitted",
                icon=":material/check_circle:",
                color="green",
            )
        st.badge(f"BSA {bsa:.2f} m²", icon=":material/straighten:", color="blue")

    if doses_res["dexamethasone_contraindicated"]:
        st.error(
            "Dexamethasone is contraindicated for leukemia (ALL) and brain tumor protocols "
            "per UZA CINV v2 p.2. Automatically substituted with ondansetron + aprepitant.",
            title="Steroid safety gate triggered",
            icon=":material/block:",
        )

    for inter in ddi_res["interactions_found"]:
        if "CRITICAL" in inter["severity"] or "HIGH" in inter["severity"]:
            st.warning(
                inter["clinical_action"],
                title=f"Interaction: {inter['interacting_pair']}",
                icon=":material/warning:",
            )

    doctor_rows = [
        {
            "Medication": row["drug"].capitalize(),
            "Days": row.get("days", "each"),
            "Exact dose (mg)": f"{row.get('dose_mg')} mg",
            "Liquid equivalent (mL)": f"{row.get('volume_ml')} mL"
            if row.get("volume_ml") is not None
            else "-",
            "Guideline source": row.get("source", ""),
        }
        for row in doses_res["doses"]
        if not row.get("blocked")
    ]
    st.table(doctor_rows, alt="Clinician antiemetic dosing table in milligrams")

# ─── SECTION 3: PARENT HOME SCHEDULE ─────────────────────────────────────────
with st.container(border=True):
    st.subheader("3. Parent home schedule (mL only)", icon=":material/family_restroom:")
    st.caption(
        "Parents receive oral liquid volumes in milliliters (mL) only — never raw milligram math."
    )

    lang_labels = {"nl": "Nederlands", "fr": "Français", "en": "English"}
    selected_lang = (
        st.segmented_control(
            "Language",
            options=["nl", "fr", "en"],
            default="nl",
            format_func=lambda x: lang_labels[x],
            selection_mode="single",
        )
        or "nl"
    )

    passport = build_parent_passport(
        language=selected_lang,
        chemo_days=int(chemo_days),
        tool_context=ctx,  # type: ignore[arg-type]
    )

    parent_rows = [
        {
            "Day": f"Day {day_obj['day']}",
            "Time": entry["time"],
            "Medication": entry["drug"].capitalize(),
            "Volume to give": f"{entry['volume_ml']} mL",
        }
        for day_obj in passport["days"]
        for entry in day_obj["entries"]
    ]
    if parent_rows:
        st.table(parent_rows, alt="Parent home administration schedule in milliliters")

    for drug_name, instr in passport["instructions"].items():
        st.caption(
            f"**{drug_name.capitalize()}:** {instr['instruction']} — *{instr['rescue']}*"
        )

# ─── SECTION 4: AI CLINICAL ASSISTANT ────────────────────────────────────────
with st.container(border=True):
    st.subheader("4. Ask the clinical assistant", icon=":material/chat:")

    quick_prompt = st.pills(
        "Quick questions",
        options=[
            "Summarize this child's anti-nausea plan",
            "Why is dexamethasone blocked or adjusted?",
            "What if the child vomits after taking a dose?",
        ],
        selection_mode="single",
        label_visibility="collapsed",
    )

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_q = st.chat_input("Ask a question about this patient's CINV plan...")
    active_q = user_q or quick_prompt

    if active_q:
        contextual_prompt = (
            f"Patient context: {age_years:g}yo, {weight_kg:g} kg, {height_cm:g} cm, "
            f"diagnosis: {indication}, chemo: {', '.join(chemo_drugs)} ({chemo_days} days), "
            f"language: {selected_lang}. Question: {active_q}"
        )
        st.session_state.chat_messages.append({"role": "user", "content": active_q})
        with st.chat_message("user"):
            st.markdown(active_q)
        with st.chat_message("assistant"):
            with st.spinner("Checking guidelines and verifying doses..."):
                reply = _ask_ai(contextual_prompt)
            st.markdown(reply)
        st.session_state.chat_messages.append({"role": "assistant", "content": reply})
