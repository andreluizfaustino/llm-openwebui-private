import json
import os
import tempfile

import pytest

from setup.src.services.state import AccessMode, GpuType, OllamaConfig, SetupState, StateService


@pytest.fixture
def tmp_state():
    with tempfile.TemporaryDirectory() as d:
        yield StateService(data_dir=d), d


def test_load_returns_default_when_file_absent(tmp_state):
    svc, _ = tmp_state
    state = svc.load()
    assert state.completed is False
    assert state.current_step == 1
    assert state.selected_models == []


def test_save_and_roundtrip(tmp_state):
    svc, d = tmp_state
    state = svc.load()
    state.current_step = 2
    state.ollama_config = OllamaConfig(gpu_type=GpuType.NVIDIA, keep_alive="10m")
    svc.save(state)

    loaded = svc.load()
    assert loaded.current_step == 2
    assert loaded.ollama_config.gpu_type == GpuType.NVIDIA
    assert loaded.ollama_config.keep_alive == "10m"


def test_completed_flag(tmp_state):
    svc, _ = tmp_state
    state = svc.load()
    state.current_step = 4
    state.selected_models = ["llama3.2:1b"]
    state.installed_models = ["llama3.2:1b"]
    state.webui_access_mode = AccessMode.LOGIN_REQUIRED
    state.completed = True
    svc.save(state)

    loaded = svc.load()
    assert loaded.completed is True


def test_reset_removes_files(tmp_state):
    svc, d = tmp_state
    state = svc.load()
    state.completed = True
    state.current_step = 4
    svc.save(state)

    # create side-effect files
    open(os.path.join(d, "open-webui.env"), "w").close()
    open(os.path.join(d, "docker-compose.override.yml"), "w").close()

    svc.reset()

    assert not os.path.exists(os.path.join(d, "setup-state.json"))
    assert not os.path.exists(os.path.join(d, "open-webui.env"))
    assert not os.path.exists(os.path.join(d, "docker-compose.override.yml"))


def test_reset_on_empty_dir_is_safe(tmp_state):
    svc, _ = tmp_state
    svc.reset()  # should not raise
