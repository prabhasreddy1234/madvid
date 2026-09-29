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
    source_type: str = "PROJECT",
    important_screens: list[str] | None = None,
    visual_identity: str = "",
    target_user: str = "",
) -> list[StoryboardScene]:
    features = features or ["Explore the core workflow", "Complete key actions", "Reach a clear result"]
    workflow = primary_workflow.strip() or features[0]
    promise = value_proposition.strip() or f"A clearer way to use {product_name}."
    action = cta.strip() or "Explore the product"
    source_label = source_type.upper()
    if source_label == "WEBSITE":
        capture_type = "Website screen"
    elif source_label in {"PLAY_STORE", "APP_STORE"} or any(
        marker in product_category.lower() for marker in ("app", "android", "ios", "mobile")
    ):
        capture_type = "Mobile app screen"
    else:
        capture_type = "Product screen"
    screens = important_screens or ["Product overview", "Primary workflow", "Outcome"]
    identity = f"{visual_identity.strip()}; " if visual_identity.strip() else ""
    audience = f" for {target_user.strip()}" if target_user.strip() else ""

    def visual(screen_index: int, direction: str) -> str:
        screen = screens[min(screen_index, len(screens) - 1)]
        return (
            f"{identity}{capture_type}: {screen} for {product_name} "
            f"({product_category}){audience}; {direction}"
        )

    timeline = [
        (
            "Product reveal",
            visual(0, "Open on the strongest product view and establish the promise"),
            product_name,
            promise,
            "Product hero",
        ),
        (
            "Primary workflow",
            visual(1, "Show the primary workflow clearly, using authentic product UI"),
            workflow,
            workflow,
            "Core workflow",
        ),
        (
            "Key benefit",
            visual(2, "Reveal the useful outcome or strongest supporting feature"),
            features[1] if len(features) > 1 else features[0],
            features[1] if len(features) > 1 else features[0],
            "Feature detail",
        ),
        (
            "Final call to action",
            visual(len(screens) - 1, "Close on the product and leave the call to action clear"),
            action,
            action,
            "Call to action",
        ),
    ]
    if duration >= 25 and len(features) > 2:
        timeline.insert(
            -1,
            (
                "More to explore",
                visual(2, "Show another distinct product moment without repeating the previous shot"),
                features[2],
                features[2],
                "More features",
            ),
        )

    scenes: list[StoryboardScene] = []
    scene_count = len(timeline)
    transitions = ("Cross dissolve", "Directional push", "Cross dissolve", "Soft wipe", "Cross dissolve")
    for index, (scene, visual, text_overlay, voice_over, source_asset) in enumerate(timeline):
        start = round(duration * index / scene_count)
        end = round(duration * (index + 1) / scene_count)
        scenes.append(
            StoryboardScene(
                timestamp=f"{start}-{end}s",
                scene=scene,
                visual=visual,
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
        source_type=product.source_type,
        important_screens=product.important_screens,
        visual_identity=product.visual_identity,
        target_user=product.target_user,
    )
