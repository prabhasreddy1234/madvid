"""Configuration and precedence logic for MADVID."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .validation import validate_duration, validate_orientation, validate_style


@dataclass
class Config:
    default_duration: int = 20
    default_style: str = "minimal"
    default_orientation: str = "landscape"
    voice: bool = False
    resolution: str = "1080p"
    preview: bool = False
    project_root: str = "."
    source_url: str | None = None

    @classmethod
    def from_dict(cls, values: dict | None) -> "Config":
        data = values or {}
        cfg = cls()
        if "defaultDuration" in data:
            cfg.default_duration = validate_duration(data["defaultDuration"])
        if "defaultStyle" in data:
            cfg.default_style = validate_style(data["defaultStyle"])
        if "defaultOrientation" in data:
            cfg.default_orientation = validate_orientation(data["defaultOrientation"])
        if "voice" in data:
            cfg.voice = bool(data["voice"])
        if "preview" in data:
            cfg.preview = bool(data["preview"])
        if "resolution" in data:
            cfg.resolution = str(data["resolution"])
        return cfg


def _read_json_file(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def load_config(
    project_cfg: dict | None = None,
    cli_overrides: dict | None = None,
    global_cfg: dict | None = None,
) -> Config:
    """Merge configuration with precedence CLI > project > global > defaults."""
    global_cfg = global_cfg or {}
    project_cfg = project_cfg or {}
    cli_overrides = cli_overrides or {}

    config = Config.from_dict(global_cfg)
    config = Config.from_dict({**config.__dict__, **project_cfg})
    config = Config.from_dict({**config.__dict__, **cli_overrides})
    return config


def load_project_config(project_root: str = ".") -> dict:
    root = Path(project_root)
    config_path = root / ".madvid" / "config.json"
    return _read_json_file(config_path)
