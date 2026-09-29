"""Minimal video styling."""

from .base import StyleTemplate


class MinimalStyle(StyleTemplate):
    def __init__(self):
        super().__init__(
            name="minimal",
            accent="#7c3aed",
            background="#0f172a",
            secondary="#e2e8f0",
            transition="Subtle fade and clean typography",
        )
