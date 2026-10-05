"""Website analysis for MADVID."""

from __future__ import annotations

import re
from html.parser import HTMLParser

import requests

from .models import ProductContext


class _PageCopyParser(HTMLParser):
    _ignored_tags = {"script", "style", "noscript", "svg"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text_parts: list[str] = []
        self.headings: list[str] = []
        self.controls: list[str] = []
        self._ignored: list[str] = []
        self._heading_tag: str | None = None
        self._heading_parts: list[str] = []
        self._control_tag: str | None = None
        self._control_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        if self._ignored:
            if tag in self._ignored_tags:
                self._ignored.append(tag)
            return
        if tag in self._ignored_tags:
            self._ignored.append(tag)
        elif tag in {"h1", "h2", "h3"}:
            self._heading_tag = tag
            self._heading_parts = []
        elif tag in {"a", "button"}:
            self._control_tag = tag
            self._control_parts = []

    def handle_endtag(self, tag: str):
        if self._ignored:
            if tag == self._ignored[-1]:
                self._ignored.pop()
            return
        if tag == self._heading_tag:
            self._append_unique(self.headings, " ".join(self._heading_parts))
            self._heading_tag = None
        if tag == self._control_tag:
            self._append_unique(self.controls, " ".join(self._control_parts))
            self._control_tag = None

    def handle_data(self, data: str):
        if self._ignored:
            return
        text = re.sub(r"\s+", " ", data).strip()
        if not text:
            return
        self.text_parts.append(text)
        if self._heading_tag:
            self._heading_parts.append(text)
        if self._control_tag:
            self._control_parts.append(text)

    @staticmethod
    def _append_unique(values: list[str], value: str) -> None:
        normalized = re.sub(r"\s+", " ", value).strip()
        if normalized and normalized.casefold() not in {item.casefold() for item in values}:
            values.append(normalized)


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
    except (requests.RequestException, OSError, ValueError, TypeError):
        html = ""

    product_name = _extract_title(html)
    if " - " in product_name:
        product_name = product_name.split(" - ", 1)[0]
    if " | " in product_name:
        product_name = product_name.split(" | ", 1)[0]
    description = _extract_meta_description(html)
    page_copy = _PageCopyParser()
    page_copy.feed(html)
    headings = [
        heading for heading in page_copy.headings
        if heading.casefold() != product_name.casefold()
    ][:8]
    value = description or (headings[0] if headings else "A modern product experience built to help users move faster.")
    features = headings[:5] or [
        "Landing page overview",
        "Core workflow",
        "Primary value proposition",
    ]
    call_to_action = next(
        (
            label for label in page_copy.controls
            if any(term in label.casefold() for term in ("start", "try", "sign up", "book", "demo", "explore", "download", "join"))
        ),
        "Get started",
    )
    if len(product_name) > 50:
        product_name = product_name[:47].rstrip() + "..."

    return ProductContext(
        product_name=product_name,
        product_category="Website product",
        target_user="Website visitors",
        value_proposition=value,
        primary_workflow=features[0],
        features=features,
        visual_identity="Website brand identity and motion-led product presentation",
        important_screens=["Landing page", *features[:3]],
        cta=call_to_action,
        source_type="WEBSITE",
        source_url=url,
        metadata={"url": url, "description": value, "headings": headings, "calls_to_action": page_copy.controls[:6]},
    )
