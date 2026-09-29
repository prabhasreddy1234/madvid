"""Security helpers that redact secrets before they reach logs or prompts."""

from __future__ import annotations

import re

SECRET_PATTERNS = (
    r"(?is)(api[_-]?key|access[_-]?token|client[_-]?secret|secret[_-]?key|password|passwd|private[_-]?key|session[_-]?id|authorization|cookie|token)\s*[:=]\s*['\"]?[^\s,'\"]+",
    r"(?is)(sk-[A-Za-z0-9]+|ghp_[A-Za-z0-9]+|xox[baprs]-[A-Za-z0-9-]+|AIza[0-9A-Za-z\-_]+)",
)


def filter_sensitive_data(text: str) -> str:
    """Return a redacted copy of text that removes common secret patterns."""
    if not text:
        return ""
    sanitized = text
    for pattern in SECRET_PATTERNS:
        sanitized = re.sub(pattern, "[REDACTED]", sanitized)
    return sanitized
