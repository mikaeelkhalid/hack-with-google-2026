# Almesis Copilot 

A guide to the whole project: what it is, how it works, and how to pitch it.

## The idea in one sentence

A clinician types in a child's chemotherapy and basic details, and Almesis Copilot answers: how likely is this treatment to make the child sick, which anti-sickness medicines are recommended, what dose, whether any of the child's other medicines clash with them, and which guideline says so.

## The problem it solves

Chemotherapy often causes nausea and vomiting (CINV). Doctors prevent it with anti-sickness medicines, but choosing the right ones for a child is hard:

- Every chemotherapy drug makes people sick to a different degree.
- Children need doses based on weight or body size, so adults' numbers do not work.
- The anti-sickness medicines can clash with other medicines the child takes.
- The guidelines are long documents, and the information is scattered.

Today, clinicians search these documents by hand. Almesis puts it all in one place, in seconds, with the source shown.

## Think of it as one expert with a toolbox

We keep the organizers' design: one AI assistant (an ADK agent on Gemini 2.5 Flash) with a set of exact tools. The assistant decides which tool to use and explains the results; the tools do the real work in plain code.

| Tool                                | What it does in plain words                                                       |
| ----------------------------------- | --------------------------------------------------------------------------------- |
| `classify_regimen_emetogenicity`    | Looks up the chemotherapy and says: minimal, low, moderate or high chance of sickness |
| `get_pogo_guideline_recommendation` | Picks the anti-sickness medicines for that risk and the child's age               |
| `check_ddi_interactions`            | Checks the child's other medicines for dangerous clashes                          |
| `calculate_risk_adjusted_regimen`   | Adjusts for this child: earlier nausea, anxiety, no steroids in ALL, and so on    |
| `compute_antiemetic_doses`          | Calculates the dose from weight and body size, then the amount in mL              |
| `search_guidelines`                 | Searches the UZA policy and POGO guideline and brings back passages with page numbers |
| `build_parent_passport`             | Builds the day-by-day medicine card for parents                                   |

A final check (the guardrail) runs on every answer before the clinician sees it.

## What happens when you press the button

1. The clinician types the child's age, weight, height, chemotherapy, other medicines, and whether the child had CINV before.
2. The assistant calls the tools in order: risk, recommended medicines, clashes, adjustments for this child, doses, guideline passages.
3. It writes one short answer: UZA policy first, POGO as the cross-check, a dose table, warnings and sources with page numbers.
4. The guardrail checks the answer. Any dose, amount or source that no tool produced is removed.
5. The screen shows the answer plus a trace of every tool call.

## Why it is safe (the most important part)

Medicine is high stakes, so the design follows four rules:

- **AI never does the math.** Doses are calculated by normal code. The AI only explains the result.
- **Facts come from tables, not from the AI's memory.** Risk levels, plans, doses and interactions live in a database that a clinician checks.
- **Everything has a source.** Each claim points to a guideline passage with a page number.
- **Unchecked data is blocked.** Every table row has a verified flag. Rows nobody has checked are not used in a real setting.

The result always ends with: Advisory Only — Requires Clinician Sign-Off. The tool helps the doctor; it does not replace the doctor.

## The Google Cloud Architecure

| Google service              | What it does here                                                  |
| --------------------------- | ------------------------------------------------------------------ |
| Gemini 2.5 Flash (on Vertex AI) | The AI that understands the question, picks tools and writes the answer |
| ADK (Agent Development Kit)     | Connects Gemini to the tools and the guardrail                          |
| Cloud Run                       | Hosts the app (web UI and A2A API) so anyone can open it with a link    |
| Cloud Trace / Logging           | Records every run and tool call                                         |
| BigQuery, Vertex AI Search      | If time allows: rule tables and guideline search as managed services    |

Everything runs in `europe-west1`, which matters for Belgian hospitals.

![Alt text](media/almesis_copilot_architecture.png)

## The bonus feature: reading protocols

If time allows: a user can upload a long clinical trial protocol PDF. Gemini reads it and pulls out the chemotherapy drugs, doses, and the page and sentence each came from. These are saved as unchecked rows, and a clinician approves them before they are used. This builds the structured database the challenge asks for.

## The 3-minute demo story

1. **Enter a child (cisplatin, 7 years, 24 kg).** The screen shows high risk, a medicine plan, and sources with page numbers.
2. **Add a medicine that clashes (voriconazole).** A warning appears.
3. **Change the weight.** The doses change, and you can show the exact formula. Say: the AI never does the math.
4. **Switch the parent passport to Dutch.** A day-by-day card with amounts in mL only.
5. **Close with safety.** Guardrail, sources, clinician review, European data.

## Lines you can use with the judges

- One focused product, not four shallow ones: the other use cases (protocol search, Pediatric Prescriber) can reuse the same tools.
- Built so a clinician can check every claim, which is what makes it usable in a hospital.
- Uses the full Google stack for real reasons: Gemini, ADK, Cloud Run, with BigQuery and Vertex AI Search as next steps.
- Safety by design: calculations in code, citations, a guardrail and a verification flag.

## Honest limits to mention

- Only made-up patients are used.
- The sample tables are placeholders until a clinician checks them against the guidelines.
- It is a decision-support prototype, not a medical device.

## Mini glossary

- **CINV:** chemotherapy-induced nausea and vomiting.
- **Emetogenicity:** how likely a drug is to cause vomiting.
- **Agent:** an AI helper that uses tools to do its job.
- **RAG:** the AI first searches documents, then answers using what it found.
- **Guardrail:** a final check that blocks wrong or unsupported answers.
- **BSA:** body surface area, a body-size number used to dose children.
- **ADK:** Google's toolkit for building agents.

## The organizers' brief

The organizers showed four steps for this use case. Here is how our solution lines up, in simple words.

| Their step                         | What our app does                                                                                                                  |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| 1. Emetic risk tiering             | Sorts the chemotherapy into HIGH (HEC), MODERATE (MEC) or LOW (LEC) risk, including regimens that run for several days             |
| 2. Cross-check hospital guidelines | Uses the UZA July 2026 policy first, compares it with the POGO guideline, and shows a guideline match or mismatch badge            |
| 3. Check patient characteristics   | Uses age, weight, body surface area and earlier nausea to fit the dose to the child and round it to a practical amount in mL       |
| 4. Antiemetic passport for parents | A day-by-day card for days at home: times, medicine, amount in mL, and clinician-written instructions, in English, Dutch or French |

The passport is built by a tool from the calculated schedule. It copies the instruction and rescue texts that a clinician wrote and never invents medical advice; the guardrail checks every time and amount on it.

The new demo ending: change the child's weight, watch the mL amount change, then switch the passport to Dutch.
