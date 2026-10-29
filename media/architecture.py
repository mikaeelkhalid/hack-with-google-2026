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
from diagrams.gcp.storage import GCS
from diagrams.onprem.client import Users
from diagrams.programming.language import Python

OUT = Path(__file__).with_name("almesis_copilot_architecture")
OPTIONAL = {"style": "dashed", "color": "gray50"}

with Diagram(
    "Almesis Copilot (uc3-aimesis-cinv)",
    filename=str(OUT),
    show=False,
    direction="LR",
    graph_attr={"fontsize": "22", "pad": "0.4", "nodesep": "0.9", "ranksep": "1.2", "splines": "spline"},
    node_attr={"fontsize": "13"},
):
    clinician = Users("Clinician / pharmacist\n(+ parent passport)")

    with Cluster("Cloud Run · europe-west1 (agents-cli deploy)"):
        ui = Run("FastAPI\nADK web UI + A2A")

        with Cluster("ADK root_agent (single agent)"):
            agent = VertexAI("root_agent\nGemini 2.5 Flash")
            guard = Python("Guardrail callback\nchecks mg / mL / [S#]\n+ advisory label")

            tools = Python(
                "Deterministic tools (no LLM math)\n\n"
                "classify_regimen_emetogenicity\n"
                "get_pogo_guideline_recommendation\n"
                "check_ddi_interactions\n"
                "calculate_risk_adjusted_regimen\n"
                "compute_antiemetic_doses (mg → mL)\n"
                "search_guidelines (page cites)\n"
                "build_parent_passport (en/nl/fr)"
            )

        with Cluster("Bundled data (in the container)"):
            tables = Python("app/tables.py\nsource + page\nverified flag")
            pdfs = GCS("docs/ PDFs\nUZA v2 policy\nPOGO 250111")

    telemetry = Logging("Cloud Trace / Logging\n(starter telemetry)")

    with Cluster("If time allows"):
        bq = BigQuery("BigQuery data products\n(mocks DDL, EU)")
        vas = VertexAI("Vertex AI Search\n(eu)")
        extract = VertexAI("Protocol PDF extraction\n→ unverified rows")

    clinician >> ui >> agent
    agent >> tools
    agent >> guard >> Edge(xlabel="advisory answer", constraint="false") >> clinician
    tools >> tables
    tools >> pdfs
    agent >> Edge(**OPTIONAL) >> telemetry
    tables >> Edge(label="DATA_BACKEND", **OPTIONAL) >> bq
    pdfs >> Edge(label="GUIDELINE_BACKEND", **OPTIONAL) >> vas
    extract >> Edge(**OPTIONAL) >> bq
