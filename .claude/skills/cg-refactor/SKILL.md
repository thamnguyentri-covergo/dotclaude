---
name: cg-refactor
description: Analyze a referenced file or folder for refactoring opportunities — split long logic into named steps, extract magic strings into constants, remove duplication (DRY), fix mixed responsibilities (SOLID), and make each function's input/output shape explicit so a reviewer can read the data pipeline top to bottom. Outputs a ranked findings report first, then applies the approved fixes. Use when the user runs /cg-refactor, or asks to "refactor this", "clean up this file", "review this for refactoring", "make this readable", "split this function", "is this DRY", or points at a file/folder and asks how to improve its structure.
---

# CG Refactor

Analyze the target, report findings ranked by payoff, apply only what the user approves. Behavior must not change.

## Step 1: Resolve the target

Target = file path, folder path, or symbol the user named. If none named, use the file most recently edited in this session; if still unclear, ask.

Read the whole target before judging anything. For a folder: list files first, read the ones with real logic (skip generated files, fixtures, snapshots, lock files, vendored code).

```bash
# folder: biggest-first, logic files only
find <target> -type f \( -name '*.js' -o -name '*.ts' -o -name '*.go' -o -name '*.py' \) \
  -not -path '*/node_modules/*' -exec wc -l {} + | sort -rn | head -20
```

Also read the target's callers and its sibling files. Two reasons: a "duplicate" may already have a shared helper a few files over, and a public function's signature can't change without checking who calls it.

## Step 2: Analyze against the five axes

For each axis, record concrete findings only — `file:line`, what is wrong, what replaces it. No generic advice.

### A. Step splitting

Flag a function when any hold:
- Does more than one thing at different levels of abstraction (fetch + transform + write in one body)
- Nesting depth ≥ 3
- Body long enough that the reader must scroll to hold it
- A comment inside the body names a phase (`// validate`, `// then build the doc`) — that comment is the extracted function's name

Fix: extract each phase into a function named for **what it produces or decides**, not how. `buildTaskFilter`, `isLeaseExpired`, `classifyDatabase` — not `handleData`, `doStep2`, `processItems`. The outer function then reads as the pipeline: a short sequence of named calls.

### B. Constants for compared strings

Flag every string (or number) literal used in a comparison, equality check, `switch` case, status assignment, or key lookup. Those are a vocabulary, not text.

Fix: one named constant object per vocabulary, in the codebase's existing constants location if there is one (look before adding a file). Reuse an existing constant if the value already has a name somewhere — a second name for the same value is a bug waiting to drift.

Skip: strings used once as a message, a log line, or a regex source. Naming those adds indirection and buys nothing.

### C. DRY

Flag duplication only when the copies share **one reason to change**. Same shape, different reasons = leave it alone and say why. Look for: repeated guard sequences, repeated build-the-same-object blocks, near-identical branches differing by one value (→ table or param), the same computation inline in several callers.

Fix: extract to one function at the level all copies can reach. If the copies live in different layers, do not invent a shared module for two callers — note it and stop.

### D. SOLID

Report only violations that hurt this code today:
- **SRP** — one module holding two unrelated reasons to change (I/O + business rules, config parsing + use of config)
- **OCP** — an `if/else` or `switch` on a type tag that grows every time a case is added → map of tag → handler
- **DIP** — business logic reaching a concrete client/driver/`process.env` directly instead of taking it as a parameter, making it untestable

Do not add an interface with one implementation, a factory for one product, or a layer "for later". That is the failure mode this axis usually causes.

### E. Visible data pipeline + solid I/O schema

The reviewer test: can a reader see, without opening any callee, what goes in and what comes out?

Flag:
- A function taking a bag (`opts`, `data`, `ctx`) whose used keys are only discoverable by reading the body → destructure the exact keys in the signature
- A return value whose shape varies by branch (object here, `null` there, throw elsewhere) → one shape, or document the contract and make the failure path a throw
- Boolean/positional params at a call site that read as nothing (`build(x, true, false)`) → named object param
- Untrusted input crossing into the module with no validation. If the repo already validates with a schema library, add one there — do not invent a new validation style.
- A missing doc line on a non-obvious contract → one JSDoc/type line stating input keys and output shape. One line, not a paragraph.

### F. Comment density

One explain comment per function, **one sentence**, only where the logic earns it: branching on several conditions, a loop with state, a parser, a precedence/classification rule, a money or security path, a non-obvious contract. Simple small functions (getter, one-line map, thin wrapper, obvious guard) get **no** comment — delete the ones that exist.

Where a comment is earned, add a small ASCII sketch of the flow or the input/output cases under it. Keep it under ~6 lines.

```js
// Classifies one cluster DB into a tenancy model; first match wins.
//   name ──▶ tenantPattern? ──▶ NEW (key = group 1)
//        ──▶ anyTenantPattern? ──▶ NEW, other tenant (no key)
//        ──▶ no match ──▶ FLEXIBLE (key = plain name)
```

Flag and cut: long prose, multi-paragraph headers, restating the code line by line, changelog/history notes, commented-out code, `// TODO` with no owner or action.

Keep as-is: comments the repo treats as spec (e.g. stub header comments), license headers, and any comment style the surrounding files already standardize on.

## Step 3: Report

No preamble. Ranked highest payoff first: payoff = clarity gained ÷ diff size.

```
### <target> — <n> findings

**1. <axis> — `file:line`**
Now: [what the code does, 1 line]
Fix: [the change, 1 line]
Why: [reader/maintenance win, 1 line]

**2. ...
```

Then:

```
**Leave alone**: [things that look refactorable but aren't, one line each with the reason]
```

Then ask which findings to apply — numbers, `all`, or `none`.

## Step 4: Apply

For each approved finding, in order:
1. Make the edit. Behavior identical — no bug fixes, no new features, no adjacent tidying. If a bug turns up, name it and leave it.
2. Match surrounding style exactly (module system, naming case, comment density, error style).
3. Remove imports/vars **your** change orphaned. Leave pre-existing dead code; mention it.

After all edits: run the repo's test command if one exists (`package.json` scripts, `Makefile`, `pytest.ini`). No tests covering the touched logic → write ONE check that fails if the refactor broke the behavior: smallest possible test in the repo's existing test style, or an `assert` self-check if the repo has no test setup.

Report: files touched, tests run + result. If tests fail, quote the output — do not describe it.

## Hard rules

- Behavior-preserving only. A refactor that changes output is a bug.
- Every changed line traces to an approved finding.
- Fewer moving parts after than before. If the diff adds files, abstractions, or indirection without deleting more complexity than it adds, drop that finding.
- Nothing speculative: no config for a value that never changes, no param nobody passes, no extension point nobody uses.
- No long prose in comments, ever. One sentence per function, only on medium/hard logic, ASCII sketch instead of paragraphs.
- Public signatures: check callers first, update all of them in the same change, or skip the finding.
