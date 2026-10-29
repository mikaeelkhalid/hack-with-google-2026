---
name: cinv-rules
description: UZA v2 / POGO pediatric CINV clinical rules (emetogenicity risk, antiemetic dosing, hard contraindications, drug interactions) and the Casus 1-3 reference cases. Use when writing or reviewing risk classification, dose calculation, interaction screening, guardrails, or test cases for Almesis.
---

Source of truth: `codelabs/uc3-aimesis-quickstart.lab.md` (read-only). Read its sections 1 (stories + Casus 1–3 table), 3 (risk/dosing/GEEN Dexamethasone) and 5 (negative safety tests) before changing clinical logic. Underlying PDFs/docx are in `codelabs/assets/` (quote paths — spaces in names). UZA July 2026 v2 policy wins; POGO 250111 is the cross-check.

## Rules to enforce in code (not in the LLM)

**Risk (acute emetogenicity: Minimal / Low / Moderate / High)**
- Dose-dependent High: Cyclophosphamide >1500 mg/m², Cytarabine ≥3 g/m², MTX ≥12 g/m².
- Carboplatin and Doxorubicin = High under UZA.
- Combination escalation: Ifosfamide (MEC) + Etoposide (LEC) → HEC.

**Dosing**
- Ondansetron 5 mg/m², max 8 mg.
- Olanzapine 0.1 mg/kg, rounded DOWN to nearest 0.5 mg.
- Dexamethasone dose split at BSA 0.6 m²; show IV Aacidexam 5 mg/mL ≈ 4 mg/mL active base alert; reduce 50% with Aprepitant (CYP3A4).
- Never combine Palonosetron with Ondansetron within 3 days.

**Hard blocks — "GEEN Dexamethasone"**
- ALL, brain tumors (`hersentumoren`), Dinutuximab beta, steroid-containing chemo regimens.

**Interactions to flag**
- Voriconazole/Posaconazole + Vincristine (CYP3A4).
- Cumulative QTc: Ondansetron + Domperidone/Haloperidol.

## Reference cases

Casus 1–3 in the lab.md table have expected outputs — use them as regression tests for any change to risk, dosing or guardrail logic. Also cover the demo path: Cisplatin, 7 y, 24 kg → add Voriconazole (interaction warning) → change weight (doses update).
