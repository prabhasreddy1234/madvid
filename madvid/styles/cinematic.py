"""Cinematic video styling."""

from .base import StyleTemplate


class CinematicStyle(StyleTemplate):
    def __init__(self):
        super().__init__(
            name="cinematic",
            accent="#f59e0b",
            background="#111827",
            secondary="#f8fafc",
            transition="Smooth zoom and gentle parallax",
        )
