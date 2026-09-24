---
name: cg-db-investigator
description: Investigate data in the CoverGo DEV MongoDB with read-only mongosh queries (connection from $DEV_MONGODB_URI) and report findings. Use when the user runs /cg-db-investigator, or asks to check, look up, verify, count, or debug anything stored in Mongo / the dev database — e.g. "check in mongo whether tenant X has SSO config", "how many policies are stuck in pending on dev", "does user abc exist in dev db", "why is this record missing", "what does the entity doc look like". Read-only: never writes, updates, or deletes.
allowed-tools: Bash(~/.claude/skills/cg-db-investigator/scripts/ro-query.py:*), Bash($HOME/.claude/skills/cg-db-investigator/scripts/ro-query.py:*)
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "$HOME/.claude/skills/cg-db-investigator/scripts/block-raw-mongo.sh"
---

# CG DB Investigator

Answer a question about data in the DEV MongoDB. Read only.

## The one way to query

Every query goes through the guard script, script on stdin:

```bash
~/.claude/skills/cg-db-investigator/scripts/ro-query.py <<'EOF'
db.getSiblingDB("<db>").getCollection("<coll>").find({ ... }).limit(10).toArray()
EOF
```

- The script rejects anything that can write (insert/update/delete/drop/create, `$out`, `$merge`, `runCommand`, …) and exits 2.
- A hook blocks raw `mongosh` and any read of `$DEV_MONGODB_URI` while this skill runs.
- Never print, echo, or log the connection string. It holds credentials.

If the guard rejects a query, rewrite it as a read. Never try to get around the guard. If the question truly needs a write (for example "fix this record"), stop and give the user the write query to run themselves.

Guard rules to write around:
- Use `db.getSiblingDB("name")` and `.getCollection("name")`. No `use`, no `db["x"]`.
- Bracket access only with numbers: `r[0]`. Use arrow functions, not `function`.
- Result-shaping JS is fine: `.map`, `.filter`, `Object.keys`, `printjson`, `EJSON.stringify`.

## Workflow

1. **Find the database.** Names look like `<Service>-<tenant>_<env>`, e.g. `EntityManagement-prudential_dev`. There are hundreds, so always filter:
   ```js
   db.getMongo().getDBNames().filter(n => /entity/i.test(n) && /prudential/i.test(n))
   ```
2. **Find the collection.** `db.getSiblingDB("<db>").getCollectionNames()`.
3. **Learn the shape.** Look at one doc before filtering on fields. Field names differ between services (`tenantId` vs `TenantId`, `_id` as string vs ObjectId).
   ```js
   db.getSiblingDB("<db>").getCollection("<coll>").findOne()
   ```
4. **Run targeted queries.** Always add `.limit(n)` and a projection. Add `.maxTimeMS(15000)` on big collections. Prefer `countDocuments` or `aggregate` + `$group` over pulling raw docs.
5. **Stop when the question is answered.** Not when the data runs out.

Output is capped at 20k chars. If you see `TRUNCATED`, narrow the query. Do not page through everything.

When the user gives an id, try both string and `ObjectId("...")` forms before calling it missing.

## Report format

```
## Answer
<1–3 sentences. Direct answer to the question.>

## Evidence
- `<db>.<collection>`: <query in short form> → <key result>
- ...

## Notes
<Only if needed: assumptions, ambiguity, what was not checked, suggested next query.>
```

Quote real values from the results. Mask secrets (passwords, tokens, client secrets) as `***`. If the data shows nothing, say "not found" plus which db, collection, and filter you checked.
