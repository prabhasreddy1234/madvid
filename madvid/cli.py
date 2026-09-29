"""Command-line interface for MADVID."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .asset_manager import ensure_output_dir
from .config import load_config, load_project_config
from .project_analyzer import analyze_project
from .security import filter_sensitive_data
from .source_resolver import SourceType, resolve_source
from .store_analyzer import analyze_store_url
from .storyboard_generator import generate_storyboard_from_product
from .validation import validate_duration, validate_orientation, validate_style
from .video_renderer import render_video
from .website_analyzer import analyze_website


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MADVID: AI Product Introduction Video Generator")
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="Initialize a MADVID project for a specific AI integration")
    init_parser.add_argument("project_name", nargs="?", default=".", help="Name of the project directory to initialize")
    init_parser.add_argument(
        "--integration",
        choices=["generic", "speckit", "copilot", "copilot-cli", "claude", "claude-code", "codex", "codex-cli", "gemini", "gemini-cli", "aider", "aider-cli"],
        default="generic",
        help="Target AI integration or CLI environment",
    )

    parser.add_argument("url", nargs="?", help="Optional URL for website or app store page")
    parser.add_argument("--duration", type=int, help="Video duration in seconds (15-30)")
    parser.add_argument("--voice", action="store_true", help="Enable voice-over")
    parser.add_argument("--no-voice", dest="voice", action="store_false", help="Disable voice-over")
    parser.add_argument("--vertical", dest="orientation", action="store_const", const="vertical", help="Render a vertical video")
    parser.add_argument("--landscape", dest="orientation", action="store_const", const="landscape", help="Render a landscape video")
    parser.add_argument("--preview", action="store_true", help="Generate a quick low-resolution preview")
    parser.add_argument("--style", choices=["minimal", "cinematic"], help="Visual style")
    return parser


def _resolve_cli_config(args: argparse.Namespace) -> dict:
    config = {}
    if args.duration is not None:
        config["defaultDuration"] = args.duration
    if args.style is not None:
        config["defaultStyle"] = args.style
    if getattr(args, "orientation", None) is not None:
        config["defaultOrientation"] = args.orientation
    if "voice" in vars(args):
        config["voice"] = bool(args.voice)
    config["preview"] = bool(args.preview)
    return config


def _safe_product_context(project_root: str, source_type: SourceType) -> dict:
    if source_type == SourceType.PROJECT:
        product = analyze_project(project_root)
        return {
            "product_name": product.product_name,
            "product_category": product.product_category,
            "features": product.features,
            "primary_workflow": product.primary_workflow,
            "value_proposition": product.value_proposition,
            "cta": product.cta,
        }
    return {
        "product_name": "Project Product",
        "product_category": "General product",
        "features": ["Core product flow", "User value", "Clear results"],
        "primary_workflow": "Main user workflow",
        "value_proposition": "Clear product value",
        "cta": "Explore the product",
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if getattr(args, "command", None) == "init":
        project_name = args.project_name or "."
        target_dir = Path(project_name)
        target_dir.mkdir(parents=True, exist_ok=True)
        config_dir = target_dir / ".madvid"
        config_dir.mkdir(parents=True, exist_ok=True)

        integration = args.integration or "generic"
        config_payload = {
            "integration": integration,
            "defaultDuration": 20,
            "defaultStyle": "minimal",
            "defaultOrientation": "landscape",
            "voice": False,
            "preview": False,
        }
        config_path = config_dir / "config.json"
        config_path.write_text(json.dumps(config_payload, indent=2), encoding="utf-8")

        print(f"Initialized MADVID project at {target_dir} for integration '{integration}'.")
        print(f"Next: cd {target_dir} && madvid --preview --duration 20 --style minimal")
        return 0

    project_root = os.getcwd()
    source = resolve_source(getattr(args, "url", None), project_root=project_root)
    if source == SourceType.PROJECT:
        project_cfg = load_project_config(project_root)
    else:
        project_cfg = {}

    cli_overrides = _resolve_cli_config(args)
    cfg = load_config(project_cfg=project_cfg, cli_overrides=cli_overrides)

    try:
        cfg.default_duration = validate_duration(cfg.default_duration)
        cfg.default_orientation = validate_orientation(cfg.default_orientation)
        cfg.default_style = validate_style(cfg.default_style)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    if args.url and not str(args.url).strip():
        raise SystemExit("MADVID could not determine a product source. Run /madvid <url> or execute MADVID inside a project directory.")

    if source == SourceType.WEBSITE and args.url:
        product = analyze_website(args.url)
    elif source in {SourceType.PLAY_STORE, SourceType.APP_STORE} and args.url:
        product = analyze_store_url(args.url)
    else:
        product = analyze_project(project_root) if source == SourceType.PROJECT else None

    if product is None:
        product = analyze_project(project_root) if os.path.exists(os.path.join(project_root, "package.json")) or os.path.exists(os.path.join(project_root, "build.gradle")) else None

    if product is None:
        product = type("Fallback", (), {"product_name": "Example Product", "product_category": "Productivity", "features": ["Core workflow", "Simple steps", "Clear outcomes"], "primary_workflow": "Main workflow", "value_proposition": "Streamlined product value", "cta": "Get started"})()

    storyboard = generate_storyboard_from_product(product, duration=cfg.default_duration)
    filtered_storyboard = [
        {
            "timestamp": scene.timestamp,
            "scene": filter_sensitive_data(scene.scene),
            "visual": filter_sensitive_data(scene.visual),
            "text_overlay": filter_sensitive_data(scene.text_overlay),
            "voice_over": filter_sensitive_data(scene.voice_over),
            "transition": filter_sensitive_data(scene.transition),
            "source_asset": filter_sensitive_data(scene.source_asset),
        }
        for scene in storyboard
    ]

    output_dir = ensure_output_dir("madvid-output")
    product_intro_path, metadata_path = render_video(
        product_name=product.product_name,
        output_dir=str(output_dir),
        duration=cfg.default_duration,
        style=cfg.default_style,
        orientation=cfg.default_orientation,
        preview=cfg.preview,
        storyboard=storyboard,
    )
    storyboard_path = output_dir / "storyboard.md"
    storyboard_path.write_text(
        "# Storyboard\n\n" + "\n\n".join(
            f"{scene['timestamp']} - {scene['scene']}\nVisual: {scene['visual']}\nText: {scene['text_overlay']}\nVoice-over: {scene['voice_over']}\nTransition: {scene['transition']}\nSource asset: {scene['source_asset']}"
            for scene in filtered_storyboard
        ),
        encoding="utf-8",
    )
    voice_path = output_dir / "voiceover.txt"
    if cfg.voice:
        first_voice = " ".join(scene["voice_over"] for scene in filtered_storyboard[:3])
        voice_path.write_text(first_voice, encoding="utf-8")
    else:
        voice_path.write_text("Voice-over disabled.", encoding="utf-8")

    metadata_path = Path(metadata_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["sourceType"] = source.value
    metadata["outputPath"] = str(product_intro_path)
    metadata["storyboardPath"] = str(storyboard_path)
    metadata["voiceoverPath"] = str(voice_path)
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    source_label = source.value if source else "PROJECT"
    print("MADVID")
    print("------")
    print(f"Source: {source_label}")
    print(f"Product: {product.product_name}")
    print(f"Duration: {cfg.default_duration}s")
    print(f"Style: {cfg.default_style}")
    print(f"Resolution: {metadata['resolution']}")
    print(f"Output: {product_intro_path}")
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
