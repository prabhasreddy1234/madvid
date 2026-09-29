"""Local-friendly video composition pipeline for MADVID."""

from __future__ import annotations

import json
from pathlib import Path

import imageio.v3 as iio
from PIL import Image, ImageDraw, ImageFont

from .asset_manager import ensure_output_dir, write_json
from .styles import get_style


def _resolve_resolution(orientation: str, preview: bool = False) -> tuple[int, int]:
    if orientation == "vertical":
        width, height = (1080, 1920)
    else:
        width, height = (1920, 1080)
    if preview:
        width = max(480, width // 2)
        height = max(270, height // 2)
    return width, height


def _make_frame(width: int, height: int, product_name: str, style_name: str, frame_index: int, total_frames: int) -> Image.Image:
    style = get_style(style_name)
    img = Image.new("RGB", (width, height), style.background)
    draw = ImageDraw.Draw(img)
    accent = style.accent
    overlay = style.secondary
    # soft gradient bands
    for y in range(0, height, 20):
        color = (30 + y // 20, 41, 59) if y % 40 == 0 else (15, 23, 42)
        draw.rectangle((0, y, width, y + 20), fill=color)
    # product block
    pad = 80
    card_left = width // 6
    card_top = height // 5
    card_w = width - 2 * card_left
    card_h = height - 2 * card_top
    draw.rounded_rectangle((card_left, card_top, card_left + card_w, card_top + card_h), radius=30, fill=(15, 23, 42), outline=accent)
    # accent bar
    draw.rounded_rectangle((card_left + 40, card_top + 50, card_left + 180, card_top + 90), radius=12, fill=accent)
    # title lines
    title = product_name[:24]
    draw.text((card_left + 40, card_top + 120), title, fill=overlay, font=None)
    draw.text((card_left + 40, card_top + 200), "AI product introduction", fill=(180, 180, 180), font=None)
    # mock UI cards
    for i in range(4):
        x = card_left + 50 + (i % 2) * 260
        y = card_top + 300 + (i // 2) * 140
        draw.rounded_rectangle((x, y, x + 220, y + 90), radius=18, fill=(35, 56, 88), outline=(80, 80, 80))
        draw.text((x + 20, y + 25), f"Feature {i + 1}", fill=overlay, font=None)
    # progress line
    progress = (frame_index / max(total_frames, 1)) * width
    draw.rectangle((0, height - 30, progress, height), fill=accent)
    return img


def render_video(
    product_name: str,
    output_dir: str = "madvid-output",
    duration: int = 20,
    style: str = "minimal",
    orientation: str = "landscape",
    preview: bool = False,
    storyboard: list | None = None,
) -> tuple[str, str]:
    output_path = ensure_output_dir(output_dir)
    width, height = _resolve_resolution(orientation, preview=preview)
    fps = 24
    total_frames = fps * duration
    video_name = "preview.mp4" if preview else "product-intro.mp4"
    video_path = output_path / video_name
    writer = iio.get_writer(str(video_path), fps=fps, codec="libx264", quality=8)
    for index in range(total_frames):
        frame = _make_frame(width, height, product_name, style, index, total_frames)
        writer.append_data(frame)
    writer.close()
    metadata = {
        "productName": product_name,
        "duration": duration,
        "orientation": orientation,
        "style": style,
        "resolution": f"{width}x{height}",
        "preview": preview,
    }
    if storyboard:
        metadata["storyboardCount"] = len(storyboard)
    write_json(output_path / "metadata.json", metadata)
    return str(video_path), str(output_path / "metadata.json")
