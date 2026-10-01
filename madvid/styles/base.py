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

    def with_brand_colors(self, brand_colors: dict[str, str]) -> "StyleTemplate":
        """Return a copy overridden with product brand colors from LLM analysis."""
        return StyleTemplate(
            name=self.name,
            accent=brand_colors.get("accent", self.accent),
            background=brand_colors.get("background", self.background),
            secondary=brand_colors.get("secondary", self.secondary),
            transition=self.transition,
        )
