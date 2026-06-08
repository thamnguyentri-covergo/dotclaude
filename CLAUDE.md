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
