import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.routers import pages, setup_api, dashboard_api


DATA_DIR = os.getenv("DATA_DIR", "/data")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
WEBUI_BASE_URL = os.getenv("WEBUI_BASE_URL", "http://open-webui:8080")
OPEN_WEBUI_HOST_URL = os.getenv("OPEN_WEBUI_HOST_URL", "http://localhost:8080")


SETUP_PORT = os.getenv("SETUP_PORT", "3000")


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(DATA_DIR, exist_ok=True)
    app.state.data_dir = DATA_DIR
    app.state.ollama_base_url = OLLAMA_BASE_URL
    app.state.webui_base_url = WEBUI_BASE_URL
    app.state.open_webui_host_url = OPEN_WEBUI_HOST_URL

    print("", flush=True)
    print("╔══════════════════════════════════════════════════════╗", flush=True)
    print("║          Private AI Workspace — Setup Ready          ║", flush=True)
    print("║                                                      ║", flush=True)
    print(f"║   Open your browser:  http://localhost:{SETUP_PORT:<14}  ║", flush=True)
    print("╚══════════════════════════════════════════════════════╝", flush=True)
    print("", flush=True)

    yield


app = FastAPI(title="Private AI Workspace Setup", lifespan=lifespan)


@app.exception_handler(httpx.ConnectError)
async def connect_error_handler(request: Request, exc: httpx.ConnectError):
    return JSONResponse(
        status_code=503,
        content={"error": "service_unavailable", "message": "A required service is not reachable. Please wait and try again."},
    )


@app.exception_handler(httpx.TimeoutException)
async def timeout_handler(request: Request, exc: httpx.TimeoutException):
    return JSONResponse(
        status_code=503,
        content={"error": "service_unavailable", "message": "A required service timed out. Please wait and try again."},
    )


_static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
os.makedirs(_static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=_static_dir), name="static")

app.include_router(pages.router)
app.include_router(setup_api.router, prefix="/api/setup")
app.include_router(dashboard_api.router, prefix="/api")


templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
app.state.templates = templates
