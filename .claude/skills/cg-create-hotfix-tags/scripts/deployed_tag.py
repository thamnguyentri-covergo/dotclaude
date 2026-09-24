#!/usr/bin/env python3
"""Image tag currently deployed to an environment, read from the k8s-saas overlays.

Usage: deployed_tag.py <K8S_SAAS_ROOT> <ENV> <SERVICE> [backend|frontend]
  deployed_tag.py ~/projects/k8s-saas CA-UAT policies  ->  2.382.9

Routing mirrors the case table in .github/workflows/bulk-generate-hotfix-prs.yaml,
which is the source of truth — re-check it when an environment is added.
"""
import re
import sys
from pathlib import Path

ROUTES = {
    "ASIA-QA": ("aws/ap-southeast-1/qa", "backend", "frontend"),
    "ASIA-PREPROD": ("aws/ap-southeast-1/preprod", "backend", "frontend"),
    "ASIA-PROD": ("aws/ap-southeast-1", "backend", "frontend"),
    "CA-UAT": ("aws/ca-central-1/uat", "backend", "frontend"),
    "CA-PREPROD": ("aws/ca-central-1/preprod", "backend", "frontend"),
    "CA-PROD": ("aws/ca-central-1/production", "backend", "frontend"),
    "EU-UAT": ("aws/eu-central-1/uat", "backend", "frontend"),
    "EU-PROD": ("aws/eu-central-1/production", "backend", "frontend"),
    "ME-UAT": ("gcp/me-central2/uat", "backend", "frontend"),
    "ME-PREPROD": ("gcp/me-central2/uat", "backend-preprod", "frontend-preprod"),
    "ME-PROD": ("gcp/me-central2/production", "backend", "frontend"),
    "ASIAEB-PREPROD": ("aws/ap-southeast-1/preprod", "backend", "frontend"),
    "ASIAEB-PROD": ("aws/ap-southeast-1", "backend", "frontend"),
}

TAG_RE = re.compile(r"^\s*tag:\s*\"?([^\s\"#]+)", re.MULTILINE)


def manifest_path(root, env, service, kind="backend"):
    base, backend_overlay, frontend_overlay = ROUTES[env.upper()]
    root = Path(root).expanduser() / "datacenters" / base / "overlays"
    if kind == "frontend":
        return root / frontend_overlay / service / "release.yaml"
    return root / backend_overlay / f"{service.lower()}.yaml"


def deployed_tag(root, env, service, kind="backend"):
    path = manifest_path(root, env, service, kind)
    if not path.is_file():
        raise FileNotFoundError(f"{env} has no {kind} manifest for {service}: {path}")
    match = TAG_RE.search(path.read_text())
    if not match:
        raise ValueError(f"no `tag:` field in {path}")
    return match.group(1)


def demo():
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        be = Path(tmp) / "datacenters/aws/ca-central-1/uat/overlays/backend"
        fe = Path(tmp) / "datacenters/aws/ca-central-1/uat/overlays/frontend/coverhealth-admin"
        be.mkdir(parents=True)
        fe.mkdir(parents=True)
        (be / "policies.yaml").write_text("spec:\n  values:\n      image:\n        tag: 2.382.9 #{\"$x\":\"y\"}\n")
        (fe / "release.yaml").write_text("      tag: 2.294.2-cauat1.16 #{\"$x\":\"y\"}\n")
        assert deployed_tag(tmp, "CA-UAT", "policies") == "2.382.9"
        assert deployed_tag(tmp, "ca-uat", "Policies") == "2.382.9"
        assert deployed_tag(tmp, "CA-UAT", "coverhealth-admin", "frontend") == "2.294.2-cauat1.16"
        try:
            deployed_tag(tmp, "EU-UAT", "policies")
        except FileNotFoundError:
            pass
        else:
            raise AssertionError("missing manifest must raise, never guess a tag")
    # ME-PREPROD shares the ME-UAT cluster and reads the -preprod overlays
    assert "backend-preprod" in str(manifest_path("/r", "ME-PREPROD", "policies"))
    print("ok")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        demo()
    else:
        print(deployed_tag(*sys.argv[1:]))
