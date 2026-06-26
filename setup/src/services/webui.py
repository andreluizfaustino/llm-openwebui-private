import os
import secrets
import subprocess

import httpx

from src.services.ollama import HealthStatus, ServiceHealth


class WebUIService:
    def __init__(self, base_url: str = "http://open-webui:8080", data_dir: str = "/data"):
        self._base_url = base_url
        self._data_dir = data_dir
        self._config_env_path = os.getenv("WEBUI_CONFIG_PATH", "/config/open-webui.env")
        self._secret_key_path = os.path.join(data_dir, ".webui-secret-key")

    async def health_check(self) -> ServiceHealth:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                # /api/config is only available after full app initialisation
                # (unlike /health which returns 200 as soon as uvicorn starts)
                r = await client.get(f"{self._base_url}/api/config")
                if r.status_code == 200:
                    return ServiceHealth(status=HealthStatus.HEALTHY, checked_at=now)
        except (httpx.ConnectError, httpx.TimeoutException):
            pass
        return ServiceHealth(status=HealthStatus.UNHEALTHY, checked_at=now)

    def generate_secret_key(self) -> str:
        if os.path.exists(self._secret_key_path):
            with open(self._secret_key_path) as f:
                return f.read().strip()
        key = secrets.token_hex(32)
        os.makedirs(self._data_dir, exist_ok=True)
        with open(self._secret_key_path, "w") as f:
            f.write(key)
        return key

    def write_env_file(self, access_mode: str) -> None:
        secret_key = self.generate_secret_key()

        access_map = {
            "public":               {"WEBUI_AUTH": "false", "ENABLE_SIGNUP": "false", "DEFAULT_USER_ROLE": "user",    "ENABLE_LOGIN_FORM": "false"},
            "login_required":       {"WEBUI_AUTH": "true",  "ENABLE_SIGNUP": "false", "DEFAULT_USER_ROLE": "pending", "ENABLE_LOGIN_FORM": "true"},
            "registration_enabled": {"WEBUI_AUTH": "true",  "ENABLE_SIGNUP": "true",  "DEFAULT_USER_ROLE": "user",    "ENABLE_LOGIN_FORM": "true"},
        }
        settings = access_map.get(access_mode, access_map["login_required"])

        lines = [
            "# Managed by the setup wizard — do not edit manually.",
            "# ENABLE_PERSISTENT_CONFIG=false forces Open WebUI to always read from",
            "# env vars, overriding values previously persisted in the database.",
            "ENABLE_PERSISTENT_CONFIG=false",
            f"WEBUI_AUTH={settings['WEBUI_AUTH']}",
            f"ENABLE_SIGNUP={settings['ENABLE_SIGNUP']}",
            f"DEFAULT_USER_ROLE={settings['DEFAULT_USER_ROLE']}",
            f"ENABLE_LOGIN_FORM={settings['ENABLE_LOGIN_FORM']}",
            f"WEBUI_SECRET_KEY={secret_key}",
            "OLLAMA_BASE_URL=http://ollama:11434",
        ]
        os.makedirs(os.path.dirname(self._config_env_path), exist_ok=True)
        with open(self._config_env_path, "w") as f:
            f.write("\n".join(lines) + "\n")

    def recreate_container_with_env(self, container_name: str, env_patch: dict) -> None:
        """Stop, remove, and recreate a container with patched env vars via Docker socket."""
        import json

        def docker_call(method: str, path: str, body=None) -> dict:
            cmd = ["curl", "--silent", "--unix-socket", "/var/run/docker.sock"]
            if method != "GET":
                cmd += ["-X", method]
            if body is not None:
                cmd += ["-H", "Content-Type: application/json", "--data", json.dumps(body)]
            cmd.append(f"http://localhost{path}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
            return json.loads(result.stdout) if result.stdout.strip() else {}

        # Inspect current container to clone its full config
        info = docker_call("GET", f"/containers/{container_name}/json")
        if not info or "Config" not in info:
            raise RuntimeError(f"Container {container_name!r} not found")

        # Patch env vars
        env_dict: dict[str, str] = {}
        for item in info["Config"].get("Env") or []:
            k, _, v = item.partition("=")
            env_dict[k] = v
        env_dict.update(env_patch)

        # Collect networks to re-attach after start (strip runtime-only fields)
        networks: dict[str, dict] = {}
        for net_name, net_cfg in (info["NetworkSettings"].get("Networks") or {}).items():
            networks[net_name] = {
                "IPAMConfig": net_cfg.get("IPAMConfig"),
                "Aliases": net_cfg.get("Aliases") or [],
                "DriverOpts": net_cfg.get("DriverOpts"),
            }

        # Build create payload — force bridge NetworkMode, reconnect to actual networks after start
        host_config = dict(info["HostConfig"])
        host_config["NetworkMode"] = "bridge"

        create_payload = {
            "Image": info["Config"]["Image"],
            "Env": [f"{k}={v}" for k, v in env_dict.items()],
            "ExposedPorts": info["Config"].get("ExposedPorts") or {},
            "Labels": info["Config"].get("Labels") or {},  # preserve Compose labels
            "HostConfig": host_config,
        }

        docker_call("POST", f"/containers/{container_name}/stop")
        docker_call("DELETE", f"/containers/{container_name}?force=true")
        created = docker_call("POST", f"/containers/create?name={container_name}", create_payload)
        container_id = created.get("Id") or container_name
        docker_call("POST", f"/containers/{container_id}/start")

        # Re-attach to all original networks
        for net_name, net_cfg in networks.items():
            docker_call("POST", f"/networks/{net_name}/connect", {
                "Container": container_id,
                "EndpointConfig": net_cfg,
            })

    # Keep as convenience alias used by older callers
    def restart_container(self, container_name: str) -> None:
        """Simple restart (does not change env vars)."""
        subprocess.run(
            ["curl", "--silent", "--unix-socket", "/var/run/docker.sock",
             "-X", "POST", f"http://localhost/containers/{container_name}/restart"],
            check=True, timeout=15,
        )
