# MADVID skill

## Purpose

MADVID is a reusable AI-terminal skill that analyzes a local product, website, or app-store listing and creates a product introduction video.

## installation

### Install as a skill/tool without cloning the full repo

For environments that support tool installation, install MADVID directly:

```bash
uv tool install "git+https://github.com/your-org/madvid.git"
```

or, from a local checkout:

```bash
cd /path/to/madvid
uv tool install --editable .
```

Then invoke the command from a project folder:

```bash
madvid --help
madvid --preview --duration 20 --style premium
```

### Register in an AI terminal

1. Install the skill with `./scripts/install.sh`, or copy `skills/madvid` to the
	target AI-terminal skill directory. For Claude Code, the personal skill path
	is `~/.claude/skills/madvid`.
2. Reload the terminal or skill registry.
3. Invoke `/madvid`.

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
