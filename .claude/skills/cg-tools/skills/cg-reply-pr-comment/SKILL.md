---
name: cg-reply-pr-comment
description: Given a pull request URL, fetch every unresolved review thread not authored by you (Copilot bots, human reviewers), spawn one subagent per thread to independently verify whether the comment is actually correct, then present a review table and — after you approve thread by thread — apply the code fixes and post the replies. Use this whenever the user pastes a PR link and wants to handle, triage, verify, answer, or respond to review comments; when they ask to check whether Copilot's review feedback is legitimate; or when they want reviewer comments on a PR fixed and replied to. Prefer this over cg-reply-pr-review whenever a PR URL is given or the user wants the fixes actually applied and the replies actually posted, rather than a JSON draft.
---

# CG Reply PR Comment

Turns a PR link into verified, approved, applied answers to review comments.

The reason this skill exists: automated reviewers (Copilot especially) produce a
mix of real bugs and confident nonsense. Replying to all of them uniformly is
either dishonest or wasteful. So each thread gets its own subagent that tries to
*prove or disprove* the comment against the real code, and nothing reaches
GitHub until the user has signed off per thread.

## Step 0: Get the PR and the code

The URL is the only argument. Everything downstream uses it verbatim — the `gh
pr-review` extension accepts a full URL as a selector, which avoids splitting
out `--repo` and `--pr`.

```bash
PR_URL="<the url the user gave>"
gh pr view "$PR_URL" --json number,title,headRefName,baseRefName,url,headRepositoryOwner
```

Two things must hold before you can verify anything:

1. **The working directory is the PR's repo.** Check `gh repo view --json nameWithOwner` against the URL. If they differ, stop and tell the user which repo to `cd` into — verification against the wrong tree is worse than no verification.
2. **The PR's head branch is checked out and current.** `git branch --show-current` should equal `headRefName`. If not, say so and ask before switching (they may have uncommitted work). You need the actual branch because subagents run tests against it.

## Step 1: Fetch unresolved threads not from you

```bash
ME=$(gh api user --jq .login)
gh pr-review review view "$PR_URL" --unresolved --not_outdated \
  | jq --arg me "$ME" '[.reviews[] | select(.comments) | .comments[]
      | select(.author_login != $me)
      | {thread_id, path, line, author_login,
         body,
         replies: [.thread_comments[]? | {author_login, body}]}]'
```

`--not_outdated` drops threads whose code no longer exists — those are noise.
Filtering on `author_login != $me` is what keeps your own threads out; a thread
where the reviewer commented and *you already replied* still shows up, and that
prior back-and-forth is important context for the subagent.

If the array is empty: say "No unresolved threads from other authors" and stop.
Nothing to approve, so don't show an empty table.

Number the threads `T1..Tn` in the order returned. That numbering is the
contract with the user for the rest of the session — never renumber it.

## Step 2: Get shared diff context once

```bash
gh pr diff "$PR_URL"
```

Pass the relevant slice to each subagent rather than making every subagent
re-fetch the whole diff. One fetch, n readers.

## Step 3: One subagent per thread

Spawn them all in a single message so they run concurrently. Use
`general-purpose`. Each gets exactly one thread — an agent judging several
threads starts rationalizing them against each other.

Prompt each with:

```
Verify one PR review comment. Decide if it is factually correct about this codebase.

PR: <url>   Branch: <headRefName>
File: <path>:<line>
Reviewer: <author_login>
Comment:
<body>
Prior replies in the thread (may contain the author's own reasoning):
<replies, or "none">

Relevant diff hunk:
<hunk for that file>

Your job is to VERIFY, not to agree. Automated reviewers are frequently wrong
about this codebase's actual conventions and runtime. Do the work:
- Read the file and the code around the line. Read what calls it.
- Check the claim against reality: does the framework version in package.json
  behave the way the comment assumes? Does the guard the comment asks for
  already exist upstream? Is the "unhandled" case actually reachable?
- Run the narrowest check that settles it — the relevant test, a one-off node
  script, a grep for every caller. Prefer evidence over reasoning.
- Read CLAUDE.md / README for conventions the comment may be ignoring.

Return exactly this JSON, no prose around it:
{
  "verdict": "valid" | "invalid" | "partly-valid",
  "confidence": "high" | "medium" | "low",
  "evidence": "1-3 sentences citing what you actually checked, with file:line or command output",
  "severity": "bug" | "risk" | "nitpick" | "question" | "none",
  "fix_plan": "concrete edits — file:line and what changes. Empty string if verdict is invalid.",
  "reply": "the reply to post, in the user's voice — see tone rules below"
}

Tone for `reply`: clear, casual, polite, direct. Under 3 sentences. No
over-apologizing, no corporate voice, no restating the comment back.
- valid + will fix: "Good catch — <what changes>. Fixed in the next push."
- partly-valid: "<the part that's right> — <fix>. <the part that isn't> is intentional because <reason>."
- invalid: lead with the fact that settles it, not with disagreement.
  e.g. "Express 5 does forward async errors — see package.json, we're on 5.1.
  The handler is covered by the error middleware."
- nitpick you'd rather defer: "Fair point, tracking it as a follow-up to keep this PR focused."
- question: answer it in one line, offer an inline code comment if it'd help.

Never write a reply that claims something is fixed unless fix_plan says how.
```

If an agent comes back `low` confidence, that is a real signal — surface it in
the table rather than smoothing it over. The user is the tiebreaker.

## Step 4: Present the table, then ask

Write for a reader who skims. Table first to decide, one short block per thread
to edit. Never a paragraph — every line is labelled and stands alone.

The `Action` column has exactly two values: `Reply + fix` or `Reply only`.

```
| # | Location | Reviewer | Comment | Verdict | Conf | Action |
|---|---|---|---|---|---|---|
| T1 | src/routes/migrations.js:10 | copilot | async errors not forwarded | invalid | high | Reply only |
| T2 | src/registry/lock.js:42 | alice | missing type in query filter | valid (bug) | high | Reply + fix |
```

Then one block per thread. Fixed labels, one line each, hard cap as shown:

```
**T2** valid (bug) · high · src/registry/lock.js:42 · alice
👮‍♂️ Reviewer says: query filter is missing `type`
🔍 Verified in code: index is (migration_id, environment, tenant, type) — this query matches a non-unique prefix
🤖 Action: Reply + fix
🛠️ Fix: src/registry/lock.js:42 — add `type` to the findOne filter
💬 Reply: "Good catch — that query was matching a non-unique index prefix. Fixed in the next push."
```

Rules for the block:

- `👮‍♂️ Reviewer says` — the comment in under 10 words. Not quoted back in full.
- `🔍 Verified in code` — one line, max two, with `file:line`. For a valid verdict it confirms the gap; for an invalid one it states the fact that kills the claim.
- `🤖 Action` — `Reply + fix` when a `Fix` line follows, `Reply only` when the block is just a reply. Must match the table row.
- `🛠️ Fix` — one line: `file:line — what changes`. Drop the line entirely when the action is `Reply only`.
- `💬 Reply` — verbatim, quoted, as it will be posted.
- No block runs past 6 lines. Long evidence gets cut, not wrapped — the user asks if they want more.
- More than 5 threads: show the first 5, say how many are left, show the rest once those are answered.

Then ask verbatim:

> What should we proceed?

## Step 5: Read the approval

The user answers per thread, terse:

```
T1. ok
T2. ok
T3. no
```

Accept the shape loosely — `T1 ok`, `1. yes`, `all ok`, `ok except T3`, `T1,T2
ok, rest no`. They are approving *the proposed action as shown*, so:

- **ok** → do it: apply the fix if there is one, post the reply.
- **no** → skip the thread entirely. No reply, no edit. They'll handle it.
- **not mentioned** → skip and say which ones you skipped for lack of an answer. Silence is not consent for something that posts publicly.
- **anything else** (a correction, "T2 ok but soften the reply", "T3 actually valid") → treat it as an instruction, revise, and re-show just that thread before acting.

## Step 6: Fix, verify, then post — in that order

Order matters: a reply saying "fixed" must not go out before the fix exists.

1. **Apply every approved fix.** Follow the repo's conventions and keep the diff to what the comment asked for — the reviewer flagged one thing, not an invitation to refactor.
2. **Run the checks.** `npm test` or whatever the repo uses. If a fix breaks something, stop before posting anything and report it — you now have new information the user approved a plan without.
3. **Post the replies:**

```bash
gh pr-review comments reply "$PR_URL" --thread-id "<thread_id>" --body "<reply>"
```

4. **Report** — one line per thread: posted / fixed / skipped, plus the files touched.

Leave the changes uncommitted and unpushed. The user reviews and pushes; that's
why the replies say "in the next push" rather than "pushed". Don't resolve the
threads either — the reviewer resolves them, and resolving your own is how a
real objection gets buried.
