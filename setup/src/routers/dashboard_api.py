import asyncio
import os

from fastapi import APIRouter, Request

from src.services.ollama import OllamaService
from src.services.state import StateService
from src.services.webui import WebUIService

router = APIRouter()


def _svc(request: Request):
    data_dir = getattr(request.app.state, "data_dir", "/data")
    ollama_url = getattr(request.app.state, "ollama_base_url", "http://ollama:11434")
    webui_url = getattr(request.app.state, "webui_base_url", "http://open-webui:8080")
    return (
        StateService(data_dir=data_dir),
        OllamaService(base_url=ollama_url),
        WebUIService(base_url=webui_url, data_dir=data_dir),
    )


@router.get("/health/services")
async def services_health(request: Request):
    _, ollama_svc, webui_svc = _svc(request)
    ollama_health, webui_health, installed = await asyncio.gather(
        ollama_svc.health_check(),
        webui_svc.health_check(),
        ollama_svc.list_installed_models(),
    )
    return {
        "ollama": {"status": ollama_health.status.value, "checked_at": ollama_health.checked_at},
        "open_webui": {"status": webui_health.status.value, "checked_at": webui_health.checked_at},
        "installed_models": installed,
    }


@router.get("/dashboard/summary")
async def dashboard_summary(request: Request):
    state_svc, ollama_svc, _ = _svc(request)
    state = state_svc.load()
    webui_url = getattr(request.app.state, "webui_base_url", "http://open-webui:8080")
    # Expose on host port 8080 isn't guaranteed; use configured URL
    open_webui_host_url = os.getenv("OPEN_WEBUI_HOST_URL", "http://localhost:8080")
    return {
        "webui_access_mode": state.webui_access_mode,
        "ollama_config": state.ollama_config.model_dump() if state.ollama_config else {},
        "installed_models": state.installed_models,
        "open_webui_url": open_webui_host_url,
    }
