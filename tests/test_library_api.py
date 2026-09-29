import pytest
from PIL import Image

from madvid import MADVID, LocalProvider, generate_video
from madvid.video_renderer import _make_frame, render_video


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
    assert result["storyboard"][1].text_overlay == "Fast onboarding"
    assert result["storyboard"][-1].text_overlay == "Explore the product"


def test_final_render_requires_real_product_screenshot(tmp_path):
    with pytest.raises(ValueError, match="requires real product screenshots"):
        render_video("Demo App", output_dir=str(tmp_path), duration=15)


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
    assert result["metadata"]["visualSource"] == "no_product_screenshots"
