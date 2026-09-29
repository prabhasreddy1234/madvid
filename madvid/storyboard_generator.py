"""Storyboard generation for MADVID product-intro videos."""

from __future__ import annotations

from dataclasses import dataclass

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
    features: list[str] | None = None,
    duration: int = 20,
    value_proposition: str = "",
    primary_workflow: str = "",
    cta: str = "Explore the product",
) -> list[StoryboardScene]:
    features = features or ["Explore the core workflow", "Complete key actions", "Reach a clear result"]
    workflow = primary_workflow.strip() or features[0]
    promise = value_proposition.strip() or f"A clearer way to use {product_name}."
    action = cta.strip() or "Explore the product"
    timeline = [
        ("Product reveal", "Hero product screen", product_name, promise, "Product hero"),
        ("Primary workflow", "Core product screen", workflow, workflow, "Core workflow"),
        ("Key benefit", "Product feature in use", features[1] if len(features) > 1 else features[0], features[1] if len(features) > 1 else features[0], "Feature detail"),
        ("Final call to action", "Product and brand close", action, action, "Call to action"),
    ]
    if duration >= 25 and len(features) > 2:
        timeline.insert(-1, ("More to explore", "Another product moment", features[2], features[2], "More features"))

    scenes: list[StoryboardScene] = []
    scene_count = len(timeline)
    transitions = ("Cross dissolve", "Directional push", "Soft wipe", "Light flash", "Cross dissolve")
    for index, (scene, visual, text_overlay, voice_over, source_asset) in enumerate(timeline):
        start = round(duration * index / scene_count)
        end = round(duration * (index + 1) / scene_count)
        scenes.append(
            StoryboardScene(
                timestamp=f"{start}-{end}s",
                scene=scene,
                visual=f"{visual} for {product_name} ({product_category})",
                text_overlay=text_overlay,
                voice_over=voice_over,
                transition=transitions[index % len(transitions)],
                source_asset=source_asset,
            )
        )
    return scenes


def generate_storyboard_from_product(product: ProductContext, duration: int = 20) -> list[StoryboardScene]:
    return generate_storyboard(
        product_name=product.product_name,
        product_category=product.product_category,
        features=product.features,
        duration=duration,
        value_proposition=product.value_proposition,
        primary_workflow=product.primary_workflow,
        cta=product.cta,
    )
