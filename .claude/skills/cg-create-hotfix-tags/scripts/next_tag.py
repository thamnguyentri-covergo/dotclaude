#!/usr/bin/env python3
"""Next hotfix release tag for a CoverGo environment.

Usage: next_tag.py <ENV> <DEPLOYED_TAG> [EXISTING_TAG ...]
  next_tag.py CA-UAT 2.382.9 v2.382.9-cauat1.0  ->  v2.382.9-cauat2.0
"""
import re
import sys

CHANNEL_RE = r"^v?{core}-{channel}(\d+)\.(\d+)$"


def channel_of(env):
    """CA-PREPROD -> capreprod. QA envs release a plain patch bump instead."""
    return None if env.upper().endswith("-QA") else env.lower().replace("-", "")


def core_of(tag):
    return tag.lstrip("v").split("-")[0]


def next_tag(env, deployed_tag, existing_tags=()):
    core = core_of(deployed_tag)
    channel = channel_of(env)
    if channel is None:
        major, minor, patch = (int(p) for p in core.split("."))
        return f"v{major}.{minor}.{patch + 1}"

    pattern = re.compile(CHANNEL_RE.format(core=re.escape(core), channel=re.escape(channel)))
    found = sorted(
        (int(m.group(1)), int(m.group(2)))
        for m in (pattern.match(t) for t in existing_tags)
        if m
    )
    if not found:
        x, y = 1, 0
    else:
        x, y = found[-1]
        x, y = (x, y + 1) if y > 0 else (x + 1, 0)
    return f"v{core}-{channel}{x}.{y}"


def demo():
    assert next_tag("ASIA-QA", "2.382.9") == "v2.382.10"
    assert next_tag("CA-UAT", "2.382.9") == "v2.382.9-cauat1.0"
    assert next_tag("CA-UAT", "2.382.9", ["v2.382.9-cauat1.0"]) == "v2.382.9-cauat2.0"
    assert next_tag("CA-UAT", "2.382.9", ["v2.382.9-cauat1.1"]) == "v2.382.9-cauat1.2"
    assert next_tag("CA-PREPROD", "1.1.1", []) == "v1.1.1-capreprod1.0"
    # deployed tag is itself a channel tag: the core, not the channel, is the base
    assert next_tag("CA-UAT", "2.382.9-cauat1.0", ["v2.382.9-cauat1.0"]) == "v2.382.9-cauat2.0"
    # another env's channel never counts toward this one
    assert next_tag("EU-UAT", "2.382.9", ["v2.382.9-cauat3.0"]) == "v2.382.9-euuat1.0"
    # highest wins regardless of listing order
    assert next_tag("CA-UAT", "1.1.1", ["v1.1.1-cauat2.0", "v1.1.1-cauat1.0"]) == "v1.1.1-cauat3.0"
    print("ok")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        demo()
    else:
        print(next_tag(sys.argv[1], sys.argv[2], sys.argv[3:]))
