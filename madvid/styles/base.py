"""Base style abstraction for MADVID."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StyleTemplate:
    name: str
    accent: str
    background: str
    secondary: str
    transition: str

    def theme(self) -> dict:
        return {
            "name": self.name,
            "accent": self.accent,
            "background": self.background,
            "secondary": self.secondary,
            "transition": self.transition,
        }
