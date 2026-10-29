# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Almesis Copilot: hackathon entry for "Solve with Google: BSPHO 2026", Use Case 3 (pediatric chemotherapy-induced nausea & vomiting decision support, clinical partner UZA). Built from scratch in this repo with Python + Google ADK. The plan and architecture live in `almesis-copilot.md` (diagram: `media/almesis_copilot_architecture_v2.png`) — read it before designing anything.

## Clinical safety rules (non-negotiable)

- The LLM never does dose math. Doses are computed in plain code from clinician-verified tables.
- Every fact row carries a `verified` flag; LLM-extracted data (e.g. from uploaded protocol PDFs) is stored as unverified until a clinician approves it.
- Every clinical claim cites a guideline passage with page number.
- Every recommendation output ends with: "Decision support only. Requires clinician review."
- Synthetic patients only. Never add real patient data anywhere.
- Rule priority: UZA July 2026 v2 policy first; POGO 250111 is the cross-check. For risk/dose/interaction logic, use the `cinv-rules` skill.

## GCP

All resources in `europe-west1` (zone `europe-west1-b`). Never create resources elsewhere or use multi-region/US defaults.

## Repo

- `codelabs/` and `usecase/` are organizer reference material (identical copies; `usecase/` has one extra pptx). Read-only — never edit. Source docs are partly in Dutch.
- Asset filenames contain spaces (some have a trailing space before `.pptx`); always quote paths.
- Solo project: commit directly to `main`, no branches/PRs.
