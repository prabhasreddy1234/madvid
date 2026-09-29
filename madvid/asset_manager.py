"""Asset management for output and media discovery."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

_VISUAL_ASSET_FOLDERS = (
    "assets/screenshots",
    "screenshots",
    "screens",
    "public",
    "assets",
    "docs/screenshots",
)
_VISUAL_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
_IGNORED_ASSET_PARTS = {".git", ".venv", "node_modules", "dist", "build", "madvid-output"}


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


def discover_visual_assets(project_root: str | None = None, limit: int = 12) -> list[str]:
    """Find usable product screenshots in conventional project asset folders."""
    root = Path(project_root or ".")
    candidates: set[Path] = set()
    for folder in _VISUAL_ASSET_FOLDERS:
        directory = root / folder
        if directory.is_dir():
            candidates.update(directory.rglob("*"))

    usable: list[Path] = []
    for path in candidates:
        if not path.is_file() or path.suffix.lower() not in _VISUAL_IMAGE_EXTENSIONS:
            continue
        relative_path = path.relative_to(root)
        if any(part in _IGNORED_ASSET_PARTS or part.startswith(".") for part in relative_path.parts):
            continue
        try:
            if path.stat().st_size > 30_000_000:
                continue
            with Image.open(path) as image:
                width, height = image.size
                if min(width, height) < 280 or max(width, height) / min(width, height) > 3:
                    continue
                image.verify()
        except (OSError, ValueError):
            continue
        usable.append(path)

    usable.sort(
        key=lambda path: (
            not any(word in path.name.lower() for word in ("screen", "capture", "product", "demo")),
            path.as_posix().lower(),
        )
    )
    return [str(path) for path in usable[:limit]]
