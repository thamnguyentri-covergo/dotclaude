# Comments

Default: no comment. Write one only when a senior engineer would misread the
code without it.

## Never write

- Restating what the code says (`// increment counter`, `// null check`)
- Repeating a symbol's own name
- Ticket IDs, history, or "unlike before / this change does not…" — that's the
  commit body and PR
- Benchmark numbers, sample sizes, decision defenses — that's the PR
- XML doc / docstring on private members
- Comments on unreachable or impossible branches

## Write only for

- **Non-obvious why** — code looks arbitrary until you know the reason
- **A trap** — footgun the next editor would step on
- **Magic constant source** — one clause: `// 500: ~1.8x over largest observed (282)`

## Budget

- 1–2 lines. 3 is the hard ceiling. Never multi-paragraph.
- Comment must be shorter than the code it explains. If longer → rename,
  extract, or add a named constant instead.

## Editing existing code

Don't comment lines you didn't change. Don't rewrite existing comments. Delete
only comments your change made wrong.
