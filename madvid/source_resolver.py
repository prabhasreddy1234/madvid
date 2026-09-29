"""Source resolution for local projects, websites, and app stores."""

from __future__ import annotations

import os
from enum import Enum
from typing import Optional
from urllib.parse import urlparse


class SourceType(str, Enum):
    PROJECT = "PROJECT"
    WEBSITE = "WEBSITE"
    PLAY_STORE = "PLAY_STORE"
    APP_STORE = "APP_STORE"


def resolve_source(url: Optional[str] = None, project_root: str = ".") -> SourceType:
    """Resolve the source type based on explicit URL or current project context."""
    if url is not None and str(url).strip():
        candidate = str(url).strip()
        parsed = urlparse(candidate)
        netloc = (parsed.netloc or "").lower()
        path = (parsed.path or "").lower()
        if "play.google.com" in netloc and "store/apps/details" in path:
            return SourceType.PLAY_STORE
        if "apps.apple.com" in netloc or "itunes.apple.com" in netloc:
            return SourceType.APP_STORE
        if parsed.scheme and parsed.netloc:
            return SourceType.WEBSITE

    if project_root and os.path.isdir(project_root):
        root = os.path.abspath(project_root)
        known_files = [
            "package.json",
            "build.gradle",
            "settings.gradle",
            "Package.swift",
            "podfile",
            "Cargo.toml",
            "pyproject.toml",
            "README.md",
            "src",
            "app",
            "ios",
            "android",
        ]
        project_exists = any(os.path.exists(os.path.join(root, item)) for item in known_files)
        if project_exists:
            return SourceType.PROJECT

    return SourceType.PROJECT
