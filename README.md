# MADVID

MADVID is an open-source AI product introduction video generator that analyzes a local project, website, or app-store listing and turns it into a polished 15–30 second product demo video.

It is designed to work as a reusable CLI tool and as a lightweight integration layer for AI-related terminal environments, including common developer tooling and AI assistants.

## Overview

MADVID takes a product source, understands the core workflow and value proposition, creates a short storyboard, and renders a final MP4 using a configurable visual style. This makes it useful for:

- product launches
- open-source project intros
- SaaS / startup landing-page demos
- app-store and marketplace previews
- AI tooling showcases

## Features

- Local project analysis
- Website analysis from a public URL
- Google Play listing analysis
- Apple App Store listing analysis
- 15–30 second output duration
- Minimal and cinematic visual styles
- Landscape and vertical output
- Optional voice-over support
- Preview mode for rapid iteration
- Security redaction for sensitive values
- Extensible architecture for future providers and renderers

## Requirements

- Python 3.9+
- pip
- Internet access for website or app-store analysis

## Installation

### Install as a tool without cloning the full repo

If the project is published to a Git repository, users can install it directly as a command-line tool:

```bash
uv tool install "git+https://github.com/your-org/madvid.git"
```

For a local checkout, this also works without cloning into a workspace project:

```bash
cd /path/to/madvid
uv tool install --editable .
```

Then verify the command is available:

```bash
madvid --help
```

### Standard local install

```bash
git clone <your-repo-url>
cd madvid
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

## Quick start

### Python library usage

MADVID is also a proper Python library for any application or AI workflow that needs to generate a 15–30 second product intro video from a project or URL.

```python
from madvid import MADVID, LocalProvider

client = MADVID(llm_provider=LocalProvider())
result = client.generate_from_project(
    project_root=".",
    duration=20,
    style="minimal",
    preview=True,
)

print(result["video_path"])
print(result["metadata"]["duration"])
```

You can also pass any custom LLM provider that implements `analyze()`:

```python
from madvid import MADVID

class MyLLM:
    name = "my-llm"

    def analyze(self, prompt: str, context: dict | None = None) -> str:
        return "Summarized product story for a compelling intro video."

client = MADVID(llm_provider=MyLLM())
result = client.generate(
    project_root=".",
    duration=20,
    style="cinematic",
)
```

### CLI usage

Run MADVID against the current project directory:

```bash
cd /path/to/your/project
madvid
```

Generate a preview for a local project:

```bash
madvid --preview --duration 20 --style minimal
```

Generate a cinematic preview with voice-over disabled:

```bash
madvid --duration 25 --style cinematic --landscape --no-voice
```

## Usage examples

### Local project

```bash
cd my-product
madvid
```

### Website URL

```bash
madvid https://example.com
```

### Google Play listing

```bash
madvid "https://play.google.com/store/apps/details?id=com.example.app"
```

### Apple App Store listing

```bash
madvid "https://apps.apple.com/us/app/example/id123456789"
```

### Preview only

```bash
madvid --preview --duration 20 --style minimal
```

### Vertical output

```bash
madvid --vertical --duration 18 --style cinematic
```

## Command reference

```bash
madvid [URL] [options]
```

Options:

```bash
--duration N          Video duration in seconds (15-30)
--voice               Enable voice-over
--no-voice            Disable voice-over
--vertical            Use vertical orientation
--landscape           Use landscape orientation
--preview             Generate a quick low-resolution preview
--style {minimal,cinematic}
```

Example commands:

```bash
madvid --duration 20 --style minimal
madvid https://example.com --duration 30 --style cinematic
madvid --preview --duration 18 --vertical
madvid --no-voice --landscape
```

## Project configuration

MADVID supports project-level configuration using a configuration file and follows the precedence order below:

CLI > project config > global config > defaults

Example configuration:

```json
{
  "defaultDuration": 20,
  "defaultStyle": "minimal",
  "defaultOrientation": "landscape",
  "voice": false,
  "preview": false
}
```

## AI CLI compatibility

MADVID is built to work across common AI-related CLI environments rather than being tied to a single vendor or terminal.

### Supported adapter families

- GitHub Copilot CLI
- OpenAI Codex CLI
- Claude Code
- Gemini CLI
- Aider
- Generic shell-based wrappers

### Install AI CLI wrappers

```bash
./scripts/install_ai_cli_adapters.sh
```

This installs thin command wrappers that delegate to the same MADVID CLI implementation.

Example usage after installation:

```bash
copilot --help
codex --help
claude --help
gemini --help
```

## Architecture

MADVID follows a modular pipeline:

1. Source detection and resolution
2. Local project, website, or store analysis
3. Product understanding and feature extraction
4. Storyboard generation
5. Rendering and export
6. Validation and metadata output

This separation keeps the project reusable, testable, and easy to extend with additional sources, renderers, or AI providers.

## Security

MADVID attempts to avoid exposing sensitive values by redacting common credential patterns before writing metadata or logs. It is designed to operate without uploading private project details unless explicitly configured by the user or environment.

## Development

Install development dependencies:

```bash
python -m pip install -e .[dev]
```

Run tests:

```bash
pytest -q
```

Run linting:

```bash
ruff check .
```

## Contributing

Contributions are welcome. Please keep changes focused, add tests when behavior changes, and follow the existing project structure.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
