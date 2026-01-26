#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
gh-web-fallback: Proactively guide to GitHub API when gh CLI is unavailable in Web environments.

Event: PreToolUse (Bash)

Purpose: Proactively guides Claude to use the GitHub REST API with curl BEFORE attempting `gh`
commands in environments where `gh` CLI is unavailable but `GITHUB_TOKEN` is available
(e.g., Claude Code Web).

Behavior:
- Detects when Claude attempts to invoke `gh` CLI commands
- Checks if `gh` CLI is NOT available using system PATH lookup
- Checks if `GITHUB_TOKEN` environment variable is available
- If both conditions are met, provides comprehensive guidance on using curl with GitHub API
- Includes 5-minute cooldown mechanism to avoid repetitive suggestions

Triggers on:
- Bash commands containing `gh` invocations: `gh issue list`, `git status && gh pr create`, etc.
- `gh` CLI is NOT available in PATH
- `GITHUB_TOKEN` is available and non-empty

Does NOT trigger when:
- `gh` CLI is available (defers to `prefer-gh-for-own-repos.py` for those cases)
- `GITHUB_TOKEN` is not available (no alternative available)
- Within 5-minute cooldown period since last suggestion
- Non-Bash tools
- Command doesn't contain `gh` invocations

Command detection:
Uses regex pattern `(?:^|[;&|]\s*)gh\s+` to match:
- Simple: `gh issue list`
- Piped: `git status | gh issue view 10`
- Chained: `git status && gh pr create`
- OR chains: `cat file || gh pr view 10`
- But NOT: `sigh`, `high` (gh must be standalone command)

Guidance provided:
- Environment explanation (gh unavailable, token available)
- 4 practical curl examples with proper authentication headers:
  1. View issue/PR
  2. List issues
  3. Create pull request
  4. Check CI status
- Tips on using `-s` flag and JSON parsing with `jq`
- Link to GitHub API documentation

Example patterns:
```bash
# View issue
curl -s -H "Authorization: token $(printenv GITHUB_TOKEN)" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/OWNER/REPO/issues/NUMBER"

# Create PR
curl -X POST -H "Authorization: token $(printenv GITHUB_TOKEN)" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/OWNER/REPO/pulls" \
  -d '{"title":"PR Title","head":"branch","base":"main","body":"Description"}'
```

State management:
- Cooldown state stored in: `~/.claude/hook-state/gh-web-fallback-cooldown`
- Contains Unix timestamp of last suggestion
- 300-second (5-minute) cooldown period
- Gracefully handles corrupted state files
- Auto-creates state directory as needed

Benefits:
- Prevents failed `gh` command attempts in Web environments
- Provides guidance proactively (before failure) rather than reactively
- Saves a tool call (no fail-then-retry cycle)
- Works alongside `gh-fallback-helper.py` as defense in depth

Relationship with other hooks:
- **Complements `prefer-gh-for-own-repos.py`**: When `gh` IS available, that hook suggests using it;
  when gh is NOT available, this hook suggests the API
- **Works with `gh-fallback-helper.py`**: This hook provides proactive guidance (PreToolUse);
  if it's missed or cooldown prevents it, gh-fallback-helper provides reactive guidance (PostToolUseFailure)

Limitations:
- Cooldown may prevent guidance on subsequent `gh` commands within 5 minutes
- Command detection is regex-based; unusual command structures may not be detected
- Only monitors Bash tool (not other command execution methods)
"""
import json
import sys
import shutil
import os
import re
import time
from pathlib import Path

# Cooldown period in seconds (5 minutes)
COOLDOWN_PERIOD = 300

# State file location
STATE_DIR = Path.home() / ".claude" / "hook-state"
STATE_FILE = STATE_DIR / "gh-web-fallback-cooldown"

# Regex pattern to detect gh command invocations
# Matches: gh, && gh, || gh, ; gh, etc.
# But NOT: sigh, high (gh must be a standalone command)
GH_COMMAND_PATTERN = r"(?:^|[;&|]\s*)gh\s+"


def is_gh_available():
    """Check if gh CLI is available in PATH."""
    try:
        return shutil.which("gh") is not None
    except Exception:
        return False


def is_github_token_available():
    """Check if GITHUB_TOKEN environment variable is set and non-empty."""
    try:
        token = os.environ.get("GITHUB_TOKEN", "").strip()
        return len(token) > 0
    except Exception:
        return False


def is_gh_command(command):
    """Check if command is attempting to use gh CLI using regex pattern."""
    try:
        if not command:
            return False
        # Use multiline mode to detect gh in chained commands
        return bool(re.search(GH_COMMAND_PATTERN, command, re.MULTILINE))
    except Exception:
        return False


def is_within_cooldown():
    """Check if we're within the cooldown period since last suggestion."""
    try:
        if not STATE_FILE.exists():
            return False

        last_suggestion_time = float(STATE_FILE.read_text().strip())
        current_time = time.time()

        return (current_time - last_suggestion_time) < COOLDOWN_PERIOD
    except Exception:
        # Gracefully handle corrupted state file
        return False


def record_suggestion():
    """Record that we just made a suggestion."""
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(str(time.time()))
    except Exception as e:
        # Log but don't fail - cooldown is nice-to-have, not critical
        print(f"Warning: Could not record cooldown state: {e}", file=sys.stderr)


def main():
    try:
        input_data = json.load(sys.stdin)
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        # Only monitor Bash tool
        if tool_name != "Bash":
            print("{}")
            sys.exit(0)

        # Extract command from tool input
        command = tool_input.get("command", "")

        # Check if command is attempting to use gh
        if not is_gh_command(command):
            print("{}")
            sys.exit(0)

        # Check if gh is available - if it is, don't suggest (let prefer-gh hook handle it)
        if is_gh_available():
            print("{}")
            sys.exit(0)

        # Check if GITHUB_TOKEN is available - if not, we can't help
        if not is_github_token_available():
            print("{}")
            sys.exit(0)

        # Check if we're within cooldown period - if so, don't suggest again
        if is_within_cooldown():
            print("{}")
            sys.exit(0)

        # Record this suggestion to enable cooldown
        record_suggestion()

        # Provide guidance to use GitHub API with curl
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": """**ENVIRONMENT NOTICE: Claude Code Web Detected**

The `gh` CLI is not available in this environment, but `GITHUB_TOKEN` is available.
Use the GitHub REST API with curl instead.

**GitHub API Patterns:**

1. **View issue/PR:**
   ```bash
   curl -s -H "Authorization: token $(printenv GITHUB_TOKEN)" \\
     -H "Accept: application/vnd.github.v3+json" \\
     "https://api.github.com/repos/OWNER/REPO/issues/NUMBER"
   ```

2. **List issues:**
   ```bash
   curl -s -H "Authorization: token $(printenv GITHUB_TOKEN)" \\
     -H "Accept: application/vnd.github.v3+json" \\
     "https://api.github.com/repos/OWNER/REPO/issues"
   ```

3. **Create pull request:**
   ```bash
   curl -X POST -H "Authorization: token $(printenv GITHUB_TOKEN)" \\
     -H "Accept: application/vnd.github.v3+json" \\
     "https://api.github.com/repos/OWNER/REPO/pulls" \\
     -d '{"title":"PR Title","head":"branch","base":"main","body":"Description"}'
   ```

4. **Check CI status:**
   ```bash
   curl -s -H "Authorization: token $(printenv GITHUB_TOKEN)" \\
     -H "Accept: application/vnd.github.v3+json" \\
     "https://api.github.com/repos/OWNER/REPO/commits/SHA/check-runs"
   ```

**Tips:**
- Use `-s` flag for silent mode (no progress)
- Parse JSON with `jq` or `python3 -m json.tool` (never manual string parsing)
- Use `$(printenv GITHUB_TOKEN)` instead of `$GITHUB_TOKEN` when using pipes
- GitHub API docs: https://docs.github.com/en/rest

**This message will only appear once per 5 minutes.**"""
            }
        }

        print(json.dumps(output))
        sys.exit(0)

    except Exception as e:
        # Log to stderr for debugging
        print(f"Error in gh-web-fallback hook: {e}", file=sys.stderr)
        # Always output valid JSON on error
        print("{}")
        sys.exit(1)


if __name__ == "__main__":
    main()
