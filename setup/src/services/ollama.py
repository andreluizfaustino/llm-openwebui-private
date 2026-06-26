import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import AsyncGenerator

import httpx


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"


@dataclass
class ServiceHealth:
    status: HealthStatus
    checked_at: str


@dataclass
class ModelInstallStatus:
    tag: str
    status: str  # pending | downloading | installed | failed
    progress_bytes: int = 0
    total_bytes: int = 0
    error_message: str | None = None


class OllamaService:
    def __init__(self, base_url: str = "http://ollama:11434"):
        self._base_url = base_url

    async def health_check(self) -> ServiceHealth:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{self._base_url}/api/version")
                if r.status_code == 200:
                    return ServiceHealth(status=HealthStatus.HEALTHY, checked_at=now)
        except (httpx.ConnectError, httpx.TimeoutException):
            pass
        return ServiceHealth(status=HealthStatus.UNHEALTHY, checked_at=now)

    async def list_installed_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"{self._base_url}/api/tags")
                if r.status_code == 200:
                    data = r.json()
                    return [m["name"] for m in data.get("models", [])]
        except (httpx.ConnectError, httpx.TimeoutException):
            pass
        return []

    async def pull_model(self, tag: str) -> AsyncGenerator[ModelInstallStatus, None]:
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/api/pull",
                    json={"name": tag},
                ) as response:
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        import json
                        try:
                            data = json.loads(line)
                        except ValueError:
                            continue
                        status_text = data.get("status", "")
                        completed = data.get("completed", 0)
                        total = data.get("total", 0)

                        if "error" in data:
                            yield ModelInstallStatus(
                                tag=tag,
                                status="failed",
                                error_message=data["error"],
                            )
                            return

                        if status_text == "success":
                            yield ModelInstallStatus(tag=tag, status="installed", progress_bytes=total, total_bytes=total)
                            return

                        yield ModelInstallStatus(
                            tag=tag,
                            status="downloading",
                            progress_bytes=completed,
                            total_bytes=total,
                        )
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            yield ModelInstallStatus(tag=tag, status="failed", error_message=str(e))

    async def is_model_installed(self, tag: str) -> bool:
        installed = await self.list_installed_models()
        return tag in installed
