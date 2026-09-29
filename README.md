# MADVID

<div align="center">
  <img src="assets/madvid-logo.svg" alt="MADVID, AI product introduction video generator" width="1120" />
</div>

<p align="center">
  <a href="#installation"><strong>Get started</strong></a> ·
  <a href="#usage"><strong>CLI usage</strong></a> ·
  <a href="#python-library"><strong>Python library</strong></a> ·
  <a href="#ai-cli-compatibility"><strong>AI CLI integration</strong></a>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.9%2B-blue" />
  <img alt="License" src="https://img.shields.io/badge/License-MIT-green" />
  <img alt="CLI" src="https://img.shields.io/badge/CLI-Ready-orange" />
  <img alt="Video" src="https://img.shields.io/badge/Video-15--30s-purple" />
</p>

MADVID is an open-source product video generator for AI teams, founders, and developers who want to turn a product, project, website, or app listing into a polished 15–30 second introduction video.

It is built as a reusable library and command-line tool that can analyze a product source, extract the core story, generate a storyboard, and render a short promotional video with a clean visual identity.

## Why MADVID

MADVID helps teams turn technical work into clear product storytelling without needing a full video production pipeline.

Use it to:

- showcase an app or website in a short demo video
- explain a product idea from a local project
- create launch-ready intros for open-source work
- generate quick video previews for demos or landing pages
- plug into AI assistant workflows and terminal environments

## How it works

MADVID follows a simple pipeline:

1. Detect the source: local project, website, or app store listing
2. Analyze product context and user value
3. Extract features and core workflow
4. Generate a storyboard and product narrative
5. Render a short MP4 with configurable style and duration
6. Output metadata, storyboard, and preview assets

## Features

- Local project analysis
- Website URL analysis
- Google Play and App Store support
- 15–30 second output windows
- Minimal and cinematic visual styles
- Landscape and vertical orientation
- Optional voice-over support
- Preview mode for fast iteration
- Python library API for embedding in apps and workflows
- AI CLI integration layer for Copilot, Claude, Codex, Gemini, and Aider
- Security-conscious redaction of sensitive values

## Installation

### Install as a tool without cloning the full repo

For a published Git repository:

```bash
uv tool install "git+https://github.com/prabhasreddy1234/madvid.git"
```

For a local checkout:

```bash
cd /path/to/madvid
uv tool install --editable .
```

Verify the command is available:

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

### CLI usage

From inside a web app or project folder:

```bash
cd /path/to/your/project
madvid
```

Generate a quick preview:

```bash
madvid --preview --duration 20 --style minimal
```

Generate a cinematic final cut:

```bash
madvid --duration 25 --style cinematic --landscape --no-voice
```

Generate vertical output:

```bash
madvid --vertical --duration 18 --style cinematic
```

### Website and app store examples

```bash
madvid https://example.com
madvid "https://play.google.com/store/apps/details?id=com.example.app"
madvid "https://apps.apple.com/us/app/example/id123456789"
```

## Usage examples

### Local project demo

```bash
cd my-project
madvid --preview --duration 20 --style minimal
```

### Production website demo

```bash
madvid https://my-app.com --duration 30 --style cinematic
```

### Vertical short-form version

```bash
madvid --vertical --duration 16 --style minimal --preview
```

## Command reference

```bash
madvid [URL] [options]
```

Available options:

```bash
--duration N          Video length in seconds (15-30)
--voice               Enable voice-over
--no-voice            Disable voice-over
--vertical            Use vertical orientation
--landscape           Use landscape orientation
--preview             Generate a fast preview render
--style {minimal,cinematic}
```

## Python library

MADVID can be imported directly into any Python project or AI app as a reusable library.

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

A custom provider can also be passed in:

```python
from madvid import MADVID

class MyLLM:
    name = "my-llm"

    def analyze(self, prompt: str, context: dict | None = None) -> str:
        return "Summarized product story for a polished short-form launch video."

client = MADVID(llm_provider=MyLLM())
result = client.generate(
    project_root=".",
    duration=20,
    style="cinematic",
)
```

## AI CLI compatibility

MADVID is built to work across common AI-related CLI environments instead of being permanently tied to a single vendor or runtime.

### Supported integration families

- GitHub Copilot CLI
- OpenAI Codex CLI
- Claude Code
- Gemini CLI
- Aider
- Generic shell wrappers

### Initialize for a target integration

```bash
madvid init my-project --integration copilot
madvid init my-project --integration claude
madvid init my-project --integration codex
madvid init my-project --integration gemini
```

This creates a project-local configuration and records the selected integration target.

### Wrapper install helper

```bash
./scripts/install_ai_cli_adapters.sh
```

This installs lightweight wrappers that call the same MADVID CLI implementation.

## Project configuration

MADVID supports project-local configuration with precedence:

CLI > project config > global config > defaults

Example:

```json
{
  "defaultDuration": 20,
  "defaultStyle": "minimal",
  "defaultOrientation": "landscape",
  "voice": false,
  "preview": false
}
```

## Architecture

MADVID is organized around a modular, provider-driven pipeline:

1. Source detection and resolution
2. Project, website, or app-store analysis
3. Product understanding and feature extraction
4. Storyboard generation
5. Rendering and export
6. Validation and metadata publication

This keeps the project reusable, testable, and extensible for new sources, styles, and AI providers.

## Security

MADVID tries to avoid leaking sensitive values by redacting common credential patterns before writing metadata or logs. It is designed for local and controlled use rather than uploading private project content without explicit configuration.

## Development

Install dev dependencies:

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

Contributions are welcome. Please keep changes focused, add tests for behavior changes, and follow the current project structure.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
