---
name: cg-explain
description: Explain a piece of code — API endpoint, business logic, module, or flow — by spawning 2-3 parallel research agents to gather context, then synthesizing a concise caveman-style explanation with ASCII diagrams. Use whenever the user asks "explain", "how does X work", "walk me through", "what does Y do", "describe the flow of", or wants to understand code they're looking at. Trigger even if the target is vague — the skill figures out what to look at.
---

# CG Explain

Spawn parallel agents to research the target, then synthesize a tight explanation with ASCII visuals. No fluff.

## Step 1: Scope the target

Parse the user's request to identify:
- **Target**: function name, file path, endpoint route, module name, or concept
- **Domain hint**: API / business logic / component / flow (use what the user says; default to "code")

If the target is ambiguous, do a quick codegraph search or grep to locate it before spawning agents.

```bash
# codegraph if indexed
codegraph explore "<target name>"
# or
grep -r "<target>" . --include="*.ts" --include="*.go" --include="*.py" -l | head -10
```

Use the result to estimate **complexity**:
- **Small** (1-2 files, <200 lines): spawn 2 agents
- **Large** (3+ files, 200+ lines, or multiple integrations): spawn 3 agents

## Step 2: Spawn agents in parallel

Launch all agents in the same turn.

### Agent 1 — Structure Scout
```
Research task (read-only):
Target: <target>
Goal: Find the entry point, file locations, function/method signatures, exported interfaces, and direct dependencies (imports, called functions, injected services).
Output: bullet list — file:line for each key symbol, plus the raw function signatures. No explanations yet.
```

### Agent 2 — Logic Tracer
```
Research task (read-only):
Target: <target>
Goal: Trace the execution path from entry to exit. Identify: main steps in order, branching conditions, data transformations, error paths, return shape.
Use codegraph or grep to follow the call chain.
Output: numbered execution steps (terse). Note any surprising or non-obvious behavior.
```

### Agent 3 (large targets only) — Integration Mapper
```
Research task (read-only):
Target: <target>
Goal: Find what this target connects to externally — other services, DB queries, queues, external APIs, config, auth. Also find who CALLS this target (callers/consumers).
Output: bullet list of integrations and callers, each with file:line.
```

## Step 3: Synthesize explanation

Read all agent outputs, then write the explanation. Follow this structure exactly — no preamble, no "I'll explain", start directly with the content:

---

### `<TargetName>` — <one-line job description>

**What**: [1 sentence. What problem does it solve?]

**How** (execution steps):
1. [Step. Terse.]
2. [Step.]
3. ...

[ASCII diagram here — see rules below]

**Key pieces**:
- `symbol` — role (one phrase)
- `symbol` — role

**Callers / consumers** (if found):
- `caller` at `file:line`

**Watch out**:
- [Non-obvious behavior, gotcha, or edge case — only if genuinely surprising. Skip if none.]

---

## ASCII diagram rules

Draw a diagram whenever the target has ANY of: multi-step flow, branching, components interacting, data moving between layers, request/response cycle, state transitions.

Pick the right shape:

**Linear flow** (request through layers):
```
Request → [Auth] → [Validate] → [Handler] → [DB] → Response
```

**Branching logic**:
```
Input
  ├─ condition A → path A → result A
  ├─ condition B → path B → result B
  └─ else        → error
```

**Component interaction**:
```
┌──────────┐    call     ┌──────────┐
│ ServiceA │ ──────────► │ ServiceB │
│          │ ◄────────── │          │
└──────────┘   response  └──────────┘
```

**Data transformation**:
```
RawInput → [parse] → DTO → [validate] → [transform] → Output
```

**Layered architecture**:
```
Controller
    │
    ▼
 Service  ◄── ExternalAPI
    │
    ▼
Repository
    │
    ▼
   DB
```

Rules:
- Keep diagrams narrow (max ~60 chars wide)
- Label arrows with the action/data, not just an arrow
- One diagram per explanation — the most important one
- If the flow is trivial (single function, no branching), skip the diagram

## Writing style

Caveman mode throughout:
- Drop articles (a/an/the), filler words (basically, just, simply, really)
- Fragments OK. Short synonyms (big not extensive, fix not "implement a solution for")
- Technical terms stay exact — don't dumb down type names, function names, SQL clauses
- Max 3 sentences per section prose block before switching to bullets/steps
- Code references always formatted as `backtick`

## Output length

- Small target: aim for ~30-50 lines total
- Large target: aim for ~50-80 lines total
- If it's getting longer, cut prose first, keep the diagram and key pieces
