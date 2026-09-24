---
name: cg-k8s-configs
description: Given one or more CoverGo k8s-saas PR URLs, print the env vars each PR adds/changes/removes on k8s Deployments (as YAML) plus the `kubectl set env` commands to apply them live on the cluster. Use whenever the user passes k8s-saas PR links and wants the env config, the kubectl commands, or wants to hot-patch a pod before Flux syncs — e.g. "/cg-k8s-configs <pr>", "give me kubectl for this k8s-saas PR", "what env vars does PR 16725 set".
---

# CG K8s Configs

Input: one or more `https://github.com/CoverGo/k8s-saas/pull/<n>` URLs (or bare PR numbers → repo `CoverGo/k8s-saas`).

## Step 1: Read each PR

```bash
gh pr view <url> --json headRefName,files
gh pr diff <url>
```

Keep only files whose diff touches an `env:` list (HelmRelease `spec.values...env`, Deployment container `env`). Skip everything else silently.

## Step 2: Resolve deployment name + namespace per file

Fetch the full file at the PR head — the diff hunk alone doesn't show the metadata:

```bash
gh api "repos/CoverGo/k8s-saas/contents/<path>?ref=<headRefName>" -q .content | base64 -d
```

Also fetch the sibling `kustomization.yaml` in the same dir, because kustomize patches often override the name or namespace.

**Deployment name**, first hit wins:
1. `spec.values.fullnameOverride` (or `spec.values.<subchart>.fullnameOverride`)
2. kustomize patch replacing `/metadata/name`
3. HelmRelease `metadata.name`
4. plain Deployment `metadata.name`

**Namespace**, first hit wins:
1. `spec.values.namespace` or `spec.values.<subchart>.namespace` (e.g. `covergo-app.namespace`)
2. kustomize patch replacing `/spec/values/namespace`
3. `spec.targetNamespace`
4. Deployment `metadata.namespace`

Never use the HelmRelease's own `metadata.namespace` (`flux-system`) — that's where Flux lives, not the pod. If still unknown, write `<namespace>` and flag it.

**Cluster**: the path `datacenters/<cloud>/<region>/<env>/...` tells which cluster. Show it so the user picks the right kube context.

## Step 3: Extract env changes

From the diff, per file:
- `+ - name: X` with `value:` → **added/changed** (if a `- name: X` line with the same name is removed in the same hunk, it's a change).
- `- - name: X` with no matching `+` → **removed**.
- `valueFrom` entries (secretKeyRef, fieldRef) → include in YAML, but no `kubectl set env` value; note them under Commands as a comment.

Keep values exactly as written (quotes stripped only for the kubectl command). Drop YAML comments.

## Step 4: Output

Exact format, one block per PR if several:

````
## <PR title> (#<n>)
Cluster: <cloud>/<region>/<env>

K8s Env Vars:
```yaml
# <namespace>/<deployment>
- name: X
  value: "..."
# removed: Y
```

Commands:
```bash
kubectl -n <namespace> set env deployment/<deployment> \
  X='...' \
  Z='...'
kubectl -n <namespace> set env deployment/<deployment> Y-
```
````

Rules:
- One `set env` per deployment covering all its added/changed vars; removals in a separate `NAME-` command.
- Single-quote values in commands; escape embedded `'` as `'\''`.
- End with one line: `Manual edits get overwritten on the next Flux Helm upgrade — merge the PR to keep them.`
