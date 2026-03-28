#!/bin/bash
set -e

SKILL_SRC="$(cd "$(dirname "$0")/coolpc" && pwd)"
SKILL_DST="$HOME/.claude/skills/coolpc"

echo "Installing coolpc skill..."
rm -rf "$SKILL_DST"
cp -r "$SKILL_SRC" "$SKILL_DST"

echo "Installed: $SKILL_DST"
echo "Files:"
find "$SKILL_DST" -type f | sed "s|$SKILL_DST/|  |"
