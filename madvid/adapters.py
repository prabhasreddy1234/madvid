"""Terminal and skill integration adapters for MADVID."""

from __future__ import annotations


class TerminalAdapter:
    """Base adapter for AI terminals or skill environments."""

    name = "generic"

    def install(self, source_path: str, target_dir: str) -> str:
        return f"Install MADVID into {target_dir} from {source_path}."

    def invoke(self, command: str) -> str:
        return command


class SpecKitAdapter(TerminalAdapter):
    name = "speckit"

    def install(self, source_path: str, target_dir: str) -> str:
        return f"Register MADVID as a SpecKit skill under {target_dir}."


class CopilotCliAdapter(TerminalAdapter):
    name = "copilot-cli"


class CodexCliAdapter(TerminalAdapter):
    name = "codex-cli"


class ClaudeCodeAdapter(TerminalAdapter):
    name = "claude-code"
