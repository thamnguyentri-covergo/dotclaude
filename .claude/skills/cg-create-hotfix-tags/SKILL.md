---
name: cg-create-hotfix-tags
description: Plan and cut CoverGo hotfix releases from merged PRs — resolves the version deployed to each target environment, computes the next channel tag (v2.382.9-cauat1.2), creates the release branch, cherry-picks the fixes cumulatively, and publishes the GitHub release so CI builds the image. Run it ONLY when the user explicitly invokes /cg-create-hotfix-tags with PR links; never start it on your own from a conversation that merely mentions hotfixes, releases or environments, because it pushes tags and fires image builds.
---

# cg-create-hotfix-tags

Turns merged PRs into per-environment hotfix releases, then hands `hotfix-tags.md` to
`cg-create-hotfix-issues`, which opens the k8s-saas `[HOTFIX]` tracking issue.

Work in two phases with a confirmation gate between them. Phase A only reads; phase B pushes
branches and publishes releases, which fires image builds and cannot be undone quietly. The user
must see the whole plan before anything is pushed — a wrong tag deployed to PROD costs far more
than the round-trip of showing a table first.

## Invocation

`/cg-create-hotfix-tags <pr-url> [<pr-url> ...]` — the arguments are the merged PRs to ship:

```
/cg-create-hotfix-tags https://github.com/CoverGo/policies/pull/1821 https://github.com/CoverGo/frontend-monorepo/pull/994
```

No PR links given: ask for them and stop. Everything else you need is derived.

**Target environments.** If the user already named them (in the invocation or earlier in the
conversation), use those and do not ask again. Otherwise ask with `AskUserQuestion`, which caps
each question at 4 options, so ask in two rounds:

1. One question, `multiSelect: true`, header `Regions`, options: `ASIA`, `CA`, `EU`, `ME`
   (ASIAEB lives under ASIA).
2. One follow-up question per chosen region, each `multiSelect: true`, listing only that
   region's environments — `ASIA`: ASIA-QA, ASIA-PREPROD, ASIA-PROD; `ASIAEB`: ASIAEB-PREPROD,
   ASIAEB-PROD; `CA`: CA-UAT, CA-PREPROD, CA-PROD; `EU`: EU-UAT, EU-PROD; `ME`: ME-UAT,
   ME-PREPROD, ME-PROD. Ask ASIAEB as its own question when ASIA is chosen. More than four
   groups: make a second `AskUserQuestion` call.

When `AskUserQuestion` is unavailable (a headless or eval run), ask in plain text instead —
never assume a set of environments.

**Jira ticket** — take the `CH-` code from the PR titles and confirm it; only ask if none carry one.

Per-environment overlay routing lives in `references/environments.md`.

## Phase A — plan (read only)

Run these for every (environment × service) pair:

1. Resolve each PR to its repo, merge commit SHA, and service name:
   `gh pr view <url> --json number,title,mergeCommit,headRepository,mergedAt`
   A PR that is not merged stops the plan — say which one and why.
2. Read the version currently deployed:
   `python3 scripts/deployed_tag.py <k8s-saas-root> <ENV> <service> [backend|frontend]`
   The script raises when the environment has no manifest for that service. Do not guess a
   path or fall back to another environment — report it and drop that pair from the plan.
3. Compute the new tag:
   `python3 scripts/next_tag.py <ENV> <deployed-tag> [existing-channel-tags...]`
   Pass existing tags when you have them (`gh api repos/<owner>/<repo>/tags --jq '.[].name'`).
   With none, the script starts the channel at `1.0`; flag that row so the user can confirm no
   channel tag already exists.
4. Derive the branch from the new tag, keeping its leading `v`: backend keeps
   the dots (`v2.382.9-cauat1.2` -> `release/v2.382.9-cauat1.2`), frontend replaces every dot
   with a dash (`release/v2-382-9-cauat1-2`), because frontend tooling rejects dots in branch
   names. Never mix the two forms.
5. Write `hotfix-tags.md` (format below) with every row at `status: planned`, print the same
   table, and stop. Ask the user to confirm before phase B.

`frontend-monorepo` releases follow their own branch process — when a PR belongs to it, say so
and ask the user for the release branch instead of deriving one.

## hotfix-tags.md

Both the review surface and the resume point. Re-running this skill reads it back: rows at
`pushed` only get their build polled, never re-cherry-picked.

```markdown
---
jira: [CH-44295]
source_prs: [CoverGo/policies#1821]
---
| env | service | repo | kind | deployed | new tag | branch | cherry-picks | status |
|---|---|---|---|---|---|---|---|---|
| CA-UAT | policies | CoverGo/policies | backend | 2.382.9-cauat1.1 | v2.382.9-cauat1.2 | release/v2.382.9-cauat1.2 | a1b2c3d | planned |
```

`status`: `planned` → `pushed` → `built` → `failed`. Anything not `built` is not deployable.

## Phase B — cut the releases (after explicit confirmation)

Per row, in order:

1. `git fetch --tags`, then branch from the tag being hotfixed — the newest tag in that channel,
   not the base release, because hotfixes are cumulative and must contain every earlier fix in
   the channel: `git checkout -b release/v1.2.1 v1.2.0` (backend) / `release/v1-2-1` (frontend)
2. `git cherry-pick <sha>` for each PR's merge commit, oldest first. A conflict stops that row:
   `git cherry-pick --abort`, mark the row `failed`, report it, and carry on with other rows.
   Never resolve a hotfix conflict unattended.
3. Check each SHA is also on `main`: `git merge-base --is-ancestor <sha> origin/main`. If not,
   warn loudly — a fix that only exists on the release branch is silently reverted by the next
   platform-version promotion, which is what `pv-env-drift-daily.yaml` alerts on.
4. Push the branch, then publish the release so the build workflow fires:
   ```bash
   gh release create v2.382.9-cauat1.2 --target release/v2.382.9-cauat1.2 \
     --title "Hotfix v2.382.9-cauat1.2 — CH-44295" --notes "..." --latest=false
   ```
   `--latest=false` is not optional. Marking a hotfix as the latest release makes every repo
   consumer pick up an environment-specific build.
5. Set the row to `pushed`.

Never force-push, never delete or move an existing tag, never re-tag a published release.

## Phase C — wait for the image

Poll the build for each pushed row: `gh run list --repo <repo> --branch <branch> --limit 5`,
then `gh run watch <id>`. On success set `built`; on failure set `failed` with the run URL.
Report the final table.

Hand off: "hotfix-tags.md is ready — run `/cg-create-hotfix-issues hotfix-tags.md`". Do not create
the tracking issue here; that skill owns it, and it refuses rows that are not `built`.
