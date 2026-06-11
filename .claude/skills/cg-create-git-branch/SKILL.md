---
name: cg-create-git-branch
description: Create a new git branch from a Jira ticket URL — fetches ticket code and title from Jira, asks the user whether it's a feature or hotfix, then creates and checks out a branch named `<kind>/<ticket-code>-<kebab-title>` from the current repo's default branch. Use whenever the user pastes an Atlassian/Jira link (covergo.atlassian.net, CH-XXXXX) and asks to start work, create a branch, check out a new branch, begin a ticket, or any phrasing like "branch for CH-12345", "start CH-44295", "checkout new branch for this ticket", "create branch from Jira", "new feature branch", "hotfix branch from ticket". Also trigger when the user gives just a ticket code (e.g. CH-44295) plus any branching intent, even without the full URL.
---

# CG Create Git Branch

Create a new git branch from a Jira ticket. The user gives a Jira URL (or a bare ticket code like `CH-44295`); the skill fetches the title, asks the kind (feature/hotfix), and creates a branch in the current working directory's repo.

## Naming convention

```
<kind>/<TICKET-CODE>-<kebab-slug-of-title>
```

- `kind` is `feature` or `hotfix` (user picks)
- `TICKET-CODE` is preserved as-is, uppercase, including the dash (e.g. `CH-44295`)
- `kebab-slug-of-title` is the ticket title lowercased, non-alphanumeric chars replaced with `-`, runs of `-` collapsed, leading/trailing `-` stripped
- No length cap — keep the full title

**Example:**
- Ticket: `CH-44295` titled `Shared Library - Create CoverGo.BuildingBlocks.QueryFilter Library`
- Kind: `feature`
- Branch: `feature/CH-44295-shared-library-create-covergo-buildingblocks-queryfilter-library`

## Step 1: Extract the ticket code

From the user's message, pull the ticket code with regex `[A-Z]+-\d+`. Accept both forms:
- Full URL: `https://covergo.atlassian.net/browse/CH-44295`
- Bare code: `CH-44295`

If no code is found, ask the user to paste the Jira URL or ticket code.

## Step 2: Fetch the ticket title from Jira

Use the Atlassian MCP. The flow:

1. Get the Atlassian cloudId:
   ```
   mcp__claude_ai_Atlassian_Rovo_2__getAccessibleAtlassianResources
   ```
   Pick the resource whose URL matches `covergo.atlassian.net` and use its `id` as `cloudId`.

2. Fetch the issue:
   ```
   mcp__claude_ai_Atlassian_Rovo_2__getJiraIssue
   { "cloudId": "<id>", "issueIdOrKey": "CH-44295" }
   ```
   Read `fields.summary` — that is the title.

If the MCP call fails (auth, network, not in the user's accessible resources), tell the user briefly and ask them to either paste the title manually or run `mcp__claude_ai_Atlassian_Rovo_2__authenticate` first.

## Step 3: Ask the user the kind

Use the `AskUserQuestion` tool with these two options exactly:

- `feature` — new feature, enhancement, story work (default)
- `hotfix` — urgent production fix

Even if the user already hinted at the kind in their original message (e.g. "create a hotfix branch for CH-1234"), confirm by asking — it's a one-click confirmation and prevents misclassification on a ticket that's about to drive a PR and a Cloudflare deploy.

If the user types something other than the two options, treat anything matching `hot.?fix` as `hotfix`, otherwise `feature`.

## Step 4: Build the slug

Sanitize the title with this transform:

1. Lowercase the whole string.
2. Replace every run of non-alphanumeric characters (anything not `[a-z0-9]`) with a single `-`.
3. Strip leading and trailing `-`.

This handles colons, dots, parentheses, slashes, ampersands, quotes, emoji, accents — anything Jira allows in a title. The dot in `CoverGo.BuildingBlocks.QueryFilter` becomes `-`, the result is `covergo-buildingblocks-queryfilter`.

A one-liner that does this in bash (used by Step 6):

```bash
slug=$(printf '%s' "$TITLE" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g')
```

## Step 5: Detect the default branch

The user is in a sub-repo (the meta-repo CoverGo.Workspace contains many git repos under `Backend/`, `Frontend/`, etc.). The current working directory's repo is the target — do not `cd` elsewhere. The CLAUDE.md guidance is explicit: branches must be made inside the sub-repo, never on the meta-repo.

Detect the default branch from the remote:

```bash
default=$(git -C "$PWD" symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's@^origin/@@')
```

If that returns empty (a fresh clone without HEAD set, or no `origin`), try in order: `main`, `master`, `dev` — pick the first that exists as a local or remote branch:

```bash
if [ -z "$default" ]; then
  for candidate in main master dev; do
    if git -C "$PWD" show-ref --verify --quiet "refs/heads/$candidate" \
       || git -C "$PWD" show-ref --verify --quiet "refs/remotes/origin/$candidate"; then
      default="$candidate"; break
    fi
  done
fi
```

If still empty, stop and ask the user which branch to base off — don't guess.

## Step 6: Pre-flight checks before creating the branch

Before touching the working tree, verify three things and bail out cleanly if any fail. These checks protect the user's in-progress work — silent failures here lose commits.

1. **Working tree is clean.** Run `git -C "$PWD" status --porcelain`. If non-empty, stop and tell the user what's dirty; ask whether to stash, commit, or proceed anyway. Do not auto-stash.
2. **Branch does not already exist.** Run `git -C "$PWD" show-ref --verify --quiet "refs/heads/$BRANCH"`. If it exists, ask the user whether to check it out instead, pick a different name, or delete the existing one. Do not silently overwrite.
3. **We are in a git repo at all.** `git -C "$PWD" rev-parse --is-inside-work-tree` returns `true`. If not, stop and tell the user the current directory isn't a git repo.

## Step 7: Create and checkout the branch

Once checks pass:

```bash
git -C "$PWD" fetch origin --quiet
git -C "$PWD" checkout "$default"
git -C "$PWD" pull --ff-only origin "$default"
git -C "$PWD" checkout -b "$BRANCH"
```

Why `--ff-only`: if the local default branch has diverged from origin, a merge here would surprise the user. Stop, report the divergence, and let them resolve.

After the final command, print the branch name and the sub-repo path:

```
Branch created: feature/CH-44295-shared-library-create-covergo-buildingblocks-queryfilter-library
Repo: Backend/Libraries/building-blocks-data-access
Base: master @ <short-sha>
```

The base sha comes from `git -C "$PWD" rev-parse --short HEAD` right after the `pull --ff-only` and before the `checkout -b`.

## End-to-end example

User message:
> Create a branch for https://covergo.atlassian.net/browse/CH-44295

Skill:
1. Extracts `CH-44295`.
2. Calls Jira MCP → title is `Shared Library - Create CoverGo.BuildingBlocks.QueryFilter Library`.
3. Asks: "What kind of branch? feature / hotfix" — user picks `feature`.
4. Slug: `shared-library-create-covergo-buildingblocks-queryfilter-library`.
5. Branch: `feature/CH-44295-shared-library-create-covergo-buildingblocks-queryfilter-library`.
6. Default branch (auto-detected from `origin/HEAD`): `master`.
7. Working tree clean, branch doesn't exist → fetch, checkout master, pull --ff-only, checkout -b.
8. Reports the branch, sub-repo path, and base sha.

## What this skill does NOT do

- Does not push the branch upstream. The user pushes when they're ready (or the prepare-pull-request skill handles it). Pushing an empty branch creates remote noise.
- Does not commit anything. Just creates the branch.
- Does not switch directories. Operates on the current working directory only — if the user is in the meta-repo root by accident, the pre-flight clean check will surface that (the meta-repo is always dirty with sub-module pointers).
- Does not edit the Jira ticket. Read-only on Jira.
