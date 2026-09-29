# MADVID

MADVID = AI Product Introduction Video Generator.

MADVID is an open-source, reusable AI-terminal skill that inspects a local project, deployed website, or App Store / Google Play listing and produces a polished 15–30 second product introduction video.

## What it does

MADVID resolves a source, analyzes the product, extracts the core workflow and value proposition, creates a storyboard, and renders a final MP4 with optional voice-over and preview mode. It is intentionally built as a reusable skill/library rather than a single one-off prompt.

## Demo

Demo placeholder coming soon.

## Features

- Project-aware video generation
- Website video generation
- Play Store support
- App Store support
- 15–30 second videos
- Voice-over support
- Preview mode
- Minimal style
- Cinematic style
- Landscape and vertical output
- Open-source and extensible architecture
- Provider abstraction for LLM, vision, and renderer integration

## Installation

1. Clone this repository.
2. Install the Python package and dependencies:

```bash
cd madvid
python3 -m pip install -e .
```

3. Register the skill in your AI-terminal environment or use the included CLI script:

```bash
./madvid
```

4. Reload the terminal if your environment requires it.

## Usage

```bash
/madvid
/madvid <url>
/madvid --duration 20 --voice --style cinematic
/madvid https://example.com --duration 30 --style minimal
/madvid --vertical --duration 20 --no-voice
/madvid --preview --style cinematic
```

## Examples

### Current project

```bash
cd my-product
/madvid
```

### Deployed website

```bash
/madvid https://example.com
```

### Google Play listing

```bash
/madvid https://play.google.com/store/apps/details?id=com.example.app
```

### App Store listing

```bash
/madvid https://apps.apple.com/us/app/example/id123456789
```

## Architecture

MADVID uses a modular pipeline:

1. Source resolution
2. Project or website analysis
3. Product understanding
4. Feature extraction
5. Asset discovery
6. Storyboard generation
7. Voice-over or captions
8. Video composition
9. Style application
10. Validation and output

The implementation is intentionally separated into reusable components that can be expanded with new source adapters, renderers, and AI providers.

## Configuration

MADVID accepts optional project config at `.madvid/config.json` with precedence:

CLI > project config > global config > defaults

Example:

```json
{
  "defaultDuration": 20,
  "defaultStyle": "minimal",
  "defaultOrientation": "landscape",
  "voice": false,
  "resolution": "1080p"
}
```

## Security

MADVID never uploads source code or secrets without explicit provider configuration. It redacts common secret patterns before writing logs or metadata, and it avoids reading or exposing .env files, tokens, certificates, and credentials.

## SpecKit and reusable skill integration

The repository includes a skill definition under `skills/madvid` and a generic adapter model so the project can be reused by different AI-terminal environments. This allows a user to register MADVID as a reusable skill and invoke it with `/madvid` after installation.

## AI CLI compatibility

MADVID is designed to be reusable across AI-related CLIs through a thin adapter model rather than being tied to one vendor.

Supported adapter families:

- GitHub Copilot CLI
- OpenAI Codex CLI
- Claude Code
- Gemini CLI
- Aider
- generic shell-based wrappers

Generic usage:

```bash
madvid --help
madvid --preview --duration 20 --style minimal
```

Wrapper installation:

```bash
./scripts/install_ai_cli_adapters.sh
```

This installs small command wrappers that delegate to the same MADVID CLI implementation.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, contribution guidelines, and extension patterns.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
