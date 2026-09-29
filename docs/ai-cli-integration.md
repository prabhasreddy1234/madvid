# AI CLI integration

MADVID is built to be reusable across multiple AI-related CLIs.

## Common integration pattern

1. Keep the MADVID core library in Python.
2. Create a thin adapter for each CLI environment.
3. Point the adapter to the same `madvid` command.
4. Expose a command or slash alias that forwards arguments.

## Included wrappers

The repository includes wrapper scripts for common CLI families:

- `scripts/ai-clis/copilot.sh`
- `scripts/ai-clis/codex.sh`
- `scripts/ai-clis/claude.sh`
- `scripts/ai-clis/gemini.sh`

These wrappers are intentionally minimal and do not alter MADVID logic.

## Registration guidance

Every AI CLI has a different registration model. In general, the adapter should do one of the following:

- install a command wrapper on PATH
- register a slash-command alias or skill manifest
- expose a command that calls `madvid` with the user arguments

## Why this pattern works

It keeps the MADVID product logic stable while allowing tool-specific wrappers to adapt to the host environment.
