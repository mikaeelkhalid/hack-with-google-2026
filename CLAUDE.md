# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Almesis Copilot: hackathon entry for "Solve with Google: BSPHO 2026", Use Case 3 (pediatric chemotherapy-induced nausea & vomiting decision support, clinical partner UZA).

The organizers provided a starter project in `uc3-aimesis-cinv/` (agents-cli 1.5.0 ADK template, Cloud Run target, A2A enabled). **All app code lives there; build on it, don't start a parallel codebase.** Before designing anything read:

- `uc3-aimesis-cinv/.agents-cli-spec.md` — the agent spec (single `root_agent` + deterministic tools).
- `uc3-aimesis-cinv/app/` — `agent.py`, `tables.py`, `dosing.py`, `guidelines.py`, `passport.py`, `guardrail.py`.
- `uc3-aimesis-cinv/GEMINI.md` — agents-cli workflow (eval loop, deploy needs explicit human approval) and workshop assets index.
- `almesis-copilot.md` (diagram: `media/almesis_copilot_architecture.png`) — unified product plan, clinical spec, and phased build guide (regenerate the diagram with `uv run --with diagrams python media/architecture.py`).

## Commands (run inside `uc3-aimesis-cinv/`)

- `agents-cli install` — install deps (uv). Run Python with `uv run`, never bare `pip`.
- `agents-cli playground` — local web UI, auto-reloads.
- `uv run pytest tests/unit tests/integration` — tests. `agents-cli lint` — ruff/ty/codespell.
- `agents-cli eval run` — eval loop over `tests/eval/datasets/`.
- `agents-cli deploy` — Cloud Run. Only after the user explicitly approves.

## Clinical safety rules (non-negotiable)

- The LLM never does dose math. Doses are computed in plain code from clinician-verified tables.
- Every fact row carries a `verified` flag; LLM-extracted data (e.g. from uploaded protocol PDFs) is stored as unverified until a clinician approves it.
- Every clinical claim cites a guideline passage with page number.
- Every recommendation ends with the advisory label. The starter uses `ADVISORY_LABEL = "Advisory Only — Requires Clinician Sign-Off"` in `app/agent.py`; keep that single constant as the source of truth.
- Synthetic patients only. Never add real patient data anywhere.
- Rule priority: UZA July 2026 v2 policy first; POGO 250111 is the cross-check. For risk/dose/interaction logic, use the `cinv-rules` skill.

## GCP

All resources in `europe-west1` (zone `europe-west1-b`). Never create resources elsewhere or use multi-region/US defaults. Exception: `GOOGLE_CLOUD_LOCATION=global` is the Gemini model endpoint (not a resource); per `GEMINI.md`, fix model 404s via location, never by changing the model.

## Repo

- Organizer reference material, read-only — never edit: `uc3-aimesis-cinv/codelabs/`, `uc3-aimesis-cinv/docs/` (clinical PDFs/docx/pptx, partly Dutch). `uc3-aimesis-cinv/docs/` is the canonical copy of the source documents.
- Asset filenames contain spaces (some have a trailing space before `.pptx`); always quote paths.
- Solo project: commit directly to `main`, no branches/PRs.
