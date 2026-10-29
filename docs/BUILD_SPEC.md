# Almesis Copilot: final build spec for coding agents

Oct 29, 2026 · @mikaeel

## Start here

This is the one final spec; it replaces the two earlier spec versions, and nothing in it is a patch. Build the phases in order and pass each phase's acceptance check before starting the next.

| Phase | What it builds | Priority |
| --- | --- | --- |
| 1 to 3 | Scaffold, seed tables, deterministic tools | Required |
| 4 | Guideline search (local PDF mode first) | Required |
| 5 | ADK agents, including the parent passport | Required |
| 6 | Streamlit UI | Required |
| 9 | Tests and demo script | Required |
| 7 | Protocol PDF extraction | If time allows |
| 8 | BigQuery, Vertex AI Search, Cloud Run | If time allows (best for scoring) |

The app can run fully locally with CSV tables and PDF search from Phase 6 on. Phase 8 moves it onto Google Cloud.

A person must supply four things the coding agent cannot invent: the UZA July 2026 CINV policy PDF, pharmacy formulation data, clinician-written parent instruction texts, and Google Cloud access. Phase 0 lists them.

Copy this prompt to the coding agent together with this document:

```
You are building Almesis Copilot, a pediatric chemotherapy-induced nausea and vomiting (CINV) decision-support MVP on Google Cloud, using Google ADK and Gemini. The full spec is the document I give you. Follow it exactly.

Working rules:
1. Build one phase at a time, in order (Phase 1 to Phase 9). After each phase, run its acceptance check and show me the result before starting the next phase. If a check fails, fix it before moving on.
2. Never let an LLM calculate or retype a clinical number. All numbers come from the deterministic tools in tools.py, which read the patient from session state.
3. Use synthetic patient data only. Never invent clinical values: seed tables are placeholders with verified=false and must stay that way.
4. If an ADK, Vertex AI or Gemini call in the spec fails or has changed, read the installed package docs or source, adapt the code, and keep the behaviour identical. Tell me what you changed.
5. Stop and ask me if you need the UZA policy PDF, pharmacy formulation data, parent instruction texts, or Google Cloud credentials. Do not make these up.
6. Keep files small. Every tool gets a pytest.

Start with Phase 1 now. After each phase report: files created, acceptance result, and anything you had to adapt.
```

## Rules for the coding agent

1. Build phases in order. Do not start phase N+1 until the acceptance checks of phase N pass.
2. LLMs never calculate or retype clinical numbers. Every number (doses, volumes, times, risk levels) comes from a deterministic Python tool that reads the patient from ADK session state. The LLM only formats.
3. Use synthetic patient data only.
4. Every clinical table has a `verified` column. Rows with `verified=false` are placeholders. Tools ignore them unless `ALLOW_UNVERIFIED=1` (dev and rehearsal only; the UI then shows a red banner).
5. Never invent hospital policy, doses, concentrations or parent instructions. Seed values are placeholders. A clinician or pharmacist replaces them.
6. Configuration only through environment variables. No secrets in the repo.
7. ADK, Discovery Engine and Gemini model IDs change over time. If a call below fails, read the installed package docs or source, adapt, and keep the behaviour identical. If `gemini-2.5-*` is retired, use the current Pro and Flash model IDs from the Vertex AI docs.
8. Keep files small. Every tool gets one pytest.
9. CSV text fields never contain commas; use semicolons inside text.

## Design decisions and final pipeline

The app implements the four steps of the UC3 brief: emetic risk tiering, cross-check against the hospital policy, patient-specific dose in mL, and a parent passport.

The ADK pipeline is a `SequentialAgent` that runs in this order:

1. `risk_agent`: tiers the regimen as HEC, MEC or LEC, including multi-day regimens.
2. `plan_agent`: picks antiemetics from the UZA policy rows first, compares them with the POGO rows, and reports a guideline match.
3. Parallel group: `guideline_agent` (RAG with page citations), `interaction_agent` (QT and CYP3A4 checks), `dosing_agent` (BSA or weight dose, converted to mL).
4. `passport_agent`: builds the day-by-day home schedule in code.
5. `synthesizer` (Gemini 2.5 Pro): writes the clinician report from the tool facts only.
6. `guardrail_agent`: checks the report against the facts.
7. `passport_writer` (Gemini 2.5 Pro): formats the parent passport in English, Dutch or French from the schedule facts and clinician-written texts.
8. `passport_guardrail`: checks every mg, mL and clock time in the passport.

Other decisions:

- **Patient data** enters session state through a `before_agent_callback` that parses the first message as JSON. Tools read it from state, so the LLM never passes clinical numbers as arguments.
- **Facts** are stored by the tools in session state under `facts_*` keys. Agents read them through `{placeholders}` in their instructions.
- **UI:** Streamlit running the ADK `Runner` in-process, deployed on Cloud Run. Agent Engine is a stretch goal.
- **Data:** nine small tables in BigQuery (location EU) with a CSV fallback (`DATA_BACKEND`).
- **RAG:** a Vertex AI Search data store in `eu`, with a local PDF-page search fallback (`GUIDELINE_BACKEND`). A file name starting with `uza_` marks hospital policy.
- **Protocol extraction:** Gemini reads the PDF natively and returns a Pydantic schema. Document AI is optional, for scanned PDFs.
- **Audit trail:** Firestore, or a local JSONL file.
- **Regions:** Vertex AI and Cloud Run `europe-west1`, BigQuery `EU`, Vertex AI Search `eu`, Firestore `eur3`. If a model is not available in `europe-west1`, use another EU region and note it.

The nine tables: `regimens`, `plan_rules`, `dose_rules`, `formulations`, `schedule_rules`, `parent_instructions`, `drug_classes`, `interaction_rules` (clinical), plus `regimen_extractions` (Phase 7 output). The guideline index lives in Vertex AI Search, not in a table.

## Phase 0: human prerequisites

A person does these, not the coding agent. Items 1 and 2 can start today; the build does not wait for 3 to 6.

1. Create a Google Cloud project with billing. Run `gcloud auth login`, `gcloud auth application-default login`, `gcloud config set project PROJECT_ID`.
2. Get the UZA July 2026 CINV policy PDF from the organizers or the clinical contact. Save it as `data/guidelines/uza_cinv_policy_2026-07.pdf`. The `uza_` prefix marks hospital policy; every other PDF counts as an external guideline.
3. Add a public external guideline PDF to `data/guidelines/`, for example the POGO pediatric CINV guideline. Check that its license allows this use.
4. A clinician or pharmacist reads the policy and the guideline, replaces the placeholder values in the seed CSVs of Phase 2 (risk tiers, plan rules, doses, schedules), fills `source` with document name and page, and sets `verified=true`. The ondansetron value of 5 mg/m2 on the brief slide is a starting point to check against the policy, not a verified value.
5. The hospital pharmacy supplies the real formulation data for `formulations.csv`: concentration in mg per mL and the practical rounding step per drug and route.
6. A clinician writes the plain-language parent instruction and rescue texts for `parent_instructions.csv` in English, Dutch and French. The AI only formats these texts; it never writes medical advice for parents.

Optional speed-up: reuse the Phase 7 extraction idea on the policy PDF to draft table rows with page numbers, then have the clinician review every row.

If items 4 to 6 are not ready for the demo, keep `ALLOW_UNVERIFIED=1` so the placeholder values work. The red banner stays visible and the pitch must say that the tables are placeholders awaiting clinician verification.

## Phase 1: scaffold

Create this layout:

```
almesis/
  app.py                    Streamlit UI + ADK Runner
  almesis_agent/
    __init__.py             loads .env, then: from . import agent
    agent.py                agents + root_agent
    tools.py                deterministic tools
    models.py  data.py  guidelines.py  presets.py  protocol.py
  data/seed/                8 CSV files (Phase 2)
  data/guidelines/          PDFs (uza_ prefix = hospital policy)
  scripts/load_bq.py  scripts/setup_gcp.sh
  tests/test_tools.py
  requirements.txt  .env.example  Dockerfile
```

`requirements.txt`:

```
google-adk
google-genai
google-cloud-bigquery
google-cloud-discoveryengine
google-cloud-firestore
pandas
db-dtypes
pydantic>=2
streamlit
pypdf
python-dotenv
pytest
```

`.env.example` (copy to `.env`):

```
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=europe-west1
MODEL_PRO=gemini-2.5-pro
MODEL_FAST=gemini-2.5-flash
DATA_BACKEND=csv
BQ_DATASET=almesis
GUIDELINE_BACKEND=local
DISCOVERY_DATASTORE=almesis-guidelines
ALLOW_UNVERIFIED=1
AUDIT_BACKEND=file
```

`almesis_agent/__init__.py`:

```python
from dotenv import load_dotenv
load_dotenv()
from . import agent
```

**Acceptance:** `pip install -r requirements.txt` succeeds and `python -c 'import google.adk'` works.

## Phase 2: seed data

Create these eight CSVs in `data/seed/` exactly as shown. All values are illustrative placeholders, not clinical guidance; the clinician replaces them in Phase 0. Keep every row `verified=false`. The ondansetron 5 mg/m2 dose comes from the organizers' slide and is also unverified. Column order matters because the BigQuery schemas in Phase 8 use the same order.

`regimens.csv` (risk tier per chemotherapy drug; `multi_day` blank means any, `true` or `false` when the policy tiers multi-day use differently):

```
drug,min_dose_mg_m2,max_dose_mg_m2,level,source,verified,multi_day
cisplatin,,,high,TODO policy+page,false,
cyclophosphamide,1000,,high,TODO policy+page,false,
doxorubicin,,,moderate,TODO policy+page,false,
carboplatin,,,moderate,TODO policy+page,false,
etoposide,,,low,TODO policy+page,false,
vincristine,,,low,TODO policy+page,false,
```

Levels are `high` (HEC), `moderate` (MEC) and `low` (LEC, includes minimal).

`plan_rules.csv` (antiemetics per level; `source_set` is `uza` for the hospital policy and `pogo` for the external guideline; the clinician edits both sets from the two documents):

```
level,drug,role,min_age_years,only_if_prior_cinv,source,verified,source_set
high,ondansetron,5HT3 antagonist,0,false,TODO,false,uza
high,aprepitant,NK1 antagonist,0.5,false,TODO,false,uza
high,dexamethasone,corticosteroid,0,false,TODO,false,uza
moderate,ondansetron,5HT3 antagonist,0,false,TODO,false,uza
moderate,dexamethasone,corticosteroid,0,false,TODO,false,uza
moderate,aprepitant,NK1 antagonist,0.5,true,TODO,false,uza
low,ondansetron,5HT3 antagonist,0,false,TODO,false,uza
high,ondansetron,5HT3 antagonist,0,false,TODO,false,pogo
high,aprepitant,NK1 antagonist,0.5,false,TODO,false,pogo
high,dexamethasone,corticosteroid,0,false,TODO,false,pogo
moderate,ondansetron,5HT3 antagonist,0,false,TODO,false,pogo
moderate,dexamethasone,corticosteroid,0,false,TODO,false,pogo
moderate,aprepitant,NK1 antagonist,0.5,true,TODO,false,pogo
low,ondansetron,5HT3 antagonist,0,false,TODO,false,pogo
```

`dose_rules.csv` (one row per drug and route; `basis` is `mg_per_kg` or `mg_per_m2`):

```
drug,route,basis,dose_per_unit,max_dose_mg,frequency,source,verified
ondansetron,IV,mg_per_m2,5,8,per scheduled time,TODO UZA policy,false
ondansetron,PO,mg_per_m2,5,8,per scheduled time,TODO UZA policy,false
dexamethasone,PO,mg_per_m2,6,,per scheduled time,TODO UZA policy,false
aprepitant,PO,mg_per_kg,3,125,per scheduled time,TODO UZA policy,false
```

`formulations.csv` (how each dose becomes a practical volume; the pharmacy supplies the real values):

```
drug,route,form,concentration_mg_per_ml,rounding_step_ml,max_rounding_diff_pct,source,verified
ondansetron,PO,syrup,0.8,0.5,10,TODO hospital pharmacy,false
dexamethasone,PO,oral solution,1,0.5,10,TODO hospital pharmacy,false
aprepitant,PO,oral suspension,25,0.5,10,TODO hospital pharmacy,false
```

`schedule_rules.csv` (when each drug is given; `setting` is `hospital` or `home`; `applies_to` is `each_chemo_day` or `delayed_days`; `delayed_days` is how many days after the last chemo day the drug continues; clock times are separated by semicolons):

```
level,drug,route,setting,applies_to,delayed_days,clock_times,source,verified
high,ondansetron,IV,hospital,each_chemo_day,0,08:00,TODO UZA policy,false
high,ondansetron,PO,home,each_chemo_day,0,16:00;22:00,TODO UZA policy,false
high,ondansetron,PO,home,delayed_days,2,08:00;16:00;22:00,TODO UZA policy,false
high,dexamethasone,PO,home,each_chemo_day,0,08:00,TODO UZA policy,false
high,aprepitant,PO,home,each_chemo_day,0,08:00,TODO UZA policy,false
moderate,ondansetron,PO,home,each_chemo_day,0,08:00;16:00,TODO UZA policy,false
moderate,dexamethasone,PO,home,each_chemo_day,0,08:00,TODO UZA policy,false
moderate,aprepitant,PO,home,each_chemo_day,0,08:00,TODO UZA policy,false
low,ondansetron,PO,home,each_chemo_day,0,08:00,TODO UZA policy,false
```

`parent_instructions.csv` (clinician-written texts; replace every TODO; repeat the `nl` and `fr` rows for each drug):

```
drug,language,instruction,rescue_instruction,source,verified
ondansetron,en,TODO plain-language instruction,TODO rescue instruction,TODO,false
ondansetron,nl,TODO,TODO,TODO,false
ondansetron,fr,TODO,TODO,TODO,false
dexamethasone,en,TODO plain-language instruction,TODO rescue instruction,TODO,false
aprepitant,en,TODO plain-language instruction,TODO rescue instruction,TODO,false
```

`drug_classes.csv`:

```
drug,class
ondansetron,qt_prolonging
voriconazole,cyp3a4_inhibitor
voriconazole,qt_prolonging
erythromycin,cyp3a4_inhibitor
erythromycin,qt_prolonging
rifampicin,cyp3a4_inducer
carbamazepine,cyp3a4_inducer
```

`interaction_rules.csv`:

```
antiemetic,other_class,severity,note,source,verified
ondansetron,qt_prolonging,major,Additive QT prolongation; consider ECG and electrolytes or an alternative,TODO,false
aprepitant,cyp3a4_inhibitor,moderate,May raise aprepitant exposure,TODO,false
aprepitant,cyp3a4_inducer,moderate,May lower aprepitant exposure,TODO,false
dexamethasone,cyp3a4_inhibitor,moderate,May raise dexamethasone exposure,TODO,false
```

**Acceptance:** `pandas.read_csv` loads all eight files without errors. Every `(level, drug)` pair in `plan_rules.csv` has a row in `schedule_rules.csv`, and every `(drug, route)` pair in `schedule_rules.csv` has a row in `dose_rules.csv`.

## Phase 3: models, data access and deterministic tools

`almesis_agent/models.py`:

```python
from pydantic import BaseModel, Field

class RegimenDrug(BaseModel):
    drug: str
    dose_mg_m2: float | None = None
    days: list[int] = Field(default=[1], min_length=1)

class Patient(BaseModel):
    age_years: float = Field(ge=0, le=25)
    weight_kg: float = Field(ge=1, le=150)
    height_cm: float = Field(ge=30, le=220)
    regimen: list[RegimenDrug] = Field(min_length=1)
    current_meds: list[str] = []
    prior_cinv: bool = False
    language: str = Field(default='en', pattern='^(en|nl|fr)$')
```

`almesis_agent/data.py`:

```python
import functools, os
import pandas as pd

SEED = os.path.join(os.path.dirname(__file__), '..', 'data', 'seed')

@functools.lru_cache(maxsize=None)
def table(name: str) -> pd.DataFrame:
    if os.getenv('DATA_BACKEND', 'csv') == 'bigquery':
        from google.cloud import bigquery
        c = bigquery.Client(project=os.environ['GOOGLE_CLOUD_PROJECT'], location='EU')
        return c.query('SELECT * FROM `' + c.project + '.' + os.environ['BQ_DATASET'] + '.' + name + '`').to_dataframe()
    return pd.read_csv(os.path.join(SEED, name + '.csv'))

def usable(df: pd.DataFrame) -> pd.DataFrame:
    if os.getenv('ALLOW_UNVERIFIED', '0') == '1':
        return df
    return df[df['verified'].astype(str).str.lower() == 'true']
```

`almesis_agent/tools.py`. Tools take no clinical arguments (only `tool_context`), return plain Python types (cast pandas and numpy values, because ADK serialises results to JSON), and store their result in session state under `facts_*`. Part 1: helpers, risk, plan.

```python
import math, re
import pandas as pd
from google.adk.tools import ToolContext
from .data import table, usable
from .models import Patient

LEVELS = ['low', 'moderate', 'high']
LABELS = {'high': 'HIGH RISK (HEC)', 'moderate': 'MODERATE (MEC)', 'low': 'LOW / MINIMAL (LEC)'}

def _true(x):
    return str(x).strip().lower() == 'true'

def _p(ctx):
    return Patient.model_validate(ctx.state['patient'])

def bsa_mosteller(height_cm, weight_kg):
    return round(math.sqrt(height_cm * weight_kg / 3600), 3)

def classify_regimen(tool_context: ToolContext) -> dict:
    '''Classify the emetogenic risk (HEC, MEC, LEC) of the patient regimen from the database. Takes no arguments.'''
    p = _p(tool_context)
    df = usable(table('regimens'))
    comps, worst = [], 'low'
    for d in p.regimen:
        match = None
        for _, r in df[df.drug.str.lower() == d.drug.lower()].iterrows():
            if pd.notna(r.multi_day) and _true(r.multi_day) != (len(d.days) > 1):
                continue
            lo = r.min_dose_mg_m2 if pd.notna(r.min_dose_mg_m2) else 0
            hi = r.max_dose_mg_m2 if pd.notna(r.max_dose_mg_m2) else float('inf')
            if d.dose_mg_m2 is None or lo <= d.dose_mg_m2 <= hi:
                match = r
                break
        if match is None:
            comps.append({'drug': d.drug, 'level': None, 'note': 'not in database'})
            continue
        comps.append({'drug': d.drug, 'level': str(match.level), 'source': str(match.source), 'verified': _true(match.verified)})
        if LEVELS.index(match.level) > LEVELS.index(worst):
            worst = str(match.level)
    unknown = [c['drug'] for c in comps if c['level'] is None]
    multi = any(len(d.days) > 1 for d in p.regimen)
    res = {'overall_level': worst, 'label': LABELS[worst], 'multi_day': multi, 'components': comps,
           'unknown_drugs': unknown, 'needs_review': bool(unknown), 'rule': 'highest component level wins'}
    tool_context.state['facts_risk'] = res
    return res

def _select(df, level, p, set_name):
    d = df[(df.source_set == set_name) & (df.level == level) & (df.min_age_years <= p.age_years)]
    prior_only = d.only_if_prior_cinv.astype(str).str.lower() == 'true'
    return d[(~prior_only) | p.prior_cinv]

def build_plan(tool_context: ToolContext) -> dict:
    '''Select antiemetics for the risk level. Hospital policy (uza) first, POGO as comparison. Takes no arguments.'''
    p = _p(tool_context)
    risk = tool_context.state['facts_risk']
    df = usable(table('plan_rules'))
    uza, pogo = _select(df, risk['overall_level'], p, 'uza'), _select(df, risk['overall_level'], p, 'pogo')
    primary = uza if not uza.empty else pogo
    a, b = set(uza.drug), set(pogo.drug)
    if uza.empty or pogo.empty:
        status = 'single_source'
    else:
        status = 'match' if a == b else 'mismatch'
    match = {'status': status, 'primary_source': 'uza' if not uza.empty else 'pogo',
             'only_in_hospital_policy': sorted(a - b), 'only_in_pogo': sorted(b - a)}
    items = [{'drug': str(r.drug), 'role': str(r.role), 'source': str(r.source)} for _, r in primary.iterrows()]
    note = '' if items else 'no plan rows for this level; no routine prophylaxis in database'
    res = {'level': risk['overall_level'], 'label': risk['label'], 'antiemetics': items,
           'prior_cinv': p.prior_cinv, 'guideline_match': match, 'note': note}
    tool_context.state['facts_plan'] = res
    return res
```

Part 2 of `tools.py`: doses in mg and mL, interactions, parent schedule, verification. Append to the same file.

```python
def compute_doses(tool_context: ToolContext) -> dict:
    '''Compute doses in code from BSA or weight, then convert to a practical volume in mL. Takes no arguments.'''
    p = _p(tool_context)
    s = tool_context.state
    plan_drugs = {a['drug'] for a in s['facts_plan']['antiemetics']}
    sched = usable(table('schedule_rules'))
    sched = sched[(sched.level == s['facts_risk']['overall_level']) & sched.drug.isin(plan_drugs)]
    pairs = sorted({(str(r.drug), str(r.route)) for _, r in sched.iterrows()})
    bsa = bsa_mosteller(p.height_cm, p.weight_kg)
    rules, forms = usable(table('dose_rules')), usable(table('formulations'))
    out = []
    for drug, route in pairs:
        rows = rules[(rules.drug == drug) & (rules.route == route)]
        if rows.empty:
            out.append({'drug': drug, 'route': route, 'dose_mg': None, 'note': 'no usable dose rule; clinician must determine dose'})
            continue
        r = rows.iloc[0]
        raw = float(r.dose_per_unit) * (p.weight_kg if r.basis == 'mg_per_kg' else bsa)
        capped = bool(pd.notna(r.max_dose_mg) and raw > float(r.max_dose_mg))
        dose = float(r.max_dose_mg) if capped else raw
        item = {'drug': drug, 'route': route, 'dose_mg': round(dose, 1), 'dose_per_unit': float(r.dose_per_unit), 'basis': str(r.basis),
                'capped_at_max': capped, 'max_dose_mg': None if pd.isna(r.max_dose_mg) else float(r.max_dose_mg),
                'frequency': str(r.frequency), 'source': str(r.source), 'verified': _true(r.verified)}
        f = forms[(forms.drug == drug) & (forms.route == route)]
        if not f.empty:
            f = f.iloc[0]
            conc, step = float(f.concentration_mg_per_ml), float(f.rounding_step_ml)
            vol = math.floor(dose / conc / step + 0.5) * step
            diff = abs(vol * conc - dose) / dose * 100
            item.update({'form': str(f.form), 'concentration_mg_per_ml': conc, 'volume_ml': round(vol, 2),
                         'actual_dose_mg': round(vol * conc, 2), 'rounding_diff_pct': round(diff, 1),
                         'rounding_ok': bool(diff <= float(f.max_rounding_diff_pct))})
        out.append(item)
    res = {'bsa_m2': bsa, 'weight_kg': p.weight_kg, 'doses': out}
    s['facts_doses'] = res
    return res

def check_interactions(tool_context: ToolContext) -> dict:
    '''Check planned antiemetics against current medicines using the rules table. Takes no arguments.'''
    p = _p(tool_context)
    cls = table('drug_classes')
    rules = usable(table('interaction_rules'))
    alerts, unknown = [], []
    for med in [m.lower() for m in p.current_meds]:
        classes = set(cls[cls.drug.str.lower() == med]['class'])
        if not classes:
            unknown.append(med)
        for a in tool_context.state['facts_plan']['antiemetics']:
            for _, r in rules[rules.antiemetic == a['drug']].iterrows():
                if r.other_class in classes:
                    alerts.append({'antiemetic': a['drug'], 'other_drug': med, 'class': str(r.other_class), 'severity': str(r.severity),
                                   'note': str(r.note), 'source': str(r.source), 'verified': _true(r.verified)})
    res = {'alerts': alerts, 'unknown_meds': unknown}
    tool_context.state['facts_interactions'] = res
    return res

def build_schedule(tool_context: ToolContext) -> dict:
    '''Build the day-by-day home schedule for parents from rules and computed doses. Takes no arguments.'''
    p = _p(tool_context)
    s = tool_context.state
    plan_drugs = {a['drug'] for a in s['facts_plan']['antiemetics']}
    rules = usable(table('schedule_rules'))
    rules = rules[(rules.level == s['facts_risk']['overall_level']) & (rules.setting == 'home') & rules.drug.isin(plan_drugs)]
    doses = {(d['drug'], d['route']): d for d in s['facts_doses']['doses'] if d.get('dose_mg') is not None}
    chemo_days = sorted({day for r in p.regimen for day in r.days})
    last = chemo_days[-1]
    days = {}
    for _, r in rules.iterrows():
        if r.applies_to == 'each_chemo_day':
            target = chemo_days
        else:
            target = list(range(last + 1, last + 1 + int(r.delayed_days)))
        d = doses.get((str(r.drug), str(r.route)))
        for day in target:
            for t in str(r.clock_times).split(';'):
                days.setdefault(day, []).append({'time': t, 'drug': str(r.drug), 'dose_mg': d['dose_mg'] if d else None,
                                                 'volume_ml': d.get('volume_ml') if d else None})
    out = [{'day': n, 'phase': 'chemo day' if n in chemo_days else 'recovery day', 'doses': sorted(v, key=lambda x: x['time'])}
           for n, v in sorted(days.items())]
    instr = usable(table('parent_instructions'))
    texts = {}
    for drug in sorted(plan_drugs):
        row = instr[(instr.drug == drug) & (instr.language == p.language)]
        if row.empty:
            row = instr[(instr.drug == drug) & (instr.language == 'en')]
        texts[drug] = None if row.empty else {'instruction': str(row.iloc[0].instruction), 'rescue': str(row.iloc[0].rescue_instruction)}
    res = {'language': p.language, 'days': out, 'instructions': texts}
    s['facts_schedule'] = res
    return res

def verify_draft(draft: str, tool_context: ToolContext, kind: str = 'plan') -> dict:
    '''Deterministically check a draft against tool facts: mg and mL values, clock times, citations, disclaimer. kind is plan or passport.'''
    s = tool_context.state
    low = draft.lower()
    allowed, vols = set(), set()
    for d in (s.get('facts_doses') or {}).get('doses', []):
        for k in ('dose_mg', 'max_dose_mg', 'dose_per_unit', 'actual_dose_mg'):
            if d.get(k) is not None:
                allowed.add(round(float(d[k]), 2))
        if d.get('volume_ml') is not None:
            vols.add(round(float(d['volume_ml']), 2))
    bad = sorted({round(float(x), 2) for x in re.findall('([0-9]+(?:[.][0-9]+)?)[ ]*mg', low)} - allowed)
    bad_ml = sorted({round(float(x), 2) for x in re.findall('([0-9]+(?:[.][0-9]+)?)[ ]*ml', low)} - vols)
    times = {x['time'] for day in (s.get('facts_schedule') or {}).get('days', []) for x in day['doses']}
    bad_times = sorted(set(re.findall('[0-9][0-9]:[0-9][0-9]', draft)) - times) if kind == 'passport' else []
    known = {e['id'] for e in (s.get('facts_evidence') or [])}
    cited = set(re.findall('[[](S[0-9]+)[]]', draft))
    unknown_cites = sorted(cited - known) if kind == 'plan' else []
    disclaimer = ('clinician review' in low) if kind == 'plan' else True
    ok = not bad and not bad_ml and not bad_times and not unknown_cites and disclaimer
    return {'unsupported_mg_values': bad, 'unsupported_ml_values': bad_ml, 'unsupported_times': bad_times,
            'unknown_citations': unknown_cites, 'has_disclaimer': disclaimer, 'ok': ok}
```

**Acceptance:** with `ALLOW_UNVERIFIED=1`, calling `classify_regimen`, `build_plan`, `compute_doses`, `check_interactions` and `build_schedule` in order on preset A (Phase 5) returns the label HIGH RISK (HEC), a plan containing ondansetron, aprepitant and dexamethasone, BSA 0.894, an ondansetron PO volume of 5.5 mL, and a schedule covering days 1 to 7 (chemo days 1 to 5, then two recovery days). The tests in Phase 9 check the same facts.

## Phase 4: guideline retrieval

`almesis_agent/guidelines.py`. The local backend searches PDF pages by keyword and gives page-level citations offline. The Vertex backend uses Vertex AI Search extractive segments; inspect the real response and adapt field names if they differ. Every hit carries `source_type`: `hospital` when the file name starts with `uza_`, otherwise `external`.

```python
import functools, glob, os, re
from google.adk.tools import ToolContext

def _type(name):
    return 'hospital' if os.path.basename(str(name or '')).lower().startswith('uza_') else 'external'

@functools.lru_cache(maxsize=1)
def _pages():
    from pypdf import PdfReader
    out = []
    pattern = os.path.join(os.path.dirname(__file__), '..', 'data', 'guidelines', '*.pdf')
    for f in glob.glob(pattern):
        for i, pg in enumerate(PdfReader(f).pages, start=1):
            out.append((os.path.basename(f), i, pg.extract_text() or ''))
    return out

def _local(query, k=5):
    terms = [t for t in re.findall('[a-z0-9]+', query.lower()) if len(t) > 2]
    scored = []
    for f, n, text in _pages():
        low = text.lower()
        s = sum(low.count(t) for t in terms)
        if s:
            i = max(low.find(terms[0]), 0)
            scored.append((s, {'title': f, 'uri': f, 'page': n, 'source_type': _type(f), 'snippet': text[max(i - 150, 0): i + 450]}))
    return [h for _, h in sorted(scored, key=lambda x: -x[0])[:k]]

def _vertex(query, k=5):
    from google.api_core.client_options import ClientOptions
    from google.cloud import discoveryengine_v1 as de
    client = de.SearchServiceClient(client_options=ClientOptions(api_endpoint='eu-discoveryengine.googleapis.com'))
    sc = ('projects/' + os.environ['GOOGLE_CLOUD_PROJECT'] + '/locations/eu/collections/default_collection/dataStores/'
          + os.environ['DISCOVERY_DATASTORE'] + '/servingConfigs/default_config')
    CS = de.SearchRequest.ContentSearchSpec
    req = de.SearchRequest(serving_config=sc, query=query, page_size=k, content_search_spec=CS(
        snippet_spec=CS.SnippetSpec(return_snippet=True),
        extractive_content_spec=CS.ExtractiveContentSpec(max_extractive_segment_count=1)))
    hits = []
    for r in client.search(req).results:
        d = r.document.derived_struct_data
        seg = (d.get('extractive_segments') or [{}])[0]
        hits.append({'title': d.get('title'), 'uri': d.get('link'), 'page': seg.get('pageNumber'),
                     'source_type': _type(d.get('link') or d.get('title')), 'snippet': (seg.get('content') or '')[:600]})
    return hits

def search_guidelines(query: str, tool_context: ToolContext) -> dict:
    '''Search the hospital policy and pediatric CINV guideline documents. Returns passages with ids S1, S2, page numbers and source_type.'''
    hits = _vertex(query) if os.getenv('GUIDELINE_BACKEND') == 'vertex' else _local(query)
    ev = list(tool_context.state.get('facts_evidence') or [])
    for h in hits:
        h['id'] = 'S' + str(len(ev) + 1)
        ev.append(h)
    tool_context.state['facts_evidence'] = ev
    return {'passages': hits}
```

**Acceptance:** with a PDF in `data/guidelines/`, a test call to `_local('dexamethasone delayed nausea children')` returns at least one hit with a page number. A file named `uza_...pdf` produces hits with `source_type` `hospital`.

## Phase 5: ADK agents and presets

`almesis_agent/presets.py` (synthetic demo patients; preset A is a multi-day cisplatin regimen like the brief, preset C uses the Dutch passport):

```python
A = {'age_years': 7, 'weight_kg': 24, 'height_cm': 120,
     'regimen': [{'drug': 'cisplatin', 'dose_mg_m2': 20, 'days': [1, 2, 3, 4, 5]}],
     'current_meds': [], 'prior_cinv': False, 'language': 'en'}
PRESETS = {
    'A: cisplatin days 1-5, 7y, 24 kg': A,
    'B: A plus voriconazole': {**A, 'current_meds': ['voriconazole']},
    'C: carboplatin, 4y, 16 kg, prior CINV, Dutch': {'age_years': 4, 'weight_kg': 16, 'height_cm': 100,
        'regimen': [{'drug': 'carboplatin', 'dose_mg_m2': None, 'days': [1]}],
        'current_meds': [], 'prior_cinv': True, 'language': 'nl'},
}
```

`almesis_agent/agent.py`:

```python
import os
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from .guidelines import search_guidelines
from .models import Patient
from .tools import (build_plan, build_schedule, check_interactions, classify_regimen,
                    compute_doses, verify_draft)

FAST = os.getenv('MODEL_FAST', 'gemini-2.5-flash')
PRO = os.getenv('MODEL_PRO', 'gemini-2.5-pro')
FACTS = ('facts_risk', 'facts_plan', 'facts_doses', 'facts_interactions', 'facts_schedule')

def init_state(callback_context):
    st = callback_context.state
    parts = callback_context.user_content.parts if callback_context.user_content else []
    text = ''.join(p.text or '' for p in parts)
    try:
        st['patient'] = Patient.model_validate_json(text).model_dump()
        for k in FACTS:
            st[k] = {}
        st['facts_evidence'] = []
    except Exception as e:
        if not st.get('patient'):
            raise ValueError('First message must be valid patient JSON: ' + str(e))

SYNTH = (
    'You write pediatric chemotherapy-induced nausea and vomiting decision support for clinicians. '
    'Use ONLY these facts. Patient: {patient}. Risk: {facts_risk}. Plan: {facts_plan}. Doses: {facts_doses}. '
    'Interactions: {facts_interactions}. Evidence passages: {facts_evidence}. '
    'Write markdown with sections: Risk level and why (use the label field); Proposed antiemetic plan '
    '(table: drug, role, route, dose mg, volume mL, source); Guideline cross-check; Interaction alerts; Evidence; Items needing clinician review. '
    'Guideline cross-check: report the hospital policy (UZA) recommendation first, then say whether POGO matches '
    '(guideline_match.status) and name any difference. '
    'Rules: copy every number exactly from the Doses facts and never calculate; if a dose is null, a rounding_ok value is false, '
    'or a source row is unverified, say so; end each guideline-derived statement with its passage id such as [S1]; '
    'if unknown_drugs is not empty, say the risk may be understated; '
    'the last line must be: Decision support only. Requires clinician review.'
)

GUARD = (
    'Call verify_draft with the full text of this draft as the draft argument: {draft_plan}. '
    'If ok is true, output the draft unchanged. If ok is false, output a corrected version: delete every sentence containing an '
    'unsupported mg or mL value or unknown citation, make sure the last line is: Decision support only. Requires clinician review. '
    'and begin with the line: Guardrail edited this answer. Output only the answer.'
)

PASSPORT = (
    'Schedule facts: {facts_schedule}. Write a parent-friendly medicine passport in the language given by the language field '
    '(en English, nl Dutch, fr French). Use only these facts. One section per day, titled Day 1, Day 2 and so on, with a table: '
    'time, medicine, amount in mL. Use the instruction and rescue texts from the instructions field word for word; '
    'if a text is missing write: Ask your care team. Show volumes in mL only, never mg. Add no medical advice of your own. Use simple words.'
)

PGUARD = (
    'Call verify_draft with the draft argument set to the full text of this passport: {draft_passport}, and kind set to passport. '
    'If ok is true, output the passport unchanged. If ok is false, delete every line containing an unsupported value and begin '
    'with the line: Guardrail edited this answer. Output only the passport.'
)

risk_agent = LlmAgent(name='risk_agent', model=FAST, tools=[classify_regimen], output_key='risk_summary',
    instruction='Call classify_regimen with no arguments, then reply with one sentence giving the label and any unknown drugs. Add no other facts.')
plan_agent = LlmAgent(name='plan_agent', model=FAST, tools=[build_plan], output_key='plan_summary',
    instruction='Call build_plan with no arguments, then reply with one sentence listing the selected drug names and the guideline match status only.')
guideline_agent = LlmAgent(name='guideline_agent', model=FAST, tools=[search_guidelines], output_key='evidence_summary',
    instruction='Risk facts: {facts_risk}. Call search_guidelines two or three times with different queries (the hospital CINV policy for this risk level in children; delayed phase; special populations). Then list the passage ids retrieved. Never invent passages.')
interaction_agent = LlmAgent(name='interaction_agent', model=FAST, tools=[check_interactions], output_key='interaction_summary',
    instruction='Call check_interactions with no arguments, then reply with one sentence giving the number of alerts. State no doses.')
dosing_agent = LlmAgent(name='dosing_agent', model=FAST, tools=[compute_doses], output_key='dosing_summary',
    instruction='Call compute_doses with no arguments, then reply with one sentence giving the number of doses computed. State no dose numbers.')
passport_agent = LlmAgent(name='passport_agent', model=FAST, tools=[build_schedule], output_key='schedule_summary',
    instruction='Call build_schedule with no arguments, then reply with one sentence giving the number of days in the schedule.')
synthesizer = LlmAgent(name='synthesizer', model=PRO, instruction=SYNTH, output_key='draft_plan')
guardrail_agent = LlmAgent(name='guardrail_agent', model=FAST, tools=[verify_draft], instruction=GUARD, output_key='final_answer')
passport_writer = LlmAgent(name='passport_writer', model=PRO, instruction=PASSPORT, output_key='draft_passport')
passport_guardrail = LlmAgent(name='passport_guardrail', model=FAST, tools=[verify_draft], instruction=PGUARD, output_key='final_passport')

root_agent = SequentialAgent(
    name='almesis_pipeline',
    sub_agents=[risk_agent, plan_agent,
                ParallelAgent(name='evidence_and_safety', sub_agents=[guideline_agent, interaction_agent, dosing_agent]),
                passport_agent, synthesizer, guardrail_agent, passport_writer, passport_guardrail],
    before_agent_callback=init_state)
```

**Acceptance:** run `adk web` from the repo root and select `almesis_agent`. Paste `json.dumps(PRESETS['A: cisplatin days 1-5, 7y, 24 kg'])` as the message. The trace shows the agents running in order, the three parallel agents each calling their tool, a clinician report with the HEC label, a plan table with mg and mL, the guideline cross-check and the disclaimer line, and then a parent passport with one section per day (days 1 to 7) showing times and mL only.

## Phase 6: Streamlit UI

`app.py` in the repo root. One page, a sidebar for the patient, five tabs.

```python
import asyncio, json, os, time, uuid
import pandas as pd
import streamlit as st
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from almesis_agent.agent import FACTS, root_agent
from almesis_agent.presets import PRESETS
from almesis_agent.protocol import extract_protocol, save as save_extraction

APP = 'almesis'
st.set_page_config(page_title='Almesis Copilot', layout='wide')
if os.getenv('ALLOW_UNVERIFIED', '0') == '1':
    st.error('DEV MODE: clinical data is NOT clinician verified. Do not use for patients.')

def audit(record: dict):
    record['ts'] = time.time()
    try:
        from google.cloud import firestore
        firestore.Client(project=os.environ['GOOGLE_CLOUD_PROJECT']).collection('audit').add(record)
    except Exception:
        with open('audit.jsonl', 'a') as f:
            f.write(json.dumps(record, default=str) + '\n')

async def _run(patient: dict):
    svc = InMemorySessionService()
    sid = str(uuid.uuid4())
    await svc.create_session(app_name=APP, user_id='u', session_id=sid)
    runner = Runner(agent=root_agent, app_name=APP, session_service=svc)
    msg = types.Content(role='user', parts=[types.Part(text=json.dumps(patient))])
    finals, trace = {}, []
    async for ev in runner.run_async(user_id='u', session_id=sid, new_message=msg):
        for p in (ev.content.parts if ev.content else []):
            if p.function_call:
                trace.append({'agent': ev.author, 'event': 'call', 'detail': f'{p.function_call.name}({dict(p.function_call.args or {})})'})
            elif p.function_response:
                trace.append({'agent': ev.author, 'event': 'result', 'detail': str(p.function_response.response)[:300]})
            elif p.text:
                trace.append({'agent': ev.author, 'event': 'text', 'detail': p.text[:300]})
        if ev.is_final_response() and ev.content and ev.content.parts:
            finals[ev.author] = ''.join(p.text or '' for p in ev.content.parts)
    sess = await svc.get_session(app_name=APP, user_id='u', session_id=sid)
    return finals, trace, dict(sess.state)

def run(patient):
    return asyncio.run(_run(patient))

st.title('Almesis Copilot')
st.caption('Pediatric CINV decision support. Synthetic data only. Decision support only; requires clinician review.')

with st.sidebar:
    name = st.selectbox('Preset patient', list(PRESETS))
    base = PRESETS[name]
    age = st.number_input('Age (years)', 0.0, 21.0, float(base['age_years']))
    weight = st.number_input('Weight (kg)', 1.0, 150.0, float(base['weight_kg']))
    height = st.number_input('Height (cm)', 40.0, 220.0, float(base['height_cm']))
    prior = st.checkbox('Prior CINV', base['prior_cinv'])
    meds = st.text_input('Current medicines (comma separated)', ', '.join(base['current_meds']))
    lang = st.selectbox('Passport language', ['en', 'nl', 'fr'], ['en', 'nl', 'fr'].index(base['language']))
    rows = [{'drug': d['drug'], 'dose_mg_m2': d['dose_mg_m2'], 'days': ','.join(map(str, d['days']))} for d in base['regimen']]
    reg = st.data_editor(pd.DataFrame(rows), num_rows='dynamic', use_container_width=True)
    go = st.button('Generate plan', type='primary')

def build_patient():
    regimen = []
    for _, r in reg.dropna(subset=['drug']).iterrows():
        days = [int(x) for x in str(r['days']).split(',') if x.strip()] or [1]
        dose = None if pd.isna(r['dose_mg_m2']) else float(r['dose_mg_m2'])
        regimen.append({'drug': str(r['drug']).strip().lower(), 'dose_mg_m2': dose, 'days': days})
    return {'age_years': age, 'weight_kg': weight, 'height_cm': height, 'regimen': regimen,
            'current_meds': [m.strip().lower() for m in meds.split(',') if m.strip()],
            'prior_cinv': prior, 'language': lang}

if go:
    patient = build_patient()
    with st.spinner('Running the agents...'):
        try:
            finals, trace, state = run(patient)
            st.session_state['result'] = {'patient': patient, 'finals': finals, 'trace': trace, 'state': state}
            audit({'patient': patient, 'plan': finals.get('guardrail_agent'), 'passport': finals.get('guardrail_agent') and finals.get('passport_guardrail')})
        except Exception as e:
            st.session_state.pop('result', None)
            st.error(f'Run failed: {e}')

t_plan, t_pass, t_trace, t_facts, t_up = st.tabs(['Plan', 'Parent passport', 'Agent trace', 'Deterministic facts', 'Protocol upload'])
res = st.session_state.get('result')

with t_plan:
    if not res:
        st.info('Choose a preset and press Generate plan.')
    else:
        s = res['state']
        c1, c2, c3 = st.columns(3)
        c1.metric('Risk label', str(s.get('facts_risk', {}).get('label', '?')))
        c2.metric('Guideline match', str(s.get('facts_plan', {}).get('guideline_match', {}).get('status', '?')))
        c3.metric('BSA (m2)', str(s.get('facts_doses', {}).get('bsa', '?')))
        st.markdown(res['finals'].get('guardrail_agent', '_No answer returned._'))

with t_pass:
    if not res:
        st.info('Generate a plan first.')
    else:
        text = res['finals'].get('passport_guardrail', '_No passport returned._')
        st.markdown(text)
        st.download_button('Download passport (.md)', text, file_name='parent_passport.md')

with t_trace:
    if res:
        st.dataframe(pd.DataFrame(res['trace']), use_container_width=True)

with t_facts:
    if res:
        for k in FACTS:
            with st.expander(k, expanded=False):
                st.json(res['state'].get(k, {}))

with t_up:
    st.write('Upload a chemotherapy protocol PDF. Gemini extracts a draft regimen for clinician review. It is never used for dosing until a clinician verifies it.')
    f = st.file_uploader('Protocol PDF', type=['pdf'])
    if f and st.button('Extract'):
        with st.spinner('Extracting...'):
            ext = extract_protocol(f.getvalue())
        st.json(ext.model_dump())
        st.session_state['ext'] = ext
    if st.session_state.get('ext') and st.button('Save as unverified draft'):
        st.success(save_extraction(st.session_state['ext']))
```

**Acceptance:** run `streamlit run app.py`. Select preset A and press Generate plan. The Plan tab shows the metrics (risk label HEC, guideline match status, BSA 0.894) and the clinician report. The Parent passport tab shows seven day sections with times and mL only, and the download button works. Switch the passport language to nl, run again, and the headings and instruction texts come out in Dutch. The Agent trace tab lists every tool call. A row appears in `audit.jsonl` (or Firestore) for each run.

## Phase 7: Protocol extraction

`almesis_agent/protocol.py` reads an uploaded protocol PDF with Gemini and returns a structured draft regimen. The draft is always stored as unverified and is never used for dosing.

```python
import json, os
from pathlib import Path
from pydantic import BaseModel
from google import genai
from google.genai import types

class ExtractedDrug(BaseModel):
    drug: str
    dose_mg_m2: float | None = None
    days: list[int] = [1]

class ExtractedRegimen(BaseModel):
    regimen_name: str
    drugs: list[ExtractedDrug]
    notes: str = ''

PROMPT = (
    'Extract the chemotherapy regimen from this protocol. Return the regimen name and every chemotherapy drug '
    'with its dose in mg per m2 and the treatment days (day numbers). Use null if a dose is not stated. '
    'Do not guess. Put anything unclear in notes.'
)

def extract_protocol(pdf_bytes: bytes) -> ExtractedRegimen:
    client = genai.Client(vertexai=True, project=os.environ['GOOGLE_CLOUD_PROJECT'],
                          location=os.getenv('GOOGLE_CLOUD_LOCATION', 'europe-west1'))
    resp = client.models.generate_content(
        model=os.getenv('MODEL_PRO', 'gemini-2.5-pro'),
        contents=[types.Part.from_bytes(data=pdf_bytes, mime_type='application/pdf'), PROMPT],
        config=types.GenerateContentConfig(response_mime_type='application/json',
                                           response_schema=ExtractedRegimen, temperature=0))
    return ExtractedRegimen.model_validate_json(resp.text)

def save(ext: ExtractedRegimen) -> str:
    row = {'regimen_name': ext.regimen_name, 'drugs_json': json.dumps([d.model_dump() for d in ext.drugs]),
           'notes': ext.notes, 'verified': False}
    ds = os.getenv('BQ_DATASET')
    if ds:
        from google.cloud import bigquery
        bq = bigquery.Client(project=os.environ['GOOGLE_CLOUD_PROJECT'])
        errs = bq.insert_rows_json(f"{os.environ['GOOGLE_CLOUD_PROJECT']}.{ds}.regimen_extractions", [row])
        if errs:
            raise RuntimeError(str(errs))
        return 'Saved to BigQuery table regimen_extractions as unverified.'
    out = Path('data/out'); out.mkdir(parents=True, exist_ok=True)
    p = out / 'regimen_extractions.jsonl'
    with p.open('a') as f:
        f.write(json.dumps(row) + '\n')
    return f'Saved to {p} as unverified.'
```

**Acceptance:** in the Protocol upload tab, upload any synthetic one-page protocol PDF and press Extract. A JSON draft with drug names, doses and days appears. Press Save as unverified draft and see the success message. No clinical table used by the agents changes.

## Phase 8: Google Cloud setup and deployment

`setup_gcp.sh` (run once by a human with project owner rights; replace `PROJECT_ID`):

```bash
#!/usr/bin/env bash
set -euo pipefail
PROJECT_ID=${PROJECT_ID:?set PROJECT_ID}
REGION=europe-west1
gcloud config set project "$PROJECT_ID"
gcloud services enable aiplatform.googleapis.com discoveryengine.googleapis.com bigquery.googleapis.com \
  firestore.googleapis.com storage.googleapis.com run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
bq --location=EU mk -d "$PROJECT_ID:almesis" || true
gcloud firestore databases create --location=eur3 || true
gsutil mb -l EU "gs://$PROJECT_ID-almesis-guidelines" || true
gsutil cp data/guidelines/*.pdf "gs://$PROJECT_ID-almesis-guidelines/"
echo 'Next: create a Vertex AI Search data store (unstructured, location eu) from that bucket, then a search app, and put their ids in .env'
```

Then load the tables (the module is `load_bq.py`, which holds the nine schemas and loads each CSV in `data/`):

```bash
chmod +x setup_gcp.sh && PROJECT_ID=your-project ./setup_gcp.sh
python load_bq.py
```

`Dockerfile`:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=8080
CMD streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
```

Deploy to Cloud Run:

```bash
gcloud run deploy almesis-copilot --source . --region europe-west1 --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_GENAI_USE_VERTEXAI=1,GOOGLE_CLOUD_LOCATION=europe-west1,BQ_DATASET=almesis,ALLOW_UNVERIFIED=1
```

Give the Cloud Run service account the roles Vertex AI User, BigQuery Data Editor, BigQuery Job User, Discovery Engine Viewer and Cloud Datastore User. Keep `ALLOW_UNVERIFIED=1` only for the demo; the red banner stays visible.

**Acceptance:** the Cloud Run URL opens the app and preset A produces the same plan as locally.

## Phase 9: Tests, demo script and definition of done

`tests/test_tools.py` runs offline against the CSVs with `ALLOW_UNVERIFIED=1`. It uses a tiny fake `ToolContext` whose `.state` is a dict. Write one test per line below, using the fixture patient P (cisplatin 20 mg/m2 on days 1 to 5, 7 years, 24 kg, 120 cm, language en):

- `test_bsa`: BSA for 24 kg and 120 cm is 0.894 (rounded to 3 decimals).
- `test_hec_label`: cisplatin gives risk level high and label HEC.
- `test_risk_and_plan`: the plan includes a 5-HT3 antagonist, dexamethasone and aprepitant for high risk, and the first guideline source is the UZA policy.
- `test_dose_cap_by_bsa`: with weight 150 and height 200, ondansetron PO is capped at 8.0 mg.
- `test_volume_is_rounded_to_step`: every dose volume in mL is a multiple of the formulation's rounding step, and `rounding_ok` is true.
- `test_schedule_runs_past_last_chemo_day`: the schedule has entries for day 6 and 7 (delayed phase).
- `test_guideline_match_reported`: `facts_plan.guideline_match.status` is one of match, mismatch, single\_source.
- `test_every_plan_drug_has_a_schedule_row`: each drug in the plan appears in the schedule.
- `test_prior_cinv_adds_aprepitant`: preset C (carboplatin, prior CINV) includes aprepitant.
- `test_interaction_alert`: voriconazole with preset A raises an alert.
- `test_verify_draft`: a draft containing an mg value that is not in the facts fails; a draft with only fact values passes; kind=passport rejects any mg value.

Run `pytest -q`; all tests must pass before demoing.

### Demo script (4 minutes)

1. Preset A. Say: a 7-year-old on 5 days of cisplatin. Show the HEC label, then the UZA-first plan with the POGO match line.
2. Open Deterministic facts. Say: every number comes from code, not from the model.
3. Preset B (adds voriconazole). Show the interaction alert.
4. Change the weight and run again. Show the mL volumes change and still sit on the pharmacy rounding step.
5. Open Parent passport, switch the language to Dutch, and run. Show the day-by-day table with mL only.
6. Close with the guardrail: show a draft where verify\_draft removed an unsupported number, and say the data is synthetic and awaiting clinician verification.

### Stretch goals

Agent Engine deployment, Document AI for scanned protocols, a PDF export of the passport, authentication on Cloud Run (IAP).

### Definition of done

- [ ] `pytest -q` passes.
- [ ] `adk web` and `streamlit run app.py` both work with preset A.
- [ ] Plan shows HEC/MEC/LEC label, UZA-first cross-check with POGO, and mg plus mL doses.
- [ ] Passport renders for all five days plus delayed days in en, nl and fr.
- [ ] Guardrails remove unsupported numbers and citations.
- [ ] Red banner shows whenever `ALLOW_UNVERIFIED=1`.
- [ ] Cloud Run URL works.
- [ ] README states: synthetic data, decision support only, requires clinician review.
