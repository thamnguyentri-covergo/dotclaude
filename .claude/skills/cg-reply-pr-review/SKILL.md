---
name: cg-reply-pr-review
description: Fetch unresolved PR review threads on the current branch's pull request, analyze each comment against the code diff, and output a JSON array of decisions and draft replies. Use when asked to reply to PR reviews, respond to reviewer comments, address PR feedback, draft replies to code review threads, or handle review comments on the current branch's PR.
---

# CG Reply PR Review

Fetches unresolved review threads from the current branch's PR, reads the code diff for context, classifies each comment, and outputs a JSON array of draft decisions and replies. Does not post anything — output only.

## Step 1: Fetch unresolved threads

```bash
pr-threads-not-from-me
```

If the result is `[]`, output `[]` and stop.

## Step 2: Get code context

```bash
BASE=$(gh pr view --json baseRefName --jq '.baseRefName')
git diff $BASE...HEAD
```

This gives you the full diff of what this branch changes relative to the merge target. Use it to understand *what code* each review comment is referring to, even if the comment doesn't include a file/line reference.

## Step 3: Analyze each thread

For each thread, read:
- `messages[0].body` — the original reviewer comment
- Any subsequent messages — prior back-and-forth context
- The relevant diff section — what actually changed in the code

Then classify the comment and decide:

| Comment Type | Valid? | Urgency | Decision |
|---|---|---|---|
| Critical bug / correctness risk | Yes | High | `fix` |
| Nitpick / nice-to-have | Yes | Low | `fix` if trivial, `no-fix` with a note to defer |
| Misunderstanding of the code | No | None | `no-fix` — clarify the intent |
| Subjective / style preference | Debatable | Medium | `no-fix` with rationale, or `fix` if you agree |
| Informational question | N/A | None | `no-fix` — answer the question, offer to add a comment |

When in doubt between `fix` and `no-fix`, lean toward `no-fix` with a clear explanation rather than an uncommitted "maybe".

## Step 4: Draft each reply

Tone: **clear, casual, polite, straightforward**. Get to the point. No fluff, no over-apologizing, no corporate speak.

Patterns by type:
- **Bug fix**: "Good catch — fixed. [One sentence on what changed.]"
- **Nitpick (deferred)**: "Fair point! I'll track this as a follow-up to keep the PR focused."
- **Nitpick (fixed)**: "Done, good call."
- **Misunderstanding**: "This is intentional — [one sentence of context]. Happy to add an inline comment if it helps."
- **Preference (agreed)**: "You're right, updated."
- **Preference (disagreed)**: "[Your rationale in one sentence]. Open to discussing if you feel strongly."
- **Question**: "[Direct answer]. Let me know if that's unclear."

Keep replies under 3 sentences unless the context genuinely needs more.

## Step 5: Output

Output a raw JSON array — one entry per thread, no markdown wrapper around it:

```json
[
  {
    "thread_id": "PRRT_kwDOSzQ4Wc6HoD9A",
    "first_message": "Comment at line 8",
    "decision": "fix",
    "reply": "Good catch — that null check was missing. Fixed."
  },
  {
    "thread_id": "PRRT_kwDOSzQ4Wc6HoD-t",
    "first_message": "Comment at line 16",
    "decision": "no-fix",
    "reply": "This is intentional — the upstream validator already guarantees non-null here. Happy to add a comment if it helps future readers."
  }
]
```

Output the JSON only. No preamble, no explanation around it.
