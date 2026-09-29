"""Shared dataclasses for MADVID."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StoryboardScene:
    timestamp: str
    scene: str
    visual: str
    text_overlay: str
    voice_over: str
    transition: str
    source_asset: str
    camera_focus: tuple[float, float] = (0.5, 0.5)
    highlight_box: tuple[float, float, float, float] | None = None
    cursor_target: tuple[float, float] | None = None
    cursor_click: bool = False

    def as_markdown(self) -> str:
        lines = [
            f"{self.timestamp}",
            f"{self.scene}",
            f"Visual: {self.visual}",
            f"Text: {self.text_overlay}",
            f"Voice-over: {self.voice_over}",
            f"Transition: {self.transition}",
            f"Source asset: {self.source_asset}",
            "",
        ]
        return "\n".join(lines)


@dataclass
class ProductContext:
    product_name: str
    product_category: str = "General product"
    target_user: str = "Product users"
    value_proposition: str = "Clear and useful product experience"
    primary_workflow: str = "Main product workflow"
    features: list[str] = field(default_factory=list)
    visual_identity: str = "Clean and modern product UI"
    important_screens: list[str] = field(default_factory=list)
    cta: str = "Get started"
    source_type: str = "PROJECT"
    source_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
