from madvid.security import filter_sensitive_data
from madvid.storyboard_generator import generate_storyboard


def test_filter_sensitive_data_removes_secrets():
    text = "API_KEY=sk-12345\npassword=secret\nOPENAI_API_KEY=abc123\nhello world"
    sanitized = filter_sensitive_data(text)
    assert "API_KEY" not in sanitized
    assert "password" not in sanitized
    assert "sk-12345" not in sanitized
    assert "hello world" in sanitized


def test_generate_storyboard_creates_scene_sequence():
    storyboard = generate_storyboard(
        product_name="Example App",
        product_category="Productivity",
        features=["Track tasks", "Team updates", "Smart summaries"],
        duration=20,
        value_proposition="Keep every project moving in one place.",
        primary_workflow="Plan work with your team.",
        cta="Start your project",
    )
    assert storyboard[0].scene == "Product reveal"
    assert len(storyboard) >= 3
    assert storyboard[-1].timestamp.endswith("20s")
    assert storyboard[0].voice_over == "Keep every project moving in one place."
    assert storyboard[-1].text_overlay == "Start your project"
    assert "Example App" in storyboard[0].visual
