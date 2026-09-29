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


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and draw.textbbox((0, 0), candidate, font=font)[2] > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


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
    eased = progress * progress * (3 - 2 * progress)
    frame = Image.new("RGB", (width, height), background)
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_left = int(width * (0.48 if scene_index % 2 == 0 else -0.45))
    glow_draw.ellipse(
        (glow_left, -int(height * 0.9), glow_left + int(width * 0.97), int(height * 0.7)),
        fill=(*accent, 24),
    )
    frame = Image.alpha_composite(frame.convert("RGBA"), glow).convert("RGB")
    draw = ImageDraw.Draw(frame)
    horizontal = width >= height
    pad_x = int(width * (0.055 if horizontal else 0.07))
    pad_y = int(height * (0.055 if horizontal else 0.04))
    small_font = _font(max(12, int(height * 0.022)), True)
    draw.text((pad_x, pad_y), product_name.upper()[:36], fill=foreground, font=small_font)
    draw.text(
        (width - pad_x, pad_y),
        f"{scene_index + 1:02d}  /  {scene_count:02d}",
        fill=(175, 181, 190),
        font=_font(max(11, int(height * 0.019))),
        anchor="ra",
    )

    if horizontal:
        if scene_index % 2 == 0:
            panel = (int(width * 0.055), int(height * 0.19), int(width * 0.59), int(height * 0.84))
            text_x = int(width * 0.68)
            text_width = int(width * 0.26)
            text_top = int(height * 0.29)
        else:
            panel = (int(width * 0.405), int(height * 0.19), int(width * 0.945), int(height * 0.84))
            text_x = int(width * 0.055)
            text_width = int(width * 0.30)
            text_top = int(height * 0.29)
        if scene_index == scene_count - 1 and scene_count > 1:
            panel = (int(width * 0.48), int(height * 0.22), int(width * 0.945), int(height * 0.78))
            text_x = int(width * 0.075)
            text_width = int(width * 0.34)
            text_top = int(height * 0.32)
    else:
        text_x = pad_x
        text_width = width - pad_x * 2
        if scene_index % 2 == 0:
            panel = (int(width * 0.055), int(height * 0.13), int(width * 0.945), int(height * 0.61))
            text_top = int(height * 0.68)
        else:
            panel = (int(width * 0.055), int(height * 0.36), int(width * 0.945), int(height * 0.83))
            text_top = int(height * 0.15)

    left, top, right, bottom = panel
    panel_width = right - left
    panel_height = bottom - top
    radius = max(8, int(min(width, height) * 0.018))
    shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (left, top + max(4, int(height * 0.012)), right, bottom + max(4, int(height * 0.012))),
        radius=radius,
        fill=(0, 0, 0, 120),
    )
    frame = Image.alpha_composite(frame.convert("RGBA"), shadow)

    mobile_capture = image is not None and image.height / image.width > 1.15
    chrome_height = 0 if mobile_capture else max(22, int(panel_height * 0.085))
    panel_layer = Image.new("RGBA", (panel_width, panel_height), (0, 0, 0, 0))
    panel_draw = ImageDraw.Draw(panel_layer)
    panel_fill = (27, 31, 38, 255) if mobile_capture else (244, 246, 248, 255)
    panel_draw.rounded_rectangle((0, 0, panel_width - 1, panel_height - 1), radius=radius, fill=panel_fill)
    if mobile_capture:
        inset = max(3, int(min(panel_width, panel_height) * 0.018))
        fitted = ImageOps.contain(
            image,
            (int(panel_width * 0.52) - inset * 2, int(panel_height * 0.88) - inset * 2),
            method=Image.Resampling.LANCZOS,
        )
        zoom = 1.0 + 0.045 * eased
        fitted = fitted.resize(
            (max(1, int(fitted.width * zoom)), max(1, int(fitted.height * zoom))),
            Image.Resampling.LANCZOS,
        )
        bezel_x = max(3, int(fitted.width * 0.04))
        bezel_y = max(5, int(fitted.height * 0.035))
        device_width = fitted.width + bezel_x * 2
        device_height = fitted.height + bezel_y * 2
        device_x = (panel_width - device_width) // 2
        device_y = (panel_height - device_height) // 2
        device_radius = max(8, int(device_width * 0.12))
        panel_draw.rounded_rectangle(
            (device_x, device_y, device_x + device_width - 1, device_y + device_height - 1),
            radius=device_radius,
            fill=(9, 11, 14, 255),
        )
        screen_x = device_x + bezel_x
        screen_y = device_y + bezel_y
        screen_mask = Image.new("L", fitted.size, 0)
        ImageDraw.Draw(screen_mask).rounded_rectangle(
            (0, 0, fitted.width - 1, fitted.height - 1),
            radius=max(4, int(device_width * 0.035)),
            fill=255,
        )
        panel_layer.paste(fitted.convert("RGBA"), (screen_x, screen_y), screen_mask)
        speaker_width = max(8, int(device_width * 0.17))
        speaker_height = max(2, int(bezel_y * 0.18))
        speaker_x = panel_width // 2 - speaker_width // 2
        speaker_y = device_y + max(1, (bezel_y - speaker_height) // 2)
        panel_draw.rounded_rectangle(
            (speaker_x, speaker_y, speaker_x + speaker_width, speaker_y + speaker_height),
            radius=speaker_height,
            fill=(48, 52, 58, 255),
        )
    else:
        panel_draw.rectangle((0, chrome_height // 2, panel_width - 1, chrome_height), fill=(244, 246, 248, 255))
        panel_draw.rectangle((1, chrome_height + 1, panel_width - 2, panel_height - 2), fill=(25, 29, 36, 255))
        dot_radius = max(2, chrome_height // 9)
        for dot_index, dot_color in enumerate(((245, 96, 86, 255), (246, 187, 66, 255), (57, 190, 112, 255))):
            dot_x = int(chrome_height * 0.55) + dot_index * dot_radius * 3
            panel_draw.ellipse((dot_x - dot_radius, chrome_height // 2 - dot_radius, dot_x + dot_radius, chrome_height // 2 + dot_radius), fill=dot_color)
    if image is not None and not mobile_capture:
        viewport = (panel_width - 2, panel_height - chrome_height - 2)
        fitted = ImageOps.contain(image, viewport, method=Image.Resampling.LANCZOS)
        zoom = 1.0 + 0.045 * eased
        zoomed = fitted.resize(
            (max(1, int(fitted.width * zoom)), max(1, int(fitted.height * zoom))),
            Image.Resampling.LANCZOS,
        )
        image_x = max(0, (panel_width - zoomed.width) // 2 - int((eased - 0.5) * panel_width * 0.012))
        image_y = chrome_height + max(0, (viewport[1] - zoomed.height) // 2 - int((eased - 0.5) * panel_height * 0.012))
        panel_layer.alpha_composite(zoomed.convert("RGBA"), (image_x, image_y))
    elif image is None:
        preview_font = _font(max(12, int(height * 0.02)), True)
        panel_draw.text(
            (panel_width // 2, chrome_height + (panel_height - chrome_height) // 2),
            "PRODUCT PREVIEW",
            fill=(142, 149, 160, 255),
            font=preview_font,
            anchor="mm",
        )
    panel_mask = Image.new("L", (panel_width, panel_height), 0)
    ImageDraw.Draw(panel_mask).rounded_rectangle((0, 0, panel_width - 1, panel_height - 1), radius=radius, fill=255)
    panel_layer.putalpha(panel_mask)
    if 0.16 < progress < 0.74:
        sweep_progress = (progress - 0.16) / 0.58
        sweep_x = int(sweep_progress * (panel_width + 80)) - 40
        sheen = Image.new("RGBA", (panel_width, panel_height), (0, 0, 0, 0))
        sheen_draw = ImageDraw.Draw(sheen)
        sheen_draw.polygon(
            (
                (sweep_x - 24, chrome_height),
                (sweep_x - 8, chrome_height),
                (sweep_x + 30, panel_height),
                (sweep_x + 14, panel_height),
            ),
            fill=(255, 255, 255, 20),
        )
        panel_layer.alpha_composite(sheen)
    panel_scale = 0.97 + 0.03 * eased
    scaled_size = (max(1, int(panel_width * panel_scale)), max(1, int(panel_height * panel_scale)))
    animated_panel = panel_layer.resize(scaled_size, Image.Resampling.LANCZOS)
    panel_x = left + (panel_width - scaled_size[0]) // 2 - int(width * 0.008 * (1.0 - eased))
    panel_y = top + (panel_height - scaled_size[1]) // 2 + int(height * 0.008 * (1.0 - eased))
    frame.alpha_composite(animated_panel, (panel_x, panel_y))
    draw = ImageDraw.Draw(frame)
    scene_label = getattr(scene, "scene", "Product overview")

    headline = getattr(scene, "text_overlay", "") or product_name
    description = getattr(scene, "voice_over", "")
    label_font = _font(max(12, int(height * (0.021 if horizontal else 0.019))), True)
    title_size = max(22, int(height * (0.062 if horizontal else 0.052)))
    title_font = _font(title_size, True)
    while title_size > 22 and draw.textbbox((0, 0), "Ag", font=title_font)[3] > height * (0.095 if horizontal else 0.065):
        title_size -= 2
        title_font = _font(title_size, True)
    description_size = max(13, int(height * (0.024 if horizontal else 0.021)))
    description_font = _font(description_size)
    text_alpha = int(255 * min(1.0, max(0.0, (progress - 0.04) / 0.2)))
    text_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)
    lift = int(height * 0.018 * (1.0 - eased))
    text_draw.text((text_x, text_top + lift), scene_label.upper()[:32], fill=(*accent, text_alpha), font=label_font)
    title_y = text_top + int(height * (0.052 if horizontal else 0.043)) + lift
    title_lines = _wrap_text(text_draw, headline[:90], title_font, text_width)
    title_line_height = int(title_size * 1.12)
    for line_index, line in enumerate(title_lines[:3]):
        text_draw.text((text_x, title_y + line_index * title_line_height), line, fill=(*foreground, text_alpha), font=title_font)
    if description:
        description_y = title_y + min(len(title_lines), 3) * title_line_height + int(height * 0.018)
        description_lines = _wrap_text(text_draw, description[:180], description_font, text_width)
        for line_index, line in enumerate(description_lines[:3]):
            text_draw.text(
                (text_x, description_y + line_index * int(description_size * 1.45)),
                line,
                fill=(206, 211, 219, int(text_alpha * 0.88)),
                font=description_font,
            )
    frame = Image.alpha_composite(frame, text_layer)
    draw = ImageDraw.Draw(frame)
    progress_y = height - max(8, int(height * 0.025))
    draw.rounded_rectangle((pad_x, progress_y, width - pad_x, progress_y + max(2, height // 240)), radius=2, fill=(255, 255, 255, 55))
    progress_width = int((width - pad_x * 2) * ((scene_index + eased) / max(scene_count, 1)))
    draw.rounded_rectangle((pad_x, progress_y, pad_x + progress_width, progress_y + max(2, height // 240)), radius=2, fill=accent)
    return frame.convert("RGB")


def _apply_transition(previous: Image.Image, current: Image.Image, progress: float, transition: str) -> Image.Image:
    eased = progress * progress * (3 - 2 * progress)
    transition_name = transition.lower()
    width, height = current.size
    if "push" in transition_name:
        offset = int(width * eased)
        frame = Image.new("RGB", current.size)
        frame.paste(previous, (-offset, 0))
        frame.paste(current, (width - offset, 0))
        return frame
    if "wipe" in transition_name:
        frame = previous.copy()
        wipe_width = int(width * eased)
        frame.paste(current.crop((0, 0, wipe_width, height)), (0, 0))
        return frame

    frame = Image.blend(previous, current, eased)
    if "flash" in transition_name:
        flash_alpha = int(150 * max(0.0, 1.0 - abs(progress - 0.5) * 2))
        flash = Image.new("RGB", current.size, (255, 255, 255))
        frame = Image.blend(frame, flash, flash_alpha / 255)
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
        transition = getattr(scenes[scene_index], "transition", "Cross dissolve") if scenes else "Cross dissolve"
        transition_progress = min(1.0, local_frame / transition_frames)
        current = _apply_transition(previous, current, transition_progress, transition)
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
