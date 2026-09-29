#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
TARGET_DIR="${1:-$HOME/.claude/skills}"

mkdir -p "$TARGET_DIR/madvid"
cp -R "$ROOT_DIR/skills/madvid/." "$TARGET_DIR/madvid/"

cat <<EOF
MADVID installation complete.
Skill installed to: $TARGET_DIR/madvid
Use the AI terminal to reload and then invoke: /madvid
EOF
