import json
import os
from dataclasses import dataclass


@dataclass
class ModelDefinition:
    tag: str
    name: str
    size_gb: float
    description: str
    hardware_recommendation: str
    compatibility: str  # recommended | compatible | not_recommended


class ModelsCatalogueService:
    def __init__(self, catalogue_path: str | None = None):
        if catalogue_path is None:
            catalogue_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "data", "models.json"
            )
        self._path = catalogue_path
        self._models: list[ModelDefinition] | None = None

    def list_models(self, installed: list[str] | None = None) -> list[dict]:
        models = self._load()
        installed_set = set(installed or [])
        return [
            {
                "tag": m.tag,
                "name": m.name,
                "size_gb": m.size_gb,
                "description": m.description,
                "hardware_recommendation": m.hardware_recommendation,
                "compatibility": m.compatibility,
                "installed": m.tag in installed_set,
            }
            for m in models
        ]

    def _load(self) -> list[ModelDefinition]:
        if self._models is not None:
            return self._models
        with open(self._path) as f:
            raw = json.load(f)
        self._models = [ModelDefinition(**item) for item in raw]
        return self._models
