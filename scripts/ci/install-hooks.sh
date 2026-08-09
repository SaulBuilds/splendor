#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Install Splendor's local git hooks (the pre-push CI gate).
set -eu
REPO="$(git rev-parse --show-toplevel)"
HOOK_DIR="$REPO/.git/hooks"
SRC="$REPO/scripts/ci/hooks"

for hook in pre-push; do
  cp "$SRC/$hook" "$HOOK_DIR/$hook"
  chmod +x "$HOOK_DIR/$hook"
  echo "installed $hook → $HOOK_DIR/$hook"
done
echo "Done. The suite now runs before every push (SPLENDOR_SKIP_CI=1 git push to bypass)."
