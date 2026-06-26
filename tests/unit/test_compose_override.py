import os
import tempfile

import pytest
import yaml

from setup.src.services.compose_override import ComposeOverrideService
from setup.src.services.state import GpuType


@pytest.fixture
def tmp_svc():
    with tempfile.TemporaryDirectory() as d:
        yield ComposeOverrideService(data_dir=d), d


def test_none_produces_no_file(tmp_svc):
    svc, d = tmp_svc
    svc.write_override(GpuType.NONE)
    assert not os.path.exists(os.path.join(d, "docker-compose.override.yml"))


def test_nvidia_produces_gpu_reservation(tmp_svc):
    svc, d = tmp_svc
    svc.write_override(GpuType.NVIDIA)
    path = os.path.join(d, "docker-compose.override.yml")
    assert os.path.exists(path)
    with open(path) as f:
        data = yaml.safe_load(f)
    devices = data["services"]["ollama"]["deploy"]["resources"]["reservations"]["devices"]
    assert devices[0]["driver"] == "nvidia"
    assert "gpu" in devices[0]["capabilities"]


def test_amd_produces_rocm_image(tmp_svc):
    svc, d = tmp_svc
    svc.write_override(GpuType.AMD)
    path = os.path.join(d, "docker-compose.override.yml")
    assert os.path.exists(path)
    with open(path) as f:
        data = yaml.safe_load(f)
    assert data["services"]["ollama"]["image"] == "ollama/ollama:rocm"


def test_remove_override_deletes_file(tmp_svc):
    svc, d = tmp_svc
    svc.write_override(GpuType.NVIDIA)
    svc.remove_override()
    assert not os.path.exists(os.path.join(d, "docker-compose.override.yml"))


def test_remove_override_safe_when_absent(tmp_svc):
    svc, _ = tmp_svc
    svc.remove_override()  # should not raise
