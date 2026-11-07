"""Almesis Copilot architecture diagram (aligned with uc3-aimesis-quickstart.lab.md & BUILD_SPEC).

Regenerate from the repo root (needs graphviz: `brew install graphviz`):
    uv run --with diagrams python media/architecture.py
"""

from pathlib import Path

from diagrams import Cluster, Diagram, Edge
from diagrams.gcp.analytics import BigQuery
from diagrams.gcp.compute import Run
from diagrams.gcp.ml import VertexAI
from diagrams.gcp.operations import Logging
from diagrams.generic.storage import Storage
from diagrams.onprem.client import Users
from diagrams.programming.language import Python

OUT = Path(__file__).with_name("almesis_copilot_architecture")
OPTIONAL = {"style": "dashed", "color": "gray50"}
# Tall node with extra vertical room so multi-line tool list sits cleanly below the Python icon.
TALL = {
    "height": "5.0",
    "width": "4.5",
    "imagepos": "tc",
    "labelloc": "b",
    "imagescale": "false",
}
MED = {
    "height": "3.4",
    "width": "3.2",
    "imagepos": "tc",
    "labelloc": "b",
    "imagescale": "false",
}

with Diagram(
    "Almesis Copilot (uc3-aimesis-cinv — UZA Policy v2 & POGO 250111)",
    filename=str(OUT),
    show=False,
    direction="LR",
    graph_attr={
        "fontsize": "20",
        "pad": "0.4",
        "nodesep": "0.75",
        "ranksep": "1.1",
        "splines": "spline",
    },
    node_attr={"fontsize": "12"},
):
    clinician = Users(
        "Clinician / Pharmacist\n+ Parent Passport (NL/FR/EN)\n& Companion App"
    )

    with Cluster("Cloud Run · europe-west1 (agents-cli deploy)"):
        ui = Run("FastAPI\nADK Web UI + A2A")

        with Cluster("ADK App (uc3_aimesis_cinv)"):
            agent = Python("root_agent\n(single LlmAgent)")
            tools = Python(
                "Deterministic Tools (Zero LLM Math)\n\n"
                "1. classify_regimen_emetogenicity\n"
                "   (UZA v2 dose thresholds + IE/combo rules)\n"
                "2. get_pogo_guideline_recommendation\n"
                "   (UZA v2 first vs. POGO 250111 diff)\n"
                "3. check_ddi_interactions\n"
                "   (CYP3A4 Vinca/Azole/NK1 + QTc score)\n"
                "4. calculate_risk_adjusted_regimen\n"
                "   (GEEN Dexa block + Casus 1–3 rules)\n"
                "5. compute_antiemetic_doses\n"
                "   (BSA/kg, Olanzapine 0.5mg floor, mg→mL)\n"
                "6. search_guidelines (page cites [S#])\n"
                "7. build_parent_passport (NL/FR/EN + BE links)",
                **TALL,
            )
            guard = Python(
                "Guardrail Callback\n(after_model_callback)\nchecks mg / mL / [S#]\n+ ADVISORY_LABEL",
                **MED,
            )

        with Cluster("Bundled Clinical Data (in container)"):
            tables = Python(
                "app/tables.py\nUZA v2 p.1–2 & POGO rules\nCasus 1–3 & BE resources\nsource + page + verified flag",
                **MED,
            )
            pdfs = Storage(
                "docs/ Corpus (Read-Only)\nAnti-emetica beleid CINV - V2.pdf\nPOGO 250111 Guideline PDF\ncasus voorbeelden.docx",
                **MED,
            )

    gemini = VertexAI("Gemini 2.5 Flash\nVertex AI (global endpoint)")
    telemetry = Logging("Cloud Trace / Logging\n(audit trail & tool traces)")

    with Cluster("Optional Cloud Data Products (europe-west1)"):
        extract = VertexAI("Protocol PDF Extraction\n→ unverified rows")
        bq = BigQuery(
            "BigQuery Data Products\n(europe-west1)",
            height="2.7",
            width="2.6",
            imagepos="tc",
            labelloc="b",
            imagescale="false",
        )
        vas = VertexAI("Vertex AI Search")

    clinician >> Edge(label="case / passport", dir="both") >> ui
    ui >> Edge(dir="both") >> agent
    agent >> Edge(label="reasoning", dir="both") >> gemini
    agent >> Edge(label="tool calls", dir="both") >> tools
    tools >> tables
    tools >> pdfs
    agent >> Edge(label="draft text") >> guard
    guard >> Edge(label="verified answer", constraint="false") >> ui
    agent >> telemetry
    tables >> Edge(label="DATA_BACKEND", **OPTIONAL) >> bq
    pdfs >> Edge(label="GUIDELINE_BACKEND", **OPTIONAL) >> vas
    extract >> Edge(**OPTIONAL) >> bq
