import pytest

from madvid.config import Config, load_config
from madvid.validation import validate_duration, validate_orientation, validate_style


def test_duration_validation_accepts_allowed_range():
    assert validate_duration(20) == 20
    assert validate_duration(15) == 15
    assert validate_duration(30) == 30


def test_duration_validation_rejects_invalid_duration():
    with pytest.raises(ValueError):
        validate_duration(10)
    with pytest.raises(ValueError):
        validate_duration(31)


def test_orientation_validation():
    assert validate_orientation("landscape") == "landscape"
    assert validate_orientation("vertical") == "vertical"
    with pytest.raises(ValueError):
        validate_orientation("square")


def test_style_validation():
    assert validate_style("minimal") == "minimal"
    assert validate_style("cinematic") == "cinematic"
    with pytest.raises(ValueError):
        validate_style("retro")


def test_config_precedence():
    project_cfg = {"defaultDuration": 20, "defaultStyle": "minimal", "voice": False}
    cfg = load_config(project_cfg=project_cfg, cli_overrides={"defaultDuration": 25, "voice": True})
    assert cfg.default_duration == 25
    assert cfg.default_style == "minimal"
    assert cfg.voice is True


def test_config_defaults():
    cfg = Config()
    assert cfg.default_duration == 20
    assert cfg.default_style == "minimal"
    assert cfg.default_orientation == "landscape"
    assert cfg.voice is False
