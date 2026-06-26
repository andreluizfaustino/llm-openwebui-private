import os

import yaml

from src.services.state import GpuType


class ComposeOverrideService:
    def __init__(self, data_dir: str = "/data"):
        self._path = os.path.join(data_dir, "docker-compose.override.yml")

    def write_override(self, gpu_type: GpuType) -> None:
        if gpu_type == GpuType.NONE:
            self.remove_override()
            return

        if gpu_type == GpuType.NVIDIA:
            override = {
                "services": {
                    "ollama": {
                        "deploy": {
                            "resources": {
                                "reservations": {
                                    "devices": [
                                        {
                                            "driver": "nvidia",
                                            "count": "all",
                                            "capabilities": ["gpu"],
                                        }
                                    ]
                                }
                            }
                        }
                    }
                }
            }
        else:  # AMD
            override = {
                "services": {
                    "ollama": {
                        "image": "ollama/ollama:rocm",
                        "devices": ["/dev/kfd", "/dev/dri"],
                    }
                }
            }

        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w") as f:
            yaml.dump(override, f, default_flow_style=False)

    def remove_override(self) -> None:
        if os.path.exists(self._path):
            os.remove(self._path)
