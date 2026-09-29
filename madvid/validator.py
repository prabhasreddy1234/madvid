"""Validation helpers for MADVID output artifacts."""

from __future__ import annotations

from pathlib import Path

from .security import filter_sensitive_data


def validate_output(output_dir: str, duration: int, orientation: str, resolution: str) -> dict:
    """Check a MADVID output bundle for obvious errors before finalizing."""
    path = Path(output_dir)
    result = {
        "output_dir_exists": path.exists(),
        "duration_ok": 15 <= duration <= 30,
        "orientation_ok": orientation in {"landscape", "vertical"},
        "resolution_ok": isinstance(resolution, str) and "x" in resolution,
        "storyboard_present": (path / "storyboard.md").exists(),
        "voiceover_present": (path / "voiceover.txt").exists(),
    }
    for artifact in ["storyboard.md", "voiceover.txt", "metadata.json"]:
        file_path = path / artifact
        if file_path.exists():
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            sanitized = filter_sensitive_data(content)
            result[f"{artifact}_sanitized"] = sanitized == content
    return result
