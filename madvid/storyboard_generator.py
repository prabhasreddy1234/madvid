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
    tagline: str = "",
    scene_hooks: list[str] | None = None,
) -> list[StoryboardScene]:
    features = features or ["Explore the core workflow", "Complete key actions", "Reach a clear result"]
    workflow = primary_workflow.strip() or features[0]
    promise = value_proposition.strip() or f"A clearer way to use {product_name}."
    hook = tagline.strip() or promise
    action = cta.strip() or "Explore the product"
    hooks = list(scene_hooks or [])
    key_features = features[1:] if workflow == features[0] else features
    key_features = (key_features or [workflow])[:3 if duration >= 25 else 2]
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

    def visual(screen_index: int, direction: str, use_capture: bool = False) -> str:
        screen = screens[min(screen_index, len(screens) - 1)]
        product_context = f"{product_name} ({product_category}){audience}"
        if use_capture:
            return (
                f"{identity}Motion-led product introduction for {product_context}; {direction}. "
                f"Use one brief authentic {capture_type.lower()} of {screen} as workflow proof, "
                "framed with animated camera movement and restrained interface highlights."
            )
        return (
            f"{identity}Motion-led product introduction for {product_context}; {direction}. "
            "Build the visual from animated typography, brand shapes, and interface-inspired motion; "
            "do not use a screenshot in this scene."
        )

    def _hook(index: int, fallback: str) -> str:
        return hooks[index] if index < len(hooks) else fallback

    timeline = [
        (
            "Opening hook",
            visual(0, "Lead with the product promise through a confident animated opening"),
            hook,
            hook,
            "Product hook",
            False,
        ),
        (
            "Product reveal",
            visual(0, "Reveal the product name and brand identity"),
            product_name,
            "",
            "Product hero",
            False,
        ),
        (
            "Primary workflow",
            visual(1, "Show the primary workflow as the key proof point", use_capture=True),
            _hook(2, workflow),
            _hook(2, workflow),
            "Core workflow",
            True,
        ),
    ]
    for feature_index, feature in enumerate(key_features):
        timeline.append(
            (
                "Feature spotlight",
                visual(
                    2 + feature_index,
                    "Animate the feature benefit and let the value read",
                    use_capture=feature_index == 0,
                ),
                _hook(3 + feature_index, feature),
                _hook(3 + feature_index, feature),
                f"Feature {feature_index + 1}",
                feature_index == 0,
            )
        )
    timeline.append(
        (
            "Final call to action",
            visual(len(screens) - 1, "Close on the brand with a clear animated call to action"),
            action,
            "",
            "Call to action",
            False,
        )
    )

    scenes: list[StoryboardScene] = []
    scene_count = len(timeline)
    transitions = ("Cross dissolve", "Cross dissolve", "Directional push", "Cross dissolve", "Soft wipe")
    for index, (scene, visual, text_overlay, voice_over, source_asset, use_capture) in enumerate(timeline):
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
                use_product_capture=use_capture,
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
        tagline=product.tagline,
        scene_hooks=product.scene_hooks,
    )
