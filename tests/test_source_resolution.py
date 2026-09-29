from madvid.source_resolver import SourceType, resolve_source


def test_resolve_website_url():
    source = resolve_source("https://example.com")
    assert source == SourceType.WEBSITE


def test_resolve_play_store_url():
    source = resolve_source("https://play.google.com/store/apps/details?id=com.example.app")
    assert source == SourceType.PLAY_STORE


def test_resolve_app_store_url():
    source = resolve_source("https://apps.apple.com/us/app/example/id123456789")
    assert source == SourceType.APP_STORE


def test_resolve_current_project_when_no_url():
    source = resolve_source(None, project_root="/tmp")
    assert source in {SourceType.PROJECT, SourceType.WEBSITE}
