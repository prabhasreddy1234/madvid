# MADVID skill

## Purpose

MADVID is a reusable AI-terminal skill that analyzes a local product, website, or app-store listing and creates a product introduction video.

## installation

1. Clone this repository.
2. Copy the `skills/madvid` directory to the target AI-terminal skill directory.
3. Reload the terminal or skill registry.
4. Invoke `/madvid`.

## Invocation

```text
/madvid
/madvid https://example.com
/madvid https://play.google.com/store/apps/details?id=com.example.app
/madvid https://apps.apple.com/us/app/example/id123456789
```

## Configuration

Use a project-root `.madvid/config.json` or global AI-terminal configuration to set defaults.

## Source resolution

The skill resolves the source in this order:

1. explicit URL
2. current project
3. request user input if necessary

## Output convention

MADVID writes output into `./madvid-output/` with:

- `product-intro.mp4`
- `storyboard.md`
- `voiceover.txt`
- `metadata.json`
- `assets/`

## Terminal adapter guidance

This skill is intentionally terminal-agnostic. Add a thin adapter per environment (GitHub Copilot CLI, Codex CLI, Claude Code, etc.) without altering the core MADVID logic.
