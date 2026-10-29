# Almesis Copilot: build spec for coding agents

Oct 29, 2026 · @mikaeel · rev 2 (on the organizer starter)

## Start here

We build on the organizer starter in `uc3-aimesis-cinv/` (agents-cli 1.5.0, ADK, Cloud Run, A2A). We keep the organizers' architecture: **one `root_agent` (`gemini-2.5-flash`) that calls deterministic Python tools** (see `uc3-aimesis-cinv/.agents-cli-spec.md`, Option A). We do not add a multi-agent pipeline, a Streamlit app or a separate codebase. Each feature below is a new tool on the same agent, or a change to an existing one.

All paths below are relative to `uc3-aimesis-cinv/`. Run every command from there.

| Phase | What it builds | Priority |
| --- | --- | --- |
| 1 | Baseline: install, tests green, playground runs | Required |
| 2 | Verifiable clinical tables (`source` with page, `verified` flag) | Required |
| 3 | Deterministic dose tool (mg and mL) | Required |
| 4 | Guideline search with page citations | Required |
| 5 | Parent passport tool (day schedule, en/nl/fr) | Required |
| 6 | Output guardrail callback | Required |
| 7 | Instruction update and eval set (Casus 1–3 and safety cases) | Required |
| 8 | Deploy to Cloud Run | Required (human approval) |
| 9 | Protocol PDF extraction, BigQuery data products, Vertex AI Search | If time allows |

Copy this prompt to the coding agent together with this document:

```
You are extending the organizer-provided Almesis (AImesis) starter in uc3-aimesis-cinv/, a pediatric CINV decision-support ADK agent. The full spec is the document I give you. Follow it exactly.

Working rules:
1. Build one phase at a time, in order. After each phase, run its acceptance check and show me the result. Fix failures before moving on.
2. Keep the single root_agent architecture. New features are new tools in app/. Do not change the model.
3. Never let the LLM calculate a clinical number. Doses, volumes, BSA, times and risk tiers come from deterministic tools.
4. Synthetic patients only. Never invent clinical values: new table rows are placeholders with verified=False.
5. Use uv and agents-cli (agents-cli install, agents-cli playground, uv run pytest). Never pip install.
6. Never run agents-cli deploy without my explicit approval.
7. If an ADK API in this spec has changed, read the installed package source, adapt, keep the behaviour, and tell me.
```

## Rules for the coding agent

1. Phases in order; acceptance check before the next phase.
2. LLMs never calculate or retype clinical numbers. Every number comes from a tool. Tools that produce numbers also store them in `tool_context.state['facts_*']` so the guardrail (Phase 6) can check the final answer against them.
3. Synthetic patient data only.
4. Every clinical table row has `source` (document + page, e.g. `UZA CINV v2 p.3`) and `verified`. Rows with `verified=False` are placeholders. Tools refuse to use them unless `ALLOW_UNVERIFIED=1` (dev and demo only), and then return `unverified_sources` so the answer says so.
5. Never invent hospital policy, doses, concentrations, page numbers or parent instructions. Unknown page: write `p.TODO`.
6. Every recommendation ends with `ADVISORY_LABEL` from `app/agent.py` ("Advisory Only — Requires Clinician Sign-Off"). It is the single source of the disclaimer.
7. Rule priority: UZA July 2026 v2 policy first, POGO 250111 as the cross-check. See the `cinv-rules` skill.
8. Config through env vars only (`.env`, copied from `.env.example`). No secrets in the repo.
9. Region `europe-west1` for every resource. `GOOGLE_CLOUD_LOCATION=global` is the Gemini endpoint only; fix model 404s through the location, never the model name (see `GEMINI.md`).
10. `docs/` and `codelabs/` in the starter are organizer material: read-only.

## What the starter already has

- `app/agent.py`: `root_agent` with 4 tools — `classify_regimen_emetogenicity`, `check_ddi_interactions`, `get_pogo_guideline_recommendation`, `calculate_risk_adjusted_regimen` — plus in-memory tables (`PEDIATRIC_CHEMO_EMETOGENICITY`, azole/QTc/vinca sets), Casus 1–3 (`UZA_CASUS_VOORBEELDEN`) and `SYSTEM_INSTRUCTION`.
- `app/fast_api_app.py`: FastAPI server with the ADK web UI and A2A routes. The playground is our UI.
- `mocks/data_products/tools.py`: a second, richer rule set (`evaluate_uza_cinv_policy_v2`, `generate_cinv_patient_passport`, `BELGIAN_CINV_PATIENT_RESOURCES`, CredibleMeds QTc registry). Not wired to the agent.
- `mocks/fixtures/*.json`: regimens (COJEC, VIDE, VAC…), POGO guideline excerpts, openFDA labels, QTc data. `mocks/data_products/bigquery_ddl.sql`: BigQuery schema.
- `tests/unit/test_dummy.py`: real unit tests for the 4 tools and the agent wiring. `tests/integration/`: agent stream and server e2e. `tests/eval/`: template dataset (generic, to replace).
- `docs/`: UZA policy PDF, POGO PDF, casus docx, user stories, slides (read-only).

Known gap: `app/agent.py` and `mocks/data_products/tools.py` disagree on several tiers (e.g. carboplatin High vs Moderate, doxorubicin Moderate vs High, ifosfamide Moderate vs High). Neither has page citations or a `verified` flag. Phase 2 makes this visible; a clinician resolves it.

## Phase 0: human prerequisites

1. GCP project with billing. `gcloud auth login`, `gcloud auth application-default login`, `gcloud config set project PROJECT_ID`. Fill `.env` from `.env.example`.
2. `uv tool install google-agents-cli` (once per machine).
3. A clinician or pharmacist checks every row in the Phase 2 tables against `docs/Anti-emetica beleid CINV - V2.pdf` and the POGO PDF, fills the page number, and sets `verified=True`.
4. The hospital pharmacy supplies formulation data (concentration mg/mL, rounding step) for Phase 3.
5. A clinician writes the parent instruction and rescue texts (en, nl, fr) for Phase 5. The AI only formats them.

If 3–5 are not ready for the demo, run with `ALLOW_UNVERIFIED=1`; the answer then lists unverified sources and the pitch says the tables await clinician verification.

## Phase 1: baseline

```bash
agents-cli install
uv run pytest tests/unit
agents-cli playground
```

In the playground, ask Casus 2: "2-year-old, ALLTogether1 induction B day 8, vincristine + daunorubicin, PO, no prior CINV."

**Acceptance:** unit tests pass; the agent calls all 4 tools, returns MEC, omits dexamethasone, and ends with the advisory label. Note any tool-call or answer problem before changing code.

## Phase 2: verifiable clinical tables

Move the clinical tables out of `app/agent.py` into `app/tables.py` (pure data, one place for pharmacists to edit) and import them back. Add to every row:

```python
"source": "UZA CINV v2 p.TODO",   # or "POGO 250111 p.TODO"
"verified": False,
```

Add to `app/tables.py`:

```python
import os

def usable(row: dict) -> bool:
    return bool(row.get("verified")) or os.getenv("ALLOW_UNVERIFIED") == "1"
```

Change the 4 existing tools so that:

- a row that is not `usable` is treated as unknown (`needs_clinician_review: True`), not silently used;
- every result carries `sources` (list of `source` strings used) and `unverified_sources` (the subset with `verified=False`).

Combination rules (`Ifosfamide + Etoposide -> High`, `Cyclophosphamide + anthracycline -> High`, …) become rows with `source`/`verified` too.

**Acceptance:** with `ALLOW_UNVERIFIED=1`, existing unit tests pass and `classify_regimen_emetogenicity(["ifosfamide", "etoposide"])` returns High plus a non-empty `unverified_sources`. Without it, the same call returns `needs_clinician_review: True`. New test: `test_unverified_rows_blocked`.

## Phase 3: deterministic dose tool

New tool in `app/dosing.py`, added to `root_agent.tools`. The LLM passes the patient's weight and height exactly as the clinician typed them; all arithmetic happens here.

Tables in `app/tables.py` (placeholder values from the casus document and brief; all `verified=False`):

```python
DOSE_RULES = [  # basis: mg_per_m2 | mg_per_kg
    {"drug": "ondansetron", "route": "PO", "days": "each", "basis": "mg_per_m2", "per_unit": 5, "max_mg": 8, "source": "UZA CINV v2 p.TODO", "verified": False},
    {"drug": "ondansetron", "route": "IV", "days": "each", "basis": "mg_per_m2", "per_unit": 5, "max_mg": 8, "source": "UZA CINV v2 p.TODO", "verified": False},
    {"drug": "aprepitant", "route": "PO", "days": "D1", "basis": "mg_per_kg", "per_unit": 3, "max_mg": 125, "source": "UZA CINV v2 p.TODO", "verified": False},
    {"drug": "aprepitant", "route": "PO", "days": "D2-D3", "basis": "mg_per_kg", "per_unit": 2, "max_mg": 80, "source": "UZA CINV v2 p.TODO", "verified": False},
]
FORMULATIONS = [  # pharmacy supplies real values
    {"drug": "ondansetron", "route": "PO", "form": "syrup", "mg_per_ml": 0.8, "step_ml": 0.5, "source": "TODO pharmacy", "verified": False},
    {"drug": "aprepitant", "route": "PO", "form": "oral suspension", "mg_per_ml": 25, "step_ml": 0.5, "source": "TODO pharmacy", "verified": False},
]
```

Dexamethasone and olanzapine rows are added by the clinician (olanzapine rounds down to 0.5 mg per the casus text; add a `round_down_mg` field when that row exists). Dexamethasone is halved when aprepitant is co-prescribed; the tool applies that, never the LLM.

```python
import math

from google.adk.tools import ToolContext

from app.tables import DOSE_RULES, FORMULATIONS, usable


def bsa_mosteller(height_cm: float, weight_kg: float) -> float:
    return round(math.sqrt(height_cm * weight_kg / 3600), 3)


def compute_antiemetic_doses(
    antiemetics: list[str], weight_kg: float, height_cm: float, route: str, tool_context: ToolContext
) -> dict:
    """Computes antiemetic doses in mg and practical volumes in mL from verified tables.

    Args:
        antiemetics: Antiemetic names from the recommended regimen.
        weight_kg: Patient weight in kg, exactly as given by the clinician.
        height_cm: Patient height in cm, exactly as given by the clinician.
        route: "PO" or "IV".
    """
    bsa = bsa_mosteller(height_cm, weight_kg)
    out, unverified = [], set()
    for drug in [a.strip().lower() for a in antiemetics]:
        rules = [r for r in DOSE_RULES if r["drug"] == drug and r["route"] == route and usable(r)]
        if not rules:
            out.append({"drug": drug, "route": route, "dose_mg": None, "note": "no usable dose rule; clinician must dose"})
            continue
        for r in rules:
            raw = r["per_unit"] * (weight_kg if r["basis"] == "mg_per_kg" else bsa)
            dose = min(raw, r["max_mg"]) if r.get("max_mg") else raw
            item = {"drug": drug, "route": route, "days": r["days"], "dose_mg": round(dose, 1),
                    "capped": dose < raw, "source": r["source"]}
            f = next((f for f in FORMULATIONS if f["drug"] == drug and f["route"] == route and usable(f)), None)
            if f:
                vol = math.floor(dose / f["mg_per_ml"] / f["step_ml"] + 0.5) * f["step_ml"]
                item |= {"form": f["form"], "volume_ml": round(vol, 2), "actual_dose_mg": round(vol * f["mg_per_ml"], 2)}
                if not f["verified"]:
                    unverified.add(f["source"])
            if not r["verified"]:
                unverified.add(r["source"])
            out.append(item)
    res = {"bsa_m2": bsa, "doses": out, "unverified_sources": sorted(unverified)}
    tool_context.state["facts_doses"] = res
    return res
```

**Acceptance:** tests in `tests/unit/test_dosing.py` (with `ALLOW_UNVERIFIED=1`, fake `tool_context` with a dict `.state`): BSA for 24 kg / 120 cm is 0.894; ondansetron PO for 150 kg / 200 cm caps at 8.0 mg; every `volume_ml` is a multiple of `step_ml`; aprepitant gives a D1 and a D2-D3 row; Casus 2 (2 y) never contains dexamethasone.

## Phase 4: guideline search with page citations

`uv add pypdf`. New tool in `app/guidelines.py`, added to `root_agent.tools`. It searches the PDFs in `docs/` page by page (offline, no cloud needed). `Anti-emetica beleid` in the file name marks the hospital policy; everything else is external.

```python
import functools
import glob
import os
import re

from google.adk.tools import ToolContext

DOCS = os.path.join(os.path.dirname(__file__), "..", "docs", "*.pdf")


@functools.lru_cache(maxsize=1)
def _pages() -> list[tuple[str, int, str]]:
    from pypdf import PdfReader
    return [(os.path.basename(f), i, p.extract_text() or "")
            for f in glob.glob(DOCS) for i, p in enumerate(PdfReader(f).pages, start=1)]


def search_guidelines(query: str, tool_context: ToolContext) -> dict:
    """Searches the UZA CINV policy and POGO guideline PDFs. Returns passages with ids (S1, S2…), file and page number."""
    terms = [t for t in re.findall(r"[a-z0-9]+", query.lower()) if len(t) > 2]
    scored = []
    for f, n, text in _pages():
        low = text.lower()
        score = sum(low.count(t) for t in terms)
        if score:
            i = max(low.find(terms[0]), 0)
            scored.append((score, {"file": f, "page": n, "snippet": text[max(i - 150, 0): i + 450],
                                   "source_type": "hospital" if "anti-emetica" in f.lower() else "external"}))
    ev = list(tool_context.state.get("facts_evidence") or [])
    hits = [h for _, h in sorted(scored, key=lambda x: -x[0])[:5]]
    for h in hits:
        h["id"] = f"S{len(ev) + 1}"
        ev.append(h)
    tool_context.state["facts_evidence"] = ev
    return {"passages": hits}
```

The UZA policy is partly Dutch: the instruction (Phase 7) tells the agent to search with both English and Dutch terms (e.g. `dexamethasone ALL` and `GEEN dexamethasone`).

**Acceptance:** `search_guidelines("dexamethasone", ctx)` returns hits with page numbers from both PDFs, the UZA one tagged `hospital`. Test: `test_guideline_search_pages`.

## Phase 5: parent passport tool

New tool `build_parent_passport(language, chemo_days, tool_context)` in `app/passport.py`. It reads `facts_doses` from state (never doses from the LLM), plus two new tables in `app/tables.py`:

- `SCHEDULE_RULES`: per tier, drug and route — `setting` (hospital/home), `applies_to` (`each_chemo_day` / `delayed_days`), `delayed_days`, `clock_times` (list). Placeholders, `verified=False`.
- `PARENT_INSTRUCTIONS`: per drug and language (en/nl/fr) — `instruction`, `rescue`, `source`, `verified`. Text is clinician-written; missing text becomes `"Ask your care team."`.

It returns one entry per day (chemo days, then delayed days) with `time`, `drug`, `volume_ml` only — no mg — plus the instructions and `BELGIAN_CINV_PATIENT_RESOURCES` from `mocks/data_products/tools.py` filtered by language. Store in `facts_passport`. Reuse the structure of `generate_cinv_patient_passport` in the mocks.

**Acceptance:** for cisplatin days 1–5, HEC, en: days 1–7 present (5 chemo + 2 delayed), only mL volumes, every time comes from `SCHEDULE_RULES`. With `language="nl"` the instruction texts are Dutch. Test: `test_passport_days_and_ml_only`.

## Phase 6: output guardrail

An `after_model_callback` on `root_agent` (in `app/guardrail.py`) checks every final text response deterministically:

- every `<number> mg` and `<number> mL` in the text is in `facts_doses` / `facts_passport` (if those exist);
- every `[S<n>]` citation exists in `facts_evidence`;
- `ADVISORY_LABEL` is present.

On failure it replaces the response text with the original text plus a top line `Guardrail: unsupported values removed` (sentences with unsupported values deleted) and appends `ADVISORY_LABEL` if missing. Skip responses that are function calls.

```python
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse

def guard(callback_context: CallbackContext, llm_response: LlmResponse) -> LlmResponse | None:
    ...  # return None to keep the response unchanged
```

**Acceptance:** unit test with a fake context: a draft with `12 mg` not in facts gets edited; a draft with only fact values and the label passes unchanged; a draft without the label gets it appended.

## Phase 7: instruction and evals

Update `SYSTEM_INSTRUCTION` in `app/agent.py`:

1. Workflow: classify → policy/guideline recommendation → DDI check → risk adjustment → `compute_antiemetic_doses` (if weight and height are given) → `search_guidelines` (English and Dutch terms) → `build_parent_passport` (if asked).
2. Report UZA policy first, then whether POGO agrees; cite every clinical claim as `[S<n>]` with file and page.
3. Copy numbers from tool results only; if `unverified_sources` is non-empty, say so in one line.
4. Hard rules stay: no dexamethasone in ALL / brain tumours / dinutuximab beta / steroid-containing regimens; no palonosetron with ondansetron within 3 days; ends with `ADVISORY_LABEL`.

Update `tests/unit/test_dummy.py::test_root_agent_wiring` for the new tool list.

Replace `tests/eval/datasets/basic-dataset.json` with: Casus 1, 2 and 3 (from `docs/casus voorbeelden.docx` / `UZA_CASUS_VOORBEELDEN`), a voriconazole + aprepitant interaction case, an infant < 6 months case, and negative safety cases from section 5 of `codelabs/uc3-aimesis-quickstart.lab.md` (e.g. asking for dexamethasone in ALL must be refused). Run `agents-cli eval run`, iterate per `GEMINI.md`.

**Acceptance:** `uv run pytest tests/unit tests/integration` passes; `agents-cli eval run` passes on Casus 1–3 and all safety cases.

## Phase 8: deploy

Only after the user explicitly approves:

```bash
gcloud config set project PROJECT_ID
agents-cli deploy
```

Region comes from `agents-cli-manifest.yaml` (`europe-west1`). Set `ALLOW_UNVERIFIED=1` on the service only for the demo.

**Acceptance:** the Cloud Run URL serves the ADK web UI and Casus 2 gives the same answer as locally.

## Phase 9: if time allows

- **Protocol PDF extraction:** tool that sends an uploaded protocol PDF to Gemini with a Pydantic response schema and returns a draft regimen, always `verified=False`, never used for dosing.
- **BigQuery data products:** create the dataset from `mocks/data_products/bigquery_ddl.sql` (location EU) and move `app/tables.py` there behind a `DATA_BACKEND` env var.
- **Vertex AI Search:** data store in `eu` over the PDFs, behind `GUIDELINE_BACKEND=vertex`, same return shape as Phase 4.
- **Audit trail:** log each final answer and its facts to Cloud Logging (already wired by the starter's telemetry).

## Demo script (4 minutes)

1. Casus 1 (16 y, COJEC B4, cisplatin): HEC, UZA-first plan with POGO cross-check, page citations, Day 2 breakthrough handling.
2. Show the tool trace in the playground: every number comes from a tool.
3. Casus 2 (2 y, ALL): dexamethasone blocked; ask for it anyway and show the refusal.
4. Casus 3 (IE): combination escalates to HEC; aprepitant extension to days 4–5.
5. Add voriconazole: interaction alert and dose modification.
6. Parent passport in Dutch: day-by-day table, mL only.
7. Close: tables are placeholders awaiting clinician verification; every answer is advisory and needs sign-off.

## Definition of done

- [ ] `uv run pytest tests/unit tests/integration` passes.
- [ ] `agents-cli eval run` passes on Casus 1–3 and the safety cases.
- [ ] Every clinical table row has `source` with page and `verified`.
- [ ] Doses in mg and mL come only from `compute_antiemetic_doses`.
- [ ] Answers cite `[S<n>]` passages with file and page; UZA first, POGO as cross-check.
- [ ] Passport renders days in en, nl and fr with mL only.
- [ ] Guardrail removes unsupported numbers and enforces `ADVISORY_LABEL`.
- [ ] Cloud Run URL works (after approval).
- [ ] README states: synthetic data, decision support only, requires clinician sign-off.
