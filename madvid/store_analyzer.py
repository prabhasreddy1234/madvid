"""Google Play and App Store listing analysis."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from .models import ProductContext


def _title_case(value: str) -> str:
    value = value.replace("-", " ").replace("_", " ")
    value = re.sub(r"\s+", " ", value).strip()
    return value.title() if value else "App Product"


def analyze_store_url(url: str) -> ProductContext:
    """Infer product context from a public store listing URL."""
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    path = parsed.path or ""

    if "play.google.com" in host:
        source_type = "PLAY_STORE"
        product_name = "Play Store App"
        category = "Android app"
        product_id = re.search(r"id=([^&]+)", url)
        if product_id:
            product_name = _title_case(product_id.group(1).replace("com.", "").replace(".app", ""))
    elif "apps.apple.com" in host or "itunes.apple.com" in host:
        source_type = "APP_STORE"
        product_name = "App Store App"
        category = "iOS app"
        match = re.search(r"/app/([^/]+)/id\d+", path)
        if match:
            product_name = _title_case(match.group(1))
    else:
        source_type = "APP_STORE"
        product_name = "Store App"
        category = "Productivity app"

    return ProductContext(
        product_name=product_name,
        product_category=category,
        target_user="App users",
        value_proposition="A polished app experience designed to help people complete core tasks quickly.",
        primary_workflow="Primary app workflow",
        features=["Onboarding", "Core workflow", "Fast result", "Clear action"],
        visual_identity="Modern app product marketing visuals",
        important_screens=["Welcome screen", "Core flow", "Outcome view"],
        cta="Get the app",
        source_type=source_type,
        source_url=url,
        metadata={"url": url, "storeType": source_type},
    )
