"""Storyboard generation for MADVID product-intro videos."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .models import ProductContext, StoryboardScene


@dataclass
class Storyboard:
    scenes: list[StoryboardScene]

    def as_markdown(self) -> str:
        lines = ["# Storyboard", "", "| Timestamp | Scene | Visual | Text overlay | Voice-over | Transition | Source asset |", "| --- | --- | --- | --- | --- | --- | --- |"]
        for scene in self.scenes:
            lines.append(
                f"| {scene.timestamp} | {scene.scene} | {scene.visual} | {scene.text_overlay} | {scene.voice_over} | {scene.transition} | {scene.source_asset} |"
            )
        return "\n".join(lines)


def _scene_segment(duration: int, index: int, scenes_total: int) -> tuple[int, int]:
    segment_length = max(3, duration // max(scenes_total, 1))
    start = min(index * segment_length, duration)
    end = min(start + segment_length, duration)
    return start, end


def generate_storyboard(
    product_name: str,
    product_category: str = "Product",
    features: Optional[list[str]] = None,
    duration: int = 20,
) -> list[StoryboardScene]:
    features = features or ["Core workflow", "Useful insights", "Clear outcome"]
    timeline = [
        ("0-3s", "Product reveal", "Hero product shot", f"{product_name}", f"Introducing {product_name}.", "Fade in", "Product splash"),
        ("3-8s", "Primary workflow", "Main product screen", features[0], f"{features[0]} in one place.", "Smooth pan", "Main workflow"),
        ("8-14s", "Feature highlight", "Feature detail screen", features[1], f"{features[1]} that keeps work moving.", "Zoom transition", "Feature asset"),
        ("14-20s", "Outcome and value", "Result dashboard", features[2], f"{product_name} turns complexity into clarity.", "Soft cut", "Outcome visual"),
    ]
    if duration >= 25:
        timeline.insert(3, ("12-16s", "Feature highlight 2", "Secondary screen", "Important action", "Fast and easy to act on.", "Arc transition", "Secondary asset"))
    if duration >= 30:
        timeline.append(("25-30s", "Final CTA", "Brand and action", "Ready to go", "Launch faster with a clearer workflow.", "Brand reveal", "CTA"))
    scenes: list[StoryboardScene] = []
    for timestamp, scene, visual, text_overlay, voice_over, transition, source_asset in timeline:
        if timestamp.endswith("s"):
            scenes.append(
                StoryboardScene(
                    timestamp=timestamp,
                    scene=scene,
                    visual=f"{visual} for {product_name} ({product_category})",
                    text_overlay=text_overlay,
                    voice_over=voice_over,
                    transition=transition,
                    source_asset=source_asset,
                )
            )
    if not scenes:
        scenes.append(
            StoryboardScene(
                timestamp="0-20s",
                scene="Product reveal",
                visual=f"{product_name} product overview",
                text_overlay=product_name,
                voice_over=f"Introducing {product_name}.",
                transition="Fade in",
                source_asset="Primary asset",
            )
        )
    return scenes


def generate_storyboard_from_product(product: ProductContext, duration: int = 20) -> list[StoryboardScene]:
    return generate_storyboard(
        product_name=product.product_name,
        product_category=product.product_category,
        features=product.features,
        duration=duration,
    )
