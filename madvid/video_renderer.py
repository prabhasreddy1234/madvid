"""Video composition pipeline for MADVID."""

from __future__ import annotations

import math
import os
import subprocess
import tempfile
import wave
from functools import lru_cache
from pathlib import Path

import imageio.v2 as iio
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

from .asset_manager import ensure_output_dir, write_json
from .styles import get_style

_NO_PRODUCT_VISUALS = (
    "A final product video requires real product screenshots or product screen recordings. "
    "Add captures to assets/screenshots/ or recordings to assets/videos/."
)


def _ffmpeg_available() -> bool:
    try:
        import imageio_ffmpeg as _iff
        exe = _iff.get_ffmpeg_exe()
        result = subprocess.run(
            [exe, "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        # Require xfade filter (FFmpeg 4.3+)
        probe = subprocess.run(
            [exe, "-filters"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        return result.returncode == 0 and b"xfade" in probe.stdout
    except Exception:
        return False


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


def _compose_premium_shot(
    width: int,
    height: int,
    image: Image.Image | None,
    scene: object | None,
    progress: float,
    style_name: str = "premium",
    brand_colors: dict[str, str] | None = None,
) -> Image.Image:
    style = get_style(style_name, brand_colors)
    accent = _rgb(style.accent)
    eased = progress * progress * (3 - 2 * progress)
    frame = Image.new("RGB", (width, height), _rgb(style.background))
    draw = ImageDraw.Draw(frame)
    top_color = _rgb(style.background)
    bottom_color = (27, 24, 43)
    for band in range(32):
        blend = band / 31
        color = tuple(int(top_color[channel] * (1 - blend) + bottom_color[channel] * blend) for channel in range(3))
        y0 = band * height // 32
        y1 = (band + 1) * height // 32
        draw.rectangle((0, y0, width, y1), fill=color)

    panel_width = int(width * 0.88)
    panel_height = int(height * (0.76 if style_name == "cinematic" else 0.78))
    panel_left = (width - panel_width) // 2
    panel_top = int(height * (0.13 if style_name == "cinematic" else 0.045))
    radius = max(8, int(min(width, height) * 0.014))
    shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (panel_left, panel_top + max(5, height // 90), panel_left + panel_width, panel_top + panel_height + max(5, height // 90)),
        radius=radius,
        fill=(0, 0, 0, 115),
    )
    frame = Image.alpha_composite(frame.convert("RGBA"), shadow)

    focus = getattr(scene, "camera_focus", (0.5, 0.5))
    focus_x = min(0.98, max(0.02, 0.5 + (focus[0] - 0.5) * eased))
    focus_y = min(0.98, max(0.02, 0.5 + (focus[1] - 0.5) * eased))
    zoom = 1.015 + 0.13 * eased
    if image is not None:
        camera = ImageOps.fit(
            image,
            (max(panel_width, int(panel_width * zoom)), max(panel_height, int(panel_height * zoom))),
            method=Image.Resampling.LANCZOS,
            centering=(focus_x, focus_y),
        )
        crop_left = (camera.width - panel_width) // 2
        crop_top = (camera.height - panel_height) // 2
        screen = camera.crop((crop_left, crop_top, crop_left + panel_width, crop_top + panel_height)).convert("RGBA")
    else:
        screen = Image.new("RGBA", (panel_width, panel_height), (26, 25, 34, 255))
        ImageDraw.Draw(screen).text(
            (panel_width // 2, panel_height // 2),
            "PRODUCT PREVIEW",
            fill=(205, 204, 216, 255),
            font=_font(max(16, int(height * 0.035)), True),
            anchor="mm",
        )

    screen_mask = Image.new("L", (panel_width, panel_height), 0)
    ImageDraw.Draw(screen_mask).rounded_rectangle(
        (0, 0, panel_width - 1, panel_height - 1), radius=radius, fill=255
    )
    screen.putalpha(screen_mask)
    frame.alpha_composite(screen, (panel_left, panel_top))
    draw = ImageDraw.Draw(frame)
    if style_name == "cinematic" and image is not None and image.height / image.width <= 1.15:
        chrome_height = max(22, int(panel_height * 0.085))
        draw.rectangle(
            (panel_left, panel_top, panel_left + panel_width - 1, panel_top + chrome_height),
            fill=(244, 246, 248, 255),
        )
        dot_radius = max(2, chrome_height // 9)
        for dot_index, dot_color in enumerate(((245, 96, 86, 255), (246, 187, 66, 255), (57, 190, 112, 255))):
            dot_x = panel_left + int(chrome_height * 0.55) + dot_index * dot_radius * 3
            draw.ellipse(
                (dot_x - dot_radius, panel_top + chrome_height // 2 - dot_radius,
                 dot_x + dot_radius, panel_top + chrome_height // 2 + dot_radius),
                fill=dot_color,
            )
    draw.rounded_rectangle(
        (panel_left, panel_top, panel_left + panel_width - 1, panel_top + panel_height - 1),
        radius=radius,
        outline=(255, 255, 255, 48),
        width=max(1, width // 1200),
    )

    def project(point_x: float, point_y: float) -> tuple[int, int]:
        return (
            int(panel_left + panel_width / 2 + (point_x - focus_x) * panel_width * zoom),
            int(panel_top + panel_height / 2 + (point_y - focus_y) * panel_height * zoom),
        )

    highlight_box = getattr(scene, "highlight_box", None)
    if highlight_box and 0.18 < progress < 0.88:
        x1, y1 = project(highlight_box[0], highlight_box[1])
        x2, y2 = project(highlight_box[2], highlight_box[3])
        pulse = max(0.0, 1.0 - abs(progress - 0.57) / 0.31)
        highlight = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        highlight_draw = ImageDraw.Draw(highlight)
        highlight_draw.rounded_rectangle(
            (x1, y1, x2, y2),
            radius=max(5, height // 100),
            fill=(*accent, int(18 + 20 * pulse)),
            outline=(*accent, int(100 + 140 * pulse)),
            width=max(2, width // 500),
        )
        frame = Image.alpha_composite(frame, highlight)

    cursor_target = getattr(scene, "cursor_target", None)
    if cursor_target and 0.12 < progress < 0.9:
        start = (min(0.96, cursor_target[0] + 0.15), min(0.96, cursor_target[1] + 0.11))
        travel = min(1.0, max(0.0, (progress - 0.14) / 0.38))
        travel = travel * travel * (3 - 2 * travel)
        current = (
            start[0] + (cursor_target[0] - start[0]) * travel,
            start[1] + (cursor_target[1] - start[1]) * travel,
        )
        cursor_x, cursor_y = project(*current)
        cursor_size = max(12, int(min(width, height) * 0.046))
        cursor = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        cursor_draw = ImageDraw.Draw(cursor)
        pointer = [
            (cursor_x, cursor_y),
            (cursor_x, cursor_y + cursor_size),
            (cursor_x + cursor_size * 0.27, cursor_y + cursor_size * 0.73),
            (cursor_x + cursor_size * 0.48, cursor_y + cursor_size * 1.02),
            (cursor_x + cursor_size * 0.62, cursor_y + cursor_size * 0.92),
            (cursor_x + cursor_size * 0.43, cursor_y + cursor_size * 0.65),
            (cursor_x + cursor_size * 0.82, cursor_y + cursor_size * 0.63),
        ]
        cursor_draw.polygon([(x + 2, y + 3) for x, y in pointer], fill=(0, 0, 0, 150))
        cursor_draw.polygon(pointer, fill=(255, 255, 255, 255), outline=(21, 19, 29, 255))
        click_progress = min(1.0, max(0.0, (progress - 0.5) / 0.32)) if getattr(scene, "cursor_click", False) else 0.0
        if click_progress:
            target_x, target_y = project(*cursor_target)
            ring_radius = int(cursor_size * (0.55 + click_progress * 0.9))
            ring_alpha = int(165 * (1.0 - click_progress))
            cursor_draw.ellipse(
                (target_x - ring_radius, target_y - ring_radius, target_x + ring_radius, target_y + ring_radius),
                outline=(*accent, ring_alpha),
                width=max(2, width // 600),
            )
        frame = Image.alpha_composite(frame, cursor)

    # Keep a restrained lower-third for copy without covering the product UI.
    draw = ImageDraw.Draw(frame)
    copy_top = int(height * 0.855)
    copy_bottom = int(height * 0.985)
    for band in range(20):
        blend = band / 19
        alpha = int(4 + 12 * blend)
        y0 = copy_top + band * (copy_bottom - copy_top) // 20
        y1 = copy_top + (band + 1) * (copy_bottom - copy_top) // 20
        draw.rectangle((0, y0, width, y1), fill=(8, 8, 13, alpha))

    headline = getattr(scene, "text_overlay", "") or ""
    description = getattr(scene, "voice_over", "") or ""
    if description.strip() == headline.strip():
        description = ""
    text_alpha = int(255 * min(1.0, max(0.0, (progress - 0.06) / 0.2)))
    lift = int(height * 0.012 * (1.0 - eased))
    text_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)
    text_left = int(width * 0.075)
    text_draw.rounded_rectangle(
        (text_left, copy_top + int(height * 0.012), text_left + int(width * 0.028), copy_top + int(height * 0.017)),
        radius=3,
        fill=(*accent, text_alpha),
    )
    title_font = _font(max(22, int(height * 0.052)), True)
    title_lines = _wrap_text(text_draw, headline[:90], title_font, int(width * 0.84))
    title_y = copy_top + int(height * 0.027) + lift
    line_height = int(height * 0.06)
    for index, line in enumerate(title_lines[:2]):
        text_draw.text(
            (text_left, title_y + index * line_height),
            line,
            fill=(255, 255, 255, text_alpha),
            font=title_font,
            stroke_width=max(0, height // 700),
            stroke_fill=(12, 11, 18, text_alpha),
        )
    if description:
        description_font = _font(max(13, int(height * 0.022)))
        description_y = title_y + min(len(title_lines), 2) * line_height
        text_draw.text(
            (text_left, description_y),
            description[:100],
            fill=(225, 224, 234, int(text_alpha * 0.88)),
            font=description_font,
        )
    return Image.alpha_composite(frame, text_layer).convert("RGB")


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
    brand_colors: dict[str, str] | None = None,
) -> Image.Image:
    if style_name.lower() == "premium" or (style_name.lower() == "cinematic" and width >= height):
        return _compose_premium_shot(width, height, image, scene, progress, style_name.lower(), brand_colors)

    style = get_style(style_name, brand_colors)
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
    if description.strip() == headline.strip():
        description = ""
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


def _open_video_sources(video_assets: list[str]) -> list[tuple[object, int, float]]:
    sources = []
    try:
        for path in video_assets:
            if not os.path.isfile(path):
                raise ValueError(f"Product video asset does not exist: {path}")
            reader = iio.get_reader(path)
            try:
                metadata = reader.get_meta_data()
                fps = float(metadata.get("fps") or 24)
                duration = float(metadata.get("duration") or 0)
                if not math.isfinite(fps) or fps <= 0:
                    raise ValueError(f"Product video asset has invalid frame rate: {path}")
                if math.isfinite(duration) and duration > 0:
                    frame_count = round(fps * duration)
                else:
                    frame_count = int(reader.count_frames())
                if frame_count < 1:
                    raise ValueError(f"Product video asset has no readable frames: {path}")
            except Exception:
                reader.close()
                raise
            sources.append((reader, frame_count, fps))
    except Exception:
        for reader, _, _ in sources:
            reader.close()
        raise
    return sources


def _video_frame_at(source: tuple[object, int, float], elapsed_seconds: float) -> Image.Image:
    reader, frame_count, source_fps = source
    frame_index = min(frame_count - 1, max(0, round(elapsed_seconds * source_fps)))
    return Image.fromarray(reader.get_data(frame_index)).convert("RGB")


def _video_images_for_frame(
    sources: list[tuple[object, int]],
    storyboard: list,
    frame_index: int,
    total_frames: int,
    output_fps: int,
) -> list[Image.Image | None]:
    scene_count = max(len(storyboard), 1)
    frames_per_scene = total_frames / scene_count
    seconds_per_scene = frames_per_scene / output_fps
    scene_index = min(int(frame_index / frames_per_scene), scene_count - 1)
    scene_progress = min(1.0, max(0.0, (frame_index - scene_index * frames_per_scene) / frames_per_scene))
    images: list[Image.Image | None] = [None] * scene_count

    scene_indices = {scene_index}
    if scene_index > 0 and frame_index - scene_index * frames_per_scene < min(10, frames_per_scene / 3):
        scene_indices.add(scene_index - 1)

    for index in scene_indices:
        source_index = min(index * len(sources) // scene_count, len(sources) - 1)
        first_scene = math.ceil(source_index * scene_count / len(sources))
        local_progress = scene_progress if index == scene_index else 0.999
        elapsed_seconds = (index - first_scene + local_progress) * seconds_per_scene
        images[index] = _video_frame_at(sources[source_index], elapsed_seconds)
    return images


def _mix_external_audio(
    video_path,
    duration: int,
    voiceover_audio: str | None,
    music_audio: str | None,
) -> None:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    muxed_path = video_path.with_name(f"{video_path.stem}.with-audio.mp4")
    command = [ffmpeg, "-y", "-i", str(video_path)]
    filters = []
    audio_labels = []
    input_index = 1

    if voiceover_audio:
        command.extend(["-i", voiceover_audio])
        filters.append(f"[{input_index}:a:0]aresample=48000,volume=1.0,apad[narration]")
        audio_labels.append("[narration]")
        input_index += 1
    if music_audio:
        command.extend(["-stream_loop", "-1", "-i", music_audio])
        filters.append(f"[{input_index}:a:0]aresample=48000,volume=0.16[music]")
        audio_labels.append("[music]")

    if len(audio_labels) == 2:
        filters.append(
            f"{''.join(audio_labels)}amix=inputs=2:duration=longest:dropout_transition=1:normalize=0,"
            f"alimiter=limit=0.95,atrim=duration={duration}[aout]"
        )
    else:
        filters.append(f"{audio_labels[0]}atrim=duration={duration},alimiter=limit=0.95[aout]")

    command.extend(
        [
            "-filter_complex", ";".join(filters),
            "-map", "0:v:0", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-t", str(duration), "-movflags", "+faststart", str(muxed_path),
        ]
    )
    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        os.replace(muxed_path, video_path)
    except subprocess.CalledProcessError as exc:
        raise ValueError("Could not mix the supplied audio; check that each file contains an audio track.") from exc
    finally:
        if muxed_path.exists():
            muxed_path.unlink()


def _validate_export(video_path, width: int, height: int, duration: int, expect_audio: bool) -> None:
    reader = iio.get_reader(str(video_path))
    try:
        metadata = reader.get_meta_data()
        actual_size = tuple(metadata.get("size") or ())
        actual_duration = float(metadata.get("duration") or 0)
        fps = float(metadata.get("fps") or 0)
        if actual_size != (width, height):
            raise RuntimeError(f"Rendered video has unexpected dimensions: {actual_size}")
        if not math.isfinite(actual_duration) or abs(actual_duration - duration) > max(0.25, 2 / max(fps, 1)):
            raise RuntimeError(f"Rendered video has unexpected duration: {actual_duration}")
        final_frame = max(0, math.ceil(actual_duration * max(fps, 1)) - 2)
        if reader.get_data(final_frame).size == 0:
            raise RuntimeError("Rendered video contains an unreadable final frame")
    finally:
        reader.close()

    if expect_audio:
        try:
            subprocess.run(
                [
                    imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-i", str(video_path),
                    "-map", "0:a:0", "-f", "null", "-",
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError as exc:
            raise RuntimeError("Rendered audio track failed decoding") from exc


def _make_frame(
    width: int,
    height: int,
    product_name: str,
    style_name: str,
    frame_index: int,
    total_frames: int,
    visual_images: list[Image.Image] | None = None,
    storyboard: list | None = None,
    brand_colors: dict[str, str] | None = None,
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
        shot_index, shot_count, shot_progress, brand_colors,
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
            previous_index, shot_count, 1.0, brand_colors,
        )
        transition = getattr(scenes[scene_index], "transition", "Cross dissolve") if scenes else "Cross dissolve"
        transition_progress = min(1.0, local_frame / transition_frames)
        current = _apply_transition(previous, current, transition_progress, transition)
    return current


def _add_premium_sound_design(video_path, duration: int, storyboard: list) -> None:
    sample_rate = 48000
    sample_count = sample_rate * duration
    time = np.arange(sample_count, dtype=np.float64) / sample_rate
    audio = np.zeros((sample_count, 2), dtype=np.float64)
    chords = (
        (130.81, 164.81, 196.0, 261.63),
        (110.0, 164.81, 220.0, 293.66),
        (146.83, 196.0, 220.0, 293.66),
        (123.47, 155.56, 196.0, 246.94),
    )
    chord_length = duration / len(chords)
    for chord_index, notes in enumerate(chords):
        start = int(chord_index * chord_length * sample_rate)
        end = min(sample_count, int((chord_index + 1) * chord_length * sample_rate))
        local = np.arange(end - start, dtype=np.float64) / sample_rate
        envelope = np.minimum(np.clip(local / 0.8, 0, 1), np.clip((chord_length - local) / 0.9, 0, 1))
        envelope *= 0.9 + 0.1 * np.sin(2 * np.pi * 0.12 * local)
        for note_index, frequency in enumerate(notes):
            phase = note_index * 0.13
            audio[start:end, 0] += np.sin(2 * np.pi * frequency * local + phase) * envelope * 0.018
            audio[start:end, 1] += np.sin(2 * np.pi * frequency * local + phase + 0.025) * envelope * 0.018

    scene_count = max(len(storyboard), 1)
    for scene_index, scene in enumerate(storyboard[1:], 1):
        cue_time = duration * scene_index / scene_count
        start = int(cue_time * sample_rate)
        cue_length = min(int(sample_rate * 0.48), sample_count - start)
        if cue_length <= 0:
            continue
        local = np.arange(cue_length, dtype=np.float64) / sample_rate
        envelope = np.exp(-local * 7.0)
        chime = (np.sin(2 * np.pi * 660 * local) + 0.42 * np.sin(2 * np.pi * 990 * local)) * envelope * 0.025
        audio[start:start + cue_length, 0] += chime
        audio[start:start + cue_length, 1] += chime * 0.92

        if getattr(scene, "cursor_target", None) and getattr(scene, "cursor_click", False):
            click_start = min(sample_count, start + int(sample_rate * 0.52))
            click_length = min(int(sample_rate * 0.09), sample_count - click_start)
            click_time = np.arange(click_length, dtype=np.float64) / sample_rate
            click_envelope = np.exp(-click_time * 62)
            click = (np.sin(2 * np.pi * (1250 * click_time - 240 * click_time ** 2)) + 0.22 * np.sin(2 * np.pi * 2100 * click_time)) * click_envelope * 0.045
            audio[click_start:click_start + click_length, 0] += click
            audio[click_start:click_start + click_length, 1] += click * 0.82

    fade_in = np.clip(time / 0.8, 0, 1)
    fade_out = np.clip((duration - time) / 1.1, 0, 1)
    audio *= (fade_in * fade_out)[:, None]
    peak = np.max(np.abs(audio))
    if peak > 0.82:
        audio *= 0.82 / peak
    pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16)

    audio_file = None
    muxed_path = video_path.with_name(f"{video_path.stem}.with-audio.mp4")
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", dir=video_path.parent, delete=False) as temporary_audio:
            audio_file = temporary_audio.name
        with wave.open(audio_file, "wb") as output:
            output.setnchannels(2)
            output.setsampwidth(2)
            output.setframerate(sample_rate)
            output.writeframes(pcm.tobytes())
        subprocess.run(
            [
                imageio_ffmpeg.get_ffmpeg_exe(),
                "-y",
                "-i",
                str(video_path),
                "-i",
                audio_file,
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "160k",
                "-movflags",
                "+faststart",
                "-shortest",
                str(muxed_path),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        os.replace(muxed_path, video_path)
    finally:
        for temporary_path in (audio_file, str(muxed_path)):
            if temporary_path and os.path.exists(temporary_path):
                os.unlink(temporary_path)


def render_video(
    product_name: str,
    output_dir: str = "madvid-output",
    duration: int = 20,
    style: str = "premium",
    orientation: str = "landscape",
    preview: bool = False,
    storyboard: list | None = None,
    visual_assets: list[str] | None = None,
    video_assets: list[str] | None = None,
    voiceover_audio: str | None = None,
    music_audio: str | None = None,
    brand_colors: dict[str, str] | None = None,
    tagline: str = "",
) -> tuple[str, str]:
    """Render a marketing-grade product video.

    Uses the FFmpeg filtergraph renderer (kinetic text, animated gradients,
    scene-specific layouts, xfade transitions) when FFmpeg 4.3+ is available.
    Falls back to the PIL frame renderer otherwise.
    """
    has_visual_file = any(os.path.isfile(path) for path in visual_assets or [])
    has_video_file = any(os.path.isfile(path) for path in video_assets or [])
    if not preview and not has_visual_file and not has_video_file:
        raise ValueError(_NO_PRODUCT_VISUALS)

    if _ffmpeg_available() and not video_assets:
        from .ffmpeg_renderer import render_video_ffmpeg
        try:
            return render_video_ffmpeg(
                product_name=product_name,
                output_dir=output_dir,
                duration=duration,
                style=style,
                orientation=orientation,
                preview=preview,
                storyboard=storyboard,
                visual_assets=visual_assets,
                video_assets=video_assets,
                voiceover_audio=voiceover_audio,
                music_audio=music_audio,
                brand_colors=brand_colors,
                tagline=tagline,
            )
        except subprocess.CalledProcessError:
            # Keep video generation available when a bundled FFmpeg lacks graph support.
            pass
    return _render_video_pil(
        product_name=product_name,
        output_dir=output_dir,
        duration=duration,
        style=style,
        orientation=orientation,
        preview=preview,
        storyboard=storyboard,
        visual_assets=visual_assets,
        video_assets=video_assets,
        voiceover_audio=voiceover_audio,
        music_audio=music_audio,
        brand_colors=brand_colors,
    )


def _render_video_pil(
    product_name: str,
    output_dir: str = "madvid-output",
    duration: int = 20,
    style: str = "premium",
    orientation: str = "landscape",
    preview: bool = False,
    storyboard: list | None = None,
    visual_assets: list[str] | None = None,
    video_assets: list[str] | None = None,
    voiceover_audio: str | None = None,
    music_audio: str | None = None,
    brand_colors: dict[str, str] | None = None,
) -> tuple[str, str]:
    output_path = ensure_output_dir(output_dir)
    width, height = _resolve_resolution(orientation, preview=preview)
    fps = 24
    total_frames = fps * duration
    video_name = "preview.mp4" if preview else "product-intro.mp4"
    final_video_path = output_path / video_name
    visual_images: list[Image.Image] = []
    for asset_path in visual_assets or []:
        try:
            with Image.open(asset_path) as image:
                visual_images.append(ImageOps.exif_transpose(image).convert("RGB"))
        except (OSError, ValueError):
            continue
    for audio_path in (voiceover_audio, music_audio):
        if audio_path and not os.path.isfile(audio_path):
            raise ValueError(f"Audio asset does not exist: {audio_path}")
    video_sources = _open_video_sources(video_assets or [])
    scene_count = max(len(storyboard or []), 1)
    if len(video_sources) > scene_count:
        for reader, _, _ in video_sources:
            reader.close()
        raise ValueError("Provide no more screen recordings than storyboard scenes.")
    for source_index, (_, frame_count, source_fps) in enumerate(video_sources):
        first_scene = math.ceil(source_index * scene_count / len(video_sources))
        next_scene = math.ceil((source_index + 1) * scene_count / len(video_sources))
        required_duration = duration * (next_scene - first_scene) / scene_count
        available_duration = frame_count / source_fps
        if available_duration + 1 / source_fps < required_duration:
            for reader, _, _ in video_sources:
                reader.close()
            raise ValueError(
                f"Screen recording is too short for its timeline segment "
                f"({available_duration:.1f}s available; {required_duration:.1f}s required)."
            )
    if not visual_images and not video_sources and not preview:
        raise ValueError(_NO_PRODUCT_VISUALS)
    video_asset_count = len(video_sources)
    with tempfile.NamedTemporaryFile(
        prefix=f".{video_name}.", suffix=".tmp.mp4", dir=output_path, delete=False
    ) as temporary_video:
        video_path = Path(temporary_video.name)
    video_path.unlink()
    writer = None
    try:
        writer = iio.get_writer(str(video_path), fps=fps, codec="libx264", quality=8, macro_block_size=1)
        for index in range(total_frames):
            frame_images = (
                _video_images_for_frame(video_sources, storyboard or [], index, total_frames, fps)
                if video_sources
                else visual_images
            )
            frame = _make_frame(width, height, product_name, style, index, total_frames, frame_images, storyboard, brand_colors)
            writer.append_data(np.asarray(frame))
        writer.close()
        writer = None
        for reader, _, _ in video_sources:
            reader.close()
        video_sources = []
        if voiceover_audio or music_audio:
            _mix_external_audio(video_path, duration, voiceover_audio, music_audio)
        elif style.lower() == "premium":
            _add_premium_sound_design(video_path, duration, storyboard or [])
        audio_tracks = []
        if voiceover_audio:
            audio_tracks.append("voiceover")
        if music_audio:
            audio_tracks.append("music")
        if not audio_tracks and style.lower() == "premium":
            audio_tracks.append("generated_sound_design")
        _validate_export(video_path, width, height, duration, bool(audio_tracks))
        os.replace(video_path, final_video_path)
        video_path = final_video_path
    except Exception:
        if writer is not None:
            writer.close()
        for reader, _, _ in video_sources:
            reader.close()
        if video_path.exists():
            video_path.unlink()
        raise
    metadata = {
        "productName": product_name,
        "duration": duration,
        "orientation": orientation,
        "style": style,
        "resolution": f"{width}x{height}",
        "frameRate": fps,
        "videoCodec": "h264",
        "preview": preview,
        "visualSource": (
            "product_video_clips" if video_asset_count else
            "product_screenshots" if visual_images else
            "no_product_screenshots"
        ),
        "visualAssetCount": len(visual_images),
        "videoAssetCount": video_asset_count,
        "audioTracks": audio_tracks,
    }
    if music_audio:
        metadata["soundtrack"] = "provided_music"
    elif style.lower() == "premium" and not voiceover_audio:
        metadata["soundtrack"] = "cinematic_ambient_bed_and_ui_cues"
    if storyboard:
        metadata["storyboardCount"] = len(storyboard)
    write_json(output_path / "metadata.json", metadata)
    return str(video_path), str(output_path / "metadata.json")
