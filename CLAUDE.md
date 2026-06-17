# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A versioned dotfiles repo for Claude Code global configuration. Running `stow .` from this directory symlinks everything into `~/.claude/`, including this file to `~/.claude/CLAUDE.md`. That makes this the **global CLAUDE.md** — it is loaded by Claude Code in every session across all projects, not scoped to this repo.

## Structure

- `.claude/settings.json` — project-level permissions and enabled plugins
- `.claude/plugins/known_marketplaces.json` — plugin marketplace sources (currently `anthropics/claude-plugins-official` via GitHub, auto-updating)
- `.claude/skills/<skill-name>/SKILL.md` — custom slash-command skills invoked via the `Skill` tool

## Skills

Each skill lives in its own subdirectory under `.claude/skills/`. The `SKILL.md` file is the entire skill definition — it uses YAML frontmatter for `name` and `description`, then markdown for the implementation instructions.

The `description` field is what Claude Code reads to decide when to trigger the skill automatically, so keep it precise and trigger-oriented.

Current custom skill: `cg-reply-pr-review` — analyzes unresolved PR review threads against the branch diff and outputs a JSON array of draft replies. It relies on `pr-threads-not-from-me` being available as a shell command.

## Settings

Permissions in `.claude/settings.json` use the pattern `"Tool(glob)"`. The current allowlist pre-approves `grep *` to reduce prompts for read-only searches.

Plugins are enabled by key under `enabledPlugins` — the key format is `<plugin-name>@<marketplace-id>`.

## Coding Guidelines

Behavioral guidelines to reduce common LLM coding mistakes.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

### 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.
