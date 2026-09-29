from madvid import MADVID, LocalProvider, generate_video


def test_library_generates_video_from_project(tmp_path):
    project_dir = tmp_path / "demo-app"
    project_dir.mkdir()
    (project_dir / "README.md").write_text("# Demo App\n\n- Fast onboarding\n- Clear workflow\n- Useful metrics\n", encoding="utf-8")

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
