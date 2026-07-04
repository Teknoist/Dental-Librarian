from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    name: str = "Dental Librarian"
    dry_run: bool = True
    require_manual_approval: bool = True
    max_pages_per_source: int = 25
    request_timeout_seconds: int = 25
    polite_delay_seconds: float = 1.0


class AIConfig(BaseModel):
    provider: str = "ollama"
    base_url: str = "http://localhost:11434"
    model: str = "qwen2.5:7b"
    temperature: float = 0
    enabled: bool = True


class ArchiveConfig(BaseModel):
    allowed_extensions: list[str] = Field(default_factory=lambda: [
        ".zip", ".7z", ".rar", ".stl", ".obj", ".ply", ".xml", ".dme", ".library", ".implant"
    ])
    output_dir: str = "archives"
    download_dir: str = "downloads"
    data_dir: str = "data"


class IAConfig(BaseModel):
    enabled: bool = False
    collection: str = "opensource"
    creator: str = "Community Archive"
    mediatype: str = "software"
    subject: list[str] = Field(default_factory=lambda: ["dental", "cadcam", "implant", "library"])


class Config(BaseModel):
    app: AppConfig = Field(default_factory=AppConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    archive: ArchiveConfig = Field(default_factory=ArchiveConfig)
    internet_archive: IAConfig = Field(default_factory=IAConfig)


def load_config(path: Path) -> Config:
    if not path.exists():
        return Config()
    with path.open("r", encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}
    return Config.model_validate(raw)
