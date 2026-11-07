"""Interactive dark-mode clinical UI for Almesis pediatric CINV copilot (uc3-aimesis-cinv).

Features:
1. Top-right live language selector (NL / FR / EN) that translates the UI & parent passport.
2. Interactive patient profile card (presets + live weight, height, diagnosis, chemo & nausea controls).
3. Clinician dosing card (mg) with UZA v2 / POGO risk badges and steroid safety gate.
4. Interactive Daily Parent Passport (mL only) with:
   - Day selector (Day 1, Day 2, Day 3...)
   - Visual Morning (☀️), Noon (🌤️), and Evening (🌙) medication cards with interactive checkoffs
   - 1-click downloadable PDF Parent Passport (`build_passport_pdf_bytes`)
5. AI clinical assistant with quick-question pills.
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
from app.passport import build_parent_passport, build_passport_pdf_bytes
from app.tables import ADVISORY_LABEL, PEDIATRIC_CHEMO_EMETOGENICITY

load_dotenv()

st.set_page_config(
    page_title="Almesis CINV copilot",
    page_icon=":material/medication:",
    layout="centered",
)

I18N: dict[str, dict[str, str]] = {
    "nl": {
        "subtitle": "UZA juli 2026 v2 & POGO 250111 pediatrische anti-emetica calculator",
        "sec1": "1. Patiëntprofiel & chemotherapie",
        "preset_label": "Kies een klinische casus",
        "age": "Leeftijd (jaren)",
        "weight": "Gewicht (kg)",
        "height": "Lengte (cm)",
        "diagnosis": "Diagnose / indicatie",
        "chemo": "Chemotherapie middelen",
        "chemo_days": "Chemo dagen",
        "prior_nausea": "Doorbraakmisselijkheid in vorige cyclus (+ olanzapine)",
        "sec2": "2. Artsenoverzicht — exacte dosering (mg)",
        "risk_badge": "emetogeen risico",
        "no_dex": "Geen dexamethasone (UZA beleid)",
        "dex_ok": "Dexamethasone toegestaan",
        "dex_alert_title": "Steroïd veiligheidsregel actief (GEEN dexamethasone)",
        "dex_alert_body": "Dexamethasone is gecontra-indiceerd bij ALL en hersentumoren volgens UZA CINV v2 p.2. Automatisch vervangen door ondansetron + aprepitant.",
        "sec3": "3. Dagelijks ouderpaspoort (enkel mL)",
        "passport_caption": "Selecteer een dag om de ochtend-, middag- en avondmedicatie in milliliter (mL) te bekijken of download de PDF.",
        "download_pdf": "Download ouderpaspoort als PDF (mL)",
        "select_day": "Selecteer dag",
        "hospital": "Ziekenhuis (chemo)",
        "home": "Thuis (vertraagde fase)",
        "morning": "☀️ Ochtend",
        "Morning_sub": "06:00 - 11:59",
        "noon": "🌤️ Middag",
        "Noon_sub": "12:00 - 17:59",
        "evening": "🌙 Avond / Nacht",
        "Evening_sub": "18:00 - 23:59",
        "no_med": "Geen medicatie op dit moment",
        "instructions_title": "Instructies & bij braken",
        "sec4": "4. Vraag de klinische AI-assistent",
        "chat_placeholder": "Stel een vraag over dit anti-misselijkheidsplan...",
        "q1": "Vat dit plan samen voor het EPD",
        "q2": "Waarom is dexamethasone geblokkeerd of aangepast?",
        "q3": "Wat als het kind braakt na inname?",
    },
    "fr": {
        "subtitle": "Calculateur anti-émétique pédiatrique UZA juillet 2026 v2 & POGO 250111",
        "sec1": "1. Profil du patient & chimiothérapie",
        "preset_label": "Choisir un cas clinique",
        "age": "Âge (ans)",
        "weight": "Poids (kg)",
        "height": "Taille (cm)",
        "diagnosis": "Diagnostic / indication",
        "chemo": "Agents de chimiothérapie",
        "chemo_days": "Jours de chimio",
        "prior_nausea": "Nausées sévères au cycle précédent (+ olanzapine)",
        "sec2": "2. Vue médecin — doses exactes (mg)",
        "risk_badge": "risque émétogène",
        "no_dex": "Pas de dexaméthasone (protocole UZA)",
        "dex_ok": "Dexaméthasone autorisée",
        "dex_alert_title": "Règle de sécurité stéroïde active (PAS de dexaméthasone)",
        "dex_alert_body": "La dexaméthasone est contre-indiquée pour les protocoles LAL (ALL) et tumeurs cérébrales (UZA CINV v2 p.2). Remplacée par ondansétron + aprépitant.",
        "sec3": "3. Passeport parents journalier (mL uniquement)",
        "passport_caption": "Sélectionnez un jour pour voir les prises du matin, midi et soir en millilitres (mL) ou téléchargez le PDF.",
        "download_pdf": "Télécharger le passeport parents en PDF (mL)",
        "select_day": "Sélectionner le jour",
        "hospital": "Hôpital (chimio)",
        "home": "Maison (phase retardée)",
        "morning": "☀️ Matin",
        "Morning_sub": "06:00 - 11:59",
        "noon": "🌤️ Midi / Après-midi",
        "Noon_sub": "12:00 - 17:59",
        "evening": "🌙 Soir / Coucher",
        "Evening_sub": "18:00 - 23:59",
        "no_med": "Aucun médicament à ce moment",
        "instructions_title": "Instructions & en cas de vomissement",
        "sec4": "4. Poser une question à l'assistant IA",
        "chat_placeholder": "Posez une question sur ce plan anti-nausée...",
        "q1": "Résumer ce plan clinique",
        "q2": "Pourquoi la dexaméthasone est-elle bloquée ?",
        "q3": "Que faire si l'enfant vomit après une dose ?",
    },
    "en": {
        "subtitle": "UZA July 2026 v2 & POGO 250111 pediatric anti-nausea calculator",
        "sec1": "1. Patient profile & chemotherapy",
        "preset_label": "Select a sample clinical case",
        "age": "Age (years)",
        "weight": "Weight (kg)",
        "height": "Height (cm)",
        "diagnosis": "Diagnosis / indication",
        "chemo": "Chemotherapy agents",
        "chemo_days": "Chemo days",
        "prior_nausea": "Breakthrough nausea in prior cycle (+ olanzapine)",
        "sec2": "2. Clinician dosing plan (mg)",
        "risk_badge": "emetogenic risk",
        "no_dex": "No dexamethasone (UZA policy)",
        "dex_ok": "Dexamethasone permitted",
        "dex_alert_title": "Steroid safety gate triggered (NO dexamethasone)",
        "dex_alert_body": "Dexamethasone is contraindicated for leukemia (ALL) and brain tumor protocols per UZA CINV v2 p.2. Automatically substituted with ondansetron + aprepitant.",
        "sec3": "3. Daily parent passport (mL only)",
        "passport_caption": "Select any day to view Morning, Noon, and Evening liquid volumes (mL) or download the printable PDF.",
        "download_pdf": "Download parent passport PDF (mL)",
        "select_day": "Select day",
        "hospital": "Hospital (chemo)",
        "home": "Home (delayed phase)",
        "morning": "☀️ Morning",
        "Morning_sub": "06:00 - 11:59",
        "noon": "🌤️ Noon",
        "Noon_sub": "12:00 - 17:59",
        "evening": "🌙 Evening",
        "Evening_sub": "18:00 - 23:59",
        "no_med": "No scheduled medication",
        "instructions_title": "Instructions & vomiting rescue rules",
        "sec4": "4. Ask the clinical AI assistant",
        "chat_placeholder": "Ask a question about this patient's CINV plan...",
        "q1": "Summarize this child's anti-nausea plan",
        "q2": "Why is dexamethasone blocked or adjusted?",
        "q3": "What if the child vomits after taking a dose?",
    },
}

CASES: dict[str, dict[str, Any]] = {
    "Case 1: 4yo neuroblastoma": {
        "age_years": 4.0,
        "weight_kg": 16.0,
        "height_cm": 102.0,
        "indication": "Solid tumor (neuroblastoma)",
        "chemo_drugs": ["cisplatin", "vincristine", "etoposide"],
        "prior_nausea": False,
        "chemo_days": 3,
    },
    "Case 2: 6yo leukemia (ALL)": {
        "age_years": 6.0,
        "weight_kg": 21.0,
        "height_cm": 116.0,
        "indication": "Acute lymphoblastic leukemia (ALL)",
        "chemo_drugs": ["doxorubicin", "vincristine"],
        "prior_nausea": False,
        "chemo_days": 1,
    },
    "Case 3: 15yo sarcoma (5-day)": {
        "age_years": 15.0,
        "weight_kg": 54.0,
        "height_cm": 168.0,
        "indication": "Solid tumor (Ewing sarcoma)",
        "chemo_drugs": ["ifosfamide", "etoposide"],
        "prior_nausea": True,
        "chemo_days": 5,
    },
}

DEFAULT_CASE = "Case 2: 6yo leukemia (ALL)"
if "active_case" not in st.session_state:
    st.session_state.active_case = DEFAULT_CASE
    for k, v in CASES[DEFAULT_CASE].items():
        st.session_state[k] = v

if "ui_lang" not in st.session_state:
    st.session_state.ui_lang = "nl"

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


# ─── TOP HEADER + TOP-RIGHT LANGUAGE SELECTOR ────────────────────────────────
hdr_left, hdr_right = st.columns([3.0, 1.3], vertical_alignment="center")
with hdr_right:
    lang_choice = st.segmented_control(
        "Language",
        options=["nl", "fr", "en"],
        default=st.session_state.ui_lang,
        format_func=lambda x: {"nl": "🇳🇱 NL", "fr": "🇫🇷 FR", "en": "🇬🇧 EN"}[x],
        selection_mode="single",
        label_visibility="collapsed",
    )
    if lang_choice and lang_choice != st.session_state.ui_lang:
        st.session_state.ui_lang = lang_choice
        st.rerun()

selected_lang = st.session_state.ui_lang
t = I18N[selected_lang]

with hdr_left:
    st.title(":material/medication: Almesis CINV copilot")
    st.caption(f"{t['subtitle']} • {ADVISORY_LABEL}")

# ─── SECTION 1: INTERACTIVE PATIENT PROFILE ──────────────────────────────────
with st.container(border=True):
    st.subheader(t["sec1"], icon=":material/person:")

    chosen_case = st.segmented_control(
        t["preset_label"],
        options=list(CASES.keys()),
        default=st.session_state.active_case,
        selection_mode="single",
    )
    if chosen_case and chosen_case != st.session_state.active_case:
        st.session_state.active_case = chosen_case
        for k, v in CASES[chosen_case].items():
            st.session_state[k] = v
        st.rerun()

    c1, c2, c3, c4 = st.columns(4)
    age_years = c1.number_input(
        t["age"], 0.5, 18.0, float(st.session_state.age_years), 0.5
    )
    weight_kg = c2.number_input(
        t["weight"], 3.0, 100.0, float(st.session_state.weight_kg), 0.5
    )
    height_cm = c3.number_input(
        t["height"], 50.0, 200.0, float(st.session_state.height_cm), 1.0
    )
    chemo_days = c4.number_input(
        t["chemo_days"], 1, 10, int(st.session_state.chemo_days), 1
    )

    indications = [
        "Solid tumor (neuroblastoma)",
        "Acute lymphoblastic leukemia (ALL)",
        "Brain tumor (hersentumor)",
        "Solid tumor (Ewing sarcoma)",
    ]
    all_chemo = sorted(PEDIATRIC_CHEMO_EMETOGENICITY.keys())

    col_diag, col_chemo = st.columns([1.1, 1.4])
    indication = col_diag.selectbox(
        t["diagnosis"],
        options=indications,
        index=indications.index(st.session_state.indication)
        if st.session_state.indication in indications
        else 0,
    )
    chemo_drugs = col_chemo.multiselect(
        t["chemo"],
        options=all_chemo,
        default=[d for d in st.session_state.chemo_drugs if d in all_chemo],
    )
    prior_nausea = st.toggle(
        t["prior_nausea"],
        value=bool(st.session_state.prior_nausea),
    )

    bsa = bsa_mosteller(weight_kg, height_cm)

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

# ─── SECTION 2: CLINICIAN DOSING PLAN (MG) ───────────────────────────────────
with st.container(border=True):
    st.subheader(t["sec2"], icon=":material/shield:")

    with st.container(horizontal=True):
        tier_color = (
            "red" if tier == "High" else ("orange" if tier == "Moderate" else "green")
        )
        st.badge(
            f"{tier} {t['risk_badge']}",
            icon=":material/vital_signs:",
            color=tier_color,
        )
        if doses_res["dexamethasone_contraindicated"]:
            st.badge(
                t["no_dex"],
                icon=":material/block:",
                color="red",
            )
        else:
            st.badge(
                t["dex_ok"],
                icon=":material/check_circle:",
                color="green",
            )
        st.badge(f"BSA {bsa:.2f} m²", icon=":material/straighten:", color="blue")

    if doses_res["dexamethasone_contraindicated"]:
        st.error(
            t["dex_alert_body"],
            title=t["dex_alert_title"],
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
            "Dose (mg)": f"{row.get('dose_mg')} mg",
            "Liquid (mL)": f"{row.get('volume_ml')} mL"
            if row.get("volume_ml") is not None
            else "-",
            "Source": row.get("source", ""),
        }
        for row in doses_res["doses"]
        if not row.get("blocked")
    ]
    st.dataframe(doctor_rows, hide_index=True, alt="Clinician dosing table in mg")

# ─── SECTION 3: DAILY PARENT PASSPORT (ML + MORNING/NOON/EVENING + PDF) ──────
with st.container(border=True):
    passport = build_parent_passport(
        language=selected_lang,
        chemo_days=int(chemo_days),
        tool_context=ctx,  # type: ignore[arg-type]
    )

    patient_summary_str = (
        f"Patient: {age_years:g} yrs, {weight_kg:g} kg, {height_cm:g} cm "
        f"(BSA {bsa:.2f} m2) | {indication} | Chemo: {', '.join(chemo_drugs)} ({chemo_days}d)"
    )
    pdf_bytes = build_passport_pdf_bytes(passport, patient_summary=patient_summary_str)

    p_hdr_left, p_hdr_right = st.columns([2.2, 1.3], vertical_alignment="center")
    with p_hdr_left:
        st.subheader(t["sec3"], icon=":material/family_restroom:")
    with p_hdr_right:
        st.download_button(
            label=t["download_pdf"],
            data=pdf_bytes,
            file_name=f"UZA_CINV_Passport_{selected_lang.upper()}_{int(weight_kg)}kg.pdf",
            mime="application/pdf",
            icon=":material/picture_as_pdf:",
            type="primary",
            width="stretch",
        )

    st.caption(t["passport_caption"])

    days_list = passport["days"]
    day_options = [d["day"] for d in days_list]
    selected_day_num = (
        st.segmented_control(
            t["select_day"],
            options=day_options,
            default=day_options[0] if day_options else 1,
            format_func=lambda d_num: (
                f"Day {d_num} ({'🏥' if d_num <= int(chemo_days) else '🏡'})"
            ),
            selection_mode="single",
        )
        or 1
    )

    active_day_obj = next(
        (d for d in days_list if d["day"] == selected_day_num),
        days_list[0],
    )
    setting_badge_text = (
        t["hospital"] if active_day_obj["setting"] == "hospital" else t["home"]
    )
    st.badge(
        f"Day {selected_day_num} — {setting_badge_text}",
        icon=":material/calendar_today:",
        color="violet" if active_day_obj["setting"] == "hospital" else "green",
    )

    # Group entries for the selected day into Morning / Noon / Evening visual slots
    slot_entries: dict[str, list[dict[str, Any]]] = {
        "morning": [],
        "noon": [],
        "evening": [],
    }
    for entry in active_day_obj["entries"]:
        slot_key = entry.get("slot")
        if not slot_key:
            hr = int(str(entry["time"]).split(":")[0])
            slot_key = "morning" if hr < 12 else ("noon" if hr < 18 else "evening")
        slot_entries[slot_key].append(entry)

    col_morn, col_noon, col_eve = st.columns(3)

    slot_configs = [
        (col_morn, "morning", t["morning"], t["Morning_sub"], "orange"),
        (col_noon, "noon", t["noon"], t["Noon_sub"], "blue"),
        (col_eve, "evening", t["evening"], t["Evening_sub"], "violet"),
    ]

    for col_widget, slot_key, slot_title, slot_hours, badge_col in slot_configs:
        with col_widget:
            with st.container(border=True):
                st.markdown(f"**{slot_title}**")
                st.caption(slot_hours)
                items = slot_entries[slot_key]
                if items:
                    for idx, item in enumerate(items):
                        drug_cap = item["drug"].capitalize()
                        vol_str = f"{item['volume_ml']} mL"
                        st.markdown(
                            f":material/schedule: **{item['time']}** — **{drug_cap}**\n\n"
                            f":{badge_col}-badge[{vol_str}]"
                        )
                        st.checkbox(
                            f"{drug_cap} ({vol_str})",
                            key=f"chk_d{selected_day_num}_{slot_key}_{idx}_{item['drug']}",
                        )
                else:
                    st.caption(f"*{t['no_med']}*")

    with st.expander(t["instructions_title"], icon=":material/info:"):
        for drug_name, instr in passport["instructions"].items():
            st.markdown(
                f"- **{drug_name.capitalize()}:** {instr['instruction']}\n"
                f"  - *{instr['rescue']}*"
            )

# ─── SECTION 4: AI CLINICAL ASSISTANT ────────────────────────────────────────
with st.container(border=True):
    st.subheader(t["sec4"], icon=":material/chat:")

    quick_prompt = st.pills(
        "Quick questions",
        options=[t["q1"], t["q2"], t["q3"]],
        selection_mode="single",
        label_visibility="collapsed",
    )

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_q = st.chat_input(t["chat_placeholder"])
    active_q = user_q or quick_prompt

    if active_q:
        contextual_prompt = (
            f"Patient context: {age_years:g}yo, {weight_kg:g} kg, {height_cm:g} cm, "
            f"diagnosis: {indication}, chemo: {', '.join(chemo_drugs)} ({chemo_days} days), "
            f"language: {selected_lang}. Respond in language '{selected_lang}'. Question: {active_q}"
        )
        st.session_state.chat_messages.append({"role": "user", "content": active_q})
        with st.chat_message("user"):
            st.markdown(active_q)
        with st.chat_message("assistant"):
            with st.spinner("..."):
                reply = _ask_ai(contextual_prompt)
            st.markdown(reply)
        st.session_state.chat_messages.append({"role": "assistant", "content": reply})
