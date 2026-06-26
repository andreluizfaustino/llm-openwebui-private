import pytest
from httpx import ASGITransport, AsyncClient

from setup.src.main import app


@pytest.fixture
async def client(tmp_path):
    app.state.data_dir = str(tmp_path)
    app.state.ollama_base_url = "http://localhost:99999"  # intentionally unreachable
    app.state.webui_base_url = "http://localhost:99998"
    app.state.open_webui_host_url = "http://localhost:8080"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_health_returns_ok(client):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_root_redirects_to_setup_when_incomplete(client):
    res = await client.get("/", follow_redirects=False)
    assert res.status_code == 302
    assert res.headers["location"] == "/setup"


@pytest.mark.anyio
async def test_setup_state_initial(client):
    res = await client.get("/api/setup/state")
    assert res.status_code == 200
    data = res.json()
    assert data["completed"] is False
    assert data["current_step"] == 1


@pytest.mark.anyio
async def test_ollama_config_advances_step(client):
    res = await client.post("/api/setup/ollama-config", json={
        "gpu_type": "none",
        "keep_alive": "5m",
        "num_parallel": 1,
    })
    assert res.status_code == 200
    assert res.json()["current_step"] == 2


@pytest.mark.anyio
async def test_webui_config_advances_step(client):
    # First advance to step 2
    await client.post("/api/setup/ollama-config", json={"gpu_type": "none"})
    res = await client.post("/api/setup/webui-config", json={"access_mode": "login_required"})
    assert res.status_code == 200
    assert res.json()["current_step"] == 4


@pytest.mark.anyio
async def test_complete_fails_when_models_not_installed(client):
    await client.post("/api/setup/ollama-config", json={"gpu_type": "none"})
    await client.post("/api/setup/models/install", json={"models": ["llama3.2:1b"]})
    await client.post("/api/setup/webui-config", json={"access_mode": "login_required"})
    res = await client.post("/api/setup/complete")
    assert res.status_code == 409


@pytest.mark.anyio
async def test_dashboard_redirects_when_incomplete(client):
    res = await client.get("/dashboard", follow_redirects=False)
    assert res.status_code == 302
    assert res.headers["location"] == "/setup"
