---
name: covergo-commit
description: Generate a git commit message following CoverGo's standard (Jira-prefixed title + optional body with context/problem/solution). Use when the user asks to "commit", "write a commit message", or runs /covergo-commit. Source standard - https://covergo.atlassian.net/wiki/spaces/Engineering/pages/681017357/Commit+message+the+right+way
---

# CoverGo commit message skill

Mandatory format for master branch of any backend repository:

```
<Jira issue number> <Commit message text>

<optional commit description>
```

## Rules

- **Title**: `<JIRA-KEY> <short imperative summary>` — ≤80 chars total. JIRA key inferred from current branch name (e.g. `feature/CH-42388-...` → `CH-42388`); if absent, ask the user.
- Optional `type:` segment (`feat:`, `fix:`, `chore:`, `refactor:`, `docs:`, `test:`) MAY follow the Jira key when the repo's recent history uses Conventional Commits style. Check `git log --oneline -10` to decide.
- **Bad titles** to avoid: bare Jira keys (`CVHL-1000`), `Fixed error`, `tests`, `Updated`, `wip`, `asdf`.
- **Body required** for features and bugfixes. May be skipped only for: formatting-only, NuGet/dependency bumps, trivial single refactor, maintenance (.gitignore, codeowners).
- Body sections (no headers needed, plain paragraphs in any order):
  - **Context** — domain knowledge a teammate needs to understand the change without asking.
  - **Problem** — why the commit exists, what it solves.
  - **Solution** — high-level approach; highlight non-obvious choices.
  - **Limitations** — library bugs, unsupported features, constraints that shaped the choice.
  - **Shortcomings** — known imperfections, future improvements.
  - **Other** — anything else relevant.
- Wrap body at 72 cols. Blank line between title and body.

## Workflow

1. Run in parallel: `git status`, `git diff --staged` (fall back to `git diff` if nothing staged), `git log --oneline -10`, `git branch --show-current`.
2. Extract Jira key from branch (regex `[A-Z]+-[0-9]+`). If missing, ask user.
3. Decide whether title alone suffices (trivial change) or a full body is required (feature/bugfix).
4. Draft title ≤80 chars, imperative mood ("Add", "Fix", "Update" — not "Added"/"Adds").
5. Draft body only with sections that add real signal. Do not invent context. If a section is empty, omit it — do not write "N/A".
6. Stage the intended files explicitly (`git add <paths>`). Do not `git add -A` / `git add .` unless user confirms.
7. Commit via HEREDOC:

   ```bash
   git commit -m "$(cat <<'EOF'
   <JIRA-KEY> <title>

   <body paragraphs>
   EOF
   )"
   ```

8. Run `git status` to confirm.

## Do not

- Do not add `Co-Authored-By` / `Generated with Claude Code` footers unless the user asks.
- Do not use `--no-verify`, `--amend`, or force-push without explicit user request.
- Do not commit `.env`, credentials, large binaries.
- Do not narrate WHAT the diff shows line-by-line — explain WHY.

## Examples

Good (feature):
```
CH-42388 feat: expose components output from create-pv-v2 action

Downstream SBOM generation needs the resolved <component>:<version>
list produced by `crt release create-v2`. Previously the action only
printed the result to logs, so callers had no machine-readable handle.

Tee crt stdout to crt.log, parse the markdown-table rows with awk,
and emit a newline-separated list via $GITHUB_OUTPUT under the
`components` output.

Parsing relies on crt's current table format; if crt changes its
output layout the awk filter will need updating.
```

Good (trivial):
```
CH-42388 chore: remove action out of create-pv-v2
```

Bad:
```
fix stuff
CH-42388
Updated
```
