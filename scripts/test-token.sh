#!/usr/bin/env bash
# Verify CLAUDE_CODE_OAUTH_TOKEN works headlessly, the way the container will use it.
#
# Runs claude with a scrubbed env and a throwaway HOME so the token is the only
# thing that can authenticate. Without that, the CLI silently falls back to your
# ~/.claude login and the test passes even with a dead token.
#
#   ./scripts/test-token.sh            # reads CLAUDE_CODE_OAUTH_TOKEN from .env
#   ./scripts/test-token.sh <token>    # or test one directly
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

TOKEN="${1:-}"
if [ -z "$TOKEN" ]; then
  [ -f .env ] || { echo "No .env and no token argument."; exit 1; }
  TOKEN="$(grep -E '^CLAUDE_CODE_OAUTH_TOKEN=' .env | head -1 | cut -d= -f2- | tr -d '"'"'"' \r')"
fi

if [ -z "$TOKEN" ]; then
  echo "FAIL  CLAUDE_CODE_OAUTH_TOKEN is empty in .env"
  echo "      Run: claude setup-token   then paste the token into .env"
  exit 1
fi

CLAUDE="$(command -v claude || echo "$HOME/.local/bin/claude")"
[ -x "$CLAUDE" ] || { echo "FAIL  claude CLI not found"; exit 1; }

echo "Token:  ${TOKEN:0:12}…${TOKEN: -4}  (${#TOKEN} chars)"
echo "CLI:    $CLAUDE"
echo

SANDBOX="$(mktemp -d)"
trap 'rm -rf "$SANDBOX"' EXIT

# env -i: no inherited ANTHROPIC_API_KEY, no existing session, HOME is empty.
OUT="$(env -i \
  HOME="$SANDBOX" \
  PATH="/usr/bin:/bin:/usr/local/bin:$(dirname "$CLAUDE")" \
  CLAUDE_CODE_OAUTH_TOKEN="$TOKEN" \
  "$CLAUDE" --print --output-format json \
    --model claude-haiku-4-5-20251001 \
    -p 'Reply with exactly: TOKEN_OK' 2>&1)"
CODE=$?

if [ $CODE -ne 0 ]; then
  echo "FAIL  exit $CODE"
  echo "$OUT" | head -20
  exit 1
fi

if ! grep -q "TOKEN_OK" <<<"$OUT"; then
  echo "FAIL  authenticated call did not come back as expected"
  echo "$OUT" | head -20
  exit 1
fi

echo "PASS  token authenticates headlessly with no ~/.claude login"
python3 - "$OUT" <<'PY' 2>/dev/null || true
import json, sys
try:
    d = json.loads(sys.argv[1])
except Exception:
    sys.exit(0)
print(f"      model: {d.get('modelUsage') and list(d['modelUsage'])[0] or '?'}")
print(f"      cost:  ${d.get('total_cost_usd', 0):.6f}")
PY
