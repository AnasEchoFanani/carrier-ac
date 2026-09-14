#!/usr/bin/env bash
set -euo pipefail

GITHUB_DIR="${GITHUB_DIR:-$HOME/GitHub}"
REPO_URL="${REPO_URL:-https://github.com/AnasEchoFanani/carrier-ac.git}"
DEST="$GITHUB_DIR/carrier-ac"

mkdir -p "$GITHUB_DIR"

if [[ -d "$DEST/.git" ]]; then
  git -C "$DEST" pull --ff-only
else
  git clone "$REPO_URL" "$DEST"
fi

cd "$DEST"

if ! command -v uv >/dev/null 2>&1; then
  python -m pip install --user uv
  export PATH="$HOME/.local/bin:$PATH"
fi

if command -v pnpm >/dev/null 2>&1; then
  pnpm install
elif command -v npm >/dev/null 2>&1; then
  npm install
else
  echo "Need nodejs/npm: sudo pacman -S nodejs npm" >&2
  exit 1
fi

uv sync --directory server --extra dev

echo "Installed in $DEST"
echo "Run: cd $DEST && pnpm dev"
