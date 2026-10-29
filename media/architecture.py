"""Almesis Copilot architecture diagram (BUILD_SPEC rev 2).

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
# Tall node so the multi-line label sits inside the node instead of under arrows.
TALL = {"height": "3.6", "width": "3.4", "imagepos": "tc", "labelloc": "b", "imagescale": "false"}

with Diagram(
    "Almesis Copilot (uc3-aimesis-cinv)",
    filename=str(OUT),
    show=False,
    direction="LR",
    graph_attr={"fontsize": "22", "pad": "0.4", "nodesep": "0.7", "ranksep": "1.0", "splines": "spline"},
    node_attr={"fontsize": "13"},
):
    clinician = Users("Clinician / pharmacist\n(+ parent passport)")

    with Cluster("Cloud Run · europe-west1 (agents-cli deploy)"):
        ui = Run("FastAPI\nADK web UI + A2A")

        with Cluster("ADK app"):
            agent = Python("root_agent\n(single LlmAgent)")
            tools = Python(
                "Deterministic tools\n(no LLM math)\n\n"
                "classify_regimen_emetogenicity\n"
                "get_pogo_guideline_recommendation\n"
                "check_ddi_interactions\n"
                "calculate_risk_adjusted_regimen\n"
                "compute_antiemetic_doses (mg → mL)\n"
                "search_guidelines (page cites)\n"
                "build_parent_passport (en/nl/fr)",
                **TALL,
            )
            guard = Python("Guardrail callback\nchecks mg / mL / [S#]\n+ advisory label")

        with Cluster("Bundled data (in the container)"):
            tables = Python("app/tables.py\nsource + page\nverified flag")
            pdfs = Storage("docs/ PDFs\nUZA v2 policy\nPOGO 250111")

    gemini = VertexAI("Gemini 2.5 Flash\nVertex AI (global endpoint)")
    telemetry = Logging("Cloud Trace / Logging\n(built into starter)")

    with Cluster("If time allows"):
        extract = VertexAI("Protocol PDF extraction\n→ unverified rows")
        bq = BigQuery("BigQuery data products\n(europe-west1)")
        vas = VertexAI("Vertex AI Search")

    clinician >> Edge(label="question / answer", dir="both") >> ui
    ui >> Edge(dir="both") >> agent
    agent >> Edge(label="reasoning", dir="both") >> gemini
    agent >> Edge(label="tool calls", dir="both") >> tools
    tools >> tables
    tools >> pdfs
    agent >> Edge(label="final text") >> guard
    guard >> Edge(label="checked answer", constraint="false") >> ui
    agent >> telemetry
    tables >> Edge(label="DATA_BACKEND", **OPTIONAL) >> bq
    pdfs >> Edge(label="GUIDELINE_BACKEND", **OPTIONAL) >> vas
    extract >> Edge(**OPTIONAL) >> bq
