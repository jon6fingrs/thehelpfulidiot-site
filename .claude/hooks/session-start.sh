#!/bin/bash
# SessionStart hook for Claude Code cloud sessions: install the pinned Zola
# so `zola build` / `zola check` / scripts/check-site.py work immediately.
# Idempotent: skips the download when the right version is already present
# (the container is cached after this runs). Local sessions are untouched.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Keep in step with README.md, .github/workflows/preview.yml and
# themes/tabi/theme.toml (min_version).
ZOLA_VERSION="0.23.6"
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"

if "$BIN_DIR/zola" --version 2>/dev/null | grep -qx "zola $ZOLA_VERSION"; then
  echo "zola $ZOLA_VERSION already installed"
else
  url="https://github.com/getzola/zola/releases/download/v${ZOLA_VERSION}/zola-v${ZOLA_VERSION}-x86_64-unknown-linux-gnu.tar.gz"
  for delay in 2 4 8 16 0; do
    if curl -fsSL "$url" | tar xz -C "$BIN_DIR" zola; then break; fi
    [ "$delay" -eq 0 ] && { echo "failed to download zola $ZOLA_VERSION" >&2; exit 1; }
    sleep "$delay"
  done
  echo "installed $("$BIN_DIR/zola" --version)"
fi

if [ -n "${CLAUDE_ENV_FILE:-}" ] && ! grep -qs "$BIN_DIR" "$CLAUDE_ENV_FILE"; then
  echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$CLAUDE_ENV_FILE"
fi
