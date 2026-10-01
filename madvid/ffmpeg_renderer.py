"""FFmpeg filtergraph renderer for MADVID — marketing-grade video output."""

from __future__ import annotations

import json
import math
import os
import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg

from .asset_manager import ensure_output_dir, write_json
from .styles import get_style


def _ffmpeg() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def _rgb_hex(color: str) -> str:
    return color.lstrip("#").upper()


def _rgba_hex(color: str, alpha: float = 1.0) -> str:
    r, g, b = [int(color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4)]
    a = int(alpha * 255)
    return f"#{r:02X}{g:02X}{b:02X}{a:02X}"


def _resolve_resolution(orientation: str, preview: bool = False) -> tuple[int, int]:
    if orientation == "vertical":
        w, h = 1080, 1920
    else:
        w, h = 1920, 1080
    if preview:
        w, h = w // 2, h // 2
    return w, h


# Scene layout types — each maps to a distinct visual composition
LAYOUT_HERO = "hero"           # Full-bleed image, large centred headline
LAYOUT_SPLIT = "split"         # Image left/right, copy opposite side
LAYOUT_STATEMENT = "statement" # No image, bold centred copy on gradient
LAYOUT_FEATURE = "feature"     # Image top 60%, copy bottom 40%
LAYOUT_CTA = "cta"             # Dark card, product name, CTA pill button

_SCENE_LAYOUTS = [
    LAYOUT_HERO,
    LAYOUT_SPLIT,
    LAYOUT_FEATURE,
    LAYOUT_SPLIT,
    LAYOUT_STATEMENT,
    LAYOUT_CTA,
]


def _scene_layout(scene_index: int, scene_count: int, scene_name: str) -> str:
    name = (scene_name or "").lower()
    if "hook" in name or "opening" in name:
        return LAYOUT_HERO
    if "cta" in name or "call to action" in name or scene_index == scene_count - 1:
        return LAYOUT_CTA
    if "reveal" in name or "product" in name:
        return LAYOUT_STATEMENT
    if "workflow" in name or "primary" in name:
        return LAYOUT_SPLIT
    return _SCENE_LAYOUTS[scene_index % len(_SCENE_LAYOUTS)]


def _escape(text: str) -> str:
    """Escape text for FFmpeg drawtext filter."""
    return (
        text.replace("\\", "\\\\")
            .replace("'", "\u2019")
            .replace(":", "\\:")
            .replace("%", "\\%")
            .replace("[", "\\[")
            .replace("]", "\\]")
    )


def _build_scene_filter(
    scene_index: int,
    scene_count: int,
    scene,
    w: int,
    h: int,
    duration_s: float,
    image_input_index: int | None,
    accent: str,
    background: str,
    secondary: str,
    product_name: str,
    tagline: str,
) -> tuple[str, str]:
    """
    Build an FFmpeg filtergraph for one scene.
    Returns (filter_chain, output_label).
    """
    bg = _rgb_hex(background)
    ac = _rgb_hex(accent)
    sc = _rgb_hex(secondary)

    # Derive a slightly lighter bg for gradient
    r, g, b = [int(background.lstrip("#")[i:i+2], 16) for i in (0, 2, 4)]
    r2 = min(255, r + 28)
    g2 = min(255, g + 22)
    b2 = min(255, b + 38)
    bg2 = f"{r2:02X}{g2:02X}{b2:02X}"

    scene_name = getattr(scene, "scene", "") or ""
    headline = (_escape(getattr(scene, "text_overlay", "") or "")).strip()
    subline = (_escape(getattr(scene, "voice_over", "") or "")).strip()
    if subline == headline:
        subline = ""
    layout = _scene_layout(scene_index, scene_count, scene_name)
    d = duration_s
    label = f"scene{scene_index}"

    # Font sizes relative to height
    title_size = max(48, int(h * 0.072))
    sub_size = max(28, int(h * 0.032))
    label_size = max(20, int(h * 0.022))
    name_size = max(22, int(h * 0.026))

    pad_x = int(w * 0.07)
    pad_y = int(h * 0.07)
    center_x = w // 2
    center_y = h // 2

    filters: list[str] = []
    base = f"base{scene_index}"

    # --- Background: animated radial gradient via color + glow overlay ---
    filters.append(
        f"color=c=#{bg}:s={w}x{h}:d={d}[{base}_bg]"
    )
    # Animated glow blob using geq
    glow_r = int(r2 * 1.18)
    glow_g = int(g2 * 1.12)
    glow_b = min(255, int(b2 * 1.45))
    filters.append(
        f"color=c=#{bg}:s={w}x{h}:d={d},"
        f"geq="
        f"r='clip({glow_r}*exp(-((X-{int(w*0.72)})^2+(Y-{int(h*0.28)})^2)/{int((w*0.38)**2)}),0,255)':"
        f"g='clip({glow_g}*exp(-((X-{int(w*0.72)})^2+(Y-{int(h*0.28)})^2)/{int((w*0.38)**2)}),0,255)':"
        f"b='clip({glow_b}*exp(-((X-{int(w*0.72)})^2+(Y-{int(h*0.28)})^2)/{int((w*0.38)**2)}),0,255)'"
        f"[{base}_glow]"
    )
    filters.append(
        f"[{base}_bg][{base}_glow]blend=all_mode=screen:all_opacity=0.55[{base}_bg2]"
    )

    # Second glow from opposite corner
    filters.append(
        f"color=c=#{bg}:s={w}x{h}:d={d},"
        f"geq="
        f"r='clip({int(r*0.9)}*exp(-((X-{int(w*0.18)})^2+(Y-{int(h*0.78)})^2)/{int((w*0.32)**2)}),0,255)':"
        f"g='clip({int(g*0.85)}*exp(-((X-{int(w*0.18)})^2+(Y-{int(h*0.78)})^2)/{int((w*0.32)**2)}),0,255)':"
        f"b='clip({min(255,int(b*1.6))}*exp(-((X-{int(w*0.18)})^2+(Y-{int(h*0.78)})^2)/{int((w*0.32)**2)}),0,255)'"
        f"[{base}_glow2]"
    )
    filters.append(
        f"[{base}_bg2][{base}_glow2]blend=all_mode=screen:all_opacity=0.38[{base}_bg3]"
    )

    # Subtle noise grain for cinematic texture
    filters.append(
        f"[{base}_bg3]noise=alls=6:allf=t[{base}_grain]"
    )

    current = f"{base}_grain"

    # --- Image panel ---
    if image_input_index is not None:
        img_in = f"[{image_input_index}:v]"
        if layout == LAYOUT_HERO:
            # Full bleed with Ken Burns + dark vignette overlay
            filters.append(
                f"{img_in}scale={w}:{h}:force_original_aspect_ratio=increase,"
                f"crop={w}:{h},"
                f"zoompan=z='min(zoom+0.0008,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"d={int(d*25)}:s={w}x{h}:fps=25[{base}_img]"
            )
            # Dark vignette
            filters.append(
                f"color=c=black:s={w}x{h}:d={d},"
                f"geq=r='255*((X/{w}-0.5)^2+(Y/{h}-0.5)^2)*2.2':g='255*((X/{w}-0.5)^2+(Y/{h}-0.5)^2)*2.2':b='255*((X/{w}-0.5)^2+(Y/{h}-0.5)^2)*2.2'"
                f"[{base}_vig]"
            )
            filters.append(
                f"[{base}_img][{base}_vig]blend=all_mode=multiply:all_opacity=0.72[{base}_imgv]"
            )
            # Blend image over bg
            filters.append(
                f"[{current}][{base}_imgv]blend=all_mode=overlay:all_opacity=0.82[{base}_withimg]"
            )
            current = f"{base}_withimg"

        elif layout == LAYOUT_SPLIT:
            panel_w = int(w * 0.52)
            panel_h = int(h * 0.72)
            panel_x = int(w * 0.44)
            panel_y = (h - panel_h) // 2
            corner = max(12, int(h * 0.018))
            filters.append(
                f"{img_in}scale={panel_w}:{panel_h}:force_original_aspect_ratio=increase,"
                f"crop={panel_w}:{panel_h},"
                f"zoompan=z='min(zoom+0.0006,1.06)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"d={int(d*25)}:s={panel_w}x{panel_h}:fps=25,"
                f"format=rgba,"
                f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':"
                f"a='if(gt(X,{corner})*gt(Y,{corner})*lt(X,{panel_w-corner})*lt(Y,{panel_h-corner}),255,"
                f"if(lt(hypot(X-{corner},Y-{corner}),{corner})*lt(X,{corner})*lt(Y,{corner}),255,"
                f"if(lt(hypot(X-{panel_w-corner},Y-{corner}),{corner})*gt(X,{panel_w-corner})*lt(Y,{corner}),255,"
                f"if(lt(hypot(X-{corner},Y-{panel_h-corner}),{corner})*lt(X,{corner})*gt(Y,{panel_h-corner}),255,"
                f"if(lt(hypot(X-{panel_w-corner},Y-{panel_h-corner}),{corner})*gt(X,{panel_w-corner})*gt(Y,{panel_h-corner}),255,0)))))'"
                f"[{base}_panel]"
            )
            # Shadow
            filters.append(
                f"color=c=#000000AA:s={panel_w}x{panel_h}:d={d}[{base}_shadow_src]"
            )
            filters.append(
                f"[{current}][{base}_shadow_src]overlay={panel_x+8}:{panel_y+10}[{base}_shadowed]"
            )
            filters.append(
                f"[{base}_shadowed][{base}_panel]overlay={panel_x}:{panel_y}[{base}_withimg]"
            )
            current = f"{base}_withimg"

        elif layout == LAYOUT_FEATURE:
            panel_w = int(w * 0.78)
            panel_h = int(h * 0.52)
            panel_x = (w - panel_w) // 2
            panel_y = int(h * 0.06)
            filters.append(
                f"{img_in}scale={panel_w}:{panel_h}:force_original_aspect_ratio=increase,"
                f"crop={panel_w}:{panel_h},"
                f"zoompan=z='min(zoom+0.0007,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"d={int(d*25)}:s={panel_w}x{panel_h}:fps=25[{base}_panel]"
            )
            filters.append(
                f"[{current}][{base}_panel]overlay={panel_x}:{panel_y}[{base}_withimg]"
            )
            current = f"{base}_withimg"

        else:
            # Default: centred panel
            panel_w = int(w * 0.64)
            panel_h = int(h * 0.62)
            panel_x = (w - panel_w) // 2
            panel_y = int(h * 0.08)
            filters.append(
                f"{img_in}scale={panel_w}:{panel_h}:force_original_aspect_ratio=increase,"
                f"crop={panel_w}:{panel_h},"
                f"zoompan=z='min(zoom+0.0007,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"d={int(d*25)}:s={panel_w}x{panel_h}:fps=25[{base}_panel]"
            )
            filters.append(
                f"[{current}][{base}_panel]overlay={panel_x}:{panel_y}[{base}_withimg]"
            )
            current = f"{base}_withimg"

    # --- Accent line (animated width reveal) ---
    line_y = int(h * 0.88)
    line_h = max(3, int(h * 0.004))
    filters.append(
        f"[{current}]drawbox="
        f"x='{pad_x}':y={line_y}:"
        f"w='min(t/{d}*{int(w*0.86)},{int(w*0.86)})':h={line_h}:"
        f"color=#{ac}:t=fill[{base}_line]"
    )
    current = f"{base}_line"

    # --- Product name watermark top-left ---
    filters.append(
        f"[{current}]drawtext="
        f"text='{_escape(product_name.upper()[:28])}':"
        f"fontsize={name_size}:fontcolor=#{sc}@0.55:"
        f"x={pad_x}:y={pad_y}:"
        f"alpha='min(t*3,1)'[{base}_name]"
    )
    current = f"{base}_name"

    # --- Scene label (small caps, accent colour) ---
    if scene_name:
        filters.append(
            f"[{current}]drawtext="
            f"text='{_escape(scene_name.upper()[:32])}':"
            f"fontsize={label_size}:fontcolor=#{ac}:"
            f"x={pad_x}:y={int(h*0.82)}:"
            f"alpha='min((t-0.1)*4,1)'[{base}_lbl]"
        )
        current = f"{base}_lbl"

    # --- Headline text with animated reveal ---
    if headline:
        if layout in (LAYOUT_HERO, LAYOUT_STATEMENT, LAYOUT_CTA):
            tx = f"(w-text_w)/2"
            ty = int(h * 0.52) if layout == LAYOUT_CTA else int(h * 0.58)
        elif layout == LAYOUT_FEATURE:
            tx = f"{pad_x}"
            ty = int(h * 0.64)
        else:
            tx = f"{pad_x}"
            ty = int(h * 0.34)

        filters.append(
            f"[{current}]drawtext="
            f"text='{headline[:72]}':"
            f"fontsize={title_size}:fontcolor=#{sc}:"
            f"x={tx}:y={ty}:"
            f"shadowx=2:shadowy=3:shadowcolor=#000000@0.6:"
            f"alpha='min((t-0.08)*5,1)':"
            f"y='{ty}+{int(h*0.022)}*(1-min((t-0.08)*5,1))'[{base}_h1]"
        )
        current = f"{base}_h1"

    # --- Subline text ---
    if subline:
        if layout in (LAYOUT_HERO, LAYOUT_STATEMENT, LAYOUT_CTA):
            sx = f"(w-text_w)/2"
            sy = int(h * 0.52) + title_size + int(h * 0.018) if layout == LAYOUT_CTA else int(h * 0.58) + title_size + int(h * 0.018)
        elif layout == LAYOUT_FEATURE:
            sx = f"{pad_x}"
            sy = int(h * 0.64) + title_size + int(h * 0.016)
        else:
            sx = f"{pad_x}"
            sy = int(h * 0.34) + title_size + int(h * 0.016)

        filters.append(
            f"[{current}]drawtext="
            f"text='{subline[:90]}':"
            f"fontsize={sub_size}:fontcolor=#{sc}@0.78:"
            f"x={sx}:y={sy}:"
            f"alpha='min((t-0.22)*4,1)'[{base}_sub]"
        )
        current = f"{base}_sub"

    # --- CTA pill badge on CTA scene ---
    if layout == LAYOUT_CTA:
        cta_text = _escape(getattr(scene, "text_overlay", "Get started") or "Get started")
        cta_y = int(h * 0.72)
        cta_x = int(w * 0.38)
        cta_w = int(w * 0.24)
        cta_h = int(h * 0.072)
        filters.append(
            f"[{current}]drawbox="
            f"x={cta_x}:y={cta_y}:w={cta_w}:h={cta_h}:"
            f"color=#{ac}:t=fill:"
            f"enable='gte(t,0.3)'[{base}_pill]"
        )
        filters.append(
            f"[{base}_pill]drawtext="
            f"text='{cta_text[:32]}':"
            f"fontsize={sub_size}:fontcolor=#000000:"
            f"x=(w-text_w)/2:y={cta_y + cta_h//2 - sub_size//2}:"
            f"alpha='min((t-0.3)*5,1)'[{base}_cta]"
        )
        current = f"{base}_cta"

    # --- Tagline on STATEMENT scene ---
    if layout == LAYOUT_STATEMENT and tagline:
        tl = _escape(tagline[:60])
        filters.append(
            f"[{current}]drawtext="
            f"text='{tl}':"
            f"fontsize={max(32, int(h*0.042))}:fontcolor=#{ac}:"
            f"x=(w-text_w)/2:y={int(h*0.44)}:"
            f"alpha='min((t-0.15)*4,1)'[{base}_tag]"
        )
        current = f"{base}_tag"

    # Fade in/out
    filters.append(
        f"[{current}]fade=t=in:st=0:d=0.35,fade=t=out:st={max(0, d-0.35)}:d=0.35[{label}]"
    )

    return ";\n".join(filters), label


def _build_transition(label_a: str, label_b: str, transition: str, out_label: str, w: int, h: int) -> str:
    """Build an xfade transition between two scene clips."""
    t = (transition or "").lower()
    if "push" in t or "wipe" in t:
        effect = "slideleft"
    elif "flash" in t:
        effect = "fadewhite"
    elif "zoom" in t:
        effect = "zoomin"
    elif "smash" in t or "cut" in t:
        effect = "fade"
    else:
        effect = "fade"
    return f"[{label_a}][{label_b}]xfade=transition={effect}:duration=0.45:offset=0[{out_label}]"


def render_video_ffmpeg(
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
    output_path = ensure_output_dir(output_dir)
    w, h = _resolve_resolution(orientation, preview=preview)
    scenes = storyboard or []
    if not scenes:
        from .storyboard_generator import generate_storyboard
        scenes = generate_storyboard(product_name=product_name, duration=duration)
    scene_count = max(len(scenes), 1)
    images = list(visual_assets or [])
    style_obj = get_style(style, brand_colors)
    accent = style_obj.accent
    background = style_obj.background
    secondary = style_obj.secondary

    scene_duration = duration / scene_count
    video_name = "preview.mp4" if preview else "product-intro.mp4"
    final_path = output_path / video_name

    # Validate audio paths
    for audio_path in (voiceover_audio, music_audio):
        if audio_path and not os.path.isfile(audio_path):
            raise ValueError(f"Audio asset does not exist: {audio_path}")

    # Build per-scene clips then concat + xfade
    scene_clips: list[Path] = []
    tmp_files: list[str] = []

    try:
        for idx, scene in enumerate(scenes):
            img_path = images[min(idx * len(images) // scene_count, len(images) - 1)] if images else None
            scene_dur = scene_duration

            # Build filtergraph for this scene
            img_input_args: list[str] = []
            img_input_index: int | None = None
            if img_path and os.path.isfile(img_path):
                img_input_args = ["-loop", "1", "-t", str(scene_dur + 1), "-i", img_path]
                img_input_index = 0

            filter_chain, out_label = _build_scene_filter(
                scene_index=idx,
                scene_count=scene_count,
                scene=scene,
                w=w,
                h=h,
                duration_s=scene_dur,
                image_input_index=img_input_index,
                accent=accent,
                background=background,
                secondary=secondary,
                product_name=product_name,
                tagline=tagline,
            )

            tmp = tempfile.NamedTemporaryFile(
                prefix=f".scene{idx}.", suffix=".mp4",
                dir=output_path, delete=False
            )
            tmp.close()
            tmp_files.append(tmp.name)
            clip_path = Path(tmp.name)

            cmd = [
                _ffmpeg(), "-y",
                "-f", "lavfi", "-t", str(scene_dur), "-i", f"color=c=#{_rgb_hex(background)}:s={w}x{h}:r=25",
            ]
            cmd += img_input_args
            cmd += [
                "-filter_complex", filter_chain,
                "-map", f"[{out_label}]",
                "-t", str(scene_dur),
                "-r", "25",
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-pix_fmt", "yuv420p",
                str(clip_path),
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            scene_clips.append(clip_path)

        # Concatenate scenes with xfade transitions
        if len(scene_clips) == 1:
            final_silent = scene_clips[0]
        else:
            final_silent = _concat_with_xfade(
                scene_clips, scenes, output_path, w, h, duration, tmp_files
            )

        # Mix audio
        _mix_audio(
            final_silent, final_path, duration,
            voiceover_audio, music_audio, style
        )

    finally:
        for f in tmp_files:
            try:
                if os.path.exists(f) and str(f) != str(final_path):
                    os.unlink(f)
            except OSError:
                pass

    metadata = {
        "productName": product_name,
        "duration": duration,
        "orientation": orientation,
        "style": style,
        "resolution": f"{w}x{h}",
        "frameRate": 25,
        "videoCodec": "h264",
        "preview": preview,
        "renderer": "ffmpeg_filtergraph",
        "visualAssetCount": len(images),
        "visualSource": "product_screenshots" if images else "no_product_screenshots",
        "audioTracks": (
            ["voiceover"] if voiceover_audio else
            (["music"] if music_audio else ["generated_sound_design"])
        ),
    }
    if brand_colors:
        metadata["brand_colors"] = brand_colors
    if tagline:
        metadata["tagline"] = tagline
    if storyboard:
        metadata["storyboardCount"] = len(storyboard)

    metadata_path = output_path / "metadata.json"
    write_json(metadata_path, metadata)
    return str(final_path), str(metadata_path)


def _concat_with_xfade(
    clips: list[Path],
    scenes: list,
    output_path: Path,
    w: int,
    h: int,
    total_duration: int,
    tmp_files: list[str],
) -> Path:
    """Concatenate scene clips using xfade transitions."""
    xfade_dur = 0.45
    # Build a single ffmpeg command with all clips and chained xfades
    cmd = [_ffmpeg(), "-y"]
    for clip in clips:
        cmd += ["-i", str(clip)]

    filters = []
    labels = [f"[{i}:v]" for i in range(len(clips))]

    # Chain xfades: each transition offsets by cumulative scene duration minus overlap
    scene_count = max(len(clips), 1)
    scene_dur = total_duration / scene_count
    current_label = labels[0]

    for i in range(1, scene_count):
        transition = getattr(scenes[i], "transition", "fade") if i < len(scenes) else "fade"
        t = (transition or "").lower()
        if "push" in t:
            effect = "slideleft"
        elif "flash" in t:
            effect = "fadewhite"
        elif "zoom" in t:
            effect = "zoomin"
        else:
            effect = "fade"

        offset = round(scene_dur * i - xfade_dur * i, 3)
        out = f"xf{i}" if i < scene_count - 1 else "final_v"
        filters.append(
            f"{current_label}{labels[i]}xfade=transition={effect}:duration={xfade_dur}:offset={offset}[{out}]"
        )
        current_label = f"[{out}]"

    tmp = tempfile.NamedTemporaryFile(
        prefix=".concat.", suffix=".mp4", dir=output_path, delete=False
    )
    tmp.close()
    tmp_files.append(tmp.name)
    out_path = Path(tmp.name)

    cmd += [
        "-filter_complex", ";".join(filters),
        "-map", "[final_v]",
        "-t", str(total_duration),
        "-r", "25",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return out_path


def _mix_audio(
    video_path: Path,
    final_path: Path,
    duration: int,
    voiceover_audio: str | None,
    music_audio: str | None,
    style: str,
) -> None:
    """Mix audio into the video. Falls back to generated ambient if no audio supplied."""
    import wave
    import numpy as np

    ffmpeg = _ffmpeg()

    if not voiceover_audio and not music_audio:
        # Generate a clean ambient music bed — warm pads + subtle pulse
        sample_rate = 48000
        n = sample_rate * duration
        t = np.linspace(0, duration, n, endpoint=False)
        audio = np.zeros((n, 2), dtype=np.float64)

        # Chord progression: Cmaj7 → Am7 → Fmaj7 → G7
        chords = [
            [130.81, 164.81, 196.00, 246.94],
            [110.00, 130.81, 164.81, 220.00],
            [174.61, 220.00, 261.63, 329.63],
            [196.00, 246.94, 293.66, 392.00],
        ]
        chord_len = duration / len(chords)
        for ci, notes in enumerate(chords):
            s = int(ci * chord_len * sample_rate)
            e = min(n, int((ci + 1) * chord_len * sample_rate))
            lt = np.arange(e - s) / sample_rate
            env = np.minimum(np.clip(lt / 1.2, 0, 1), np.clip((chord_len - lt) / 1.4, 0, 1))
            env = env ** 1.4
            for ni, freq in enumerate(notes):
                phase = ni * 0.17
                # Pad: sine + slight detuned layer
                wave_l = np.sin(2 * np.pi * freq * lt + phase) * 0.022
                wave_r = np.sin(2 * np.pi * freq * 1.0015 * lt + phase + 0.04) * 0.022
                audio[s:e, 0] += wave_l * env
                audio[s:e, 1] += wave_r * env
                # Sub octave warmth
                audio[s:e, 0] += np.sin(2 * np.pi * freq * 0.5 * lt) * env * 0.008
                audio[s:e, 1] += np.sin(2 * np.pi * freq * 0.5 * lt) * env * 0.008

        # Subtle pulse / hi-hat on beats
        bpm = 90
        beat_interval = 60.0 / bpm
        beat_times = np.arange(0, duration, beat_interval)
        for bt in beat_times:
            bs = int(bt * sample_rate)
            bl = min(int(0.04 * sample_rate), n - bs)
            if bl <= 0:
                continue
            lt = np.arange(bl) / sample_rate
            click = np.sin(2 * np.pi * 4200 * lt) * np.exp(-lt * 180) * 0.018
            audio[bs:bs+bl, 0] += click
            audio[bs:bs+bl, 1] += click * 0.88

        # Scene transition chimes
        scene_count = 1
        for si in range(1, scene_count + 1):
            cs = int(duration * si / max(scene_count, 1) * sample_rate)
            cl = min(int(0.5 * sample_rate), n - cs)
            if cl <= 0:
                continue
            lt = np.arange(cl) / sample_rate
            chime = (np.sin(2 * np.pi * 880 * lt) + 0.4 * np.sin(2 * np.pi * 1320 * lt)) * np.exp(-lt * 9) * 0.028
            audio[cs:cs+cl, 0] += chime
            audio[cs:cs+cl, 1] += chime * 0.9

        # Fade in/out
        fade_s = int(1.2 * sample_rate)
        fade_e = int(1.8 * sample_rate)
        audio[:fade_s, :] *= np.linspace(0, 1, fade_s)[:, None]
        audio[-fade_e:, :] *= np.linspace(1, 0, fade_e)[:, None]

        peak = np.max(np.abs(audio))
        if peak > 0.001:
            audio = audio / peak * 0.78

        pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16)
        wav_tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        wav_tmp.close()
        try:
            with wave.open(wav_tmp.name, "wb") as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(pcm.tobytes())
            subprocess.run(
                [ffmpeg, "-y", "-i", str(video_path), "-i", wav_tmp.name,
                 "-map", "0:v:0", "-map", "1:a:0",
                 "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                 "-t", str(duration), "-movflags", "+faststart", str(final_path)],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            )
        finally:
            if os.path.exists(wav_tmp.name):
                os.unlink(wav_tmp.name)
        return

    # External audio supplied
    cmd = [ffmpeg, "-y", "-i", str(video_path)]
    filters = []
    labels = []
    idx = 1
    if voiceover_audio:
        cmd += ["-i", voiceover_audio]
        filters.append(f"[{idx}:a]aresample=48000,volume=1.0,apad[vo]")
        labels.append("[vo]")
        idx += 1
    if music_audio:
        cmd += ["-stream_loop", "-1", "-i", music_audio]
        filters.append(f"[{idx}:a]aresample=48000,volume=0.14[mus]")
        labels.append("[mus]")

    if len(labels) == 2:
        filters.append(
            f"{''.join(labels)}amix=inputs=2:duration=longest:normalize=0,"
            f"alimiter=limit=0.95,atrim=duration={duration}[aout]"
        )
    else:
        filters.append(f"{labels[0]}atrim=duration={duration},alimiter=limit=0.95[aout]")

    cmd += [
        "-filter_complex", ";".join(filters),
        "-map", "0:v:0", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-t", str(duration), "-movflags", "+faststart", str(final_path),
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as exc:
        raise ValueError("Could not mix audio. Check that each file contains an audio track.") from exc
