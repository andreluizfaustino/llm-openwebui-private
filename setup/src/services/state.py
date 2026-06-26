import json
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, field_validator


class GpuType(str, Enum):
    NONE = "none"
    NVIDIA = "nvidia"
    AMD = "amd"


class AccessMode(str, Enum):
    PUBLIC = "public"
    LOGIN_REQUIRED = "login_required"
    REGISTRATION_ENABLED = "registration_enabled"


class OllamaConfig(BaseModel):
    gpu_type: GpuType = GpuType.NONE
    num_parallel: Optional[int] = 1
    max_loaded_models: Optional[int] = None
    keep_alive: Optional[str] = "5m"
    origins: Optional[str] = None
    gpu_layers: Optional[int] = None


class SetupState(BaseModel):
    completed: bool = False
    current_step: int = 1
    ollama_config: OllamaConfig = OllamaConfig()
    selected_models: list[str] = []
    installed_models: list[str] = []
    webui_access_mode: Optional[AccessMode] = None
    created_at: str = ""
    updated_at: str = ""

    @field_validator("current_step")
    @classmethod
    def validate_step(cls, v: int) -> int:
        if v not in (1, 2, 3, 4):
            raise ValueError("current_step must be 1–4")
        return v


class StateService:
    def __init__(self, data_dir: str = "/data"):
        self._path = os.path.join(data_dir, "setup-state.json")

    def load(self) -> SetupState:
        if not os.path.exists(self._path):
            return SetupState(created_at=_now(), updated_at=_now())
        with open(self._path) as f:
            data = json.load(f)
        return SetupState(**data)

    def save(self, state: SetupState) -> SetupState:
        state.updated_at = _now()
        if not state.created_at:
            state.created_at = state.updated_at
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w") as f:
            json.dump(state.model_dump(), f, indent=2)
        return state

    def reset(self) -> None:
        if os.path.exists(self._path):
            os.remove(self._path)
        env_path = os.path.join(os.path.dirname(self._path), "open-webui.env")
        if os.path.exists(env_path):
            os.remove(env_path)
        override_path = os.path.join(os.path.dirname(self._path), "docker-compose.override.yml")
        if os.path.exists(override_path):
            os.remove(override_path)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
