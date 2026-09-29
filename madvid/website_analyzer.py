"""Website analysis for MADVID."""

from __future__ import annotations

import re
from typing import Optional

import requests

from .models import ProductContext


def _extract_title(html: str) -> str:
    match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if match:
        return re.sub(r"\s+", " ", match.group(1)).strip()
    return "Product Website"


def _extract_meta_description(html: str) -> str:
    match = re.search(
        r"<meta[^>]+name=[\"']description[\"'][^>]+content=[\"']([^\"']+)[\"']|<meta[^>]+content=[\"']([^\"']+)[\"'][^>]+name=[\"']description[\"']",
        html,
        re.IGNORECASE | re.DOTALL,
    )
    if match:
        value = match.group(1) or match.group(2) or ""
        return re.sub(r"\s+", " ", value).strip()
    return ""


def analyze_website(url: str) -> ProductContext:
    """Analyze a website URL and return a product context for storyboard generation."""
    try:
        response = requests.get(url, timeout=10)
        if hasattr(response, "raise_for_status"):
            response.raise_for_status()
        html = getattr(response, "text", "")
    except Exception:
        html = ""

    product_name = _extract_title(html)
    if " - " in product_name:
        product_name = product_name.split(" - ", 1)[0]
    if " | " in product_name:
        product_name = product_name.split(" | ", 1)[0]
    description = _extract_meta_description(html) or "A modern product experience with a clear path to value."
    value = description if description else "A modern product experience built to help users move faster."
    features = [
        "Landing page overview",
        "Core workflow",
        "Primary value proposition",
        "Call to action",
    ]
    if len(product_name) > 50:
        product_name = product_name[:47].rstrip() + "..."

    return ProductContext(
        product_name=product_name,
        product_category="Website product",
        target_user="Website visitors",
        value_proposition=value,
        primary_workflow="Primary product workflow",
        features=features,
        visual_identity="Clean product interface and landing-page flow",
        important_screens=["Landing page", "Main workflow", "Result or CTA"],
        cta="Get started",
        source_type="WEBSITE",
        source_url=url,
        metadata={"url": url, "description": value},
    )
