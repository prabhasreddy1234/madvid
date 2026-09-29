"""Provider abstractions for AI and runtime integrations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class LLMProvider(ABC):
    name = "base"

    @abstractmethod
    def analyze(self, prompt: str, context: Optional[dict] = None) -> str:
        raise NotImplementedError


class VisionProvider(ABC):
    @abstractmethod
    def inspect(self, image_path: str, prompt: str) -> str:
        raise NotImplementedError


class VoiceProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str, output_path: str) -> str:
        raise NotImplementedError


class BrowserProvider(ABC):
    @abstractmethod
    def open_url(self, url: str) -> str:
        raise NotImplementedError


class MobileAutomationProvider(ABC):
    @abstractmethod
    def launch(self, app_target: str) -> bool:
        raise NotImplementedError


class RendererProvider(ABC):
    @abstractmethod
    def render(self, *args, **kwargs):
        raise NotImplementedError


class LocalProvider(LLMProvider, VisionProvider, VoiceProvider, BrowserProvider, MobileAutomationProvider, RendererProvider):
    name = "local"

    def analyze(self, prompt: str, context: Optional[dict] = None) -> str:
        return "Local provider stub; no external AI call configured."

    def inspect(self, image_path: str, prompt: str) -> str:
        return f"Local vision inspection for {image_path}: prompt accepted but no external service configured."

    def synthesize(self, text: str, output_path: str) -> str:
        return output_path

    def open_url(self, url: str) -> str:
        return url

    def launch(self, app_target: str) -> bool:
        return True

    def render(self, *args, **kwargs):
        return args
