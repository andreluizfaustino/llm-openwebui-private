import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.services.state import StateService

router = APIRouter()

_templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "..", "templates")
)


def _state_service(request: Request) -> StateService:
    data_dir = getattr(request.app.state, "data_dir", "/data")
    return StateService(data_dir=data_dir)


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    state = _state_service(request).load()
    if state.completed:
        return RedirectResponse(url="/dashboard", status_code=302)
    return RedirectResponse(url="/setup", status_code=302)


@router.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    state = _state_service(request).load()
    if state.completed:
        return RedirectResponse(url="/dashboard", status_code=302)
    step = state.current_step
    template = f"setup/step{step}.html"
    open_webui_url = getattr(request.app.state, "open_webui_host_url", "http://localhost:8080")
    return _templates.TemplateResponse(request=request, name=template, context={"state": state, "open_webui_url": open_webui_url})


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    state = _state_service(request).load()
    if not state.completed:
        return RedirectResponse(url="/setup", status_code=302)
    return _templates.TemplateResponse(request=request, name="dashboard.html", context={"state": state})
