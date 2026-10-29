# Coding Agent Guide

## Prerequisites

Install the CLI (one-time):
```bash
uv tool install google-agents-cli
```

---

## Development Phases

### Phase 1: Understand Requirements
Before writing any code, understand the project's requirements, constraints, and success criteria.

### Phase 2: Build and Implement
Implement agent logic in `app/`. Use `agents-cli playground` for interactive testing. Iterate based on user feedback.

### Phase 3: The Evaluation Loop (Main Iteration Phase)
Start with 1-2 eval cases, run `agents-cli eval run`, iterate by making changes and rerunning it until satisfied. Expect 5-10+ iterations. Once you have a baseline, reach for `agents-cli eval compare` (regression diffs), `agents-cli eval analyze` (cluster failure modes), and `agents-cli eval optimize` (auto-tune prompts). See the **Evaluation Guide** for metrics, dataset schema, LLM-as-judge config, and common gotchas.

### Phase 4: Pre-Deployment Tests
Run `uv run pytest tests/unit tests/integration`. Fix issues until all tests pass.

### Phase 5: Deploy to Dev
**Requires explicit human approval.** Run `agents-cli deploy` only after user confirms. See the **Deployment Guide** for details.

### Phase 6: Production Deployment
Ask the user: Option A (simple single-project) or Option B (full CI/CD pipeline with `agents-cli infra cicd`).

## Development Commands

| Command | Purpose |
|---------|---------|
| `agents-cli playground` | Interactive local testing |
| `uv run pytest tests/unit tests/integration` | Run unit and integration tests |
| `agents-cli eval dataset synthesize` | Synthesize multi-turn eval scenarios for your agent |
| `agents-cli eval run` | Run the agent over the eval dataset and grade the traces |
| `agents-cli eval generate` / `agents-cli eval grade` | Decoupled form: produce traces, then grade them |
| `agents-cli eval compare` | Compare two grade-results files (regression check) |
| `agents-cli eval analyze` | Cluster failure modes from grade results |
| `agents-cli eval metric list` | List built-in metrics available in the SDK |
| `agents-cli eval optimize` | Auto-tune agent prompts using eval data |
| `agents-cli lint` | Check code quality |
| `agents-cli infra single-project` | Set up project infrastructure (Terraform) |
| `agents-cli deploy` | Deploy to dev |
| `agents-cli scaffold enhance` | Add deployment target or CI/CD to project |
| `agents-cli scaffold upgrade` | Upgrade project to latest version |

---

## Operational Guidelines for Coding Agents

- **Code preservation**: Only modify code directly targeted by the user's request. Preserve all surrounding code, config values (e.g., `model`), comments, and formatting.
- **NEVER change the model** unless explicitly asked.
- **Model 404 errors**: Fix `GOOGLE_CLOUD_LOCATION` (e.g., `global` instead of `europe-west1`), not the model name.
- **ADK tool imports**: Import the tool instance, not the module: `from google.adk.tools.load_web_page import load_web_page`
- **Run Python with `uv`**: `uv run python script.py`. Run `agents-cli install` first.
- **Stop on repeated errors**: If the same error appears 3+ times, fix the root cause instead of retrying.
- **Terraform conflicts** (Error 409): Use `terraform import` instead of retrying creation.

# Dispatched Workshop Assets (`gs://swg-workshop` & `AImesis latest` Drive -> UC3)
- **Clinical Leads**: **Katleen Balliauw & Anthe De Pauw** (Hospital Pharmacists, University Hospital Antwerp / UZA)
- **Google Cloud CE POC**: **Payam Ebrahimi** (`@payame`)
- **Codelab & Guide (`codelabs/`)**:
  - `codelabs/uc3-aimesis-quickstart.lab.md` & `codelabs/index.html`
  - `codelabs/guide.html` & `codelabs/img/`
- **Clinical Docs, UZA Policy, POGO Guideline & Case Examples Corpus (`docs/`)**:
  - `docs/Anti-emetica beleid CINV - V2.pdf`: Official UZA Pediatric Oncology CINV Prophylaxis & Breakthrough Policy (July 2026 v2)
  - `docs/POGO Emetogenicity Classification Guideline Final-rev- 250111.pdf`: Official 87-page POGO Acute Emetogenic Potential Guideline (Final-rev-250111)
  - `docs/casus voorbeelden.docx`: 3 official UZA clinical case examples (**Casus 1**: 16yo HR-NBL2 RAPID COJEC Cycle B4; **Casus 2**: 2yo ALLTogether1 Induction B Day 8; **Casus 3**: iEuroEwing 5-day IE Cycle #3)
  - `docs/user stories AImesis version 2.pdf`: 6 official clinical user stories (Stories 1–6)
  - `docs/AImesis_pediatric CINVcontrol clinical decision support .pptx`: Updated 9-slide clinical briefing deck (Katleen Balliauw & Anthe De Pauw, UZA)
  - `docs/Pitch slides AImesis versie 2 .pptx`: Main-stage pitch slide (`Every child with cancer deserves comfort!`)
  - `docs/CINV resources in Belgium.xlsx`: Curated Belgian pediatric oncology family resources (`UZ Gent`, `UZ Leuven`, `UZA`, `HUDERF`, `Stichting tegen Kanker`)
- **Mocks & Fixtures (`mocks/`)**:
  - `mocks/fixtures/` & `mocks/data_products/`: UC3 fixtures and data products
