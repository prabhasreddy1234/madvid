"""MADVID package."""

from .config import Config, load_config
from .core import MADVID, generate_video
from .providers import LLMProvider, LocalProvider
from .source_resolver import SourceType, resolve_source
from .store_analyzer import analyze_store_url
from .validation import validate_duration, validate_orientation, validate_style
from .website_analyzer import analyze_website

__all__ = [
    "MADVID",
    "Config",
    "LLMProvider",
    "LocalProvider",
    "SourceType",
    "analyze_store_url",
    "analyze_website",
    "generate_video",
    "load_config",
    "resolve_source",
    "validate_duration",
    "validate_orientation",
    "validate_style",
]
