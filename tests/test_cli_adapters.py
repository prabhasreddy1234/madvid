import json

from madvid.adapters import (
    ClaudeCodeAdapter,
    CodexCliAdapter,
    CopilotCliAdapter,
    GeminiCliAdapter,
    TerminalAdapter,
    get_adapter,
)
from madvid.cli import main


def test_generic_adapter_has_base_invocation_behavior():
    adapter = TerminalAdapter()
    assert adapter.name == "generic"
    assert "madvid" in adapter.invoke("madvid --help")


def test_vendor_adapters_are_registered():
    assert CopilotCliAdapter().name == "copilot-cli"
    assert CodexCliAdapter().name == "codex-cli"
    assert ClaudeCodeAdapter().name == "claude-code"
    assert GeminiCliAdapter().name == "gemini-cli"


def test_vendor_adapter_install_text_mentions_skill_registration():
    bundler = CopilotCliAdapter()
    install_text = bundler.install("/tmp/madvid", "~/.config/madvid")
    assert "madvid" in install_text.lower()
    assert "install" in install_text.lower() or "register" in install_text.lower()


def test_get_adapter_accepts_vendor_names_without_prefixes():
    assert get_adapter("copilot").name == "copilot-cli"
    assert get_adapter("claude").name == "claude-code"
    assert get_adapter("codex").name == "codex-cli"


def test_init_command_creates_project_scaffold_for_integration(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = main(["init", "demo-app", "--integration", "copilot"])

    assert result == 0
    project_dir = tmp_path / "demo-app"
    config_path = project_dir / ".madvid" / "config.json"
    assert config_path.exists()

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload["integration"] == "copilot"
    assert payload["defaultStyle"] == "minimal"
