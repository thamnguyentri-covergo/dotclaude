#!/usr/bin/env bash
# PreToolUse(Bash) hook: while the skill is active, all Mongo access must go through ro-query.py.
cmd=$(jq -r '.tool_input.command // ""') || { echo "Blocked: unreadable hook input" >&2; exit 2; }
if grep -qiE 'mongosh|\bmongo\b|mongodb(\+srv)?://|DEV_MONGODB_URI' <<<"$cmd"; then
  echo "Blocked: query Mongo only via ro-query.py (read-only guard). Do not call mongosh or read \$DEV_MONGODB_URI directly." >&2
  exit 2
fi
exit 0
