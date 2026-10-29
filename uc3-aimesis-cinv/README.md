# uc3-aimesis-cinv

Simple ReAct agent
Agent generated with `agents-cli` version `1.5.0`

## Project Structure

```
uc3-aimesis-cinv/
├── app/                       # Core agent code
│   ├── streamlit_app.py       # Interactive multilingual (NL/FR/EN) Clinical & Parent Passport UI
│   ├── agent.py               # Single root_agent (gemini-2.5-flash) & 7 tools
│   ├── tables.py              # Verifiable clinical tables (UZA v2 + POGO 250111)
│   ├── dosing.py              # Deterministic BSA, mg, rounding & mL dosing
│   ├── guidelines.py          # Page-cited PDF guideline search
│   ├── passport.py            # Multilingual (en/nl/fr) parent passport & PDF export
│   ├── guardrail.py           # Deterministic after_model_callback guardrail
│   ├── fast_api_app.py        # FastAPI Backend server + Streamlit UI proxy + ADK Web UI & A2A
│   └── app_utils/             # A2A and telemetry helpers
├── codelabs/                  # Official workshop codelab & guide
├── docs/                      # Canonical UZA CINV v2 & POGO 250111 PDFs + casus
├── tests/                     # Unit, integration, and eval tests
├── GEMINI.md                  # AI-assisted development guide
└── pyproject.toml             # Project dependencies
```

> 💡 **Tip:** Use [Antigravity CLI](https://antigravity.google/) for AI-assisted development - project context is pre-configured in `GEMINI.md`.

## Requirements

Before you begin, ensure you have:
- **uv**: Python package manager (used for all dependency management in this project) - [Install](https://docs.astral.sh/uv/getting-started/installation/) ([add packages](https://docs.astral.sh/uv/concepts/dependencies/) with `uv add <package>`)
- **agents-cli**: Agents CLI - Install with `uv tool install google-agents-cli`
- **Google Cloud SDK**: For GCP services - [Install](https://cloud.google.com/sdk/docs/install)


## Quick Start (Step-by-Step Local Setup)

### 1. Install `agents-cli` and project dependencies

```bash
uvx google-agents-cli setup
uv sync   # or: agents-cli install
```

### 2. Configure Environment Variables (`.env`)

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` with either **Vertex AI** (`gcloud auth application-default login` + `GOOGLE_CLOUD_PROJECT=<your-project-id>`) or **Google AI Studio** (`GOOGLE_GENAI_USE_VERTEXAI=false` + `GEMINI_API_KEY=<your-api-key>`). Keep `ALLOW_UNVERIFIED=1` enabled for local development.

### 3. Run the Application Locally

- **Option A — Interactive Streamlit Clinical UI (Fastest):**
  ```bash
  uv run streamlit run app/streamlit_app.py
  ```
  Opens at `http://localhost:8501`.

- **Option B — Full FastAPI Server (Streamlit UI + ADK Dev UI + A2A):**
  ```bash
  uv run uvicorn app.fast_api_app:app --host 0.0.0.0 --port 8000
  ```
  - Clinical & Parent Passport UI: `http://localhost:8000/ui/`
  - ADK Developer Trace UI: `http://localhost:8000/dev-ui/`
  - A2A Endpoint: `http://localhost:8000/a2a/app`

- **Option C — ADK Playground (Auto-Reload):**
  ```bash
  agents-cli playground
  ```

You can also use features from the [ADK](https://adk.dev/) CLI with `uv run adk`.

## Commands

| Command              | Description                                                                                 |
| -------------------- | ------------------------------------------------------------------------------------------- |
| `agents-cli install` | Install dependencies using uv                                                         |
| `agents-cli playground` | Launch local development environment                                                  |
| `agents-cli lint`    | Run code quality checks                                                               |
| `agents-cli eval`    | Evaluate agent behavior (generate, grade, analyze, and more — see `agents-cli eval --help`) |
| `uv run pytest tests/unit tests/integration` | Run unit and integration tests                                                        |
| `agents-cli deploy`  | Deploy agent to Cloud Run                                                                   || [A2A Inspector](https://github.com/a2aproject/a2a-inspector) | Launch A2A Protocol Inspector                                                        |

## 🛠️ Project Management

| Command | What It Does |
|---------|--------------|
| `agents-cli scaffold enhance` | Add CI/CD pipelines and Terraform infrastructure |
| `agents-cli infra cicd` | One-command setup of entire CI/CD pipeline + infrastructure |
| `agents-cli scaffold upgrade` | Auto-upgrade to latest version while preserving customizations |

---

## Development

Edit your agent logic in `app/agent.py` and test with `agents-cli playground` - it auto-reloads on save.

## Deployment

```bash
gcloud config set project <your-project-id>
agents-cli deploy
```

To add CI/CD and Terraform, run `agents-cli scaffold enhance`.
To set up your production infrastructure, run `agents-cli infra cicd`.

## Observability

Built-in telemetry exports to Cloud Trace, BigQuery, and Cloud Logging.

## A2A Inspector

This agent supports the [A2A Protocol](https://a2a-protocol.org/). Use the [A2A Inspector](https://github.com/a2aproject/a2a-inspector) to test interoperability.
See the [A2A Inspector docs](https://github.com/a2aproject/a2a-inspector) for details.
