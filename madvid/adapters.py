"""Terminal and skill integration adapters for MADVID."""

from __future__ import annotations


class TerminalAdapter:
    """Base adapter for AI terminals or skill environments."""

    name = "generic"

    def install(self, source_path: str, target_dir: str) -> str:
        return f"Install MADVID into {target_dir} from {source_path}."

    def invoke(self, command: str) -> str:
        return command

    def manifest(self) -> dict:
        return {
            "name": self.name,
            "command": "madvid",
            "description": "Generate product-introduction videos from projects, websites, or app-store listings.",
        }


class SpecKitAdapter(TerminalAdapter):
    name = "speckit"

    def install(self, source_path: str, target_dir: str) -> str:
        return f"Register MADVID as a SpecKit skill under {target_dir}."


class CopilotCliAdapter(TerminalAdapter):
    name = "copilot-cli"

    def install(self, source_path: str, target_dir: str) -> str:
        return f"Register MADVID with the Copilot CLI under {target_dir} and expose /madvid."


class CodexCliAdapter(TerminalAdapter):
    name = "codex-cli"

    def install(self, source_path: str, target_dir: str) -> str:
        return f"Register MADVID with the Codex CLI under {target_dir} and expose /madvid."


class ClaudeCodeAdapter(TerminalAdapter):
    name = "claude-code"

    def install(self, source_path: str, target_dir: str) -> str:
        return f"Register MADVID with Claude Code under {target_dir} and expose /madvid."


class GeminiCliAdapter(TerminalAdapter):
    name = "gemini-cli"

    def install(self, source_path: str, target_dir: str) -> str:
        return f"Register MADVID with Gemini CLI under {target_dir} and expose /madvid."


class AiderCliAdapter(TerminalAdapter):
    name = "aider-cli"

    def install(self, source_path: str, target_dir: str) -> str:
        return f"Register MADVID with Aider under {target_dir} and expose /madvid."


def get_adapter(name: str) -> TerminalAdapter:
    adapters = {
        "generic": TerminalAdapter(),
        "speckit": SpecKitAdapter(),
        "copilot-cli": CopilotCliAdapter(),
        "codex-cli": CodexCliAdapter(),
        "claude-code": ClaudeCodeAdapter(),
        "gemini-cli": GeminiCliAdapter(),
        "aider-cli": AiderCliAdapter(),
    }
    return adapters.get((name or "generic").lower(), TerminalAdapter())
