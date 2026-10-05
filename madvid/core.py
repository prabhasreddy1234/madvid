"""Reusable library entry points for MADVID."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .asset_manager import discover_video_assets, discover_visual_assets
from .project_analyzer import analyze_project
from .providers import LLMProvider, LocalProvider
from .source_resolver import SourceType, resolve_source
from .store_analyzer import analyze_store_url
from .storyboard_generator import generate_storyboard_from_product
from .video_renderer import render_video
from .website_analyzer import analyze_website


def _parse_llm_json(raw: str) -> dict | None:
    """Extract and parse the first JSON object from an LLM response."""
    try:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except (ValueError, TypeError):
        pass
    return None


class MADVID:
    """Core library interface for generating product-introduction videos with any LLM provider."""

    def __init__(self, llm_provider: LLMProvider | None = None):
        self.llm_provider = llm_provider or LocalProvider()

    def _enrich_product(self, product, *, source_label: str | None = None, duration: int = 20) -> object:
        if not hasattr(self.llm_provider, "analyze"):
            return product

        prompt = (
            f"You are a product marketing director. Analyze this product and return a JSON object with these exact keys:\n"
            f"- tagline: a punchy 6-10 word product tagline\n"
            f"- value_proposition: one compelling sentence (max 120 chars) on the core user benefit\n"
            f"- cta: a strong 2-5 word call to action (e.g. 'Start for free', 'See it in action')\n"
            f"- features: list of 3-5 benefit-led feature strings (start with a verb, max 60 chars each)\n"
            f"- scene_hooks: list of 4-6 short punchy scene copy strings for a launch video (max 50 chars each)\n"
            f"- brand_colors: object with 'accent' (primary brand hex), 'background' (dark bg hex), 'secondary' (light text hex)\n"
            f"- target_user: who this product is for (max 40 chars)\n"
            f"- primary_workflow: the single most important thing a user does (max 80 chars)\n"
            f"\nCreate the story for a {duration}-second product intro/demo, within the 15-30 second format. "
            f"Make it motion-led, not a screenshot slideshow: use an animated hook, product reveal, benefit-led workflow, and clear CTA. "
            f"Reserve authentic UI captures for at most two short proof moments; use brand motion graphics elsewhere. "
            f"Ground every claim in the supplied product context and do not invent capabilities.\n"
            f"\nProduct: {getattr(product, 'product_name', 'Product')}\n"
            f"Category: {getattr(product, 'product_category', 'General product')}\n"
            f"Current features: {getattr(product, 'features', [])}\n"
            f"Current value prop: {getattr(product, 'value_proposition', '')}\n"
            f"Source: {source_label}\n"
            f"\nReturn only valid JSON, no markdown fences."
        )
        raw = self.llm_provider.analyze(
            prompt,
            {
                "product_name": getattr(product, "product_name", "Product"),
                "category": getattr(product, "product_category", "General product"),
                "features": getattr(product, "features", []),
                "source_label": source_label,
            },
        )

        parsed = _parse_llm_json(raw)
        if parsed:
            if parsed.get("tagline"):
                product.tagline = str(parsed["tagline"])[:80]
            if parsed.get("value_proposition"):
                product.value_proposition = str(parsed["value_proposition"])[:240]
            if parsed.get("cta"):
                product.cta = str(parsed["cta"])[:60]
            if parsed.get("features") and isinstance(parsed["features"], list):
                product.features = [str(f)[:80] for f in parsed["features"][:5]]
            if parsed.get("scene_hooks") and isinstance(parsed["scene_hooks"], list):
                product.scene_hooks = [str(h)[:60] for h in parsed["scene_hooks"][:6]]
            if parsed.get("brand_colors") and isinstance(parsed["brand_colors"], dict):
                product.brand_colors = {
                    k: v for k, v in parsed["brand_colors"].items()
                    if k in ("accent", "background", "secondary") and isinstance(v, str) and v.startswith("#")
                }
            if parsed.get("target_user"):
                product.target_user = str(parsed["target_user"])[:80]
            if parsed.get("primary_workflow"):
                product.primary_workflow = str(parsed["primary_workflow"])[:120]

        metadata = dict(getattr(product, "metadata", {}))
        metadata["llm_raw"] = raw
        metadata["llm_provider"] = getattr(self.llm_provider, "name", "unknown")
        product.metadata = metadata
        return product

    def generate_from_project(
        self,
        project_root: str = ".",
        *,
        duration: int = 20,
        style: str = "premium",
        preview: bool = False,
        orientation: str = "landscape",
        video_assets: list[str] | None = None,
        voiceover_audio: str | None = None,
        music_audio: str | None = None,
    ) -> dict:
        product = analyze_project(project_root)
        product = self._enrich_product(product, source_label="PROJECT", duration=duration)
        storyboard = generate_storyboard_from_product(product, duration=duration)
        output_dir = str(Path(project_root) / "madvid-output")
        video_path, metadata_path = render_video(
            product_name=product.product_name,
            output_dir=output_dir,
            duration=duration,
            style=style,
            orientation=orientation,
            preview=preview,
            storyboard=storyboard,
            visual_assets=discover_visual_assets(project_root),
            video_assets=discover_video_assets(project_root) if video_assets is None else video_assets,
            voiceover_audio=voiceover_audio,
            music_audio=music_audio,
            brand_colors=product.brand_colors or None,
            tagline=product.tagline or "",
        )
        metadata = json.loads(Path(metadata_path).read_text(encoding="utf-8"))
        metadata["source_type"] = "PROJECT"
        metadata["project_root"] = project_root
        metadata["llm_provider"] = getattr(self.llm_provider, "name", "unknown")
        if product.brand_colors:
            metadata["brand_colors"] = product.brand_colors
        if product.tagline:
            metadata["tagline"] = product.tagline
        Path(metadata_path).write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return {
            "video_path": video_path,
            "metadata_path": metadata_path,
            "storyboard": storyboard,
            "metadata": metadata,
        }

    def generate_from_url(
        self,
        source_url: str,
        *,
        project_root: str = ".",
        duration: int = 20,
        style: str = "premium",
        preview: bool = False,
        orientation: str = "landscape",
        video_assets: list[str] | None = None,
        voiceover_audio: str | None = None,
        music_audio: str | None = None,
    ) -> dict:
        source_type = resolve_source(source_url, project_root=project_root)
        if source_type == SourceType.WEBSITE:
            product = analyze_website(source_url)
        elif source_type in {SourceType.PLAY_STORE, SourceType.APP_STORE}:
            product = analyze_store_url(source_url)
        else:
            product = analyze_project(project_root)
        product = self._enrich_product(product, source_label=source_type.value, duration=duration)
        storyboard = generate_storyboard_from_product(product, duration=duration)
        output_dir = str(Path(project_root) / "madvid-output")
        video_path, metadata_path = render_video(
            product_name=product.product_name,
            output_dir=output_dir,
            duration=duration,
            style=style,
            orientation=orientation,
            preview=preview,
            storyboard=storyboard,
            visual_assets=discover_visual_assets(project_root),
            video_assets=discover_video_assets(project_root) if video_assets is None else video_assets,
            voiceover_audio=voiceover_audio,
            music_audio=music_audio,
            brand_colors=product.brand_colors or None,
            tagline=product.tagline or "",
        )
        metadata = json.loads(Path(metadata_path).read_text(encoding="utf-8"))
        metadata["source_type"] = source_type.value
        metadata["source_url"] = source_url
        metadata["llm_provider"] = getattr(self.llm_provider, "name", "unknown")
        if product.brand_colors:
            metadata["brand_colors"] = product.brand_colors
        if product.tagline:
            metadata["tagline"] = product.tagline
        Path(metadata_path).write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return {
            "video_path": video_path,
            "metadata_path": metadata_path,
            "storyboard": storyboard,
            "metadata": metadata,
        }

    def generate(
        self,
        *,
        project_root: str = ".",
        source_url: str | None = None,
        duration: int = 20,
        style: str = "premium",
        preview: bool = False,
        orientation: str = "landscape",
        video_assets: list[str] | None = None,
        voiceover_audio: str | None = None,
        music_audio: str | None = None,
    ) -> dict:
        if source_url:
            return self.generate_from_url(
                source_url,
                project_root=project_root,
                duration=duration,
                style=style,
                preview=preview,
                orientation=orientation,
                video_assets=video_assets,
                voiceover_audio=voiceover_audio,
                music_audio=music_audio,
            )
        return self.generate_from_project(
            project_root=project_root,
            duration=duration,
            style=style,
            preview=preview,
            orientation=orientation,
            video_assets=video_assets,
            voiceover_audio=voiceover_audio,
            music_audio=music_audio,
        )


def generate_video(
    *,
    project_root: str = ".",
    source_url: str | None = None,
    duration: int = 20,
    style: str = "premium",
    preview: bool = False,
    orientation: str = "landscape",
    llm_provider: LLMProvider | None = None,
    video_assets: list[str] | None = None,
    voiceover_audio: str | None = None,
    music_audio: str | None = None,
) -> dict:
    client = MADVID(llm_provider=llm_provider)
    return client.generate(
        project_root=project_root,
        source_url=source_url,
        duration=duration,
        style=style,
        preview=preview,
        orientation=orientation,
        video_assets=video_assets,
        voiceover_audio=voiceover_audio,
        music_audio=music_audio,
    )
