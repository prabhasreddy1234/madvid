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
    assert storyboard[0].scene == "Opening hook"
    assert any(scene.scene == "Product reveal" for scene in storyboard)
    assert len(storyboard) >= 5
    assert storyboard[-1].timestamp.endswith("20s")
    assert storyboard[0].voice_over == "Keep every project moving in one place."
    assert storyboard[-1].text_overlay == "Start your project"
    assert "Example App" in storyboard[0].visual
    assert sum(scene.use_product_capture is True for scene in storyboard) <= 2
    assert storyboard[0].use_product_capture is False
    assert storyboard[-1].use_product_capture is False
    assert "do not use a screenshot" in storyboard[0].visual


def test_storyboard_visuals_match_website_and_mobile_app_sources():
    website = generate_storyboard(
        product_name="Acme Flow",
        product_category="Website product",
        source_type="WEBSITE",
        important_screens=["Landing page", "Workspace", "Results"],
        visual_identity="Clean product interface",
        target_user="Operations teams",
    )
    mobile_app = generate_storyboard(
        product_name="Acme Pocket",
        product_category="iOS app",
        source_type="APP_STORE",
        important_screens=["Welcome screen", "Daily plan", "Completed task"],
    )

    assert "Website screen: Workspace" in website[2].visual
    assert "Clean product interface" in website[0].visual
    assert "for Operations teams" in website[0].visual
    assert "Mobile app screen: Daily plan" in mobile_app[2].visual
    assert "Daily plan" in mobile_app[2].visual
    assert all(scene.transition != "Light flash" for scene in website)
