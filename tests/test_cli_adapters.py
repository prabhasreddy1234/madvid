from madvid.adapters import (
    ClaudeCodeAdapter,
    CodexCliAdapter,
    CopilotCliAdapter,
    GeminiCliAdapter,
    TerminalAdapter,
)


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
