#!/bin/bash
# Claude Code status line — Catppuccin Frappe powerline style
# Receives JSON session data on stdin, prints a single colored line
# Requires a Nerd Font (e.g. any Nerd Font patched terminal font)
#
# Setup:
#   1. Save this file to ~/.claude/statusline.sh
#   2. chmod +x ~/.claude/statusline.sh
#   3. Add to ~/.claude/settings.json:
#      {
#        "statusLine": {
#          "type": "command",
#          "command": "bash ~/.claude/statusline.sh",
#          "padding": 0
#        }
#      }
#   4. Restart Claude Code
#
# Segments (left to right):
#   [model] [git branch +staged ~modified] [context bar % tokens $cost duration] [output style] [agent] [vim mode]
#
# Dependencies: jq, git, awk, md5/md5sum

input=$(cat)

# Catppuccin Frappe — truecolor ANSI (foreground only)
FG_BLUE=$'\e[38;2;140;170;238m'    # #8caaee
FG_GREEN=$'\e[38;2;166;209;137m'   # #a6d189
FG_YELLOW=$'\e[38;2;229;200;144m'  # #e5c890
FG_MAUVE=$'\e[38;2;202;158;230m'   # #ca9ee6
FG_TEAL=$'\e[38;2;129;200;190m'    # #81c8be
FG_PEACH=$'\e[38;2;239;159;118m'   # #ef9f76
FG_DIM=$'\e[38;2;115;121;148m'     # #737994 overlay0 — empty bar portion

BOLD=$'\e[1m'
RESET=$'\e[0m'

# Nerd Font glyphs
SEP='|'
CHIP='✨'   # U+274B eight teardrop-spoked propeller asterisk
BRANCH='' # U+E0A0
ROBOT=''  # U+F544 fa-robot󱙺

# Extract all fields in one jq call (unit separator to handle empty fields)
IFS=$'\x1f' read -r CURRENT_DIR MODEL DIR PCT USED_TOKENS MAX_TOKENS COST VIM_MODE DURATION_MS STYLE AGENT TOTAL_INPUT TOTAL_OUTPUT CTX_SIZE REMAINING_PCT CURRENT_USAGE EXCEEDS_200K WORKTREE_NAME WORKTREE_BRANCH < <(
  echo "$input" | jq -r '[
    (.workspace.current_dir // ""),
    (.model.display_name // "claude"),
    (.workspace.current_dir // ""),
    ((.context_window.used_percentage // 0) | floor | tostring),
    (.context_window.used_tokens // 0 | tostring),
    (.context_window.max_tokens // 0 | tostring),
    (.cost.total_cost_usd // 0 | tostring),
    (.vim.mode // ""),
    (.cost.total_duration_ms // 0 | tostring),
    (.output_style.name // "default"),
    (.agent.name // ""),
    (.context_window.total_input_tokens // 0 | tostring),
    (.context_window.total_output_tokens // 0 | tostring),
    (.context_window.context_window_size // 0 | tostring),
    ((.context_window.remaining_percentage // 0) | floor | tostring),
    (.context_window.current_usage // 0 | tostring),
    (.context_window.exceeds_200k_tokens // false | tostring),
    (.worktree.name // ""),
    (.worktree.branch // "")
  ] | join("\u001f")'
)

# Git status — cached to avoid lag on large repos
CACHE_DIR_KEY=$(printf '%s' "$DIR" | md5 2>/dev/null || printf '%s' "$DIR" | md5sum 2>/dev/null | cut -d' ' -f1)
CACHE_FILE="/tmp/statusline-git-cache-${CACHE_DIR_KEY}"
CACHE_MAX_AGE=5

cache_is_stale() {
    [ ! -f "$CACHE_FILE" ] && return 0
    local age=$(( $(date +%s) - $(stat -f %m "$CACHE_FILE" 2>/dev/null || stat -c %Y "$CACHE_FILE" 2>/dev/null || echo 0) ))
    [ "$age" -gt "$CACHE_MAX_AGE" ]
}

if cache_is_stale; then
    if [ -n "$DIR" ] && git -C "$DIR" rev-parse --git-dir > /dev/null 2>&1; then
        BRANCH_NAME=$(git -C "$DIR" branch --show-current 2>/dev/null)
        STAGED=$(git -C "$DIR" diff --cached --numstat 2>/dev/null | wc -l | tr -d ' ')
        MODIFIED=$(git -C "$DIR" diff --numstat 2>/dev/null | wc -l | tr -d ' ')
        printf '1|%s|%s|%s\n' "$BRANCH_NAME" "$STAGED" "$MODIFIED" > "$CACHE_FILE"
    else
        printf '0|||\n' > "$CACHE_FILE"
    fi
fi

IFS='|' read -r IS_GIT BRANCH_NAME STAGED MODIFIED < "$CACHE_FILE"

# Context bar — 10 chars, block medium style: ████▒▒▒▒▒▒
FILLED=$((PCT * 10 / 100))
EMPTY=$((10 - FILLED))
BAR=""
[ "$FILLED" -gt 0 ] && BAR="${FG_MAUVE}$(printf "%${FILLED}s" | tr ' ' '█')"
[ "$EMPTY"  -gt 0 ] && BAR="${BAR}${FG_DIM}$(printf "%${EMPTY}s" | tr ' ' '▒')"
BAR="${BAR}${RESET}"

# Token usage formatting (e.g. "12k/200k")
TOKEN_FMT=$(awk -v u="$USED_TOKENS" -v m="$MAX_TOKENS" 'BEGIN {
    if (u+0 == 0 && m+0 == 0) { print ""; exit }
    if (u >= 1000) uf = sprintf("%.0fk", u/1000)
    else uf = u
    if (m >= 1000) mf = sprintf("%.0fk", m/1000)
    else mf = m
    if (m+0 > 0) printf "%s/%s", uf, mf
    else printf "%s", uf
}')

# Input/output token formatting
INPUT_FMT=$(awk -v t="$TOTAL_INPUT" 'BEGIN {
    if (t+0 == 0) { print ""; exit }
    if (t >= 1000) printf "↑%.0fk", t/1000
    else printf "↑%s", t
}')
OUTPUT_FMT=$(awk -v t="$TOTAL_OUTPUT" 'BEGIN {
    if (t+0 == 0) { print ""; exit }
    if (t >= 1000) printf "↓%.0fk", t/1000
    else printf "↓%s", t
}')

# Cost formatting
COST_FMT=$(awk -v c="$COST" 'BEGIN { printf "💸 %.2f$", c+0 }')

# Duration formatting
DURATION_FMT=$(awk -v ms="$DURATION_MS" 'BEGIN {
    s = int(ms / 1000); m = int(s / 60); h = int(m / 60)
    if (h > 0) printf "⏰ %dh%dm", h, m % 60
    else        printf "⏰ %dm", m
}')

# Git segment color — yellow if dirty, green if clean
GIT_COLOR="$FG_GREEN"
if [ "${IS_GIT:-0}" = "1" ]; then
    if [ "${STAGED:-0}" -gt 0 ] || [ "${MODIFIED:-0}" -gt 0 ]; then
        GIT_COLOR="$FG_YELLOW"
    fi
fi

# Vim mode color
VIM_COLOR="$FG_GREEN"
[ "$VIM_MODE" = "NORMAL" ] && VIM_COLOR="$FG_YELLOW"

# Build line — model segment
LINE="${RESET}${FG_BLUE}${BOLD}${CHIP} ${MODEL}${RESET}"

# Git segment
if [ "${IS_GIT:-0}" = "1" ]; then
    GIT_TEXT="${BRANCH} ${BRANCH_NAME}"
    [ "${STAGED:-0}"   -gt 0 ] && GIT_TEXT="${GIT_TEXT} +${STAGED}"
    [ "${MODIFIED:-0}" -gt 0 ] && GIT_TEXT="${GIT_TEXT} ~${MODIFIED}"
    LINE="${LINE} ${FG_DIM}${SEP}${RESET} ${GIT_COLOR}${BOLD}${GIT_TEXT}${RESET}"
fi

# Worktree segment
if [ -n "$WORKTREE_NAME" ]; then
    WORKTREE_TEXT="$WORKTREE_NAME"
    [ -n "$WORKTREE_BRANCH" ] && WORKTREE_TEXT="${WORKTREE_TEXT} ${BRANCH} ${WORKTREE_BRANCH}"
    LINE="${LINE} ${FG_DIM}${SEP}${RESET} ${FG_TEAL}${BOLD}${WORKTREE_TEXT}${RESET}"
fi

# Context + tokens + cost + duration segment
CTX_TEXT="${BAR}${FG_MAUVE} ${PCT}%"
[ -n "$TOKEN_FMT" ] && CTX_TEXT="${CTX_TEXT} ${TOKEN_FMT}"
CTX_TEXT="${CTX_TEXT}${RESET} ${FG_DIM}${SEP}${RESET} ${FG_MAUVE}${BOLD}${DURATION_FMT}"
[ -n "$INPUT_FMT" ]  && CTX_TEXT="${CTX_TEXT}${RESET} ${FG_DIM}${SEP}${RESET} ${FG_MAUVE}${BOLD}${INPUT_FMT}"
[ -n "$OUTPUT_FMT" ] && CTX_TEXT="${CTX_TEXT}${RESET} ${FG_DIM}${SEP}${RESET} ${FG_MAUVE}${BOLD}${OUTPUT_FMT}"

# Extra context window fields
CTX_SIZE_FMT=$(awk -v t="$CTX_SIZE" 'BEGIN { if (t+0==0) exit; if (t>=1000) printf "🧠 %.0fk",t/1000; else printf "🧠 %s",t }')
[ -n "$CTX_SIZE_FMT" ]     && CTX_TEXT="${CTX_TEXT}${RESET} ${FG_DIM}${SEP}${RESET} ${FG_MAUVE}${BOLD}${CTX_SIZE_FMT}"
[ "${REMAINING_PCT:-0}" -gt 0 ] && CTX_TEXT="${CTX_TEXT}${RESET} ${FG_DIM}${SEP}${RESET} ${FG_MAUVE}${BOLD}🤖 ${REMAINING_PCT}%"
CURRENT_USAGE_FMT=$(awk -v t="$CURRENT_USAGE" 'BEGIN { if (t+0==0) exit; if (t>=1000) printf "cur:%.0fk",t/1000; else printf "cur:%s",t }')
[ -n "$CURRENT_USAGE_FMT" ] && CTX_TEXT="${CTX_TEXT}${RESET} ${FG_DIM}${SEP}${RESET} ${FG_MAUVE}${BOLD}${CURRENT_USAGE_FMT}"
[ "$EXCEEDS_200K" = "true" ] && CTX_TEXT="${CTX_TEXT}${RESET} ${FG_DIM}${SEP}${RESET} ${FG_PEACH}${BOLD}>200k"
CTX_TEXT="${CTX_TEXT}${RESET} ${FG_DIM}${SEP}${RESET} ${FG_MAUVE}${BOLD}${COST_FMT}"

LINE="${LINE} ${FG_DIM}${SEP}${RESET} ${FG_MAUVE}${BOLD}${CTX_TEXT}${RESET}"

# Output style — teal, hidden when default
if [ -n "$STYLE" ] && [ "$STYLE" != "default" ]; then
    LINE="${LINE} ${FG_DIM}${SEP}${RESET} ${FG_TEAL}${BOLD}${STYLE}${RESET}"
fi

# Agent — peach, only shown when --agent flag is active
if [ -n "$AGENT" ]; then
    LINE="${LINE} ${FG_DIM}${SEP}${RESET} ${FG_PEACH}${BOLD}${ROBOT} ${AGENT}${RESET}"
fi

# Vim mode — only shown when vim mode is enabled
if [ -n "$VIM_MODE" ]; then
    LINE="${LINE} ${FG_DIM}${SEP}${RESET} ${VIM_COLOR}${BOLD}${VIM_MODE}${RESET}"
fi

printf '%s\n' "$LINE"
