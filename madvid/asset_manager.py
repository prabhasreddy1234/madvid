"""Asset management for output and media discovery."""

from __future__ import annotations

import json
from pathlib import Path


def ensure_output_dir(output_dir: str = "madvid-output") -> Path:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    asset_dir = path / "assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)


def discover_assets(project_root: str | None = None) -> list[str]:
    root = Path(project_root) if project_root else Path('.')
    assets: list[str] = []
    for folder in ("assets", "public", "src", "app", "android", "ios"):
        candidate = root / folder
        if candidate.exists():
            assets.append(str(candidate))
    return assets
