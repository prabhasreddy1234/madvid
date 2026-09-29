"""Validation helpers for user-driven MADVID options."""

from __future__ import annotations

ALLOWED_DURATIONS = range(15, 31)
VALID_ORIENTATIONS = {"landscape", "vertical"}
VALID_STYLES = {"minimal", "cinematic"}


def validate_duration(duration: int) -> int:
    """Return a valid duration in seconds or raise ValueError."""
    try:
        duration = int(duration)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise ValueError("Duration must be an integer between 15 and 30 seconds.") from exc
    if duration not in ALLOWED_DURATIONS:
        raise ValueError("Duration must be between 15 and 30 seconds.")
    return duration


def validate_orientation(orientation: str) -> str:
    """Return a valid orientation or raise ValueError."""
    value = (orientation or "").strip().lower()
    if value not in VALID_ORIENTATIONS:
        raise ValueError("Orientation must be 'landscape' or 'vertical'.")
    return value


def validate_style(style: str) -> str:
    """Return a valid style or raise ValueError."""
    value = (style or "").strip().lower()
    if value not in VALID_STYLES:
        raise ValueError("Style must be 'minimal' or 'cinematic'.")
    return value
