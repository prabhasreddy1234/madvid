#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
TARGET_DIR="${1:-$HOME/.madvid/skills}"

mkdir -p "$TARGET_DIR"
cp -R "$ROOT_DIR/skills/madvid" "$TARGET_DIR/"

cat <<EOF
MADVID installation complete.
Skill copy installed to: $TARGET_DIR
Use the AI terminal to reload and then invoke: /madvid
EOF
