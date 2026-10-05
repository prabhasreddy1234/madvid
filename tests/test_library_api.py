import json
import subprocess
import wave
from dataclasses import FrozenInstanceError
from pathlib import Path

import imageio.v2 as iio
import imageio_ffmpeg
import numpy as np
import pytest
from PIL import Image

from madvid import MADVID, LocalProvider, generate_video
from madvid.asset_manager import discover_video_assets
from madvid.ffmpeg_renderer import render_video_ffmpeg
from madvid.models import ProductContext, StoryboardScene
from madvid.storyboard_generator import generate_storyboard
from madvid.styles import get_style
import madvid.video_renderer as video_renderer
from madvid.video_renderer import _apply_transition, _make_frame, render_video


def test_style_presets_are_immutable():
    style = get_style("minimal")

    with pytest.raises(FrozenInstanceError):
        style.accent = "#ffffff"


def test_ffmpeg_renderer_maps_screenshot_input_after_background(tmp_path, monkeypatch):
    screenshot_path = tmp_path / "screenshot.png"
    Image.new("RGB", (96, 64), (35, 150, 100)).save(screenshot_path)
    storyboard = generate_storyboard(product_name="Demo App", duration=3)[2:3]
    commands = []

    def fail_render(command, **kwargs):
        commands.append(command)
        raise subprocess.CalledProcessError(8, command)

    monkeypatch.setattr("madvid.ffmpeg_renderer._ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr("madvid.ffmpeg_renderer.subprocess.run", fail_render)

    with pytest.raises(subprocess.CalledProcessError):
        render_video_ffmpeg(
            product_name="Demo App",
            output_dir=str(tmp_path),
            duration=3,
            preview=True,
            storyboard=storyboard,
            visual_assets=[str(screenshot_path)],
        )

    filtergraph = commands[0][commands[0].index("-filter_complex") + 1]
    assert "[1:v]" in filtergraph
    assert "[0:v]" not in filtergraph


def test_ffmpeg_filtergraph_failure_falls_back_to_pil(tmp_path, monkeypatch):
    fallback_result = (str(tmp_path / "preview.mp4"), str(tmp_path / "metadata.json"))
    screenshot_path = tmp_path / "screenshot.png"
    Image.new("RGB", (96, 64), (35, 150, 100)).save(screenshot_path)

    def fail_render(**kwargs):
        raise subprocess.CalledProcessError(8, ["ffmpeg"])

    monkeypatch.setattr(video_renderer, "_ffmpeg_available", lambda: True)
    monkeypatch.setattr("madvid.ffmpeg_renderer.render_video_ffmpeg", fail_render)
    monkeypatch.setattr(video_renderer, "_render_video_pil", lambda **kwargs: fallback_result)

    assert video_renderer.render_video(
        "Demo App", output_dir=str(tmp_path), preview=True, visual_assets=[str(screenshot_path)]
    ) == fallback_result


def test_library_generates_video_from_project(tmp_path):
    project_dir = tmp_path / "demo-app"
    project_dir.mkdir()
    (project_dir / "README.md").write_text("# Demo App\n\n- Fast onboarding\n- Clear workflow\n- Useful metrics\n", encoding="utf-8")
    screenshots_dir = project_dir / "assets" / "screenshots"
    screenshots_dir.mkdir(parents=True)
    Image.new("RGB", (640, 360), (35, 150, 100)).save(screenshots_dir / "dashboard.png")

    client = MADVID(llm_provider=LocalProvider())
    result = client.generate_from_project(
        project_root=str(project_dir),
        duration=15,
        style="minimal",
        preview=True,
    )

    assert result["metadata"]["duration"] == 15
    assert result["metadata"]["preview"] is True
    assert result["video_path"].endswith(".mp4")
    assert result["metadata"]["visualSource"] == "product_screenshots"
    assert result["metadata"]["visualAssetCount"] == 1
    assert result["storyboard"][2].text_overlay == "Fast onboarding"
    assert result["storyboard"][-1].text_overlay == "Explore the product"


def test_final_render_generates_animated_product_concept_without_screenshot(tmp_path, monkeypatch):
    monkeypatch.setattr(video_renderer, "_ffmpeg_available", lambda: False)
    monkeypatch.setattr(video_renderer, "_resolve_resolution", lambda orientation, preview=False: (240, 136))

    result = render_video("Demo App", output_dir=str(tmp_path), duration=15, style="minimal")

    assert result[0].endswith("product-intro.mp4")
    assert result[1].endswith("metadata.json")
    metadata = json.loads(Path(result[1]).read_text(encoding="utf-8"))
    assert metadata["duration"] == 15
    assert metadata["visualSource"] == "animated_product_concept"
    reader = iio.get_reader(result[0])
    try:
        assert not np.array_equal(reader.get_data(0), reader.get_data(20))
    finally:
        reader.close()


def test_llm_receives_motion_led_product_video_brief():
    prompts = []

    class PromptProvider:
        name = "prompt-test"

        def analyze(self, prompt, context=None):
            prompts.append(prompt)
            return "{}"

    MADVID(llm_provider=PromptProvider())._enrich_product(
        ProductContext(product_name="Demo App"), source_label="WEBSITE", duration=25
    )

    assert "25-second product intro/demo" in prompts[0]
    assert "not a screenshot slideshow" in prompts[0]
    assert "at most two short proof moments" in prompts[0]


def test_discover_video_assets_finds_recordings_and_ignores_build_output(tmp_path):
    videos_dir = tmp_path / "assets" / "videos"
    videos_dir.mkdir(parents=True)
    (videos_dir / "product-demo.mp4").write_bytes(b"video")
    (videos_dir / "notes.txt").write_text("not a video", encoding="utf-8")
    ignored_dir = tmp_path / "assets" / "videos" / "build"
    ignored_dir.mkdir()
    (ignored_dir / "generated.mp4").write_bytes(b"video")

    assets = discover_video_assets(str(tmp_path))

    assert assets == [str(videos_dir / "product-demo.mp4")]


def test_project_generation_uses_recording_and_mixes_real_audio(tmp_path):
    project_dir = tmp_path / "recorded-app"
    videos_dir = project_dir / "assets" / "videos"
    videos_dir.mkdir(parents=True)
    (project_dir / "README.md").write_text("# Recorded App\n\n- Clear workflow\n", encoding="utf-8")

    recording_path = videos_dir / "product-demo.mp4"
    writer = iio.get_writer(str(recording_path), fps=12, codec="libx264", macro_block_size=1)
    for frame_index in range(12):
        frame = np.zeros((64, 96, 3), dtype=np.uint8)
        frame[:, :, 0] = frame_index * 18
        writer.append_data(frame)
    writer.close()

    audio_dir = project_dir / "assets" / "audio"
    audio_dir.mkdir()
    samples = (np.sin(np.arange(8000) * 2 * np.pi * 440 / 16000) * 4000).astype(np.int16)
    audio_paths = [audio_dir / "narration.wav", audio_dir / "music.wav"]
    for audio_path in audio_paths:
        with wave.open(str(audio_path), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(16000)
            output.writeframes(samples.tobytes())

    result = generate_video(
        project_root=str(project_dir),
        duration=1,
        style="minimal",
        preview=True,
        voiceover_audio=str(audio_paths[0]),
        music_audio=str(audio_paths[1]),
    )

    assert result["metadata"]["visualSource"] == "product_video_clips"
    assert result["metadata"]["videoAssetCount"] == 1
    assert result["metadata"]["audioTracks"] == ["voiceover", "music"]
    subprocess.run(
        [
            imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-i", result["video_path"],
            "-map", "0:a:0", "-f", "null", "-",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    with pytest.raises(ValueError, match="too short for its timeline segment"):
        render_video(
            "Recorded App",
            output_dir=str(project_dir / "short-render"),
            duration=2,
            style="minimal",
            preview=True,
            storyboard=result["storyboard"],
            video_assets=[str(recording_path)],
        )


def test_failed_audio_mux_preserves_previous_export(tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    existing_export = output_dir / "preview.mp4"
    existing_export.write_bytes(b"previous export")
    screenshot_path = tmp_path / "screen.png"
    Image.new("RGB", (640, 360), (35, 150, 100)).save(screenshot_path)
    invalid_audio = tmp_path / "invalid-audio.wav"
    invalid_audio.write_text("not an audio stream", encoding="utf-8")

    with pytest.raises(ValueError, match="Could not mix the supplied audio"):
        render_video(
            "Demo App",
            output_dir=str(output_dir),
            duration=1,
            style="minimal",
            preview=True,
            visual_assets=[str(screenshot_path)],
            voiceover_audio=str(invalid_audio),
        )

    assert existing_export.read_bytes() == b"previous export"
    assert not list(output_dir.glob(".*.tmp.mp4"))


def test_real_screenshots_cross_dissolve_between_scenes():
    red_screen = Image.new("RGB", (640, 360), (230, 35, 40))
    blue_screen = Image.new("RGB", (640, 360), (35, 50, 230))

    transition = _make_frame(480, 270, "Demo", "cinematic", 244, 480, [red_screen, blue_screen])

    red, green, blue = transition.getpixel((240, 135))
    assert red > 50
    assert blue > 50
    assert green < 60


@pytest.mark.parametrize(
    ("width", "height", "chrome_point", "image_point"),
    [
        (480, 270, (50, 56), (100, 150)),
        (270, 480, (40, 68), (135, 180)),
    ],
)
def test_product_shot_uses_framed_capture_in_both_orientations(width, height, chrome_point, image_point):
    screenshot = Image.new("RGB", (640, 360), (35, 150, 100))

    frame = _make_frame(width, height, "Demo", "cinematic", 12, 24, [screenshot])

    chrome_pixel = frame.getpixel(chrome_point)
    assert min(chrome_pixel) > 200
    assert frame.getpixel(image_point) == (35, 150, 100)


def test_portrait_product_capture_uses_phone_frame():
    screenshot = Image.new("RGB", (360, 640), (35, 150, 100))

    frame = _make_frame(480, 270, "Demo", "cinematic", 12, 24, [screenshot])

    assert min(frame.getpixel((50, 56))) < 100
    assert sum(pixel == (35, 150, 100) for pixel in frame.getdata()) > 1000


def test_many_product_screenshots_map_to_available_storyboard_scenes():
    screenshots = [
        Image.new("RGB", (640, 360), (35 + index * 20, 50, 230 - index * 20))
        for index in range(6)
    ]
    storyboard = generate_storyboard(
        product_name="Demo Website",
        product_category="Website product",
        duration=12,
        source_type="WEBSITE",
        important_screens=["Landing page", "Features", "Benefits", "Get started"],
    )
    frame = _make_frame(480, 270, "Demo Website", "cinematic", 240, 288, screenshots, storyboard)

    assert frame.size == (480, 270)
    assert frame.getbbox() == (0, 0, 480, 270)


def test_premium_shot_animates_camera_highlight_and_cursor():
    screenshot = Image.new("RGB", (1440, 900), (245, 243, 255))
    scene = StoryboardScene(
        "0-3s",
        "Product reveal",
        "Avento landing page",
        "Get Started",
        "",
        "Cross dissolve",
        "Hero screen",
        camera_focus=(0.5, 0.535),
        highlight_box=(0.43, 0.50, 0.57, 0.57),
        cursor_target=(0.5, 0.535),
    )

    opening = _make_frame(480, 270, "Avento", "premium", 0, 24, [screenshot], [scene])
    interaction = _make_frame(480, 270, "Avento", "premium", 12, 24, [screenshot], [scene])
    closing = _make_frame(480, 270, "Avento", "premium", 23, 24, [screenshot], [scene])

    assert opening.size == (480, 270)
    assert opening.tobytes() != interaction.tobytes()
    assert interaction.tobytes() != closing.tobytes()


@pytest.mark.parametrize("transition", ["Directional push", "Soft wipe"])
def test_directional_transitions_reveal_the_next_scene(transition):
    previous = Image.new("RGB", (100, 60), (220, 30, 30))
    current = Image.new("RGB", (100, 60), (30, 30, 220))

    frame = _apply_transition(previous, current, 0.5, transition)

    assert frame.getpixel((10, 30)) != frame.getpixel((90, 30))


def test_light_flash_transition_adds_a_brief_highlight():
    previous = Image.new("RGB", (100, 60), (20, 20, 20))
    current = Image.new("RGB", (100, 60), (40, 40, 40))

    frame = _apply_transition(previous, current, 0.5, "Light flash")

    assert min(frame.getpixel((50, 30))) > 150


def test_product_shot_has_motion_within_a_scene():
    screenshot = Image.new("RGB", (640, 360), (35, 150, 100))

    opening = _make_frame(480, 270, "Demo", "cinematic", 0, 24, [screenshot])
    closing = _make_frame(480, 270, "Demo", "cinematic", 23, 24, [screenshot])

    assert opening.tobytes() != closing.tobytes()


def test_generate_video_function_uses_project_root_and_provider(tmp_path):
    project_dir = tmp_path / "instant-app"
    project_dir.mkdir()
    (project_dir / "README.md").write_text("# Instant App\n\n- Easy setup\n- Clear output\n- Clear value\n", encoding="utf-8")

    result = generate_video(
        project_root=str(project_dir),
        duration=20,
        style="cinematic",
        preview=True,
        llm_provider=LocalProvider(),
    )

    assert result["metadata"]["style"] == "cinematic"
    assert result["metadata"]["duration"] == 20
    assert result["metadata"]["visualSource"] == "animated_product_concept"
