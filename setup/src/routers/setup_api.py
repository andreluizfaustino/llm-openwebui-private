import asyncio
import json
import os
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from src.services.compose_override import ComposeOverrideService
from src.services.models_catalogue import ModelsCatalogueService
from src.services.ollama import OllamaService
from src.services.state import AccessMode, GpuType, OllamaConfig, StateService
from src.services.webui import WebUIService

router = APIRouter()

# In-memory install state (per-process; reset on container restart)
_install_tasks: dict[str, asyncio.Task] = {}
_install_results: dict[str, dict] = {}  # tag -> ModelInstallStatus dict


def _svc(request: Request):
    data_dir = getattr(request.app.state, "data_dir", "/data")
    ollama_url = getattr(request.app.state, "ollama_base_url", "http://ollama:11434")
    webui_url = getattr(request.app.state, "webui_base_url", "http://open-webui:8080")
    return (
        StateService(data_dir=data_dir),
        OllamaService(base_url=ollama_url),
        WebUIService(base_url=webui_url, data_dir=data_dir),
        ModelsCatalogueService(),
        ComposeOverrideService(data_dir=data_dir),
    )


# ── State ──────────────────────────────────────────────────────────────────────

@router.get("/state")
async def get_state(request: Request):
    state_svc, *_ = _svc(request)
    return state_svc.load().model_dump()


# ── Step 1: Ollama Config ──────────────────────────────────────────────────────

@router.get("/ollama-config/defaults")
async def ollama_config_defaults():
    return {
        "fields": [
            {
                "key": "gpu_type",
                "label": "GPU Acceleration",
                "description": "Select your GPU type. This determines the Ollama Docker image and runtime configuration.",
                "type": "select",
                "default": "none",
                "options": [
                    {"value": "none", "label": "CPU only (no GPU)"},
                    {"value": "nvidia", "label": "NVIDIA GPU (CUDA)"},
                    {"value": "amd", "label": "AMD GPU (ROCm)"},
                ],
            },
            {
                "key": "keep_alive",
                "env_var": "OLLAMA_KEEP_ALIVE",
                "label": "Keep models loaded",
                "description": "How long to keep a model in memory after last use. Examples: 5m, 1h, -1 (always).",
                "default": "5m",
                "type": "string",
            },
            {
                "key": "num_parallel",
                "env_var": "OLLAMA_NUM_PARALLEL",
                "label": "Parallel requests",
                "description": "Maximum number of parallel inference requests.",
                "default": 1,
                "type": "integer",
            },
        ]
    }


class OllamaConfigRequest(BaseModel):
    gpu_type: GpuType = GpuType.NONE
    keep_alive: str | None = "5m"
    num_parallel: int | None = 1
    max_loaded_models: int | None = None
    origins: str | None = None
    gpu_layers: int | None = None


@router.post("/ollama-config")
async def save_ollama_config(body: OllamaConfigRequest, request: Request):
    state_svc, _, _, _, override_svc = _svc(request)
    state = state_svc.load()
    state.ollama_config = OllamaConfig(**body.model_dump())
    state.current_step = 2
    override_svc.write_override(body.gpu_type)
    state_svc.save(state)
    return {"current_step": 2}


# ── Step 2: Models ────────────────────────────────────────────────────────────

@router.get("/models")
async def list_models(request: Request):
    state_svc, ollama_svc, *_ = _svc(request)
    _, catalogue_svc, *_ = (None, ModelsCatalogueService(), None, None, None)
    installed = await ollama_svc.list_installed_models()
    models = ModelsCatalogueService().list_models(installed=installed)
    return {"models": models}


class InstallRequest(BaseModel):
    models: list[str]


@router.post("/models/install", status_code=202)
async def start_install(body: InstallRequest, request: Request):
    if not body.models:
        raise HTTPException(status_code=400, detail="Select at least one model.")
    state_svc, ollama_svc, *_ = _svc(request)
    state = state_svc.load()
    state.selected_models = body.models
    state_svc.save(state)
    # Reset previous results for selected models
    for tag in body.models:
        _install_results[tag] = {"tag": tag, "status": "pending", "progress_bytes": 0, "total_bytes": 0, "error_message": None}
    return {"message": "Download started"}


@router.get("/models/progress")
async def model_progress(request: Request):
    state_svc, ollama_svc, *_ = _svc(request)
    state = state_svc.load()
    tags = state.selected_models

    async def stream() -> AsyncGenerator[str, None]:
        for tag in tags:
            if _install_results.get(tag, {}).get("status") == "installed":
                continue
            async for status in ollama_svc.pull_model(tag):
                result = {
                    "tag": status.tag,
                    "status": status.status,
                    "progress_bytes": status.progress_bytes,
                    "total_bytes": status.total_bytes,
                    "error_message": status.error_message,
                }
                _install_results[tag] = result
                yield f"data: {json.dumps(result)}\n\n"
                if status.status in ("installed", "failed"):
                    break

            if _install_results.get(tag, {}).get("status") == "installed":
                current = state_svc.load()
                if tag not in current.installed_models:
                    current.installed_models.append(tag)
                    state_svc.save(current)

        yield f"data: {json.dumps({'event': 'complete'})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


class RetryRequest(BaseModel):
    tag: str


@router.post("/models/retry", status_code=202)
async def retry_model(body: RetryRequest, request: Request):
    state_svc, *_ = _svc(request)
    state = state_svc.load()
    if body.tag not in state.selected_models:
        raise HTTPException(status_code=404, detail="Model not in selected list.")
    current = _install_results.get(body.tag, {})
    if current.get("status") not in ("failed", "pending", None):
        raise HTTPException(status_code=409, detail="Model is not in a failed state.")
    _install_results[body.tag] = {"tag": body.tag, "status": "pending", "progress_bytes": 0, "total_bytes": 0, "error_message": None}
    return {"message": "Retry started"}


# ── Step 3: Open WebUI Config ─────────────────────────────────────────────────

class WebUIConfigRequest(BaseModel):
    access_mode: AccessMode


@router.post("/step2/confirm")
async def confirm_step2(request: Request):
    state_svc, *_ = _svc(request)
    state = state_svc.load()
    if not state.installed_models:
        raise HTTPException(status_code=409, detail="At least one model must be installed before proceeding.")
    state.current_step = 3
    state_svc.save(state)
    return {"current_step": 3}


@router.post("/webui-config")
async def save_webui_config(body: WebUIConfigRequest, request: Request):
    state_svc, *_ = _svc(request)
    state = state_svc.load()
    state.webui_access_mode = body.access_mode
    state.current_step = 4
    state_svc.save(state)
    return {"current_step": 4}


# ── Step 4: Complete ──────────────────────────────────────────────────────────

@router.post("/complete")
async def complete_setup(request: Request):
    state_svc, _, webui_svc, *_ = _svc(request)
    state = state_svc.load()
    not_installed = [t for t in state.selected_models if t not in state.installed_models]
    if not_installed:
        raise HTTPException(
            status_code=409,
            detail=f"Models not yet installed: {', '.join(not_installed)}",
        )
    if state.webui_access_mode is None:
        raise HTTPException(status_code=409, detail="Open WebUI access mode not configured.")

    access_mode = state.webui_access_mode.value
    webui_svc.write_env_file(access_mode)

    # Build the exact env patch to apply to the open-webui container
    access_map = {
        "public":               {"WEBUI_AUTH": "false", "ENABLE_SIGNUP": "false", "DEFAULT_USER_ROLE": "user",    "ENABLE_LOGIN_FORM": "false"},
        "login_required":       {"WEBUI_AUTH": "true",  "ENABLE_SIGNUP": "false", "DEFAULT_USER_ROLE": "pending", "ENABLE_LOGIN_FORM": "true"},
        "registration_enabled": {"WEBUI_AUTH": "true",  "ENABLE_SIGNUP": "true",  "DEFAULT_USER_ROLE": "user",    "ENABLE_LOGIN_FORM": "true"},
    }
    env_patch = access_map.get(access_mode, access_map["login_required"])
    env_patch["WEBUI_SECRET_KEY"] = webui_svc.generate_secret_key()
    env_patch["ENABLE_PERSISTENT_CONFIG"] = "false"

    container_name = os.getenv("WEBUI_CONTAINER_NAME", "llm-workspace-webui")
    try:
        webui_svc.recreate_container_with_env(container_name, env_patch)
    except Exception as exc:
        # Log but don't fail the request — step-4 health polling will confirm status
        import logging
        logging.getLogger(__name__).error("Container recreation failed: %s", exc)

    state.completed = True
    state_svc.save(state)
    return {"completed": True}
