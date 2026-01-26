#!/usr/bin/env bash
# Wrapper to run hooks with graceful failure handling
# Usage: run-with-fallback.sh <fail-mode> <hook-script>
# fail-mode: "open" (advisory) or "closed" (safety-critical)

set -uo pipefail

FAIL_MODE="$1"
HOOK_SCRIPT="$2"
HOOK_NAME="$(basename "$HOOK_SCRIPT")"

# Check if hook file exists
if [[ ! -f "$HOOK_SCRIPT" ]]; then
    if [[ "$FAIL_MODE" == "closed" ]]; then
        echo "{\"hookSpecificOutput\": {\"permissionDecision\": \"deny\", \"permissionDecisionReason\": \"Safety hook not found: $HOOK_NAME. Blocking for safety. Check .claude/hooks/ directory.\"}}"
    else
        echo "{\"hookSpecificOutput\": {\"additionalContext\": \"Warning: Hook not found: $HOOK_NAME. Proceeding without validation.\"}}"
    fi
    exit 0
fi

# Check if hook is executable
if [[ ! -x "$HOOK_SCRIPT" ]]; then
    chmod +x "$HOOK_SCRIPT" 2>/dev/null || true
fi

# Try to execute the hook
if uv run --script "$HOOK_SCRIPT"; then
    exit 0
fi

# Hook execution failed
if [[ "$FAIL_MODE" == "closed" ]]; then
    echo "{\"hookSpecificOutput\": {\"permissionDecision\": \"deny\", \"permissionDecisionReason\": \"Safety hook execution failed: $HOOK_NAME. Blocking for safety.\"}}"
else
    echo "{\"hookSpecificOutput\": {\"additionalContext\": \"Warning: Hook execution failed: $HOOK_NAME. Check hook logs for details.\"}}"
fi

exit 0
