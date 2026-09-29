#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
TARGET_DIR="${1:-$HOME/.local/bin}"
mkdir -p "$TARGET_DIR"

for script in "$ROOT_DIR"/scripts/ai-clis/*.sh; do
  name="$(basename "$script" .sh)"
  cp "$script" "$TARGET_DIR/$name"
  chmod +x "$TARGET_DIR/$name"
done

cat <<EOF
MADVID AI CLI adapters installed.
Available wrappers:
  - copilot
  - codex
  - claude
  - gemini

Each wrapper simply executes the MADVID CLI.
EOF
