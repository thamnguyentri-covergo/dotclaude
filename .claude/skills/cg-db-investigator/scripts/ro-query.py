#!/usr/bin/env python3
"""Run a read-only mongosh script against $DEV_MONGODB_URI.

Usage: ro-query.py <<'EOF'
db.getSiblingDB("x").getCollection("y").find({}).limit(5).toArray()
EOF

The script is rejected before it reaches mongosh if it could write.
"""
import os
import re
import subprocess
import sys

WRITE_OPS = (
    "insert insertOne insertMany update updateOne updateMany replaceOne remove deleteOne deleteMany "
    "bulkWrite findOneAndUpdate findOneAndReplace findOneAndDelete findAndModify save drop dropDatabase "
    "dropIndex dropIndexes createCollection createIndex createIndexes createView createSearchIndex "
    "renameCollection runCommand adminCommand createUser updateUser dropUser dropAllUsers createRole "
    "updateRole dropRole grantRolesToUser revokeRolesFromUser shutdownServer compact reIndex hideIndex "
    "unhideIndex convertToCapped setProfilingLevel killOp fsyncLock fsyncUnlock enableSharding "
    "shardCollection mapReduce watch startSession withTransaction setReadPref"
).split()
# Exact names, so fields like updatedAt / createdAt / isDeleted stay allowed.
WRITE_WORDS = re.compile(r"\b(" + "|".join(WRITE_OPS) + r")\b|\$(out|merge|function|accumulator|where)\b")

ALLOWED_CALLS = {
    # mongosh read API
    "getMongo", "getDBNames", "getSiblingDB", "getCollection", "getCollectionNames", "getCollectionInfos", "getName",
    "find", "findOne", "aggregate", "countDocuments", "estimatedDocumentCount", "count",
    "distinct", "getIndexes", "stats", "explain", "sort", "limit", "skip", "project",
    "projection", "hint", "maxTimeMS", "batchSize", "toArray", "pretty", "hasNext", "next",
    "print", "printjson", "ObjectId", "ISODate", "Date", "UUID", "NumberLong", "NumberDecimal",
    "stringify", "parse", "EJSON",
    # plain JS on results
    "map", "filter", "forEach", "reduce", "slice", "join", "includes", "push", "some", "every",
    "keys", "values", "entries", "fromEntries", "toString", "toISOString", "toJSON", "getTime",
    "now", "floor", "round", "ceil", "max", "min", "abs", "String", "Number", "Boolean", "Array",
    "isArray", "length", "at", "flat", "flatMap", "concat", "indexOf", "startsWith", "endsWith",
    "toLowerCase", "toUpperCase", "trim", "split", "padStart", "Set", "Map", "has", "get", "set",
    "add", "from", "localeCompare", "toFixed", "test", "match",
    # keywords that precede "("
    "if", "for", "while", "switch", "return", "catch", "of", "in", "typeof",
}

BLOCKED_PATTERNS = [
    (re.compile(r"\\[ux]"), "escape sequences"),
    (re.compile(r"\]\s*\("), "calling a bracket-accessed value"),
    (re.compile(r"\)\s*\("), "calling a call result"),
    (re.compile(r"[\w$)\]]\s*\[(?!\s*-?\d+\s*\])"), "non-numeric bracket access (use getCollection)"),
    (re.compile(r"[{,]\s*\[[^\]]*\]\s*:"), "computed keys"),
    (re.compile(r"\b(function|Function|eval|load|require|process|fs|globalThis|this|Reflect|Proxy"
                r"|constructor|prototype|__proto__|import|fetch|exec\w*|setTimeout|setInterval"
                r"|quit|exit|use|sh|rs|sp)\b"), "blocked identifier"),
]

MAX_OUTPUT = 20_000

CALL = re.compile(r"([A-Za-z_$][\w$]*)\s*\(")


def violations(script: str) -> list[str]:
    found = [f"write/admin op: {m.group(0)}" for m in WRITE_WORDS.finditer(script)]
    for pattern, why in BLOCKED_PATTERNS:
        found += [f"{why}: {m.group(0)!r}" for m in pattern.finditer(script)]
    found += [f"call not in allowlist: {m.group(1)}()" for m in CALL.finditer(script)
              if m.group(1) not in ALLOWED_CALLS]
    return found


def main() -> int:
    script = sys.stdin.read().strip()
    if not script:
        print("REJECTED: empty script on stdin", file=sys.stderr)
        return 2
    bad = violations(script)
    if bad:
        print("REJECTED (read-only guard):\n  " + "\n  ".join(dict.fromkeys(bad)), file=sys.stderr)
        return 2
    uri = os.environ.get("DEV_MONGODB_URI")
    if not uri:
        print("DEV_MONGODB_URI is not set", file=sys.stderr)
        return 2
    res = subprocess.run(["mongosh", uri, "--quiet", "--norc", "--eval", script],
                         capture_output=True, text=True)
    out = res.stdout
    if len(out) > MAX_OUTPUT:
        out = out[:MAX_OUTPUT] + f"\n... TRUNCATED ({len(res.stdout)} chars). Narrow the query: filter, project, limit.\n"
    sys.stdout.write(out)
    sys.stderr.write(res.stderr)
    return res.returncode


if __name__ == "__main__":
    sys.exit(main())
