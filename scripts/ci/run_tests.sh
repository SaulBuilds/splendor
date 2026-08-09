#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Splendor local CI — runs the whole tests/splendor/ suite headlessly and exits
# non-zero on any failure. Local-only by design: the Blender-runtime tests need
# the built binary, which stock GitHub-hosted runners don't have (a self-hosted
# runner or a prebuilt binary would be needed to move this to Actions).
#
# Usage:  bash scripts/ci/run_tests.sh
#         SPLENDOR_BLENDER=/path/to/blender bash scripts/ci/run_tests.sh
set -u

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
BLENDER="${SPLENDOR_BLENDER:-$REPO/../build_linux/bin/blender}"
cd "$REPO" || exit 2

# Tests that require the Blender runtime (bpy / gpu).
BLENDER_TESTS=(
  tests/splendor/test_s0_2_retro_shader.py
  tests/splendor/test_s0_3_governed_action_api.py
  tests/splendor/test_spl_s1_ui.py
  tests/splendor/test_spl_s2_nodes.py
  tests/splendor/test_spl_s2_backends.py
  tests/splendor/test_spl_s3_training.py
)
# Pure-Python tests (test_s0_4 spawns Blender internally).
PYTHON_TESTS=(
  tests/splendor/test_s0_4_mcp_server.py
  tests/splendor/test_s0_5_backend_router.py
  tests/splendor/test_s0_6_eval_sdk.py
  tests/splendor/test_s0_7_workflow_graph.py
  tests/splendor/test_s0_8_chain_pinning.py
)

pass=0; fail=0; skip=0
failed=()
log=/tmp/spl_ci_last.log

run() {  # $1 label, rest = command
  local label="$1"; shift
  local start; start=$SECONDS
  if "$@" >"$log" 2>&1; then
    printf '  \033[32mPASS\033[0m  %-46s %ss\n' "$label" "$((SECONDS - start))"
    pass=$((pass + 1))
  else
    local rc=$?
    printf '  \033[31mFAIL\033[0m  %-46s (exit %s)\n' "$label" "$rc"
    sed 's/^/        /' "$log" | tail -20
    fail=$((fail + 1)); failed+=("$label")
  fi
}

echo "== Splendor local CI =="
echo "repo:    $REPO"
echo "blender: $BLENDER"
echo

for t in "${PYTHON_TESTS[@]}"; do run "$t" python3 "$t"; done

if [ -x "$BLENDER" ]; then
  for t in "${BLENDER_TESTS[@]}"; do
    run "$t" "$BLENDER" --background --factory-startup --python "$t"
  done
else
  echo "  SKIP  Blender-runtime tests — binary not found at $BLENDER"
  echo "        (set SPLENDOR_BLENDER, or build the fork)"
  skip=$((skip + ${#BLENDER_TESTS[@]}))
fi

echo
echo "== $pass passed · $fail failed · $skip skipped =="
if [ "$fail" -ne 0 ]; then
  printf '   - %s\n' "${failed[@]}"
  exit 1
fi
echo "ALL GREEN"
