"""Style registry for MADVID visuals."""

from __future__ import annotations

from .cinematic import CinematicStyle
from .minimal import MinimalStyle
from .premium import PremiumStyle


def get_style(name: str, brand_colors: dict[str, str] | None = None):
    styles = {"minimal": MinimalStyle(), "cinematic": CinematicStyle(), "premium": PremiumStyle()}
    style = styles.get((name or "minimal").lower())
    if style is None:
        raise ValueError("Unsupported style.")
    if brand_colors:
        return style.with_brand_colors(brand_colors)
    return style


__all__ = ["CinematicStyle", "MinimalStyle", "PremiumStyle", "get_style"]
