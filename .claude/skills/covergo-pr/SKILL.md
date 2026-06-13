---
name: covergo-pr
description: Create a GitHub pull request following CoverGo's PR guideline. Reads the linked Jira ticket (title + description), inspects the current branch's diff, drafts a compliant PR title and description, then opens the PR with `gh pr create`. Use when the user runs /covergo-pr <Jira-link> or asks to "open a CoverGo PR" / "create PR for ticket X". Source guideline - https://covergo.atlassian.net/wiki/spaces/Engineering/pages/1166639159/Pull+Request+Creation+and+Review+Guideline
---

# CoverGo pull request skill

Create a PR that satisfies the CoverGo "Pull Request Creation and Review Guideline".

## Inputs

- `$1` — a Jira ticket URL (e.g. `https://covergo.atlassian.net/browse/CH-42388`) **or** a bare Jira key (`CH-42388`).
- If missing, extract the Jira key from the current branch name (regex `[A-Z]+-[0-9]+`). If still missing, ask the user.

## Guideline requirements (must satisfy)

**Title format** — `<JIRA-KEY> <Commit message text>`
- No colon separator between the key and the text.
- Present tense, imperative mood ("Update client", not "Updated client" / "Updates client").
- First letter of the message uppercase.
- Example: `CGG-8080 Update client`.
- Do **not** prepend Conventional Commit prefixes (no `feat:`, `fix:` etc.) in the **PR title** — the guideline format is strict.

**Description** — must be non-empty and must explain:
- The **purpose** of the change and **why** it is needed (the "how it was implemented" summary — not a copy of the Jira ticket which says "what").
- Points of interest for the reviewer: tricky decisions, caveats, follow-ups, performance/security notes.
- A link to the Jira ticket alone is **not** a valid description.
- If the target repo has a `.github/pull_request_template.md`, follow that template's sections.
- Mention the reason if the diff exceeds **500 LOC** (soft limit per guideline).

**Other**
- Squash-merge is the standard; do not change merge settings.
- Do not push or merge without user confirmation.

## Workflow

### 1. Gather context (run in parallel)

- `git status`
- `git branch --show-current`
- `git remote -v` (to confirm a remote exists)
- `git log --oneline origin/HEAD..HEAD` *(fall back to `origin/main` or `origin/master` if `origin/HEAD` is unset)*
- `git diff --stat <base>...HEAD` and `git diff <base>...HEAD` for the actual changes
- Check for `.github/pull_request_template.md` in the repo root and `.github/` directory
- Extract the Jira key from `$1` or the branch name

### 2. Fetch the Jira ticket

Use the Atlassian MCP tool `mcp__claude_ai_Atlassian_Rovo_2__getJiraIssue` with:
- `cloudId`: `covergo.atlassian.net`
- `issueIdOrKey`: the Jira key (e.g. `CH-42388`)

Pull out:
- Issue **summary** (title)
- Issue **description** (the "what" / business context)
- Issue **type** (Story / Bug / Task) — informs whether the PR is a feature, fix, or chore

If the fetch fails (auth, network), ask the user to paste the ticket summary + description.

### 3. Draft the PR title

Format: `<JIRA-KEY> <Imperative summary>`

Pick the imperative summary from:
1. The most recent commit subject on the branch if it already starts with the Jira key — strip the key and reuse the rest (cleaned up).
2. Otherwise synthesize from the Jira summary, rewritten imperative + uppercase first letter.

Keep ≤ ~80 chars. No trailing period.

### 4. Draft the PR description

Default structure (plain markdown, no required headings unless a repo template exists):

```
## Summary
<1–3 sentences: what the PR does and why. Focus on the "how" — implementation approach,
not a restatement of the Jira ticket.>

## Changes
- <bullet per cohesive change group, mapped to commits where useful>
- <…>

## Notes for reviewer
- <points of interest: tricky logic, non-obvious tradeoffs, deferred work, perf/security notes>
- <call out anything that needs special attention>

## Jira
[<JIRA-KEY>](<full Jira URL>)
```

Rules:
- Only include sections that add real signal. Drop `Notes for reviewer` if there are none.
- Do **not** restate the Jira ticket verbatim. The Jira link covers "what".
- If a `pull_request_template.md` exists, use **its** structure instead and fill the sections.
- If diff > 500 LOC, add a short paragraph explaining why the PR is large (e.g. generated code, migration, mechanical rename).

### 5. Pre-flight checks

- Confirm the branch is pushed: `git rev-parse @{u}` — if it fails or is behind, run `git push -u origin <branch>` **after** confirming with the user.
- Confirm the base branch (default to `main` or `master`; if the repo uses `develop`, infer from `git remote show origin` or ask).
- Show the drafted title and description to the user for approval **before** calling `gh pr create`.

### 6. Create the PR

```bash
gh pr create \
  --title "<JIRA-KEY> <Title text>" \
  --base <base-branch> \
  --body "$(cat <<'EOF'
<rendered description from step 4>
EOF
)"
```

Return the PR URL to the user.

### 7. After creation

- Do **not** auto-request reviewers, post to Slack, or merge.
- Remind the user (one line) that per the guideline they need: 1 internal-squad approval + 1 code-owner approval, and that code-owner review is requested in `#engineering-pr-reviews`.

## Do not

- Do not add `Co-Authored-By` / `Generated with Claude Code` footers unless the user asks.
- Do not use `--draft` unless the user asks.
- Do not push, force-push, or merge without explicit user confirmation.
- Do not invent context that isn't in the diff or the Jira ticket.
- Do not paste the Jira description verbatim into the PR body — summarize and focus on **how** it was implemented.
- Do not use a Conventional Commit prefix in the PR title (`feat:`, `fix:`); the guideline format omits it.

## Examples

### Good title
```
CH-42388 Expose components output from create-pv-v2 action
```

### Good description (feature)
```
## Summary
Downstream SBOM generation needs a machine-readable list of
<component>:<version> pairs produced by `crt release create-v2`. The
action previously only printed results to logs, so callers had no
handle. This PR tees crt stdout to a log file, parses the markdown
table with awk, and exposes the result via `$GITHUB_OUTPUT`.

## Changes
- Add `components` output to `action.yml`
- Tee `crt` stdout to `crt.log` and parse rows with awk
- Update README with the new output and a usage example

## Notes for reviewer
- Parsing depends on crt's current table format; the awk filter will
  need updating if crt changes its output layout. Tracked in CH-42400.
- No unit tests — action is a thin shell wrapper; covered by the
  integration workflow in `.github/workflows/test-action.yml`.

## Jira
[CH-42388](https://covergo.atlassian.net/browse/CH-42388)
```

### Bad
- Title: `CH-42388` (bare key), `Fixed stuff`, `feat: CH-42388: update client` (wrong format).
- Description: just a Jira link, or empty, or a copy-paste of the Jira ticket.
