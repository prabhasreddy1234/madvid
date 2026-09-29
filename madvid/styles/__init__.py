"""Style registry for MADVID visuals."""

from .cinematic import CinematicStyle
from .minimal import MinimalStyle
from .premium import PremiumStyle


def get_style(name: str):
    styles = {"minimal": MinimalStyle(), "cinematic": CinematicStyle(), "premium": PremiumStyle()}
    style = styles.get((name or "minimal").lower())
    if style is None:
        raise ValueError("Unsupported style.")
    return style


__all__ = ["CinematicStyle", "MinimalStyle", "PremiumStyle", "get_style"]
