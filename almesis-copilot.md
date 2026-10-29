# Almesis Copilot (AImesis — UC3 Pediatric CINV Control)

A guide to the whole project: what it is, how it works, how it resolves every task in `codelabs/uc3-aimesis-quickstart.lab.md`, and how to pitch it at **Solve with Google: BSPHO 2026 (Wintercircus Ghent)**.

- **Clinical Leads:** Katleen Balliauw & Anthe De Pauw (Hospital Pharmacists, UZA — Koningin Mathilde Moeder- en kindcentrum)
- **Google Cloud CE POC:** Payam Ebrahimi (`@payame`)
- **Starter & App Path:** `uc3-aimesis-cinv/`

---

## The idea in one sentence

A clinician types in a child's chemotherapy (with doses in `mg/m²`), diagnosis, age, weight, height, and concomitant medicines, and **Almesis Copilot** answers in seconds: the exact **UZA July 2026 v2** & **POGO 250111** emetogenic risk tier (including dose thresholds and multi-agent combination escalations), the safe weight/BSA-adjusted antiemetic regimen (enforcing **"GEEN Dexamethasone"** hard blocks, **Olanzapine `0.5 mg` floor rounding**, and **IV `Aacidexam® 5 mg/mL = ±4 mg/mL` active base** conversion), **CYP3A4 & cumulative QTc** interaction alerts, page-cited guideline comparisons, and a multilingual (**NL / FR / EN**) **CINV Patient Passport + Companion App** schedule for parents.

---

## The clinical problem it solves

Chemotherapy-Induced Nausea and Vomiting (**CINV**) is one of the most distressing treatment toxicities for children with cancer. Preventing it safely requires cross-checking multiple sources under time pressure:

1. **Dose-dependent & combination emetogenicity (Story 1):** A single drug's risk changes with dose (`Cyclophosphamide > 1500 mg/m²` is High, `≤ 1500 mg/m²` is Moderate; `Cytarabine ≥ 3 g/m²` is High; `Methotrexate ≥ 12 g/m²` is High), and combinations escalate risk (`Ifosfamide [MEC] + Etoposide [LEC] → High [HEC]` in **Casus 3**). Moreover, hospital policy (**UZA July 2026 v2**) classifies `Carboplatin` and `Doxorubicin` as **High**, whereas **POGO 250111** lists them as Moderate in some contexts.
2. **Pediatric dosing precision & hard contraindications (Story 2):**
   - **Hard block (`"GEEN Dexamethasone"`):** Never give Dexamethasone for CINV in **ALL** (**Casus 2**), **Brain Tumors (`hersentumoren`)**, **Dinutuximab beta** immunotherapy, **AML / CAR-T**, or chemotherapy blocks that already contain corticosteroids.
   - **Exact pediatric rounding & formulation math:**
     - `Ondansetron`: `5 mg/m²` (max `8 mg/dose`), `3x/d` in HEC, `2x/d` in MEC, `1x/d` in LEC (`2x/d PO` at discharge).
     - `Dexamethasone`: split at `BSA 0.6 m²` (`< 0.6 m²`: `1 mg 2x/d` with Aprepitant / `2 mg 2x/d` without; `≥ 0.6 m²`: `2 mg 2x/d` with Aprepitant / `4 mg 2x/d` without — automatic **50% CYP3A4 reduction** with Aprepitant) plus the **IV `Aacidexam® 5 mg/mL = ±4 mg/mL` active dexamethasone base** alert.
     - `(Fos)Aprepitant`: contraindicated `< 6 months` or `≤ 6 kg`; `< 12y`: `3 mg/kg` Day 1 (max `125 mg`) then `2 mg/kg` Days 2–3 (max `80 mg`); `≥ 12y`: `125 mg` Day 1, `80 mg` Days 2–3.
     - `Olanzapine`: indicated `≥ 2y` in HEC (`0.1 mg/kg` PO `1x/d`, max `5 mg`), **rounded DOWN to the nearest `0.5 mg`** (e.g., `18.9 kg × 0.1 mg/kg = 1.89 mg → 1.5 mg`).
3. **Prior-cycle EHR (`toernota`) history & formulation personalization (Story 3):** Children who cannot swallow tablets need oral syrup/suspension (`mg → mL`) or IV switches; patients with breakthrough nausea on prior cycles need step-up prophylaxis (`Ondansetron 2x/d → 3x/d` or `Palonosetron` switch in **Casus 1**; extending `Aprepitant` onto Days 4–5 for 5-day `IE` regimens in **Casus 3**; `Lorazepam` or `Alizapride` rescue).
4. **Discharge handover & Belgian family resources (Story 4):** Parents going home need a jargon-free day-by-day schedule (`NL`/`FR`/`EN`) in `mL`/`mg`, red-flag dehydration signs, direct links to verified Belgian hospital brochures (`CINV resources in Belgium.xlsx` without the *"Brussels Bilingual Redirection Loop"*), and a single-tap **Companion App** nausea tracker.
5. **Literature cross-check & lethal DDI/QTc screening (Stories 5 & 6):** Clinicians need side-by-side **UZA v2 vs. POGO 250111** comparisons with page numbers, plus automatic blocks for **Voriconazole / Posaconazole + Vincristine** (severe CYP3A4 neurotoxicity / paralytic ileus), **Azole + Aprepitant** CYP3A4 overload, **Ifosfamide + Aprepitant** encephalopathy risk, and cumulative **CredibleMeds QTc prolongation** (`Ondansetron` + `Voriconazole` / `Domperidone` / `Haloperidol` / `Olanzapine`).

---

## Official UZA Clinical Case Examples (`casus voorbeelden.docx`)

| Case | Patient & Protocol | Regimen & Emetogenicity | Prior Cycle History (`toernota` / EPD) | Almesis Copilot Resolution |
| :--- | :--- | :--- | :--- | :--- |
| **Casus 1** | **16yo girl**, Neuroblastoma (`HR-NBL2`, **RAPID COJEC** Induction: alternating `A1/B1/C1/B2/A2/B3/C2/B4`) | Upcoming **Cyclus B4 (25/09/2026)**: `Vincristine` (Low) + `Cisplatin` (High) $\rightarrow$ **HEC** | On Cycle B3 (05/09), prescribed Ondansetron **2x/d** + Aprepitant + Dexamethasone + Olanzapine; **still had nausea on Day 2** in `toernota`. | Step up Ondansetron from `2x/d` to full UZA v2 HEC **`3x/d`** (`5 mg/m²` max `8 mg`) **OR** switch to IV **Palonosetron** (`20 mcg/kg` max `1500 mcg` `<17y`; never combine with Ondansetron within 3 days) + Aprepitant (`125 mg` D1, `80 mg` D2–3) + Dexamethasone (50% CYP3A4 reduced) + evening Olanzapine; add breakthrough Alizapride/Lorazepam & log in Companion App. |
| **Casus 2** | **2yo boy**, Acute Lymphoblastic Leukemia (`ALLTogether1`, **Induction B**, Day 8) | **Day 8 Chemo**: `Vincristine` (Low) + `Daunorubicin` (MEC) $\rightarrow$ **MEC** | No nausea or vomiting reported in prior administration. | **Ondansetron (`5 mg/m² 2x/d`) + Aprepitant (`3 mg/kg` D1, `2 mg/kg` D2–3 oral suspension)**. **STRICT HARD BLOCK: `GEEN Dexamethasone bij ALL`!** |
| **Casus 3** | Pediatric/adolescent **Ewing Sarcoma** (`iEuroEwing`, alternating `VDC` & `IE`, starting **5-day `IE` Cycle #3**) | **5-day `IE` course**: `Ifosfamide` (MEC alone) + `Etoposide` (LEC alone) $\rightarrow$ **Combination = HEC** (UZA v2 p.1 & POGO 250111) | Breakthrough nausea & vomiting documented on **Day 4** of previous 5-day `IE` cycles. | Maximal HEC quadruple prophylaxis (**Ondansetron `3x/d` + Dexamethasone + Aprepitant + Olanzapine**) + **extend Aprepitant onto Days 4 and 5** for the 5-day multi-day regimen in consultation with the clinical pharmacist. |

---

## Think of it as one expert with a deterministic toolbox

We build directly on the organizer starter in `uc3-aimesis-cinv/`: **one ADK `root_agent` (`gemini-2.5-flash`)** orchestrating deterministic Python tools and an output guardrail callback. The LLM decides which tools to call and synthesizes the explanation; **plain Python code does 100% of the classification, dose math, rounding, and safety checks**.

| Tool | User Story | What it does in plain words |
| :--- | :--- | :--- |
| `classify_regimen_emetogenicity` | **Story 1 & 5** | Classifies each drug and the overall regimen (`Minimal`, `Low`, `Moderate`, `High`) using **UZA v2 p.1 dose-dependent thresholds** (`Cyclophosphamide >1500 mg/m²`, `Cytarabine ≥3 g/m²`, `MTX ≥12 g/m²`, `Carboplatin`/`Doxorubicin` = UZA High), **combination escalations** (`Ifosfamide + Etoposide → HEC`), and returns a **UZA v2 vs. POGO 250111 cross-check diff** |
| `get_pogo_guideline_recommendation` | **Story 1, 2 & 5** | Returns both the **UZA July 2026 v2 baseline regimen** (e.g., HEC 4-drug with Olanzapine `>2y`, MEC Ondansetron `2x/d` + Dexamethasone or Aprepitant) and the **POGO 250111** age-stratified recommendation (`<1y`, `1–11y`, `≥12y`) |
| `check_ddi_interactions` | **Story 6** | Screens for **CYP3A4 blocks** (`Voriconazole/Posaconazole + Vincristine` severe neurotoxicity, `Azole + Aprepitant`, `Aprepitant/Azole + Dexamethasone` 50% reduction, `Ifosfamide + Aprepitant` encephalopathy) and **cumulative CredibleMeds QTc risk** (`Ondansetron` + `Voriconazole` / `Domperidone` / `Haloperidol` / `Olanzapine` / anthracyclines) |
| `calculate_risk_adjusted_regimen` | **Story 2 & 3** | Enforces **`"GEEN Dexamethasone"`** in ALL (**Casus 2**), Brain Tumors (`hersentumoren`), Dinutuximab beta, and steroid-containing chemo; applies **Casus 1** (`Ondansetron 2x/d → 3x/d` or `Palonosetron` 3-day rule), **Casus 3** (Days 4–5 Aprepitant extension), infant `<6m` exclusions, and swallowing/formulation overrides |
| `compute_antiemetic_doses` | **Story 2 & 3** | Computes Mosteller BSA and exact doses in `mg` and liquid volumes in `mL`: `Ondansetron 5 mg/m² (max 8 mg)`, `Dexamethasone` split at `BSA 0.6 m²` + **IV `Aacidexam® 5 mg/mL = ±4 mg/mL` active base alert**, `Aprepitant` weight/age tiers, **`Olanzapine 0.1 mg/kg` rounded DOWN to nearest `0.5 mg`**, and `Lorazepam`/`Alizapride` breakthrough doses |
| `search_guidelines` | **Story 5** | Searches `Anti-emetica beleid CINV - V2.pdf` (hospital policy) and `POGO Emetogenicity Classification Guideline Final-rev- 250111.pdf` page-by-page and returns passages with `[S#]` IDs and page numbers |
| `build_parent_passport` | **Story 4** | Builds the multilingual (`en` / `nl` / `fr`) day-by-day **CINV Patient Passport** (chemo days + delayed phase days, practical `mL` volumes / rounded doses, red-flag dehydration signs, curated Belgian hospital links from `CINV resources in Belgium.xlsx` with the *Brussels Bilingual Redirection Note*, and **Companion App** symptom logger hooks) |

---

## What happens when you press the button

1. **Input:** The clinician enters the child's age, weight, height/BSA, diagnosis/protocol, chemotherapy drugs (and doses in `mg/m²`), concomitant medications (e.g., `voriconazole`, `domperidone`), swallowing ability, and prior-cycle CINV history (`toernota`).
2. **Deterministic Tool Chain:** `root_agent` calls the tools in sequence:
   - `classify_regimen_emetogenicity` $\rightarrow$ UZA v2 tier + POGO 250111 comparison.
   - `get_pogo_guideline_recommendation` $\rightarrow$ UZA v2 + POGO baseline regimens.
   - `check_ddi_interactions` $\rightarrow$ CYP3A4 & cumulative QTc safety gate.
   - `calculate_risk_adjusted_regimen` $\rightarrow$ `"GEEN Dexamethasone"` block + Casus 1–3 personalizations.
   - `compute_antiemetic_doses` $\rightarrow$ BSA/weight math, `0.5 mg` Olanzapine floor rounding, `Aacidexam®` conversion, and `mL` syrup volumes stored in `tool_context.state["facts_doses"]`.
   - `search_guidelines` $\rightarrow$ exact page citations (`[S1]`, `[S2]`, …) stored in `tool_context.state["facts_evidence"]`.
   - `build_parent_passport` $\rightarrow$ multilingual (`NL`/`FR`/`EN`) schedule + Belgian resources stored in `tool_context.state["facts_passport"]`.
3. **Output Guardrail (`after_model_callback`):** Before the clinician sees the response, `app/guardrail.py` verifies that every `<number> mg` / `<number> mL` and `[S#]` citation in the text matches `tool_context.state`, strips any unsupported numbers, and enforces `"Advisory Only — Requires Clinician Sign-Off"`.

---

## Why it is safe (non-negotiable clinical guardrails)

- **AI never does the math:** BSA, `5 mg/m²` caps, `BSA 0.6 m²` dexamethasone splits, `Aacidexam® 4 mg/mL` conversions, `Olanzapine 0.5 mg` floor rounding, and `mL` liquid volumes are computed purely in deterministic Python.
- **Hard Contraindication Enforcement (`"GEEN Dexamethasone"`):** Deterministically blocks dexamethasone in ALL (**Casus 2**), Brain Tumors (`hersentumoren`), Dinutuximab beta, AML/CAR-T, and steroid-containing chemo regimens.
- **Facts come from clinician-verifiable tables (`app/tables.py`):** Every rule row carries `source` (with document & page number, e.g., `UZA CINV v2 p.1`, `UZA CINV v2 p.2`, `POGO 250111`) and a `verified` flag. Unverified rows are blocked unless `ALLOW_UNVERIFIED=1` is set for demo mode (which explicitly flags `unverified_sources` in the output).
- **Mandatory Regulatory Banner:** Every tool output and final agent response ends with `Advisory Only — Requires Clinician Sign-Off`.

---

## The Google Cloud Architecture

| Google Cloud Service | What it does in Almesis Copilot |
| :--- | :--- |
| **Gemini 2.5 Flash (Vertex AI)** | Orchestrates the 7 deterministic clinical tools and formats the clinician summary & parent passport |
| **ADK (Agent Development Kit)** | Connects `root_agent`, `ToolContext` state (`facts_doses`, `facts_evidence`, `facts_passport`), and the `after_model_callback` guardrail |
| **Cloud Run (`europe-west1`)** | Hosts the FastAPI + ADK Web UI + A2A endpoint so clinicians can open it via a link |
| **Cloud Trace & Cloud Logging** | Records every prompt, deterministic tool call, and guardrail check for hospital auditability |
| **BigQuery & Vertex AI Search** | Optional managed backends (`DATA_BACKEND`, `GUIDELINE_BACKEND`) in `europe-west1` + protocol PDF extraction to unverified rows |

All cloud infrastructure runs in **`europe-west1`** (Belgium — GDPR & Belgian hospital data residency compliant).

![Almesis Copilot Architecture](media/almesis_copilot_architecture.png)

---

## Alignment with the Codelab & Organizers' Brief

| Organizer Brief / User Story | Codelab Requirement (`uc3-aimesis-quickstart.lab.md`) | How Almesis Copilot Resolves It |
| :--- | :--- | :--- |
| **1. Emetic risk tiering (Story 1)** | Dose-dependent thresholds (`Cyclophosphamide >1500 mg/m²`, `Cytarabine ≥3 g/m²`, `MTX ≥12 g/m²`, `Carboplatin`/`Doxorubicin` = UZA High) + combination escalation (`Ifosfamide + Etoposide → HEC`, **Casus 3**) | `classify_regimen_emetogenicity` & `evaluate_uza_cinv_policy_v2` evaluate both drug names and optional `drug_doses_mg_m2` against `UZA CINV v2 p.1` and `POGO 250111` |
| **2. Cross-check hospital guidelines (Story 5)** | UZA July 2026 v2 policy first, side-by-side comparison with 87-page POGO 250111 guideline with page citations | `classify_regimen_emetogenicity`, `get_pogo_guideline_recommendation`, and `search_guidelines` return UZA v2 vs. POGO diffs and `[S#]` page snippets |
| **3. Patient characteristics, dosing & DDIs (Stories 2, 3 & 6)** | `"GEEN Dexamethasone"` block (**Casus 2**), `Olanzapine 0.1 mg/kg` floor to `0.5 mg` (`18.9 kg → 1.5 mg`), `Aacidexam® 5 mg/mL = ±4 mg/mL` alert, **Casus 1** (`Ondansetron 3x/d` / `Palonosetron`), **Casus 3** (D4–5 `Aprepitant`), `Voriconazole + Vincristine` block & cumulative QTc (`Ondansetron + Domperidone/Haloperidol`) | `compute_antiemetic_doses`, `calculate_risk_adjusted_regimen`, and `check_ddi_interactions` compute exact `mg` & `mL` doses and enforce all hard blocks |
| **4. Antiemetic passport & Companion App (Story 4)** | Multilingual (`NL`/`FR`/`EN`) day-by-day schedule, red-flag dehydration signs, curated Belgian links (`CINV resources in Belgium.xlsx` + Brussels redirection note), and 1-tap Companion App nausea logging | `build_parent_passport` & `generate_cinv_patient_passport` generate the family schedule from `facts_doses` with Belgian hospital links and Companion App tracking |

---

## The 3-Minute Wintercircus Jury Demo Story

1. **Dose-Dependent Escalation & Olanzapine `0.5 mg` Floor Rounding (Stories 1 & 2):**
   - Run an `18.9 kg` (`BSA 0.76 m²`, `6yo`) solid tumor child on `Cisplatin + Doxorubicin` (cannot swallow tablets, anticipatory vomiting) — or show `Cyclophosphamide` stepping up from `Moderate` (`1000 mg/m²`) to `High` (`1600 mg/m²`).
   - Point to the tool trace: **Olanzapine `18.9 kg × 0.1 mg/kg = 1.89 mg → 1.5 mg` (rounded down to nearest `0.5 mg`)**, **Dexamethasone `2 mg 2x/d` (50% reduced for Aprepitant) with the IV `Aacidexam® 5 mg/mL = ±4 mg/mL` (`0.5 mL`) alert**, and liquid `mL` volumes. Say: *"The AI never does the math."*
2. **Casus 2 ("GEEN Dexamethasone") & Casus 3 (5-Day `IE` Combination Escalation):**
   - **Casus 2 (2yo boy, ALLTogether1 Induction B Day 8: Vincristine + Daunorubicin):** Shows `MEC`, recommends `Ondansetron 2x/d + Aprepitant`, and triggers **`HARD BLOCK: GEEN Dexamethasone bij ALL`** (same block for Brain Tumors / Dinutuximab beta).
   - **Casus 3 (iEuroEwing 5-day `IE`: Ifosfamide + Etoposide with Day 4 breakthrough nausea):** Shows `Ifosfamide (MEC) + Etoposide (LEC) → HEC` per `UZA CINV v2 p.1` & `POGO 250111`, recommends quadruple HEC prophylaxis, and flags extending `Aprepitant` onto Days 4–5.
3. **Lethal CYP3A4 & Cumulative QTc Safety Gate (Story 6):**
   - Add **`Voriconazole`** to a regimen containing **`Vincristine`** and **`Ondansetron`** (or add `Domperidone`/`Haloperidol`): flags the **CRITICAL `Voriconazole + Vincristine` neurotoxicity/paralytic ileus block** (hold azole 24–48h), **Azole + Aprepitant** interaction, and **HIGH cumulative QTc risk** with ECG / K+ / Mg2+ orders.
4. **Multilingual Dutch/French Patient Passport & UZA v2 vs. POGO Diff (Stories 4 & 5):**
   - Switch the CINV Patient Passport to **Dutch (`NL`)**: shows the day-by-day schedule in practical `mL` / rounded doses, Belgian family brochures (`UZA`, `ZAS`, `CHU de Liège`, `Stichting tegen Kanker`, `KickCancer`, `UZ Leuven` with the *Brussels Bilingual Redirection Note*), Companion App 1-tap nausea logging, `[S#]` page citations from `UZA CINV v2 p.1–2` vs. `POGO 250111`, and the guardrail-enforced `"Advisory Only — Requires Clinician Sign-Off"` banner.

---

## Implementation Architecture & Build Spec (`uc3-aimesis-cinv/`)

All application code lives in `uc3-aimesis-cinv/app/` and keeps the single `root_agent` (`gemini-2.5-flash`) architecture:

| Module | Responsibility | Status |
| :--- | :--- | :--- |
| `app/tables.py` | Verifiable clinical tables (`PEDIATRIC_CHEMO_EMETOGENICITY`, `COMBINATION_ESCALATION_RULES`, `DOSE_RULES`, `FORMULATIONS`, `SCHEDULE_RULES`, `PARENT_INSTRUCTIONS`, `BELGIAN_CINV_PATIENT_RESOURCES`, `QTC_RISK_REGISTRY`) with `source` (document + page) and `verified` flag (`usable(row)` respects `ALLOW_UNVERIFIED=1`) | ✅ Complete |
| `app/dosing.py` | Deterministic `bsa_mosteller` and `compute_antiemetic_doses` (`mg` & `mL` volumes, `"GEEN Dexamethasone"` hard block, `BSA 0.6 m²` split, `Aacidexam® 5 mg/mL = ±4 mg/mL` active base alert, `Olanzapine 0.5 mg` floor rounding); stores `facts_doses` in `ToolContext.state` | ✅ Complete |
| `app/guidelines.py` | Page-by-page PDF search (`search_guidelines`) over `docs/Anti-emetica beleid CINV - V2.pdf` (`hospital`) and `docs/POGO Emetogenicity Classification Guideline Final-rev- 250111.pdf` (`external`); stores `[S#]` citations in `facts_evidence` | ✅ Complete |
| `app/passport.py` | Multilingual (`en`/`nl`/`fr`) parent schedule (`build_parent_passport`) with `mL`-only liquid volumes, `SCHEDULE_RULES` clock times, Belgian hospital links, and Companion App nausea logger; stores `facts_passport` | ✅ Complete |
| `app/guardrail.py` | Deterministic `after_model_callback` (`guard`) verifying every `<number> mg`/`<number> mL` and `[S<n>]` citation against `ToolContext.state` and enforcing `ADVISORY_LABEL` | ✅ Complete |
| `app/agent.py` | `root_agent` (`gemini-2.5-flash`) wired with all 7 tools, `after_model_callback=guard`, `UZA_CASUS_VOORBEELDEN` (Casus 1–3), and `SYSTEM_INSTRUCTION` | ✅ Complete |
| `tests/` | Unit tests (`tests/unit/test_dosing.py`, `tests/unit/test_dummy.py`), integration tests (`tests/integration/`), and evaluation dataset (`tests/eval/datasets/basic-dataset.json`) covering Casus 1–3 and safety gates | ✅ Complete |

### Quick Commands (run inside `uc3-aimesis-cinv/`)

```bash
# 1. Install dependencies
agents-cli install

# 2. Run unit & integration tests (with ALLOW_UNVERIFIED=1 for demo tables)
ALLOW_UNVERIFIED=1 uv run pytest tests/unit tests/integration -v

# 3. Launch local ADK Web UI playground
ALLOW_UNVERIFIED=1 agents-cli playground

# 4. Run evaluation suite
ALLOW_UNVERIFIED=1 agents-cli eval run

# 5. Deploy to Cloud Run (europe-west1) — requires explicit human approval
gcloud config set project qwiklabs-gcp-02-42ffcfa95945
agents-cli deploy
```

