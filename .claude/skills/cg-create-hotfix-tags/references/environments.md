# Environment routing

Mirrors the `case` table in k8s-saas `.github/workflows/bulk-generate-hotfix-prs.yaml` (source of truth — re-read it when an env is added). Paths are relative to `datacenters/`.

| env | base dir | backend overlay | frontend overlay |
|---|---|---|---|
| ASIA-QA | aws/ap-southeast-1/qa | backend | frontend |
| ASIA-PREPROD | aws/ap-southeast-1/preprod | backend | frontend |
| ASIA-PROD | aws/ap-southeast-1 | backend | frontend |
| CA-UAT | aws/ca-central-1/uat | backend | frontend |
| CA-PREPROD | aws/ca-central-1/preprod | backend | frontend |
| CA-PROD | aws/ca-central-1/production | backend | frontend |
| EU-UAT | aws/eu-central-1/uat | backend | frontend |
| EU-PROD | aws/eu-central-1/production | backend | frontend |
| ME-UAT | gcp/me-central2/uat | backend | frontend |
| ME-PREPROD | gcp/me-central2/uat | backend-preprod | frontend-preprod |
| ME-PROD | gcp/me-central2/production | backend | frontend |
| ASIAEB-PREPROD | aws/ap-southeast-1/preprod | backend | frontend |
| ASIAEB-PROD | aws/ap-southeast-1 | backend | frontend |

Channel id for a tag suffix = the env label lowercased with dashes removed (`CA-PREPROD` -> `capreprod`). `*-QA` takes a plain patch bump with no suffix.
