"""Reusable library entry points for MADVID."""

from __future__ import annotations

import json
from pathlib import Path

from .project_analyzer import analyze_project
from .providers import LLMProvider, LocalProvider
from .source_resolver import SourceType, resolve_source
from .store_analyzer import analyze_store_url
from .storyboard_generator import generate_storyboard_from_product
from .video_renderer import render_video
from .website_analyzer import analyze_website


class MADVID:
    """Core library interface for generating product-introduction videos with any LLM provider."""

    def __init__(self, llm_provider: LLMProvider | None = None):
        self.llm_provider = llm_provider or LocalProvider()

    def _enrich_product(self, product, *, source_label: str | None = None) -> object:
        if hasattr(self.llm_provider, "analyze"):
            summary = self.llm_provider.analyze(
                f"Summarize the product '{getattr(product, 'product_name', 'Product')}' for a 15-30 second marketing video.",
                {
                    "product_name": getattr(product, "product_name", "Product"),
                    "category": getattr(product, "product_category", "General product"),
                    "features": getattr(product, "features", []),
                    "source_label": source_label,
                },
            )
            metadata = dict(getattr(product, "metadata", {}))
            metadata["llm_summary"] = summary
            metadata["llm_provider"] = getattr(self.llm_provider, "name", "unknown")
            product.metadata = metadata
        return product

    def generate_from_project(
        self,
        project_root: str = ".",
        *,
        duration: int = 20,
        style: str = "minimal",
        preview: bool = False,
        orientation: str = "landscape",
    ) -> dict:
        product = analyze_project(project_root)
        product = self._enrich_product(product, source_label="PROJECT")
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
        )
        metadata = json.loads(Path(metadata_path).read_text(encoding="utf-8"))
        metadata["source_type"] = "PROJECT"
        metadata["project_root"] = project_root
        metadata["llm_provider"] = getattr(self.llm_provider, "name", "unknown")
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
        style: str = "minimal",
        preview: bool = False,
        orientation: str = "landscape",
    ) -> dict:
        source_type = resolve_source(source_url, project_root=project_root)
        if source_type == SourceType.WEBSITE:
            product = analyze_website(source_url)
        elif source_type in {SourceType.PLAY_STORE, SourceType.APP_STORE}:
            product = analyze_store_url(source_url)
        else:
            product = analyze_project(project_root)
        product = self._enrich_product(product, source_label=source_type.value)
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
        )
        metadata = json.loads(Path(metadata_path).read_text(encoding="utf-8"))
        metadata["source_type"] = source_type.value
        metadata["source_url"] = source_url
        metadata["llm_provider"] = getattr(self.llm_provider, "name", "unknown")
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
        style: str = "minimal",
        preview: bool = False,
        orientation: str = "landscape",
    ) -> dict:
        if source_url:
            return self.generate_from_url(
                source_url,
                project_root=project_root,
                duration=duration,
                style=style,
                preview=preview,
                orientation=orientation,
            )
        return self.generate_from_project(
            project_root=project_root,
            duration=duration,
            style=style,
            preview=preview,
            orientation=orientation,
        )


def generate_video(
    *,
    project_root: str = ".",
    source_url: str | None = None,
    duration: int = 20,
    style: str = "minimal",
    preview: bool = False,
    orientation: str = "landscape",
    llm_provider: LLMProvider | None = None,
) -> dict:
    client = MADVID(llm_provider=llm_provider)
    return client.generate(
        project_root=project_root,
        source_url=source_url,
        duration=duration,
        style=style,
        preview=preview,
        orientation=orientation,
    )
