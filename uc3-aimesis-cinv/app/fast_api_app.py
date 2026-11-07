# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import contextlib
import os
import subprocess
import sys
from collections.abc import AsyncIterator

import httpx
import websockets
from a2a.server.tasks import InMemoryTaskStore
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.runners import Runner

from app.app_utils import services
from app.app_utils.a2a import attach_a2a_routes

load_dotenv()
allow_origins = (
    os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else None
)
otel_to_cloud = True

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STREAMLIT_PORT = int(os.getenv("STREAMLIT_PORT", "8501"))
STREAMLIT_HTTP_BASE = f"http://127.0.0.1:{STREAMLIT_PORT}"
STREAMLIT_WS_BASE = f"ws://127.0.0.1:{STREAMLIT_PORT}"


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from app.agent import app as adk_app
    from app.agent import root_agent

    runner = Runner(
        app=adk_app,
        session_service=services.get_session_service(),
        artifact_service=services.get_artifact_service(),
        auto_create_session=True,
    )
    app.state.runner = runner
    app.state.agent_app_name = adk_app.name
    await attach_a2a_routes(
        app,
        agent=root_agent,
        runner=runner,
        task_store=InMemoryTaskStore(),
        rpc_path=f"/a2a/{adk_app.name}",
    )

    streamlit_proc: subprocess.Popen[bytes] | None = None
    if os.getenv("INTEGRATION_TEST") != "TRUE":
        streamlit_script = os.path.join(os.path.dirname(__file__), "streamlit_app.py")
        streamlit_proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                streamlit_script,
                f"--server.port={STREAMLIT_PORT}",
                "--server.address=127.0.0.1",
                "--server.baseUrlPath=ui",
                "--server.headless=true",
                "--server.enableCORS=false",
                "--server.enableXsrfProtection=false",
                "--browser.gatherUsageStats=false",
            ],
            cwd=AGENT_DIR,
        )

    try:
        yield
    finally:
        if streamlit_proc is not None:
            streamlit_proc.terminate()
            try:
                streamlit_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                streamlit_proc.kill()


app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    artifact_service_uri=services.ARTIFACT_SERVICE_URI,
    allow_origins=allow_origins,
    session_service_uri=services.SESSION_SERVICE_URI,
    otel_to_cloud=otel_to_cloud,
    lifespan=lifespan,
)
app.title = "uc3-aimesis-cinv"
app.description = "API for interacting with the Agent uc3-aimesis-cinv"

# Replace the default `/` redirect so root opens the Streamlit Clinical UI (`/ui`),
# while `/dev-ui/` remains available for raw ADK trace inspection.
app.router.routes = [r for r in app.router.routes if getattr(r, "path", None) != "/"]


@app.get("/", include_in_schema=False)
@app.get("/ui", include_in_schema=False)
async def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/ui/")


@app.websocket("/ui/_stcore/stream")
async def proxy_streamlit_ws(websocket: WebSocket) -> None:
    subprotocols = websocket.headers.get("sec-websocket-protocol")
    accepted_subprotocol = subprotocols.split(",")[0].strip() if subprotocols else None
    await websocket.accept(subprotocol=accepted_subprotocol)
    target_ws_url = f"{STREAMLIT_WS_BASE}/ui/_stcore/stream"

    try:
        async with websockets.connect(
            target_ws_url,
            max_size=None,
            open_timeout=15,
        ) as st_ws:

            async def _client_to_st() -> None:
                try:
                    while True:
                        msg = await websocket.receive()
                        if msg.get("type") == "websocket.disconnect":
                            break
                        if "text" in msg and msg["text"] is not None:
                            await st_ws.send(msg["text"])
                        elif "bytes" in msg and msg["bytes"] is not None:
                            await st_ws.send(msg["bytes"])
                except WebSocketDisconnect:
                    pass

            async def _st_to_client() -> None:
                try:
                    async for message in st_ws:
                        if isinstance(message, bytes):
                            await websocket.send_bytes(message)
                        else:
                            await websocket.send_text(message)
                except Exception:
                    pass

            _done, pending = await asyncio.wait(
                [
                    asyncio.create_task(_client_to_st()),
                    asyncio.create_task(_st_to_client()),
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
    except Exception:
        with contextlib.suppress(Exception):
            await websocket.close()


@app.api_route(
    "/ui/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    include_in_schema=False,
)
async def proxy_streamlit_http(request: Request, path: str = "") -> Response:
    target_url = f"{STREAMLIT_HTTP_BASE}/ui/{path}"
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in {"host", "content-length", "transfer-encoding"}
    }
    body = await request.body()

    async with httpx.AsyncClient(follow_redirects=False, timeout=60.0) as client:
        for attempt in range(10):
            try:
                resp = await client.request(
                    method=request.method,
                    url=target_url,
                    headers=headers,
                    content=body,
                )
                excluded_resp_headers = {
                    "content-encoding",
                    "content-length",
                    "transfer-encoding",
                    "connection",
                }
                resp_headers = {
                    k: v
                    for k, v in resp.headers.items()
                    if k.lower() not in excluded_resp_headers
                }
                return Response(
                    content=resp.content,
                    status_code=resp.status_code,
                    headers=resp_headers,
                    media_type=resp.headers.get("content-type"),
                )
            except httpx.ConnectError:
                if attempt < 9:
                    await asyncio.sleep(0.5)
                else:
                    return Response(
                        content="Streamlit UI is warming up, please refresh in a second...",
                        status_code=503,
                    )
    return Response(content="Streamlit UI unavailable", status_code=503)


# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
