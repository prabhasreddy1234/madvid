from madvid.store_analyzer import analyze_store_url
from madvid.website_analyzer import analyze_website


def test_analyze_website_extracts_title_and_value(monkeypatch):
    class FakeResponse:
        status_code = 200
        text = """
        <html>
          <head>
            <title>Acme Flow</title>
            <meta name="description" content="Track work and shipping in one place." />
          </head>
          <body><h1>Acme Flow</h1></body>
        </html>
        """

    monkeypatch.setattr("requests.get", lambda *a, **k: FakeResponse())
    context = analyze_website("https://example.com")
    assert context.product_name == "Acme Flow"
    assert "shipping" in context.value_proposition.lower()


def test_analyze_store_url_identifies_play_store_listing(monkeypatch):
    context = analyze_store_url("https://play.google.com/store/apps/details?id=com.example.app")
    assert context.source_type == "PLAY_STORE"
    assert "App" in context.product_name or "Example" in context.product_name or context.product_category


def test_analyze_store_url_identifies_app_store_listing(monkeypatch):
    context = analyze_store_url("https://apps.apple.com/us/app/example/id123456789")
    assert context.source_type == "APP_STORE"
    assert context.product_name
