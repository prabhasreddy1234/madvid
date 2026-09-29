"""Local-friendly video composition pipeline for MADVID."""

from __future__ import annotations

from functools import lru_cache

import imageio.v2 as iio
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

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


@lru_cache(maxsize=32)
def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        "/System/Library/Fonts/Supplemental/Avenir Next.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _rgb(color: str) -> tuple[int, int, int]:
    value = color.lstrip("#")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def _compose_shot(
    width: int,
    height: int,
    product_name: str,
    style_name: str,
    image: Image.Image | None,
    scene: object | None,
    scene_index: int,
    scene_count: int,
    progress: float,
) -> Image.Image:
    style = get_style(style_name)
    background = _rgb(style.background)
    accent = _rgb(style.accent)
    foreground = _rgb(style.secondary)
    frame = Image.new("RGB", (width, height), background)

    if image is not None:
        margin_x = int(width * 0.035)
        margin_top = int(height * 0.035)
        caption_height = int(height * 0.24)
        viewport = (width - margin_x * 2, height - margin_top - caption_height)
        fitted = ImageOps.contain(image, viewport, method=Image.Resampling.LANCZOS)
        eased = progress * progress * (3 - 2 * progress)
        zoom = 1.0 + 0.035 * eased
        zoomed = fitted.resize(
            (max(1, int(fitted.width * zoom)), max(1, int(fitted.height * zoom))),
            Image.Resampling.LANCZOS,
        )
        x = (width - zoomed.width) // 2 - int((eased - 0.5) * width * 0.006)
        y = margin_top + (viewport[1] - zoomed.height) // 2 - int((eased - 0.5) * height * 0.006)
        frame.paste(zoomed, (x, y))

    shade = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    shade_draw = ImageDraw.Draw(shade)
    caption_top = int(height * 0.76)
    for y in range(caption_top, height):
        alpha = int(205 * ((y - caption_top) / max(height - caption_top, 1)) ** 0.6)
        shade_draw.line((0, y, width, y), fill=(0, 0, 0, alpha))
    frame = Image.alpha_composite(frame.convert("RGBA"), shade).convert("RGB")
    draw = ImageDraw.Draw(frame)

    pad_x = int(width * 0.065)
    pad_y = int(height * 0.055)
    draw.text((pad_x, pad_y), product_name.upper()[:36], fill=foreground, font=_font(max(14, int(height * 0.025)), True))
    draw.text(
        (width - pad_x, pad_y),
        f"{scene_index + 1:02d}  /  {scene_count:02d}",
        fill=(210, 210, 210),
        font=_font(max(12, int(height * 0.021))),
        anchor="ra",
    )
    draw.line((pad_x, pad_y + int(height * 0.045), width - pad_x, pad_y + int(height * 0.045)), fill=(255, 255, 255, 90), width=max(1, width // 1200))

    scene_label = getattr(scene, "scene", "Product overview")
    headline = getattr(scene, "text_overlay", "") or product_name
    description = getattr(scene, "voice_over", "")
    caption_y = caption_top + int(height * 0.055)
    label_font = _font(max(13, int(height * 0.022)), True)
    title_text = headline[:56]
    title_size = max(24, int(height * 0.058))
    title_font = _font(title_size, True)
    while title_size > 24 and draw.textbbox((0, 0), title_text, font=title_font)[2] > width * 0.86:
        title_size -= 2
        title_font = _font(title_size, True)
    description_text = description[:90]
    description_size = max(14, int(height * 0.023))
    description_font = _font(description_size)
    while description_size > 14 and draw.textbbox((0, 0), description_text, font=description_font)[2] > width * 0.86:
        description_size -= 2
        description_font = _font(description_size)
    draw.text((pad_x, caption_y), scene_label.upper(), fill=accent, font=label_font)
    title_y = caption_y + int(height * 0.04)
    draw.text((pad_x, title_y), title_text, fill=foreground, font=title_font)
    if description:
        description_y = title_y + int(height * 0.075)
        draw.text((pad_x, description_y), description_text, fill=(220, 224, 230), font=description_font)

    return frame


def _make_frame(
    width: int,
    height: int,
    product_name: str,
    style_name: str,
    frame_index: int,
    total_frames: int,
    visual_images: list[Image.Image] | None = None,
    storyboard: list | None = None,
) -> Image.Image:
    images = visual_images or []
    scenes = storyboard or []
    shot_count = max(len(images), len(scenes), 1)
    frames_per_shot = max(total_frames / shot_count, 1)
    shot_index = min(int(frame_index / frames_per_shot), shot_count - 1)
    shot_progress = min(1.0, max(0.0, (frame_index - shot_index * frames_per_shot) / frames_per_shot))
    image_index = min(shot_index * len(images) // shot_count, len(images) - 1) if images else None
    scene_index = min(shot_index * len(scenes) // shot_count, len(scenes) - 1) if scenes else None
    current = _compose_shot(
        width, height, product_name, style_name,
        images[image_index] if image_index is not None else None,
        scenes[scene_index] if scene_index is not None else None,
        shot_index, shot_count, shot_progress,
    )

    transition_frames = min(int(24 * 0.45), max(1, int(frames_per_shot // 3)))
    local_frame = frame_index - shot_index * frames_per_shot
    if shot_index > 0 and local_frame < transition_frames:
        previous_index = shot_index - 1
        previous_image_index = min(previous_index * len(images) // shot_count, len(images) - 1) if images else None
        previous_scene_index = min(previous_index * len(scenes) // shot_count, len(scenes) - 1) if scenes else None
        previous = _compose_shot(
            width, height, product_name, style_name,
            images[previous_image_index] if previous_image_index is not None else None,
            scenes[previous_scene_index] if previous_scene_index is not None else None,
            previous_index, shot_count, 1.0,
        )
        blend = min(1.0, local_frame / transition_frames)
        current = Image.blend(previous, current, blend)
    return current


def render_video(
    product_name: str,
    output_dir: str = "madvid-output",
    duration: int = 20,
    style: str = "minimal",
    orientation: str = "landscape",
    preview: bool = False,
    storyboard: list | None = None,
    visual_assets: list[str] | None = None,
) -> tuple[str, str]:
    output_path = ensure_output_dir(output_dir)
    width, height = _resolve_resolution(orientation, preview=preview)
    fps = 24
    total_frames = fps * duration
    video_name = "preview.mp4" if preview else "product-intro.mp4"
    video_path = output_path / video_name
    visual_images: list[Image.Image] = []
    for asset_path in visual_assets or []:
        try:
            with Image.open(asset_path) as image:
                visual_images.append(ImageOps.exif_transpose(image).convert("RGB"))
        except (OSError, ValueError):
            continue
    if not visual_images and not preview:
        raise ValueError(
            "A final product video requires real product screenshots. Add captures to "
            "assets/screenshots/ (or screenshots/, screens/, or public/)."
        )
    writer = iio.get_writer(str(video_path), fps=fps, codec="libx264", quality=8, macro_block_size=1)
    for index in range(total_frames):
        frame = _make_frame(width, height, product_name, style, index, total_frames, visual_images, storyboard)
        writer.append_data(np.asarray(frame))
    writer.close()
    metadata = {
        "productName": product_name,
        "duration": duration,
        "orientation": orientation,
        "style": style,
        "resolution": f"{width}x{height}",
        "preview": preview,
        "visualSource": "product_screenshots" if visual_images else "no_product_screenshots",
        "visualAssetCount": len(visual_images),
    }
    if storyboard:
        metadata["storyboardCount"] = len(storyboard)
    write_json(output_path / "metadata.json", metadata)
    return str(video_path), str(output_path / "metadata.json")
