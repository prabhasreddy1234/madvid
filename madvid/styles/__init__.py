"""Style registry for MADVID visuals."""

from .cinematic import CinematicStyle
from .minimal import MinimalStyle


def get_style(name: str):
    styles = {"minimal": MinimalStyle(), "cinematic": CinematicStyle()}
    style = styles.get((name or "minimal").lower())
    if style is None:
        raise ValueError("Unsupported style.")
    return style


__all__ = ["CinematicStyle", "MinimalStyle", "get_style"]
