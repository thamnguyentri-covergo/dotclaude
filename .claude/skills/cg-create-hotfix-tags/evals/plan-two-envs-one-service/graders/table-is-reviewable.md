---
type: llm
focus: {source: file, path: hotfix-tags.md}
weight: 2
---
The file holds one table row per environment (CA-UAT, CA-PREPROD) for the policies service.
Each row names the currently deployed tag, the new hotfix tag, a release branch derived from
that new tag, the cherry-pick SHA a1b2c3d4, and status `planned`.
